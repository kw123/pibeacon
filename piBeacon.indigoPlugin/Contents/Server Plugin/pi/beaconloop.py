#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  adopted by Karl Wachs Nov27	2015
#
# scans for any kind of BLE message and sends info to indigo plugin
#
# has 2 method: socket and commandline (hcidump) to get info
#
# also scanns for sensor devices that send of eg temp/ hum/ acceleration ble messages
#
# can also beep and get battery level w gatttool commands
#
# can also send all  messages parsed to the plugin as requested
#
# can also track a single mac, all messages and all steps to ID these messages
#
# it is now >5< years in development
#
# runs on all kinds of RPI and BLE UART and external dongles
#
## ok for py3

from __future__ import division
import sys, os, subprocess, copy
import time,datetime
import struct
try:
	import bluetooth._bluetooth as bluez
	bluezPresent = True
except:
	bluezPresent = False
import json

import math
import fcntl
#import codex

sys.path.append(os.getcwd())
import	piBeaconUtils as U
import	piBeaconGlobals as G

import  pexpect
G.program = "beaconloop"
VERSION   = 8.60

if sys.version[0] == "3": usePython3 = True
else:					  usePython3 = False


try:	import codecs
except:	pass

def hex2str(inString):
	try:
		if sys.version[0] == '3':
			return codecs.decode(inString,"hex").decode('utf-8')
		else:
			return  inString.decode("hex")
	except Exception as e:
		U.logger.log(20,"hexstring: >>{}<<".format(inString), exc_info=True)
	return "00"
	
####-------------------------------------------------------------------------####
def readPopen(cmd):
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception as e:
			U.logger.log(20,"", exc_info=True)

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

def signedIntfrom8(string):
	try:
		intNumber = int(string,16)
		if intNumber > 127: intNumber -= 256
	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
		return 0
	return intNumber

def signedIntfrom16(string):
	try:
		intNumber = int(string,16)
		if intNumber > 32767: intNumber -= 65536
	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
		return 0
	return intNumber

def signedIntfrom24(string):
	try:
		intNumber = int(string,24)
		if intNumber > 8388608: intNumber -= 16777216
	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
		return 0
	return intNumber


def intFrom8(hexString, start):
	return int(hexString[start:start+2],16)

def intFrom16(hexString, start):
	return int(hexString[start:start+4],16)


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
			
	

def startBlueTooth(pi, reUse=False, thisHCI="", trymyBLEmac="", hardreset=False):
	global myBLEmac, downCount
	global lastLESCANrestart
	global rpiDataAcquistionMethod

	myBLEmac = ""
	devId	 = 0
	useHCI	 = ""
	bus 	 = ""
	## good explanation: http://gaiger-G.programming.blogspot.com/2015/01/bluetooth-low-energy.html
	U.logger.log(20,"(re)starting bluetooth")
	startTime = time.time()
	logLevelStart = 20
	if thisHCI !="": logLevelStart = 10
	U.writeFile("temp/beaconloop.hci", json.dumps({}))
	try:
		HCIs = U.whichHCI()
		U.logger.log(20,"thisHCI:{}; HCIs available:{}".format(thisHCI, HCIs)  )
		for hci in HCIs["hci"]:
			if hci == "": continue
			if thisHCI != "" and hci!=thisHCI: continue
			U.logger.log(20,"checking hci:{}".format(hci)  )

			if hardreset:
				cmd = "sudo hciconfig {} down".format(hci)
				ret = readPopen(cmd) # enable bluetooth
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime)  )
				#cmd = "sudo rmmod btusb"
				#ret = subprocess.Popen(cmd, shell=True,stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate() # enable bluetooth
				#U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime)  )
				#cmd = "sudo modprobe btusb"
				#ret = subprocess.Popen(cmd, shell=True,stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate() # enable bluetooth
				#U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime)  )
				cmd = "sudo invoke-rc.d bluetooth restart"
				ret = readPopen(cmd) # enable bluetooth
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime)  )
				cmd = "sudo hciconfig {} up".format(hci)
				ret = readPopen(cmd) # enable bluetooth
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime)  )

			elif reUse:
				cmd = "sudo hciconfig "+hci+" reset"
				ret = readPopen(cmd) # 
				U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )

			else:
				cmd = "sudo hciconfig "+hci+" reset"
				ret =readPopen(cmd)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )
				if ret[1] != "":
					time.sleep(0.2)
					ret = readPopen(cmd)
					U.logger.log(logLevelStart,"resetting {} bluetooth".format(hci))

				cmd = "hciconfig "
				ret = readPopen(cmd) # test bluetooth
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )

				cmd = "sudo hciconfig "+hci+" up"
				ret = readPopen(cmd) # enable bluetooth
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime)  )
				if ret[1] != "":
					time.sleep(0.2)
					ret = readPopen(cmd) # enable bluetooth
					U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )
					cmd = "hciconfig "
					ret = readPopen(cmd) # test bluetooth
					U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )

			if rpiDataAcquistionMethod.find("hcidump") == 0:
				cmd	 = "sudo hciconfig {} noleadv &\n sudo hciconfig {} noscan &".format(hci, hci)
				ret = readPopen(cmd)
				U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd.replace("\n",";"), ret, time.time()- startTime)  )

		time.sleep(1)

		#### selct the proper hci bus: if just one take that one, if 2, use bus="uart", if no uart use hci0, or use last one
		if not reUse: HCIs = U.whichHCI()
		if HCIs !={} and "hci" in  HCIs and HCIs["hci"] !={}:

			#U.logger.log(30,"myBLEmac HCIs{}".format( HCIs))
			useHCI,  myBLEmac, devId, bus = U.selectHCI(HCIs["hci"], G.BeaconUseHCINo,"USB", tryBLEmac=trymyBLEmac)
			U.writeFile("temp/beaconloop.hci", json.dumps({"usedHCI":useHCI, "myBLEmac": myBLEmac, "usedBus":bus}))
			U.writeFile("beaconloop.hci", json.dumps({"usedHCI":useHCI, "myBLEmac": myBLEmac, "usedBus":bus}))
			text = "{}-{}-{}".format(useHCI, bus, myBLEmac)
			U.sendURL( data={"data":{"hciInfo":text}}, squeeze=False, wait=False )

			if myBLEmac ==  -1:
				U.logger.log(20,"myBLEmac wrong: myBLEmac:{}, HCIs:{}".format( myBLEmac, HCIs))
				return 0,  0, -1, useHCI
			U.logger.log(20,"Beacon Use HCINo {};  useHCI:{};  myBLEmac:{}; devId:{}, bus:{};  DT:{:.3f}" .format(G.BeaconUseHCINo, useHCI, myBLEmac, devId, bus, time.time()- startTime))
			
			if 	rpiDataAcquistionMethod.find("hcidump") == 0:
				cmd	 = "sudo hciconfig {} leadv 3 &".format(useHCI)
				ret = readPopen(cmd)
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
				ret = readPopen(cmd)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )


			if 	rpiDataAcquistionMethod .find("hcidump" ) == 0:
				restartLESCAN(useHCI, logLevelStart, force=True )

			if	True or rpiDataAcquistionMethod == "socket":
				####################################set adv params		minInt	 maxInt		  nonconectable	 +??  <== THIS rpi to send beacons every 10 secs only 
				#											   00 40=	0x4000* 0.625 msec = 16*4*256 = 10 secs	 bytes are reverse !! 
				#											   00 10=	0x1000* 0.625 msec = 16*1*256 = 2.5 secs
				#											   00 04=	0x0400* 0.625 msec =	4*256 = 0.625 secs
				#cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + " 0x0006"	  + " 00 10"+ " 00 20" +  " 03"			   +   " 00 00 00 00 00 00 00 00 07 00"
				cmd	 = "hcitool -i {} cmd{} 0x0006 00 10 00 20 03 00 00 00 00 00 00 00 00 07 00 &".format(useHCI, OGF)
				## maxInt= A0 00 ==	 100ms;	 40 06 == 1000ms; =0 19 = 4 =seconds  (0x30x00	==> 64*256*0.625 ms = 10.024secs  use little endian )
				ret = readPopen(cmd)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime)  )
				####################################LE Set Advertise Enable
				#cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + " 0x000a" + " 01"
				time.sleep(0.1)
				cmd	 = "hcitool -i {} cmd{} 0x000a 01 &".format(useHCI, OGF)
				ret = readPopen(cmd)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, time.time()- startTime) )
				time.sleep(0.1)


			ret = HCIs["ret"]
		else:
			ret =["",""]

		if ret[1] != "":	
			U.logger.log(20,"BLE start returned:\n{}error:>>{}<<".format(ret[0],ret[1]))
			U.sendURL( data={"data":{"hciInfo":"err-BLE-start"}}, squeeze=False, wait=False )

		else:
				U.logger.log(20,"BLE start returned:\n{}my BLE mac# is >>{}<<, on bus:{}".format(ret[0], myBLEmac, bus))
				if useHCI in HCIs["hci"]:
					if HCIs["hci"][useHCI]["upDown"] == "DOWN":
						if downCount > 1:
							U.logger.log(20,"reboot requested,{} is DOWN using hciconfig ".format(useHCI))
							U.writeFile("temp/rebootNeeded","bluetooth_startup {} is DOWN using hciconfig FORCE".format(useHCI))
							U.sendURL( data={"data":{"hciInfo":"err-BLE-down"}}, squeeze=False, wait=False )
							time.sleep(10)
						downCount +=1
						time.sleep(10)
						return 0,  "", -1, useHCI
				else:
					U.logger.log(30," {}  not in hciconfig list".format(useHCI))
					downCount +=1
					if downCount > 1:
						U.sendURL( data={"data":{"hciInfo":"err-BLE-channel-missing"}}, squeeze=False, wait=False )
						U.logger.log(30,"reboot requested,{} is DOWN using hciconfig ".format(useHCI))
						U.writeFile("temp/rebootNeeded","bluetooth_startup {} is DOWN using hciconfig FORCE".format(useHCI))
						time.sleep(10)
					downCount +=1
					time.sleep(10)
					return 0,  "", -1, useHCI
					
				
		if myBLEmac == "":
			U.sendURL( data={"data":{"hciInfo":"err-BLE-start-mac-empty"}}, squeeze=False, wait=False )
			return 0, "", -1, useHCI

	except Exception as e: 
		U.logger.log(30,"", exc_info=True)
		U.sendURL( data={"data":{"hciInfo":"err-BLE-start"}}, squeeze=False, wait=False )
		time.sleep(10)
		U.writeFile("temp/restartNeeded","bluetooth_startup.ERROR:{}".format(e))
		downHCI(useHCI)
		time.sleep(0.2)
		return 0, "", -5, useHCI


	U.writeFile("temp/beaconloop.hci", json.dumps({"usedHCI":useHCI, "myBLEmac": myBLEmac, "usedBus":bus}))
	U.writeFile("beaconloop.hci", json.dumps({"usedHCI":useHCI, "myBLEmac": myBLEmac, "usedBus":bus}))


	if rpiDataAcquistionMethod.find("hcidump" ) == 0:
		return "", myBLEmac, 0, useHCI


	if rpiDataAcquistionMethod == "socket":
		try:
			sock = bluez.hci_open_dev(devId)
			U.logger.log(30, "ble thread started")
		except	Exception as e:
			U.logger.log(30,"error accessing bluetooth device...".format(e))
			if downCount > 2:
				U.writeFile("temp/rebootNeeded","bluetooth_startup.ERROR:{} FORCE ".format(e))
				downHCI(useHCI)
			downCount +=1
			return 0,  "", -1, useHCI
		
		try:
			hci_le_set_scan_parameters(sock)
			hci_enable_le_scan(sock)
		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
			if "{}".format(e).find("Bad file descriptor") >-1:
				U.writeFile("temp/rebootNeeded","bluetooth_startup.ERROR:Bad_file_descriptor...SSD.damaged? FORCE ")
			if "{}".format(e).find("Network is down") >-1:
				if downCount > 2:
					U.writeFile("temp/rebootNeeded","bluetooth_startup.ERROR:Network_is_down...need_to_reboot FORCE ")
				downCount +=1
			downHCI(useHCI)
			return 0, "", -1, useHCI

	return sock, myBLEmac, 0, useHCI



#################################
def restartLESCAN(useHCI, loglevel, force=False):
	global rpiDataAcquistionMethod
	global lastLESCANrestart
	try:
		if rpiDataAcquistionMethod == "socket": return 
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
			U.killOldPgm(-1,"hcitool") # will kill the launching sudo parent process, lescan still running
			cmd	 = "sudo hcitool -i {} lescan --duplicates  > /dev/null 2>&1 &".format(useHCI,G.homeDir)
			#cmd	 = "sudo hcitool -i {} lescan --privacy --passive --discovery=l  > /dev/null 2>&1 &".format(useHCI,G.homeDir)
			#cmd	 = "sudo hcitool -i {} lescan --passive --discovery=l  > /dev/null 2>&1 &".format(useHCI,G.homeDir)
			#cmd	 = "sudo hcitool -i {} lescan > /dev/null 2>&1 &".format(useHCI,G.homeDir)
			ret = readPopen(cmd)
			U.logger.log(loglevel,"cmd:{} .. ret:{}...  dT:{:.3f}".format(cmd, ret, time.time() - tt) )
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
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
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
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
		msg = "{}".format(ListenProcessFileHandle.stderr)
		if msg.find("open file") == -1 and msg.find("io.BufferedReader") == -1:	# try this again
			U.logger.log(30,"hci#: {}; error connecting {}".format(hci, msg) )
			time.sleep(20)
			return  "error {}".format(msg)

		U.killOldPgm(-1,"sudo hcidump")

		if not U.pgmStillRunning("hcidump -i"):
			U.logger.log(40,"hcidump not running ")
			return "error"

		# set the O_NONBLOCK flag of ListenProcessFileHandle.stdout file descriptor:
		flags = fcntl.fcntl(ListenProcessFileHandle.stdout, fcntl.F_GETFL)  # get current p.stdout flags
		fcntl.fcntl(ListenProcessFileHandle.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
		time.sleep(0.1)
		return  ""

	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
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
	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
	return 

####-------------------------------------------------------------------------####
def openEncoding(ff, readOrWrite):
	if sys.version_info[0]  > 2:
		return open( ff, readOrWrite, encoding="utf-8")
	else:
		return codecs.open( ff ,readOrWrite, "utf-8")

def toBytesIfPy3(text):
	if sys.version_info[0]  > 2:
		return bytes(text,"utf8")
	else:
		return text


#################################
def readHCUIDUMPlistener():
	global readBufferSize, ListenProcessFileHandle
	global readFrom

	if readFrom != "":
		messages =[]
		try:
			if os.path.isfile(readFrom):
				f= openEncoding(readFrom,"r")
				messages = f.read()
				f.close()
				subprocess.call("rm {}".format(readFrom), shell=True)
				if len(messages) > 5:
					return [messages.strip("\n")]
			return []
				
		except	Exception as e:
			U.logger.log(20,"", exc_info=True)
		return []

	try:
		lines = (os.read(ListenProcessFileHandle.stdout.fileno(),readBufferSize)).decode("utf8") 
		#U.logger.log(20, "{}".format(lines))
		if len(lines) == 0: return []
		messages = combineLines(lines)
		#U.logger.log(20, u"readHCUIDUMPlistener lines:\n{}".format(lines))
		#U.logger.log(20, u"readHCUIDUMPlistener messages\n{}".format(json.dumps(messages).replace(",","\n")))
		return messages
	except	Exception as e:
		if "{}".format(e).find("[Errno 35]") > -1:	 # "Errno 35" is the normal response if no data, if other error stop and restart
			pass
			#U.logger.log(20, u"Errno 35")
		if "{}".format(e).find("[Errno 1]") > -1:	 
			pass
			#U.logger.log(20, u"Errno 1")
		if "{}".format(e).find("temporarily") > -1:
			pass
			#U.logger.log(20, u"Errno 11")
		else:
			if "{}".format(e) != "None":
				U.logger.log(20,"", exc_info=True)
				out= ""
				try: out+= "fileNo: {}".format(ListenProcessFileHandle.stdout.fileno() )
				except: pass
				if "{}".format(e).find("[Errno 22]") > -1:  # "Errno 22" is  general read error "wrong parameter"
					out+= " ..      try lowering read buffer parameter in config" 
					U.logger.log(20,out)
				else:
					U.logger.log(20,out)
		time.sleep(0.5)
		return []

	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
	return []
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
			if line.find("-") > -1: continue
			if line.find(".") > -1: continue
			if line.find(",") > -1: continue
			if line.find(":") > -1: continue
			if line.find("<") > -1: continue
			readbuffer += line.replace(" ","")

		rd = readbuffer.split(">")
		ll = len(rd)
		nn = 0
		for line in rd:
			nn +=1
			if len(line) < 40 and nn < ll: continue
			MSGs.append(line) 
		if len(MSGs) == 0: return []

		if len(MSGs[-1]) < 40:
			readbuffer = MSGs[-1]
			#U.logger.log(20, u"readHCUIDUMPlistener leftover>{}<, >{}<".format(readbuffer,MSGs[-1] ))
			del MSGs[-1]
		else:
			readbuffer = ""
	
		return MSGs	
	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
	return []

	
#################################
def toReject(text):
	global doRejects
	try:
		if not doRejects: return 

		U.writeFile("temp/rejects", "{};{}\n".format(time.time(), text, writeOrAppend="a"))

	except	Exception as e:
		if "{}".format(e).find("Read-only file system:") >-1:
			U.doReboot(tt=0)

#################################
def fixOldNames():

	if os.path.isfile(G.homeDir+"beaconsExistingHistory"):
		subprocess.call("sudo mv "+G.homeDir+"beaconsExistingHistory " + G.homeDir+"beacon_ExistingHistory", shell=True)

def readParams(init=False):
	global collectMsgs, loopMaxCallBLE,  beacon_ExistingHistory, signalDelta,fastDownList, ignoreMAC
	global acceptNewiBeacons,acceptNewBeaconMAC, acceptNewTagiBeacons,onlyTheseMAC,enableiBeacons, sendFullUUID,BLEsensorMACs, minSignalOff, minSignalOn, knownBeaconTags
	global acceptNewMFGNameBeacons
	global oldRaw, lastRead
	global rpiDataAcquistionMethod
	global batteryLevelUUID
	global fastBLEReaction, output
	if init:
		collectMsgs			= 10  # in parse loop collect how many messages max	  ========	all max are an "OR" : if one hits it stops
		loopMaxCallBLE		= 900 # max loop count	in main pgm to collect msgs
		portOfServer		= "8176"
		G.ipOfServer	  	= ""
		G.passwordOfServer	= ""
		G.userIdOfServer  	= ""
		G.myPiNumber	  	= "0"
		lastRead			= 0
		oldRaw				= "xxx"

	inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
	doParams = True
	if inp == "":				doParams = False
	if lastRead2 == lastRead:	doParams = False
	lastRead   = lastRead2
	if inpRaw == oldRaw:		doParams = False
	oldRaw	   = inpRaw

	if doParams:
		try:
			if "output" in inp : output = copy.deepcopy(inp["output"])
			else: output = {}
			if "enableiBeacons"		in inp:	 enableiBeacons=	   (inp["enableiBeacons"])
			if enableiBeacons == "0":
				U.logger.log(50," termination ibeacon scanning due to parameter file")
				time.sleep(0.5)
				stopHCUIDUMPlistener()
				sys.exit(3)
			U.getGlobalParams(inp)

			acceptNewMFGNameBeacons = ""
			if "rebootSeconds"				in inp:	 rebootSeconds =			int(inp["rebootSeconds"])
			if "acceptNewiBeacons"			in inp:	 acceptNewiBeacons =		int(inp["acceptNewiBeacons"])
			if "acceptNewTagiBeacons"		in inp:	 acceptNewTagiBeacons =		(inp["acceptNewTagiBeacons"])
			if "acceptNewBeaconMAC"			in inp:	 acceptNewBeaconMAC =		(inp["acceptNewBeaconMAC"])
			if "sendFullUUID"				in inp:	 sendFullUUID =				(inp["sendFullUUID"]=="1" )
			if "acceptNewMFGNameBeacons"	in inp:	 acceptNewMFGNameBeacons =	(inp["acceptNewMFGNameBeacons"])


			if bluezPresent:
				if "rpiDataAcquistionMethod" in inp:	 
					xx =		 	 								(inp["rpiDataAcquistionMethod"])
					if xx != rpiDataAcquistionMethod and rpiDataAcquistionMethod != "":
						U.restartMyself(param="", reason="new data aquisition method", python3=usePython3)
					rpiDataAcquistionMethod = xx
				else:
					rpiDataAcquistionMethod = "hcidump"
			else:
					rpiDataAcquistionMethod = "hcidump"

			if "sensors"			 in inp: 
				sensors =			 (inp["sensors"])
				for sensor in sensors:
					#U.logger.log(20,"doing sensor:{}".format(sensor))
					for devId in sensors[sensor]:
						sensD	= sensors[sensor][devId]
						#U.logger.log(20,"doing sensor details:{}".format(sensD))
						if "mac" not in sensD: continue
						mac = sensD["mac"]
						#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,u"mac {} passed 1".format(mac))
						if sensors[sensor][devId].get("isBLESensorDevice",False):
							#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,u"mac {} passed 2".format(mac))
							if mac not in BLEsensorMACs: 
								BLEsensorMACs[mac] = {}
								#U.logger.log(20,u"init mac for sensor:{}".format(mac))

							if sensor not in BLEsensorMACs[mac]: 
								BLEsensorMACs[mac][sensor] = {}
								#U.logger.log(20,u"init sensor for sensor:{}".format(mac))

							BLEsensorMACs[mac][sensor]["devId"] 						= devId
							try:	BLEsensorMACs[mac][sensor]["offsetPress"]   		= float(sensD["offsetPress"])
							except: BLEsensorMACs[mac][sensor]["offsetPress"]			= 0.
							try:	BLEsensorMACs[mac][sensor]["offsetHum"]   			= float(sensD["offsetHum"])
							except: BLEsensorMACs[mac][sensor]["offsetHum"]				= 0.
							try:	BLEsensorMACs[mac][sensor]["offsetTemp"]   			= float(sensD["offsetTemp"])
							except: BLEsensorMACs[mac][sensor]["offsetTemp"]			= 0.
							try:	BLEsensorMACs[mac][sensor]["multTemp"] 				= float(sensD["multTemp"])
							except: BLEsensorMACs[mac][sensor]["multTemp"] 				= 1.
							try:	BLEsensorMACs[mac][sensor]["updateIndigoTiming"] 	= float(sensD["updateIndigoTiming"])
							except: BLEsensorMACs[mac][sensor]["updateIndigoTiming"] 	= 10.
							try:	BLEsensorMACs[mac][sensor]["updateIndigoDeltaAccelVector"]	= float(sensD["updateIndigoDeltaAccelVector"])
							except: BLEsensorMACs[mac][sensor]["updateIndigoDeltaAccelVector"] = 30. # % total abs of vector change
							try:	BLEsensorMACs[mac][sensor]["updateIndigoDeltaMaxXYZ"] = float(sensD["updateIndigoDeltaMaxXYZ"])
							except: BLEsensorMACs[mac][sensor]["updateIndigoDeltaMaxXYZ"] = 30. # N/s*s *1000 
							try:	BLEsensorMACs[mac][sensor]["updateIndigoDeltaTemp"] = float(sensD["updateIndigoDeltaTemp"])
							except: BLEsensorMACs[mac][sensor]["updateIndigoDeltaTemp"] = 1 # =1C 
							try:	BLEsensorMACs[mac][sensor]["minSendDelta"] 			= float(sensD["minSendDelta"])
							except: BLEsensorMACs[mac][sensor]["minSendDelta"] 			= 4 #  seconds betwen updates
							try:	BLEsensorMACs[mac][sensor]["numberOfMeasurementToAverage"] 			= int(sensD["numberOfMeasurementToAverage"])
							except: BLEsensorMACs[mac][sensor]["numberOfMeasurementToAverage"] 			= 4 #  number of averages

							try:	
									xx = int(sensD["numberOfMeasurementToAverage"])
									if "numberOfMeasurementToAverage" in BLEsensorMACs[mac][sensor]: 
										if BLEsensorMACs[mac][sensor]["numberOfMeasurementToAverage"] != xx:
											BLEsensorMACs[mac][sensor]["nMessages"] = 0
							except: 
									xx = 4 #  number of averages
							BLEsensorMACs[mac][sensor]["numberOfMeasurementToAverage"] = xx

							if "accelerationTotal" not in BLEsensorMACs[mac][sensor]:
								#U.logger.log(20,u"init values for sensor:{}".format(mac))
								BLEsensorMACs[mac][sensor]["batteryLevel"]					= ""
								BLEsensorMACs[mac][sensor]["accelerationTotal"]				= 0
								BLEsensorMACs[mac][sensor]["accelerationX"]				 	= 0
								BLEsensorMACs[mac][sensor]["accelerationY"]				 	= 0
								BLEsensorMACs[mac][sensor]["accelerationZ"]				 	= 0
								BLEsensorMACs[mac][sensor]["light"]				 			= -1
								BLEsensorMACs[mac][sensor]["lastUpdate"]				 	= time.time() - 50
								BLEsensorMACs[mac][sensor]["lastUpdate1"]				 	= 0
								BLEsensorMACs[mac][sensor]["lastUpdate2"]				 	= 0
								BLEsensorMACs[mac][sensor]["SOS"]				 			= False
								BLEsensorMACs[mac][sensor]["hum"]				 			= -100
								BLEsensorMACs[mac][sensor]["Formaldehyde"]				 	= -100
								BLEsensorMACs[mac][sensor]["temp"]				 			= -100
								BLEsensorMACs[mac][sensor]["tempAve"]				 		=[-100,-100,-100]
								BLEsensorMACs[mac][sensor]["humAve"]				 		=[-100,-100,-100]
								BLEsensorMACs[mac][sensor]["illuminance"]					= -100
								BLEsensorMACs[mac][sensor]["AmbientTemperature"] 			= -100
								BLEsensorMACs[mac][sensor]["onOff"]		 					= False
								BLEsensorMACs[mac][sensor]["onOff1"]		 				= False
								BLEsensorMACs[mac][sensor]["onOff2"]		 				= False
								BLEsensorMACs[mac][sensor]["onOff3"]		 				= False
								BLEsensorMACs[mac][sensor]["onOff4"] 						= False
								BLEsensorMACs[mac][sensor]["onOff5"] 						= False
								BLEsensorMACs[mac][sensor]["onOff6"] 						= False
								BLEsensorMACs[mac][sensor]["alive"] 						= False
								BLEsensorMACs[mac][sensor]["counter"] 						= "-1"
								BLEsensorMACs[mac][sensor]["batteryVoltage"] 	 	 		= -1
								BLEsensorMACs[mac][sensor]["chipTemperature"] 	 	 		= -1
								BLEsensorMACs[mac][sensor]["secsSinceStart"] 	 	 		= -1
								BLEsensorMACs[mac][sensor]["nMessages"] 	 	 			= 0
								BLEsensorMACs[mac][sensor]["lastMotion"]   					= -1
								BLEsensorMACs[mac][sensor]["motion"]   						= False
								BLEsensorMACs[mac][sensor]["motionDuration"]   				= -1
								BLEsensorMACs[mac][sensor]["secsSinceLastM"]   				= -1
								BLEsensorMACs[mac][sensor]["batteryLevel"]  				= ""
								BLEsensorMACs[mac][sensor]["closed"]  						= -1
								BLEsensorMACs[mac][sensor]["shortOpen"]  					= -1
								BLEsensorMACs[mac][sensor]["longOpen"]  					= -1
								BLEsensorMACs[mac][sensor]["pressCounter"]  				= -1
								BLEsensorMACs[mac][sensor]["marker"]  						= ""


		except	Exception as e:
			U.logger.log(30,"", exc_info=True)



	knownBeaconTags = {}
	onlyTheseMAC 	= {}
	ignoreMAC 		= []
	fastDownList 	= {}
	minSignalOff 	= {}
	minSignalOn 	= {}
	signalDelta 	= {}
	batteryLevelUUID = {}
	try:
		f = open("{}temp/knownBeaconTags".format(G.homeDir),"r")
		knownBeaconTags = json.loads(f.read().strip("\n"))
		f.close()
	except:	pass	



	try:
		f = open("{}temp/beacon_parameters".format(G.homeDir),"r")
		InParams = json.loads(f.read().strip("\n"))
		f.close()
		onlyTheseMAC	 = InParams.get("onlyTheseMAC", {})
		ignoreMAC		 = InParams.get("ignoreMAC", [])
		fastDownList	 = InParams.get("fastDownList", {})
		minSignalOff	 = InParams.get("minSignalOff", {})
		minSignalOn		 = InParams.get("minSignalOn", {})
		signalDelta	 	 = InParams.get("signalDelta", {})
		batteryLevelUUID = InParams.get("batteryLevelUUID", {})
		fastBLEReaction	 = InParams.get("fastBLEReaction", {})
	except: pass


	if False:	
		U.logger.log(0,"fastDownList:       {}".format(fastDownList))
		U.logger.log(0,"signalDelta:        {}".format(signalDelta))
		U.logger.log(0,"ignoreMAC:          {}".format(ignoreMAC))

	return


#################################, check if signal strength is acceptable for fastdown 
def setEmptybeaconsThisReadCycle(mac):
	global beaconsThisReadCycle
	try:
			beaconsThisReadCycle[mac]={"typeOfBeacon":"", "txPower":0, "rssi":0, "timeSt":0,"batteryLevel":"","mfg_info":"","mode":"","onOffState":"", "iBeacon":"","reason":0,"TLMenabled":"","inMotion":"","calibrated":"","position":"","light":"","allowsConnection":""}
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

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
	except Exception as e:
		if "{}".format(e).find("Read-only file system:") >-1:
			U.doReboot(tt=0)
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
			beacon_ExistingHistory[mac]["count"]	= 0

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
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
		beacon_ExistingHistory[mac]["txPower"]		= ""
		beacon_ExistingHistory[mac]["count"]		= 1

		#U.logger.log(30,u"mac:{}; beacon_ExistingHistory:{}".format(mac, beacon_ExistingHistory[mac]))

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)


