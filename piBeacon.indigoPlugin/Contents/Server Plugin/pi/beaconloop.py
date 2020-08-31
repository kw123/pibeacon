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
import fcntl

sys.path.append(os.getcwd())
import	piBeaconUtils as U
import	piBeaconGlobals as G
import  pexpect
G.program = "beaconloop"
version   = 7.13


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

def signedIntfromString(string):
	try:
		intNumber = int(string,16)
		if intNumber > 127: intNumber -= 256
	except	Exception, e:
		U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 0
	return intNumber


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
	global lastLESCANrestart
	global rpiDataAcquistionMethod


	useHCI	 = ""
	myBLEmac = ""
	devId	 = 0
	## good explanation: http://gaiger-G.programming.blogspot.com/2015/01/bluetooth-low-energy.html
	U.logger.log(30,"(re)starting bluetooth")
	try:
		HCIs = U.whichHCI()
		for hci in HCIs["hci"]:
			cmd = "sudo hciconfig "+hci+" down"
			U.logger.log(10,"startBlueTooth down: {}" .format(cmd))
			subprocess.call(cmd, shell=True) # disable bluetooth
			time.sleep(0.2)
			cmd = "sudo hciconfig "+hci+" up"
			U.logger.log(10,"startBlueTooth  up: {}" .format(cmd))
			subprocess.call(cmd, shell=True) # enable bluetooth
			time.sleep(0.2)
			cmd	 = "sudo hciconfig {} noleadv".format(useHCI)
			U.logger.log(20,cmd) 
			subprocess.call(cmd,shell=True,stdout=subprocess.PIPE)
			cmd	 = "sudo hciconfig {} noscan".format(useHCI)
			U.logger.log(20,cmd) 
			subprocess.call(cmd,shell=True,stdout=subprocess.PIPE)
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
			

			if 	rpiDataAcquistionMethod == "hcidump":
				cmd	 = "sudo hciconfig {} leadv 3".format(useHCI)
				U.logger.log(20,cmd) 
				ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE).communicate()
				U.logger.log(20,"ret:{}".format(ret) )
				time.sleep(0.2)
				

			if	True:
				# setup broadcast message
				OGF					= " 0x08"
				OCF					= " 0x0008"
				iBeaconPrefix		= " 1E 02 01 1A 1A FF 4C 00 02 15"
				uuid				= " 2f 23 44 54 cf 6d 4a 0f ad f2 f4 91 1b a9 ff a6"
				MAJ					= " 78 90"
				MIN					= " 00 "+"0%x"%(int(pi))
				txP					= " C5 00"
				#cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + OCF + iBeaconPrefix + uuid + MAJ + MIN + txP
				cmd	 = "hcitool -i {} cmd{}{}{}{}{}{}{} &".format(useHCI, OGF, OCF, iBeaconPrefix, uuid, MAJ, MIN, txP)
				U.logger.log(20,cmd) 
				subprocess.call(cmd,shell=True,stdout=subprocess.PIPE)
				time.sleep(0.2)


			if 	rpiDataAcquistionMethod == "hcidump":
				restartLESCAN(useHCI)



			if	rpiDataAcquistionMethod == "socket":
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

	if rpiDataAcquistionMethod == "hcidump":
		return "", myBLEmac, 0, useHCI


	if rpiDataAcquistionMethod == "socket":
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
def restartLESCAN(useHCI):
	global rpiDataAcquistionMethod
	global lastLESCANrestart
	try:
		if rpiDataAcquistionMethod != "hcidump": return 
		if time.time() - lastLESCANrestart  > 500:
			lastLESCANrestart = time.time()
			U.killOldPgm(-1,"lescan") # will kill the launching sudo parent process, lescan still running
			#cmd = "sudo hciconfig {} reset".format(useHCI)
			#U.logger.log(20,cmd) 
			#ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE).communicate()
			cmd	 = "sudo hcitool -i {} lescan --duplicates  > /dev/null 2>&1 &".format(useHCI,G.homeDir)
			U.logger.log(20,cmd) 
			ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE).communicate()
			U.logger.log(20,"ret:{}".format(ret) )
			time.sleep(0.2)
			U.killOldPgm(-1,"sudo hcitool") # will kill the launching sudo parent process, lescan still running
	except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return
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


