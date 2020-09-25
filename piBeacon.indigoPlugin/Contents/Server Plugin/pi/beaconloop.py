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
version   = 8.30


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

def signedIntfromString16(string):
	try:
		intNumber = int(string,16)
		if intNumber > 32767: intNumber -= 65536
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
			
	

def startBlueTooth(pi,reUse=False,thisHCI=""):
	global myBLEmac, downCount
	global lastLESCANrestart
	global rpiDataAcquistionMethod

	myBLEmac = ""
	devId	 = 0
	useHCI	 = ""
	## good explanation: http://gaiger-G.programming.blogspot.com/2015/01/bluetooth-low-energy.html
	U.logger.log(30,"(re)starting bluetooth")
	startTime = time.time()
	logLevelStart = 20
	if thisHCI !="": logLevelStart = 10
	try:
		HCIs = U.whichHCI()
		for hci in HCIs["hci"]:
			if thisHCI != "" and hci !=thisHCI: continue

			if reUse:
				cmd = "sudo hciconfig "+hci+" reset"
				ret = subprocess.call(cmd, shell=True) # 
				U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )

			else:
				cmd = "sudo hciconfig "+hci+" down"
				ret = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate()# disable bluetooth
				U.logger.log(10,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )
				if ret[1] !="":
					time.sleep(0.2)
					ret = subprocess.call(cmd, shell=True) # enable bluetooth
					U.logger.log(logLevelStart)

				cmd = "sudo hciconfig "+hci+" up"
				ret = subprocess.Popen(cmd, shell=True,stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate() # enable bluetooth
				U.logger.log(10,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime)  )
				if ret[1] !="":
					time.sleep(0.2)
					ret = subprocess.call(cmd, shell=True) # enable bluetooth
					U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )

			cmd	 = "sudo hciconfig {} noleadv &\n sudo hciconfig {} noscan &".format(hci, hci)
			ret = subprocess.call(cmd,shell=True,stdout=subprocess.PIPE)
			U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd.replace("\n",";"), ret, time.time()- startTime)  )


		#### selct the proper hci bus: if just one take that one, if 2, use bus="uart", if no uart use hci0
		if not reUse: HCIs = U.whichHCI()
		if HCIs !={} and "hci" in  HCIs and HCIs["hci"] !={}:

			#U.logger.log(30,"myBLEmac HCIs{}".format( HCIs))
			useHCI,  myBLEmac, devId = U.selectHCI(HCIs["hci"], G.BeaconUseHCINo,"UART")
			if myBLEmac ==  -1:
				U.logger.log(20,"myBLEmac wrong: myBLEmac:{}, HCIs:{}".format( myBLEmac, HCIs))
				return 0,  0, -1, useHCI
			U.logger.log(20,"Beacon Use HCINo {};  useHCI:{};  myBLEmac:{}; devId:{}, DT:{:.3f}" .format(G.BeaconUseHCINo, useHCI, myBLEmac, devId, time.time()- startTime))
			
			if 	rpiDataAcquistionMethod == "hcidump":
				cmd	 = "sudo hciconfig {} leadv 3 &".format(useHCI)
				ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE).communicate()
				U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )
				

			if	True:
				# setup broadcast message
				OGF					= " 0x08"
				OCF					= " 0x0008"
				iBeaconPrefix		= " 1E 02 01 1A 1A FF 4C 00 02 15"
				uuid				= " 2f 23 44 54 cf 6d 4a 0f ad f2 f4 91 1b a9 ff a6"
				MAJ					= " 00 01"
				MIN					= " 00 "+"0%x"%(int(pi))
				txP					= " C5 00"
				#cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + OCF + iBeaconPrefix + uuid + MAJ + MIN + txP
				cmd	 = "hcitool -i {} cmd{}{}{}{}{}{}{} &".format(useHCI, OGF, OCF, iBeaconPrefix, uuid, MAJ, MIN, txP)
				ret = subprocess.call(cmd,shell=True,stdout=subprocess.PIPE)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )


			if 	rpiDataAcquistionMethod == "hcidump":
				restartLESCAN(useHCI, logLevelStart, force=True )



			if	rpiDataAcquistionMethod == "socket":
				####################################set adv params		minInt	 maxInt		  nonconectable	 +??  <== THIS rpi to send beacons every 10 secs only 
				#											   00 40=	0x4000* 0.625 msec = 16*4*256 = 10 secs	 bytes are reverse !! 
				#											   00 10=	0x1000* 0.625 msec = 16*1*256 = 2.5 secs
				#											   00 04=	0x0400* 0.625 msec =	4*256 = 0.625 secs
				#cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + " 0x0006"	  + " 00 10"+ " 00 20" +  " 03"			   +   " 00 00 00 00 00 00 00 00 07 00"
				cmd	 = "hcitool -i {} cmd{} 0x0006 00 10 00 20 03 00 00 00 00 00 00 00 00 07 00 &".format(useHCI, OGF)
				## maxInt= A0 00 ==	 100ms;	 40 06 == 1000ms; =0 19 = 4 =seconds  (0x30x00	==> 64*256*0.625 ms = 10.024secs  use little endian )
				ret = subprocess.call(cmd,shell=True,stdout=subprocess.PIPE)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime)  )
				####################################LE Set Advertise Enable
				#cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + " 0x000a" + " 01"
				time.sleep(0.1)
				cmd	 = "hcitool -i {} cmd{} 0x000a 01 &".format(useHCI, OGF)
				ret = subprocess.call(cmd,shell=True,stdout=subprocess.PIPE)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )
				time.sleep(0.1)


			if not reUse: HCIs = U.whichHCI()
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
def restartLESCAN(useHCI, loglevel, force=False):
	global rpiDataAcquistionMethod
	global lastLESCANrestart
	try:
		if rpiDataAcquistionMethod != "hcidump": return 
		if time.time() - lastLESCANrestart  > 5 or force:
			tt = time.time()
			lastLESCANrestart = tt
			#cmd	 = "sudo hciconfig {} reset".format(useHCI,G.homeDir)
			#ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE).communicate()
			#U.logger.log(20,"cmd:{} .. ret:{}...  startuptime: dT:{:.3f}".format(cmd, ret, time.time() - tt) )
			#U.killOldPgm(-1,"lescan") # will kill the launching sudo parent process, lescan still running
			#cmd = "sudo hciconfig {} reset".format(useHCI)
			#U.logger.log(20,cmd) 
			#ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE).communicate()
			# --privacy and -- duplicates does not work on some RPI / USB devices
			#cmd	 = "sudo hcitool -i {} lescan --duplicates  > /dev/null 2>&1 &".format(useHCI,G.homeDir)
			#cmd	 = "sudo hcitool -i {} lescan --privacy --passive --discovery=l  > /dev/null 2>&1 &".format(useHCI,G.homeDir)
			#cmd	 = "sudo hcitool -i {} lescan --passive --discovery=l  > /dev/null 2>&1 &".format(useHCI,G.homeDir)
			U.killOldPgm(-1,"hcitool") # will kill the launching sudo parent process, lescan still running
			cmd	 = "sudo hcitool -i {} lescan > /dev/null 2>&1 &".format(useHCI,G.homeDir)
			ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE).communicate()
			U.logger.log(loglevel,"cmd:{} .. ret:{}...  dT:{:.3f}".format(cmd, ret, time.time() - tt) )
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
def startHCUIDUMPlistnr(hci):
	global myBLEmac
	global ListenProcessFileHandle
	global readFrom

	try:
		if readFrom != "": return ""
		if ListenProcessFileHandle !="":
			stopHCUIDUMPlistener()

		cmd = "sudo hcidump -i {} --raw".format(hci)
		U.logger.log(20,"cmd {}".format(cmd))
		ListenProcessFileHandle = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		##pid = ListenProcessFileHandle.pid
		##self.myLog( text=u" pid= " + unicode(pid) )
		msg = unicode(ListenProcessFileHandle.stderr)
		if msg.find("open file") == -1:	# try this again
			self.indiLOG.log(40,"uType {}; IP#: {}; error connecting {}".format(uType, ipNumber, msg) )
			self.sleep(20)
			return  "error "+ unicode(msg)

		U.killOldPgm(-1,"sudo hcidump")

		if not U.pgmStillRunning("hcidump -i"):
			self.indiLOG.log(40,"hcidump not running ")
			return "error"

		# set the O_NONBLOCK flag of ListenProcessFileHandle.stdout file descriptor:
		flags = fcntl.fcntl(ListenProcessFileHandle.stdout, fcntl.F_GETFL)  # get current p.stdout flags
		fcntl.fcntl(ListenProcessFileHandle.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
		time.sleep(0.1)
		return  ""

	except	Exception, e:
		U.logger.log(20,"startConnect: in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return  "error "+ unicode(e)
	except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return  "error"

#################################
def stopHCUIDUMPlistener():
	global readFrom
	global ListenProcessFileHandle
	if readFrom =="": return 
	try:
		U.logger.log(20, u"stopping hcidump --raw  and hcitool -i xxx lescan procs and handles")
		U.killOldPgm(-1,"hcidump")
		U.killOldPgm(-1,"hcitool")
		if ListenProcessFileHandle != "":
			ListenProcessFileHandle.terminate()
			ListenProcessFileHandle = ""
	except	Exception, e:
		U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


#################################
def readHCUIDUMPlistener():
	global readBufferSize, ListenProcessFileHandle
	global readFrom

	if readFrom != "":
		messages =[]
		try:
			if os.path.isfile(readFrom):
				f = open(readFrom)
				messages = f.read()
				f.close()
				subprocess.call("rm {}".format(readFrom), shell=True)
				if len(messages) > 5:
					return [messages.strip("\n")]
			return []
				
		except	Exception, e:
			U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return []

	try:
		lines = os.read(ListenProcessFileHandle.stdout.fileno(),readBufferSize) 
		if len(lines) == 0: return []
		messages = combineLines(lines)
		#U.logger.log(20, u"readHCUIDUMPlistener lines:\n{}".format(lines))
		#U.logger.log(20, u"readHCUIDUMPlistener messages\n{}".format(json.dumps(messages).replace(",","\n")))
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
			MSGs.append(line[14:]) # start w the MAC#, skip the preamble
		if len(MSGs) ==0: return []

		if len(MSGs[-1]) < 40:
			readbuffer = MSGs[-1]
			#U.logger.log(20, u"readHCUIDUMPlistener leftover>{}<, >{}<".format(readbuffer,MSGs[-1] ))
			del MSGs[-1]
		else:
			readbuffer = ""		
	
		return MSGs	
	except	Exception, e:
		U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return []

	
#################################
def toReject(text):
	global doRejects
	try:
		if not doRejects: return 

		f=open("{}temp/rejects".format(G.homeDir),"a")
		f.write(str(time.time())+";"+text+"\n")
		f.close()

	except	Exception, e:
		if unicode(e).find("Read-only file system:") >-1:
			f = open(G.homeDir+"temp/rebootNeeded","w")
			f.write("Read-only file system")
			f.close()

#################################
def fixOldNames():

	if os.path.isfile(G.homeDir+"beaconsExistingHistory"):
		subprocess.call("sudo mv "+G.homeDir+"beaconsExistingHistory " + G.homeDir+"beacon_ExistingHistory", shell=True)





def readParams(init):
	global collectMsgs, loopMaxCallBLE,  beacon_ExistingHistory, signalDelta,fastDownList, ignoreMAC
	global acceptNewiBeacons, acceptNewTagiBeacons,onlyTheseMAC,enableiBeacons, sendFullUUID,BLEsensorMACs, minSignalOff, minSignalOn, knownBeaconTags
	global oldRaw, lastRead
	global rpiDataAcquistionMethod
	if init:
		collectMsgs			= 10  # in parse loop collect how many messages max	  ========	all max are an "OR" : if one hits it stops
		loopMaxCallBLE		= 900 # max loop count	in main pgm to collect msgs
		portOfServer		= "8176"
		G.ipOfServer	  	= ""
		G.passwordOfServer	= ""
		G.userIdOfServer  	= ""
		G.myPiNumber	  	= "0"

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
			if "acceptNewiBeacons"		in inp:	 acceptNewiBeacons=	  int(inp["acceptNewiBeacons"])
			if "acceptNewTagiBeacons"	in inp:	 acceptNewTagiBeacons=	 (inp["acceptNewTagiBeacons"])
			if "sendFullUUID"			in inp:	 sendFullUUID=			 (inp["sendFullUUID"]=="1" )

			if "rpiDataAcquistionMethod"				in inp:	 
				xx =		 	 										(inp["rpiDataAcquistionMethod"])
				if xx != rpiDataAcquistionMethod and rpiDataAcquistionMethod != "":
					U.restartMyself(param="", reason="new data aquisition method")
				rpiDataAcquistionMethod = xx
			else:
				rpiDataAcquistionMethod = "hcidump"


			if "sensors"			 in inp: 
				sensors =			 (inp["sensors"])
				for sensor in G.BLEsensorTypes:
					if sensor in sensors:
						for devId in sensors[sensor]:
							sensD	= sensors[sensor][devId]
							mac		= sensD["mac"]
							if mac not in BLEsensorMACs: BLEsensorMACs[mac] = {}
							
							BLEsensorMACs[mac]["type"] 							= sensor
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
								BLEsensorMACs[mac]["lastUpdate"]				 	= 0
								BLEsensorMACs[mac]["lastUpdate1"]				 	= 0
								BLEsensorMACs[mac]["lastUpdate2"]				 	= 0
								BLEsensorMACs[mac]["SOS"]				 			= False
								BLEsensorMACs[mac]["hum"]				 			= -100
								BLEsensorMACs[mac]["temp"]				 			= -100
								BLEsensorMACs[mac]["AmbientTemperature"] 			= -100
								BLEsensorMACs[mac]["onOff"]		 					= False
								BLEsensorMACs[mac]["onOff1"]		 				= False
								BLEsensorMACs[mac]["onOff2"]		 				= False
								BLEsensorMACs[mac]["onOff3"]		 				= False
								BLEsensorMACs[mac]["onOff"] 						= False
								BLEsensorMACs[mac]["alive"] 						= False
								BLEsensorMACs[mac]["counter"] 						= "-1"
								BLEsensorMACs[mac]["batteryVoltage"] 	 	 		= -1
								BLEsensorMACs[mac]["chipTemperature"] 	 	 		= -1
								BLEsensorMACs[mac]["secsSinceStart"] 	 	 		= -1

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
	try:		onlyTheseMAC = InParams["onlyTheseMAC"]
	except:		onlyTheseMAC = {}

	try:		ignoreMAC = InParams["ignoreMAC"]
	except:		ignoreMAC = []
		
	try:		fastDownList = InParams["fastDownList"]
	except:		fastDownList = {}

	try:		minSignalOff = InParams["minSignalOff"]
	except:		minSignalOff = {}

	try:		minSignalOn = InParams["minSignalOn"]
	except:		minSignalOn = {}

	try:		signalDelta = InParams["signalDelta"]
	except:		signalDelta = {}

		
	U.logger.log(0,"fastDownList:       {}".format(fastDownList))
	U.logger.log(0,"signalDelta:        {}".format(signalDelta))
	U.logger.log(0,"ignoreMAC:          {}".format(ignoreMAC))
	return


#################################, check if signal strength is acceptable for fastdown 
def setEmptybeaconsThisReadCycle(mac):
	global beaconsThisReadCycle
	try:
			beaconsThisReadCycle[mac]={"typeOfBeacon":"", "txPower":0, "rssi":0, "timeSt":0,"batteryLevel":"","mfg_info":"", "iBeacon":"","reason":0}
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

#################################
def readbeacon_ExistingHistory():
	global	beacon_ExistingHistory, lastWriteHistory
	try:
		fg = open("{}temp/beacon_ExistingHistory".format(G.homeDir),"r")
		beacon_ExistingHistory = json.loads(fg.read())
		fg.close()
		reset=False
		for beacon in beacon_ExistingHistory:
			if "fastDown" not in beacon_ExistingHistory["beacon"]: 
				reset=True
				break				
		if reset:
			beacon_ExistingHistory={}
	except: 
		beacon_ExistingHistory={}
	lastWriteHistory=time.time()
	return
	

#################################
def writebeacon_ExistingHistory():
	global	 beacon_ExistingHistory, lastWriteHistory
	if time.time() - lastWriteHistory < 30: return
	lastWriteHistory=time.time()
	try:
		fg = open("{}temp/beacon_ExistingHistory".format(G.homeDir),"w")
		fg.write(json.dumps(beacon_ExistingHistory))
		fg.close()
	except Exception, e:
		if unicode(e).find("Read-only file system:") >-1:
			subprocess.call("sudo reboot", shell=True)
	return 

#################################
def stripOldHistory(mac):
	global	beacon_ExistingHistory, deleteHistoryAfterSeconds

	if  mac in beacon_ExistingHistory:
		ll = len(beacon_ExistingHistory[mac]["rssi"])
		for kk in range(ll):
			if len(beacon_ExistingHistory[mac]["rssi"]) > 10:
				del beacon_ExistingHistory[mac]["rssi"][0]
				del beacon_ExistingHistory[mac]["timeSt"][0]
				del beacon_ExistingHistory[mac]["reason"][0]

		ll = len(beacon_ExistingHistory[mac]["rssi"])
		for kk in range(ll):
			if len(beacon_ExistingHistory[mac]["rssi"]) > 1:
				if time.time() - beacon_ExistingHistory[mac]["timeSt"][0] > deleteHistoryAfterSeconds:
					del beacon_ExistingHistory[mac]["rssi"][0]
					del beacon_ExistingHistory[mac]["timeSt"][0]
					del beacon_ExistingHistory[mac]["reason"][0]
				else:
					break
	return 

#################################
def emptyHistory(mac):
	global	beacon_ExistingHistory
	try:
		if  mac in beacon_ExistingHistory:
			beacon_ExistingHistory[mac]["rssi"]		=[]
			beacon_ExistingHistory[mac]["timeSt"]	=[]
			beacon_ExistingHistory[mac]["reason"]	=[]
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

#################################
def handleHistory():
	global	beacon_ExistingHistory

	for beacon in beacon_ExistingHistory:
		stripOldHistory(beacon)
	# save history to file
	writebeacon_ExistingHistory() 
	return

#################################, check if signal strength is acceptable for fastdown 
def copyToHistory(mac):
	global beaconsThisReadCycle, beacon_ExistingHistory
	try:
		if mac not in beacon_ExistingHistory:
			beacon_ExistingHistory[mac]= copy.copy(beaconsThisReadCycle[mac])
		beacon_ExistingHistory[mac]["fastDown"]		= False
		beacon_ExistingHistory[mac]["rssi"]			= []
		beacon_ExistingHistory[mac]["timeSt"]		= []
		beacon_ExistingHistory[mac]["reason"]		= []
		beacon_ExistingHistory[mac]["txPower"]		= 0
		beacon_ExistingHistory[mac]["count"]		= 1

		#U.logger.log(30,u"mac:{}; beacon_ExistingHistory:{}".format(mac, beacon_ExistingHistory[mac]))

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


#################################, check if signal strength is acceptable for fastdown 
def fillHistory(mac):
	global beaconsThisReadCycle, beacon_ExistingHistory
	try:
		if mac not in beacon_ExistingHistory: 
			copyToHistory(mac) 

		beacon_ExistingHistory[mac]["rssi"].append(beaconsThisReadCycle[mac]["rssi"])
		beacon_ExistingHistory[mac]["timeSt"].append(beaconsThisReadCycle[mac]["timeSt"])
		beacon_ExistingHistory[mac]["reason"].append(beaconsThisReadCycle[mac]["reason"])
		beacon_ExistingHistory[mac]["txPower"]				+= beaconsThisReadCycle[mac]["txPower"]
		beacon_ExistingHistory[mac]["count"]				+= 1
		if beaconsThisReadCycle[mac]["batteryLevel"] !="": 	beacon_ExistingHistory[mac]["batteryLevel"]	= beaconsThisReadCycle[mac]["batteryLevel"]
		if beaconsThisReadCycle[mac]["iBeacon"] !="": 		beacon_ExistingHistory[mac]["iBeacon"]		= beaconsThisReadCycle[mac]["iBeacon"]
		if beaconsThisReadCycle[mac]["mfg_info"] !="":		beacon_ExistingHistory[mac]["mfg_info"]		= beaconsThisReadCycle[mac]["mfg_info"]
		if beaconsThisReadCycle[mac]["typeOfBeacon"] !="":	beacon_ExistingHistory[mac]["typeOfBeacon"]	= beaconsThisReadCycle[mac]["typeOfBeacon"]
		stripOldHistory(mac)
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


#################################
def checkMinMaxSignalAcceptMessage(mac, rssi):
	global beacon_ExistingHistory, minSignalOff, minSignalOn
	try:
		#returns true signal accepted
		# signal must be higher than x to switch to on and lower than y to switch to off 

		# quick check if enabled, if not accpet message
		if mac not in minSignalOn and  mac not in minSignalOff: return True

		on = False
		if mac in beacon_ExistingHistory:
			if len(beacon_ExistingHistory[mac]["timeSt"]) > 0:
				if time.time() - beacon_ExistingHistory[mac]["timeSt"][-1] < 60: on = True

		if not on and  mac in minSignalOn   and rssi < minSignalOn[mac]:	return False
		if     on and  mac in minSignalOff  and rssi < minSignalOff[mac]:	return False
			
		return True

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		
	
#################################
def composeMSG(timeAtLoopStart):
	global collectMsgs, loopMaxCallBLE
	global myBLEmac, sendFullUUID,  mapReasonToText, downCount, beaconsOnline
	global beaconsThisReadCycle, beacon_ExistingHistory
	global reasonMax
	global trackMac, logCountTrackMac
	try:
		nMessages = 0
		if myBLEmac == "00:00:00:00:00:00":
			time.sleep(2)
			U.restartMyself(param="", reason="bad BLE  =00..00")

		data = []
		for beacon in beaconsThisReadCycle:
			if beacon not in beacon_ExistingHistory: continue
			if beacon_ExistingHistory[beacon]["fastDown"] : continue
			if len(beacon_ExistingHistory[beacon]["rssi"]) == 0: continue
			if time.time() - beacon_ExistingHistory[beacon]["timeSt"][-1] > 55: continue # do not resend old data
			try:
				if beacon_ExistingHistory[beacon]["count"] != 0:
					avePower	=int(beacon_ExistingHistory[beacon]["txPower"]   /max(1,beacon_ExistingHistory[beacon]["count"]))
					if beacon_ExistingHistory[beacon]["fastDown"]:	aveSignal = -999 
					else:											aveSignal = int(sum(beacon_ExistingHistory[beacon]["rssi"]) /max(1,len(beacon_ExistingHistory[beacon]["rssi"])))
					if avePower > -200:								beaconsOnline[beacon] = int(time.time())
					beacon_ExistingHistory[beacon]["reason"][-1] = max(1, beacon_ExistingHistory[beacon]["reason"][-1] )
					r  = min(8,beacon_ExistingHistory[beacon]["reason"][-1])
					rr = mapReasonToText[r]
					newData = {"mac": beacon,
						"reason": rr, 
						"rssi": aveSignal, 
						"txPower": avePower, 
						"count": beacon_ExistingHistory[beacon]["count"]-1,
						"batteryLevel": beacon_ExistingHistory[beacon]["batteryLevel"],
						"mfg_info": beacon_ExistingHistory[beacon]["mfg_info"],
						"typeOfBeacon": beacon_ExistingHistory[beacon]["typeOfBeacon"],
						"iBeacon": beacon_ExistingHistory[beacon]["iBeacon"],
						}
					downCount = 0
					data.append(newData)

					if  (beacon == trackMac or trackMac =="*") and logCountTrackMac >0:
						writeTrackMac("MSG===  ","data:{}".format(newData), beacon)
					beacon_ExistingHistory[beacon]["count"] = 1
			except	Exception, e:
				U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				U.logger.log(30, " error composing mac:{}, beaconsThisReadCycle \n{}".format(beacon, beaconsThisReadCycle[beacon]))

		nMessages = len(data)
		if nMessages >1: downCount = 0
		U.sendURL({"msgs":data,"pi":str(G.myPiNumber),"piMAC":myBLEmac,"secsCol":int(time.time()-timeAtLoopStart),"reason":mapReasonToText[reasonMax]})

		# save active iBeacons for getbeaconparameters() process
		copyBE = copy.copy(beaconsOnline)
		for be in copyBE:
			if time.time() - copyBE[be] > 90:
				del beaconsOnline[be]
		U.writeJson("{}temp/beaconsOnline".format(G.homeDir), beaconsOnline, sort_keys=False, indent=0)
		return nMessages
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 0



#################################
def composeMSGForThisMacOnly(mac):
	global beaconsThisReadCycle, beacon_ExistingHistory, mapReasonToText
	global myBLEmac, secsCollected
	global trackMac, logCountTrackMac
	try:
		avePower	=int(beacon_ExistingHistory[mac]["txPower"]) /max(1,beacon_ExistingHistory[mac]["count"]-1)
		if beacon_ExistingHistory[mac]["fastDown"]:	aveSignal = -999 
		else:										aveSignal = round(beacon_ExistingHistory[mac]["rssi"][-1],1)
		if avePower > -200:
			beaconsOnline[mac] = int(time.time())
		beacon_ExistingHistory[mac]["reason"][-1] = max(1, beacon_ExistingHistory[mac]["reason"][-1] )
		r  = min(8,beacon_ExistingHistory[mac]["reason"][-1])
		rr = mapReasonToText[r]
		data = {"mac": mac,
			"reason": rr, 
			"rssi": aveSignal, 
			"txPower": avePower, 
			"count": max(1,beacon_ExistingHistory[mac]["count"]-1),
			"batteryLevel": beacon_ExistingHistory[mac]["batteryLevel"],
			"mfg_info": beacon_ExistingHistory[mac]["mfg_info"],
			"typeOfBeacon": beacon_ExistingHistory[mac]["typeOfBeacon"],
			"iBeacon": beacon_ExistingHistory[mac]["iBeacon"],
			}
		U.sendURL({"msgs":[data],"pi":str(G.myPiNumber),"piMAC":myBLEmac,"secsCol":1,"reason":rr})
		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("MSG-s   ", "sending single msg:{}".format(data),mac)

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 0



#################################
def checkIfDeltaSignal(mac):
	global collectMsgs, loopMaxCallBLE, signalDelta
	global onlyTheseMAC, beaconsThisReadCycle, beacon_ExistingHistory
 	global reasonMax

	try:
		if mac not in beacon_ExistingHistory: 			 return False
		if mac not in signalDelta: 						 return False
		if beacon_ExistingHistory[mac]["fastDown"]:		 return False
		if len(beacon_ExistingHistory[mac]["rssi"]) < 2: return False # need at least 2 messages

		rssi = beacon_ExistingHistory[mac]["rssi"][-1]
		rssiAve = sum(beacon_ExistingHistory[mac]["rssi"][1:]) / max(1,len(beacon_ExistingHistory[mac]["rssi"][1:]) )
		deltaTrue = abs(rssiAve-rssi) >  signalDelta[mac]	# delta signal > xdBm (set param)
		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("delta?  ", "abs(rssi:{} -rssiAve:{:4.0f}) < :{}? ==> {}".format(rssi, rssiAve, signalDelta[mac], deltaTrue),mac)

		if deltaTrue:	# delta signal > xdBm (set param)
			beacon_ExistingHistory[mac]["reason"][-1] = 6 
			composeMSGForThisMacOnly(mac)	
			return True

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30,u"mac:{}\nbeaconsThisReadCycle:{}".format(mac, beaconsThisReadCycle ))

	return False


#################################
def checkIfFastDownForAll():
	global fastDownList, beacon_ExistingHistory, trackMac, logCountTrackMac
	global beaconsThisReadCycle
	global reasonMax 

	try:
	## ----------  check if this is a fast down device
		tt = time.time()
		for beacon in fastDownList:  

			if beacon not in beacon_ExistingHistory: 												continue # not in history never had an UP signal is already gone
			if len(beacon_ExistingHistory[beacon]["timeSt"]) ==0: 									continue #  have not received anything this period, give it a bit more time
			if tt- beacon_ExistingHistory[beacon]["timeSt"][-1] < fastDownList[beacon]["seconds"]: 	continue #  have not received anything this period, give it a bit more time
			if beacon_ExistingHistory[beacon]["fastDown"]: 											continue # already fast down send

			if  (beacon == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("FstDA   ", "set to fastDown Active ", beacon)

			beacon_ExistingHistory[beacon]["reason"][-1] = 3 
			beacon_ExistingHistory[beacon]["fastDown"]	= True
			composeMSGForThisMacOnly(beacon)	
			emptyHistory(beacon)

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30,u"mac {}:  beacon_ExistingHistory={}".format(beacon, beacon_ExistingHistory[beacon]))

	return



#################################, check if signal strength is acceptable for fastdown 
def checkIfNewBeacon(mac):
	global trackMac, logCountTrackMac
	global beacon_ExistingHistory 
	try:
		#U.logger.log(20,u"mac{} checkIfNewBeacon trackMac:{}  logCountTrackMac:{}".format(mac, trackMac, logCountTrackMac))
		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac( "New?  ", "checking if Beacon is back " ,mac)

		if  mac not in beacon_ExistingHistory: return False

		if  len(beacon_ExistingHistory[mac]["timeSt"]) == 0:
			#U.logger.log(30,u"mac{} checkIfNewBeacon empty history={}".format(mac,beacon_ExistingHistory[mac]))
			return False

		if beacon_ExistingHistory[mac]["count"] == 1 or len(beacon_ExistingHistory[mac]["timeSt"]) <2 or time.time() - beacon_ExistingHistory[mac]["timeSt"][-1] > 30  or beacon_ExistingHistory[mac]["fastDown"]:
			if  (mac == trackMac or trackMac == "*") and logCountTrackMac >0:
				writeTrackMac( "New!  ", "beacon is back, send message" ,mac)
			if mac in beacon_ExistingHistory: 
				if mac in fastDownList: 		beacon_ExistingHistory[mac]["reason"][-1] = 4 # beacon_fastdown is back
				else: 							beacon_ExistingHistory[mac]["reason"][-1] = 5 # beacon is back
			else:								beacon_ExistingHistory[mac]["reason"][-1] = 2 # beacon is new
			beacon_ExistingHistory[mac]["fastDown"] = False
			composeMSGForThisMacOnly(mac)
			return True

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
def doSensors( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min):
	global BLEsensorMACs
	bl = ""
	try:

		if mac not in BLEsensorMACs:
			return tx, bl, UUID, Maj, Min, False
 
		if BLEsensorMACs[mac]["type"] == "BLEmyBLUEt":  								
			return domyBlueT( mac, rx, tx, hexData, UUID, Maj, Min)

		if BLEsensorMACs[mac]["type"] == "BLERuuviTag":
			return  doRuuviTag( mac, rx, tx, hexData, UUID, Maj, Min)

		if BLEsensorMACs[mac]["type"].find("BLEiBS") >-1:
			return  doBLEiBSxx( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, BLEsensorMACs[mac]["type"])

		if BLEsensorMACs[mac]["type"].find("BLEminewE8") >-1:
			return  doBLEminewE8( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min)

		if BLEsensorMACs[mac]["type"].find("BLEiSensor") >-1:
			return  doBLEiSensor( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min)


		if BLEsensorMACs[mac]["type"].find("BLESatech") >-1:
			return  doBLESatech( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, BLEsensorMACs[mac]["type"])


	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return tx, bl, UUID, Maj, Min, False

#################################

def doBLEiSensor(mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min):
	global BLEsensorMACs, sensors

	""" format:
- 04 3E 23 02 01 03 00 88 B8 37 22 9A AC   17 02 01 06  09 08 69 53 65 6E 73 6F 72 20  09 FF 00 DB 97 46 43 02 07 04 D4
- 04 3E 23 02 01 03 00 88 B8 37 22 9A AC   17 02 01 06  09 08 69 53 65 6E 73 6F 72 20  09 FF 00 DB 97 46 43 02 08 05 D4
									pos#   01 23 45 67  89 01 23 45 67 89 01 23 45 67  89 01 23 45 67 89 01 23 45 67 
																										 43 00 1D 18 DD;
														    ?  i  S  e  n  s  o  r ?         FW
 																							    devID-- 
 																							    data:    DD = 4= send alive 3= gas sensor
 																							                EV 02 = alarm  (= 0010 = alarm, 1000 = alive )
 																							                    ctrl = 08
  																							                      count= 04..05 ..06 .. 

	"""

	try:
		
		hexData = hexData[12:]
		if len(hexData) < 40: return tx, "", UUID, Maj, Min, False

		#U.logger.log(20,u"doBLEiSensor {}  hexData:{};".format(mac, hexData))
		TagPos 	= hexData.find("02010609086953656E736F722009FF") 
		if TagPos !=2: 	return tx, "", UUID, Maj, Min, False

		UUID 			= "BLEiSensor"
		Maj  			= mac
		sensor			= "BLEiSensor"
		p = 40
		flags 			= int(hexData[p:p+2],16) & 0b00011111
		if    flags == 0b00000000: 	sensorType = "iSensor-undefined"
		elif  flags == 0b00000001:	sensorType = "iSensor-IR-Fence"
		elif  flags == 0b00000010:	sensorType = "iSensor-PIR"
		elif  flags == 0b00000011:	sensorType = "iSensor-Gas"
		elif  flags == 0b00000100:	sensorType = "iSensor-Panic"
		elif  flags == 0b00000101:	sensorType = "iSensor-Smoke"
		elif  flags == 0b00000110:	sensorType = "iSensor-Door"
		elif  flags == 0b00000111:	sensorType = "iSensor-GlasBreak"
		elif  flags == 0b00001000:	sensorType = "iSensor-Vibration"
		elif  flags == 0b00001001:	sensorType = "iSensor-WaterLevel"
		elif  flags == 0b00001010:	sensorType = "iSensor-HighTemp"
		elif  flags == 0b00010110:	sensorType = "iSensor-DoorBell"
		elif  flags == 0b00011001:	sensorType = "iSensor-RemoteKeyFob"
		elif  flags == 0b00011010:	sensorType = "iSensor-WirelessKeypad"
		elif  flags == 0b00011110:	sensorType = "iSensor-WirelessSiren"
		elif  flags == 0b00011111:	sensorType = "iSensor-RemoteSwitch"
		else:						sensorType = "other"
		Min  			= sensorType # is the counter


		flags 			= int(hexData[p:p+2],16) & 0b11100000
		if flags & 0b01000000 != 0:	sendsAlive = True
		else:						sendsAlive = False

		p = 42
		flags 			= int(hexData[p:p+2],16)
		tampered		= flags & 0b00000001 != 0
		onOff			= flags & 0b00000010 != 0
		lowVoltage		= flags & 0b00000100 != 0
		alive			= flags & 0b00001000 != 0
		p = 46
		counter			= int(hexData[p:p+2],16)

		dd={   # the data dict to be send 
				'onOff': 		onOff,
				'alive': 		alive,
				'counter': 		counter,
				'lowVoltage': 	lowVoltage,
				'tampered': 	tampered,
				'sensorType': 	sensorType,
				'sendsAlive': 	sendsAlive,
				"rssi":			int(rx),
			}
		#U.logger.log(20, " .... checking  data:{} counter hex:{}".format( dd , hexData[42:42+5]) )
		deltaTime 			= time.time() - BLEsensorMACs[mac]["lastUpdate"]
		trigTime 			= deltaTime   > BLEsensorMACs[mac]["updateIndigoTiming"]  			# send min every xx secs

		if counter != BLEsensorMACs[mac]["counter"] or trigTime:
			# compose complete message
			U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
			BLEsensorMACs[mac]["lastUpdate"] = time.time()

		# remember last values
		BLEsensorMACs[mac]["onOff"] 		= onOff
		BLEsensorMACs[mac]["alive"] 		= alive
		BLEsensorMACs[mac]["counter"] 		= counter

		return tx, "", UUID, Maj, Min, False

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False




#################################
def doBLEiBSxx( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensorType):
	global BLEsensorMACs
	try:
		HexStr 				= hexData[12:]
		if len(HexStr) < 40: 
			return tx, "", UUID, Maj, Min, False

		posFound, dPos, x, y =  testComplexTag(HexStr, "", mac, macplain, macplainReverse, Maj="", Min="", tagPos=2, tagString="0201061XFFXX008XBC",checkMajMin=False )
		#U.logger.log(20, "mac:{}   posFound:{}, dPos:{}, sensorType:{}, HexStr:{}".format(mac, posFound, dPos, sensorType, HexStr) )	

		if dPos !=0:
			return tx, "", UUID, Maj, Min, False

		sensor				= sensorType
		UUID				= sensor
		Maj					= "sensor"
		devId				= BLEsensorMACs[mac]["devId"]
		Bstring 			= HexStr[22:24]+HexStr[20:22]
		batteryVoltage		= (int(Bstring,16) & 0b0000111111111111)*10 # in mV
		batteryLevel 		= batLevelTempCorrection(batteryVoltage, 20.) # no correction

		data   = {sensor:{devId:{}}}
		data[sensor][devId] ={"batteryVoltage":batteryVoltage,"batteryLevel":batteryLevel,"type":sensorType,"mac":mac,"rssi":float(rx),"txPower":-60}

		# iBS01T:  	02010612FF590080BCbbbbxxFFFFFFFFFFFFFFFFFFFF
		#  			
		# iBS01-G:  02010612FF590080BC   bbbb   xx FFFFFFFFFFFFFFFFFFFF
		# iBS01RG:	02010619FF590081BC   bbbb   xxxxyyyyzzzzxxxxyyyyzzzzxxxxyyyyzzzz
		#                   1 2 3 4 5    6 7    8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
		#      		0       1            2                  3               4
		# pos 		234567890123456789  >0123< >45< >6789< >0123< 4567 >89< 012345
		# bits 		02010612FF0D0083BC   2901   00   4409   4309  0000 >17< 030000
		#                           volt   0/1  
		#testComplexTag(hexstring, tag, mac, macplain, macplainReverse, Maj="", Min="", tagPos="", tagString="" )
		if   HexStr.find("02010619FF0D0081BC") == 2:		subTypeHex 	= "iBS03RG"
		elif HexStr.find("02010619FF590081BC") == 2:		subTypeHex 	= "iBS01RG"
		elif HexStr.find("02010612FF590081BC") == 2:		subTypeHex 	= "iBS01"
		elif HexStr.find("02010612FF0D0083BC") == 2:		subTypeHex 	= "iBS02"
		elif HexStr.find("02010619FF0D0083BC") == 2:		subTypeHex 	= "iBS03"
		elif HexStr.find("02010612FF590080BC") == 2:		subTypeHex 	= "iBS01T"
		elif HexStr.find("02010612FF590080BC") == 2:		subTypeHex 	= "iBS03G"
		else:												subTypeHex  = ""
		hexCode2 	= HexStr[38:40]
		#U.logger.log(20, "mac:{}   subTypeHex:{}; hexCode2:{}".format(mac, subTypeHex, hexCode2 ) )

		AmbientTemperature		= ""
		temp					= "" 
		hum						= ""
		onOff					= "" 
		onOff1					= "" 
		accelerationX			= ""
		accelerationY			= ""
		accelerationZ			= ""
		updateIndigoDeltaAccel 	= ""
		updateIndigoDeltaMaxXYZ = ""

		Trig 				= ""
		if  sensorType in ["BLEiBS01"]: 	# on/off
			p = 24 # start of on/off
			onOff = HexStr[p:p+2]  != "00"
			data[sensor][devId]["onOff"] = onOff
			if BLEsensorMACs[mac]["onOff"] != onOff: Trig += "switch/"
			#U.logger.log(20, "mac:{}   HexStr[p:p+2]:{}, old01:{};  new01:{}".format(mac, HexStr[p:p+2], BLEsensorMACs[mac]["onOff"], onOff ) )

		elif  sensorType == "BLEiBS03G": 	
			p = 24 # start of on/off
			Bstring 			= HexStr[p:p+2]
			iVAL				= int(Bstring,16)
			onOff1				= iVAL &  0b00000100 != 0
			onOff				= iVAL &  0b00000010 != 0
			if BLEsensorMACs[mac]["onOff"]  != onOff: Trig += "switch/"
			data[sensor][devId]["onOff"] = onOff
			if BLEsensorMACs[mac]["onOff1"] != onOff1: Trig += "switch1/"
			data[sensor][devId]["onOff1"] = onOff1

		elif  sensorType == "BLEiBS03T": 	
			p = 26 # start of temp
			temp = ( signedIntfromString16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100. + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
			if abs(BLEsensorMACs[mac]["temp"] - temp) >= BLEsensorMACs[mac]["updateIndigoDeltaTemp"]: Trig +=  "temp/"
			data[sensor][devId]["temp"] 		= temp 
			batteryLevel 						= batLevelTempCorrection(batteryVoltage, temp)
			data[sensor][devId]["batteryLevel"] = batteryLevel


		elif  sensorType == "BLEiBS03TP": 	
			p = 26# start of temp
			temp = (signedIntfromString16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100. + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
			if abs(BLEsensorMACs[mac]["temp"] - temp) >= BLEsensorMACs[mac]["updateIndigoDeltaTemp"]: Trig +=  "temp/"
			data[sensor][devId]["temp"] 		= temp 
			batteryLevel 						= batLevelTempCorrection(batteryVoltage, temp)
			data[sensor][devId]["batteryLevel"] = batteryLevel
			p = 30# start of temp probe
			AmbientTemperature = signedIntfromString16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100.
			if abs(BLEsensorMACs[mac]["AmbientTemperature"] - AmbientTemperature) >=1: Trig +=  "ambient-temp/"
			data[sensor][devId]["AmbientTemperature"] = AmbientTemperature


		elif  sensorType == "BLEiBS01T": 	
			iVAL						 = int(HexStr[24:26],8)
			onOff						 = iVAL &  0b00000001 != 0
			data[sensor][devId]["onOff"] = onOff

			p = 26# start of temp
			temp = (signedIntfromString16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100. + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
			data[sensor][devId]["temp"] 		= temp 

			batteryLevel 						= batLevelTempCorrection(batteryVoltage, temp)
			data[sensor][devId]["batteryLevel"] = batteryLevel

			p = 30# start of hum probe
			hum = signedIntfromString16( HexStr[p+2:p+4] + HexStr[p:p+2] )
			data[sensor][devId]["hum"] = hum

			if abs(BLEsensorMACs[mac]["temp"] - temp) >= 1: Trig +=  "temp/"
			if abs(BLEsensorMACs[mac]["hum"] -   hum) >1 :  Trig +=  "hum/"
			if onOff != BLEsensorMACs[mac]["onOff"] :		Trig +=  "onOff"
			#U.logger.log(20, "mac:{}   Bstring:{}, iVAL:{:016b}, batteryVoltage:{}  onOff:{}, Trig:{}; data:{}".format(mac,Bstring, iVAL,batteryVoltage,  onOff, Trig, data[sensor][devId]) )


		elif  sensorType in["BLEiBS01RG","BLEiBS03RG"]:
			Bstring 			= HexStr[22:24]+HexStr[20:22]
			iVAL				= int(Bstring,16)
			onOff1				= iVAL &  0b0010000000000000 != 0
			onOff				= iVAL &  0b0001000000000000 != 0
			p = 24 + 12 # there are 3 measuremenst send, take the middle 
			#U.logger.log(20, "mac:{}   hex[p]:{} x:{}, y:{},z:{} ".format(mac,hexData[p:], hexData[ p :p+4 ],hexData[ p+4 :p+8 ],hexData[ p+8 :p+12 ]) )
			accelerationX 	= signedIntfromString16(hexData[p+2 :p+4 ]+hexData[p  :p+2 ])*(4) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationY 	= signedIntfromString16(hexData[p+6 :p+8 ]+hexData[p+4:p+6 ])*(4) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationZ 	= signedIntfromString16(hexData[p+10:p+12]+hexData[p+8:p+10])*(4) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)
		# make deltas compared to last send 
			dX 			= abs(BLEsensorMACs[mac]["accelerationX"]		- accelerationX)
			dY 			= abs(BLEsensorMACs[mac]["accelerationY"]		- accelerationY)
			dZ 			= abs(BLEsensorMACs[mac]["accelerationZ"]		- accelerationZ)

			dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
			deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000
			trigAccel 	= dTot			> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"] 	# acceleration change triggers 
			trigDeltaXZY= deltaXYZ		> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]			# acceleration-turn change triggers 
			if trigAccel:    							Trig += "accel/"
			if trigDeltaXZY: 							Trig += "deltaXYZ/"
			if onOff != BLEsensorMACs[mac]["onOff"]:	Trig += "onOff/" 
			data[sensor][devId]["accelerationTotal"] 		= int(accelerationTotal)
			data[sensor][devId]["accelerationX"] 			= int(accelerationX)
			data[sensor][devId]["accelerationY"] 			= int(accelerationY)
			data[sensor][devId]["accelerationZ"] 			= int(accelerationZ)
			data[sensor][devId]["accelerationXYZMaxDelta"]  = int(deltaXYZ)
			data[sensor][devId]["accelerationVectorDelta"]  = int(dTot)
			data[sensor][devId]["onOff"]  					= onOff
			data[sensor][devId]["onOff1"]  					= onOff1
			#U.logger.log(20, "mac:{}   Bstring:{}, iVAL:{:016b}, batteryVoltage:{}  onOff:{}, Trig:{}; data:{}".format(mac,Bstring, iVAL,batteryVoltage,  onOff, Trig, data[sensor][devId]) )

		else:
			return tx, "", UUID, Maj, Min, False

		# check if we should send data to indigo
		deltaTime 			= time.time() - BLEsensorMACs[mac]["lastUpdate"]
		trigTime 			= deltaTime   > BLEsensorMACs[mac]["updateIndigoTiming"]  			# send min every xx secs
		#U.logger.log(20, "mac:{}    HexStr20-23:{}- 24-26{} irOnOff:{}, batteryVoltage:{}".format(mac, HexStr[20:24],  HexStr[24:26], irOnOff, batteryVoltage) )

		#U.logger.log(20, "{}   trigTime:{},  Trig:{}, deltaTime:{};  updateIndigoTiming:{}".format(mac, trigTime, Trig, deltaTime, BLEsensorMACs[mac]["updateIndigoTiming"]) )
		if  trigTime or Trig != "":
			trig = ""
			if trigTime:	 trig  = "Time/"
			elif Trig !="" : trig  += Trig
			data[sensor][devId]["trigger"]  					= trig.strip("/")
			U.sendURL({"sensors":data})
			# save last values to comapre at next round, check if we should send if delta  > paramter
			BLEsensorMACs[mac]["lastUpdate"] 					= time.time()
			BLEsensorMACs[mac]["onOff1"] 	 					= onOff1
			BLEsensorMACs[mac]["onOff"] 	 					= onOff
			BLEsensorMACs[mac]["temp"] 	 	 					= temp
			BLEsensorMACs[mac]["hum"] 	 	 					= hum
			BLEsensorMACs[mac]["AmbientTemperature"] 			= AmbientTemperature
			BLEsensorMACs[mac]["accelerationX"] 				= accelerationX
			BLEsensorMACs[mac]["accelerationY"] 				= accelerationY
			BLEsensorMACs[mac]["accelerationZ"] 				= accelerationZ

		return tx, batteryLevel, sensorType, mac, "sensor", False
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return tx, "", UUID, Maj, Min, False


#################################
def doBLESatech( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensorType):
	global BLEsensorMACs
	"""
Assuming the following BL:E messages (starting directly afetr the reverse MAC #)
HexStr:1A0201060303E1FF1216E1FFA103 5D0000000000F2  DD04BD1DD4F7  B2 #accel
HexStr:180201060303E1FF1016E1FFA104 5D 1A17 3456  DD04BD1DD4F7  AF  # temp
HexStr:180201060303E1FF1016E1FFA108 5D DD04BD1DD4F7 504C5553  AD  # # battery % and PLUS name
HexStr:170201060303AAFE1116AAFE2000 0B6D  1600  000008D4  00000DE8  B7 # gen info
HexStr:0E0201060A09426561636F6E666967

if     HexStr.find("0201060303E1FF1016E1FFA104") == 2:	
	subType 	= "tempHum"
	dataString 	= HexStr.split("0201060303E1FF")[1]
	dataString 	= dataString.split("E1FFA1")[1][2:]
	dataString 	= dataString.split(macplain)[0]
	# == 5D1A173456DD04BD1DD4F7
	p = 0;	batteryLevel 	= int(dataString[p:p+2],16)
	p = 2; 	temp = round(signedIntfromString16(dataString[p :p+4]) /255.,2)
	p = 6;	hum  = round(signedIntfromString16(dataString[p :p+4]) /255.,1)

elif   HexStr.find("0201060303E1FF1216E1FFA103") == 2:	
	subType 	= "accel"
	dataString 	= HexStr.split("0201060303E1FF")[1]
	dataString 	= dataString.split("E1FFA1")[1][2:]
	dataString 	= dataString.split(macplain)[0]
	# == 5D0000000000F2
	p = 2 
	accelerationX 	= signedIntfromString16(dataString[p  :p+4 ]) *4
	accelerationY	= signedIntfromString16(dataString[p+4:p+8 ]) *4
	accelerationZ 	= signedIntfromString16(dataString[p+8:p+12]) *4
	accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)

elif   HexStr.find("0201060303AAFE1116AAFE2000") == 2:	
	subType 	= "genInfo"
	dataString 	= HexStr.split("0201060303AAFE1116AAFE2000")[1]  ## + mV-- C- Cp- adC----- secs-strt"
	# gives: 0B6D1600000008D400000DE8B7
	p = 0; bv	= dataString[p  :p+4];	batteryVoltage 	= int(bv,16)
	p = 4 ;	ct	= dataString[p  :p+4];	chipTemperature	= round(float(int(ct,16))/255.,1)
	p = 8 ;	c	= dataString[p  :p+8];	counter 		= int(c,32)
	p = 16; ss	= dataString[p  :p+8];	secsSinceStart 	= int(ss,32)

elif   HexStr.find("0201060303E1FF0F16E1FFA1FF") == 2:	
	subType 	= "sos"

elif   HexStr.find("0201060A09426561636F6E666967") == 2:	
	subType 	= "Beaconfig" # name msg

elif   HexStr.find("0201060303E1FF1016E1FFA108") == 2:	
	subType 	= "PLUS" # name msg
	dataString 	= HexStr.split("0201060303E1FF1016E1FFA108")[1]  ##  bb mac# "PLUS"
	# 5D         DD04BD1DD4F7   504C5553AD
	# hex bat    MAC #          P L U S 
	p = 0;	batteryLevel 	= int(dataString[p:p+2],16)

	"""

	try:
		HexStr 				= hexData[12:]
		if len(HexStr) < 40: 
			return tx, "", UUID, Maj, Min, False

		devId				= BLEsensorMACs[mac]["devId"]
		sensor				= sensorType

		subType = ""
		if     HexStr.find("0201060303E1FF1016E1FFA104") == 2:	subType 	= "tempHum"
		elif   HexStr.find("0201060303E1FF1216E1FFA103") == 2:	subType 	= "accel"
		elif   HexStr.find("0201060303AAFE1116AAFE2000") == 2:	subType 	= "genInfo"
		elif   HexStr.find("0201060303E1FF0F16E1FFA1FF") == 2:	subType 	= "sos"

		data   = {sensor:{devId:{}}}
		data[sensor][devId] = {"type":sensorType,"mac":mac,"rssi":float(rx),"txPower":-60}

		if BLEsensorMACs[mac]["SOS"] and subType != "sos":
			data[sensor][devId]["trigger"] = "SOS_Off"
			U.sendURL({"sensors":data})
			BLEsensorMACs[mac]["SOS"] 	= False

		if subType == "":
			return tx, "", UUID, Maj, Min, False


		UUID					= sensor
		Maj						= "sensor"
		chipTemperature			= "" 
		temp					= "" 
		hum						= ""
		accelerationX			= ""
		accelerationY			= ""
		accelerationZ			= ""
		updateIndigoDeltaAccel 	= ""
		updateIndigoDeltaMaxXYZ = ""
		batteryLevel			= ""
		batteryVoltage			= ""
		secsSinceStart			= ""
		counter					= ""
		Trig 					= ""
		Trig1 					= ""
		Trig2 					= ""


		if  subType == "sos": 	
			#U.logger.log(20, "mac:{}   sos:  HexStr:{}".format(mac, HexStr[2:] ) )	
			if  not  BLEsensorMACs[mac]["SOS"]:
				data[sensor][devId]["trigger"] = "SOS_button_pressed@"+datetime.datetime.now().strftime("%Y-%m%d-%H:%M:%S")
				U.sendURL({"sensors":data})
			BLEsensorMACs[mac]["SOS"] 	= True
			return tx, "", UUID, Maj, Min, False


		elif  subType == "genInfo": 	
			dataString 	= HexStr.split("0201060303AAFE1116AAFE2000")[1]  ## + mV-- C- Cp- adC----- secs-strt"
			p = 0; bv	= dataString[p  :p+4];	batteryVoltage 	= int(bv,16)
			p = 4 ;	ct	= dataString[p  :p+4];	chipTemperature	= round(float(int(ct,16))/255.,1)
			p = 8 ;	c	= dataString[p  :p+8];	counter 		= int(c,32)
			p = 16; ss	= dataString[p  :p+8];	secsSinceStart 	= int(ss,32)

			data[sensor][devId]["chipTemperature"] 	= chipTemperature 
			data[sensor][devId]["secsSinceStart"] 	= secsSinceStart 
			data[sensor][devId]["counter"] 			= counter 
			data[sensor][devId]["batteryVoltage"] 	= batteryVoltage
			trigTime2 			= time.time() - BLEsensorMACs[mac]["lastUpdate2"]   > BLEsensorMACs[mac]["updateIndigoTiming"]			# send min every xx secs
			if  trigTime2 or Trig2 != "":
				trig = ""
				if trigTime2: 	  trig  = "Time/"
				elif Trig2 != "": trig  += Trig2
				data[sensor][devId]["trigger"]  					= trig.strip("/")
				U.sendURL({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac]["lastUpdate2"] 					= time.time()
				BLEsensorMACs[mac]["chipTemperature"] 	 	 		= chipTemperature
				BLEsensorMACs[mac]["secsSinceStart"] 	 	 		= secsSinceStart
				BLEsensorMACs[mac]["counter"] 	 	 				= counter
				BLEsensorMACs[mac]["batteryVoltage"] 	 	 		= batteryVoltage

		elif  subType == "tempHum": 	
			dataString 	= HexStr.split("0201060303E1FF")[1]
			dataString 	= dataString.split("E1FFA1")[1][2:]
			dataString 	= dataString.split(macplain)[0]
			p = 2; 	temp = round(signedIntfromString16(dataString[p :p+4]) /255.,2)
			p = 6;	hum  = round(signedIntfromString16(dataString[p :p+4]) /255.,1)
			if abs(BLEsensorMACs[mac]["temp"] - temp) >= BLEsensorMACs[mac]["updateIndigoDeltaTemp"]: 	Trig1 +=  "temp/"
			if abs(BLEsensorMACs[mac]["hum"] - hum)   >= 2: 											Trig1 +=  "hum/"
			batteryLevel 	= int(dataString[0:2],16)
			data[sensor][devId]["temp"] 		= temp 
			data[sensor][devId]["hum"] 			= hum 
			data[sensor][devId]["batteryLevel"] = batteryLevel

			trigTime1 			= time.time() - BLEsensorMACs[mac]["lastUpdate1"]   > BLEsensorMACs[mac]["updateIndigoTiming"]			# send min every xx secs
			if  trigTime1 or Trig1 != "":
				trig = ""
				if trigTime1: 	  trig  = "Time/"
				elif Trig1 != "": trig  += Trig1
				data[sensor][devId]["trigger"]  					= trig.strip("/")
				U.sendURL({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac]["lastUpdate1"] 					= time.time()
				BLEsensorMACs[mac]["temp"] 	 	 					= temp
				BLEsensorMACs[mac]["hum"] 	 	 					= hum

		elif  subType  == "accel":
			dataString 	= HexStr.split("0201060303E1FF")[1]
			dataString 	= dataString.split("E1FFA1")[1][2:]
			dataString 	= dataString.split(macplain)[0]
			p = 2 
			accelerationX 	= signedIntfromString16(dataString[p  :p+4 ]) *4
			accelerationY	= signedIntfromString16(dataString[p+4:p+8 ]) *4
			accelerationZ 	= signedIntfromString16(dataString[p+8:p+12]) *4
			accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)
		# make deltas compared to last send 
			dX 			= abs(BLEsensorMACs[mac]["accelerationX"]		- accelerationX)
			dY 			= abs(BLEsensorMACs[mac]["accelerationY"]		- accelerationY)
			dZ 			= abs(BLEsensorMACs[mac]["accelerationZ"]		- accelerationZ)

			dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
			deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000
			trigAccel 	= dTot			> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"] 	# acceleration change triggers 
			trigDeltaXZY= deltaXYZ		> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]			# acceleration-turn change triggers 
			if trigAccel:    							Trig += "accel/"
			if trigDeltaXZY: 							Trig += "deltaXYZ/"
			data[sensor][devId]["accelerationTotal"] 		= int(accelerationTotal)
			data[sensor][devId]["accelerationX"] 			= int(accelerationX)
			data[sensor][devId]["accelerationY"] 			= int(accelerationY)
			data[sensor][devId]["accelerationZ"] 			= int(accelerationZ)
			data[sensor][devId]["accelerationXYZMaxDelta"]  = int(deltaXYZ)
			data[sensor][devId]["accelerationVectorDelta"]  = int(dTot)

			trigTime 			= time.time() - BLEsensorMACs[mac]["lastUpdate"]   > BLEsensorMACs[mac]["updateIndigoTiming"]# send min every xx secs
			if  trigTime or Trig != "":
				trig = ""
				if trigTime:	 trig  = "Time/"
				elif Trig != "": trig  += Trig
				data[sensor][devId]["trigger"]  					= trig.strip("/")
				U.sendURL({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac]["lastUpdate"] 					= time.time()
				BLEsensorMACs[mac]["accelerationX"] 				= accelerationX
				BLEsensorMACs[mac]["accelerationY"] 				= accelerationY
				BLEsensorMACs[mac]["accelerationZ"] 				= accelerationZ

		return tx, batteryLevel, sensorType, mac, "sensor", False


	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return tx, "", UUID, Maj, Min, False


#################################
def batLevelTempCorrection(batteryVoltage, temp):
	try:
		battreyLowVsTemp			= (1. + min(0,temp-10)/100.) * 2900 # (changes to 0.9* 2900 @ 0C; to = 0.8*2900 @-10C )
		batteryLevel 				= int(min(100,max(0,100* (batteryVoltage - battreyLowVsTemp)/(3100.-battreyLowVsTemp))))
		return batteryLevel
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 0

#################################
def domyBlueT( mac, rx, tx, hexData, UUID, Maj, Min):
	global BLEsensorMACs
	try:
		if len(hexData) < 55:
			return tx, "", UUID, Maj, Min, True
		UUID = hexData[12:40]
		Maj	 = str(int(hexData[40:44],16))
		Min	 = str(int(hexData[44:48],16))
		RawData = hexData[48:48+6] # get bytes # 31,32,33	 (starts at # 0 , #33 has sign, if !=0 subtract 2**15
		RawData = [int(RawData[0],16), int(RawData[1],16), int(RawData[2],16)]
		#RawData = list(struct.unpack("BBB", pkt[31:34])) # get bytes # 31,32,33	 (starts at # 0 , #33 has sign, if !=0 subtract 2**15
		if RawData[2] != 0: tSign = 0x10000 # == 65536 == 2<<15
		else:				tSign = 0
		r8				= RawData[1] << 8 
		sensorData		= ( r8 + RawData[0] - tSign ) /100.
		sensor			= "BLEmyBlueT"
		devId			= BLEsensorMACs[mac]["devId"]
		try:	temp  	= (sensorData + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
		except: temp  	= sensorData
		#U.logger.log(20, "{}   RX:{}; TX:{}; temp:{}".format(mac, rx, tx, temp) )
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
## minew E8 ########################
#################################
def doBLEminewE8(mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min):
	global BLEsensorMACs, sensors

	""" format:

hexData:1A0201060303E1FF1216E1FFA103640005FFFB01004B80A33F23ACEC; x:0005 y:FFFB, z:0100
        1A0201060303E1FF1216E1FFA103640005FFFEFF064B80A33F23ACCE
        1A0201060303E1FF1216E1FFA103XXXXXXXXXXXXXXRMAC########"
   pos: 012345678911234567892123456789312345678941234567895123
                                    BB  = Battery
                                      xxxx = x accelt 			here: 0005 =  0.05G
                                          yyyy = y accelt		here: FFFE = -0.01 
                                              zzzz = z accelt	here: 064B = 1.611
		accel: 0x0000 = 0
		accel: 0xFFFE = -0.01
		accel: 0x00FD = 0.98 g
	"""

	try:
		
		hexData = hexData[12:]
		if len(hexData) < 54: 							return tx, "", UUID, Maj, Min, False

		#U.logger.log(20,u"doBLEminewE8 {}  hexData:{}; x:{} y:{}, z:{}".format(mac, hexData, hexData[30:34], hexData[34:38], hexData[38:42]))


		TagPos 	= hexData.find("1A0201060303E1FF1216E1FFA103") 
		if TagPos !=0: 									return tx, "", UUID, Maj, Min, False
		#U.logger.log(20,u"doBLEminewE8 {}  2".format(mac))

		UUID 						= "BLEminewE8"
		Maj  						= mac
		Min  						= "sensor"
		sensor 						= "BLEminewE8"


		# unpack  rest of sensor data 
		p = 30
		accelerationX 	= signedIntfromString16(hexData[ p :p+4 ])*(10./2.45) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
		accelerationY 	= signedIntfromString16(hexData[p+4:p+8 ])*(10./2.45)
		accelerationZ 	= signedIntfromString16(hexData[p+8:p+12])*(10./2.45)
		accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)
		batteryLevel	= int(hexData[28:30],16)

		# make deltas compared to last send 
		dX 			= abs(BLEsensorMACs[mac]["accelerationX"]		- accelerationX)
		dY 			= abs(BLEsensorMACs[mac]["accelerationY"]		- accelerationY)
		dZ 			= abs(BLEsensorMACs[mac]["accelerationZ"]		- accelerationZ)

		dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
		deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000

		deltaTime 	= time.time() - BLEsensorMACs[mac]["lastUpdate"]

		# check if we should send data to indigo
		trigMinTime	= deltaTime 	> BLEsensorMACs[mac]["minSendDelta"] 				# dont send too often
		trigTime 	= deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"]  			# send min every xx secs
		trigAccel 	= dTot			> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"] 	# acceleration change triggers 
		trigDeltaXZY= deltaXYZ		> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]			# acceleration-turn change triggers 
		trig = ""
		if trigTime:		trig += "Time/"
		else:
			if trigAccel:	trig += "Accel-Total/"
			if trigDeltaXZY:trig += "Accel-Max-xyz/"
		#U.logger.log(20, "mac:{}    trigMinTime:{} deltaXYZ:{}, trig:{}".format(mac, trigMinTime, deltaXYZ, trig) )

		if trigMinTime and	( trigTime or trigAccel or trigDeltaXZY ):
			dd={   # the data dict to be send 
				'accelerationTotal': 	int(accelerationTotal),
				'accelerationX': 		int(accelerationX),
				'accelerationY': 		int(accelerationY),
				'accelerationZ': 		int(accelerationZ),
				'accelerationXYZMaxDelta':int(deltaXYZ),
				'accelerationVectorDelta':int(dTot),
				'batteryLevel': 		int(batteryLevel),
				'trigger': 				trig.strip("/"),
				"rssi":					int(rx),
			}
			#U.logger.log(20, " .... sending  data:{}".format( dd ) )

			## compose complete message
			U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

			# remember last values
			BLEsensorMACs[mac]["lastUpdate"] 			= time.time()
			BLEsensorMACs[mac]["accelerationX"] 		= accelerationX
			BLEsensorMACs[mac]["accelerationY"] 		= accelerationY
			BLEsensorMACs[mac]["accelerationZ"] 		= accelerationZ
		return tx, batteryLevel, UUID, Maj, Min, False

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False



#################################
#################################
## Ruuvi ########################
#################################
def doRuuviTag( mac, rx, tx, hexData, UUID, Maj, Min):
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
		
		if len(hexData) < 44: 	return tx, "", UUID, Maj, Min, False

		ruuviTagPos 	= hexData.find("FF990405") 
		tagFound	= ruuviTagPos > 20 and ruuviTagPos < 24 
		if not tagFound: 		return tx, "", UUID, Maj, Min, False

		UUID 						= "ruuviTag"
		Maj  						= mac
		Min  						= "sensor"
		sensor 						= "BLERuuviTag"
		# make data into right format (bytes)
		byte_data 					= bytearray.fromhex(hexData[ruuviTagPos + 6:])
		# umpack the first set of data


		# sensor is active, get all data and send if conditions ok

		# unpack  rest of sensor data 
		accelerationTotal, accelerationX, accelerationY, accelerationZ 	= doRuuviTag_magValues(byte_data)
		temp 					= (doRuuviTag_temperature(byte_data)+ BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
		batteryVoltage, txPower = doRuuviTag_powerinfo(byte_data)
		batteryLevel 			= batLevelTempCorrection(batteryVoltage, temp)
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

## Ruuvi  END   #################
#################################



#################################
## BLE Sensors  END   ###########
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
		writeTrackMac("        ","\nTRACKMAC started on pi#:{}, for MAC# {}".format(G.myPiNumber, trackMac), trackMac+"\n")
		startTimeTrackMac = time.time() + 30
		subprocess.call("rm {}temp/beaconloop.trackmac".format(G.homeDir), shell=True)
		subprocess.call("rm {}temp/trackmac.log".format(G.homeDir), shell=True)
		logCountTrackMac = nLogMgsTrackMac
		if trackMac =="*": logCountTrackMac *=3
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


#################################
def trackMacStopIf(hexstr, mac):
	global logCountTrackMac, trackMac, nLogMgsTrackMac, startTimeTrackMac, trackMacText
	try:

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac > 0:
			logCountTrackMac -= 1
			writeTrackMac("RAW===  ",  "{};  count: {}; time left:{:3.0f}; hex: {}".format( datetime.datetime.now().strftime("%H:%M:%S.%f")[:-5], logCountTrackMac,  (startTimeTrackMac -time.time()), hexstr) ,mac)
			
		if logCountTrackMac == 0 or (startTimeTrackMac >0 and time.time() > startTimeTrackMac):
			writeTrackMac("END     ","FINISHed TRACKMAC logging ===", trackMac)
			logCountTrackMac  = -10
			startTimeTrackMac = 0
			trackMac = ""
			U.sendURL(data={"trackMac":trackMacText}, squeeze=False)

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

		dataCollectionTime = 25 # secs 


		f = open(G.homeDir+"temp/beaconloop.BLEAnalysis","r")
		rssiCutoff = f.read().strip("\n")
		f.close()
		subprocess.call("rm {}temp/beaconloop.BLEAnalysis".format(G.homeDir), shell=True)
		rssiCutoff = int(rssiCutoff)

		bluetoothctl = False
		lescanData	 = False

		## init, set dict and delete old files
		MACs={}
		subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/lescan.data > /dev/null 2>&1 ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/hcidump.data > /dev/null 2>&1 ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/hcidump.temp > /dev/null 2>&1 ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/bluetoothctl.data > /dev/null 2>&1 ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/BLEAnalysis-new.json > /dev/null 2>&1 ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/BLEAnalysis-existing.json > /dev/null 2>&1 ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		subprocess.Popen("sudo rm "+G.homeDir+"temp/BLEAnalysis-rejected.json > /dev/null 2>&1 ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

		stopHCUIDUMPlistener()
		U.killOldPgm(-1,"hcidump")
		U.killOldPgm(-1,"hcitool")
		U.killOldPgm(-1,"lescan")

		## now listen to BLE
		starttime = time.time()
		U.logger.log(20, u"starting  BLEAnalysis, rssi cutoff= {}[dBm]".format(rssiCutoff))
		U.logger.log(20, u"sudo hciconfig {} reset".format(hci))
		subprocess.Popen("sudo hciconfig "+hci+" reset", shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20, "sudo timeout -s SIGINT "+str(dataCollectionTime)+"s hcitool -i "+hci+" lescan  ")
		subprocess.Popen("sudo timeout -s SIGINT "+str(dataCollectionTime)+"s hcitool -i "+hci+" lescan  > "+G.homeDir+"temp/lescan.data &", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		time.sleep(0.3)
		U.logger.log(20, "sudo timeout -s SIGINT "+str(dataCollectionTime)+"s hcidump -i "+hci+" --raw  | sed -e :a -e '$!N;s/\\n  //;ta' -e 'P;D'")
		subprocess.Popen("sudo timeout -s SIGINT "+str(dataCollectionTime)+"s hcidump -i "+hci+" --raw  | sed -e :a -e '$!N;s/\\n  //;ta' -e 'P;D' > "+G.homeDir+"temp/hcidump.data &", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		time.sleep(dataCollectionTime)

		if bluetoothctl:
			U.logger.log(20, "sudo timeout -s SIGINT "+str(dataCollectionTime)+"s bluetoothctl scan on")
			subprocess.Popen("sudo timeout -s SIGINT "+str(dataCollectionTime)+"s bluetoothctl scan on > "+G.homeDir+"temp/bluetoothctl.data &", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			time.sleep(dataCollectionTime+.1)
		U.logger.log(20, "prep done; after@: {:.1f} secs".format(time.time()-starttime))
		subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)


		out = []

		###### analyse output  #######
		if bluetoothctl: # bluetoothctl
			f = open(G.homeDir+"temp/bluetoothctl.data","r")
			xxx = f.read()
			f.close()
			DeviceFound = False
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
						MACs[mac] = {"max_rssi":-99, "max_TX": -99,"MSG_in_10Secs": 0,"mfg_info":"","n_of_MSG_Types":0, "typeOfBeacon":[],"typeOfBeacon-msg#":[],"raw_data":[],"pos_of_MAC_in_UUID":[],"pos_of_reverse_MAC_in_UUID":[], "possible_knownTag_options":[]}
					try:	MACs[mac]["max_rssi"] = max(MACs[mac]["max_rssi"],int(items[1]))
					except: pass
				else:
					items = data.split(" ")
					#print mac, items
					if mac not in MACs: 
						linesDevices +=1
						MACs[mac] = {"max_rssi":-99, "max_TX": -99,"MSG_in_10Secs": 0,"mfg_info":"","n_of_MSG_Types":0, "typeOfBeacon":[],"typeOfBeacon-msg#":[],"raw_data":[],"pos_of_MAC_in_UUID":[],"pos_of_reverse_MAC_in_UUID":[], "possible_knownTag_options":[]}
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
				max_TX = -99
				linesIn +=1
				if len(line) < 60: 		continue
				if line.find(">") ==-1: continue
				linesAccepted +=1
				line = line[2:].strip()
				items = line.split()
				mac = (items[7:13])[::-1]
				mac = ":".join(mac)
				#U.logger.log(20, " line:{}".format(line))
				hexString = (line.replace(" ",""))[14+12:]
				##U.logger.log(20, "mac:{};   hexstr:{} ".format(mac, hexString ))
				parsedData = parsePackage(mac, hexString, logData=False)
				#if mac =="DD:33:0A:11:15:E3": print "hcidump found DD:33:0A:11:15:E3", line
				if mac not in MACs: 
					MACs[mac] = {"max_rssi":-99, "max_TX": -99,"MSG_in_10Secs": 0,"mfg_info":"","iBeacon":"","n_of_MSG_Types":0,"typeOfBeacon":[],"typeOfBeacon-msg#":[],"raw_data":[],"pos_of_MAC_in_UUID":[],"pos_of_reverse_MAC_in_UUID":[], "possible_knownTag_options":[]}
				present = False

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

				if "mfg_info" in parsedData:
					MACs[mac]["mfg_info"] = parsedData["mfg_info"]
				if "iBeacon" in parsedData:
					MACs[mac]["iBeacon"] = parsedData["iBeacon"]
				if "TxPowerLevel" in parsedData:
					try:
						tx = signedIntfromString(parsedData["TxPowerLevel"])
						MACs[mac]["max_TX"] = max(MACs[mac]["max_TX"],tx )
					except: pass
				#print mac, "present:>{}<".format(line[2:-3])
				try: 
					if MACs[mac]["max_TX"]  == -99:
						max_TX 	= max(MACs[mac]["max_TX"],   signedIntfromString(line[-5:-3]))
				except: pass
				rssi 	    = max(MACs[mac]["max_rssi"], signedIntfromString(line[-2:]))
					
				MACs[mac]["MSG_in_10Secs"] +=1
				MACs[mac]["max_rssi"] 		= rssi
				MACs[mac]["max_TX"] 		= max_TX
			out+= "\nhcidump\n" 
			out+= xxx
			U.logger.log(20, "finished  hcidump:     lines -in: {:4d}, accepted: {:4d},  n-devices: {:4d}".format(linesIn,linesAccepted,linesDevices ))

		if lescanData: # 
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
						MACs[mac] = {"max_rssi":-99, "max_TX": -99,"MSG_in_10Secs": 0,"mfg_info":"","n_of_MSG_Types":0,"typeOfBeacon":[],"typeOfBeacon-msg#":[],"raw_data":[],"pos_of_MAC_in_UUID":[],"pos_of_reverse_MAC_in_UUID":[], "possible_knownTag_options":[]}
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
					knownMACS[mac]["possible_knownTag_options"].append('"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","useOnlyThisTagToAcceptBeaconMsgDefault": 1, "pos": 12,"posDelta": 0,"tag":"'+hexStr[12:-3]+'"}')
					knownMACS[mac]["typeOfBeacon"].append("")
					knownMACS[mac]["typeOfBeacon-msg#"].append(nmsg)
					knownMACS[mac]["pos_of_MAC_in_UUID"].append(macPos)
					knownMACS[mac]["pos_of_reverse_MAC_in_UUID"].append(RmacPos)
					knownMACS[mac]["n_of_MSG_Types"] = nmsg

					tag = "other"
					knownMACS[mac]["typeOfBeacon"][-1] = tag
					knownMACS[mac]["typeOfBeacon-msg#"][-1] = nmsg
					knownMACS[mac]["possible_knownTag_options"][-1]= " use: "+tag
					for tag in knownBeaconTags:
						if tag == "other": continue
						#U.logger.log(20, "tag: {} ".format(tag)) 
						posFound, dPostest, Maj, Min = testComplexTag(hexStr[12:-2], tag, mac, mac.replace(":",""), hexStr[0:12],"","")
						if posFound != -1:
							knownMACS[mac]["typeOfBeacon"][-1] = tag
							knownMACS[mac]["typeOfBeacon-msg#"][-1] = nmsg
							knownMACS[mac]["possible_knownTag_options"][-1]= " use: "+tag
							break
							
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
					newMACs[mac]["possible_knownTag_options"].append('"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","useOnlyThisTagToAcceptBeaconMsgDefault": 1, "pos": 12,"posDelta": 0,"tag":"'+hexStr[12:-3]+'"}')
					newMACs[mac]["typeOfBeacon"].append("")
					newMACs[mac]["typeOfBeacon-msg#"].append(nmsg)
					newMACs[mac]["pos_of_MAC_in_UUID"].append(macPos)
					newMACs[mac]["pos_of_reverse_MAC_in_UUID"].append(RmacPos)
					newMACs[mac]["n_of_MSG_Types"] = nmsg
					if macPos >-1: 	
						newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","useOnlyThisTagToAcceptBeaconMsgDefault": 1, "pos": 12,"posDelta": 0,"tag":"'+hexStr[12:macPos]+'MAC#########"}'
					elif RmacPos >-1: 	
						newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","useOnlyThisTagToAcceptBeaconMsgDefault": 1, "pos": 12,"posDelta": 0,"tag":"'+hexStr[12:RmacPos]+'RMAC########"}'

					tag = "other"
					newMACs[mac]["typeOfBeacon"][-1] = tag
					newMACs[mac]["typeOfBeacon-msg#"][-1] = nmsg
					newMACs[mac]["possible_knownTag_options"][-1]= " use: "+tag
					for tag in knownBeaconTags:
						if tag == "other": continue
						posFound, dPostest, Maj, Min  = testComplexTag(hexStr[12:-2], tag, mac, mac.replace(":",""), hexStr[0:12], "", "" )
						if posFound != -1:
							newMACs[mac]["typeOfBeacon"][-1] = tag
							newMACs[mac]["typeOfBeacon-msg#"][-1] = nmsg
							newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","useOnlyThisTagToAcceptBeaconMsgDefault": 1, "pos": '+str(posFound)+',"posDelta": 0,"tag":"'+hexStr[12:-3]+'"}'
							newMACs[mac]["pos_of_MAC_in_UUID"][-1] = macPos
							newMACs[mac]["pos_of_reverse_MAC_in_UUID"][-1] = RmacPos
							if macPos >-1: 	
								newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","useOnlyThisTagToAcceptBeaconMsgDefault": 1, "pos": '+str(posFound)+',"posDelta": 0,"tag":"'+hexStr[12:macPos]+'MAC#########"}'
							if RmacPos >-1: 	
								newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","useOnlyThisTagToAcceptBeaconMsgDefault": 1, "pos": '+str(posFound)+',"posDelta": 0,"tag":"'+hexStr[12:RmacPos]+'RMAC########"}'
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




#################################
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
# hexstring starts after mac#
###

def testComplexTag(hexstring, tag, mac, macplain, macplainReverse, Maj="", Min="", tagPos="", tagString="",checkMajMin=True ):
	global knownBeaconTags, logCountTrackMac, trackMac
	try:
		inputString = copy.copy(hexstring)
		if tag != ""		: tagPos 		= int(knownBeaconTags[tag]["pos"])
		if tagString == ""	: tagString 	= knownBeaconTags[tag]["hexCode"].upper()

		if tagString.find("-") >-1: # 
			tagString = tagString[:-1]
		lTag = len(tagString)
		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			if tag == "":
				writeTrackMac("tst-0   ","tagPos:{}; lTag:{} tagString: {}; ".format(tagPos, lTag, tagString ), mac)
			else:
				writeTrackMac("tst-0   ","tagPos:{}; lTag:{}, tag:{}; tagString: {}; ".format(tagPos, lTag, tag, tagString ), mac)

		if tagString.find("X") >-1:
			indexes = [n for n, v in enumerate(tagString) if v == 'X'] 
			inputString 	= list(inputString.upper())
			#writeTrackMac("tag-0   ","indexes:{}".format(indexes), mac)
			for ii in indexes:
				if ii+tagPos < len(inputString):
					inputString[ii+tagPos] = "X"
				else: return -1, 100, Maj, Min
			inputString = ("").join(inputString)

		if tagString.find("RMAC########") >-1:
			tagString = tagString.replace("RMAC########", macplainReverse)

		elif tagString.find("MAC#########") >-1:
			tagString = tagString.replace("MAC#########", macplain)

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tst-1   ","tagString   fin: {}".format(tagString), mac)
			writeTrackMac("tst-2   ","inputString tst: {}".format(inputString), mac)

		posFound 	= inputString.find(tagString)
		dPos 		= posFound - tagPos

		if len(inputString) < lTag + tagPos: posFound =-1; dPos = 100

		if checkMajMin and dPos ==0: 
			if knownBeaconTags[tag]["Maj"].find("UUID:") >-1:
				MPos= knownBeaconTags[tag]["Maj"].split(":")[1].split("-")
				#U.logger.log(20,u"Maj:{}, Mpos:{}".format(knownBeaconTags[tag]["Maj"],MPos))
				Maj = "{}".format(int(hexstring[int(MPos[0]):int(MPos[1])],16))
				
			if knownBeaconTags[tag]["Min"].find("UUID:")>-1:
				MPos= knownBeaconTags[tag]["Min"].split(":")[1].split("-")
				#U.logger.log(20,u"Min:{}, Mpos:{}".format(knownBeaconTags[tag]["Min"],MPos))
				Min = "{}".format(int(hexstring[int(MPos[0]):int(MPos[1])],16))
			

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("tst-F   ","posFound: {}, dPos: {}, tag: {}, tagString: {}".format(posFound, dPos, tag, tagString), mac)

		return posFound, dPos, Maj, Min
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30,u"Mac#:{}".format(mac))
	return -1,100, Maj, Min


#################################
def parsePackage(mac, hexstring, logData=False): # hexstring starts after mac#

	global typeHexToString 
	try:
		typeHexToString = {
			"01":"Flags",
			"02":"IncompleteListof16-bitServiceClassUUIDs",
			"03":"CompleteListof16-bitServiceClassUUIDs",
			"04":"IncompleteListof32-bitServiceClassUUIDs",
			"05":"IncompleteListof32-bitServiceClassUUIDs",
			"06":"IncompleteListof128-bitServiceClassUUIDs",
			"07":"CompleteListof128-bitServiceClassUUIDs",
			"08":"ShortName",
			"09":"Name",
			"0A":"TxPowerLevel",
			"10":"DeviceID",
			"12":"SlaveConnectionIntervalRange", 
			"16":"ServiceData", 
			"19":"Appearance", 
			"1A":"AdvertisingInterval",
			"1B":"DeviceAddress",
			"20":"ServiceData-32-bitUUID",
			"21":"ServiceData-128-bitUUID",
			"FF":"UUID",
			}
		totalLength = int(hexstring[0:2],16)
		if totalLength < 6: return {}
		retData = {}
		retData["len"] = totalLength
		result =[]
		p = 0
		lenP = 0
		if ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
				writeTrackMac("pars0   ","totalLength:{}; hexstring: {}; ".format(totalLength,  hexstring ), mac)
		for ii in range(8):
			p = p+2 + lenP*2
			if p > totalLength*2: break
			try: lenP  = int(hexstring[p:p+2],16)
			except: continue

			if lenP > 2: 
				typeP = hexstring[p+2:p+4]
				result.append({})
				result[-1]["len"] = lenP
				if typeP in typeHexToString:
					result[-1]["type"] = typeHexToString[typeP]

				else: 
					result[-1]["type"] = "unknown:"+typeP

				res = hexstring[p+4: p+4 + lenP*2 -2]

				if result[-1]["type"] in  ["Name","ShortName"]:
					dd = ""
					ll = int(len(res)/2)
					for ii in range(ll):
						x = res[ii*2:ii*2+2]
						if x == "00": continue
						dd +=x.decode("hex") 
					if  logData or ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
						writeTrackMac("parsM   ","res:{}, dd:{}, ll:{}".format( res, dd, ll ), mac)

					result[-1]["data"] = dd
					retData["mfg_info"] = result[-1]["data"]

				elif result[-1]["type"] in  ["UUID"]:
					if res[0:8] =="4C000215":
						try:
							uuidEnd = 8+2*16
							iBeacon = res[8:uuidEnd] +"-"+str(int(res[uuidEnd:uuidEnd+4],16)) +"-"+str(int(res[uuidEnd+4:uuidEnd+4+4],16))
							result[-1]["data"] = "iBeacon:"+iBeacon
							retData["iBeacon"] = iBeacon
						except:
							continue
					else:
						result[-1]["data"] = "UUID:"+res[8:]
						retData["UUID"] = res[8:]

				elif result[-1]["type"] in  ["ServiceData"]:
					result[-1]["ServiceData"] = res
					retData["ServiceData"] = res

				else:					
					result[-1]["data"] = res
					retData[result[-1]["type"]] = res
				rest = hexstring[p+2 + lenP*2:]
				if  ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
						writeTrackMac("parsT   "," p:{:2d}, typeP:{},  result:{}, rest:{}".format( p, typeP, result[-1], rest), mac)
		if  ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
			writeTrackMac("parsE   "," lenTotal:{}, data:{}, hexstr:{}".format( totalLength, retData, hexstring), mac)
		return 	retData	
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30,u" hexstr:{}".format(hexstring))
	return retData



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
def checkForBatteryInfo( tag, tagFound, mac, hexstr ):
	global knownBeaconTags
	global trackMac, logCountTrackMac
	try:
		bl = ""
		if tag in knownBeaconTags and tagFound == "found":
			if type(knownBeaconTags[tag]["battCmd"]) != type({}) and knownBeaconTags[tag]["battCmd"].find("msg:") >-1:
				# parameter format:     "battCmd": "msg:pos=-3,norm=255", 
				try:
					params	=  knownBeaconTags[tag]["battCmd"]
					params	= params.split("msg:")[1]
					if mac == trackMac and logCountTrackMac >0:
						writeTrackMac("Bat-1   ","params:{}".format(params), mac )
					params	= params.split(",")
					par = {}
					for item in params:
						ii = item.split("=")
						par[ii[0]]= ii[1]
					if mac == trackMac and logCountTrackMac >0:
						writeTrackMac("Bat-1   ","params:{}, par-split:{}".format(params, par), mac )

					batPos	= int(par["pos"])*2
					norm	= float(par["norm"])
					try:	length	= int(par["len"])
					except:	length  = 1
					try:	reverse	= int(par["reverse"]) == 1
					except:	reverse = False

					batHexStr = hexstr[12:]
					Bstring =  batHexStr[batPos:batPos+length*2]
					if reverse:
 						Bstring = Bstring[2:4]+Bstring[0:2]
					bl	 	= 100.* int(Bstring,16)/norm
					if mac == trackMac and logCountTrackMac >0:
						writeTrackMac("Bat-2   ", "batpos:{}, hex:{}, norm:{}, length:{}, reverse:{}; bl:{}".format(batPos, Bstring, norm, length, reverse, bl),  mac )
				except	Exception, e:
					if mac == trackMac and logCountTrackMac >0:
						writeTrackMac("        ", u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), mac)
					bl	= ""

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return bl



#################################
def checkIfTagged(mac, macplain, macplainReverse, UUID, Min, Maj, isOnlySensor, hexstr, batteryLevel, rssi, txPower):
	global trackMac, logCountTrackMac, onlyTheseMAC, knownBeaconTags
	global beaconNew, beacon_ExistingHistory, ignoreMAC
	try:
		prio  				= -1
		dPos  				= -100
		UUID1 				= ""
		tagFound 			= "notTested"
		rejectThisMessage 	= True
		mfg_info			= ""
		iBeacon				= ""
		typeOfBeacon		= "other"

		try: parsedData = parsePackage(mac, hexstr[12:], logData=False)
		except:
			return True
		if "iBeacon" in parsedData: iBeacon = parsedData["iBeacon"]
		else:						iBeacon = ""
		if "mfg_info" in parsedData:mfg_info = parsedData["mfg_info"]
		else:						mfg_info = ""
		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("parse   ", "parsedData {}".format(parsedData), mac)

		setEmptybeaconsThisReadCycle(mac)

		### is this a know beacon with a known tag ?
		rejectThisMessage 	= True
		tagFound 			= "failed"
		if mac in onlyTheseMAC:  
			tag 			= onlyTheseMAC[mac]["typeOfBeacon"]
			useOnlyIfTagged = onlyTheseMAC[mac]["useOnlyIfTagged"] # this is from props, device edit setiings, overwrites default

			if useOnlyIfTagged == 0: 
				rejectThisMessage = False

			if tag != "":
				if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
					writeTrackMac("tag-1   ", "tag:{}, useOnlyIfTagged: {}".format(tag, useOnlyIfTagged), mac)
				# right message format, if yes us main UUID
				if  tag in knownBeaconTags:
					UUID1 	= tag
					UUID 	= UUID1
					posFound, dPos, Maj, Min = testComplexTag(hexstr[12:-2], tag, mac, macplain, macplainReverse, Maj, Min)
					if tag == "iBeacon" and iBeacon != "":
						rejectThisMessage = False
						iB = iBeacon.split("-")
						Maj  = iB[1]
						Min  = iB[2]

					if posFound == -1 or abs(dPos) > knownBeaconTags[tag]["posDelta"]:
						tagFound = "failed"
					else: 
						tagFound = "found"
						rejectThisMessage = False
						typeOfBeacon = tag

				else: 
					tagFound = "failed"


		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-5   ", "rejectThisMessage:{}, tagFound:{}; UUID: {}, Maj: {}, Min: {}".format(rejectThisMessage, tagFound, UUID, Maj, Min),mac)

		## mac not in current list, check if should look for it = accept new beacons?
		if tagFound  != "found" and (acceptNewTagiBeacons != "off"):#   for testing only or trackMac != ""):
			## check if in tag list

			for seq in range(0,5): # check high prio first starts w 0
				for tag in knownBeaconTags:
					if tag == "other": 									continue
					try:
						if knownBeaconTags[tag]["sequence"] != seq: 	continue
					except:
						U.logger.log(20,u"in tag: {}: kn:{}".format(tag,knownBeaconTags[tag]))
						continue
					if knownBeaconTags[tag]["pos"] == -1: 			 	continue
					posFound, dPos, Maj, Min = testComplexTag(hexstr[12:-2], tag, mac, macplain, macplainReverse, Maj, Min)
					if posFound == -1: 									continue
					if abs(dPos) > knownBeaconTags[tag]["posDelta"]: 	continue
					if acceptNewTagiBeacons == "all" or acceptNewTagiBeacons == tag:
						typeOfBeacon = tag
						UUID = tag
						UUID1 = tag
						tagFound = "found"
						rejectThisMessage = False
						if tag == "iBeacon" and iBeacon != "":
							iB = iBeacon.split("-")
							Maj  = iB[1]
							Min  = iB[2]
					break
				if tagFound =="found": break

			if tagFound != "found" and (acceptNewTagiBeacons == "all" or acceptNewTagiBeacons == "other"):
				UUID = "other"
				UUID1 = "other"
				tagFound = "found"
				typeOfBeacon = "other"
				rejectThisMessage = False
				if tag == "iBeacon" and iBeacon != "":
					iB = iBeacon.split("-")
					Maj  = iB[1]
					Min  = iB[2]

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-6   ", "isOnlySensor:{},  batteryLevel:{} tagFound: {}, UUID: {}, rejectThisMessage: {}".format(isOnlySensor,  batteryLevel, tagFound, UUID, rejectThisMessage) ,mac)


		if rejectThisMessage: # unknow beacon.. accept if RSSI > accept
			if mac not in onlyTheseMAC:
				if rssi > acceptNewiBeacons: 
					if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
						writeTrackMac("tag-7   ", "accept rssi > accept new  and !tagfound", mac)
					rejectThisMessage = False

		if batteryLevel == "": 
			batteryLevel = checkForBatteryInfo( typeOfBeacon, tagFound, mac, hexstr )

		fillbeaconsThisReadCycle(mac, rssi, txPower, iBeacon, mfg_info, batteryLevel, typeOfBeacon)

		if not checkMinMaxSignalAcceptMessage(mac, rssi): rejectThisMessage = True

		if not rejectThisMessage and mac in beaconsThisReadCycle: fillHistory(mac)

		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-9   ", "beaconsThisReadCycle ..mfg_info: {},rejectThisMessage:{},  iBeacon: {}, batteryLevel>{}<".format(mfg_info, rejectThisMessage, iBeacon, batteryLevel) ,mac)


	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return rejectThisMessage


#################################
def getBasicData(hexstr):
	try:
		msgStart		= 14
		majEnd 			= len(hexstr) - 12	
		uuidLen 		= min( 32, (majEnd - msgStart))
		UUID 			= hexstr[-uuidLen-12:-12]
		Maj	 			= str(int(hexstr[-12:-8],16))
		Min	 			= str(int(hexstr[-8:-4],16))
		txPower	 		= signedIntfromString(str(signedIntfromString(hexstr[-4:-2])))
		rssi			= signedIntfromString(hexstr[-2:])
		mfgID			= hexstr[msgStart+10:msgStart+14]
		pType 			= hexstr[msgStart+14:msgStart+16]  # 02  = procimity beacon, BE  = ALT beacon nBytes  = 27
		typeOfBeacon 	= hexstr[msgStart+8:msgStart+10]  #  FF = iBeacon
		typeOfBeacon 	+= "-"+pType.upper() 
		return 	msgStart, majEnd, uuidLen, UUID, Maj, Min, rssi,txPower, mfgID, pType, typeOfBeacon
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 	"", "", "", "", "", "", "", "", "", "",  ""




#################################
def fillbeaconsThisReadCycle(mac, rssi, txPower, iBeacon, mfg_info, batteryLevel, typeOfBeacon):
	global beaconsThisReadCycle
	try:
		try: 	batteryLevel = int(batteryLevel)
		except: batteryLevel = ""

		if mac not in beaconsThisReadCycle: setEmptybeaconsThisReadCycle(mac)
					
		if True:
										beaconsThisReadCycle[mac]["rssi"]			= rssi # signal
										beaconsThisReadCycle[mac]["txPower"]		= float(txPower) # transmit power
										beaconsThisReadCycle[mac]["timeSt"]			= time.time() 
										beaconsThisReadCycle[mac]["batteryLevel"]	= batteryLevel # battery level 
		if iBeacon != "": 				beaconsThisReadCycle[mac]["iBeacon"]		= iBeacon # 
		if mfg_info != "": 				beaconsThisReadCycle[mac]["mfg_info"]		= mfg_info # 
		if typeOfBeacon != "other": 	beaconsThisReadCycle[mac]["typeOfBeacon"]	= typeOfBeacon # 

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 


def checkIfBLEprogramIsRunning(useHCI):
	global rpiDataAcquistionMethod

	try:
		if not U.checkIfHCiUP(useHCI, verbose=True):
			U.logger.log(30,u"{} not up".format(useHCI))
			return False

		if not rpiDataAcquistionMethod == "hcidump": 
			return True

		if U.pgmStillRunning("hcidump -i", verbose=True) and U.pgmStillRunning("hcitool -i", verbose=True):
			return True
		else:
			U.logger.log(30,u"hcidump or hcitool lescan  not up")
			return False

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return False


#################################
#################################
######## BLE SENSORS END  #######
#################################
#################################


####### main pgm / loop ############





####### main pgm / loop ############

def execbeaconloop(test):
	global collectMsgs, sendAfterSeconds, loopMaxCallBLE, deleteHistoryAfterSeconds,lastWriteHistory
	global acceptNewiBeacons, acceptNewTagiBeacons, onlyTheseMAC,enableiBeacons, minSignalOff, minSignalOn, knownBeaconTags
	global myBLEmac, BLEsensorMACs
	global oldRaw,	lastRead
	global  mapReasonToText
	global downCount, beaconsOnline, logCountTrackMac, trackMac, nLogMgsTrackMac, startTimeTrackMac, trackMacText
	global rpiDataAcquistionMethod
	global readBufferSize
	global readbuffer
	global ListenProcessFileHandle
	global lastLESCANrestart
	global beaconsThisReadCycle, beacon_ExistingHistory
	global reasonMax 
	global doRejects
	global readFrom
	global ignoreMAC
	global restartBLE


	deleteHistoryAfterSeconds = 600
	sendAfterSeconds	= 60
	doRejects			= False
	lastLESCANrestart	= 0
	ListenProcessFileHandle =""
	readbuffer			= ""
	readBufferSize		= 4096*8
	rpiDataAcquistionMethod		 	= ""
	acceptNewTagiBeacons = ""
	beaconsOnline		= {}

	downCount 			= 0

	BLEsensorMACs 		= {}
	startTimeTrackMac	= -10
	trackMacText		= ""
	#						0		1		2				3			4			5				6				7			8			9
	mapReasonToText		= ["init","timer","new_beacon","fastDown","fastDown_back","beacon_is_back","delta_signal","quickSens","newParams","",""]
	oldRaw				= ""
	lastRead			= 0
	minSignalOff		= {}
	minSignalOn			= {}
	acceptNewiBeacons	= -999
	enableiBeacons		= "1"
	G.authentication	= "digest"
	# get params
	onlyTheseMAC		={}
	ignoreMAC			=[]
	signalDelta			={}
	fastDownList	={}
	myBLEmac			= ""
	sensor				= G.program	 
	sendFullUUID		= False
	badMacs				= ["00:00:00:00:00:00"]

	U.killOldPgm(-1,"hcidump")
	U.killOldPgm(-1,"hcitool")
	U.killOldPgm(-1,"lescan")

	if test != "normal": readFrom = test
	else: 				 readFrom = ""


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
		retCode = startHCUIDUMPlistnr(useHCI)
		if retCode != "":
			U.logger.log(30,"beaconloop exit, === error in starting HCIdump listener, exit beaconloop ===")
			return

	U.logger.log(30,"using >{}< for data read method testMode:>{}< ".format(rpiDataAcquistionMethod, readFrom!=""))
	
	loopCount		= 0
	tt				= time.time()
	logfileCheck	= tt + 10
	paramCheck		= tt + 10
	sensCheck 		= tt + 10
	checkIPConnection	=tt

	U.echoLastAlive(G.program)
	lastAlive		= tt
	G.tStart		= tt
	beaconsThisReadCycle		= {}
	trackMac		= ""
	nLogMgsTrackMac	= 11 # # of message logged for sepcial mac 
	bleRestartCounter = 0
	eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()
	##print "beaconloop", eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled
	nEmptyMessagesInARow 		 = 0
	lastMSGwithDataPlain = tt
	lastMSGwithDataPassed = tt
	maxLoopCount	 = 6000
	restartCount	 = 0
	logCountTrackMac = -10 
	nMsgs			 = 0
	restartBLE 		 = time.time()
	U.logger.log(30, "starting loop")
	try:
		while True:
			loopCount += 1
			# max every 5 minutes  .. restart BLE hcidump to clear out temp files if accumulated, takes ~1 secs 
			if time.time() - restartBLE > 300 and rpiDataAcquistionMethod == "hcidump":
				restartBLE = time.time()
				startBlueTooth(G.myPiNumber,reUse=True,thisHCI=useHCI)
				retCode = startHCUIDUMPlistnr(useHCI)
				U.logger.log(20, "time needed to restartBLE:{:.2f}[secs]".format(time.time()- restartBLE))

			tt = time.time()
			if tt - checkIPConnection > 600: # check once per 10 minutes
				checkIPConnection = tt
				eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
			
			beaconsThisReadCycle = {}
		
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
				restartBLE = time.time()
				if rpiDataAcquistionMethod == "hcidump":
					retCode = startHCUIDUMPlistnr(useHCI)
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
				tt = round(time.time(),2)
				
				if (reasonMax > 1 or loopCount == 1 ) and tt -G.tStart > 30 : break	# only after ~30 seconds after start....  to avoid lots of short messages in the beginning = collect all ibeacons before sending

				if tt - timeAtLoopStart	 > sendAfter: 
					break # send curl msgs after collecting for xx seconds

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
					if readFrom != "":
						if len(Msgs) >0: 
							U.logger.log(20, u"TestMode: read {}".format(Msgs))
						else:
							time.sleep(5)

				nMsgs = len(Msgs)
				oneValid = False
				for hexstr in Msgs: 
					nCharThisMessage	= len(hexstr)
	
					##U.logger.log(20, "loopCount:{}  #:{}  len:{}".format(loopCount, iiWhile, len(pkt))) 
					#U.logger.log(20, "data nChar:{}".format(nCharThisMessage))
					# skip junk data 
					if nCharThisMessage < 16:  continue
					if nCharThisMessage > 120: continue
						
					try:
						# build the return string: mac#, uuid-major-minor,txpower??,rssi
						lastMSGwithDataPlain = int(time.time())
					
						macplainReverse 	= hexstr[0:12]
						mac 				= macplainReverse[10:12]+":"+macplainReverse[8:10]+":"+macplainReverse[6:8]+":"+macplainReverse[4:6]+":"+macplainReverse[2:4]+":"+macplainReverse[0:2]
						macplain 			= mac.replace(":","")


						if readFrom !="":
							U.logger.log(20, u"TestMode: start: mac:{}, rest:{}".format(mac, hexstr[12:]))

						########  track mac  start / end ############
						trackMacStopIf(hexstr, mac)

						if mac in ignoreMAC: 		
							if readFrom !="":
								U.logger.log(20, u"TestMode: ignored mac:{}".format(mac))
							continue # set to ignore in plugin

						msgStart, majEnd, uuidLen, UUID, Maj, Min, rssi, txPower, mfgID, pType, typeOfBeacon = getBasicData(hexstr)

						if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
							writeTrackMac("basic   ", "UUID: {}, Maj: {}, Min: {}, RX :{}, TX: {}".format(UUID, Maj, Min, rssi, txPower) ,mac)

						txPower, batteryLevel, UUID, Maj, Min, isOnlySensor  = doSensors( mac, macplain, macplainReverse, rssi, txPower, hexstr, UUID, Maj, Min)

						if isOnlySensor:
							lastMSGwithDataPassed = int(time.time())
							continue

						if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
							writeTrackMac("A-Sens  ", "UUID: {}, Maj: {}, Min: {}, RX :{}, TX: {}, batteryLevel:{}".format(UUID, Maj, Min, rssi, txPower, batteryLevel) ,mac)

						## doing this derectly does not work, first hasve to save then test reject
						if checkIfTagged(mac, macplain, macplainReverse, UUID, Min, Maj, isOnlySensor, hexstr, batteryLevel, rssi, txPower): continue
						#if reject: continue


						if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
							writeTrackMac("A-tag   ", "after checkIfTagged, msg accepted, checking for new, changed signal,... ",mac)

						lastMSGwithDataPassed = int(time.time())
		
						#if mac in fastDownList: sendAfter = min(45., sendAfterSeconds)

						if time.time() - G.tStart > 31: # wee need some history first 
							#U.logger.log(50, u"time.time() - G.tStart:{}".format(time.time() - G.tStart) )
							if checkIfNewBeacon(mac): continue

							if checkIfDeltaSignal(mac): continue

						if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
							writeTrackMac("Accpt   ", "{}".format(beaconsThisReadCycle[mac]) ,mac)

					except	Exception, e:
						U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)+ "  bad data, skipping")
						continue

				
				sensCheck, paramCheck = doLoopCheck(tt, sensCheck, paramCheck, sensor, useHCI )

				if time.time() - G.tStart > 31: checkIfFastDownForAll() # send -999 if gone 

			if rpiDataAcquistionMethod == "socket":
				sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
				
			if readFrom !="":
				lastMSGwithDataPlain = time.time()
				lastMSGwithDataPassed = time.time()
				nEmptyMessagesInARow = 0
				U.echoLastAlive(G.program)
				if len(Msgs) > 0:
					nMessagesSend = composeMSG(timeAtLoopStart)
					handleHistory() 
				U.logger.log(20, u"TestMode: {}".format(beacon_ExistingHistory))
				time.sleep(5)
				continue

			nMessagesSend = composeMSG(timeAtLoopStart)
			handleHistory() 
			U.echoLastAlive(G.program)


			dt1 = int(time.time() - lastMSGwithDataPlain)
			dt2 = int(time.time() - lastMSGwithDataPassed)
			if  nMessagesSend > 0:
				nEmptyMessagesInARow = 0
						
			else:
				nEmptyMessagesInARow += 1
				if nEmptyMessagesInARow > 2 and not checkIfBLEprogramIsRunning(useHCI):
					U.logger.log(30, " restarting BLE stack due to no messages "+G.program)
					if rpiDataAcquistionMethod == "socket":
						sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber)
						restartBLE = time.time()
						maxLoopCount = 6000
					else:
						time.sleep(0.5)
						restartLESCAN(useHCI, 20, force=True)
						stopHCUIDUMPlistener()
						sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber)
						startHCUIDUMPlistnr(useHCI)
						restartBLE = time.time()
						#U.restartMyself(param="", reason="no messages:{} in a row;  hcitool -i hcix / hcidump -i hcix  not running, ".format(nEmptyMessagesInARow))

			if nEmptyMessagesInARow > 20:
				maxLoopCount = 20
				restartCount +=1
				U.logger.log(30, u" time w/out any message .. anydata: {}[secs];  okdata: {}[secs];   loopCount:{};  restartCount:{},nEmptyMessagesInARow:{} ".format(dt1, dt2, loopCount, restartCount,nEmptyMessagesInARow))
				if restartCount > 0:
					U.logger.log(30, " restarting BLE stack due to no messages " )
					time.sleep(0.5)
					U.restartMyself(param="", reason="too long a time w/o message")

	except	Exception, e:
		U.logger.log(50, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30, "  exiting loop due to error\n restarting "+G.program)
		stopHCUIDUMPlistener()
		time.sleep(20)
		subprocess.call("/usr/bin/python "+G.homeDir+G.program+".py &", shell=True)
	try: 	G.sendThread["run"] = False; time.sleep(1)
	except: pass

U.echoLastAlive(G.program)
try: test = sys.argv[1]
except: test = "normal"
execbeaconloop(test)
stopHCUIDUMPlistener()
U.logger.log(30,"end of beaconloop.py ") 
sys.exit(0)		   