#################################, check if signal strength is acceptable for fastdown 
def fillHistory(mac):
	global beaconsThisReadCycle, beacon_ExistingHistory
	try:
		if mac not in beacon_ExistingHistory: 
			copyToHistory(mac) 

		beacon_ExistingHistory[mac]["rssi"].append(beaconsThisReadCycle[mac]["rssi"])
		beacon_ExistingHistory[mac]["timeSt"].append(beaconsThisReadCycle[mac]["timeSt"])
		beacon_ExistingHistory[mac]["reason"].append(beaconsThisReadCycle[mac]["reason"])
		if beaconsThisReadCycle[mac]["txPower"] != "": 			beacon_ExistingHistory[mac]["txPower"] = beaconsThisReadCycle[mac]["txPower"]
		beacon_ExistingHistory[mac]["count"] += 1
		if beaconsThisReadCycle[mac]["batteryLevel"] !="": 		beacon_ExistingHistory[mac]["batteryLevel"]		= beaconsThisReadCycle[mac]["batteryLevel"]
		if beaconsThisReadCycle[mac]["calibrated"] !="": 		beacon_ExistingHistory[mac]["calibrated"]		= beaconsThisReadCycle[mac]["calibrated"]
		if beaconsThisReadCycle[mac]["position"] !="": 			beacon_ExistingHistory[mac]["position"]			= beaconsThisReadCycle[mac]["position"]
		if beaconsThisReadCycle[mac]["mode"] !="": 				beacon_ExistingHistory[mac]["mode"]				= beaconsThisReadCycle[mac]["mode"]
		if beaconsThisReadCycle[mac]["onOffState"] !="": 		beacon_ExistingHistory[mac]["onOffState"]		= beaconsThisReadCycle[mac]["onOffState"]
		if beaconsThisReadCycle[mac]["light"] !="": 			beacon_ExistingHistory[mac]["light"]			= beaconsThisReadCycle[mac]["light"]
		if beaconsThisReadCycle[mac]["iBeacon"] !="": 			beacon_ExistingHistory[mac]["iBeacon"]			= beaconsThisReadCycle[mac]["iBeacon"]
		if beaconsThisReadCycle[mac]["TLMenabled"] !="":		beacon_ExistingHistory[mac]["TLMenabled"]		= True
		if beaconsThisReadCycle[mac]["mfg_info"] !="":			beacon_ExistingHistory[mac]["mfg_info"]			= beaconsThisReadCycle[mac]["mfg_info"]
		if beaconsThisReadCycle[mac]["subtypeOfBeacon"] !="":	beacon_ExistingHistory[mac]["subtypeOfBeacon"]	= beaconsThisReadCycle[mac]["subtypeOfBeacon"]
		if beaconsThisReadCycle[mac]["inMotion"] != "":			beacon_ExistingHistory[mac]["inMotion"]			= beaconsThisReadCycle[mac]["inMotion"]
		if beaconsThisReadCycle[mac].get("allowsConnection","") != "":	beacon_ExistingHistory[mac]["allowsConnection"]	= beaconsThisReadCycle[mac]["allowsConnection"]
		if beaconsThisReadCycle[mac].get("analyzed","")  != "":	beacon_ExistingHistory[mac]["analyzed"]			= beaconsThisReadCycle[mac]["analyzed"]

		if "typeOfBeacon" not in beacon_ExistingHistory:
			if beaconsThisReadCycle[mac]["typeOfBeacon"] != "":	beacon_ExistingHistory[mac]["typeOfBeacon"]		= beaconsThisReadCycle[mac]["typeOfBeacon"]
		elif beaconsThisReadCycle[mac]["typeOfBeacon"]  not in ["", "other"]:
																beacon_ExistingHistory[mac]["typeOfBeacon"]		= beaconsThisReadCycle[mac]["typeOfBeacon"]
		stripOldHistory(mac)
		#U.logger.log(20,u"mac {} beaconsThisReadCycle{}".format(mac,beaconsThisReadCycle[mac] ))
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)


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

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

		
	
#################################
def composeMSG(timeAtLoopStart):
	global collectMsgs, loopMaxCallBLE
	global myBLEmac, sendFullUUID,  mapReasonToText, downCount, beaconsOnline
	global beaconsThisReadCycle, beacon_ExistingHistory
	global reasonMax
	global onlyTheseMAC
	global trackMac, logCountTrackMac
	try:
		nMessages = 0
		if myBLEmac == "00:00:00:00:00:00":
			time.sleep(2)
			U.restartMyself(param="", reason="bad BLE  =00..00", python3=usePython3)

		data = []
		for beacon in beaconsThisReadCycle:
			verbose = beacon == "xE4:7E:5F:23:82:1C"
			if verbose: U.logger.log(20,u" mac:{}, in use:{},  in  beacon_ExistingHistory:{}".format(beacon, beacon in onlyTheseMAC ,beacon in beacon_ExistingHistory))
			if beacon not in beacon_ExistingHistory: continue
			if beacon_ExistingHistory[beacon]["fastDown"] : continue
			if len(beacon_ExistingHistory[beacon]["rssi"]) == 0: continue
			if time.time() - beacon_ExistingHistory[beacon]["timeSt"][-1] > 55: continue # do not resend old data
			try:
				if beacon_ExistingHistory[beacon]["count"] != 0:

					try: 	avePower = int(beacon_ExistingHistory[beacon]["txPower"]) #  /max(1,beacon_ExistingHistory[mac]["count"]-1)
					except: avePower = -60
					if verbose: U.logger.log(20, "mac:{}, avePower:{},  beacon_ExistingHistory txp:{}".format(beacon, avePower, beacon_ExistingHistory[beacon]["txPower"]))

					#avePower	=int(beacon_ExistingHistory[beacon]["txPower"]   /max(1,beacon_ExistingHistory[beacon]["count"]))
					if False and beacon not in onlyTheseMAC:
						U.logger.log(20,u" mac:{}, not in use,  sending".format(beacon))

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
						"typeOfBeacon": beacon_ExistingHistory[beacon]["typeOfBeacon"]
						}
					for xx in extraStates:
						if xx in beacon_ExistingHistory[beacon] and beacon_ExistingHistory[beacon][xx] !="": newData[xx]	= beacon_ExistingHistory[beacon][xx]
	
					downCount = 0
					data.append(newData)
					if verbose: U.logger.log(20,u"mac:{}  data:{} ".format(beacon, data))
					if verbose: U.logger.log(20,u"mac:{}  exH :{} ".format(beacon, beacon_ExistingHistory[beacon]))

					if  (beacon == trackMac or trackMac =="*") and logCountTrackMac >0:
						writeTrackMac("MSG===  ","data:{}".format(newData), beacon)
					beacon_ExistingHistory[beacon]["count"] = 1
					beacon_ExistingHistory[beacon]["lastMessageSend"] = time.time()
			except	Exception as e:
				U.logger.log(30,"", exc_info=True)
				U.logger.log(30, " error composing mac:{}, beaconsThisReadCycle \n{}".format(beacon, beaconsThisReadCycle[beacon]))

		nMessages = len(data)
		if nMessages >1: downCount = 0
		U.sendURL({"msgs":data,"pi":str(G.myPiNumber),"piMAC":myBLEmac,"secsCol":int(time.time()-timeAtLoopStart),"reason":mapReasonToText[reasonMax]})
		#U.logger.log(20, "beacons collected:{}".format(len(data)))

		# save active iBeacons for getbeaconparameters() process
		copyBE = copy.copy(beaconsOnline)
		for be in copyBE:
			if time.time() - copyBE[be] > 90:
				del beaconsOnline[be]
		U.writeJson("{}temp/beaconsOnline".format(G.homeDir), beaconsOnline, sort_keys=False, indent=0)
		return nMessages
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 0



#################################
def composeMSGForThisMacOnly(mac):
	global beaconsThisReadCycle, beacon_ExistingHistory, mapReasonToText
	global myBLEmac, secsCollected
	global trackMac, logCountTrackMac
	global extraStates
	try:
		try: 	avePower = int(beacon_ExistingHistory[mac]["txPower"]) #  /max(1,beacon_ExistingHistory[mac]["count"]-1)
		except: avePower = -60
		if beacon_ExistingHistory[mac]["fastDown"]:	aveSignal = -999 
		else:										aveSignal = int(beacon_ExistingHistory[mac]["rssi"][-1])
		if avePower > -200:
			beaconsOnline[mac] = int(time.time())
		beacon_ExistingHistory[mac]["reason"][-1] = max(1, beacon_ExistingHistory[mac]["reason"][-1] )
		r  = min(10,beacon_ExistingHistory[mac]["reason"][-1])
		rr = mapReasonToText[r]
		data = {"mac": mac,
			"reason": rr, 
			"rssi": aveSignal, 
			"txPower": avePower, 
			"count": max(1,beacon_ExistingHistory[mac]["count"]-1),
			"typeOfBeacon": beacon_ExistingHistory[mac]["typeOfBeacon"]
			}
		for xx in extraStates: 
			if beacon_ExistingHistory[mac].get(xx,"") != "": data[xx]	= beacon_ExistingHistory[mac][xx]

		beacon_ExistingHistory[mac]["lastMessageSend"] = time.time()
		U.sendURL({"msgs":[data],"pi":str(G.myPiNumber),"piMAC":myBLEmac,"secsCol":1,"reason":rr})
		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("MSG-s   ", "sending single msg:{}".format(data),mac)
		return 1
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 0



#################################
def checkIfinMotion(mac, tag):
	global collectMsgs, loopMaxCallBLE, signalDelta
	global onlyTheseMAC, beaconsThisReadCycle, beacon_ExistingHistory
	global reasonMax

	try:
		if mac not in beacon_ExistingHistory: 			 return False
		if mac not in beaconsThisReadCycle: 			 return False
		if tag not in knownBeaconTags:					 return False
		if beacon_ExistingHistory[mac]["count"] <1:		 return False # need at least 1 messages

		if "inMotion" not in beaconsThisReadCycle[mac] or "inMotion" not in beacon_ExistingHistory[mac]:
														 return False

		if beaconsThisReadCycle[mac]["inMotion"] == "":  return False

		if "lastMessageSend" not in beacon_ExistingHistory[mac]:
														 return False
		#U.logger.log(20,u"mac:{} pasesd-1".format(mac))

		if time.time() - beacon_ExistingHistory[mac]["lastMessageSend"] < 1.1: 
														 return False
		#U.logger.log(20,u"mac:{} passed-2 beaconsThisReadCycle:{} ".format(mac, beaconsThisReadCycle[mac]))


		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("motion? ", " beaconsThisReadCycle[inMotion]:{}".format(beaconsThisReadCycle[mac]["inMotion"]),mac)

		if (
			( beaconsThisReadCycle[mac]["inMotion"] or beaconsThisReadCycle[mac]["inMotion"] != beacon_ExistingHistory[mac]["inMotion"] ) or 
			( "position" in beacon_ExistingHistory[mac] and "position" in beaconsThisReadCycle[mac] and beaconsThisReadCycle[mac]["position"] != beacon_ExistingHistory[mac]["position"])
			) :
			beacon_ExistingHistory[mac]["reason"][-1] = 9 
			beacon_ExistingHistory[mac]["inMotion"] = beaconsThisReadCycle[mac]["inMotion"]
			if "position" in beaconsThisReadCycle[mac]:
				beacon_ExistingHistory[mac]["position"] = beaconsThisReadCycle[mac]["position"]
			composeMSGForThisMacOnly(mac)	
			U.logger.log(20,u"mac:{} detected move/stop to pos:{}, inMotion:{}".format(mac, beacon_ExistingHistory[mac]["position"], beacon_ExistingHistory[mac]["inMotion"]))
			return True

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,u"mac:{}\nbeaconsThisReadCycle:{}".format(mac, beaconsThisReadCycle ))

	return False


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

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
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

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,u"mac {}:  beacon_ExistingHistory={}".format(beacon, beacon_ExistingHistory[beacon]))

	return



#################################, check if signal strength is acceptable for fastdown 
def checkIfBeaconIsBack(mac):
	global trackMac, logCountTrackMac
	global beacon_ExistingHistory 
	try:
		#U.logger.log(20,u"mac{} checkIfBeaconIsBack trackMac:{}  logCountTrackMac:{}".format(mac, trackMac, logCountTrackMac))
		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac( "New?    ", "checking if Beacon is back " ,mac)

		if  mac not in beacon_ExistingHistory: return False

		if  len(beacon_ExistingHistory[mac]["timeSt"]) == 0:
			#U.logger.log(30,u"mac{} checkIfBeaconIsBack empty history={}".format(mac,beacon_ExistingHistory[mac]))
			return False

		if beacon_ExistingHistory[mac]["count"] == 1 or len(beacon_ExistingHistory[mac]["timeSt"]) < 2 or time.time() - beacon_ExistingHistory[mac]["timeSt"][-1] > 30  or beacon_ExistingHistory[mac]["fastDown"]:
			if  (mac == trackMac or trackMac == "*") and logCountTrackMac >0:
				writeTrackMac( "New!    ", "beacon is back, send message" ,mac)
			if mac in beacon_ExistingHistory: 
				if mac in fastDownList: 		beacon_ExistingHistory[mac]["reason"][-1] = 4 # beacon_fastdown is back
				else: 							beacon_ExistingHistory[mac]["reason"][-1] = 5 # beacon is back
			else:								beacon_ExistingHistory[mac]["reason"][-1] = 2 # beacon is new
			beacon_ExistingHistory[mac]["fastDown"] = False
			composeMSGForThisMacOnly(mac)
			return True

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return False
		


#################################
def checkIfBLErestart():
	if os.path.isfile(G.homeDir + "temp/BLErestart") :
		os.remove(G.homeDir + "temp/BLErestart")
		U.logger.log(30," restart of BLE stack requested") 
		return True
	return False



#################################
def doFastSwitchBotPress(mac, trigOnOff):
	global fastBLEReaction
	global fastBLEReactionLastAction
	try:

		"""
		fastBLEReaction::fastBLEReaction:{u'B8:7C:6F:1A:D9:65': 
			{u'cmd': {u'pulseLengthOn': u'0', u'repeat': u'2', u'pulseLengthOff': u'0.0', u'cmd': u'pulses', u'repeatDelay': u'0', u'mac': u'F9:A6:49:9A:DF:85', u'pulses': u'1', u'mode': u'batch', u'pulseDelay': u'0.0', u'outputDev': 1323447574," u'sensorTriggerValue': u'on'}, u'indigoIdOfSwitchbot': 1323447574, u'pwdOfSwitchbotRPI': u'karl123.',
			 u'IdOfSwitchbotRPI': u'pi', u'macOfSwitchbot': u'F9:A6:49:9A:DF:85', u'piU': u'12', u'IPOfSwitchbotRPI': u'192.168.1.35'}}
		"""
		#U.logger.log(20,"mac:{}, trigOnOff:{}, fastBLEReaction:{}".format(mac, trigOnOff, fastBLEReaction)) 
		if mac not in fastBLEReaction: return 
		if mac in fastBLEReactionLastAction and time.time() - fastBLEReactionLastAction[mac] < 2: return 
		fastBLEReactionLastAction[mac] = time.time()

		macOfSwitchbot 		= fastBLEReaction[mac]["macOfSwitchbot"]
		IPOfSwitchbotRPI 	= fastBLEReaction[mac]["IPOfSwitchbotRPI"]
		IdOfSwitchbotRPI	= fastBLEReaction[mac]["IdOfSwitchbotRPI"]
		pwdOfSwitchbotRPI 	= fastBLEReaction[mac]["pwdOfSwitchbotRPI"]

		swbotcmd 			= fastBLEReaction[mac]["cmd"]
		sensorTriggerValue 	= swbotcmd["sensorTriggerValue"]
		if sensorTriggerValue != trigOnOff:
			#U.logger.log(20,"mac:{}, rejected due to trigOnOff:{}!={}:sensorTriggerValue ".format(mac, trigOnOff, sensorTriggerValue)) 
			return 

		# local action:
		#swbotcmd = '{{"mac":"{}","cmd":"onOff","onOff":1,"mode":"batch","source":"doFastSwitchBotPress"}}'.format(macOfSwitchbot)
		#cmd = '{{"mac":"{}","pulses":1,"pulseLengthOn":2,"pulseLengthOff":2,"source":"doFastSwitchBotPress"}}'.format(switchBotMAC)
		U.logger.log(20,"switchbot input ip# from:{}, to:{}; command: {}".format(G.ipAddress, IPOfSwitchbotRPI, swbotcmd) )
		if IPOfSwitchbotRPI == G.ipAddress: fName = "{}temp/switchbot.cmd".format(G.homeDir)
		else:								fName = "{}temp/switchbot.sendToOtherRpi".format(G.homeDir)

		#write command to file, then eitehr execute locally or at other rpi through sftp
		f = open(fName,"w")
		f.write(json.dumps(swbotcmd))
		f.close()

		if IPOfSwitchbotRPI == G.ipAddress: 
			return 

		sftpcmd = "sudo /usr/bin/sftp {}@{}".format(IdOfSwitchbotRPI, IPOfSwitchbotRPI) 
		U.logger.log(20,"sftp command: {},  local ip:{}<".format(sftpcmd, G.ipAddress) )
		expC = pexpect.spawn(sftpcmd)
		ret = expC.expect(["sftp>","assword","yes/no",pexpect.TIMEOUT], timeout=10)
		U.logger.log(20,"ret1: {}".format(ret) )
		if ret == 2:
			U.logger.log(20,u"... send yes: {}-{}".format(expC.before,expC.after))
			expC.sendline("yes\r")
			ret = expC.expect(["sftp>","assword",pexpect.TIMEOUT], timeout=10)
			U.logger.log(20,"ret2:{}".format(ret) )
		if ret == 1:
			expC.sendline(pwdOfSwitchbotRPI)
			ret = expC.expect(["sftp>",pexpect.TIMEOUT], timeout=10)
			U.logger.log(20,"ret3:{}".format(ret) )
		if ret == 0:
			expC.sendline("put /home/pi/pibeacon/temp/switchbot.sendToOtherRpi /home/pi/pibeacon/temp/switchbot.cmd")
			ret = expC.expect(["/home/pi/pibeacon/temp/switchbot.sendToOtherRpi",pexpect.TIMEOUT], timeout=10)
			U.logger.log(20,"ret4:{}".format(ret) )
			if ret == 0:
				U.logger.log(20,"file send to {} ".format(IPOfSwitchbotRPI)) 
				expC.sendline("quit")
				return 

			expC.sendline("quit")
			U.logger.log(20,u"... failed: {}-{}".format(expC.before,expC.after))
			return 
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 



#################################
#################################
######## BLE SENSORS ############
#################################
######################import bluetooth._bluetooth###########
def doSensors( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min):
	global BLEsensorMACs
	bl = ""
	try:

		#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,u"mac:{}; checking  in BLEsensorMACs:{}".format(mac, mac in BLEsensorMACs)) 
		if mac not in BLEsensorMACs:
			return tx, bl, UUID, Maj, Min, False

		#U.logger.log(20,u"doSensors {}   typeId:{:20s}; hexData:{}".format(mac, type, hexData))
 


		for sensor in BLEsensorMACs[mac]:
			if sensor == "BLEmyBLUEt":  								
				return domyBlueT( mac, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor == "BLERuuviTag":
				return  doRuuviTag( mac, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor.find("BLEiBS") >-1:
				return  doBLEiBSxx( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor.find("BLEminew") >-1:
				return  doBLEminew( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor.find("BLEiSensor") >-1:
				return  doBLEiSensor( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor.find("BLESatech") >-1:
				return  doBLESatech( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor.find("BLEapril") >-1:
				return  doBLEapril( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor.find("BLEswitchbotTempHum") >-1:
				return  doBLEswitchbotTempHum( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor in ["BLEswitchbotContact","BLEswitchbotMotion"]:
				return  doBLEswitchbotSensor( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor.find("BLEXiaomiMiTempHumRound") >-1:
				return  doBLEXiaomiMi( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)
			if sensor.find("BLEXiaomiMiTempHumClock") >-1:
				return  doBLEXiaomiMi( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor.find("BLEXiaomiMiformaldehyde") >-1:
				return  doBLEXiaomiMi( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor.find("BLEgoveeTempHum") >-1:
				return  doBLEgoveeTempHum( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

			if sensor.find("BLEblueradio") >-1:
				return  doBLEBLEblueradio( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor)

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return  tx, bl, UUID, Maj, Min, False

#################################


def doBLEswitchbotSensor(mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor):
	global BLEsensorMACs, sensors
	global switchbotData
	try:
		if len(hexData) < 30: return tx, "", UUID, Maj, Min, False

		hexData = hexData[12:]
		"""
		type1
                                MAC#-------- 
											  xx          bright changes counter 00-ff
											     b        brightnesss &b000000010  10=bright; 01 = dim
											     		+ 4 = 5/6
											       V      Version = 1.2? 
											 	   secs motion secs since last int("xxxx",16) event 64k seconds

			11 02 0106 0D FF6909 D99919AE2A81 4C 6 C 0018      
            11 02 0106 0D FF6909 D99919AE2A81 32 6 C 000D  BF;
			01 23 4567 89 112345 678921234567 89 3 1 2345

		type2
						     bb : int("xx",16)&0b01111111
							    cccc	  = secs since last motion = int(cccccc,64)
									ff    : dimm    	= ff & 0b0001
											bright  	= ff & 0b0010
											mediumSsns 	= ff & 0b0100
											shortSens  	= ff & 0b1000
											longSens   	= ff & 0b1100 == 0
			0A 09 163DFD7300 D6 001001   rssi: C0
			0A 09 163DFD7380 64 308106   rssi: BC
			0A 09 163DFD7380 64 32EB06B9;

			01 23 4567891123 45 678921         23

		type3
							 BB:								0-1	int("BB",16)&0b01111111   = battery 0-64 = 0-100 some times first bit  is on, dont know why
							   G:								2	int("G",16)               = mostly 0 ?
							    K:								3	int("K",16)               = closed=x00x, open=x01x, long open=x10x if bright= xxx1
							     ssss							4-7 int("ssss",16)            = secs since ??? restarts once at battery start, or device soft restart = when type4 ssss hight bit is  0-> 1
							         tttt:						8-11int("tttt",16)            = 0-2**16-1 secs since last open / closed 
										 o:						12	int("o",16)&0b1100        =  abxx  ab changes when opened 01 -> 10 -> 11 -> 01
							              C :					13	int("C",16)&0b0001        = 1-15 counter for press button
			0D 0C 163DFD6400 E4020018001B40                     
			01 23 4567891123 45678921234567
                             01234567891123

		type4   nothing for motion, only for bright/dim
								MAC#-------- 
											  pp 				0-1	int(w,16)                 = 0-255 secs press counter (not seconds) 
											    W				2	int(w,16)  RAyz=  R =1xxx = 10 secs after boot stays ?? until ?? powersave ..?, some times just switches
											    W				2	int(w,16)  0A00 , A= x1xx = 1=bright, 0=dim    
											    W				2	int(w,16)  b0yz=  y= xx10 = left open
											    W				2	int(w,16)  b0yz=  z= xx01 = open
											    W				2	int(w,16)  b0yz=  z= xx00 = close
												 H 				3	int("H"")                 = 1100  ???   using  last 2 bits for operflow for ssss or tttt
												  ssss :		4-7	int("ssss",16)            = secs since ??? restarts once at battery start, or device soft restart = when type4 ssss hight bit is  0-> 1
													  tttt :	8-11int("tttt",16)&0b00000000 = 0-2**16-1 secs since last open/close/left open  
														  o:	12	int("o",16)&0b1100        =  abxx  ab changes when opened 01 -> 10 -> 11 -> 01
														   C:	13	int("b",16)&0b0001        = 1-15 counter for press button
			14 020106 10 FF6909 C9D180A1AA9C  5B0C06A106871E   
	msg1-- 2 b   1  2 
	msg2-- 16 b          1 2 3  4 5 6 7 8 9   1 2 3 4 5 6
			01 234567 89 112345 678921234567  89312345678941   
                                              01234567891123
		"""
		doPrint = False#mac == "E4:7E:5F:23:82:1C"

		if   "110201060DFF6909"+macplain in  hexData: dType = 1  # for motion sensor
		elif "0A09163DFD73"  			 in  hexData: dType = 2  # for motion sensor
		elif "0D0C163DFD64"				 in  hexData: dType = 3  # for contact sensor
		elif "1402010610FF6909"+macplain in  hexData: dType = 4  # for contact sensor
		else:								 		  dType = 0

		if dType == 0: 
			if  doPrint: U.logger.log(20, u"mac:{}, sens:{}; dType:{}; len(hexData):{}; hexData:{};".format(mac, sensor, dType, len(hexData), hexData ))
			return tx, "", UUID, Maj, Min, False
		doPrint = doPrint #and (dType == 1 or dType == 2) 
		if  doPrint: U.logger.log(20, u"mac:{}, sens:{}; dType:{}; len(hexData):{}; hexData:{};".format(mac, sensor, dType, len(hexData), hexData ))

		lightCounter 	= -1
		light	  		= ""
		motion			= False
		motionDuration	= -1
		secsSinceLastM	= -1
		batteryLevel	= ""
		lastMotion	 	= -1
		dontknow		= 0

		if switchbotData == {}:
			jData, raw  = U.readJson("{}temp/switchbot.data".format(G.homeDir))
			if len(raw) > 10:
				switchbotData = jData

		if mac not in switchbotData or "buttonCounter" not in switchbotData[mac]:
			switchbotData[mac] = {}
			switchbotData[mac]["buttonCounter"]		= ""
			switchbotData[mac]["onOff"]				= ""
			switchbotData[mac]["status4"]			= -1
			switchbotData[mac]["BlindicatorBit"]	= -1
			switchbotData[mac]["light"]				= ""
			switchbotData[mac]["openCounter"]		= -1
			switchbotData[mac]["resetCounter"]		= -1
			switchbotData[mac]["closed"]			= -1
			switchbotData[mac]["openCloseInd"]		= -1
			switchbotData[mac]["shortOpen"]			= -1
			switchbotData[mac]["longOpen"]			= -1
			switchbotData[mac]["timeButton"]		= 0
			switchbotData[mac]["timeClosed"]		= 0
			switchbotData[mac]["timeShortOpen"]		= 0
			switchbotData[mac]["timeLongOpen"]		= 0
			switchbotData[mac]["timelightChange"]	= 0
			switchbotData[mac]["counter"] 			= -1
			switchbotData[mac]["counternew"] 		= 0
			switchbotData[mac]["secsSinceLastEvent"] = 0
			switchbotData[mac]["sensitivity"] =		 "shortRange"
			switchbotData[mac]["brightness"] 		= "dim"


		## motion Sensor
		if dType == 1:
			hData 			= hexData[28:36] #686C0016
			lightCounter 	= int(hData[0:2],16)
			flag	  		= int(hData[2],16)
			light	  		= "bright" if flag&0b0011 == 2 else "dim"
			motion			= int(hData[2],16)  & 0b0100 != 0
			dontknow		= (int(hData[3],16) & 0b1110) 
			secsSinceLastM	= int(hData[4:8],16) + ((int(hData[3],16)&0b0001) * 65536)
			if motion:
				lastMotion 		= int(time.time() - secsSinceLastM) #epoch time at last motion
				motionDuration 	= secsSinceLastM
				if BLEsensorMACs[mac][sensor]["lastMotion"]  > 0:
					lastMotion 	= max(lastMotion, BLEsensorMACs[mac][sensor]["lastMotion"] )
					BLEsensorMACs[mac][sensor]["lastMotion"] =  lastMotion
				else:
					BLEsensorMACs[mac][sensor]["lastMotion"] = lastMotion
			BLEsensorMACs[mac][sensor]["secsSinceLastM"] = secsSinceLastM
			if BLEsensorMACs[mac][sensor]["motionDuration"] > BLEsensorMACs[mac][sensor]["secsSinceLastM"]: BLEsensorMACs[mac][sensor]["motionDuration"] = BLEsensorMACs[mac][sensor]["secsSinceLastM"]
			if BLEsensorMACs[mac][sensor]["motionDuration"] ==-1: BLEsensorMACs[mac][sensor]["motionDuration"] = BLEsensorMACs[mac][sensor]["secsSinceLastM"]
						
			dd={   # the data dict to be send 
							'onOffState': 			motion,
							'light': 				light,
							'sensitivity': 			switchbotData[mac]["sensitivity"],
							'lightCounter': 		lightCounter,
							'lastOn': 				lastMotion,
							'motionDuration': 		motionDuration,
							'mac': 					mac,
							"rssi":					int(rx)
					}
			if BLEsensorMACs[mac][sensor]["batteryLevel"] != "": 	dd["batteryLevel"] 	 = BLEsensorMACs[mac][sensor]["batteryLevel"]
			if lastMotion > -1: 									dd["lastMotion"] 	 = BLEsensorMACs[mac][sensor]["lastMotion"]
			if BLEsensorMACs[mac][sensor]["motionDuration"] > -1: 	dd["motionDuration"] = BLEsensorMACs[mac][sensor]["motionDuration"]

			if motion:	updateEvery = 9
			else:		updateEvery = 40

			#U.logger.log(20, u"mac:{},  light:{}-{:08b}".format(mac, light, flag))


			trig = ""
			if						time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]   > updateEvery:  	trig += "timeSinceLastUpdate/"  	# send min every xx secs
			if  lastMotion > 0	and abs(lastMotion - BLEsensorMACs[mac][sensor]["lastMotion"]) > 1:  			trig += "timeSinceLastMotion/"
			if light != ""		and light != BLEsensorMACs[mac][sensor]["light"]:  								trig += "lightChange/"
			if 						motion  != BLEsensorMACs[mac][sensor]["motion"]:							trig += "motion/"

			if True:
										BLEsensorMACs[mac][sensor]["motion"]			= motion
										BLEsensorMACs[mac][sensor]["light"]				= light
			if lastMotion != -1:		BLEsensorMACs[mac][sensor]["lastMotion"]		= lastMotion
			if motionDuration != -1:	BLEsensorMACs[mac][sensor]["motionDuration"]	= motionDuration

			if trig != "":
						dd["trigger"] = trig.strip("/")
						if  doPrint: U.logger.log(20, "mac:{} updindigo:{}; dd:{}".format( mac, updateEvery,  dd)  )
						# compose complete message
						U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})
						# remember last values
						BLEsensorMACs[mac][sensor]["lastUpdate"] 		= time.time()
						fastSwitchBotPress = "on" if motion else ""
						if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)
			if doPrint: U.logger.log(20, u"mac:{}, trig:{}, lastMotion:{}".format(mac, trig, updateEvery, lastMotion ))

					
			UUID = sensor
			Maj  = mac
			return  tx, batteryLevel, UUID, Maj, Min, False		


		if dType == 2:
			hData3 = hexData[20:22]
			flags  = int(hData3, 16)
			dimm    = flags & 0b0001
			bright  = flags & 0b0010
			mediumS = flags & 0b0100
			shortS  = flags & 0b1000
			longS   = flags & 0b1100 == 0
			hData1 = hexData[16:20]
			secsSinceLastEvent = int(hData1,32)
			hData2 = hexData[14:16]
			BL = int(hData2,16)&0b01111111
			if doPrint: U.logger.log(20, u"mac:{}, bat:{}-hex:{}, secsSinceLastEvent:{}-hex:{}, flags:{}-{:b}".format(mac, BL, hData2, secsSinceLastEvent, hData1, hData3, flags))
			BLEsensorMACs[mac][sensor]["batteryLevel"] = BL
			switchbotData[mac]["brightness"] = "bright" if bright else "dim"
			if mediumS: 	switchbotData[mac]["sensitivity"]  = "long"
			elif shortS:	switchbotData[mac]["sensitivity"]  = "medium"
			else:			switchbotData[mac]["sensitivity"]  = "long"
			switchbotData[mac]["secsSinceLastEvent"] = secsSinceLastEvent
			BLEsensorMACs[mac][sensor]["secsSinceLastEvent"] = secsSinceLastEvent
			return  tx, BLEsensorMACs[mac][sensor]["batteryLevel"], UUID, Maj, Min, False		


		## contact sensor

		## for type 3/4 get most of the info from type3, then send out package
		if dType == 3:								#01 2 3 4567 8901 2 3 pos
			hData 				= hexData[14:28]	#E4 0 2 0018 001B 4 0 
			BL					= int(hData[0:2],16)&0b01111111
			BlindicatorBit		= int(hData[0:2],16)&0b10000000 >>6
			closed1				= int(hData[3],16)&0b00000110 == 0b00000000
			shortOpen 			= int(hData[3],16)&0b00000110 == 0b00000010
			longOpen 			= int(hData[3],16)&0b00000110 == 0b00000100
			light 				= "bright" if int(hData[3],16)&0b00000001 == 1 else "dim"
			resetCounter 		= int(hData[4:8],16)
			openCounter 		= int(hData[8:12],16)
			openCloseInd		= int(hData[12],16)>>2
			buttonCounter		= int(hData[13],16)

			if switchbotData[mac]["status4"] == -1: # wait for at least one package from dtype =4
				if  doPrint: U.logger.log(20, u"mac:{}, sens:{}; dType:{}; ret 1".format(mac, sensor, dType) )
				return tx, BL, UUID, Maj, Min, False

			trig = ""
			onOff = ""
			if closed1: 															switchbotData[mac]["timeClosed"] 		= round(time.time(),1);							onOff += "cl1/"
			if 					(closed1	!= switchbotData[mac]["closed"]): 																			trig += "cl2/"
			if closed1 and		(closed1	!= switchbotData[mac]["closed"]): 		switchbotData[mac]["timeClosed"] 		= round(time.time(),1); 	trig += "cl3"
			if shortOpen	and (shortOpen	!= switchbotData[mac]["shortOpen"]): 	switchbotData[mac]["timeShortOpen"]		= round(time.time(),1); 	trig += "shortO/" ; onOff += "so/"
			if longOpen		and (longOpen	!= switchbotData[mac]["longOpen"]):		switchbotData[mac]["timeLongOpen"] 		= round(time.time(),1); 	trig += "longOp" 
			if 					light		!= switchbotData[mac]["light"]: 		switchbotData[mac]["timelightChange"]	= round(time.time(),1); 	trig += "lightC/" 
			if 					buttonCounter != switchbotData[mac]["buttonCounter"]: switchbotData[mac]["timeButton"]		= round(time.time(),1); 	trig += "button/" 

			if not shortOpen and not longOpen: 																																onOff += "notSL/"
			# if very short close, it seems closed is false but counter gets updated (+2)
			if 					switchbotData[mac]["counternew"] >1: 				switchbotData[mac]["timeClosed"] 		= round(time.time(),1);		trig += "cl4/" ; 	onOff += "cn/"
			if					BL			!= BLEsensorMACs[mac][sensor]["batteryLevel"]:																trig += "batLevel/" 
			if 					openCloseInd != switchbotData[mac]["openCloseInd"]: switchbotData[mac]["timeClosed"] 		= round(time.time(),1);		trig += "flag/" 
			if 					onOff != switchbotData[mac]["onOff"]: 																					trig += "onOff/" 
			switchbotData[mac]["onOff"] 			= onOff

			switchbotData[mac]["closed"] 			= closed1
			switchbotData[mac]["openCloseInd"] 		= openCloseInd
			switchbotData[mac]["resetCounter"] 		= resetCounter
			switchbotData[mac]["openCounter"]		= openCounter
			switchbotData[mac]["longOpen"] 			= longOpen
			switchbotData[mac]["BlindicatorBit"] 	= BlindicatorBit
			switchbotData[mac]["light"] 		 	= light
			switchbotData[mac]["resetCounter"] 		= resetCounter
			switchbotData[mac]["closed"] 			= closed1
			switchbotData[mac]["shortOpen"] 		= shortOpen
			switchbotData[mac]["longOpen"] 			= longOpen
			switchbotData[mac]["buttonCounter"] 	= buttonCounter
			BLEsensorMACs[mac][sensor]["batteryLevel"] = BL

		
			dd={   # the data dict to be send 
							'light': 				light,
							'counter': 				switchbotData[mac]["counter"],
							'onOffState': 			onOff !="",
							'buttonCounter':		switchbotData[mac]["buttonCounter"],
							'shortOpen': 			switchbotData[mac]["shortOpen"],
							'longOpen': 			switchbotData[mac]["longOpen"] ,
							'lastButton': 			switchbotData[mac]["timeButton"] ,
							'lastLightChange': 		switchbotData[mac]["timelightChange"] ,
							'lastOn': 				switchbotData[mac]["timeClosed"] ,
							'lastShortOpen': 		switchbotData[mac]["timeShortOpen"] ,
							'lastLongOpen': 		switchbotData[mac]["timeLongOpen"] ,
							'batteryLevel': 		BL,
							'sensitivity': 			switchbotData[mac]["sensitivity"],
							'mac': 					mac,
							"rssi":					int(rx)
					}

			if trig !="":	updateEvery = 0
			else:			updateEvery = 50
			if switchbotData[mac]["closed"] != closed1 or switchbotData[mac]["counternew"] >1: updateEvery = 0
			if updateEvery >0 and (time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]   > updateEvery): trig +="time"  	# send min every xx secs


			if doPrint: U.logger.log(20, u"mac:{}, updateEvery:{:2d}, bin:{:08b} , cl1:{} newC{:3d}, openC:{:3d}, c:{:3d}, resetC:{:3d}, CShort:{}, Bli:{}, st4:{}, flag:{}, dd:{:}, onOff:{}, trig:{}, ".format(mac, updateEvery, int(hData[3],16), closed1, switchbotData[mac]["counternew"] , openCounter, switchbotData[mac]["counter"], resetCounter, switchbotData[mac]["buttonCounter"], BlindicatorBit, switchbotData[mac]["status4"], openCloseInd, dd, onOff, trig))

			if trig != "":
						dd["trigger"] = trig.strip("/")
						if False and doPrint: U.logger.log(20, "mac:{} triggers:oneChange:{}; sending data ".format( mac, trig )  )
						# compose complete message
						U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})
						# remember last values
						BLEsensorMACs[mac][sensor]["lastUpdate"] 		= time.time()
						U.writeFile("temp/switchbot.data",json.dumps(switchbotData))
						switchbotData[mac]["counternew"] = 0

						fastSwitchBotPress = "on" if onOff !="" else "off"
						if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)
					
			UUID = sensor
			Maj  = mac
			return  tx, BLEsensorMACs[mac][sensor]["batteryLevel"], UUID, Maj, Min, False		

		if dType == 4:				#01 2 3 4567 8901 2 3 Pos
			hData = hexData[28:42]  #5B 0 C 06A1 0687 1 E 
			switchbotData[mac]["status4"] 		= int(hData[3],16)
			switchbotData[mac]["counternew"] 	= int(hData[0:2],16) - switchbotData[mac]["counter"]
			switchbotData[mac]["counter"] 		= int(hData[0:2],16)
			if  doPrint: U.logger.log(20, u"mac:{}, hData= 0-1:{:}; 2b:{:4b}; 3b:{:4b}; 4-7:{}; 8-11:{}; 12b:{:4b}; 13:{:2d}; ".format(mac,  hData[0:2],  int(hData[2],16),   int(hData[3],16), hData[4:8], hData[8:12], int(hData[12],16), int(hData[13],16)) )
			return tx, BLEsensorMACs[mac][sensor]["batteryLevel"], UUID, Maj, Min, False

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False




def doBLEswitchbotTempHum(mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor):
	global BLEsensorMACs, sensors
	try:
		if len(hexData) < 60: return tx, "", UUID, Maj, Min, False

		hexData = hexData[12:]
		"""
				        name string ------------------------                               th start:        
		1C 11 07 1B C5 D5 A5 02 00 B8 9F E6 11 4D 22 00 0D A2 CB   09 16 00 0D 63 D0 CE 00 11 04 curtain 
		1C 11 07 1B C5 D5 A5 02 00 B8 9F E6 11 4D 22 00 0D A2 CB   09 16 00 0D 63 D0 CE 00 11 04 curtain 
	NO !!  11 07 1B C5 D5 A5 02 00 B8 9F E6 11 4D 22 00 0D A2 CB   08-							  curtain ??
																   09 16 00 0D 63 90 E4 00 11 00  
																			   ^^ curtain = 63 = c
																				  ^^ calibrated  90 = 
																					 ^^ in motion
																						^^ light level / device chain

		   11 07 1B C5 D5 A5 02 00 B8 9F E6 11 4D 22 00 0D A2 CB   06-
        1C 11 07 1B C5 D5 A5 02 00 B8 9F E6 11 4D 22 00 0D A2 CB   09 16 00 0D 54 10 64 01 99 AD   DA
																		 start ------------------
																			   ^^ =type:
																					48 = H = switchbot (Hand),  63 = c = curtain,  73=s= motion sensor, 64= d= contactsensor, 54=T= temp , see: https://github.com/Danielhiversen/pySwitchbot/blob/master/switchbot/adv_parser.py
	pos:01 23 45 67 89 11 23 45 67 89 21 23 45 67 89 31 23 45 67   89 41 23 45 67 89 51 23 45 67   89 
	pos:                                                                 01 23 45 67 89 11 23 45 
																					 BB tt TT HH 	
        for other devices: 
																		 00 0D 48 D0 E1
																	  00 0D 62 00 64 00
																		 00 0D 48 90 00 low battery
																		 00 0D 48 D0 64
																		 00 0D 48 D0 DF 95%


	switchbot 
	pos:01 23 45 67 89 11 23 45 67 89 21 23 45 67 89 31 23 45 67   89 41 23 45 67 89 51 23 45 67   89 
		19 11 07 1B C5 D5 A5 02 00 B8 9F E6 11 4D 22 00 0D A2 CB   06 16 00 0D 48 10 5D   switchbot 
																			    H
																				   switch mode &10000000 / is on:  not(& 0b01000000) if _switch_mode else False,
																					bb & 01111111


		"""
		doPrint 		= False
		#if mac == "A4:C1:38:98:15:CB": doPrint 		= True
		out 			= ""
		startData = 42
		if doPrint: U.logger.log(20, u"mac:{}, sens:{}; startData:{}, len(hexData):{}; hexData:{};".format(mac, sensor, startData,  len(hexData), hexData ))
		if  "1C11071BC5D5A50200B89FE6114D22000DA2CB0916" not in  hexData: return tx, "", UUID, Maj, Min, False
		hData = hexData[startData:]
		if doPrint: U.logger.log(20, u"mac:{},  len(hexData):{}".format(mac, hData ))

		tempFra = int(hData[10:12].encode('utf-8'), 16) / 10.0
		tempInt = int(hData[12:14].encode('utf-8'), 16)
		if tempInt < 128:
			tempInt *= -1
			tempFra *= -1
		else:
			tempInt -= 128
		temp = tempInt + tempFra
		hum = int(hData[14:16].encode('utf-8'), 16) % 128
		#fahrenheit  = int(hData[8:10].encode('utf-8'), 16) &  0b10000000

		batteryLevel = int(hData[8:10].encode('utf-8'), 16) & 0b01111111
		model = chr(int(hData[4:6],16))
		mode  = int(hData[6:8],16)

		if doPrint: U.logger.log(20, u"mac:{}, temp:{},  hum:{}".format(mac,temp,hum ))
		trig = ""
		if time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]   > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]: trig+= "timeSinceLastUpdate/" 			# send min every xx secs
		if abs(temp - BLEsensorMACs[mac][sensor]["temp"]) > 0.5: trig+= "tempChange/" 
		if abs(hum - BLEsensorMACs[mac][sensor]["hum"]) > 2: trig+= "humChange/" 
		trig = trig.strip("/")

		dd={   # the data dict to be send 
						'temp': 		round(temp+ BLEsensorMACs[mac][sensor]["offsetTemp"],1),
						'hum': 			int(hum + BLEsensorMACs[mac][sensor]["offsetHum"]),
						'batteryLevel': batteryLevel,
						'model': 		model,
						'mode': 		mode,
						'mac': 			mac,
						'trig': 		trig,
						'mac': 			mac,
						"rssi":			int(rx)
				}

		if doPrint: U.logger.log(20, u"mac:{}, temp:{}, hum:{}, trig{}".format(mac, temp, hum, trig))

		if  trig !="":
					# compose complete message
					U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})
					# remember last values
					if  doPrint: U.logger.log(20, "mac:{} trig:{}; updateIndigoTiming:{}; send:{}".format( mac, trig,BLEsensorMACs[mac][sensor]["updateIndigoTiming"] ,  dd)  )
					BLEsensorMACs[mac][sensor]["lastUpdate"] 	= time.time()
					BLEsensorMACs[mac][sensor]["temp"]    	 	= temp
					BLEsensorMACs[mac][sensor]["hum"]    	 	= hum
					BLEsensorMACs[mac][sensor]["batteryLevel"]  = batteryLevel
		UUID = sensor
		Maj  = mac
		return  tx, batteryLevel, UUID, Maj, Min, False		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False