#################################
def downHCI(useHCI):
	try:
		subprocess.Popen("sudo hciconfig {} down &".format(useHCI),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE) # enable bluetooth
		time.sleep(0.2)
		subprocess.Popen("sudo service bluetooth restart &",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(0.2)
		subprocess.Popen("sudo service dbus restart &",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(0.2)
	except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return



#################################
def startHCUIDUMPlistener(hci):
	global myBLEmac
	global ListenProcessFileHandle
	try:
		cmd = "sudo hcidump -i {} --raw".format(hci)
		U.logger.log(20,"startHCUIDUMPlistener: cmd {}".format(cmd))
		ListenProcessFileHandle = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		##pid = ListenProcessFileHandle.pid
		##self.myLog( text=u" pid= " + unicode(pid) )
		msg = unicode(ListenProcessFileHandle.stderr)
		if msg.find("open file") == -1:	# try this again
			self.indiLOG.log(40,"uType {}; IP#: {}; error connecting {}".formaat(uType, ipNumber, msg) )
			self.sleep(20)
			return  "error "+ unicode(msg)
		U.killOldPgm(-1,"sudo hcidump")

		# set the O_NONBLOCK flag of ListenProcessFileHandle.stdout file descriptor:
		flags = fcntl.fcntl(ListenProcessFileHandle.stdout, fcntl.F_GETFL)  # get current p.stdout flags
		fcntl.fcntl(ListenProcessFileHandle.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
		time.sleep(0.1)
		return  ""
	except	Exception, e:
		U.logger.log(20,"startConnect: in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return "", "error "+ unicode(e)
		self.indiLOG.log(40,"startConnect timeout, not able to  connect after 20 tries ")
		return "","error connecting"
	except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return  "error"

#################################
def stopHCUIDUMPlistener():
	global ListenProcessFileHandle
	try:
		U.killOldPgm(-1,"hcidump")
		U.killOldPgm(-1,"hcitool")
		if ListenProcessFileHandle != "":
			ListenProcessFileHandle.terminate()
	except	Exception, e:
		U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


#################################
def readHCUIDUMPlistener():
	global readBufferSize, ListenProcessFileHandle
	try:
		lines = os.read(ListenProcessFileHandle.stdout.fileno(),readBufferSize) 
		if len(lines) == 0: return []
		messages = combineLines(lines)
		#U.logger.log(20, u"readHCUIDUMPlistener lines:\n{},\nmessages\n{}".format(lines, messages))
		return messages
	except	Exception, e:
		if unicode(e).find("[Errno 35]") > -1:	 # "Errno 35" is the normal response if no data, if other error stop and restart
			pass
			#U.logger.log(20, u"Errno 35")
		if unicode(e).find("[Errno 1]") > -1:	 # "Errno 35" is the normal response if no data, if other error stop and restart
			pass
			#U.logger.log(20, u"Errno 11")
		if unicode(e).find("temporarily") > -1:	 # "Errno 35" is the normal response if no data, if other error stop and restart
			pass
			#U.logger.log(20, u"Errno 11")
		else:
			if unicode(e) != "None":
				out = "os.read(ListenProcessFileHandle.stdout.fileno(),{})  in Line {} has error={}".format(readBufferSize, sys.exc_traceback.tb_lineno, e)
				try: out+= "fileNo: {}".format(ListenProcessFileHandle.stdout.fileno() )
				except: pass
				if unicode(e).find("[Errno 22]") > -1:  # "Errno 22" is  general read error "wrong parameter"
					out+= " ..      try lowering read buffer parameter in config" 
					U.logger.log(20,out)
				else:
					U.logger.log(20,out)
		time.sleep(0.5)
		return ""

	except	Exception, e:
		U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return ""
#################################
def combineLines(lines):
	global readbuffer
	"""
> 04 3E 1A 02 01 00 00 78 D6 0F FB 22 3C 0E 02 01 06 0A FF 4C 
  00 10 05 0B 18 C0 60 71 D5 
> 04 3E 2B 02 01 03 01 6A 9C 49 17 D4 E8 1F 02 01 06 1B FF 4C 
  00 02 15 EB EF D0 83 70 A2 47 C8 98 37 E7 B5 63 4D F5 24 00 
  03 00 04 FF 59 B4 
0123456789112345678921234567893123456789412345678951234567896
000215EBEFD08370A247C89837E7B5634DF52400 

	"""
	try:
		MSGs=[]
		msg = ""
		countLinesPerMsg = 1
		for line in lines.split("\n"):
			if line.find("-") >-1: continue
			if line.find(".") >-1: continue
			if line.find(",") >-1: continue
			if line.find(":") >-1: continue
			if line.find("<") >-1: continue
			readbuffer += line.replace(" ","")

		rd = readbuffer.split(">")
		ll = len(rd)
		nn = 0
		for line in rd:
			nn +=1
			if len(line) < 40 and nn < ll: continue
			MSGs.append(line[14:])
		if len(MSGs) ==0: return []

		if len(MSGs[-1]) < 40:
			readbuffer = MSGs[-1]
			#U.logger.log(20, u"readHCUIDUMPlistener leftover>{}<, >{}<".format(readbuffer,MSGs[-1] ))
			del MSGs[-1]
			
		return MSGs	
	except	Exception, e:
		U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return []

	
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
	global collectMsgs, sendAfterSeconds, loopMaxCallBLE, ignoreUUID,UUIDtoIphoneReverse, beacon_ExistingHistory, deleteHistoryAfterSeconds,ignoreMAC,signalDelta,UUIDtoIphone,offsetUUID,fastDownMinSignal,maxParseSec,batteryLevelPosition,doNotIgnore
	global acceptNewiBeacons, acceptNewTagiBeacons,onlyTheseMAC,enableiBeacons, sendFullUUID,BLEsensorMACs, minSignalCutoff, acceptJunkBeacons,knownBeaconTags
	global oldRaw, lastRead
	global rpiDataAcquistionMethod
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
				stopHCUIDUMPlistener()
				sys.exit(3)
			U.getGlobalParams(inp)

			if "rebootSeconds"			in inp:	 rebootSeconds=		  int(inp["rebootSeconds"])
			if "sendAfterSeconds"		in inp:	 sendAfterSeconds=	  int(inp["sendAfterSeconds"])
			if "acceptNewiBeacons"		in inp:	 acceptNewiBeacons=	  int(inp["acceptNewiBeacons"])
			if "acceptNewTagiBeacons"	in inp:	 acceptNewTagiBeacons=	 (inp["acceptNewTagiBeacons"])
			if "sendFullUUID"			in inp:	 sendFullUUID=			 (inp["sendFullUUID"]=="1" )
			if "acceptJunkBeacons"		in inp:	 acceptJunkBeacons=		 (inp["acceptJunkBeacons"]=="1" )

			if "rpiDataAcquistionMethod"				in inp:	 
				xx =		 	 										(inp["rpiDataAcquistionMethod"])
				if xx != rpiDataAcquistionMethod and rpiDataAcquistionMethod != "":
					U.restartMyself(param="", reason="new data aquisition method")
				rpiDataAcquistionMethod = xx
			else:
				rpiDataAcquistionMethod = "socket"


			if "deleteHistoryAfterSeconds"	in inp:
									  deleteHistoryAfterSeconds=  int(inp["deleteHistoryAfterSeconds"])
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
		
	try:		fastDownMinSignal=InParams["fastDownMinSignal"]
	except:		fastDownMinSignal={}

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


		
	U.logger.log(0,"fastDownMinSignal:  {}".format(fastDownMinSignal))
	U.logger.log(0,"signalDelta:        {}".format(signalDelta))
	U.logger.log(0,"ignoreUUID:          {}".format(ignoreUUID))
	U.logger.log(0,"ignoreMAC:           {}".format(ignoreMAC))
	U.logger.log(0,"UUIDtoIphone:        {}".format(UUIDtoIphone))
	U.logger.log(0,"UUIDtoIphoneReverse: {}".format(UUIDtoIphoneReverse))
	return


		
	
#################################
def composeMSG(timeAtLoopStart):
	global	 collectMsgs, sendAfterSeconds, loopMaxCallBLE,	 ignoreUUID,  beacon_ExistingHistory, deleteHistoryAfterSeconds
	global myBLEmac, sendFullUUID,  mapReasonToText, downCount, beaconsOnline
	global beaconsNew
	global reasonMax
	try:
		if myBLEmac == "00:00:00:00:00:00":
			time.sleep(2)
			U.restartMyself(param="", reason="bad BLE  =00..00")

		data = []
		for beaconMAC in beaconsNew:
			if beaconMAC not in beacon_ExistingHistory: continue
			try:
				testIphone, mac =checkIfIphone(beaconsNew[beaconMAC]["uuid"],beaconMAC)
				if sendFullUUID or beacon_ExistingHistory[beaconMAC]["lCount"] ==0 or beacon_ExistingHistory[beaconMAC]["lCount"] ==5 or beacon_ExistingHistory[beaconMAC]["reason"] ==2 or testIphone:
					uuid = beaconsNew[beaconMAC]["uuid"]
					if sendFullUUID:
						beacon_ExistingHistory[beaconMAC]["lCount"]=0
					else:
						beacon_ExistingHistory[beaconMAC]["lCount"]=10
				else:
					uuid = "x-x-x"
				if beaconsNew[beaconMAC]["count"] !=0 :
					avePower	=float("%5.0f"%(beaconsNew[beaconMAC]["txPower"]	/beaconsNew[beaconMAC]["count"]))
					aveSignal	=float("%5.1f"%(beaconsNew[beaconMAC]["rssi"]		/beaconsNew[beaconMAC]["count"]))
					if avePower > -200:
						beaconsOnline[beaconMAC] = int(time.time())
					r  = min(6,max(0,beacon_ExistingHistory[beaconMAC]["reason"]))
					rr = mapReasonToText[r]
					newData = {"mac": beaconMAC,
						"reason": rr, 
						"uuid": uuid, 
						"rssi": aveSignal, 
						"txPower": avePower, 
						"count": beaconsNew[beaconMAC]["count"],
						"batteryLevel": beaconsNew[beaconMAC]["bLevel"],
						"pktInfo": beaconsNew[beaconMAC]["pktInfo"]}
					downCount = 0
					data.append(newData)
					beacon_ExistingHistory[beaconMAC]["rssi"]  = beaconsNew[beaconMAC]["rssi"]/max(beaconsNew[beaconMAC]["count"],1.) # average last rssi
					beacon_ExistingHistory[beaconMAC]["count"] = beaconsNew[beaconMAC]["count"] 
					beacon_ExistingHistory[beaconMAC]["timeSt"] = time.time()
			except	Exception, e:
				U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				U.logger.log(30, " error composing mac:{}, beaconsNew \n{}".format(beaconMAC, beaconsNew[beaconMAC]))

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
def checkIfNewOrDeltaSignalOrWasMissing(beaconMAC, beaconMSG):
	global collectMsgs, sendAfterSeconds, loopMaxCallBLE, ignoreUUID, beacon_ExistingHistory, deleteHistoryAfterSeconds,signalDelta,fastDownMinSignal, minSignalCutoff
	global onlyTheseMAC, beaconsNew
 	global reasonMax

	t=time.time()
	rssi = float(beaconMSG[2])
	try:
		if beaconMAC not in beacon_ExistingHistory: # is it new?
			if beaconMAC in minSignalCutoff:
				if	rssi < minSignalCutoff[beaconMAC]:
					#print "rejecting: ", beaconMAC, minSignalCutoff[beaconMAC] ,  float(beaconMSG[2])
					return
				else:
					#print "accepting: ", beaconMAC, minSignalCutoff[beaconMAC] ,  float(beaconMSG[2])
					pass
			if beaconMAC not in onlyTheseMAC:
				reasonMax = max(reasonMax, 2)
			else:
				reasonMax = max(reasonMax, 5)

			beacon_ExistingHistory[beaconMAC]={"uuid":beaconMSG[1],"lCount":1,"txPower":float(beaconMSG[3]),"rssi":rssi,"reason":reasonMax ,"timeSt":t,"count":beaconsNew[beaconMAC]["dCount"]}
			
		# no up if signal weak  
		elif beaconMAC in minSignalCutoff and rssi < minSignalCutoff[beaconMAC]:# 
			return

		elif beacon_ExistingHistory[beaconMAC]["rssi"] == -999: # in fast down mode, was down for some time
			reasonMax = max(reasonMax, 4)
			beacon_ExistingHistory[beaconMAC]={"uuid":beaconMSG[1],"lCount":1,"txPower":float(beaconMSG[3]),"rssi":rssi,"reason":reasonMax ,"timeSt":t,"count":beaconsNew[beaconMAC]["dCount"]}
 
		elif (t - beacon_ExistingHistory[beaconMAC]["timeSt"])	> 1.3*sendAfterSeconds: # not new but have not heard for > 1+1/3 periods
			reasonMax = max(reasonMax, 5)
			beacon_ExistingHistory[beaconMAC]["reason"] = reasonMax 
			#print	"curl: first msg after	collect time "+ beaconMAC +" "+unicode(beacon_ExistingHistory[beaconMAC])

		elif beaconMAC in signalDelta: 
			if beacon_ExistingHistory[beaconMAC]["rssi"] != -999. and rssi != 0:
				if abs(beacon_ExistingHistory[beaconMAC]["rssi"]-rssi) >  signalDelta[beaconMAC] :	# delta signal > xxdBm (set param)
					if beaconsNew[beaconMAC]["dCount"] > 0:
						#print beaconMAC, "signalDelta",beacon_ExistingHistory[beaconMAC]["rssi"], float(beaconMSG[2]), signalDelta[beaconMAC] 
						reasonMax = max(reasonMax, 6)
						beacon_ExistingHistory[beaconMAC]["reason"] = reasonMax 
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
		U.logger.log(30,u"beaconMAC:{}\nbeaconMSG:{}\nbeaconsNew:{}".format(beaconMAC, beaconMSG,beaconsNew ))

	return


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
def checkIfFastDown():
	global fastDownMinSignal, beacon_ExistingHistory, trackMac, logCountTrackMac
	global beaconsNew
	global reasonMax 

	try:
	## ----------  check if this is a fast down device
		tt= time.time()
		for beacon in fastDownMinSignal:
			if beacon not in beacon_ExistingHistory: continue # not in history never had an UP signal is already gone

			if beacon in beaconsNew:
				if tt - beaconsNew[beacon]["timeSt"] < fastDownMinSignal[beacon]["seconds"]: 
					beacon_ExistingHistory[beacon]["rssi"]		= beaconsNew[beacon]["rssi"]
					beacon_ExistingHistory[beacon]["timeSt"]	= beaconsNew[beacon]["timeSt"]
					beacon_ExistingHistory[beacon]["txPower"]	= beaconsNew[beacon]["txPower"]
					beacon_ExistingHistory[beacon]["uuid"]		= beaconsNew[beacon]["uuid"]
					beacon_ExistingHistory[beacon]["count"]		= beaconsNew[beacon]["count"]
					continue 

				if tt- beacon_ExistingHistory[beacon]["timeSt"] <	fastDownMinSignal[beacon]["seconds"]: continue		#  shorter trigger
			elif   tt- beacon_ExistingHistory[beacon]["timeSt"] <	fastDownMinSignal[beacon]["seconds"]: continue		#  have not received anything this period, give it a bit more time

			if beacon_ExistingHistory[beacon]["rssi"] == -999: continue # already fast down send

			if  (beacon == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac( "FstDA ", "set to fastDown Active " ,beacon)
				 
			reasonMax = max(reasonMax, 3)
			beacon_ExistingHistory[beacon]["timeSt"] = tt
			beacon_ExistingHistory[beacon]["rssi"]	 = -999
			beacon_ExistingHistory[beacon]["reason"] = reasonMax 
			beaconsNew[beacon] = {
				"uuid" : beacon_ExistingHistory[beacon]["uuid"],
				"txPower": beacon_ExistingHistory[beacon]["txPower"],
				"rssi": -999,
				"timeSt" :tt,
				"bLevel": "",
				"pktInfo": "",
				"dCount": 0,
				"count": 1}
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return

#################################, check if signal strength is acceptable for fastdown 
def checkIfFastDownMinSignal(beaconMAC, rssi ):
	global fastDownMinSignal, trackMac, logCountTrackMac
	global reasonMax 
	try:
		if  (beaconMAC == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac( "FstD6 ", "checking if in min Signal fastDown " ,beaconMAC)
		if beaconMAC in fastDownMinSignal:
			if "fastDownMinSignal" in fastDownMinSignal[beaconMAC]:
				if  (beaconMAC == trackMac or trackMac =="*") and logCountTrackMac >0:
					writeTrackMac( "FstD7 ", "checking actual Signal " ,beaconMAC)
				if rssi < fastDownMinSignal[beaconMAC]["fastDownMinSignal"]: 
					if  (beaconMAC == trackMac or trackMac == "*") and logCountTrackMac >0:
						writeTrackMac( "FstD8 ", ", setting active " ,beaconMAC)
					reasonMax = max(3, reasonMax )
					return 
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 
		
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
def doSensors( mac, rx, tx, nCharThisMessage, hexData, UUID, Maj, Min):
	global BLEsensorMACs
	bl = ""
	try:

		if mac in BLEsensorMACs and BLEsensorMACs[mac]["type"] == "myBLUEt":  								
			return domyBlueT( mac, rx, tx, nCharThisMessage, hexData, UUID, Maj, Min)

		## check if Ruuvi tag present at right position, should be at pos 22
		ruuviTagPos 	= hexData.find("FF990405") 
		ruuviTagFound	= ruuviTagPos > 20 and ruuviTagPos < 24 # give range just in case
		ruuviSensorActive = ( mac in BLEsensorMACs  and BLEsensorMACs[mac]["type"] == "RuuviTag")
		#if mac == "ED:1B:05:6E:CA:59":
		#	U.logger.log(30,u"ruuvitag -1 mac:{};  pos={}; ruuviSensorActive:{}, hexData:{}".format(mac, ruuviTagPos, ruuviSensorActive, hexData))
		if ruuviTagFound or ruuviSensorActive: 
			return  doRuuviTag( mac, rx, tx, nCharThisMessage, hexData, ruuviTagPos, ruuviSensorActive, UUID, Maj, Min)

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return tx, bl, UUID, Maj, Min, False

#################################
def domyBlueT( mac, rx, tx, nCharThisMessage, hexData, UUID, Maj, Min):
	global BLEsensorMACs
	try:
		if nCharThisMessage < 55:
			return tx, "", UUID, Maj, Min, True
		RawData = hexData[48:48+6] # get bytes # 31,32,33	 (starts at # 0 , #33 has sign, if !=0 subtract 2**15
		RawData = [int(RawData[0],16), int(RawData[1],16), int(RawData[2],16)]
		#RawData = list(struct.unpack("BBB", pkt[31:34])) # get bytes # 31,32,33	 (starts at # 0 , #33 has sign, if !=0 subtract 2**15
		if RawData[2] != 0: tSign = 0x10000 # == 65536 == 2<<15
		else:				tSign = 0
		r8				= RawData[1] << 8 
		sensorData		= ( r8 + RawData[0] - tSign ) /100.
		sensor			= "BLEsensor"
		devId			= BLEsensorMACs[mac]["devId"]
		try:	temp  	= (sensorData + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
		except: temp  	= sensorData
		U.logger.log(10, "{}   RX:{}; TX:{}; temp:{}; nBytes:{}".format(mac, rx, tx, temp, nCharThisMessage) )
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
def doRuuviTag( mac, rx, tx, nCharThisMessage,hexData, ruuviTagPos, ruuviSensorActive, UUID, Maj, Min):
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
		battreyLowVsTemp		= (1. + min(0,temp-10)/100.) * 2900 # (changes to 0.9* 2900 @ 0C; to = 0.8*2900 @-10C )
		batteryLevel 			= int(min(100,max(0,100* (batteryVoltage - battreyLowVsTemp)/(3100.-battreyLowVsTemp))))
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



#################################
def checkIFtrackMacIsRequested():
	global logCountTrackMac, trackMac, nLogMgsTrackMac, startTimeTrackMac, trackMacText
	try:
		if not os.path.isfile(G.homeDir+"temp/beaconloop.trackmac"): return False
		f = open(G.homeDir+"temp/beaconloop.trackmac","r")
		trackMac = f.read().strip("\n")
		f.close()
		trackMacText = ""
		writeTrackMac("","\nTRACKMAC started on pi#:"+str(G.myPiNumber)+", for MAC# ", trackMac+"\n")
		startTimeTrackMac = time.time()
		subprocess.call("rm {}temp/beaconloop.trackmac".format(G.homeDir), shell=True)
		subprocess.call("rm {}temp/trackmac.log".format(G.homeDir), shell=True)
		logCountTrackMac = nLogMgsTrackMac
		if trackMac =="*": logCountTrackMac *=3
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

#################################
def writeTrackMac(textOut0, textOut2, mac):
	global logCountTrackMac, trackMac, nLogMgsTrackMac, trackMacText
	try:
		f = open(G.homeDir+"temp/trackmac.log","a")
		if textOut0 == "":
			f.write(textOut2+"\n")
		else:
			f.write(textOut0+mac+", "+textOut2+"\n")
		f.close()
		print textOut0+mac+", "+textOut2
		U.logger.log(20,textOut0+mac+", "+textOut2)
		trackMacText += textOut0+mac+" "+textOut2+";;"
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


#################################
def BLEAnalysis(hci):
	global onlyTheseMAC, knownBeaconTags
	try:
		if not os.path.isfile(G.homeDir+"temp/beaconloop.BLEAnalysis"): return False

		dataCollectionTime = 22 # secs 


		f = open(G.homeDir+"temp/beaconloop.BLEAnalysis","r")
		rssiCutoff = f.read().strip("\n")
		f.close()
		subprocess.call("rm {}temp/beaconloop.BLEAnalysis".format(G.homeDir), shell=True)
		rssiCutoff = int(rssiCutoff)



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

		stopHCUIDUMPlistener()
		U.killOldPgm(-1,"hcidump")
		U.killOldPgm(-1,"hcitool")
		U.killOldPgm(-1,"lescan")

		## now listen to BLE
		starttime = time.time()
		U.logger.log(20, u"starting  BLEAnalysis, rssi cutoff= {}[dBm]".format(rssiCutoff))
		U.logger.log(20, u"sudo hciconfig {} reset".format(hci))
		subprocess.Popen("sudo hciconfig "+hci+" reset",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20, "sudo timeout -s SIGINT "+str(dataCollectionTime)+"s hcitool -i "+hci+" lescan")
		subprocess.Popen("sudo timeout -s SIGINT "+str(dataCollectionTime)+"s hcitool -i "+hci+" lescan --duplicates > "+G.homeDir+"temp/lescan.data &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
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
					max_TX 	= max(MACs[mac]["max_TX"],   signedIntfromString(line[-5:-3]))
					rssi 	= max(MACs[mac]["max_rssi"], signedIntfromString(line[-2:]))
					
					#rssi 	= max(MACs[mac]["max_rssi"],  int("%i"%struct.unpack('b', line[-2:].decode('hex'))) )
					#max_TX 	= MACs[mac]["max_TX"] = max(MACs[mac]["max_TX"],  int("%i"%struct.unpack('b', line[-5:-3].decode('hex'))) )
				except: continue
				for ll in MACs[mac]["raw_data"]:
					#print mac, "test   :>{}<".format(ll[0:-3])
					if line[:-6].strip() in ll:# w/o RX TX
						present = True
						#print mac, "test   : duplicate"
						break
				if not present:
					#U.logger.log(20, "adding:>>{}<< ".format(line[:-3])) 
					MACs[mac]["raw_data"].append( line )
					linesDevices +=1
				
				MACs[mac]["MSG_in_10Secs"] +=1
				MACs[mac]["max_rssi"] 		= rssi
				MACs[mac]["max_TX"] 		= max_TX
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
					hexStr = msg.replace(" ","")[14:] # this starts w MAC # no spaces
					macPos = hexStr[12:].find(mac.replace(":","")) #check if mac # present afetr mac #
					RmacPos = hexStr[12:].find(hexStr[0:12])	  # check if reverse mac# repsent after mac 
					#U.logger.log(20, "hexstr: {} ".format(hexStr)) 
					knownMACS[mac]["n_of_MSG_Types"] = nmsg
					knownMACS[mac]["possible_knownTag_options"].append('"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","prio": 1, "pos": 12,"posDelta": 0,"tag":"'+hexStr[12:-3]+'"}')
					knownMACS[mac]["beaconType"].append("")
					knownMACS[mac]["beaconType-msg#"].append(nmsg)
					knownMACS[mac]["pos_of_MAC_in_UUID"].append(macPos)
					knownMACS[mac]["pos_of_reverse_MAC_in_UUID"].append(RmacPos)
					knownMACS[mac]["n_of_MSG_Types"] = nmsg
					for tag in knownBeaconTags:
						#U.logger.log(20, "tag: {} ".format(tag)) 
						posFound, dPostest = testComplexTag(hexStr[12:-2], tag, mac, mac.replace(":",""), hexStr[0:12])
						if posFound != -1:
							knownMACS[mac]["beaconType"][-1] = tag
							knownMACS[mac]["beaconType-msg#"][-1] = nmsg
							knownMACS[mac]["possible_knownTag_options"][-1]= " use: "+tag

							
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
					newMACs[mac]["possible_knownTag_options"].append('"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","prio": 1, "pos": 12,"posDelta": 0,"tag":"'+hexStr[12:-3]+'"}')
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
						posFound, dPostest = testComplexTag(hexStr[12:-2], tag, mac, mac.replace(":",""), hexStr[0:12])
						if posFound != -1:
							newMACs[mac]["beaconType"][-1] = tag
							newMACs[mac]["beaconType-msg#"][-1] = nmsg
							newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","prio": 1, "pos": '+str(posFound)+',"posDelta": 0,"tag":"'+hexStr[12:-3]+'"}'
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


def beep(useHCI):
	global beaconsOnline
	try:	
		if not os.path.isfile(G.homeDir+"temp/beaconloop.beep"): return False
		#U.logger.log(20,"beepBeacon ")

		f = open(G.homeDir+"temp/beaconloop.beep","r")
		devices = f.read().strip("\n")
		f.close()

		subprocess.call("rm {}temp/beaconloop.beep".format(G.homeDir), shell=True)

		# devices: '{u'24:DA:11:21:2B:20': {u'cmdOff': u'char-write-cmd 0x0011 00', u'cmdON': u'char-write-cmd  0x0011  02', u'beepTime': 2.0}}'
		devices = json.loads(devices)
		if len(devices) == 0: return False
		expCommands = ""
		stopHCUIDUMPlistener()
		U.killOldPgm(-1,"hcidump")
		U.killOldPgm(-1,"hcitool")
		U.killOldPgm(-1,"lescan")
		ret = subprocess.Popen("sudo /bin/hciconfig {} reset".format(useHCI),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		U.logger.log(20,"beepBeacon devices:{}".format(devices))
		for mac in devices:
			#U.logger.log(20,"beepBeacon mac:{}".format(mac))
			if len(mac) < 10: continue
			params		= devices[mac]
			
			tryAgain = 3
			for kk in range(3):
				tryAgain -= 1
				if tryAgain < 0: break
				if tryAgain != 2:
					try: expCommands.sendline("disconnect")	
					except: pass	

				if "random" in params and params["random"] == "randomON":	random = " -t random"
				else:					 									random = " "
				cmd = "sudo /usr/bin/gatttool -i {} {} -b {} -I".format(useHCI, random, mac) 
				U.logger.log(20,cmd)
				expCommands = pexpect.spawn(cmd)
				ret = expCommands.expect([">","error",pexpect.TIMEOUT], timeout=10)
				if ret == 0:
					U.logger.log(20,"... successful: {}-{}".format(expCommands.before,expCommands.after))
					connected = True
				elif ret == 1:
					if ii < ntriesConnect-1: 
						U.logger.log(20, u"... error, giving up: {}-{}".format(expCommands.before,expCommands.after))
						time.sleep(1)
						break
				elif ret == 2:
					if ii < ntriesConnect-1: 
						U.logger.log(20, u"... timeout, giving up: {}-{}".format(expCommands.before,expCommands.after))
						time.sleep(1)
						break
				else:
					if ii < ntriesConnect-1: 
						U.logger.log(20,"... unexpected, giving up: {}-{}".format(expCommands.before,expCommands.after))
						time.sleep(1)
						break

				time.sleep(0.1)

				if "mustBeUp" in params and params["mustBeUp"]: force = False
				else:											force = True
				if  not force and mac not in beaconsOnline:
					U.logger.log(20,"mac: {}; skipping, not online or not in range".format(mac) )
					continue
				try:
					cmdON		= params["cmdON"]
					cmdOff		= params["cmdOff"]
					beepTime	= float(params["beepTime"])
					U.logger.log(20,"{}:   cmdON:{};  cmdOff:{};  beepTime:{} ".format(mac, cmdON, cmdOff, beepTime) )

					connected = False
					ntriesConnect = 6
					for ii in range(ntriesConnect):
						try:
							U.logger.log(20,"expect connect ")
							expCommands.sendline("connect ")
							ret = expCommands.expect(["Connection successful","Error", pexpect.TIMEOUT], timeout=15)
							if ret == 0:
								U.logger.log(20,"... successful: {}".format(expCommands.after))
								connected = True
								break
							elif ret == 1:
								if ii < ntriesConnect-1: 
									U.logger.log(20, u"... error, try again: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(1)
							elif ret == 2:
								if ii < ntriesConnect-1: 
									U.logger.log(20, u"... timeout, try again: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(1)
							else:
								if ii < ntriesConnect-1: 
									U.logger.log(20,"... unexpected, try again: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(1)

						except Exception, e:
							U.logger.log(20, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							if ii < ntriesConnect-1: 
								U.logger.log(20, u"... error, try again")
								time.sleep(1)

					if not connected:
						U.logger.log(20, u"connect error, giving up")
						tryAgain = True
					
					else:
						startbeep = time.time()
						lastBeep = 0
						success = True
						for ii in range(50):
							if time.time() - lastBeep > 10:
								for cc in cmdON:
									U.logger.log(20,"sendline  cmd{}".format( cc))
									expCommands.sendline( cc )
									ret = expCommands.expect([mac,"Error","failed",pexpect.TIMEOUT], timeout=5)
									if ret == 0:
										U.logger.log(20,"... successful: {}-{}".format(expCommands.before,expCommands.after))
										time.sleep(0.1)
										continue
									elif ret in[1,2]:
										if ii < ntriesConnect-1: 
											U.logger.log(20, u"... error, quit: {}-{}".format(expCommands.before,expCommands.after))
										success = False
										break
									elif ret == 3:
										U.logger.log(20,"... timeout, quit: {}-{}".format(expCommands.before,expCommands.after))
										success = False
										break
									else:
										U.logger.log(20,"... unexpected, quit: {}-{}".format(expCommands.before,expCommands.after))
										success = False
										break
								lastBeep = time.time()
							if time.time() - startbeep > beepTime: break
							time.sleep(1)

						if success:
							for cc in cmdOff:
								U.logger.log(20,"sendline  cmd{}".format( cc))
								expCommands.sendline( cc )
								ret = expCommands.expect([mac,"Error","failed",pexpect.TIMEOUT], timeout=5)
								if ret == 0:
									U.logger.log(20,"... successful: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(0.1)
								elif ret in[1,2]:
									U.logger.log(20,"... error: {}-{}".format(expCommands.before,expCommands.after))
								elif ret == 3:
									U.logger.log(20,"... timeout: {}-{}".format(expCommands.before,expCommands.after))
								else:
									U.logger.log(20,"... unknown: {}-{}".format(expCommands.before,expCommands.after))
								tryAgain = -1

						expCommands.sendline("disconnect" )
						U.logger.log(20,"sendline disconnect ")
						ret = expCommands.expect([">","Error",pexpect.TIMEOUT], timeout=5)
						if ret == 0:
							U.logger.log(20,"... successful: {}".format(expCommands.after))
						elif ret == 1:
							U.logger.log(20,"... error: {}".format(expCommands.after))
						elif ret == 2:
							U.logger.log(20,"... timeout: {}".format(expCommands.after))
						else: 
							U.logger.log(20,"... unknown: {}".format(expCommands.after))


				except Exception, e:
					U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					time.sleep(1)
			#U.logger.log(20,"beepBeacon end of mac:{}".format(mac))
			if expCommands !="":
				try:	expCommands.sendline("quit\r" )
				except: pass

		if expCommands !="":
			expCommands.close()		
	except Exception, e:
			U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return True




def getBeaconParameters(useHCI):
	global beaconsOnline

	data ={} 
	try:	
		if not os.path.isfile(G.homeDir+"temp/beaconloop.getBeaconParameters"): return False
		#U.logger.log(20,"beepBeacon ")

		f = open(G.homeDir+"temp/beaconloop.getBeaconParameters","r")
		devices = f.read().strip("\n")
		f.close()

		subprocess.call("rm {}temp/beaconloop.getBeaconParameters".format(G.homeDir), shell=True)

		# devices: '{u'24:DA:11:21:2B:20': {u'cmdOff': u'char-write-cmd 0x0011 00', u'cmdON': u'char-write-cmd  0x0011  02', u'beepTime': 2.0}}'
		devices = json.loads(devices)
		U.logger.log(20,"getBeaconParameters devices:{}".format(devices))
		if len(devices) ==0: return False

		U.killOldPgm(-1,"hcidump")
		U.killOldPgm(-1,"hcitool")
		U.killOldPgm(-1,"lescan")

		cmd = "sudo /bin/hciconfig hci0 down;sudo /bin/hciconfig hci0 up"
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

 		timeoutSecs = 15
		for mac in devices:
			if len(mac) < 10: continue
			if False and mac not in beaconsOnline:
				U.logger.log(20,"mac: {}; skipping, not online or not in range".format(mac) )
				continue
			try:
				params		= devices[mac]["battCmd"]
				U.logger.log(20,"params:{}".format(params))
				if type(params) != type({}): continue

				if params["random"] == "randomON":	random = " -t random "
				else:				    			random = " "
				uuid   = params["uuid"]
				bits   = params["bits"]
				shift  = params["shift"]
				norm   = params["norm"]
				offset = params["offset"]
#					devices:{u'24:DA:11:21:2B:20': {u'battCmd': {u'random': u'public', u'bits': 63, u'uuid': u'2A19', u'norm': 36}}}

				cmd = "/usr/bin/timeout -s SIGKILL {}   /usr/bin/gatttool -b {} {} --char-read --uuid={}".format(timeoutSecs, mac,random, uuid)
				##					                   /usr/bin/gatttool -b 24:da:11:27:E4:23 --char-read --uuid=2A19 -t public / random   
				U.logger.log(20,"cmd: {}".format(cmd) )
				ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				check = (ret[0]+" -- "+ret[1]).lower().strip("\n").replace("\n"," -- ").strip()
				valueF = 0; valueI = 0; valueB = ""; valueC = 0; valueD = 0
				if check.find("connect error") >-1:	valueF = check
				elif check.find("killed") >-1:		valueF = "timeout"
				elif check.find("error") >-1: 		valueF = check
				else: 
					valueF = -2
					ret2 = ret[0].split("value: ")
					if len(ret2) == 2:  
						try:
							valueI = int(ret2[1].strip(),16) 
							valueB = valueI & bits 
							valueC = valueB
							if   shift > 0: valueC *= shift 
							elif shift < 0:	valueC /= -shift
							valueD = max(0,valueC + offset)
							valueF = min(100, int( ( valueD *100. )/norm ))
						except Exception, e:
							U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				U.logger.log(20,"... ret: {}; bits: {}; norm:{}; value-I: {}; B: {}; C: {}; d: {};  F: {} ".format(check, bits, norm, valueI, valueB, valueC, valueD, valueF) )
				if "sensors" not in data: data["sensors"] = {}
				if "getBeaconParameters" not in data["sensors"]: data["sensors"]["getBeaconParameters"] ={}
				if mac not in data["sensors"]["getBeaconParameters"]: data["sensors"]["getBeaconParameters"][mac] ={}
				data["sensors"]["getBeaconParameters"][mac] = {"batteryLevel":valueF}
			except Exception, e:
				if unicode(e).find("Timeout") == -1:
					U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				else:
					U.logger.log(20, u"Line {} has timeout".format(sys.exc_traceback.tb_lineno))
				time.sleep(1)

			
	except Exception, e:
			U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	if data != {}:
		U.sendURL(data, wait=True, squeeze=False)
		time.sleep(0.5)

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

		if tagString.find("-") >-1: # 
			tagString = tagString[:-1]
			lTag = len(tagString)
		else: 
			lTag = 100
		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-0 ","tag:"+tag+"; tagString: "+tagString+";  lTag:"+str(lTag), mac)

		if tagString.find("X") >-1:
			indexes = [n for n, v in enumerate(tagString) if v == 'X'] 
			testString 	= list(testString.upper())
			for ii in indexes:
				if ii+tagPos < len(testString):
					testString[ii+tagPos] = "X"
				else: return -1, 100

			testString = ("").join(testString)
		if tagString.find("RMAC########") >-1:
			tagString = tagString.replace("RMAC########", macplainReverse)

		elif tagString.find("MAC#########") >-1:
			tagString = tagString.replace("MAC#########", macplain)

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-1 ","tagString Fin: "+tagString, mac)
			writeTrackMac("tag-2 ","tagString tst: "+testString, mac)
		posFound 	= testString.find(tagString)
		dPos 		= posFound - tagPos
		if len(testString) > lTag + tagPos: posFound =-1; dPos = 100
		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-F ","posFound: "+str(posFound)+", dPos: "+str(dPos)+", tag: "+tag+ ", "+str( knownBeaconTags[tag]["tag"])+", tagString: "+tagString, mac)
		return posFound, dPos
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30,u"Mac#:{}".format(mac))
	return -1,100 


#################################
def doLoopCheck(tt, sc, pc, sensor, useHCI):
	global reasonMax 

	try:		
		sensCheck  = copy.copy(sc) 
		paramCheck = copy.copy(pc) 
		if tt - sensCheck > 2:
			sensCheck = tt		

			checkIFtrackMacIsRequested()

			if U.checkNowFile(sensor): reasonMax = max(reasonMax, 7)

			if BLEAnalysis(useHCI):
				U.restartMyself(param="", reason="BLE analysis")

			if beep(useHCI):
				U.restartMyself(param="", reason="beep")

			if getBeaconParameters(useHCI):
				U.restartMyself(param="", reason="get battery levels")


		if tt - paramCheck > 10:
			if readParams(False): reasonMax = max(reasonMax, 8) # new params
			paramCheck=time.time()

		return sensCheck, paramCheck 

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return sensCheck, paramCheck 


#################################
def checkForBatteryInfo( UUID1, tagFound, mac, hexstr ):
	global trackMac, knownBeaconTags
	try:
		bl = ""
		if UUID1 in knownBeaconTags and tagFound == "found":
			if type(knownBeaconTags[UUID1]["battCmd"]) != type({}) and knownBeaconTags[UUID1]["battCmd"].find("msg:") >-1:
				# parameter format:     "battCmd": "msg:pos=-3,norm=255", 
				try:
					params	=  knownBeaconTags[UUID1]["battCmd"]
					params	= params.split("msg:")[1]
					if mac == trackMac and logCountTrackMac >0:
						writeTrackMac(  "Bat-1 ","params:{}".format(params), mac )
					params	= params.split(",")
					batPos	= int(params[0].split("=")[1])*2
					norm	= float(params[1].split("=")[1])
					batHexStr = hexstr[12:]
					bl	 	=100.* int(batHexStr[batPos:batPos+2],16)/norm
					if mac == trackMac and logCountTrackMac >0:
						writeTrackMac(  "Bat-2 ", "params:{}, batpos:{}, hex:{}, norm:{}, bl:{}".format(params, batPos, batHexStr[batPos:batPos+2], norm, bl),  mac )
				except	Exception, e:
					if mac == trackMac and logCountTrackMac >0:
						writeTrackMac("", u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), mac)
					bl	= ""

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return bl


#################################
def checkIfTagged(mac, macplain, macplainReverse, UUID, Min, Maj, isOnlySensor, hexstr, blIn, rssi):
	global trackMac, logCountTrackMac, onlyTheseMAC, knownBeaconTags, acceptJunkBeacons
	try:
		prio  				= -1
		dPos  				= -100
		UUID1 				= ""
		tagFound 			= "notTested"
		rejectThisMessage 	= False
		mac 				= copy.copy(mac)
		bl  				= copy.copy(blIn)


		### is this a know beacon with a known tag ?
		if mac in onlyTheseMAC  and onlyTheseMAC[mac] != ["",0,"",""]:
			tag 			= onlyTheseMAC[mac][0]
			prio 			= onlyTheseMAC[mac][1] # this is from knownbeacons
			uuidMajMin 		= onlyTheseMAC[mac][2].split("-")
			useOnlyPrioMsg 	= onlyTheseMAC[mac][3] == "1" # this is from props, device edit setiings
			if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac( "1-    ", "tag:"+tag+ ", prio:"+str(prio)+", uuidMajMin:"+str(uuidMajMin)+", useOnlyPrioMsg: "+str(useOnlyPrioMsg), mac)
			# right message format, if yes us main UUID
			if  tag in knownBeaconTags:
				UUID1 	= onlyTheseMAC[mac][0]
				UUID 	= UUID1
				Maj 	= uuidMajMin[1]
				Min 	= uuidMajMin[2]
				tagFound = "notTested"
				posFound, dPos = testComplexTag(hexstr[12:-2], tag, mac, macplain, macplainReverse)
				if posFound == -1 or abs(dPos) > knownBeaconTags[tag]["posDelta"]:
					tagFound = "failed"
					if useOnlyPrioMsg:
						rejectThisMessage = True
				else: 
					tagFound = "found"
		else:
			rejectThisMessage 	= True


		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac( "5-    ", "rejectThisMessage:" +str(rejectThisMessage)+ ", UUID: "+UUID +"  "+ str(Maj)+"  "+ str(Min),mac)

		## mac not in current list?
		if UUID1 == "" and (acceptNewTagiBeacons !="off" or trackMac != ""):
			## check if in tag list
		
			for tag in knownBeaconTags:
				if knownBeaconTags[tag]["pos"] == -1: 			 	continue
				posFound, dPos = testComplexTag(hexstr[12:-2], tag, mac, macplain, macplainReverse)
				if posFound == -1: 									continue
				if abs(dPos) > knownBeaconTags[tag]["posDelta"]: 	continue
				if acceptNewTagiBeacons == "all" or acceptNewTagiBeacons == tag:
					tagFound = "found"
					UUID = tag
					UUID1 = tag
					rejectThisMessage 	= False
				break

		if UUID1 == "": rejectThisMessage = True

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac( "9-    ", "isOnlySensor:"+str(isOnlySensor)+", checking bat: "+str(knownBeaconTags[tag]["battCmd"]) +" tagFound: "+str(tagFound)+ ", UUID: "+UUID+ ", rejectThisMessage: "+str(rejectThisMessage) ,mac)

		if not acceptJunkBeacons:
			if UUID == "": 
				#print "reject UUID" 
				if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
					writeTrackMac( "10    ", "reject bad uuid", mac)
				rejectThisMessage = True

		if rejectThisMessage: # unknow beacon.. accept if RSSI > accept
			if mac not in onlyTheseMAC  and mac not in doNotIgnore:
				if rssi > acceptNewiBeacons: 
					writeTrackMac( "12-   ", "accept rssi > accept new  and !tagfound", mac)
					rejectThisMessage = False

		if bl == "": 
			bl = checkForBatteryInfo( UUID1, tagFound, mac, hexstr )


		iphoneUUID, imac = checkIfIphone(UUID, mac)
		if not iphoneUUID:
			#if checkIfIgnore(uuid, mac): 
			#	if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			#		writeTrackMac( "12-   ", "reject checkIfIgnore ", mac) 
			pass
		else:
			rejectThisMessage = False
			mac = imac

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return mac, tagFound, rejectThisMessage, UUID, UUID1, Maj, Min, bl

#################################
#################################
######## BLE SENSORS END  #######
#################################
#################################


####### main pgm / loop ############


#################################



####### main pgm / loop ############

def execbeaconloop():
	global collectMsgs, sendAfterSeconds, loopMaxCallBLE, ignoreUUID,  beacon_ExistingHistory, deleteHistoryAfterSeconds,lastWriteHistory,maxParseSec,batteryLevelPosition
	global acceptNewiBeacons, acceptNewTagiBeacons, onlyTheseMAC,enableiBeacons,offsetUUID,alreadyIgnored, sendFullUUID, minSignalCutoff, acceptJunkBeacons, knownBeaconTags
	global myBLEmac, BLEsensorMACs
	global oldRaw,	lastRead
	global UUIDtoIphone, UUIDtoIphoneReverse, mapReasonToText
	global downCount, doNotIgnore, beaconsOnline, logCountTrackMac, trackMac, nLogMgsTrackMac, startTimeTrackMac, trackMacText
	global rpiDataAcquistionMethod
	global readBufferSize
	global readbuffer
	global ListenProcessFileHandle
	global lastLESCANrestart
	global beaconsNew
	global reasonMax 



	lastLESCANrestart	= 0
	ListenProcessFileHandle =""
	readbuffer			= ""
	readBufferSize		= 4096*8
	rpiDataAcquistionMethod		 	= ""
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
	UUIDtoIphoneReverse	 ={}
	offsetUUID			={}
	fastDownMinSignal	={}
	batteryLevelPosition={}
	alreadyIgnored		={}
	lastIgnoreReset		=0
	myBLEmac			= ""
	sensor				= G.program	 
	sendFullUUID		= False
	badMacs				= ["00:00:00:00:00:00"]

	U.killOldPgm(-1,"hcidump")
	U.killOldPgm(-1,"hcitool")
	U.killOldPgm(-1,"lescan")


	myPID				= str(os.getpid())
	#kill old G.programs
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")
	count = U.killOldPgm(-1,"hciconfig")
	if count > 4:
		U.logger.log(50,"beaconloop exit, hciconfig, to many ghost hciconfig processes running:{}".format(count))
		U.sendRebootHTML("bluetooth_startup is DOWN  too many  ghost hciconfig processes running ",reboot=True, force=True)
		time.sleep(10)

	readParams(True)

	U.logger.log(30,"======= starting v:{} ========".format(version))


	fixOldNames()


	# getIp address 
	if U.getIPNumber() > 0:
		U.logger.log(30, " no ip number ")
		time.sleep(10)
		return


	# get history
	readbeacon_ExistingHistory()


	## start bluetooth
	for ii in range(5):
		sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber)  
		if retCode ==0: break 
		time.sleep(3)
	if retCode != 0: 
		U.logger.log(30,"beaconloop exit, recode from getting BLE stack >0, after 3 tries:")
		return

	if rpiDataAcquistionMethod == "hcidump":
		retCode = startHCUIDUMPlistener(useHCI)
		if retCode != "":
			U.logger.log(30,"beaconloop exit, === error in starting HCIdump listener, exit beaconloop ===")
			return

	U.logger.log(30,"using >{}< for data read method".format(rpiDataAcquistionMethod))
	
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

	lastMSGwithDataPlain = tt
	lastMSGwithDataPassed = tt
	maxLoopCount	 = 6000
	restartCount	 = 0
	logCountTrackMac = 0 
	nMsgs			 = 0
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

			reasonMax = 1

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

			if rpiDataAcquistionMethod == "socket":
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
				
				
				if reasonMax > 1 and tt -G.tStart > 30: break	# only after ~30 seconds after start....  to avoid lots of short messages in the beginning = collect all ibeacons before sending

				if tt - timeAtLoopStart	 > sendAfter: 
					break # send curl msgs after collecting for xx seconds

				## get new data
				allBeaconMSGs=[]

				if nMsgs > 2: time.sleep(0.2)
				hexstr = ""

				if rpiDataAcquistionMethod == "socket":
					try: 
						pkt = sock.recv(255)
						Msgs = [(stringFromPacket(pkt[7:])).upper()]
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
				
				if rpiDataAcquistionMethod == "hcidump":
					Msgs = readHCUIDUMPlistener()

				nMsgs = len(Msgs)
				oneValid = False
				for hexstr in Msgs: 
					nCharThisMessage	= len(hexstr)
	
					##U.logger.log(20, "loopCount:{}  #:{}  len:{}".format(loopCount, iiWhile, len(pkt))) 
					#U.logger.log(20, "data nChar:{}".format(nCharThisMessage))
					if nCharThisMessage < 20: 
						U.logger.log(20, "bad data nChar:{}".format(nCharThisMessage))
						break
					try:
						# build the return string: mac#, uuid-major-minor,txpower??,rssi
						lastMSGwithDataPlain = int(time.time())
					
						macplainReverse 	= hexstr[0:12]
						mac 				= macplainReverse[10:12]+":"+macplainReverse[8:10]+":"+macplainReverse[6:8]+":"+macplainReverse[4:6]+":"+macplainReverse[2:4]+":"+macplainReverse[0:2]
						macplain 			= mac.replace(":","")

						########  track mac  start / end ############
						if (mac == trackMac or trackMac =="*") and logCountTrackMac >0 :
							logCountTrackMac -= 1
							writeTrackMac("RAW---", (datetime.datetime.now().strftime("%H:%M:%S.%f"))[:-5]+ " logCountTrackMac: "+ str(logCountTrackMac)+" hex: "+hexstr ,mac)
								
							if logCountTrackMac <= 0 or time.time() - startTimeTrackMac > 30:
								writeTrackMac("END   ","FINISHed TRACKMAC logging ===", trackMac)
								logCountTrackMac  = -1
								trackMac = ""
								U.sendURL(data={"trackMac":trackMacText}, squeeze=False)


						if not acceptJunkBeacons:
							if nCharThisMessage < 20: 
								continue # this is not supported ..

						# set prelim variables, default settings ..
						msgStart		= 14
						majEnd 			= len(hexstr) - 12	
						uuidLen 		= min( 32, (majEnd - msgStart))
						UUID 			= hexstr[-uuidLen-12:-12]
						Maj	 			= str(int(hexstr[-12:-8],16))
						Min	 			= str(int(hexstr[-8:-4],16))
						tx		 		= str(signedIntfromString(hexstr[-4:-2]))
						rssi			= signedIntfromString(hexstr[-2:])
						rx  			= str(rssi)
						mfgID			= hexstr[msgStart+10:msgStart+14]
						pType 			= hexstr[msgStart+14:msgStart+16]  # 02  = procimity beacon, BE  = ALT beacon nBytes  = 27
						beaconType 		= hexstr[msgStart+8:msgStart+10]  #  FF = iBeacon
						beaconType 		+= "-"+pType.upper() 

						tx, bl, UUID, Maj, Min, isOnlySensor  = doSensors( mac, rx, tx, nCharThisMessage, hexstr, UUID, Maj, Min)

						if isOnlySensor:
							rejectThisMessage 	= True
							lastMSGwithDataPassed = int(time.time())
							continue

						if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
							writeTrackMac( "0-    ", "UUID: "+UUID+ ", Maj: "+str(Maj)+", Min: "+Min +", RX:"+rx+", TX:"+tx ,mac)
						mac, tagFound, rejectThisMessage, UUID, UUID1, Maj, Min, bl = checkIfTagged(mac, macplain, macplainReverse, UUID, Min, Maj, isOnlySensor, hexstr, bl, rssi )

						if rejectThisMessage: continue


						lastMSGwithDataPassed = int(time.time())

						if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
							writeTrackMac( "21-   ", "added to beaconMSG", mac)

						# compose message

						try: 
							beaconMAC	= mac
							uuid		= UUID+"-"+Maj+"-"+Min
							rssi		= float(rx)
							txPower		= float(tx)
							try: 	bLevel = int(bl)
							except: bLevel = ""
						except	Exception, e:
							U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							U.logger.log(30, "bad data >> "+unicode(beaconMSG)+"  <<beaconMSG")
							continue# skip if bad data

						beaconMSG = [mac, UUID+"-"+Maj+"-"+Min, rx, tx, bLevel, beaconType, nCharThisMessage]


						### if in fast down lost and signal < xx ignore this signal= count as not there 
						if beaconMAC in fastDownMinSignal : sendAfter = min(45., sendAfterSeconds)

						checkIfFastDownMinSignal(beaconMAC, rssi)

						if beaconMAC not in beaconsNew: # add fresh one if not in new list
							beaconsNew[beaconMAC]={"uuid":uuid, "txPower":txPower, "rssi":rssi, "count":1, "dCount":0,"timeSt":tt,"bLevel":bLevel, "pktInfo":"len:"+str(nCharThisMessage)+", type:"+beaconType}# [uid-major-minor,txPower,signal strength, # of measuremnts
					
						else:  # increment averages and counters
							beaconsNew[beaconMAC]["rssi"]	 += rssi # signal
							beaconsNew[beaconMAC]["count"]	 += 1  # count for calculating averages
							beaconsNew[beaconMAC]["txPower"] += txPower # transmit power
							beaconsNew[beaconMAC]["timeSt"]	 = tt  
							if bLevel != "":
								beaconsNew[beaconMAC]["bLevel"]	 = bLevel # battery level 
							if "pktInfo" not in beaconsNew[beaconMAC]: # add fresh one if not in new list
								beaconsNew[beaconMAC]["pktInfo"] = "len:"+str(nCharThisMessage)+", type:"+beaconType
							if "dCount" not in beaconsNew[beaconMAC]: # add fresh one if not in new list
								beaconsNew[beaconMAC]["dCount"] = 0



						checkIfNewOrDeltaSignalOrWasMissing(beaconMAC, beaconMSG)
						if  (beaconMAC == trackMac or trackMac =="*") and logCountTrackMac >0:
							writeTrackMac( "-MSG- ", "{}".format(beaconsNew[beaconMAC]) ,beaconMAC)
						####if beaconMAC =="0C:F3:EE:00:66:15": print  beaconsNew

					except	Exception, e:
						U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)+ "  bad data, skipping")
						try:
							print "	 MAC:  ", mac
							print "	 UUID: ", UUID
						except: pass
						continue# skip if bad data

					checkIfFastDown() # send -999 if gone 

					sensCheck, paramCheck = doLoopCheck(tt, sensCheck, paramCheck, sensor, useHCI )
					oneValid = True

				# only needed if no valid msgs in loop
				if not oneValid:
					sensCheck, paramCheck = doLoopCheck(tt, sensCheck, paramCheck, sensor, useHCI )

			if rpiDataAcquistionMethod == "socket":
				sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )

			composeMSG(timeAtLoopStart)
			handleHistory() 
			U.echoLastAlive(G.program)
			#restartLESCAN(useHCI)

			dt1 = int(time.time() - lastMSGwithDataPlain)
			dt2 = int(time.time() - lastMSGwithDataPassed)
			if dt1 > G.rebootIfNoMessagesSeconds:
				if dt1 > 90 or dt2 > 90:
					G.debug = 10
					maxLoopCount = 20
					restartCount +=1
					U.logger.log(30, u" time w/out any message .. anydata: %6d[secs];  okdata: %6d[secs];   loopCount:%d;  restartCount:%d"%(dt1, dt2, loopCount, restartCount))
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
		stopHCUIDUMPlistener()
		time.sleep(20)
		subprocess.call("/usr/bin/python "+G.homeDir+G.program+".py &", shell=True)
	try: 	G.sendThread["run"] = False; time.sleep(1)
	except: pass

U.echoLastAlive(G.program)
execbeaconloop()
stopHCUIDUMPlistener()
U.logger.log(30,"end of beaconloop.py ") 
sys.exit(0)		   