def doBLEBLEblueradio(mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor):
	global BLEsensorMACs, sensors
	try:
		if len(hexData) < 60: return tx, "", UUID, Maj, Min, False

		hexData = hexData[12:]
		"""
		blueradio sensor bug info from 
		https://www.blueradios.com/SensorBug%20Interface%20Specification%20v1.3.0.0a.pdf
		package
		ll	                       ll ID--------------   BB  Ct   typ mod       typ mod          typ         
		1A  02 01 05  03 02 0A 18  12 FF 85 00 02 00 3C  62  0B   41  02   20   42  16   2F 00   43   CC 01 B3, tag1:-1, tag2:18
		1A  02 01 06  03 02 0A 18  12 FF 85 00 02 00 3C  62  0B   41  02   20   42  16   26 00   43   5F 01   	                                                                           0A   FF   88 EC 00     09 02 CD 15   64 02
	pos:01  23 45 67  89 11 23 45  67 89 21 23 45 67 89  31  23   45  67   89   41  23   45 67   89   51 23  
		1A  02 01 05  03 02 0A 18  12 FF 85 00 02 00 7C  64  00   41  02   02   42  16   3A 00   43   93 01
		data can be any sequence, can be present or not  
		ct = config count, stys same only increments if config changes

		typ = 41: accel / open/close, 
						  mod=02: 
						open/close =   data 00/02

		typ = 42: light  mod info: 	rresolutionMaxV = bits 4,5, range = bits 2,3  data len = bit 0,1, eg "16" = 01 01 10
									range			= [1000, 4000, 16000, 64000]
									resolutionMaxV 	= [65535, 4095, 255, 15]
									light[lux]  = (signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] ) * range / resolutionMaxV

		typ = 43: temp;  
									temp = (signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] )*0.0625
		"""
		doPrint 		= False
		#if mac == "EC:FE:7E:10:9C:E7": doPrint = True
		if doPrint: U.logger.log(20, u"mac:{}, sensor:{} hexData:{}, tag1:{}, tag2:{}".format(mac, sensor,  hexData, hexData.find("03020A18"), hexData.find("FF85000200")))

		if hexData.find("03020A18") != 8:  
			return tx, "", UUID, Maj, Min, False
		if hexData.find("FF85000200") != 18:  
			return tx, "", UUID, Maj, Min, False


		rangeV			= [1000.,  4000., 16000., 64000.]
		rangeText		= [1,  4, 16, 64]
		resolutionMaxV 	= [65535., 4095., 255.,   15.]
		resolutionBits 	= [16, 12, 8,   4]

		onOff 			= BLEsensorMACs[mac][sensor]["onOff"]
		temp  			= BLEsensorMACs[mac][sensor]["temp"]
		illuminance 	= BLEsensorMACs[mac][sensor]["illuminance"]
		counter			= BLEsensorMACs[mac][sensor]["illuminance"]
		sensorSetup 	= {"temp":"","Accel":"","Light":""}
		p = 0
		lTot = len(hexData)

		p = 16
		lDat = int(hexData[p:p+2],16)*2 

		p = 30
		if doPrint: U.logger.log(20, u"mac:{}, sens:{}; passed 1".format(mac, sensor ))

		p = 30
		batteryLevel =  min(100,max(0,int( hexData[p:p+2],16)))

		p = 32
		counter =  min(100,max(0,int( hexData[p:p+2],16)))

		p = 34
		for nn in range(3):
			if p > lTot -8: break

			dType = hexData[p:p+2]

			if doPrint: U.logger.log(20, u"mac:{}, sens:{}; p:{}, tot char:{}, dType:{}, hexData:{}".format(mac, sensor, p, lTot, dType, hexData[p:-2] ))

			if dType == "41":
				if hexData[p+2:p+4] == "02":
					onOff = hexData[p+4:p+6] != "02"
					sensorSetup["Accel"] = "Op/Cl"
				p += 6		
				#if doPrint: U.logger.log(20, u"mac:{}, sens:{}; onOff:{}".format(mac, sensor, onOff ))

			elif dType == "42":
				testHEX		= hexData[p+2:p+4]
				testNumber  = int(testHEX ,16) & 0b00111111 
				dataLen 	=              testNumber   & 0b00000011 
				rangeInd 	= max(0,min(3,(testNumber   & 0b00001100) >>2 )) 
				resInd	 	= max(0,min(3,(testNumber   & 0b00110000) >>4 )) 
				if dataLen == 2:
					illuminance = round(int(hexData[p+6:p+8] + hexData[p+4:p+6],16 ) * rangeV[rangeInd] / resolutionMaxV[resInd],1)
					p += 8		
					sensorSetup["Light"] = "range={}k,{}b".format(rangeText[rangeInd],resolutionBits[resInd])
				elif dataLen == 1:
					illuminance = round(int(hexData[p+4:p+6],16) * rangeV[rangeInd] / resolutionMaxV[resInd],1)
					sensorSetup["Light"] = "range={}k,{}b;".format(rangeText[rangeInd],resolutionBits[resInd])
					p += 6		
				if doPrint: U.logger.log(20, u"mac:{}, sens:{}; illuminance:{},  dataLen:{}, rangeInd:{}, range:{}, resInd:{} res:{}, testHEX:{},testbin:{:6b} testNumber:{}, rangeX:{}, resX:{}, hexData".format(mac, sensor, illuminance, dataLen, rangeInd, rangeV[rangeInd] ,resInd,resolutionMaxV[resInd], testHEX,testNumber, testNumber, testNumber & 0b00001100, testNumber & 0b00110000 , hexData[p:p+8]))

			elif dType == "43":
				temp = round(signedIntfrom16( hexData[p+4:p+6] + hexData[p+2:p+4] )*0.0625,1) + BLEsensorMACs[mac][sensor]["offsetTemp"]
				sensorSetup["temp"] = "16b"
				#if doPrint: U.logger.log(20, u"mac:{}, sens:{}; temp:{}, hacData:{}".format(mac, sensor, temp,hexData[p+2:p+6] ))
				p += 6		

			else: # this is not a std tag, skip and try to find next
				nextFound = False
				for ii in [2,4,6,8]:
					if p + ii < lTot -2:
						if hexData[p+ii:p+ii+2] in ["41","42","43"]:
							p += (ii - 2)
							nextFound = True
							break
				#if doPrint: U.logger.log(20, u"mac:{}, sens:{}; p:{}, dType:{} not found, break".format(mac, sensor, p, dType ))
				if not nextFound: break
		ss = u""
		for item in sensorSetup:
			ss += item+u":"+sensorSetup[item]+u";"
		sensorSetup = ss.strip(u";")


		BLEsensorMACs[mac][sensor]["nMessages"] +=1 

		dd={   # the data dict to be send 
						'temp': 		round(temp+ BLEsensorMACs[mac][sensor]["offsetTemp"],1),
						'illuminance':	illuminance, 
						'onOff': 		onOff, 
						'sensorSetup':	sensorSetup, 
						'batteryLevel': batteryLevel, 
						'mac': 			mac,
						"rssi":			int(rx)
				}

		trigTime 	= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]   > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
		trigTemp	= abs(temp - BLEsensorMACs[mac][sensor]["temp"]) > 0.5
		trigLux		= (illuminance < 20 and abs(illuminance - BLEsensorMACs[mac][sensor]["illuminance"]) > 4) or (illuminance > 20 and abs(illuminance - BLEsensorMACs[mac][sensor]["illuminance"])/max(2,BLEsensorMACs[mac][sensor]["illuminance"]) > 0.1) #10%
		trigonOff	= onOff != BLEsensorMACs[mac][sensor]["onOff"]

		if doPrint: U.logger.log(20, u"mac:{}, temp:{}, illuminance:{}, counter:{}, triggers:{};{};{}".format(mac, temp, illuminance, counter, trigTime, trigTemp, trigLux))

		if  trigTime or trigTemp or trigLux or trigonOff:
					# compose complete message
					U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})

					# remember last values
					if doPrint: U.logger.log(20, "mac:{} triggers: Time:{}; temp:{}; lux:{}, onOff:{}; updateIndigoTiming:{}; send:{}".format( mac, trigTime , trigTemp , trigLux, trigonOff,BLEsensorMACs[mac][sensor]["updateIndigoTiming"] ,  dd)  )
					BLEsensorMACs[mac][sensor]["lastUpdate"]	= time.time()
					BLEsensorMACs[mac][sensor]["temp"]			= temp
					BLEsensorMACs[mac][sensor]["illuminance"]	= illuminance
					BLEsensorMACs[mac][sensor]["onOff"]			= onOff
					BLEsensorMACs[mac][sensor]["batteryLevel"]	= batteryLevel

		UUID = sensor
		Maj  = mac
		return  tx, batteryLevel, UUID, Maj, Min, False		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False

#################################


def doBLEgoveeTempHum(mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor):
	global BLEsensorMACs, sensors
	try:
		if len(hexData) < 60: return tx, "", UUID, Maj, Min, False

		hexData = hexData[12:]
		"""
		govee package  structure:


		_D774
		_15CB
09475648
		after mac#:
		GVH5177_C097:
				  name string ------------------------                                  mfg  type:        3byte data (1,2,3) + battery level
		1F  0D   09 47 56 48 35 31 37 37 5F 43 30 39 37   03 03 88 EC   02 01 05   09   FF   01 00 01 01  03 68 C1   64
	pos:01  23   45 67 89 11 23 45 67 89 21 23 45 67 89   31 23 45 67   89 41 23   45   67   89 51 23 45  67 89 61   23

		GVH5075_5F5E
		1F  0D   09 47 56 48 35 30 37 35 5F 35 46 35 45   03 03 88 EC   02 01 05   09   FF   88 EC 00     03 6C 8D      64 00
	pos:01  23   45 67 89 11 23 45 67 89 21 23 45 67 89   31 23 45 67   89 41 23   45   67   89 51 23     45 67 89 61   23 24

		GVH5075_5F5E
		                                                                           0A   FF   88 EC 00     09 02 CD 15   64 02
	pos:01  23   45 67 89 11 23 45 67 89 21 23 45 67 89   31 23 45 67   89 41 23   45   67   89 51 23     45 67 89 61   23


		data = int(1,16)<<16 + int(2,16)<<8 + int(3,16)
		temp = data /10000
		hum = data %1000 / 10.
		"""
		doPrint 		= False
		#if mac == "A4:C1:38:98:15:CB": doPrint 		= True
		out 			= ""

		typeInfo 		= 	{"A":{"pos0":44, "type": "3+1",   "id":"09FF01000101"},
							 "B":{"pos0":44, "type": "3+1",   "id":"09FF88EC00"},
							 "C":{"pos0":44, "type": "2+2+1", "id":"0AFF88EC00"}
							}

		sens = ""
		#U.logger.log(20, u"mac:{}, sensor:{} hexData:{}".format(mac, sensor,  hexData))
		dataType 	= ""
		startData 	= -1
		for stype in  typeInfo:
			posTag = hexData.find(typeInfo[stype]["id"])
			if abs(posTag - typeInfo[stype]["pos0"]) < 3:
				sens 		= stype
				dataType 	= typeInfo[sens]["type"]
				startData 	= posTag + len(typeInfo[sens]["id"])
				break
		if sens == "": 
			return tx, "", UUID, Maj, Min, False


		if False and doPrint: U.logger.log(20, u"mac:{}, sens:{}; startData:{}, pos-id: {}, type:{}, len(hexData):{}".format(mac, sens, startData, typeInfo[sens]["pos0"], dataType, len(hexData) ))
		hData = hexData[startData:]

#-0.7, hData:8047375ACB, intData:8388608 + 18176 + 55  =  8406839, temp:840.7, hum:84.4
# hum = 34   8388608 + 27136 + 205 = -27341, temp:-2.7, intD:8415949, hum:94.9
#		 8421953 == -3.8

		if dataType == "3+1":
			intData1	 = int(hData[0:2],16)<<16
			intData2	 = int(hData[2:4],16)<<8 
			intData3	 = int(hData[4:6],16)
			intData 	 = intData1 + intData2 + intData3
			if intData >= 8388608: 
				intData = 8388608 - intData
			# need to fix negative numbers
			temp 		 = float(intData)/10000.
			temp 		 = round(temp,1)

			hum 		 = min(100,max(0,float( abs(intData)%1000 / 10.)))#  + 0.5)))

			batteryLevel = min(100,max(0,int( hData[6:8],16)))
			if doPrint: U.logger.log(20, u"mac:{}, hData:{}, intData:{} + {} + {} = {}, temp:{},  hum:{}".format(mac, hData,  intData1, intData2, intData3, intData,temp,hum ))

		elif dataType == "2+2+1":
			temp		 = int(hData[0:2],16)<<8 + int(hData[2:4],16)
			if temp > 32767: temp -= 65536
			temp		 = round(  temp /100.,  1)
			hum		 	 =  min(100,max(0,float(int(hData[4:6],16)<<8 + int(hData[6:8],16)) /100. + 0.5))
			batteryLevel =  min(100,max(0,int( hData[8:10],16)))

		else:
			return tx, "", UUID, Maj, Min, False

		out = ""
		if doPrint:
			for ii in range(0,len(hexData)-2,2):
				out+= hexData[ii:ii+2] + " "
				#U.logger.log(20, u"mac:{}, sensor:{} data string:{}, {}".format(mac,sensor,  hData,  out))
				pass

		BLEsensorMACs[mac][sensor]["nMessages"] +=1 

		dd={   # the data dict to be send 
						'temp': 		round(temp+ BLEsensorMACs[mac][sensor]["offsetTemp"],1),
						'hum': 			int(hum + BLEsensorMACs[mac][sensor]["offsetHum"]),
						'batteryLevel': batteryLevel, 
						'counter': 		BLEsensorMACs[mac][sensor]["nMessages"], 
						'mac': 			mac,
						"rssi":			int(rx)
				}

		trigTime 	= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]   > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
		trigTemp	= abs(temp - BLEsensorMACs[mac][sensor]["temp"]) > 0.5
		trigHum		= abs(hum - BLEsensorMACs[mac][sensor]["hum"]) > 2

		if False and doPrint: U.logger.log(20, u"mac:{}, temp:{}, hum:{}, triggers:{};{};{};   nMessages:{}".format(mac, temp, hum, trigTime, trigTemp, trigHum, BLEsensorMACs[mac][sensor]["nMessages"]))

		if BLEsensorMACs[mac][sensor]["nMessages"] > 0 and hum > -100. and temp > -100.:
			if  trigTime or trigTemp or trigHum:
					# compose complete message
					U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})

					# remember last values
					if  False and doPrint: U.logger.log(20, "mac:{} triggers:Time:{};temp:{};hum:{}; updateIndigoTiming:{}; send:{}".format( mac, trigTime , trigTemp , trigHum,BLEsensorMACs[mac][sensor]["updateIndigoTiming"] ,  dd)  )
					BLEsensorMACs[mac][sensor]["lastUpdate"] = time.time()
					BLEsensorMACs[mac][sensor]["temp"]    	 = temp
					BLEsensorMACs[mac][sensor]["hum"]    	 = hum
					BLEsensorMACs[mac][sensor]["batteryLevel"] = batteryLevel
		UUID = sensor
		Maj  = mac
		return  tx, batteryLevel, UUID, Maj, Min, False		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False

#################################

def doBLEXiaomiMi(mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor):
	global BLEsensorMACs, sensors
	try:
		if len(hexData) < 55: return tx, "", UUID, Maj, Min, False

		hexData = hexData[12:]
		"""
		## message formats for round sensor - LYWSDCGQ = AA 01 = S-typ
        ##                                       counter                                    data-
        ##                                             S-typ ct   reverse mac -----   Stype ll      1  2  3  4		
		##16 02 01 06                12 16 95 FE 50 20 AA 01 nn   E2 1D 37 34 2D 58   0A 10 01      64      			0A=battery; 	ll= 1 byte
		##17 02 01 06                13 16 95 FE 50 20 AA 01 nn   E2 1D 37 34 2D 58   06 10 02      16 02   			06=hum; 		ll= 2 byte
		##17 02 01 06                13 16 95 FE 50 20 AA 01 nn   E2 1D 37 34 2D 58   04 10 02      DA 02   			04=temp; 		ll= 2 byte
		##17 02 01 06                13 16 95 FE 51 20 DF 02 7D   FC 10 00 43 57 48   06 10 02      0E 02  
		##19 02 01 06                15 16 95 FE 50 20 AA 01 nn   E2 1D 37 34 2D 58   0D 10 04      FC 00   1E 02  		0D=temp + hum;	ll= 4 byte
	pos                                 01 23 45 67 89 11 23 45   67 89 21 23 45 67   89 31 23      45 67   89 41  pos in tag 
		## formaldehyde
		##17 02 01 06                13 16 95 FE 51 20 DF 02 7E   FC 10 00 43 57 48   10 10 02      4200 

		# 
	pos   01 23 45 67                89 11 23 45 67 89 21 23 45   67 89 31 23 45 67   89 41 23      45 67   89 61		position in hexData
		##
		## clock - LYWSD02 = 5B 04 = S-typ, no battery level? , each meassge is eitherh T or H or bat only 
		## mac#                E7:2E:01:41:5C:D9                                        
        ##ll            ll           ll                S-typ ct   reverse mac -----   ?? Stype ll   1  2 		
		## clock T         02 1A 18  13 16 95 FE 70 20 5B 04 49   D9 5C 41 01 2E E7   09 0A 10 01   26 00
		##                 02 1A 18  13 16 95 FE 70 20 5B 04 54   D9 5C 41 01 2E E7   09 04 10 02   EA 00
		##1C 02 01 06   03 02 1A 18  14 16 95 FE 70 20 5B 04 nn   D9 5C 41 01 2E E7   09 04 10 02   EE 00    			04=temp  00ee --> 238/10 = 23.8
		##1C 02 01 06   03 02 1A 18  14 16 95 FE 70 20 5B 04 nn   D9 5C 41 01 2E E7   09 06 10 02   A4 01    			06=hum   01aa --> 420/10 = 42.9%
		##1C 02 01 06   03 02 1A 18  14 16 95 FE 70 20 5B 04 nn   D9 5C 41 01 2E E7   09 0A 10 01   5B 00				0A=batt  5B   --> 91  ll= 1 byte, not too often
	pos   01 23 45 67   89 11 23 45  67 89 21 23 45 67 89 31 23   45 67 89 41 23 45   67 89 51 23   45 67				position in hexData


	# Xiaomi sensor types dictionary 
	#                              binary?
	XIAOMI_TYPE_DICT = {
		b'\x98\x00': ("HHCCJCY01", False),
		b'\xAA\x01': ("LYWSDCGQ", False),    # TH round
		b'\x5B\x04': ("LYWSD02", False),     # clock TH 
		b'\x47\x03': ("CGG1", False),
		b'\x5D\x01': ("HHCCPOT002", False),
		b'\xBC\x03': ("GCLS002", False),
		b'\x5B\x05': ("LYWSD03MMC", False),  # TH square
		b'\x76\x05': ("CGD1", False),
		b'\xDF\x02': ("JQJCY01YM", False),
		b'\x0A\x04': ("WX08ZM", True),
		b'\x87\x03': ("MHO-C401", False),
		b'\xd3\x06': ("MHO-C303", False),
		b'\x8B\x09': ("MCCGQ02HL", True),
		b'\x83\x00': ("YM-K1501", True),
	}

		MJHFD1_0010FC formaldehyd T H formA \mg/m**3

	# Sensor type indexes dictionary for sensor platform
	# Temperature, Humidity, Moisture, Conductivity, Illuminance, Formaldehyde, Consumable, Battery, Switch, Opening, Light
	#                          sensor               binary
	# Measurement type [T  H  M  C  I  F  Cn B]  [Sw O  L  B]     (start from 0, 9 - no data)
	MMTS_DICT = {
		'HHCCJCY01' : [[0, 9, 1, 2, 3, 9, 9, 9], [9, 9, 9, 9]],
		'GCLS002'   : [[0, 9, 1, 2, 3, 9, 9, 9], [9, 9, 9, 9]],
		'HHCCPOT002': [[9, 9, 0, 1, 9, 9, 9, 9], [9, 9, 9, 9]],
		'LYWSDCGQ'  : [[0, 1, 9, 9, 9, 9, 9, 2], [9, 9, 9, 9]], # TH round
		'LYWSD02'   : [[0, 1, 9, 9, 9, 9, 9, 2], [9, 9, 9, 9]], # clock TH 
		'CGG1'      : [[0, 1, 9, 9, 9, 9, 9, 2], [9, 9, 9, 9]],
		'LYWSD03MMC': [[0, 1, 9, 9, 9, 9, 9, 2], [9, 9, 9, 9]], # TH square
		'CGD1'      : [[0, 1, 9, 9, 9, 9, 9, 2], [9, 9, 9, 9]],
		'JQJCY01YM' : [[0, 1, 9, 9, 9, 2, 9, 3], [9, 9, 9, 9]],
		'WX08ZM'    : [[9, 9, 9, 9, 9, 9, 0, 1], [0, 9, 9, 1]],
		'MHO-C401'  : [[0, 1, 9, 9, 9, 9, 9, 2], [9, 9, 9, 9]],
		'MHO-C303'  : [[0, 1, 9, 9, 9, 9, 9, 2], [9, 9, 9, 9]],
		'MCCGQ02HL' : [[9, 9, 9, 9, 9, 9, 9, 0], [9, 0, 1, 2]],
		'YM-K1501'  : [[0, 9, 9, 9, 9, 9, 9, 9], [0, 9, 9, 9]],
	}

	"""
		doPrint 		= False
		#if mac == "48:57:43:00:10:FC": doPrint = True
		out 			= ""
		testStringTEMP 	= "x"
		testStringHUM  	= "x"
		testStringTH 	= "x"
		testStringBAT 	= "x"
		testStringFORM 	= "x" # Formaldehyde

		BATtag   		= "0A1001"
		TEMPtag  		= "041002"
		HUMtag   		= "061002"
		TEMPHtag 		= "0D1004"
		FORMAtag 		= "101002"
		#							 						ID-tag		sensTypeTag		counter
		typeInfo 		= 	{ "LYWSDCGQ":{"pos0":10, "pos1":[ 0,14], "pos2":[28,34], "posC":14, "id":"1695FE5020AA01"}
							, "MJHFD1":  {"pos0":10, "pos1":[ 0,14], "pos2":[28,34], "posC":14, "id":"1695FE5120DF02"}
							, "LYWSD02": {"pos0":18, "pos1":[ 0,14], "pos2":[30,36], "posC":14, "id":"1695FE70205B04"}
							}

		found = False
		for stype in  typeInfo:
			if hexData.find(typeInfo[stype]["id"]) >-1:
				found = True
				break
		if not found: 
			if False and doPrint: U.logger.log(20, u"mac:{}, stype not found, sensor:{}".format(mac, sensor))
			return tx, "", UUID, Maj, Min, False



		sens = ""
		if	 sensor.find("Round") >-1: 			sens = "LYWSDCGQ"
		elif sensor.find("Clock") >-1: 			sens = "LYWSD02"
		elif sensor.find("formaldehyde") >-1: 	sens = "MJHFD1"
		else: 
			if doPrint: U.logger.log(20, u"mac:{},sens not found:{}, sensor:{}".format(mac, sens, sensor))
			return tx, "", UUID, Maj, Min, False
		if doPrint: U.logger.log(20, u"mac:{}, sens:{}, sensor:{} start ========".format(mac, sens, sensor))

		hData = hexData[typeInfo[sens]["pos0"]:]

		testString		= hData[typeInfo[sens]["pos1"][0]:typeInfo[sens]["pos1"][1]]	+ macplainReverse + hData[typeInfo[sens]["pos2"][0]:typeInfo[sens]["pos2"][1]]
		testStringTEMP 	= typeInfo[sens]["id"] 											+ macplainReverse + TEMPtag
		testStringTH	= typeInfo[sens]["id"] 											+ macplainReverse + TEMPHtag
		testStringHUM	= typeInfo[sens]["id"] 											+ macplainReverse + HUMtag
		testStringFORM	= typeInfo[sens]["id"] 											+ macplainReverse + FORMAtag
		testStringBAT	= typeInfo[sens]["id"] 											+ macplainReverse + BATtag
		dataString		= hData[typeInfo[sens]["pos2"][1]:]
		counter			= int(hData[typeInfo[sens]["posC"]:typeInfo[sens]["posC"]+2],16)

		if BLEsensorMACs[mac][sensor]["nMessages"] == 0:
			BLEsensorMACs[mac][sensor]["tempAve"] = []
			BLEsensorMACs[mac][sensor]["tempHum"] = []
			for ii in range(BLEsensorMACs[mac][sensor]["numberOfMeasurementToAverage"]):
				BLEsensorMACs[mac][sensor]["tempAve"].append(-100)
				BLEsensorMACs[mac][sensor]["tempHum"].append(-100)

		out = ""
		for ii in range(10,len(hexData)-2,2):
			out+= hexData[ii:ii+2] + " "
		if doPrint:
			U.logger.log(20, u"mac:{},sensor:{} data string:{}, count:{}, \nteststr:{}\nformTag:{}\nout:{}".format(mac,sensor,  dataString, counter, testString, testStringFORM, out))


		temp 			= BLEsensorMACs[mac][sensor]["temp"]
		hum  			= BLEsensorMACs[mac][sensor]["hum"]
		Formaldehyde  	= BLEsensorMACs[mac][sensor]["Formaldehyde"]

		if testString == testStringTH: 
			val = int(dataString[0:2],16) + int(dataString[2:4],16)*256
			if val > 32767: val -= 65536
			temp = tralingAv(sensor, mac, "tempAve", val/10.)
			val = int(dataString[4:6],16) + int(dataString[6:8],16)*256+0.5
			if val > 32767: val -= 65536
			hum = int( tralingAv(sensor, mac, "humAve", val/10.))
			if doPrint:
				U.logger.log(20, u"mac:{}, typ: TH  {}+{} =tem:{}; {}+{} =hum:{}  dataString:{} ".format(mac, dataString[0:2],dataString[2:4],  temp, dataString[4:6],dataString[6:8], hum, out))
			BLEsensorMACs[mac][sensor]["nMessages"] += 1

		elif testString == testStringHUM: 
			val = int(dataString[0:2],16) + int(dataString[2:4],16)*256 +0.5
			if val > 32767: val -= 65536
			hum = int( tralingAv(sensor, mac,"humAve", val/10.) )
			if doPrint:
				U.logger.log(20, u"mac:{}, typ: H  {}+{} =Hum:{};   dataString:{}".format(mac, dataString[0:2],dataString[2:4],  hum, out))
			if BLEsensorMACs[mac][sensor]["hum"]   == -100: 
				BLEsensorMACs[mac][sensor]["hum"]   = hum
			BLEsensorMACs[mac][sensor]["nMessages"] += 1

		elif testString == testStringTEMP:
			val = int(dataString[0:2],16) + int(dataString[2:4],16)*256
			if val > 32767: val -= 65536
			temp = tralingAv(sensor, mac, "tempAve", val/10.)  
			if doPrint:
				U.logger.log(20, u"mac:{}, typ: T  {}+{} =temp:{};   dataString:{}".format(mac, dataString[0:2],dataString[2:4],  temp, out))
			if BLEsensorMACs[mac][sensor]["temp"]   == -100: 
				BLEsensorMACs[mac][sensor]["temp"]   = temp
			BLEsensorMACs[mac][sensor]["nMessages"] += 1

		elif testString == testStringFORM: 
			Formaldehyde  = (int(dataString[0:2],16) + int(dataString[2:4],16)*256. ) /100.
			if doPrint:
				U.logger.log(20, u"mac:{}, typ: B  {}    =Formaldehyde:{};   dataString:{}".format(mac, dataString[0:2],  Formaldehyde, out))
			BLEsensorMACs[mac][sensor]["nMessages"] += 1


		elif testString == testStringBAT: 
			BLEsensorMACs[mac][sensor]["batteryLevel"]  = int(dataString[0:2],16) 
			if doPrint:
				U.logger.log(20, u"mac:{}, typ: B  {}    =bat:{};   dataString:{}".format(mac, dataString[0:2],  BLEsensorMACs[mac][sensor]["batteryLevel"] , out))
			BLEsensorMACs[mac][sensor]["nMessages"] += 1

		else:
			if doPrint: U.logger.log(20, u"mac:{}, tag not found, dataString:{}  hexstr:{} ".format(mac, dataString, out ))
			return tx, BLEsensorMACs[mac][sensor]["batteryLevel"], UUID, Maj, Min, False	


		
		dd = {}  # the data dict to be send 
		dd['mac'] =	mac
		if temp > -100: 											dd['temp'] 			= round(temp+ BLEsensorMACs[mac][sensor]["offsetTemp"],1)
		if hum > -100: 												dd['hum']			= int(hum + BLEsensorMACs[mac][sensor]["offsetHum"])
		if Formaldehyde > -100: 									dd['Formaldehyde']	= round(Formaldehyde,2)
		if counter > -100: 											dd['counter']		= counter 
		if BLEsensorMACs[mac][sensor]["batteryLevel"] !="":
			if BLEsensorMACs[mac][sensor]["batteryLevel"] >-100:
																	dd['batteryLevel']	= BLEsensorMACs[mac][sensor]["batteryLevel"]
		if rx > -101: 												dd['rssi']			= int(rx)

		trigTime 	= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]   > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
		trigTemp	= abs(temp - BLEsensorMACs[mac][sensor]["temp"]) 				 > 0.5
		trigHum		= abs(hum - BLEsensorMACs[mac][sensor]["hum"]) 					 > 2
		trigFOM		= abs(Formaldehyde - BLEsensorMACs[mac][sensor]["Formaldehyde"]) > 0.1

		if doPrint: U.logger.log(20, u"mac:{}, temp:{}, hum:{}, form:{}, triggers:{};{};{};{};   nMessages:{}".format(mac, temp, hum, Formaldehyde, trigTime, trigTemp, trigHum, trigFOM, BLEsensorMACs[mac][sensor]["nMessages"]))

		if BLEsensorMACs[mac][sensor]["nMessages"] > 6 and temp > -100.:
			if  trigTime or trigTemp or trigHum or trigFOM:
					# compose complete message
					U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})

					# remember last values
					if doPrint: U.logger.log(20, "mac:{} triggers:Time:{};temp:{};hum:{},form:{}; updateIndigoTiming:{}; send:{}".format( mac, trigTime , trigTemp , trigHum, trigFOM, BLEsensorMACs[mac][sensor]["updateIndigoTiming"] ,  dd)  )
					BLEsensorMACs[mac][sensor]["lastUpdate"]	= time.time()
					BLEsensorMACs[mac][sensor]["counter"]		= counter
					BLEsensorMACs[mac][sensor]["temp"]    		= temp
					BLEsensorMACs[mac][sensor]["hum"]		 	= hum
					BLEsensorMACs[mac][sensor]["Formaldehyde"]	= Formaldehyde
		UUID = sensor
		Maj  = mac
		return  tx, BLEsensorMACs[mac][sensor]["batteryLevel"], UUID, Maj, Min, False		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False

#################################
def tralingAv(sensor, mac, avType, retVal):
	global BLEsensorMACs
	try:
		BLEsensorMACs[mac][sensor][avType].append(retVal)
		BLEsensorMACs[mac][sensor][avType].pop(0)
		yy = 0
		nn = 0.
		#U.logger.log(20, " mac:{}  avType:{}; retVal:{}; BLEsensorMACs: {} ".format( mac, avType, retVal, BLEsensorMACs[mac][sensor][avType])  )

		#build averages and exclude max and min values, only works for nn >2

		maxV = max(BLEsensorMACs[mac][sensor][avType])
		minV = min(BLEsensorMACs[mac][sensor][avType])
		mm   = len(BLEsensorMACs[mac][sensor][avType])

		for xx in BLEsensorMACs[mac][sensor][avType]:
			if xx == -100: continue
			if mm > 2:
				if xx == minV: continue
				if xx == maxV: continue
			nn += 1.
			yy += xx
		if nn > 1: retVal = yy / nn
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return retVal


#################################
def doBLEiSensor(mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor):
	global BLEsensorMACs, sensors

	""" format:
																							
- on/off sensors 
									pos#      01 23 45  67 89 01 23 45 67 89 01 23 45  67 89 01 23 45 67 89 01 23 45   67 89 01 23 45 67 89 01 23   RSSI
- 04 3E 23 02 01 03 00 88 B8 37 22 9A AC   17 02 01 06  09 08 69 53 65 6E 73 6F 72 20  09 FF 00 DB 97 46 43 02 07 04    D4
- 04 3E 23 02 01 03 00 88 B8 37 22 9A AC   17 02 01 06  09 08 69 53 65 6E 73 6F 72 20  09 FF 00 DB 97 46 43 02 08 05    D4
										   17 02 01 06  09 08 69 53 65 6E 73 6F 72 20  09 FF 10 AE CC 37 39 04 01 FF    4 button remote
					   r- MA C# ## ## ##                       i  S  e  n  s  o  r  _   = name of sensortype  string "iSensor "
														 				               LL = length of data 
														 								  FT = FF = frame type =GAP_AD_TYPE_MANU_SPECIFIC_DATA
														 								     FW--- = 00 = firmware 
																						        devID--- = DB 97 46
																							             data----  = 43 02 07
																									     TP  = typeID = 43 = 01000011 = sends alive, and gas sensor
																									        EV  = eventData
																									           CB  = control byte = counter
																									eg:  Data  send alive 3= gas sensor
																							                EV 02 = alarm  (= 0010 = alarm, 1000 = alive )
																							                   CB = 07/08 = count= 04..05..06..07..08.. 
 
																							                      CS = 04,05 = check sum = byte 0 +..byte7

 temp / humidity sensor 
									pos#      01 23 45  67 89 01 23 45 67 89 01 23 45  67 89  01 23 45 67 89 01 23 45 67 89 01 23 45 67 89 01   23   RSSI
- 04 3E 2B 02 01 03 00 22 80 E3 22 9A AC   1F 02 01 06  09 08 69 53 65 6E 73 6F 72 20  11 FF  22 E3 80 22 4C 00 02 00 1D 5D 35 03 00 00 00 A7   C5
- 04 3E 2B 02 01 03 00 22 80 E3 22 9A AC   1F 02 01 06  09 08 69 53 65 6E 73 6F 72 20  11 FF  22 E3 80 22 4C 00 01 00 1E 18 3B 03 00 00 00 68   D1
					   r- MA C# ## ## ##                       i  S  e  n  s  o  r  _   = name of sensortype  string "iSensor "
														 				               LL = length of data 
														 								  FT = FF = frame type =GAP_AD_TYPE_MANU_SPECIFIC_DATA
														 								      FW--- = 22 = firmware 
																						         devID--- = E3 80 22
																						                  typeID--- = 4C
																											 EV data 00   
																												CT data 02 00
																													   Tempd 1D 5D  = int.dec  = 16+13. 5*16+13/256*100 = 19.085C
																													        humd 35 03  int.dec = 3*16+5.3 = 53.001
																											
																														
																													 
			


	"""

	try:
		
		hexData = hexData[14:]
		if len(hexData) < 40: return tx, "", UUID, Maj, Min, False
		TagPos1 	= hexData.find("02010609086953656E736F722009FF") 
		TagPos2 	= hexData.find("02010609086953656E736F722011FF") 
		#                                        i S e n s o r _
		if TagPos1 !=0 and TagPos2 !=0: return tx, "", UUID, Maj, Min, False
		remoteTrig = False
		tempTrig   = False
		UUID 				= sensor
		Maj  				= mac
		deviceByte			= intFrom8(hexData,38)
		typeID				= deviceByte & 0b00011111
		if    deviceByte &  0b00010000 !=0: remote = True
		else:								remote = False

		doDebug = False
		if False and mac in ["AC:9A:22:CC:EB:8E"]: doDebug = True
		

		if  doDebug:
			U.logger.log(20, " mac:{}  TagPos1:{}  TagPos2:{}, deviceByte:{:08b}, typeID:{}, remote:{}".format( mac, TagPos1, TagPos2, deviceByte, typeID, remote) )

		fastSwitchBotPress = "" 

		if TagPos2 == 0: 
				out =""
				for ii in range(30,len(hexData),2):
					out += hexData[ii:ii+2]+" "
				firmWare	= intFrom8(hexData,30)
				devId1		= intFrom8(hexData,32)
				devId2		= intFrom8(hexData,34)
				devId3		= intFrom8(hexData,36)
				eventData 	= intFrom8(hexData,40)
				counter		= intFrom8(hexData,42)
				cData		= intFrom8(hexData,44)
				temp1   	= intFrom8(hexData,46)
				temp2   	= intFrom8(hexData,48)
				hum1	   	= intFrom8(hexData,50)
				hum2	   	= intFrom8(hexData,52)
				empty1	   	= intFrom8(hexData,54)
				empty2	   	= intFrom8(hexData,56)
				empty3	   	= intFrom8(hexData,58)
				checkSum	= intFrom8(hexData,60)
				checkSumCalc= (firmWare + devId1 + devId2 + devId3 + deviceByte + eventData + counter + cData + temp1 + temp2 +hum1 + hum2 + empty1 + empty2 + empty2) & 255 # only one byte
						
				temp   		= float(temp1)
				if temp > 127: temp -= 256
				temp 		+= temp2/256. + BLEsensorMACs[mac][sensor]["offsetTemp"]

				hum 		= float(hum1)
				if hum > 127: hum -= 256
				hum 		+= hum2/256.+ BLEsensorMACs[mac][sensor]["offsetHum"] +0.5

				sendsAlive	= eventData & 0b00001000 != 0
				lowVoltage	= eventData & 0b00000100 != 0
				alarm		= eventData & 0b00000010 != 0
				tampered	= eventData & 0b00000001 != 0

				sensorType = "undefined"
				if    typeId == 0b00001100: sensorType = "TempHum"
				else: return tx, "", UUID, Maj, Min, False

				#U.logger.log(20, " mac:{} counter:{}, hum:{:5.2f}; temp:{:9.3f}; sendsAlive:{}, lowVoltage:{}, alarm:{}, tampered:{}, checkSum:{}, csCalc:{},  hex:{}".format( mac, counter, hum, temp, sendsAlive, lowVoltage, alarm, tampered, checkSum, checkSumCalc, out)  )
				if  sensorType == "TempHum":
					dd={   # the data dict to be send 
							'lowVoltage': 	eventData & 0b00000100 != 0,
							'temp': 		round(temp,2),
							'hum': 			int(hum),
							'tampered': 	eventData & 0b00000001 != 0,
							'counter': 		counter, # changes only when pressed twice or ~1 sec after the last
							'sensorType': 	sensorType,
							'sendsAlive': 	sendsAlive,
							'mac': 			mac,
							"rssi":			int(rx)
					}

				trigTime 	= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]   > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
				trigCount	= False and counter != BLEsensorMACs[mac][sensor]["counter"] 			# send min every xx secs
				trigTemp	= abs(temp - BLEsensorMACs[mac][sensor]["temp"]) > 0.5
				trigHum		= abs(hum - BLEsensorMACs[mac][sensor]["hum"]) > 1

				if  trigCount or trigTime or trigTemp or trigHum:
					# compose complete message
					U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})

					# remember last values
					BLEsensorMACs[mac][sensor]["lastUpdate"] = time.time()
					BLEsensorMACs[mac][sensor]["counter"]    = counter
					BLEsensorMACs[mac][sensor]["temp"]    	 = temp
					BLEsensorMACs[mac][sensor]["hum"]    	 = hum

				return  tx, "", UUID, Maj, Min, False		


		elif TagPos1 == 0: 
			firmWare	= intFrom8(hexData,30)
			devId1		= intFrom8(hexData,32)
			devId2		= intFrom8(hexData,34)
			devId3		= intFrom8(hexData,36)
			eventData 	= intFrom8(hexData,40)
			counter		= intFrom8(hexData,42)
			checkSum	= intFrom8(hexData,44)

			checkSumCalc 		= (firmWare + devId1 + devId2 + devId3 + deviceByte + eventData + counter) & 255 # only one byte

			if checkSum != checkSumCalc:
				U.logger.log(20, " mac:{}   checksum error  hex:{}, chs:{} chscalc:{}".format( mac, hexData[32:48], checkSum, checkSumCalc) )
				U.sendURL( {"sensors":{sensor: {BLEsensorMACs[mac][sensor]["devId"]: {"badsensor":True, "rssi":int(rx)} }}} )
				return tx, "", UUID, Maj, Min, False 


			counter			= counter & 0b00011111
			sendsAlive 		= deviceByte & 0b01000000 != 0
			biDirection 	= deviceByte & 0b10000000 != 0# Not used 
			if    typeID == 0b00000000: sensorType = "undefined"
			elif  typeID == 0b00000001:	sensorType = "IR-Fence"
			elif  typeID == 0b00000010:	sensorType = "PIR"
			elif  typeID == 0b00000011:	sensorType = "Gas"
			elif  typeID == 0b00000100:	sensorType = "Panic"
			elif  typeID == 0b00000101:	sensorType = "Smoke"
			elif  typeID == 0b00000110:	sensorType = "Door"
			elif  typeID == 0b00000111:	sensorType = "GlasBreak"
			elif  typeID == 0b00001000:	sensorType = "Vibration"
			elif  typeID == 0b00001001:	sensorType = "WaterLevel"
			elif  typeID == 0b00001010:	sensorType = "HighTemp"
	#		elif  typeID == 0b00001011:	sensorType = "undefined"		
	#		elif  typeID == 0b00001100:	sensorType = "undefined"
	#		elif  typeID == 0b00001101:	sensorType = "undefined"
	#		elif  typeID == 0b00001110:	sensorType = "undefined"
	#		elif  typeID == 0b00001111:	sensorType = "undefined"

	#		elif  typeID == 0b00010000:	sensorType = "undefined"	
	#		elif  typeID == 0b00010001:	sensorType = "undefined"	
	#		elif  typeID == 0b00010010:	sensorType = "undefined"	
	#		elif  typeID == 0b00010011:	sensorType = "undefined"	
	#		elif  typeID == 0b00010100:	sensorType = "undefined"	
	#		elif  typeID == 0b00010101:	sensorType = "undefined"	
			elif  typeID == 0b00010110:	sensorType = "DoorBell"		
	#		elif  typeID == 0b00010111:	sensorType = "undefined"	
	#		elif  typeID == 0b00011000:	sensorType = "undefined"	
			elif  typeID == 0b00011001:	sensorType = "RemoteKeyFob"	
			elif  typeID == 0b00011010:	sensorType = "WirelessKeypad"
	#		elif  typeID == 0b00011011:	sensorType = "undefined"	
	#		elif  typeID == 0b00011100:	sensorType = "undefined"	
	#		elif  typeID == 0b00011101:	sensorType = "undefined"	
			elif  typeID == 0b00011110:	sensorType = "WirelessSiren"  # not supported, will just post the bits
			elif  typeID == 0b00011111:	sensorType = "RemoteSwitch"	  # not supported, will just post the bits
			else:						sensorType = "undefined"

			Min  			= sensorType 

			if  doDebug: U.logger.log(20, " mac:{}   typeID:{}, eventData:{:08b}, sensorType:{}, remote:{}".format( mac, typeID, eventData, sensorType, remote) )

			if sensorType in ["DoorBell", "RemoteKeyFob", "RemoteSwitch",  "Door", "WaterLevel",  "Panic"]:
				if 	time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]  > 1.: remoteTrig = True
				if  sensorType == "DoorBell":
					dd={   # the data dict to be send 
							'lowVoltage': 	eventData & 0b00000100 != 0,
							'onOff': 		eventData & 0b00000010 != 0,
							'tampered': 	eventData & 0b00000001 != 0,
							'counter': 		counter, # changes only when pressed twice or ~1 sec after the last
							'sensorType': 	sensorType,
							'sendsAlive': 	sendsAlive,
							'mac': 			mac,
							"rssi":			int(rx)
					}
					if eventData & 0b00000010 != 0: fastSwitchBotPress =  "on"
					else: 							fastSwitchBotPress =  "off"
				elif  sensorType == "RemoteKeyFob":
					anybutton = eventData & 0b00001000 != 0 or eventData & 0b00000100 != 0 or eventData & 0b00000010 != 0 or eventData & 0b00000001 != 0
					dd={   # the data dict to be send 
							'SOS': 			eventData & 0b00001000 != 0,
							'home': 		eventData & 0b00000100 != 0,
							'away': 		eventData & 0b00000010 != 0,
							'disarm': 		eventData & 0b00000001 != 0,
							'counter': 		counter, # not used always 1
							'sensorType': 	sensorType,
							'sendsAlive': 	sendsAlive, # should be false always
							'mac': 			mac,
							"rssi":			int(rx)
					}
					if anybutton: fastSwitchBotPress =  "on"
					else: 		  fastSwitchBotPress =  "off"
				elif sensorType == "RemoteSwitch":
					dd={   # the data dict to be send 
							'state': 		eventData & 0b00000100 != 0,
							'onOff': 		eventData & 0b00000010 != 0,
							'counter': 		counter,
							'sensorType': 	sensorType,
							'sendsAlive': 	sendsAlive,
							'mac': 			mac,
							"rssi":			int(rx)
					}
					if eventData & 0b000000010 != 0: fastSwitchBotPress = "on"
					else: 						 	 fastSwitchBotPress = "off"
				elif sensorType == "Door":
					dd={   # the data dict to be send 
							'state': 		(eventData & 0b00000100) != 0,
							'onOff': 		(eventData & 0b00000010) == 0, # this one is on if disconnected, off if mag is close, reversing logic 
							'counter': 		counter,
							'sensorType': 	sensorType,
							'sendsAlive': 	sendsAlive,
							'mac': 			mac,
							"rssi":			int(rx)
					}
					if eventData & 0b000000010 != 0: fastSwitchBotPress = "on"
					else: 						 	 fastSwitchBotPress = "off"
				elif sensorType == "WaterLevel":
					dd={   # the data dict to be send 
							'onOff': 		(eventData & 0b00000010) == 0,
							'counter': 		counter,
							'sensorType': 	sensorType,
							'sendsAlive': 	sendsAlive,
							'tampered': 	eventData & 0b00000001 != 0,
							'mac': 			mac,
							"rssi":			int(rx)
					}
					if eventData & 0b000000010 != 0: fastSwitchBotPress = "on"
					else: 						 	 fastSwitchBotPress = "off"
					if  doDebug: U.logger.log(20, " mac:{}  in waterlevel;".format(mac))

				elif  sensorType == "Panic":
					dd={   # the data dict to be send 
							'onOff': 		eventData & 0b00000010 != 0,
							'counter': 		counter,
							'sensorType': 	sensorType,
							'sendsAlive': 	sendsAlive,
							'mac': 			mac,
							"rssi":			int(rx)
						}
					if eventData & 0b000000010 != 0: fastSwitchBotPress = "on"

			else: # all other type onOff
					dd={   
							'bits': 		"{:b}".format(eventData),
							'alive': 		eventData & 0b00001000 != 0,
							'lowVoltage': 	eventData & 0b00000100 != 0,
							'onOff': 		eventData & 0b00000010 != 0,
							'tampered': 	eventData & 0b00000001 != 0,
							'counter': 		counter,
							'sensorType': 	sensorType,
							'sendsAlive': 	sendsAlive,
							'mac': 			mac,
							"rssi":			int(rx)
						}
					if eventData & 0b000000010 != 0: fastSwitchBotPress = "on"
					else: 						 	 fastSwitchBotPress = "off"


		#U.logger.log(20, " .... checking  data:{} counter hex:{}".format( dd , hexData[42:42+5]) )
		trigTime 			= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]   > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
		trigCount			= counter != BLEsensorMACs[mac][sensor]["counter"] 			# send min every xx secs

		if  doDebug: U.logger.log(20, " mac:{}  sending dd:{};".format(mac, dd))

		if  trigCount or trigTime or remoteTrig:
			trig = ""
			if trigCount: trig += "count/"
			if trigTime: trig += "timer/"
			if remoteTrig: trig += "event/"
			trig = trig.strip("/")
			dd["trigger"] = trig   
			dd["mac"] = mac   
			# compose complete message
			U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})
			#U.logger.log(20,u"sensor pressed {}-{} :{}".format(mac,sensor, dd))
			# remember last values
			BLEsensorMACs[mac][sensor]["lastUpdate"] = time.time()
			BLEsensorMACs[mac][sensor]["counter"]    = counter

			if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)

		return tx, "", UUID, Maj, Min, False

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False



#################################
def doBLEiBSxx( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor):
	global BLEsensorMACs
	global fastBLEReaction

	try:
		HexStr0 				= hexData[12:] # skip mac  + length
		if len(HexStr0) < 40: 
			return tx, "", UUID, Maj, Min, False

		verbose = mac == "xxCF:85:DE:C6:90:55"

		posFound, dPos, x, y, subtypeOfBeacon =  testComplexTag(HexStr0, "iBSxx", mac, macplain, macplainReverse, Maj="", Min="", checkMajMin=False, calledFrom="doBLEiBSxx" )
		#U.logger.log(20, "mac:{}   posFound:{}, dPos:{}, subtypeOfBeacon:{}, HexStr:{}".format(mac, posFound, dPos, subtypeOfBeacon, HexStr0) )	

		if dPos !=0:
			return tx, "", UUID, Maj, Min, False

		infostart 			= 7*2   #  
		HexStr				= hexData[infostart:]
		UUID				= sensor
		Maj					= "sensor"
		devId				= BLEsensorMACs[mac][sensor]["devId"]
		fastSwitchBotPress	= ""
		# position of starting point for ..
		batPos 				= 9*2
		eventPos			= 11*2
		sens1Pos			= 12*2
		sens2Pos			= 14*2
		accelPos			= 11*2

		# used in all sebnsor types, all at same pos.
		Bstring 			= HexStr[batPos+2:batPos+4]+HexStr[batPos:batPos+2]
		batteryVoltage		= (int(Bstring,16) & 0b0000111111111111)*10 # in mV
		batteryLevel 		= batLevelTempCorrection(batteryVoltage, 20.) # no correction
		#if mac =="00:81:F9:86:02:52": U.logger.log(20,u"{} bat v:{:4}, batL:{:3}, Bstring:{}".format(mac, batteryVoltage, batteryLevel, Bstring))

		data   = {sensor:{devId:{}}}
		data[sensor][devId] ={"batteryVoltage":batteryVoltage,"batteryLevel":batteryLevel,"type":sensor,"mac":mac,"rssi":float(rx),"txPower":-60}

		p = 5*2
		if   HexStr.find("0D0081BC") == p:		subTypeHex 	= "iBS03RG"
		elif HexStr.find("590081BC") == p:		subTypeHex 	= "iBS01RG"
		elif HexStr.find("0D0083BC") == p:		subTypeHex 	= "iBS02"
		elif HexStr.find("0D0083BC") == p:		subTypeHex 	= "iBS03"
		elif HexStr.find("590080BC") == p:		subTypeHex 	= "iBS01"
		else:									subTypeHex  = ""

		p = 7*2
		pFormat = HexStr[p:p+4]
		#  123456789 1123 4567 8921 23 4567 8931 2345 67 8941234567890
		# 02010619FF 5900 81BC 3601 08 00F8 FF04 0104 00 F8FF08010400F8FF0801BF
		# 02010612FF 5900 80BC 2101 00 FFFF FFFF FFFF FF FFFFFFBB
		# 02010612FF 0D00 83BC 2801 00 AAAA FFFF 0000 04 070000BB
		# 02010612FF 5900 80BC 2B01 00 FFFF FFFF FEFF 0D 000801BD
		# 02010612FF 0D00 83BC 3101 00 AAAA FFFF 0000 10 040000BF
		# 02010612FF 5900 80BC 2B01 00 FFFF FFFF 0900 0F 000601AE
		# 02010612FF 5900 80BC 2B01 02 FFFF FFFF 56FF 7A 001CFFBF
		# 02010619FF 5900 81BC 3011 FFFF 2300 07FF FDFF 2200 05FF FFFF 2100 07FF BD
		p = 18*2
		st = HexStr[p:p+2]
		iBSType = ""
		if pFormat == "80BC":  # iBS01 types:
			if	 st == "03": iBSType = "iBS01"
			elif st == "04": iBSType = "iBS01H"
			elif st == "05": iBSType = "iBS01T"
			elif st == "06": iBSType = "iBS01G"
			elif st == "0F": iBSType = "iBS01G"
			elif st == "FF": iBSType = "iBS01T"

		elif pFormat == "83BC":  # iBS03 and 4 types:
			if	 st == "01": iBSType = "iBS02PIR2"
			elif st == "02": iBSType = "iBS02IR2"
			elif st == "04": iBSType = "iBS01H"
			elif st == "05": iBSType = "iBS01T"
			elif st == "06": iBSType = "iBS01G"
			elif st == "10": iBSType = "iBS03"
			elif st == "12": iBSType = "iBS03P"
			elif st == "13": iBSType = "iBS03R"
			elif st == "14": iBSType = "iBS03T_HR"
			elif st == "15": iBSType = "iBS03T"
			elif st == "16": iBSType = "iBS03G"
			elif st == "17": iBSType = "iBS03TP"
			elif st == "18": iBSType = "iBS04i"
			elif st == "19": iBSType = "iBS04"

		elif pFormat == "81BC":  # iBS01 types:
			iBSType = "iBS03RG"


		# 80BC = event 1 byte, + sens1 2 bytes + sens2 2 bytes 
		# 81BC = event in bat info ,  +3 accel x,y,z each 6 bytes 
		# 83BC = event 1 byte, + sens1 2 bytes + sens2 2 bytes 


		AmbientTemperature		= ""
		temp					= "" 
		hum						= ""
		accelerationX			= ""
		accelerationY			= ""
		accelerationZ			= ""
		updateIndigoDeltaAccel 	= ""
		updateIndigoDeltaMaxXYZ = ""
		if verbose: U.logger.log(20, "{} sensor:{:10s}, iBSType:{:10s}, subtypeOfBeacon:{:10s}, pFormat:{:4s}, st:{:2s}, HexStr:{}".format(mac, sensor, iBSType, subtypeOfBeacon, pFormat, st, HexStr) )	
		p = eventPos# start of on/off
		onOffBits 	= int(HexStr[p:p+2],16)
		button 		= ( onOffBits &  0b00000001 ) != 0
		moving 		= ( onOffBits &  0b00000010 ) != 0
		hallSensor 	= ( onOffBits &  0b00000100 ) != 0 
		freeFall 	= ( onOffBits &  0b00001000 ) != 0 
		PIR 		= ( onOffBits &  0b00010000 ) != 0 
		IR 			= ( onOffBits &  0b00100000 ) != 0 
		iVAL		= int(Bstring,16)
		onOff1		= iVAL &  0b00000100 != 0
		onOff		= iVAL &  0b00000010 != 0

		Trig 				= ""
		if  sensor  == "BLEiBS01" : 	# on/off
			onOff								= button or moving or hallSensor or freeFall or PIR or IR
			onOff1								= button
			data[sensor][devId]["onOff"] 		= onOff
			data[sensor][devId]["onOff1"] 		= button
			data[sensor][devId]["onOff2"] 		= moving
			data[sensor][devId]["onOff3"] 		= hallSensor
			data[sensor][devId]["onOff4"] 		= freeFall
			data[sensor][devId]["onOff5"] 		= PIR
			data[sensor][devId]["onOff6"] 		= IR
			if BLEsensorMACs[mac][sensor]["onOff1"] 	!= button: Trig += "button/"
			if BLEsensorMACs[mac][sensor]["onOff2"] 	!= moving: Trig += "moving/"
			if BLEsensorMACs[mac][sensor]["onOff3"] 	!= hallSensor: Trig += "hallSensor/"
			if BLEsensorMACs[mac][sensor]["onOff4"] 	!= freeFall: Trig += "freeFall/"
			if BLEsensorMACs[mac][sensor]["onOff5"] 	!= PIR: Trig += "pir/"
			if BLEsensorMACs[mac][sensor]["onOff6"] 	!= IR: Trig += "ir/"
			fastSwitchBotPress = "on" if onOff else "off"
			if verbose: U.logger.log(20, "mac:{}   HexStr[p:p+2]:{}, old01:{};  new01:{}, Trig:{}".format(mac, HexStr[p:p+2], BLEsensorMACs[mac][sensor], onOff, Trig ) )

		elif  sensor == "BLEiBS03G": 	
			if BLEsensorMACs[mac][sensor]["onOff"]  != onOff: Trig += "switch/"
			data[sensor][devId]["onOff"] = onOff
			if BLEsensorMACs[mac][sensor]["onOff1"] != onOff1: Trig += "switch1/"
			data[sensor][devId][sensor]["onOff1"] = onOff1

		elif  sensor == "BLEiBS03T": 	
			p = sens1Pos # start of temp
			temp = ( signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100. + BLEsensorMACs[mac][sensor]["offsetTemp"]) * BLEsensorMACs[mac][sensor]["multTemp"]
			if abs(BLEsensorMACs[mac][sensor]["temp"] - temp) >= BLEsensorMACs[mac][sensor]["updateIndigoDeltaTemp"]: Trig +=  "temp/"
			data[sensor][devId]["temp"] 		= temp 
			batteryLevel 						= batLevelTempCorrection(batteryVoltage, temp)
			data[sensor][devId]["batteryLevel"] = batteryLevel


		elif  sensor == "BLEiBS03TP": 	
			p = sens1Pos# start of temp
			temp = (signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100. + BLEsensorMACs[mac][sensor]["offsetTemp"]) * BLEsensorMACs[mac][sensor]["multTemp"]
			if abs(BLEsensorMACs[mac][sensor]["temp"] - temp) >= BLEsensorMACs[mac][sensor]["updateIndigoDeltaTemp"]: Trig +=  "temp/"
			data[sensor][devId]["temp"] 		= temp 
			batteryLevel 						= batLevelTempCorrection(batteryVoltage, temp)
			data[sensor][devId]["batteryLevel"] = batteryLevel
			p = sens2Pos# start of temp probe
			AmbientTemperature = signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100.
			if abs(BLEsensorMACs[mac][sensor]["AmbientTemperature"] - AmbientTemperature) >=1: Trig +=  "ambient-temp/"
			data[sensor][devId]["AmbientTemperature"] = AmbientTemperature


		elif  sensor == "BLEiBS01T": 	
			data[sensor][devId]["onOff"] = button

			p = sens1Pos# start of temp
			temp = (signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100. + BLEsensorMACs[mac][sensor]["offsetTemp"]) * BLEsensorMACs[mac][sensor]["multTemp"]
			data[sensor][devId]["temp"] 		= temp 

			batteryLevel 						= batLevelTempCorrection(batteryVoltage, temp)
			data[sensor][devId]["batteryLevel"] = batteryLevel

			p = sens2Pos# start of hum probe
			hum = int( signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] ) + BLEsensorMACs[mac][sensor]["offsetHum"] +0.5 )
			data[sensor][devId]["hum"] = hum

			if abs(BLEsensorMACs[mac][sensor]["temp"] - temp) >= 1: Trig +=  "temp/"
			if abs(BLEsensorMACs[mac][sensor]["hum"] -   hum) >1 :  Trig +=  "hum/"
			if onOff != BLEsensorMACs[mac][sensor]["onOff"] :		Trig +=  "onOff"
			if verbose: U.logger.log(20, "mac:{}   sens1Pos:{}, sens2Pos:{}, Bstring:{}, iVAL:{:016b}, batteryVoltage:{}  onOff:{}, Trig:{}; data:{}".format(mac, sens1Pos, sens2Pos, Bstring, iVAL,batteryVoltage,  onOff, Trig, data[sensor][devId]) )
			fastSwitchBotPress = "on" if onOff else "off"


		elif  sensor in["BLEiBS01RG","BLEiBS03RG"]:
			p = accelPos # there are 3 measuremenst send, take the middle 
			#U.logger.log(20, "{} hex[p]:{} x:{}, y:{},z:{} ".format(mac,HexStr[p:], HexStr[ p :p+4 ],HexStr[ p+4 :p+8 ],HexStr[ p+8 :p+12 ]) )
			accelerationX 	= signedIntfrom16(hexData[p+2 :p+4 ]+HexStr[p  :p+2 ])*(4) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationY 	= signedIntfrom16(hexData[p+6 :p+8 ]+HexStr[p+4:p+6 ])*(4) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationZ 	= signedIntfrom16(hexData[p+10:p+12]+HexStr[p+8:p+10])*(4) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)
		# make deltas compared to last send 
			dX 			= abs(BLEsensorMACs[mac][sensor]["accelerationX"]		- accelerationX)
			dY 			= abs(BLEsensorMACs[mac][sensor]["accelerationY"]		- accelerationY)
			dZ 			= abs(BLEsensorMACs[mac][sensor]["accelerationZ"]		- accelerationZ)

			dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
			deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000
			trigAccel 	= dTot			> BLEsensorMACs[mac][sensor]["updateIndigoDeltaAccelVector"] 	# acceleration change triggers 
			trigDeltaXZY= deltaXYZ		> BLEsensorMACs[mac][sensor]["updateIndigoDeltaMaxXYZ"]			# acceleration-turn change triggers 
			if trigAccel:    							Trig += "accel/"
			if trigDeltaXZY: 							Trig += "deltaXYZ/"
			if onOff != BLEsensorMACs[mac][sensor]["onOff"]:	Trig += "onOff/" 
			data[sensor][devId]["accelerationTotal"] 		= int(accelerationTotal)
			data[sensor][devId]["accelerationX"] 			= int(accelerationX)
			data[sensor][devId]["accelerationY"] 			= int(accelerationY)
			data[sensor][devId]["accelerationZ"] 			= int(accelerationZ)
			data[sensor][devId]["accelerationXYZMaxDelta"]  = int(deltaXYZ)
			data[sensor][devId]["accelerationVectorDelta"]  = int(dTot)
			data[sensor][devId]["onOff"]  					= onOff
			data[sensor][devId]["onOff1"]  					= onOff1
			if verbose: U.logger.log(20, "{} Bstring:{}, iVAL:{:016b},  onOff:{}, Trig:{}; data:{}".format(mac,Bstring, iVAL,  onOff, Trig, data[sensor][devId]) )
			fastSwitchBotPress = "on" if onOff or onOff1 else "off"

		else:
			return tx, "", UUID, Maj, Min, False

		# check if we should send data to indigo
		deltaTime 			= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]
		trigTime 			= deltaTime   > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
		#U.logger.log(20, "mac:{}    HexStr20-23:{}- 24-26{} irOnOff:{}, batteryVoltage:{}".format(mac, HexStr[20:24],  HexStr[24:26], irOnOff, batteryVoltage) )

		#U.logger.log(20, "{}   trigTime:{},  Trig:{}, deltaTime:{};  updateIndigoTiming:{}, dada:{}".format(mac, trigTime, Trig, deltaTime, BLEsensorMACs[mac][sensor]["updateIndigoTiming"], data[sensor][devId]) )
		if  trigTime or Trig != "":
			trig = ""
			if trigTime:	 trig  = "Time/"
			elif Trig !="" : trig  += Trig
			data[sensor][devId]["trigger"]  					= trig.strip("/")
			U.sendURL({"sensors":data})
			# save last values to comapre at next round, check if we should send if delta  > paramter
			BLEsensorMACs[mac][sensor]["lastUpdate"] 					= time.time()
			BLEsensorMACs[mac][sensor]["onOff"] 	 					= onOff#  = ALL OR JUST BUTTON 
			BLEsensorMACs[mac][sensor]["onOff1"] 	 					= onOff1# == button
			BLEsensorMACs[mac][sensor]["onOff2"] 	 					= moving
			BLEsensorMACs[mac][sensor]["onOff3"] 	 					= hallSensor
			BLEsensorMACs[mac][sensor]["onOff4"] 	 					= freeFall
			BLEsensorMACs[mac][sensor]["onOff5"] 	 					= PIR
			BLEsensorMACs[mac][sensor]["onOff6"] 	 					= IR
			BLEsensorMACs[mac][sensor]["temp"] 	 	 					= temp
			BLEsensorMACs[mac][sensor]["hum"] 	 	 					= hum
			BLEsensorMACs[mac][sensor]["AmbientTemperature"] 			= AmbientTemperature
			BLEsensorMACs[mac][sensor]["accelerationX"] 				= accelerationX
			BLEsensorMACs[mac][sensor]["accelerationY"] 				= accelerationY
			BLEsensorMACs[mac][sensor]["accelerationZ"] 				= accelerationZ

			if fastSwitchBotPress != "": doFastSwitchBotPress(mac, fastSwitchBotPress)

		return tx, batteryLevel, sensor, mac, "sensor", False
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return tx, "", UUID, Maj, Min, False


#################################
def doBLESatech( mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor):
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
	p = 2; 	temp = round(signedIntfrom16(dataString[p :p+4]) /255.,2)
	p = 6;	hum  = round(signedIntfrom16(dataString[p :p+4]) /255.,1)

elif   HexStr.find("0201060303E1FF1216E1FFA103") == 2:	
	subType 	= "accel"
	dataString 	= HexStr.split("0201060303E1FF")[1]
	dataString 	= dataString.split("E1FFA1")[1][2:]
	dataString 	= dataString.split(macplain)[0]
	# == 5D0000000000F2
	p = 2 
	accelerationX 	= signedIntfrom16(dataString[p  :p+4 ]) *4
	accelerationY	= signedIntfrom16(dataString[p+4:p+8 ]) *4
	accelerationZ 	= signedIntfrom16(dataString[p+8:p+12]) *4
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

		devId				= BLEsensorMACs[mac][sensor]["devId"]

		subType = ""
		if     HexStr.find("0201060303E1FF1016E1FFA104") == 2:	subType 	= "tempHum"
		elif   HexStr.find("0201060303E1FF1216E1FFA103") == 2:	subType 	= "accel"
		elif   HexStr.find("0201060303AAFE1116AAFE2000") == 2:	subType 	= "genInfo"
		elif   HexStr.find("0201060303E1FF0F16E1FFA1FF") == 2:	subType 	= "sos"

		data   = {sensor:{devId:{}}}
		data[sensor][devId] = {"type":sensor,"mac":mac,"rssi":float(rx),"txPower":-60}

		if BLEsensorMACs[mac][sensor]["SOS"] and subType != "sos":
			data[sensor][devId]["trigger"] = "SOS_Off"
			U.sendURL({"sensors":data})
			BLEsensorMACs[mac][sensor]["SOS"] 	= False

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
			if  not  BLEsensorMACs[mac][sensor]["SOS"]:
				data[sensor][devId]["trigger"] = "SOS_button_pressed@"+datetime.datetime.now().strftime("%Y-%m%d-%H:%M:%S")
				U.sendURL({"sensors":data})
			BLEsensorMACs[mac][sensor]["SOS"] 	= True
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
			trigTime2 			= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate2"]   > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]			# send min every xx secs
			if  trigTime2 or Trig2 != "":
				trig = ""
				if trigTime2: 	  trig  = "Time/"
				elif Trig2 != "": trig  += Trig2
				data[sensor][devId]["trigger"]  					= trig.strip("/")
				U.sendURL({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac][sensor]["lastUpdate2"] 					= time.time()
				BLEsensorMACs[mac][sensor]["chipTemperature"] 	 	 		= chipTemperature
				BLEsensorMACs[mac][sensor]["secsSinceStart"] 	 	 		= secsSinceStart
				BLEsensorMACs[mac][sensor]["counter"] 	 	 				= counter
				BLEsensorMACs[mac][sensor]["batteryVoltage"] 	 	 		= batteryVoltage

		elif  subType == "tempHum": 	
			dataString 	= HexStr.split("0201060303E1FF")[1]
			dataString 	= dataString.split("E1FFA1")[1][2:]
			dataString 	= dataString.split(macplain)[0]
			p = 2; 	temp = round(signedIntfrom16(dataString[p :p+4]) /255.,2)   + BLEsensorMACs[mac][sensor]["offsetTemp"]
			p = 6;	hum  = int(signedIntfrom16(dataString[p :p+4]) /255. + 0.5) + BLEsensorMACs[mac][sensor]["offsetHum"]
			if abs(BLEsensorMACs[mac][sensor]["temp"] - temp) >= BLEsensorMACs[mac][sensor]["updateIndigoDeltaTemp"]: 	Trig1 +=  "temp/"
			if abs(BLEsensorMACs[mac][sensor]["hum"] - hum)   >= 2: 											Trig1 +=  "hum/"
			batteryLevel 	= int(dataString[0:2],16)
			data[sensor][devId]["temp"] 		= temp 
			data[sensor][devId]["hum"] 			= hum 
			data[sensor][devId]["batteryLevel"] = batteryLevel

			trigTime1 			= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate1"]   > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]			# send min every xx secs
			if  trigTime1 or Trig1 != "":
				trig = ""
				if trigTime1: 	  trig  = "Time/"
				elif Trig1 != "": trig  += Trig1
				data[sensor][devId]["trigger"]  					= trig.strip("/")
				U.sendURL({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac][sensor]["lastUpdate1"] 					= time.time()
				BLEsensorMACs[mac][sensor]["temp"] 	 	 					= temp
				BLEsensorMACs[mac][sensor]["hum"] 	 	 					= hum

		elif  subType  == "accel":
			dataString 	= HexStr.split("0201060303E1FF")[1]
			dataString 	= dataString.split("E1FFA1")[1][2:]
			dataString 	= dataString.split(macplain)[0]
			p = 2 
			accelerationX 	= signedIntfrom16(dataString[p  :p+4 ]) *4
			accelerationY	= signedIntfrom16(dataString[p+4:p+8 ]) *4
			accelerationZ 	= signedIntfrom16(dataString[p+8:p+12]) *4
			accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)
		# make deltas compared to last send 
			dX 			= abs(BLEsensorMACs[mac][sensor]["accelerationX"]		- accelerationX)
			dY 			= abs(BLEsensorMACs[mac][sensor]["accelerationY"]		- accelerationY)
			dZ 			= abs(BLEsensorMACs[mac][sensor]["accelerationZ"]		- accelerationZ)

			dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
			deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000
			trigAccel 	= dTot			> BLEsensorMACs[mac][sensor]["updateIndigoDeltaAccelVector"] 	# acceleration change triggers 
			trigDeltaXZY= deltaXYZ		> BLEsensorMACs[mac][sensor]["updateIndigoDeltaMaxXYZ"]			# acceleration-turn change triggers 
			if trigAccel:    							Trig += "accel/"
			if trigDeltaXZY: 							Trig += "deltaXYZ/"
			data[sensor][devId]["accelerationTotal"] 		= int(accelerationTotal)
			data[sensor][devId]["accelerationX"] 			= int(accelerationX)
			data[sensor][devId]["accelerationY"] 			= int(accelerationY)
			data[sensor][devId]["accelerationZ"] 			= int(accelerationZ)
			data[sensor][devId]["accelerationXYZMaxDelta"]  = int(deltaXYZ)
			data[sensor][devId]["accelerationVectorDelta"]  = int(dTot)

			trigTime 			= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]   > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]# send min every xx secs
			if  trigTime or Trig != "":
				trig = ""
				if trigTime:	 trig  = "Time/"
				elif Trig != "": trig  += Trig
				data[sensor][devId]["trigger"]  					= trig.strip("/")
				U.sendURL({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac][sensor]["lastUpdate"] 					= time.time()
				BLEsensorMACs[mac][sensor]["accelerationX"] 				= accelerationX
				BLEsensorMACs[mac][sensor]["accelerationY"] 				= accelerationY
				BLEsensorMACs[mac][sensor]["accelerationZ"] 				= accelerationZ

		return tx, batteryLevel, sensor, mac, "sensor", False


	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return tx, "", UUID, Maj, Min, False


#################################
def batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=3000., batteryVoltAt0=2700.):
	try:
		batteryLowVsTemp			= (1. + 0.7*min(0.,temp-10.)/100.) * batteryVoltAt0 
		batteryLevel 				= int(min(100.,max(0.,100.* (batteryVoltage - batteryLowVsTemp)/(batteryVoltAt100-batteryLowVsTemp))))
		return batteryLevel
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 0

#################################
def domyBlueT( mac, rx, tx, hexData, UUID, Maj, Min,sensor):
	global BLEsensorMACs
	try:
		if len(hexData) < 55:
			return tx, "", UUID, Maj, Min, True
		UUID = hexData[12:40]
		Maj	 = str(intFrom16(hexData, 40))
		Min	 = str(intFrom16(hexData, 44))

		RawData = hexData[48:48+6] # get bytes # 31,32,33	 (starts at # 0 , #33 has sign, if !=0 subtract 2**15
		RawData = [int(RawData[0],16), int(RawData[1],16), int(RawData[2],16)]
		#RawData = list(struct.unpack("BBB", pkt[31:34])) # get bytes # 31,32,33	 (starts at # 0 , #33 has sign, if !=0 subtract 2**15
		if RawData[2] != 0: tSign = 0x10000 # == 65536 == 2<<15
		else:				tSign = 0
		r8				= RawData[1] << 8 
		sensorData		= ( r8 + RawData[0] - tSign ) /100.
		sensor			= "BLEmyBlueT"
		devId			= BLEsensorMACs[mac][sensor]["devId"]
		try:	temp  	= (sensorData + BLEsensorMACs[mac][sensor]["offsetTemp"]) * BLEsensorMACs[mac][sensor]["multTemp"]
		except: temp  	= sensorData
		#U.logger.log(20, "{}   RX:{}; TX:{}; temp:{}".format(mac, rx, tx, temp) )
		# print "raw, tSign, t1<<8, sensorData, sensorData*9./5 +32.", RawData, tSign, r8, temp, sensorData, sensorData*9./5 +32.
		if time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]  > BLEsensorMACs[mac][sensor]["updateIndigoTiming"]: 
			data   = {sensor:{devId:{}}}
			data[sensor][devId] = {"temp":temp, "type":sensor,"mac":mac,"rssi":float(rx),"txPower":float(tx)}
			U.sendURL({"sensors":data})
			BLEsensorMACs[mac][sensor]["lastUpdate"] = time.time()
		return tx, "", "myBlueT", mac, "sensor", True
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
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
def doBLEapril(mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min,sensor):
	global BLEsensorMACs, sensors
	try:
		
		hexData = hexData[12:]
		if len(hexData) < 37: 							return tx, "", UUID, Maj, Min, False



		sensType = ""
		if   hexData.find("1F020106030359FE171659FEAB0103"+macplainReverse) ==0: sensType = "TAccel"
		elif hexData.find("1A020106030359FE121659FEAB03"+macplainReverse)   ==0: sensType = "THL"
		else:						return tx, "", UUID, Maj, Min, False

		Maj  			= mac
		Min  			= "sensor"



		if sensType == "TAccel":
			""" format:
  pos        01234567 89112345 67 89 21 23 45 67 89 31 23 45 67 89 41 23 45 67 89 51 23 45 67 89 61 23                  
			 1F020106 030359FE 17 16 59 FE AB 01 03 D9 7E 3D 2E CA D2 5A 00 01 F9 D7 29 04 16 64 00 00 D2 
                                                    rmac------------- tt tt SM xx yy zz cd ld BB TX BS RX
			"""


			UUID 						= "BLEaprilAccel"


			# unpack   sensor data 
			p = 42
			# does not work temp 			= signedIntfrom16(hexData[p+2:p+4]+hexData[p:p+2])/8.
			onOff1 			= intFrom8(hexData[p+4:p+6 ],0) !=0 # move
			accelerationX 	= signedIntfrom8(hexData[p+6:p+8 ])*16*.95
			accelerationY 	= signedIntfrom8(hexData[p+8:p+10])*16*.95
			accelerationZ 	= signedIntfrom8(hexData[p+10:p+12])*16*.95
			currEvSecs		= intFrom8(hexData[p+12:p+14],0)
			prevEvSec		= intFrom8(hexData[p+14:p+16],0)
			batteryLevel	= intFrom8(hexData[p+16:p+18],0)
			TXint	  		= intFrom8(hexData[p+18:p+20],0)
			onOff			= intFrom8(hexData[p+20:p+22],0) !=0 # button
			accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)

			# make deltas compared to last send 
			#dT 			= abs(BLEsensorMACs[mac][sensor]["temp"]				- temp)
			dX 			= abs(BLEsensorMACs[mac][sensor]["accelerationX"]		- accelerationX)
			dY 			= abs(BLEsensorMACs[mac][sensor]["accelerationY"]		- accelerationY)
			dZ 			= abs(BLEsensorMACs[mac][sensor]["accelerationZ"]		- accelerationZ)

			dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
			deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000

			deltaTime 	= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]

			# check if we should send data to indigo
			trigMinTime	= deltaTime 	> BLEsensorMACs[mac][sensor]["minSendDelta"] 				# dont send too often
			trigTime 	= deltaTime 	> BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
			trigAccel 	= dTot			> BLEsensorMACs[mac][sensor]["updateIndigoDeltaAccelVector"] 	# acceleration change triggers 
			trigonOff 	= onOff != BLEsensorMACs[mac][sensor]["onOff"] or  onOff1 != BLEsensorMACs[mac][sensor]["onOff1"]
			trigDeltaXZY= deltaXYZ		> BLEsensorMACs[mac][sensor]["updateIndigoDeltaMaxXYZ"]			# acceleration-turn change triggers 
			trig = ""
			if trigTime:		trig += "Time/"
			else:
				if trigAccel:	trig += "Accel-Total/"
				if trigDeltaXZY:trig += "Accel-Max-xyz/"
				#if trigTemp:	trig += "temp/"
			#U.logger.log(20, "mac:{}    trigMinTime:{} deltaXYZ:{}, trig:{} acc xyz:{};{};{}".format(mac, trigMinTime, deltaXYZ, trig, accelerationX, accelerationY, accelerationZ) )

			if trigMinTime and	( trigTime or trigAccel or trigDeltaXZY or trigonOff):
				dd={   # the data dict to be send 
					'accelerationTotal': 	int(accelerationTotal),
					'accelerationX': 		int(accelerationX),
					'accelerationY': 		int(accelerationY),
					'accelerationZ': 		int(accelerationZ),
					'accelerationXYZMaxDelta':int(deltaXYZ),
					'accelerationVectorDelta':int(dTot),
					'onOff': 				onOff,
					'onOff1': 				onOff1,
					'batteryLevel': 		int(batteryLevel),
					'trigger': 				trig.strip("/"),
					'mac': 					mac,
					"rssi":					int(rx)
				}

				## compose complete message
				U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})
				fastSwitchBotPress = "on" if (onOff or onOff1) else ""
				if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)

				# remember last values
				BLEsensorMACs[mac][sensor]["lastUpdate"] 			= time.time()
				BLEsensorMACs[mac][sensor]["accelerationX"] 		= accelerationX
				BLEsensorMACs[mac][sensor]["accelerationY"] 		= accelerationY
				BLEsensorMACs[mac][sensor]["accelerationZ"] 		= accelerationZ
				BLEsensorMACs[mac][sensor]["onOff"] 				= onOff
				BLEsensorMACs[mac][sensor]["onOff1"] 				= onOff1
			return tx, batteryLevel, UUID, Maj, Min, False


		elif sensType == "THL":

			""" format:
	pos		 01 23 45 67 89 11 23 45  67 89 21 23 45 67 89 31 23 45 67 89 41 23 45 67 89 51 23
			 1A 02 01 06 03 03 59 FE  12 16 59 FE AB 03 57 C1 56 C5 9C EF 64 D8 00 5F 00 18 00 AC
                                                        RMAC ------------ BB t2 t1 h2 h1 l2 l1 RX
			"""

			UUID 						= "BLEaprilTHL"


			# unpack   sensor data 
			p = 42
			batteryLevel	= intFrom8(hexData[p-2:p],0)
			temp 			= signedIntfrom16(hexData[p+2:p+4]+hexData[p+0:p+2])/8. + BLEsensorMACs[mac][sensor]["offsetTemp"]
			hum  			= intFrom16(hexData[p+6:p+8]+hexData[p+4:p+6],0)/2.
			illuminance		= intFrom16(hexData[p+10:p+12]+hexData[p+8:p+10],0)

			#U.logger.log(20,u"doBLEapril THL {} temp:{}, hum:{}, illuminance:{}; hexdata:{}".format(mac, temp, hum, illuminance, hexData[p:p+12]))

			# make deltas compared to last send 
			Trig 	= 			abs(BLEsensorMACs[mac][sensor]["temp"]			- temp) > 0.5
			Trig 	= Trig or 	abs(BLEsensorMACs[mac][sensor]["hum"]			- hum) > 2.
			Trig 	= Trig or 	abs(BLEsensorMACs[mac][sensor]["illuminance"]	- illuminance) > 10.


			deltaTime 	= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]

			# check if we should send data to indigo
			trigMinTime	= deltaTime 	> BLEsensorMACs[mac][sensor]["minSendDelta"] 				# dont send too often
			trigTime 	= deltaTime 	> BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
			trig = ""

			if Trig or trigTime:
				dd={   # the data dict to be send 
					'hum': 					int(hum),
					'temp': 				round(temp,1),
					'illuminance': 			illuminance,
					'batteryLevel': 		int(batteryLevel),
					'mac': 					mac,
					"rssi":					int(rx)
				}

				## compose complete message
				U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})

				# remember last values
				BLEsensorMACs[mac][sensor]["lastUpdate"] 			= time.time()
				BLEsensorMACs[mac][sensor]["temp"] 					= temp
				BLEsensorMACs[mac][sensor]["hum"] 					= hum
				BLEsensorMACs[mac][sensor]["illuminance"] 			= illuminance
			return tx, batteryLevel, UUID, Maj, Min, False

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False


#################################
def doBLEminew(mac, macplain, macplainReverse, rx, tx, hexData, UUID, Maj, Min, sensor):
	global BLEsensorMACs, sensors
	try:
		
		hexData = hexData[12:]
		if len(hexData) < 44: 							return tx, "", UUID, Maj, Min, False

		#U.logger.log(20,u"doBLEminew {}  hexData:{}; x:{} y:{}, z:{}".format(mac, hexData, hexData[30:34], hexData[34:38], hexData[38:42]))


		sensType =""
		if   hexData.find("1A0201060303E1FF1216E1FFA103") ==0: sensType = "ACC"
		elif hexData.find("180201060303E1FF1016E1FFA101") ==0: sensType = "TH"
		elif hexData.find("150201060303E1FF0D16E1FFA102") ==0: sensType = "light"
		elif hexData.find("190201060303AAFE1116AAFE2000") ==0: sensType = "batteryVoltage"
		else:						return tx, "", UUID, Maj, Min, False

		Maj  			= mac
		Min  			= "sensor"
		batteryLevel	= intFrom8(hexData, 28)

		#U.logger.log(20,u"doBLEminew {}  sensType:{},  hexdata:{} ".format(mac,sensType, hexData))
		if sensType == "batteryVoltage":
			p = 28
			BLEsensorMACs[mac][sensor]["batteryVoltage"] = signedIntfrom16(hexData[ p :p+4 ]) # in mV
			#U.logger.log(20,u"doBLEminews1TH {}  sensType:{},  batteryVoltage:{}, hexdata:{} {} ".format(mac,sensType, BLEsensorMACs[mac][sensor]["batteryVoltage"],hexData[p:p+2],hexData[p+2:p+4]))


		elif sensType == "light":
			""" format:
			   pos: 01 23 45 67   89 11 23 45   67 89 21 23 45 67 89 31 23 45 67 89 41 23 
			hexData:15 02 01 06   03 03 E1 FF   0D 16 E1 FF A1 02 64 00 74 35 A4 3F 23 AC 
					15 02 01 06   03 03 E1 FF   0D 16 E1 FF A1 02 64 01 74 35 A4 3F 23 AC 
												                  BB  = Battery
														             li = light  is 00 or 01
			"""


			UUID 						= "BLEminew"


			# unpack   sensor data 
			p = 30;	onOff 			= int(hexData[ p :p+2 ]) !=0
			p = 28;	batteryLevel 	= int(hexData[ p :p+2 ])

			deltaTime 	= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]
			deltaonOff 	= onOff != BLEsensorMACs[mac][sensor]["onOff"]

			# check if we should send data to indigo
			trigMinTime	= deltaTime 	> BLEsensorMACs[mac][sensor]["minSendDelta"] 				# dont send too often
			trigTime 	= deltaTime 	> BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
#U.logger.log(20, "mac:{}    trigMinTime:{} deltaXYZ:{}, trig:{} acc xyz:{};{};{}".format(mac, trigMinTime, deltaXYZ, trig, accelerationX, accelerationY, accelerationZ) )

			if trigMinTime and	( trigTime or trigAccel or trigDeltaXZY ):
				dd={   # the data dict to be send 
					'onOff': 				onOff,
					'batteryLevel': 		int(batteryLevel),
					"rssi":					int(rx),
				}
				if BLEsensorMACs[mac][sensor]["batteryVoltage"] != -1:
					dd["batteryVoltage"] = BLEsensorMACs[mac][sensor]["batteryVoltage"]
				#U.logger.log(20, " .... sending  data:{}".format( dd ) )

				## compose complete message
				U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})

				# remember last values
				BLEsensorMACs[mac][sensor]["lastUpdate"] 			= time.time()
				BLEsensorMACs[mac][sensor]["onOff"] 				= onOff
				fastSwitchBotPress = "on" if onOff else "off"
				if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)

			return tx, batteryLevel, UUID, Maj, Min, False

		elif sensType == "ACC":
			""" format:
			hexData:1A0201060303E1FF1216E1FFA103640005FFFB01004B80A33F23ACEC; x:0005 y:FFFB, z:0100
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


			UUID 						= "BLEminew"


			# unpack   sensor data 
			p = 30
			accelerationX 	= signedIntfrom16(hexData[ p :p+4 ])*(10./2.45) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationY 	= signedIntfrom16(hexData[p+4:p+8 ])*(10./2.45)
			accelerationZ 	= signedIntfrom16(hexData[p+8:p+12])*(10./2.45)
			accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)

			# make deltas compared to last send 
			dX 			= abs(BLEsensorMACs[mac][sensor]["accelerationX"]		- accelerationX)
			dY 			= abs(BLEsensorMACs[mac][sensor]["accelerationY"]		- accelerationY)
			dZ 			= abs(BLEsensorMACs[mac][sensor]["accelerationZ"]		- accelerationZ)

			dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
			deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000

			deltaTime 	= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate1"]

			# check if we should send data to indigo
			trigMinTime	= deltaTime 	> BLEsensorMACs[mac][sensor]["minSendDelta"] 				# dont send too often
			trigTime 	= deltaTime 	> BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
			trigAccel 	= dTot			> BLEsensorMACs[mac][sensor]["updateIndigoDeltaAccelVector"] 	# acceleration change triggers 
			trigDeltaXZY= deltaXYZ		> BLEsensorMACs[mac][sensor]["updateIndigoDeltaMaxXYZ"]			# acceleration-turn change triggers 
			trig = ""
			if trigTime:		trig += "Time/"
			else:
				if trigAccel:	trig += "Accel-Total/"
				if trigDeltaXZY:trig += "Accel-Max-xyz/"
			#U.logger.log(20, "mac:{}    trigMinTime:{} deltaXYZ:{}, trig:{} acc xyz:{};{};{}".format(mac, trigMinTime, deltaXYZ, trig, accelerationX, accelerationY, accelerationZ) )

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
					'mac': 					mac,
					"rssi":					int(rx)
				}
				if BLEsensorMACs[mac][sensor]["batteryVoltage"] != -1:
					dd["batteryVoltage"] = BLEsensorMACs[mac][sensor]["batteryVoltage"]
				#U.logger.log(20, " .... sending  data:{}".format( dd ) )

				## compose complete message
				U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})

				# remember last values
				BLEsensorMACs[mac][sensor]["lastUpdate1"] 			= time.time()
				BLEsensorMACs[mac][sensor]["accelerationX"] 		= accelerationX
				BLEsensorMACs[mac][sensor]["accelerationY"] 		= accelerationY
				BLEsensorMACs[mac][sensor]["accelerationZ"] 		= accelerationZ
			return tx, batteryLevel, UUID, Maj, Min, False


		if sensType == "TH":

			""" format:

		   pos: 01 23 45 67 89 11 23 45 67 89 21 23 45 67 89 31 23 45 67 89 41 23 45 67  
		hexData:18 02 01 06 03 03 E1 FF 10 16 E1 FF A1 01 64 15 91 41 9C 79 B8 A1 3F 23 
														  BB  = Battery
															 temp- 
																   HUM-- 
		hexData:18 02 01 06 03 03 E1 FF 10 16 E1 FF A1 01 64 15 91 41 9C  rmac############
			"""
				
			UUID 						= "BLEminew"
			

			# unpack   sensor data 
			p = 30
			temp 				= float(signedIntfrom8(hexData[ p   :p+2 ]))  + intFrom8(hexData[p+2:p+4],0)/256. + BLEsensorMACs[mac][sensor]["offsetTemp"]
			hum				 	= float(signedIntfrom8(hexData[ p+4 :p+6 ]))  + intFrom8(hexData[p+6:p+8],0)/256. + BLEsensorMACs[mac][sensor]["offsetHum"]
			#U.logger.log(20,u"doBLEminews1TH {}  pos:{}, temp:{}, hum:{}, hexdata:{} {} {} {}".format(mac,TagPos, temp, hum, hexData[p:p+2],hexData[p+2:p+4],hexData[p+4:p+6],hexData[p+6:p+8]))

			# make deltas compared to last send 
			Trig 	= 			abs(BLEsensorMACs[mac][sensor]["temp"]		- temp) > 0.5
			Trig 	= Trig or 	abs(BLEsensorMACs[mac][sensor]["hum"]		- hum) > 2.


			deltaTime 	= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]

			# check if we should send data to indigo
			trigMinTime	= deltaTime 	> BLEsensorMACs[mac][sensor]["minSendDelta"] 				# dont send too often
			trigTime 	= deltaTime 	> BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
			trig = ""

			if Trig or trigTime:
				dd={   # the data dict to be send 
					'hum': 					int(hum),
					'temp': 				round(temp,1),
					'batteryLevel': 		int(batteryLevel),
					'mac': 					mac,
					"rssi":					int(rx)
				}
				if BLEsensorMACs[mac][sensor]["batteryVoltage"] != -1:
					dd["batteryVoltage"] = BLEsensorMACs[mac][sensor]["batteryVoltage"]
				#U.logger.log(20, " .... sending  data:{}".format( dd ) )

				## compose complete message
				U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})

				# remember last values
				BLEsensorMACs[mac][sensor]["lastUpdate"] 			= time.time()
				BLEsensorMACs[mac][sensor]["temp"] 					= temp
				BLEsensorMACs[mac][sensor]["hum"] 					= hum
			return tx, batteryLevel, UUID, Maj, Min, False

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,u"mac#{}; sensor:{}, sensType:{}, hexdata:{}".format(mac, sensor, sensType, hexData))
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False



#################################
#################################
## Ruuvi ########################
#################################
def doRuuviTag( mac, rx, tx, hexData, UUID, Maj, Min,sensor):
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
		
		if len(hexData) < 44: 	
			#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,u"mac:{};  < 44..{} ".format(mac, len(hexData))) 
			return tx, "", UUID, Maj, Min, False
		#        mac---------  ll flag   ll tag 
		#        012345678911 23 456789 21 23456789 
		#		 012345678901 1F 020106 1B FF990405
		ruuviTag 		= "0201061BFF9904"
		ruuviTagPos 	= hexData.find(ruuviTag) 
		tagFound		= ruuviTagPos == 14 
		if not tagFound: 		
			#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,u"mac:{};  tagnotfound..{}".format(mac, tag )) 
			return tx, "", UUID, Maj, Min, False

		UUID 						= "ruuviTag"
		Maj  						= mac
		Min  						= "sensor"
		sensor 						= "BLERuuviTag"
		# make data into right format (bytes)
		byte_data 					= bytearray.fromhex(hexData[ruuviTagPos + len(ruuviTag):])
		dataFormat					= byte_data[0]

		# sensor is active, get all data and send if conditions ok
		# unpack  rest of sensor data 
		accelerationTotal, accelerationX, accelerationY, accelerationZ 	= doRuuviTag_magValues(byte_data)
		temp 					= (doRuuviTag_temperature(byte_data)+ BLEsensorMACs[mac][sensor]["offsetTemp"]) * BLEsensorMACs[mac][sensor]["multTemp"]
		batteryVoltage, txPower = doRuuviTag_powerinfo(byte_data)
		batteryLevel 			= batLevelTempCorrection(batteryVoltage, temp)
		# make deltas compared to last send 
		dX 			= abs(BLEsensorMACs[mac][sensor]["accelerationX"]		- accelerationX)
		dY 			= abs(BLEsensorMACs[mac][sensor]["accelerationY"]		- accelerationY)
		dZ 			= abs(BLEsensorMACs[mac][sensor]["accelerationZ"]		- accelerationZ)
		dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
		deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000

		deltatemp 	= abs(BLEsensorMACs[mac][sensor]["temp"] - temp)  
		deltaTime 	= time.time() - BLEsensorMACs[mac][sensor]["lastUpdate"]

		# check if we should send data to indigo
		trigMinTime	= deltaTime 	> BLEsensorMACs[mac][sensor]["minSendDelta"] 				# dont send too often
		trigTime 	= deltaTime 	> BLEsensorMACs[mac][sensor]["updateIndigoTiming"]  			# send min every xx secs
		trigTemp 	= deltatemp 	> BLEsensorMACs[mac][sensor]["updateIndigoDeltaTemp"] 			# temp change triggers
		trigAccel 	= dTot			> BLEsensorMACs[mac][sensor]["updateIndigoDeltaAccelVector"] 	# acceleration change triggers 
		trigDeltaXZY= deltaXYZ		> BLEsensorMACs[mac][sensor]["updateIndigoDeltaMaxXYZ"]			# acceleration-turn change triggers 
		trig = ""
		if trigTime:		trig += "Time/"
		else:
			if trigTemp: 	trig += "Temp/"
			if trigAccel:	trig += "Accel-Total/"
			if trigDeltaXZY:trig += "Accel-Max-xyz/"
		#U.logger.log(20, "mac:{}    trigMinTime:{} deltaXYZ:{}, trig:{}".format(mac, trigMinTime, deltaXYZ, trig) )

		if trigMinTime and ( trigTime or trigTemp or trigAccel or trigDeltaXZY ):
			dd={   # the data dict to be send 
				'data_format': 			dataFormat,
				'hum': 					int(doRuuviTag_humidity(byte_data)	 + BLEsensorMACs[mac][sensor]["offsetHum"] + 0.5),
				'temp': 				round(temp							 + BLEsensorMACs[mac][sensor]["offsetTemp"],1),
				'press': 				round(doRuuviTag_pressure(byte_data) + BLEsensorMACs[mac][sensor]["offsetPress"],1),
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
				'mac': 					mac,
				"rssi":					int(rx)
			}
			#U.logger.log(20, " .... sending  data:{}".format( dd ) )

			## compose complete message
			U.sendURL({"sensors":{sensor:{BLEsensorMACs[mac][sensor]["devId"]:dd}}})

			# remember last values
			BLEsensorMACs[mac][sensor]["lastUpdate"] 			= time.time()
			BLEsensorMACs[mac][sensor]["accelerationTotal"] 	= accelerationTotal
			BLEsensorMACs[mac][sensor]["accelerationX"] 		= accelerationX
			BLEsensorMACs[mac][sensor]["accelerationY"] 		= accelerationY
			BLEsensorMACs[mac][sensor]["accelerationZ"] 		= accelerationZ
			BLEsensorMACs[mac][sensor]["temp"] 					= temp

		# overwrite UUID etc for this ibeacon if used later
		#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,u"mac:{};  returning.. batteryLevel:{}".format(mac, batteryLevel)) 
		return str(txPower), batteryLevel, UUID, Maj, Min, False

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return tx, "", UUID, Maj, Min, False


#################################
def doRuuviTag_temperature( data):
	"""Return temperature in celsius"""
	if data[1:2] == 0x7FFF:
		return 0

	temperature = twos_complement((data[1] << 8) + data[2], 16) / 200
	return round(temperature, 1)

#################################
def doRuuviTag_humidity( data):
	"""Return humidity %"""
	if data[3:4] == 0xFFFF:
		return 0

	humidity = ((data[3] & 0xFF) << 8 | data[4] & 0xFF) / 400
	return round(humidity, 1)

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
	if (	data[7:8] == 0x7FFF or
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
	global logCountTrackMac, trackMac, trackRawOnly, trackmacFilter, nLogMgsTrackMac, startTimeTrackMac, trackMacText, collectTime
	try:
		if not os.path.isfile(G.homeDir+"temp/beaconloop.trackmac"): return False

		f = open(G.homeDir+"temp/beaconloop.trackmac","r")
		xx = f.read().strip("\n")
		f.close()
		xx 					= xx.split("-")
		trackRawOnly 		= False
		trackmacFilter 		= ""
		collectTime 		= 30 
		nLogMgsTrackMac		= 11 # # of message logged for sepcial mac 
		logCountTrackMac 	= nLogMgsTrackMac
		if len(xx) == 2:
			if xx[1].lower().find("raw") > -1:
				trackRawOnly = True
				logCountTrackMac = nLogMgsTrackMac * 5
				collectTime = 50 
			elif xx[1].lower().find("~filter~") > -1:
				trackmacFilter = xx[1].split("~filter~")[1]
				logCountTrackMac  = nLogMgsTrackMac * 10
				collectTime = 90 
		elif len(xx) == 3: 
			if xx[1].lower().find("raw") > -1:
				trackRawOnly = True
				logCountTrackMac = nLogMgsTrackMac * 5
				collectTime = 50 
			if xx[2].lower().find("~filter~") > -1:
				trackmacFilter = xx[2].split("~filter~")[1]
				logCountTrackMac  = nLogMgsTrackMac * 10
				collectTime = 90 

		trackMac = xx[0]
		trackMacText = ""
		writeTrackMac("START   ","\nTRACKMAC started on pi#:{}, for MAC# {}, options: raw:{}, filter:>{}<".format(G.myPiNumber, trackMac, trackRawOnly, trackmacFilter), trackMac+"\n" )
		startTimeTrackMac = time.time()
		subprocess.call("rm {}temp/beaconloop.trackmac".format(G.homeDir), shell=True)
		subprocess.call("rm {}temp/trackmac.log".format(G.homeDir), shell=True)
		if trackMac =="*": logCountTrackMac *=3
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)


#################################
def trackMacStopIf(hexstr, mac):
	global logCountTrackMac, trackMac, nLogMgsTrackMac, startTimeTrackMac, trackMacText, collectTime
	try:

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac > 0:
			logCountTrackMac -= 1
			writeTrackMac("RAW===  ",  "{};  count: {}; time left:{:3.0f}; hex: {}".format( datetime.datetime.now().strftime("%H:%M:%S.%f")[:-5], logCountTrackMac,  (startTimeTrackMac+collectTime -time.time()), hexstr) ,mac)
			
		if logCountTrackMac == 0 or (startTimeTrackMac > 0 and time.time() - startTimeTrackMac > collectTime):
			writeTrackMac("END     ","FINISHed TRACKMAC logging ===", trackMac)
			logCountTrackMac  = -10
			startTimeTrackMac = -1
			trackMac = ""
			U.sendURL(data={"trackMac":trackMacText}, squeeze=False)

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

#################################
def writeTrackMac(textOut0, textOut2, mac):
	global logCountTrackMac, trackMac, trackRawOnly, trackmacFilter, nLogMgsTrackMac, trackMacText, startTimeTrackMac
	try:
		##print  textOut0+mac+", "+textOut2
		if trackRawOnly and ( textOut0.find("RAW") == -1 and textOut0.find("START ") == -1 and textOut0.find("END ") == -1): return 
		if trackmacFilter != ""  and textOut2.find(trackmacFilter) == -1: return 
		minSecs = datetime.datetime.now().strftime("%M:%S.%f")[:-5] +"-"
		f = open(G.homeDir+"temp/trackmac.log","a")
		if textOut0 == "":
			f.write(textOut2+"\n")
		else:
			f.write(minSecs+textOut0+mac+", "+textOut2+"\n")
		f.close()
		U.logger.log(20,minSecs+textOut0+mac+", "+textOut2)
		trackMacText += minSecs+textOut0+mac+" "+textOut2+";;"
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)


#################################
def fillHCIdump(hexstr):
	global rpiDataAcquistionMethod, BLEcollectStartTime, writeDumpDataHandle
	try:
		if BLEcollectStartTime > 0 and rpiDataAcquistionMethod != "socket":
			if not os.path.isfile(G.homeDir+"temp/hcidump.data") or writeDumpDataHandle == "":
				writeDumpDataHandle = open(G.homeDir+"temp/hcidump.data","a")
			outstring = "> " + " ".join([ hexstr[i:i+2] for i in range(0,len(hexstr),2) ])+"\n"
			writeDumpDataHandle.write(outstring)

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return  hexstr[14:] # start w the MAC#, skip the preamble


#################################
def BLEAnalysisSocket(hci):
	global onlyTheseMAC, knownBeaconTags
	global bleServiceSections, BLEanalysisdataCollectionTime, BLEcollectStartTime
	try:
		if rpiDataAcquistionMethod != "socket": return False

		bluetoothctl = False
		lescanData	 = False
		## init, set dict and delete old files
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
		BLEcollectStartTime = time.time()
		U.logger.log(20, u"starting  BLEAnalysis, rssi cutoff= {}[dBm]".format(BLEanalysisrssiCutoff))
		U.logger.log(20, u"sudo hciconfig {} reset".format(hci))
		subprocess.Popen("sudo hciconfig "+hci+" reset", shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20, "sudo timeout -s SIGINT "+str(BLEanalysisdataCollectionTime)+"s hcitool -i "+hci+" lescan  --duplicates ")
		subprocess.Popen("sudo timeout -s SIGINT "+str(BLEanalysisdataCollectionTime)+"s hcitool -i "+hci+" lescan  --duplicates > "+G.homeDir+"temp/lescan.data &", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		time.sleep(0.3)
		U.logger.log(20, "sudo timeout -s SIGINT "+str(BLEanalysisdataCollectionTime)+"s hcidump -i "+hci+" --raw  | sed -e :a -e '$!N;s/\\n  //;ta' -e 'P;D'")
		subprocess.Popen("sudo timeout -s SIGINT "+str(BLEanalysisdataCollectionTime)+"s hcidump -i "+hci+" --raw  | sed -e :a -e '$!N;s/\\n  //;ta' -e 'P;D' > "+G.homeDir+"temp/hcidump.data &", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		time.sleep(BLEanalysisdataCollectionTime)

		if bluetoothctl:
			U.logger.log(20, "sudo timeout -s SIGINT "+str(BLEanalysisdataCollectionTime)+"s bluetoothctl scan on")
			subprocess.Popen("sudo timeout -s SIGINT "+str(BLEanalysisdataCollectionTime)+"s bluetoothctl scan on > "+G.homeDir+"temp/bluetoothctl.data &", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			time.sleep(BLEanalysisdataCollectionTime+.1)
		U.logger.log(20, "prep done; after@: {:.1f} secs".format(time.time()-BLEcollectStartTime))
		subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

		BLEAnalysis()
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
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	
	BLEcollectStartTime = -1
	return
#################################
def BLEAnalysisStart(hci):
	global onlyTheseMAC, knownBeaconTags, writeDumpDataHandle
	global bleServiceSections, BLEanalysisdataCollectionTime, BLEcollectStartTime, BLEanalysisrssiCutoff
	global rpiDataAcquistionMethod
	try:
		if BLEcollectStartTime == -1 and os.path.isfile(G.homeDir+"temp/beaconloop.BLEAnalysis"): 
			f = open(G.homeDir+"temp/beaconloop.BLEAnalysis","r")
			try: 	BLEanalysisrssiCutoff = int(f.read().strip("\n"))
			except: BLEanalysisrssiCutoff = -99.
			f.close()
			subprocess.call("rm {}temp/beaconloop.BLEAnalysis".format(G.homeDir), shell=True)
			BLEcollectStartTime = time.time()

			U.logger.log(20,u"starting ble analysis with rssi cutoff:{}  using method:{}, for  {} secs, starttimeStamp:{}".format(BLEanalysisrssiCutoff, rpiDataAcquistionMethod, BLEanalysisdataCollectionTime, BLEcollectStartTime))
			if os.path.isfile(G.homeDir+"temp/hcidump.data"):
				subprocess.call("rm {}temp/hcidump.data".format(G.homeDir), shell=True)

			if rpiDataAcquistionMethod == "socket": 
				if BLEAnalysisSocket(hci): return True
			return False

		elif  BLEcollectStartTime >0:
			#U.logger.log(20,u"testing ble analysis :{}".format(time.time() - BLEcollectStartTime))
			if time.time() - BLEcollectStartTime >= BLEanalysisdataCollectionTime: 
				if writeDumpDataHandle !="":
					writeDumpDataHandle.close()
				BLEAnalysis()
				BLEcollectStartTime = -1
			return False

		BLEanalysisdataCollectionTime = 25 # secs 
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	BLEcollectStartTime = -1
	return False

#################################
def BLEAnalysis():
	global onlyTheseMAC, knownBeaconTags, parsedData
	global bleServiceSections, BLEanalysisdataCollectionTime, BLEanalysisrssiCutoff, BLEcollectStartTime
	try:
		if time.time() - BLEcollectStartTime <= BLEanalysisdataCollectionTime: return 
		if not os.path.isfile(G.homeDir+"temp/hcidump.data"): return 
		f = open(G.homeDir+"temp/hcidump.data","r")
		xxx = f.read()
		f.close()
		#print xxx [0:100]
		linesIn = 0
		linesDevices = 0
		linesAccepted = 0
		out = []
		extraLists = {"TLM":[],"iBeacon":[]}
		MACs = {}
		collectionTime = time.time() - BLEcollectStartTime
		for line in xxx.split("\n"):
			max_TX = -99
			linesIn +=1
			if len(line) < 60: 		 continue
			if line.find(">") == -1: continue
			linesAccepted +=1
			line = line[2:].strip()
			items = line.split()
			mac = (items[7:13])[::-1]
			mac = ":".join(mac)
			#U.logger.log(20, " line:{}".format(line))
			hexString = (line.replace(" ",""))[14+12:]
			##U.logger.log(20, "mac:{};   hexstr:{} ".format(mac, hexString ))
			parsePackage(mac, hexString, logData=False)
			if mac not in MACs: 
				MACs[mac] = {"max_rssi":-99, "max_TX": -99,"MSG_in_10Secs": 0,
				"n_of_MSG_Types":0,"typeOfBeacon":[],"typeOfBeacon-msg#":[],"nMessages":[],
				"raw_data":[],"pos_of_MAC":[],"pos_of_r-MAC":[], "possible_knownTag_options":[]}
				for ee in extraLists:
					MACs[mac][ee] = []
				for mmm in bleServiceSections:
					mm  = bleServiceSections[mmm]
					MACs[mac][mm] = []
			present = False

			nMsgNumber = -1
			for ll in MACs[mac]["raw_data"]:
				nMsgNumber += 1
				#print mac, "test   :>{}<".format(ll[0:-3])
				if line[:-3].strip() in ll: # w/o RX
					present = True
					#print mac, "test   : duplicate"
					break
			if not present:
				#U.logger.log(20, "adding:>>{}<< ".format(line[:-3])) 
				MACs[mac]["raw_data"].append( line )
				MACs[mac]["nMessages"].append(0)
				nMsgNumber = len(MACs[mac]["raw_data"]) - 1
				linesDevices +=1
				for mmm in bleServiceSections:
					mm  = bleServiceSections[mmm]
					if mm in parsedData["analyzed"]: 			MACs[mac][mm].append(parsedData["analyzed"][mm])
					else:										MACs[mac][mm].append("")
				for ee in extraLists:
					if ee in parsedData["analyzed"]:			MACs[mac][ee].append(parsedData["analyzed"][ee])
					else:										MACs[mac][ee].append("")

			MACs[mac]["nMessages"][nMsgNumber]+=1
			if "TxPowerLevel" in parsedData["analyzed"]:
				try:
					tx = signedIntfrom8(parsedData["analyzed"]["TxPowerLevel"])
					MACs[mac]["max_TX"] = max(MACs[mac]["max_TX"],tx )
				except: pass
			#print mac, "present:>{}<".format(line[2:-3])
			try: 
				if MACs[mac]["max_TX"]  == - 99:
					max_TX 	= max(MACs[mac]["max_TX"],   signedIntfrom8(line[-5:-3]))
			except: pass
			rssi 	    = max(MACs[mac]["max_rssi"], signedIntfrom8(line[-2:]))
				
			MACs[mac]["MSG_in_10Secs"] +=1
			MACs[mac]["max_rssi"] 		= rssi
			MACs[mac]["max_TX"] 		= max_TX
		out+= "\nhcidump\n" 
		out+= xxx
		U.logger.log(20, "finished  hcidump:     lines -in: {:4d}, accepted: {:4d},  n-devices: {:4d}".format(linesIn,linesAccepted,linesDevices ))


		# clean up 
		delMAC = {}
		for mac in MACs:
			if MACs[mac]["raw_data"]  == []:  
				delMAC[mac] = "Reason: no_raw_data, " + str(MACs[mac])
			if MACs[mac]["max_rssi"] < BLEanalysisrssiCutoff: 
				if mac not in delMAC:
					delMAC[mac]  = "Reason: max_rssi:"+str(MACs[mac]["max_rssi"])+" < cuttoff; " + str( MACs[mac]["raw_data"])
				else:
					delMAC[mac] +=       ", max_rssi:"+str(MACs[mac]["max_rssi"])+" < cuttoff; " + str( MACs[mac]["raw_data"])

		out1 ="\n MACs not accepted:\n"
		for mac in delMAC:
			out1 += "{}: {}\n".format(mac, delMAC[mac])
			del MACs[mac]
		#U.logger.log(20, out1)
		
		knownMACS = {}
		newMACs   = {}
		#U.logger.log(20, "MACs: {} ".format(MACs)) 


		## now combine the  results in to known and new and rejected
		for mac in MACs:
			#print  "tagging mac: : {} ".format(mac)
			MACs[mac]["MSG_in_10Secs"] = "{:.1f}".format(10.* float(MACs[mac]["MSG_in_10Secs"])/collectionTime) #  of messages in 10 secs
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
					knownMACS[mac]["pos_of_MAC"].append(macPos)
					knownMACS[mac]["pos_of_r-MAC"].append(RmacPos)
					knownMACS[mac]["n_of_MSG_Types"] = nmsg

					tag = "other"
					knownMACS[mac]["typeOfBeacon"][-1] = tag
					knownMACS[mac]["typeOfBeacon-msg#"][-1] = nmsg
					knownMACS[mac]["possible_knownTag_options"][-1]= " use: "+tag
					for tag in knownBeaconTags:
						if tag == "other": continue
						#U.logger.log(20, "tag: {} ".format(tag)) 
						posFound, dPostest, Maj, Min, subtypeOfBeacon = testComplexTag(hexStr[12:-2], tag, mac, mac.replace(":",""), hexStr[0:12],"","", calledFrom="BLEAnalysis")
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
					newMACs[mac]["possible_knownTag_options"].append('"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","useOnlyThisTagToAcceptBeaconMsgDefault": 1, "pos": 12,"posDelta": 0,"tag":"'+hexStr[12:-3]+'"}')
					newMACs[mac]["typeOfBeacon"].append("")
					newMACs[mac]["typeOfBeacon-msg#"].append(nmsg)
					newMACs[mac]["pos_of_MAC"].append(macPos)
					newMACs[mac]["pos_of_r-MAC"].append(RmacPos)
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
						posFound, dPostest, Maj, Min, subtypeOfBeacon  = testComplexTag(hexStr[12:-2], tag, mac, mac.replace(":",""), hexStr[0:12], "", "", calledFrom="BLEAnalysis" )
						if posFound != -1:
							newMACs[mac]["typeOfBeacon"][-1] = tag
							newMACs[mac]["typeOfBeacon-msg#"][-1] = nmsg
							newMACs[mac]["possible_knownTag_options"][-1] = '"name_here":{"battCmd": "off", "beepCmd": "off", "dBm": "-61","useOnlyThisTagToAcceptBeaconMsgDefault": 1, "pos": '+str(posFound)+',"posDelta": 0,"tag":"'+hexStr[12:-3]+'"}'
							newMACs[mac]["pos_of_MAC"][-1] = macPos
							newMACs[mac]["pos_of_r-MAC"][-1] = RmacPos
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
		dd = {"BLEAnalysis":{"rejected_Beacons":delMAC, "new_Beacons":newMACs,"existing_Beacons":knownMACS,"rssiCutoff":str(BLEanalysisrssiCutoff)}}
		ldd = len("{}".format(dd))
		U.logger.log(20, "finished  BLEAnalysis: {:.1f} secs, waiting for sending bytes:{}; :\n{}".format(time.time()-BLEcollectStartTime, ldd, "{}".format(dd)[0:300]))
		subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		U.sendURL(dd, squeeze=False, verbose=True, wait=True)
		time.sleep(5.+ min(10,ldd/20000.))
		U.logger.log(20, "========== BLEanalysis finished ========\n")

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	BLEcollectStartTime = -1
	return


#################################
def beep(useHCI):
	global beaconsOnline
	try:	
		restart = False

		while True: 
			if not os.path.isfile(G.homeDir+"temp/beaconloop.beep"): break
			f = open(G.homeDir+"temp/beaconloop.beep","r")
			deviceList = f.read().strip("\n").split("\n")
			f.close()
			subprocess.call("rm {}temp/beaconloop.beep".format(G.homeDir), shell=True)
			U.logger.log(20,u"beepBeacon deviceList:{}".format(deviceList))

			# devices: '{u'24:DA:11:21:2B:20': {u'cmdOff': u'char-write-cmd 0x0011 00', u'cmdON': u'char-write-cmd  0x0011  02', u'beepTime': 2.0}}'
			for devices in deviceList:
				if len(devices) == 0: continue
				devices = json.loads(devices)
				if len(devices) == 0: continue
				expCommands = ""
				stopHCUIDUMPlistener()
				U.killOldPgm(-1,"hcidump")
				U.killOldPgm(-1,"hcitool")
				U.killOldPgm(-1,"lescan")
				restart = True
				cmd = "sudo /bin/hciconfig {} reset".format(useHCI)
				ret = readPopen(cmd)

				#U.logger.log(20,"beepBeacon devices:{}".format(devices))
				for mac in devices:
					#U.logger.log(20,"beepBeacon mac:{}".format(mac))
					if len(mac) < 10: continue
					params		= devices[mac]
					if "mustBeUp" in params and params["mustBeUp"]: force = False
					else:											force = True
					if  not force and mac not in beaconsOnline:
						U.logger.log(20,u"mac: {}; skipping, not online or not in range".format(mac) )
						continue
			
					tryAgain = 3
					for kk in range(3):
						tryAgain -= 1
						if tryAgain < 0: break
						if tryAgain != 2 and expCommands != "":
							try: expCommands.sendline("disconnect")	
							except: pass	

						if "random" in params and params["random"] == "randomON":	random = " -t random"
						else:					 									random = " "
						cmd = "sudo /usr/bin/gatttool -i {} {} -b {} -I".format(useHCI, random, mac) 
						U.logger.log(20,cmd)
						expCommands = pexpect.spawn(cmd)
						ret = expCommands.expect([">","error",pexpect.TIMEOUT], timeout=10)
						if ret == 0:
							U.logger.log(20,u"... successful: {}-{}".format(expCommands.before,expCommands.after))
							connected = True
						else:
							if ii < ntriesConnect-1:
								if ret == 1:	U.logger.log(20, u"... error, giving up: {}-{}".format(expCommands.before,expCommands.after))
								elif ret == 2:	U.logger.log(20, u"... timeout, giving up: {}-{}".format(expCommands.before,expCommands.after))
								else:			U.logger.log(20, "... unexpected, giving up: {}-{}".format(expCommands.before,expCommands.after))
							expCommands.kill(0)
							time.sleep(0.1)
							break

						time.sleep(0.1)

						try:
							cmdON		= params["cmdON"]
							cmdOff		= params["cmdOff"]
							beepTime	= float(params["beepTime"])
							U.logger.log(20,"{}:   cmdON:{};  cmdOff:{};  beepTime:{} ".format(mac, cmdON, cmdOff, beepTime) )

							connected = False
							ntriesConnect = 6
							for ii in range(ntriesConnect):
								try:
									U.logger.log(20,u"expect connect ")
									expCommands.sendline("connect ")
									ret = expCommands.expect(["Connection successful","Error", pexpect.TIMEOUT], timeout=15)
									if ret == 0:
										U.logger.log(20,u"... successful: {}".format(expCommands.after))
										connected = True
										break
									else:
										if ii < ntriesConnect-1: 
											if ret == 1:	U.logger.log(20, u"... error, try again: {}-{}".format(expCommands.before,expCommands.after))
											elif ret == 2:	U.logger.log(20, u"... timeout, try again: {}-{}".format(expCommands.before,expCommands.after))
											else:			U.logger.log(20, "... unexpected, try again: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(1)

								except Exception as e:
									U.logger.log(20,"", exc_info=True)
									if ii < ntriesConnect-1: 
										U.logger.log(20, u"... error, try again")
										time.sleep(1)

							if not connected:
								U.logger.log(20, u"connect error, giving up")
								tryAgain = 0
					
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
												U.logger.log(20,u"... successful: {}-{}".format(expCommands.before,expCommands.after))
												time.sleep(0.1)
												continue
											else:
												if ii < ntriesConnect-1: 
													if ret in[1,2]:	U.logger.log(20, u"... error, quit: {}-{}".format(expCommands.before,expCommands.after))
													elif ret == 3:	U.logger.log(20, "... timeout, quit: {}-{}".format(expCommands.before,expCommands.after))
													else:			U.logger.log(20, "... unexpected, quit: {}-{}".format(expCommands.before,expCommands.after))
											success = False
											break
										lastBeep = time.time()
									if time.time() - startbeep > beepTime: break
									time.sleep(1)

								if success:
									for cc in cmdOff:
										U.logger.log(20,u"sendline  cmd{}".format( cc))
										expCommands.sendline( cc )
										ret = expCommands.expect([mac,"Error","failed",pexpect.TIMEOUT], timeout=5)
										if ret == 0:
											U.logger.log(20,u"... successful: {}-{}".format(expCommands.before,expCommands.after))
											time.sleep(0.1)
										else:
											if ret in[1,2]:	U.logger.log(20, "... error: {}-{}".format(expCommands.before,expCommands.after))
											elif ret == 3:	U.logger.log(20, "... timeout: {}-{}".format(expCommands.before,expCommands.after))
											else:			U.logger.log(20, "... unknown: {}-{}".format(expCommands.before,expCommands.after))
										tryAgain = -1

								expCommands.sendline("disconnect" )
								U.logger.log(20,u"sendline disconnect ")
								ret = expCommands.expect([">","Error",pexpect.TIMEOUT], timeout=5)
								if ret == 0:
									U.logger.log(20,u"... successful: {}".format(expCommands.after))
								else:
									if ret == 1: 	U.logger.log(20, "... error: {}".format(expCommands.after))
									elif ret == 2:	U.logger.log(20, "... timeout: {}".format(expCommands.after))
									else: 			U.logger.log(20, "... unknown: {}".format(expCommands.after))
									expCommands.kill(0)
									expCommands = ""

						except Exception as e:
							U.logger.log(30,"", exc_info=True)
							time.sleep(1)
					if expCommands !="":
						try:	expCommands.sendline("quit\r" )
						except: pass
						try:	expCommands.kill(0)
						except: pass
						expCommands = ""


				if expCommands !="":
					try:	expCommands.sendline("quit\r" )
					except: pass
					try:	expCommands.kill(0)
					except: pass
	except Exception as e:
			U.logger.log(30,"", exc_info=True)

	return restart



#################################
def updateTimeAndZone(useHCI):
	global beaconsOnline
	'''
	============
	for XiaomiTimeLYWSD02 
	cmd = "gatttool -i {} -I -b {}".format(hci, MAC)
	then do expect ... 
	tt = char-read-hnd 3e

	currTime = int(tt[0:2],16) * 1 + int(tt[2:4],16) * 256 +int(tt[4:6],16) * 8*256 +int(tt[6:8],16) * 256*256
	currTS   = int(tt[8:10])
	if currTS > 127: currTS = 256 - currTS

	write back:
	correctTz = -time.timezone /3600 + time.localtime().tm_isdst 
	correctTT = int(time.time()) + 1  # +1 for delay of writing

	tt = "{:8x}".format(correctTT)
	if ts < 0:  tsh = "f{:01x}".format(16-correctTz)
	else:		tsh = "0{:01x}".format(correctTz)

	writeback = tt + tsh
	char-write-req 3e writeback
	==============
	'''
	try:	
		restart = False

		while True: 
			if not os.path.isfile(G.homeDir+"temp/beaconloop.updateTimeAndZone"): break
			f = open(G.homeDir+"temp/beaconloop.updateTimeAndZone","r")
			deviceList = f.read().strip("\n").split("\n")
			f.close()
			subprocess.call("rm {}temp/beaconloop.updateTimeAndZone".format(G.homeDir), shell=True)
			U.logger.log(20,u"updateTimeAndZone deviceList:{}".format(deviceList))

			# devices: '{u'24:DA:11:21:2B:20': "xxx"}'
			for devices1 in deviceList:
				if len(devices1) == 0: continue
				devices = json.loads(devices1)
				if len(devices) == 0: continue
				expCommands = ""
				stopHCUIDUMPlistener()
				U.killOldPgm(-1,"hcidump")
				U.killOldPgm(-1,"hcitool")
				U.killOldPgm(-1,"lescan")
				restart = True
				cmd = "sudo /bin/hciconfig {} reset".format(useHCI)
				ret = readPopen(cmd)

				#U.logger.log(20,"beepBeacon devices:{}".format(devices))
				for mac in devices:
					success = False
					U.logger.log(20,"updateTimeAndZone mac:{}".format(mac))
					if len(mac) < 10: continue
			
					tryAgain = 3
					for kk in range(2):
						tryAgain -= 1
						if tryAgain < 0: break
						if tryAgain != 2 and expCommands != "":
							try: expCommands.sendline("disconnect")	
							except: pass	

						cmd = "sudo /usr/bin/gatttool -i {} -b {} -I".format(useHCI, mac) 
						U.logger.log(20,cmd)
						expCommands = pexpect.spawn(cmd)
						ret = expCommands.expect([">","error",pexpect.TIMEOUT], timeout=10)
						if ret == 0:
							U.logger.log(20,u"... successful: {}-{}".format(expCommands.before,expCommands.after))
							connected = True
						else:
							if ii < ntriesConnect-1:
								if ret == 1:	U.logger.log(20, u"... error, giving up: {}-{}".format(expCommands.before,expCommands.after))
								elif ret == 2:	U.logger.log(20, u"... timeout, giving up: {}-{}".format(expCommands.before,expCommands.after))
								else:			U.logger.log(20, "... unexpected, giving up: {}-{}".format(expCommands.before,expCommands.after))
							expCommands.kill(0)
							time.sleep(0.1)
							continue

						time.sleep(0.1)

						try:

							connected = False
							ntriesConnect = 2
							for ii in range(ntriesConnect):
								try:
									U.logger.log(20,u"expect connect ")
									expCommands.sendline("connect ")
									ret = expCommands.expect(["Connection successful","Error", pexpect.TIMEOUT], timeout=15)
									if ret == 0:
										U.logger.log(20,u"... successful: {}".format(expCommands.after))
										connected = True
										break
									else:
										if ii < ntriesConnect-1: 
											if ret == 1:	U.logger.log(20, u"... error, try again: {}-{}".format(expCommands.before,expCommands.after))
											elif ret == 2:	U.logger.log(20, u"... timeout, try again: {}-{}".format(expCommands.before,expCommands.after))
											else:			U.logger.log(20, "... unexpected, try again: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(1)

								except Exception as e:
									U.logger.log(20,"", exc_info=True)
									if ii < ntriesConnect-1: 
										U.logger.log(20, u"... error, try again")
										time.sleep(1)

							if not connected:
								U.logger.log(20, u"connect error, giving up")
								tryAgain = 0
					
							else:
								correctTz = int(-time.timezone //3600 + time.localtime().tm_isdst)
								correctTT = int(time.time()) 

								tsh = "{:8x}".format(correctTT)
								correctTT = int(time.time()) + 1  # +1 for delay of writing
								xx = correctTT
								tsh = ""

								ex =[256*256*256,256*256,256,1]
								for ii in range(4):
									temp = xx // ex[ii]
									tsh =  "{:02x}".format(temp) + tsh
									xx  = xx - temp*ex[ii]

								if correctTz < 0:	tz = "f{:01x}".format(16-correctTz)
								else:				tz = "0{:01x}".format(correctTz)
								writeback =tsh + tz
								cmdON		= ["char-write-req 3e {}".format(writeback)]
								U.logger.log(20,"{}:   cmd:{},   timestamp:{}".format(mac, cmdON, correctTT) )
								success = False
								for ii in range(3):
										for cc in cmdON:
											U.logger.log(20,"sendline  cmd:{}".format( cc))
											expCommands.sendline( cc )
											ret = expCommands.expect([mac,"Error","failed",pexpect.TIMEOUT], timeout=5)
											if ret == 0:
												U.logger.log(20,u"... successful: {}-{}".format(expCommands.before,expCommands.after))
												success = True
												break
											else:
												if ii < ntriesConnect-1: 
													if ret in[1,2]:	U.logger.log(20, u"... error, quit: {}-{}".format(expCommands.before,expCommands.after))
													elif ret == 3:	U.logger.log(20, "... timeout, quit: {}-{}".format(expCommands.before,expCommands.after))
													else:			U.logger.log(20, "... unexpected, quit: {}-{}".format(expCommands.before,expCommands.after))
											time.sleep(1)
											success = False
										if success: break 

								expCommands.sendline("disconnect" )
								U.logger.log(20,u"sendline disconnect ")
								ret = expCommands.expect([">","Error",pexpect.TIMEOUT], timeout=5)
								if ret == 0:
									U.logger.log(20,u"... successful: {}".format(expCommands.after))
								else:
									if ret == 1: 	U.logger.log(20, "... error: {}".format(expCommands.after))
									elif ret == 2:	U.logger.log(20, "... timeout: {}".format(expCommands.after))
									else: 			U.logger.log(20, "... unknown: {}".format(expCommands.after))
									expCommands.kill(0)
									expCommands = ""

						except Exception as e:
							U.logger.log(30,"", exc_info=True)
							time.sleep(1)
						if success: break

					if expCommands !="":
						try:	expCommands.sendline("quit\r" )
						except: pass
						try:	expCommands.kill(0)
						except: pass
						expCommands = ""


				if expCommands !="":
					try:	expCommands.sendline("quit\r" )
					except: pass
					try:	expCommands.kill(0)
					except: pass


	except Exception as e:
			U.logger.log(30,"", exc_info=True)

	return restart



#################################
def getBeaconParameters(useHCI):
	global beaconsOnline

	data ={} 
	try:	
		if not os.path.isfile(G.homeDir+"temp/beaconloop.getBeaconParameters"): return False

		f = open(G.homeDir+"temp/beaconloop.getBeaconParameters","r")
		devices = f.read().strip("\n")
		f.close()

		subprocess.call("rm {}temp/beaconloop.getBeaconParameters".format(G.homeDir), shell=True)

		devices = json.loads(devices)
		U.logger.log(20,"getBeaconParameters devices:{}".format(devices))
		if len(devices) ==0: return False

		U.killOldPgm(-1,"hcidump")
		U.killOldPgm(-1,"hcitool")
		U.killOldPgm(-1,"lescan")
		time.sleep(0.2)

		cmd = "sudo /bin/hciconfig {} down;sudo /bin/hciconfig {} up".format(useHCI, useHCI)
		ret = readPopen(cmd)

		timeoutSecs = 15
		nTries = 3
		if "sensors" not in data: data["sensors"] = {}
		if "getBeaconParameters" not in data["sensors"]: data["sensors"]["getBeaconParameters"] ={}
		for mac in devices:
			if len(mac) < 10: continue
			if False and mac not in beaconsOnline:
				U.logger.log(20,u"mac: {}; skipping, not online or not in range".format(mac) )
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

				cmd = "/usr/bin/timeout -s SIGKILL {}   /usr/bin/gatttool -i {} -b {} {} --char-read --uuid={}".format(timeoutSecs, useHCI, mac, random, uuid)
				##					                   /usr/bin/gatttool -b 24:da:11:27:E4:23 --char-read --uuid=2A19 -t public / random   
				U.logger.log(20,"cmd: {}".format(cmd))
				if mac not in data["sensors"]["getBeaconParameters"]: data["sensors"]["getBeaconParameters"][mac] = {}
				for ii in range(nTries):
					ret = readPopen(cmd)
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
							except Exception as e:
								U.logger.log(30,"", exc_info=True)
					U.logger.log(20,u"try#:{}/{} ... ret: {}; bits: {}; norm:{}; value-I: {}; B: {}; C: {}; d: {};  F: {} ".format(ii+1, nTries, check, bits, norm, valueI, valueB, valueC, valueD, valueF) )
					data["sensors"]["getBeaconParameters"][mac] = {"batteryLevel":valueF}
					if valueF != -2: break
					if ii < nTries-1: time.sleep(0.2)


			except Exception as e:
				if "{}".format(e).find("Timeout") == -1:
					U.logger.log(30,"", exc_info=True)
				else:
					U.logger.log(20,"", exc_info=True)
				time.sleep(1)

			
	except Exception as e:
			U.logger.log(30,"", exc_info=True)

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

def testComplexTag(hexstring, tag, mac, macplain, macplainReverse, Maj="", Min="", tagPos="", tagString="",checkMajMin=True, calledFrom="" ):
	global knownBeaconTags, logCountTrackMac, trackMac
	try:
		subtypeOfBeacon = ""
		inputString = copy.copy(hexstring)
		if tag != ""		: tagPos 		= int(knownBeaconTags[tag].get("pos",0))
		if tagString == ""	: tagString 	= knownBeaconTags[tag].get("hexCode","").upper()
		dPos 	 = 0
		posFound = -1

		tagString2						 	= knownBeaconTags[tag].get("hexCode2","").upper()
		matchString					 		= knownBeaconTags[tag].get("match",False)

		if tagString.find("-") >-1: # 
			tagString = tagString[:-1]
		lTag = len(tagString)
		lTag2 = len(tagString2)


		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			if tag == "":
				writeTrackMac("tst-0   ","matchString:{}; tagPos:{}; lTag:{} tagString: {}; tagString2:{} ".format(matchString, tagPos, lTag, tagString, tagString2 ), mac)
			else:
				writeTrackMac("tst-0   ","matchString:{}; tagPos:{}; lTag:{}, tag:{}; tagString: {}; tagString2:{} ".format(matchString, tagPos, lTag, tag, tagString,tagString2 ), mac)

		if lTag + lTag2 > len(inputString): 
			if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("tst-L   "," reject length ", mac)
			return posFound, dPos, Maj, Min, subtypeOfBeacon


		if tagString.find("X") >-1:
			indexes = [n for n, v in enumerate(tagString) if v == 'X'] 
			inputString 	= list(inputString.upper())
			#writeTrackMac("tag-0   ","indexes:{}".format(indexes), mac)
			for ii in indexes:
				if ii+tagPos < len(inputString):
					inputString[ii+tagPos] = "X"
				else: return -1, 100, Maj, Min, ""
			inputString = ("").join(inputString)

		if tagString.find("RMAC########") >-1:
			tagString = tagString.replace("RMAC########", macplainReverse)

		elif tagString.find("MAC#########") >-1:
			tagString = tagString.replace("MAC#########", macplain)

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tst-1   ","tagString   fin: {} + {} ".format(tagString, tagString2), mac)
			writeTrackMac("tst-1   ","inputString:     {}".format(inputString), mac)

		if matchString: 
			if inputString != tagString:
				posFound = -1
				dPos = 98
				if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
					writeTrackMac("tst-M   ","reject total match".format(), mac)
			else:
				posFound 	= inputString.find(tagString)
				dPos 		= posFound - tagPos

		else:
			posFound 	= inputString.find(tagString)
			dPos 		= posFound - tagPos

		if lTag2 >0 and posFound > -1 and dPos == 0:
			if inputString.find(tagString2) == -1: posFound == -1; dPos = 99

		if len(inputString) < lTag + tagPos: posFound =-1; dPos = 100

		if tag in knownBeaconTags and checkMajMin and dPos == 0: 
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

		if  posFound > -1 and dPos == 0 and tag !="" and tag in knownBeaconTags :
			#if tag == "iBSxx":U.logger.log(20,u"{} tag:{}==\n  {},\n{} ".format(mac, tag,  tagString, hexstring))
			if "subtypeOfBeacon" in knownBeaconTags[tag] and knownBeaconTags[tag]["subtypeOfBeacon"] !={}:
				subtypeOfBeacon = knownBeaconTags[tag]["subtypeOfBeacon"]
				#if tag == "iBSxx": U.logger.log(20,u" {} posFound:{},   has subDevtype:{}, calledFrom:{}, hexstring:{}".format(mac,posFound, subtypeOfBeacon, calledFrom, hexstring))
				pos = subtypeOfBeacon["pos"]
				mask = subtypeOfBeacon["mask"]
				intHex = subtypeOfBeacon["intHex"]
				length = subtypeOfBeacon["length"]
				if len(hexstring) > pos+length:
					if intHex == "int":
						dataTAG = intFrom8(hexstring, pos)& mask
					else:
						dataTAG = hexstring[pos:pos+length]

					#if tag == "iBSxx":U.logger.log(20,u"{} has  compare:{}-{}".format(mac, hexstring[pos:pos+length], dataTAG))
					for devTypeID in subtypeOfBeacon["devTypeID"]:
						if intHex == "int":
							searchTAG = intFrom8(devTypeID,0)
						else:
							searchTAG = devTypeID
						#if tag == "iBSxx":U.logger.log(20,u"{}           to:{}-{}".format(mac, devTypeID, searchTAG))
						if dataTAG == searchTAG:
							subtypeOfBeacon = subtypeOfBeacon["devTypeID"][devTypeID]
							#if tag == "iBSxx":U.logger.log(20,u" {} has subtypeOfBeacon is :{}".format(mac, subtypeOfBeacon))
							break

		return posFound, dPos, Maj, Min, subtypeOfBeacon
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,u"Mac#:{}, tag:{}".format(mac, tag, ))
	return -1,100, Maj, Min, ""


#################################
def parsePackage(mac, hexstring, logData=False): # hexstring starts after mac#
	global bleServiceSections, parsedData

	try:
		totalLength = int(hexstring[0:2],16)
		if totalLength < 6: return {}
		parsedData = {"len": totalLength, "sections":[], "analyzed":{}}
		sectionsData = []
		analyzed = {}
		startOfSection = 0
		lenSection = 0
		if ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
				writeTrackMac("pars0   ","totalLength:{}; hexstring: {}; ".format(totalLength,  hexstring ), mac)
		for ii in range(8):
			startOfSection = startOfSection+2 + lenSection*2
			if startOfSection > totalLength*2: break
			try: lenSection  = int(hexstring[startOfSection:startOfSection+2],16)
			except: continue

			if lenSection > 0: 
				typeOfSection = hexstring[startOfSection+2:startOfSection+4]
				sectionsData.append({})
				sectionsData[-1]["len"] = lenSection
				if typeOfSection in bleServiceSections:
					sectionsData[-1]["type"] = bleServiceSections[typeOfSection]

				else: 
					sectionsData[-1]["type"] = "unknown:"+typeOfSection

				section = hexstring[startOfSection+4: startOfSection+4 + lenSection*2 -2]


				if sectionsData[-1]["type"] in ["Flags"]:
					if  logData or ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
						writeTrackMac("parsM   ","Flag: section:{}".format( section), mac)
					sectionsData[-1]["data"] = section
					analyzed["Flags"] = section

				elif sectionsData[-1]["type"] in ["Name"]:
					dd = ""
					ll = int(len(section)/2)
					for ii in range(ll):
						x = section[ii*2:ii*2+2]
						if x == "00":  dd+= "~"
						dd += hex2str(x)
					if  logData or ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
						writeTrackMac("parsM   ","Name: section:{}, dd:{}, ll:{}".format( section, dd, ll ), mac)

					sectionsData[-1]["data"] = dd
					analyzed["mfg_info"] = sectionsData[-1]["data"]
					analyzed["Name"] = sectionsData[-1]["data"]

				elif sectionsData[-1]["type"] in  ["ShortName"]:
					dd = ""
					ll = int(len(section)/2)
					for ii in range(ll):
						x = section[ii*2:ii*2+2]
						if x == "00":  dd+= "~"
						dd += hex2str(x)
					if  logData or ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
						writeTrackMac("parsM   ","ShortName: section:{}, dd:{}, ll:{}".format( section, dd, ll ), mac)

					sectionsData[-1]["data"] = dd
					analyzed["mfg_info"] = sectionsData[-1]["data"]
					analyzed["ShortName"] = sectionsData[-1]["data"]



				elif sectionsData[-1]["type"] in  ["UUID"]:
					if section[0:8] =="4C000215":
						try:
							uuidEnd = 8+2*16
							iBeacon = section[8:uuidEnd] +"-"+str(int(section[uuidEnd:uuidEnd+4],16)) +"-"+str(int(section[uuidEnd+4:uuidEnd+4+4],16))
							sectionsData[-1]["data"] = "iBeacon:"+iBeacon
							analyzed["iBeacon"] = iBeacon
						except:
							continue
					else:
						sectionsData[-1]["data"] = "Other:"+section[8:]
						analyzed["Other"] = section

				elif sectionsData[-1]["type"] in ["ServiceData"]:
					sectionsData[-1]["ServiceData"] = section
					analyzed["ServiceData"] = section
					xxx = getTLMdata(mac, section, verbose=False)
					if xxx != {}:
						analyzed["TLM"] = xxx
				else:					
					sectionsData[-1]["data"] = section
					analyzed[sectionsData[-1]["type"]] = section
				rest = hexstring[startOfSection+2 + lenSection*2:]
				if  ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
						writeTrackMac("parsT   "," startOfSection:{:2d}, typeOfSection:{},  sectionsData:{}, rest:{}".format( startOfSection, typeOfSection, sectionsData[-1], rest), mac)
		if  ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
			writeTrackMac("parsE   "," lenTotal:{}, data:{}, hexstr:{}".format( totalLength, analyzed, hexstring), mac)
		parsedData["sections"] = sectionsData
		parsedData["analyzed"] = analyzed

		return 	
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,u" hexstr:{}".format(hexstring))
	return 



#################################
def getTLMdata(mac, section, verbose = False):
	try:
		retData = {}
		tagPos = section.find("AAFE2000") # tag for TLM data 

		if tagPos == -1: 					return retData

		if  len(section) - tagPos != 32:	return retData

		startNext	= tagPos + 8

		lSec 		= 4
		VbatH 		= section[startNext:startNext+lSec]
		Vbat 		= int(VbatH,16)
		startNext  += lSec

		lSec 		= 4
		tempH 		= section[startNext:startNext+lSec]
		temp1 		= intFrom8(tempH,0)
		if temp1 > 127: temp1 -= 256
		temp2		= intFrom8(tempH,2)/256.
		temp 		= round(float(temp1) + temp2, 1)
		startNext  += lSec

		lSec 		= 8
		advCountH 	= section[startNext:startNext+lSec]
		advCount 	= int(advCountH,16)
		startNext  += lSec

		lSec 		= 8
		timeSinceH 	= section[startNext:startNext+lSec]
		timeSince 	= int(timeSinceH,16)/10.

		retData = {"batteryVoltage":Vbat, "temp":temp, "advCount":advCount, "timeSince":timeSince}
		if verbose: 
			U.logger.log(20,u" mac:{:}, Vbat:{:}={:4d}; temp:{:}={:.2f}, advCount:{:}={:10d}, timeSince:{:}={:12.1f}, hex:{:}".format(mac, VbatH, Vbat, tempH, temp, advCountH, advCount, timeSinceH, timeSince, section))

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
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

			if BLEAnalysisStart(useHCI):
				U.restartMyself(param="", reason="BLEanalysis", python3=usePython3)

			if beep(useHCI):
				U.restartMyself(param="", reason="beep", python3=usePython3)

			if updateTimeAndZone(useHCI):
				U.restartMyself(param="", reason="updateTimeAndZone", python3=usePython3)

			if getBeaconParameters(useHCI):
				U.restartMyself(param="", reason="get battery levels", python3=usePython3)


		if tt - paramCheck > 10:
			if readParams(): reasonMax = max(reasonMax, 8) # new params
			paramCheck=time.time()

		return sensCheck, paramCheck 

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return sensCheck, paramCheck 


#################################
def checkForValueInfo( tag, tagFound, mac, hexstr ):
	global knownBeaconTags
	global trackMac, logCountTrackMac
	global getMsgInfoCmds
	try:
		if mac == trackMac and logCountTrackMac >0:
			writeTrackMac("Val-0   ","tag:{}; tagFound:{}; tagin:{}; hexstr:{}".format(tag, tagFound, tag in knownBeaconTags, hexstr), mac )
		results = {}
		verbose = mac =="xxxC6:8F:F7:A5:8C:14"
		if verbose:	U.logger.log(20,u"mac:{}, tag:{}, tagFound:{}, hexstr:{}".format(mac, tag, tagFound, hexstr[12:]))
		if tag in knownBeaconTags and tagFound == "found" and "commands" in knownBeaconTags[tag]:
			for cmdName in knownBeaconTags[tag]["commands"]:
				cmdDict = knownBeaconTags[tag]["commands"][cmdName]
				if cmdDict == None: continue
				if cmdDict == "": continue
				if cmdDict == {}: continue
				if type(cmdDict) == type(""): continue
				if cmdDict.get("type","") != "msgGet": continue
				if "params" not in cmdDict: continue
				params = cmdDict["params"]
				results[cmdName] = ""
				try:
					if  verbose:
						#U.logger.log(20,u"mac:{}, tag:{}, cmd:{}, params:{}".format(mac, tag, cmdName, params))
						pass
					if len(params) > 1: 
						if mac == trackMac and logCountTrackMac >0:
							writeTrackMac(cmd+"-1   ","params:{}".format(cmdName,params), mac )
						pos	= int(params["pos"])*2
					
						if "and" in params:			andWith = int(params["and"])
						else:						andWith = 255
						if "nType" in params:		nType = params["nType"]
						else:						nType = "int"
						if "resultON" in params:	resultON = params["resultON"]
						else:						resultON = ""
						if "resultOFF" in params:	resultOFF = params["resultOFF"]
						else:				    	resultOFF = ""

						norm = 1
						try:
							if nType == "float": norm = float(params["norm"])
							else:				 norm = int(params["norm"])
						except: pass
							
						try:	length	= int(params["len"])
						except:	length  = 1
						try:	reverse	= int(params["reverse"]) == 1
						except:	reverse = False

						bHexStr = hexstr[12:]
						Bstring =  bHexStr[pos:pos+length*2]

						if reverse:
							Bstring = Bstring[2:4]+Bstring[0:2]
						if nType =="float":	results[cmdName] = float(int(Bstring,16)&andWith)/norm
						else:				results[cmdName] = (int(Bstring,16)&andWith)//norm

						if nType == "int": 		results[cmdName] = int(results[cmdName]+0.5)
						if nType == "bool": 	results[cmdName] = results[cmdName] != 0
						if nType == "float": 	results[cmdName] = float(results[cmdName])
						if nType == "string": 	results[cmdName] = resultON if results[cmdName] else resultOFF
						if nType == "bits": 	results[cmdName] = "{:08b}".format(results[cmdName])
						if verbose:  U.logger.log(20,"{}: cmdName:{:15s}, bHexStr:{} pos:{}, hex:{}, norm:{}, length:{}, andWith:{}, reverse:{}, Bstring:{}, andResult:{}, resultON:{}, resultOFF:{}, res:{}".format(mac, cmdName, bHexStr, pos, Bstring, norm, length, andWith, reverse, Bstring, int(Bstring,16)&andWith, resultON, resultOFF, results[cmdName] ) )
						if mac == trackMac and logCountTrackMac >0:
							writeTrackMac(cmd[0:3]+"-4   ", "val:{}".format(cmd[0:3],results[cmdName] ),  mac )

				except	Exception as e:
					U.logger.log(30,"", exc_info=True)
					if mac == trackMac and logCountTrackMac >0:
						U.logger.log(20,"", exc_info=True)
					results[cmdName] = ""

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return results


#################################
def checkIfTagged(mac, macplain, macplainReverse, UUID, Min, Maj, isOnlySensor, hexstr, batteryLevel, rssi, txPower):
	global trackMac, logCountTrackMac, onlyTheseMAC, knownBeaconTags, acceptNewBeaconMAC
	global beaconNew, beacon_ExistingHistory, ignoreMAC
	global acceptNewMFGNameBeacons
	global batteryLevelUUID
	global parsedData
	try:
		prio  				= -1
		dPos  				= -100
		UUID1 				= ""
		tagFound 			= "notTested"
		rejectThisMessage 	= "reject"
		mfg_info			= ""
		iBeacon				= ""
		mode				= ""
		onOff				= ""
		typeOfBeacon		= "other"
		subtypeOfBeacon		= ""
		existing 			= mac in onlyTheseMAC
		mfgTagged 			= False

		try:  parsePackage(mac, hexstr[12:], logData=False)
		except:
			return rejectThisMessage

		if "iBeacon" in parsedData["analyzed"]: iBeacon = parsedData["analyzed"]["iBeacon"]
		else:									iBeacon = ""
		if "mfg_info" in parsedData["analyzed"]:mfg_info = parsedData["analyzed"]["mfg_info"]
		else:									mfg_info = ""
		if "TLM" in parsedData["analyzed"] and "batteryVoltage" in  parsedData["analyzed"]["TLM"]:
			batteryVoltage = parsedData["analyzed"]["TLM"]["batteryVoltage"]
			temp = parsedData["analyzed"]["TLM"]["temp"]
			TLMenabled = True
		else:
			TLMenabled = ""
			batteryVoltage = 0
			temp = 20.
			
		
		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("parse   ", "parsedData {}".format(parsedData), mac)

		setEmptybeaconsThisReadCycle(mac)

		### is this a know beacon with a known tag ?
		rejectThisMessage 	= "reject"
		tagFound 			= "failed"
		tagOld				= ""
		if existing:  
			tagOld 			= onlyTheseMAC[mac].get("typeOfBeacon","")
			useOnlyIfTagged = onlyTheseMAC[mac].get("useOnlyIfTagged",0) # this is from props, device edit settings, overwrites default

			if useOnlyIfTagged == 0: 
				rejectThisMessage = "all"

			if tagOld not in ["", "other"]:
				if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
					writeTrackMac("tag-1   ", "tag:{}, useOnlyIfTagged: {}".format(tagOld, useOnlyIfTagged), mac)
				# right message format, if yes us main UUID
				if  tagOld in knownBeaconTags:
					UUID1 	= tagOld
					UUID 	= UUID1
					posFound, dPos, Maj, Min, subtypeOfBeacon = testComplexTag(hexstr[12:-2], tagOld, mac, macplain, macplainReverse, Maj, Min, calledFrom="checkIfTagged-1")
					if tagOld == "iBeacon" and iBeacon != "":
						rejectThisMessage = tagOld
						iB = iBeacon.split("-")
						Maj  = iB[1]
						Min  = iB[2]

					if posFound == -1 or abs(dPos) > knownBeaconTags[tagOld]["posDelta"]:
						tagFound = "failed"
					else: 
						tagFound = "found"
						rejectThisMessage = tagOld
						typeOfBeacon = tagOld

				else: 
					tagFound = "failed"


		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-5   ", "rejectThisMessage:{}, tagFound:{}; UUID: {}, Maj: {}, Min: {}".format(rejectThisMessage, tagFound, UUID, Maj, Min),mac)

		#if mac == "D5:BB:6F:BD:30:0E": U.logger.log(20,"{} pass1 tagFound:{}, tagOld:{}".format(mac, tagFound, tagOld) )

		## mac not in current list, check if should look for it = accept new beacons?
		# 1. not existing: accept  if match w acceptNewTagiBeacons or mfg tag match 
		# 2. if exists check for tag other than "other"

		if not existing and acceptNewMFGNameBeacons not in ["","off"]:
			## check if in tag list
			if  mfg_info.lower().find(acceptNewMFGNameBeacons.lower()) == 0: 
				rejectThisMessage = mfg_info
				mfgTagged = True

		#if mac == "E2:DD:A7:F9:89:28": U.logger.log(20,"{} testing  .. acceptNewMFGNameBeacons:{}, mfg_info:{}".format(mac, acceptNewMFGNameBeacons, mfg_info) )
		if (
			(existing and tagOld in ["", "other"]) or  # check if we find a better tag than "other"
			( not existing  and  (acceptNewTagiBeacons != "off"  or mfgTagged)   ) # if not existing try to find tag if enabled 
			):

			for testTag in knownBeaconTags:
				#if mac == "D5:BB:6F:BD:30:0E": U.logger.log(20,"{} testing  testTag:{}".format(mac, testTag) )
				if testTag in ["other", tagOld, "iBeacon"]: 		continue
				if knownBeaconTags[testTag]["pos"] == -1: 			continue
				posFound, dPos, Maj, Min, subtypeOfBeacon = testComplexTag(hexstr[12:-2], testTag, mac, macplain, macplainReverse, Maj, Min, calledFrom="checkIfTagged-2")
				if posFound == -1: 									continue
				if abs(dPos) > knownBeaconTags[testTag]["posDelta"]:continue
				#if mac == "E2:DD:A7:F9:89:28": U.logger.log(20,"{} 2 tagOld:{}, testing  testTag:{}, posFound:{}, check:{}".format(mac, tagOld, testTag, posFound, acceptNewTagiBeacons == "all" or acceptNewTagiBeacons == testTag or tagOld in ["", "other"]) )
				if acceptNewTagiBeacons == "all" or acceptNewTagiBeacons == testTag or (existing and tagOld in ["", "other"]):
					typeOfBeacon 		= testTag
					UUID 				= testTag
					UUID1 				= testTag
					tagFound 			= "found"
					rejectThisMessage 	= testTag
					if testTag == "iBeacon" and iBeacon != "":
						iB = iBeacon.split("-")
						Maj  = iB[1]
						Min  = iB[2]
					#if mac == "E2:DD:A7:F9:89:28": U.logger.log(20,"{} 3 rejectThisMessage:{}, typeOfBeacon:{}, tagFound:{}".format(mac, rejectThisMessage, typeOfBeacon, tagFound) )
					break
				if tagFound == "found": break

		if tagFound != "found" and acceptNewTagiBeacons == "all":
			UUID = "other"
			UUID1 = "other"
			tagFound = "found"
			typeOfBeacon = "other"
			rejectThisMessage = "other"
			if testTag == "iBeacon" and iBeacon != "":
				iB = iBeacon.split("-")
				Maj  = iB[1]
				Min  = iB[2]

		#if mac == "E2:DD:A7:F9:89:28": U.logger.log(20,"{} 4 rejectThisMessage:{}, typeOfBeacon:{}, tagFound:{}".format(mac, rejectThisMessage, typeOfBeacon, tagFound) )

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-6   ", "isOnlySensor:{},  batteryLevel:{} tagFound: {}, UUID: {}, rejectThisMessage: {}".format(isOnlySensor,  batteryLevel, tagFound, UUID, rejectThisMessage) ,mac)

		if mac == acceptNewBeaconMAC:
			rejectThisMessage = "new"
			if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("tag-7   ", "accept THIS spec MAC #", mac)

		if rejectThisMessage == "reject": # unknow beacon.. accept if RSSI > accept
			if mac not in onlyTheseMAC:
				if rssi > acceptNewiBeacons: 
					if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
						writeTrackMac("tag-8   ", "accept rssi > accept new  and !tagfound and not accept mfg name", mac)
					#print " new beacon :", mac, rssi, acceptNewiBeacons
					rejectThisMessage = "new"

		results = checkForValueInfo( typeOfBeacon, tagFound, mac, hexstr )
		if batteryLevel != "" or "batteryLevel" not in results: results["batteryLevel"] = batteryLevel

		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-9   ", " batteryLevel>{}<".format(results["batteryLevel"]) ,mac)

		if results["batteryLevel"] == "" and batteryVoltage !=0: 
			batteryVoltAt100 = 3000.
			batteryVoltAt0   = 2700.
			if mac in  batteryLevelUUID and batteryLevelUUID[mac].find("TLM") ==0: # format is TLM-Vol@0-Volt@100%
				levels = batteryLevelUUID[mac].split("-")
				if len(levels) == 3:
					batteryVoltAt100 = float(levels[1]) 
					batteryVoltAt0   = float(levels[2]) 
				#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,u"mac {}; 0:{};  100:{}".format(mac, batteryVoltAt0,batteryVoltAt100))
			results["batteryLevel"] = batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=batteryVoltAt100, batteryVoltAt0=batteryVoltAt0)

		#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,u"mac {}; results[]:{};  batteryLevel:{}".format(mac, results["batteryLevel"] , batteryLevel))
		fillbeaconsThisReadCycle(mac, rssi, txPower, iBeacon, mfg_info, typeOfBeacon, subtypeOfBeacon, TLMenabled, results, parsedData["analyzed"])

		if not checkMinMaxSignalAcceptMessage(mac, rssi): rejectThisMessage = "reject"

		if rejectThisMessage != "reject" and mac in beaconsThisReadCycle: fillHistory(mac)

		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-E   ", "beaconsThisReadCycle ..mfg_info: {}, rejectThisMessage:{},  iBeacon: {}, batteryLevel>{}<".format(mfg_info, rejectThisMessage, iBeacon, batteryLevel) ,mac)


	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	if rejectThisMessage == mfg_info:
		pass
		#U.logger.log(20,"{} accepted .. rejectThisMessage:{}".format(mac, rejectThisMessage) )
	#if mac == "E2:DD:A7:F9:89:28": U.logger.log(20,"{} 5 rejectThisMessage:{}, typeOfBeacon:{}, results:{}".format(mac, rejectThisMessage, typeOfBeacon, results) )
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
		txPower	 		= signedIntfrom8(str(signedIntfrom8(hexstr[-4:-2])))
		rssi			= signedIntfrom8(hexstr[-2:])
		mfgID			= hexstr[msgStart+10:msgStart+14]
		pType 			= hexstr[msgStart+14:msgStart+16]  # 02  = procimity beacon, BE  = ALT beacon nBytes  = 27
		typeOfBeacon 	= hexstr[msgStart+8:msgStart+10]  #  FF = iBeacon
		typeOfBeacon 	+= "-"+pType.upper() 
		return 	msgStart, majEnd, uuidLen, UUID, Maj, Min, rssi,txPower, mfgID, pType, typeOfBeacon
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 	"", "", "", "", "", "", "", "", "", "",  ""




#################################
def fillbeaconsThisReadCycle(mac, rssi, txPower, iBeacon, mfg_info, typeOfBeacon, subtypeOfBeacon, TLMenabled, result, analyzed):
	global beaconsThisReadCycle
	try:
		if mac not in beaconsThisReadCycle: setEmptybeaconsThisReadCycle(mac)
					
		if True:
										beaconsThisReadCycle[mac]["rssi"]			= rssi # signal
										beaconsThisReadCycle[mac]["txPower"]		= float(txPower) # transmit power
										beaconsThisReadCycle[mac]["timeSt"]			= time.time() 
										beaconsThisReadCycle[mac]["subtypeOfBeacon"]= "" # 
										beaconsThisReadCycle[mac]["analyzed"]		= analyzed
		if typeOfBeacon !="" and beaconsThisReadCycle[mac].get("typeOfBeacon","other") == "other":
										beaconsThisReadCycle[mac]["typeOfBeacon"]	= typeOfBeacon 
		if iBeacon != "": 				beaconsThisReadCycle[mac]["iBeacon"]		= iBeacon # 
		if mfg_info != "": 				beaconsThisReadCycle[mac]["mfg_info"]		= mfg_info # 
		if TLMenabled !="":				beaconsThisReadCycle[mac]["TLMenabled"]		= True
		if subtypeOfBeacon !="":		beaconsThisReadCycle[mac]["subtypeOfBeacon"]= subtypeOfBeacon
		if typeOfBeacon != "other": 	beaconsThisReadCycle[mac]["typeOfBeacon"]	= typeOfBeacon # 

		for  ii in result:
			if result[ii] != "":		beaconsThisReadCycle[mac][ii]				= result[ii]
		beaconsThisReadCycle[mac]["analyzed"]				= analyzed
	
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 


def checkIfBLEprogramIsRunning(useHCI):
	global rpiDataAcquistionMethod

	try:
		if not U.checkIfHCiUP(useHCI, verbose=False):
			U.logger.log(30,u"{} not up".format(useHCI))
			return False

		if  rpiDataAcquistionMethod.find("socket") ==0: 
			return True

		if U.pgmStillRunning("hcidump -i", verbose=False): # and U.pgmStillRunning("hcitool -i", verbose=True):
			return True
		else:
			U.logger.log(30,u"hcidump or hcitool lescan  not up")
			return False

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
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
	global acceptNewiBeacons, acceptNewBeaconMAC, acceptNewTagiBeacons, onlyTheseMAC,enableiBeacons, minSignalOff, minSignalOn, knownBeaconTags
	global myBLEmac, BLEsensorMACs
	global oldRaw,	lastRead
	global mapReasonToText
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
	global batteryLevelUUID
	global bleServiceSections
	global BLEcollectStartTime
	global BLEanalysisdataCollectionTime
	global writeDumpDataHandle
	global switchbotData
	global fastBLEReaction, output, fastBLEReactionLastAction
	global trackRawOnly 
	global acceptNewMFGNameBeacons
	global extraStates

	extraStates = ["calibrated","position","light","mode","onOffState", "mfg_info","iBeacon","batteryLevel","subtypeOfBeacon","TLMenabled","inMotion","allowsConnection","analyzed"]
	acceptNewMFGNameBeacons = ""

	trackRawOnly 			= False
	fastBLEReactionLastAction = {}
	output					= {}
	fastBLEReaction			= {}
	BLEanalysisdataCollectionTime = 25 # secs 
	deleteHistoryAfterSeconds = 600
	switchbotData 			= {}
	writeDumpDataHandle 	= ""
	BLEcollectStartTime		= -1
	sendAfterSeconds		= 60
	doRejects				= False
	lastLESCANrestart		= 0
	ListenProcessFileHandle =""
	readbuffer				= ""
	readBufferSize			= 4096*8
	rpiDataAcquistionMethod	= ""
	acceptNewTagiBeacons 	= ""
	acceptNewBeaconMAC	 	= ""
	beaconsOnline			= {}

	downCount 				= 0

	BLEsensorMACs 			= {}
	startTimeTrackMac		= -10
	trackMacText			= ""
	#						0			1		2				3			4			5				6				7			8			9
	mapReasonToText			= ["init","timer","new_beacon","fastDown","fastDown_back","beacon_is_back","delta_signal","quickSens","newParams","inMotion","","",""]
	oldRaw					= ""
	lastRead				= 0
	minSignalOff			= {}
	minSignalOn				= {}
	acceptNewiBeacons		= -999
	enableiBeacons			= "1"
	G.authentication		= "digest"
	# get params
	onlyTheseMAC			= {}
	ignoreMAC				= []
	signalDelta				= {}
	batteryLevelUUID		= {}
	fastDownList			= {}
	myBLEmac				= ""
	sensor					= G.program	 
	sendFullUUID			= False
	badMacs					= ["00:00:00:00:00:00"]

	U.killOldPgm(-1,"hcidump")
	U.killOldPgm(-1,"hcitool")
	U.killOldPgm(-1,"lescan")

	if test != "normal": readFrom = test
	else: 				 readFrom = ""

	bleServiceSections = {
		"01":"Flags",
		"02":"16BServClinc",
		"03":"16BServClcmplt",
		"04":"32BServClinc",
		"05":"32BServClcmplt",
		"06":"128BServClinc",
		"07":"128BServClcmplt",
		"08":"ShortName",
		"09":"Name",
		"0A":"TxPowerLevel",
		"10":"DeviceID",
		"12":"SlaveConnectionIntervalRange", 
		"16":"ServiceData", 
		"19":"Appearance", 
		"1A":"AdvertisingInterval",
		"1B":"DeviceAddress",
		"20":"ServiceData-32B",
		"21":"ServiceData-128B",
		"FF":"UUID"
		}
	myPID				= str(os.getpid())
	#kill old G.programs
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")
	count = U.killOldPgm(-1,"hciconfig")
	if count > 4:
		U.logger.log(50,"beaconloop exit, hciconfig, to many ghost hciconfig processes running:{}".format(count))
		U.sendRebootHTML("bluetooth_startup is DOWN  too many  ghost hciconfig processes running ",reboot=True, force=True)
		time.sleep(10)

	readParams(init=True)

	U.logger.log(30,"======= starting beaconloop v:{}".format(VERSION))
	U.echoLastAlive(G.program)

	fixOldNames()

	# getIp address 
	if U.getIPNumber() > 0:
		U.logger.log(30, " no ip number ")
		time.sleep(10)
		return

	# get history
	readbeacon_ExistingHistory()

	# try to reuse last settings, if not new bus set in parameters
	hciBeaconloopUsed, raw  = U.readJson("{}beaconloop.hci".format(G.homeDir))
	#  = {"usedHCI":useHCI, "myBLEmac": myBLEmac, "usedBus":bus}
	if hciBeaconloopUsed != {}:
		trymyBLEmac = hciBeaconloopUsed["myBLEmac"]
		thisHCI = hciBeaconloopUsed["usedHCI"]
		usedBus = hciBeaconloopUsed["usedBus"]
	else:
		trymyBLEmac = ""
		thisHCI = ""
		usedBus = ""
	if G.BeaconUseHCINo != "" and G.BeaconUseHCINo != usedBus:
		trymyBLEmac = ""
		thisHCI = ""


	## start bluetooth
	for ii in range(5):
		sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber, thisHCI=thisHCI, trymyBLEmac=trymyBLEmac)  
		if retCode == 0: break 
		time.sleep(3)
	if retCode != 0: 
		U.logger.log(30,"beaconloop exit, recode from getting BLE stack >0, after 3 tries:")
		return

 

	if rpiDataAcquistionMethod.find("hcidump") == 0:
		retCode = startHCUIDUMPlistnr(useHCI)
		if retCode != "":
			U.logger.log(30,"beaconloop exit, === error in starting HCIdump listener, exit beaconloop ===")
			return

	U.logger.log(30,"using >{}< for data read method testMode:>{}< ".format(rpiDataAcquistionMethod, readFrom!=""))
	
	loopCount				= 0
	logfileCheck			= time.time() + 10
	paramCheck				= time.time() + 10
	sensCheck 				= time.time() + 10
	checkIPConnection		= time.time()

	U.echoLastAlive(G.program)
	lastAlive				= time.time()
	G.tStart				= time.time()
	beaconsThisReadCycle	= {}
	trackMac				= ""
	bleRestartCounter 		= 0
	eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()
	##print "beaconloop", eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled
	nEmptyMessagesInARow 	 = 0
	lastMSGwithDataPlain 	= time.time()
	lastMSGwithDataPassed 	= time.time()
	maxLoopCount	 		= 6000
	restartCount	 		= 0
	logCountTrackMac 		= -10 
	nMsgs			 		= 0
	restartBLE 				= time.time()
	nMsgs					= 0
	zeroInARow 				= 0
	zeroInARowMax	 		= 6
	lastmsg    		 		= time.time() + 5
	lastmsgMaxDelta	 		= 3
	stackrestartcount		= 0
	dtinner = [0,0,0,0,0,0,0,0,0,0]

	U.logger.log(20, "starting loop")
	try:
				while True:
					loopCount += 1
					# max every 5 minutes  .. restart BLE hcidump to clear out temp files if accumulated, takes ~1 secs 
					if time.time() - restartBLE > 300 and rpiDataAcquistionMethod == "hcidumpWithRestart":
						restartBLE = time.time()
						sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber, reUse=True, thisHCI=useHCI, trymyBLEmac=myBLEmac) 
						retCode = startHCUIDUMPlistnr(useHCI)
						U.logger.log(20, "time needed to restartBLE:{:.2f}[secs]".format(time.time()- restartBLE))

					tt = time.time()
					if tt - checkIPConnection > 600: # check once per 10 minutes
						checkIPConnection = tt
						eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
			
					beaconsThisReadCycle = {}
		
					#U.logger.log(0,"beacons info: {}".format(beacon_ExistingHistory))
					timeAtLoopStart = tt

					U.echoLastAlive(G.program)

					reasonMax = 1

					if checkIfBLErestart():
						bleRestartCounter +=1
						if bleRestartCounter > 10: 
							U.restartMyself(param="", reason="bad BLE restart", python3=usePython3)
							time.sleep(1)
							sys.exit(4)

						sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber, thisHCI=useHCI, trymyBLEmac=myBLEmac) 
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
					nMsgs = 0
					while iiWhile > 0:
								startofInnerLoop = time.time()
								iiWhile -= 1
								tt = round(time.time(),2)
				
								if (reasonMax > 1 or loopCount == 1 ) and tt -G.tStart > 30 : break	# only after ~30 seconds after start....  to avoid lots of short messages in the beginning = collect all ibeacons before sending

								if tt - timeAtLoopStart	 > sendAfter: 
									break # send curl msgs after collecting for xx seconds

								if   nMsgs < 2: time.sleep(0.15)
								elif nMsgs < 5: time.sleep(0.1)
								else: 			time.sleep(0.05)
								hexstr = ""

								if rpiDataAcquistionMethod.find("hcidump" ) == 0:
											Msgs = readHCUIDUMPlistener()
											if readFrom != "":
												if len(Msgs) >0: 
													U.logger.log(20, u"TestMode: read {}".format(Msgs))
												else:
													time.sleep(5)

								elif rpiDataAcquistionMethod == "socket":
											try: 
												pkt = sock.recv(255)
												Msgs = [(stringFromPacket(pkt)).upper()]
											except Exception as e:
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

												U.logger.log(30,"", exc_info=True)
												time.sleep(1)
												U.restartMyself(param="", reason="sock.recv error", python3=usePython3)
				

								#### check new messages
								dtinner[0] = max(dtinner[0], time.time() - startofInnerLoop )

								nLast = nMsgs
								nMsgs = len(Msgs)
								oneValid = False

								if nMsgs == 0: 
									zeroInARow += 1
									#U.logger.log(20, "loopCount:{} nMsgs:{} , lastN:{}, zeroInARow:{}, max zero msgs in a row:{}".format(loopCount, nMsgs, nLast, zeroInARow, zeroInARowMax) )
									if zeroInARow > zeroInARowMax or time.time() - lastmsg > lastmsgMaxDelta: 
										#U.logger.log(20, "break loop, too many empty messages: {}, ble-UP?:{}".format(zeroInARow, checkIfBLEprogramIsRunning(useHCI)) )
										zeroInARow  = 0
										break
								else:
									zeroInARow = 0
									lastmsg    = time.time()
									#U.logger.log(20, "loopCount:{} nMsgs:{} ,".format(loopCount, nMsgs) )


								for hexstr in Msgs: 

									hexstr = fillHCIdump(hexstr)
									nCharThisMessage	= len(hexstr)


									#U.logger.log(20, "data nChar:{}, hexStr:{}".format(nCharThisMessage,hexstr[0:50]))
									# skip junk data 
									if nCharThisMessage < 16:  continue
									if nCharThisMessage > 120: continue
									#U.logger.log(20, "nMsgs:{} len:{}..  :{}".format(nMsgs, nCharThisMessage, hexstr[:30]) )
						

									dtinner[1] = max(dtinner[1], time.time() - startofInnerLoop )
									try:
										# build the return string: mac#, uuid-major-minor,txpower??,rssi
										lastMSGwithDataPlain = int(time.time())
					
										macplainReverse 	= hexstr[0:12]
										mac 				= macplainReverse[10:12]+":"+macplainReverse[8:10]+":"+macplainReverse[6:8]+":"+macplainReverse[4:6]+":"+macplainReverse[2:4]+":"+macplainReverse[0:2]
										macplain 			= mac.replace(":","")

										#if mac == "xxAC:23:3F:33:88:08":
											#U.logger.log(20, u" mac:{}, hexstr:{}".format(mac, hexstr[12:]))

										if readFrom !="":
											U.logger.log(20, u"TestMode: start: mac:{}, rest:{}".format(mac, hexstr[12:]))

										########  track mac  start / end ############
										trackMacStopIf(hexstr, mac)
										dtinner[2] = max(dtinner[2], time.time() - startofInnerLoop )



										msgStart, majEnd, uuidLen, UUID, Maj, Min, rssi, txPower, mfgID, pType, typeOfBeacon = getBasicData(hexstr)
										dtinner[3] = max(dtinner[3], time.time() - startofInnerLoop )


										if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
											writeTrackMac("basic   ", "UUID: {}, Maj: {}, Min: {}, RX :{}, TX: {}".format(UUID, Maj, Min, rssi, txPower) ,mac)

										# check if this is a sensor, will send its own msg to mac, and will return battery level if present 
										try:
											txPower, batteryLevel, UUID, Maj, Min, isOnlySensor  = doSensors( mac, macplain, macplainReverse, rssi, txPower, hexstr, UUID, Maj, Min)
										except	Exception as e:
											U.logger.log(30,"", exc_info=True)
											U.logger.log(30, " {} has exception".format(mac))
											continue
										dtinner[4] = max(dtinner[4], time.time() - startofInnerLoop )

										# cehc if only sensor, not beacon
										if isOnlySensor:
											lastMSGwithDataPassed = int(time.time())
											continue

										# check if known rejected mac
										if mac in ignoreMAC: 
											if readFrom !="":
												U.logger.log(20, u"TestMode: ignored mac:{}".format(mac))
											continue # set to ignore in plugin



										if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
											writeTrackMac("A-Sens  ", "UUID: {}, Maj: {}, Min: {}, RX :{}, TX: {}, batteryLevel:{}".format(UUID, Maj, Min, rssi, txPower, batteryLevel) ,mac)

										
										## doing this directly does not work, first have to save then test reject
										rejectMac = checkIfTagged(mac, macplain, macplainReverse, UUID, Min, Maj, isOnlySensor, hexstr, batteryLevel, rssi, txPower)
										if rejectMac == "reject": continue
										dtinner[5] = max(dtinner[5], time.time() - startofInnerLoop )

										if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
											writeTrackMac("A-tag   ", "after checkIfTagged, msg accepted, checking for new, changed signal,... ",mac)

										lastMSGwithDataPassed = int(time.time())
		
										#if mac in fastDownList: sendAfter = min(45., sendAfterSeconds)

										if time.time() - G.tStart > 31: # wee need some history first 
											#U.logger.log(50, u"time.time() - G.tStart:{}".format(time.time() - G.tStart) )
											if checkIfBeaconIsBack(mac): continue

											if checkIfDeltaSignal(mac): continue

											if checkIfinMotion(mac, rejectMac): continue

										if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
											writeTrackMac("Accpt   ", "{}".format(beaconsThisReadCycle[mac]) ,mac)

									except	Exception as e:
										U.logger.log(30,"", exc_info=True)
										continue

				
								dtinner[6] = max(dtinner[6], time.time() - startofInnerLoop )
								sensCheck, paramCheck = doLoopCheck(tt, sensCheck, paramCheck, sensor, useHCI )
								dtinner[7] = max(dtinner[7], time.time() - startofInnerLoop )

								if time.time() - G.tStart > 31: checkIfFastDownForAll() # send -999 if gone 
								dtinner[8] = max(dtinner[8], time.time() - startofInnerLoop )

					if rpiDataAcquistionMethod == "socket":
						sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
				
					if readFrom !="":
						lastMSGwithDataPlain  = time.time()
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
						if (nEmptyMessagesInARow > 3 or not checkIfBLEprogramIsRunning(useHCI)):
							cmd = "rfkill list"
							ret = readPopen(cmd)

							U.logger.log(30, u"time w/out any message .. last anydata: {}[secs]; last okdata: {}[secs]; loopCount:{}; restartCount:{}, nEmptyMessagesInARow:{}, dtinnerL:{}\n    rfkill list:{} ".format(dt1, dt2, loopCount, restartCount, nEmptyMessagesInARow, dtinner, ret))
							if stackrestartcount < 5:
								U.logger.log(20, "restarting stack  due to no messages " )
								if rpiDataAcquistionMethod == "socket":
									sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber, thisHCI=useHCI, trymyBLEmac=myBLEmac) 
									restartBLE = time.time()
									maxLoopCount = 6000
								else:
									stopHCUIDUMPlistener()
									sock, myBLEmac, retCode, useHCI = startBlueTooth(G.myPiNumber, thisHCI=useHCI, trymyBLEmac=myBLEmac, hardreset=True) 
									#restartLESCAN(useHCI, 20, force=True)
									startHCUIDUMPlistnr(useHCI)
									restartBLE = time.time()
									#U.restartMyself(param="", reason="no messages:{} in a row;  hcitool -i hcix / hcidump -i hcix  not running, ".format(nEmptyMessagesInARow), python3=usePython3)
								nEmptyMessagesInARow = 0
								stackrestartcount +=1
							else:
								maxLoopCount = 20
								restartCount +=1
								if restartCount > 0:
									U.logger.log(20, "restarting beaconloop  due to no messages " )
									time.sleep(0.5)
									U.restartMyself(param="", reason="too long a time w/o message", python3=usePython3)

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
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
