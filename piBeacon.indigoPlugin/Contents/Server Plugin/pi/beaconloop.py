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

import threading


import math
import fcntl
#import codex

sys.path.append(os.getcwd())
import	piBeaconUtils as U
import	piBeaconGlobals as G

import  pexpect
G.program = "beaconloop"
VERSION   = 9.60

if sys.version[0] == "3": usePython3 = True
else:					  usePython3 = False


try:	import codecs
except:	pass


iTrackDevTypes = {"0":"0","1":"","2":""   ,"3":"Finder-3","4":"Wallet-4",  "5":"",  "6":"Mini-6",  "7":"",  "8":"Rechargeable-8",   "9":"Glasses-9","A":"A","B":"B","C":"C","D":"D","E":"E","F":"F"}
		# first step to drive with table, not ready yet
		# [ name,#of bytes, type, factor]
shellyTagToProperty = { 
			"00":{"name":"packetId",		"bytes":1,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0,		"unit":"",		"mapVtoText":{}									},
			"01":{"name":"batteryLevel",	"bytes":1,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0,		"unit":"%",		"mapVtoText":{}									},
			"03":{"name":"hum",				"bytes":2,	"type":"int",		"typeFinal":"float,2",	"factor":0.01,	"trigValue":0.01,	"unit":"%",		"mapVtoText":{}									},
			"2E":{"name":"hum",				"bytes":1,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0.01,	"unit":"%",		"mapVtoText":{}									},
			"08":{"name":"dewpoint",		"bytes":2,	"type":"int",		"typeFinal":"float,1",	"factor":0.01,	"trigValue":0.01,	"unit":"C",		"mapVtoText":{}									},
			"06":{"name":"mass",			"bytes":2,	"type":"int",		"typeFinal":"float,2",	"factor":0.01,	"trigValue":0.01,	"unit":"Kg",	"mapVtoText":{}									},
			"07":{"name":"mass",			"bytes":2,	"type":"int",		"typeFinal":"float,1",	"factor":0.01,	"trigValue":0.01,	"unit":"lbs",	"mapVtoText":{}									}, 
			"14":{"name":"moisture",		"bytes":2,	"type":"int",		"typeFinal":"float,1",	"factor":0.01,	"trigValue":0.01,	"unit":"%",		"mapVtoText":{}									}, 
			"2F":{"name":"moisture",		"bytes":1,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0.01,	"unit":"%",		"mapVtoText":{}									},
			"02":{"name":"temp",			"bytes":3,	"type":"sint",		"typeFinal":"float,1",	"factor":0.01,	"trigValue":0.03,	"unit":"C",		"mapVtoText":{}									},
			"0D":{"name":"pm25",			"bytes":3,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0.03,	"unit":"ug/m3",	"mapVtoText":{}									},
			"0E":{"name":"pm10",			"bytes":3,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0.03,	"unit":"ug/m3",	"mapVtoText":{}									},
			"45":{"name":"temp",			"bytes":2,	"type":"sint",		"typeFinal":"float,1",	"factor":0.1,	"trigValue":0.03,	"unit":"C",		"mapVtoText":{}									},
			"03":{"name":"press",			"bytes":3,	"type":"int",		"typeFinal":"float,2",	"factor":0.01,	"trigValue":0.03,	"unit":"hPa",	"mapVtoText":{}									},
			"40":{"name":"distance ",		"bytes":2,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0.03,	"unit":"mm",	"mapVtoText":{}									},
			"41":{"name":"distance ",		"bytes":2,	"type":"int",		"typeFinal":"int",		"factor":0.1,	"trigValue":0.03,	"unit":"m",		"mapVtoText":{}									},
			"12":{"name":"CO2",				"bytes":2,	"type":"int",		"typeFinal":"float,1",	"factor":0.1,	"trigValue":0.03,	"unit":"ppm",	"mapVtoText":{}									},
			"43":{"name":"current",			"bytes":2,	"type":"int",		"typeFinal":"float,3",	"factor":0.001,	"trigValue":0.02,	"unit":"A",		"mapVtoText":{}									},
			"0C":{"name":"voltage",			"bytes":2,	"type":"int",		"typeFinal":"float,3",	"factor":0.001,	"trigValue":0.02,	"unit":"V",		"mapVtoText":{}									},
			"4A":{"name":"voltage",			"bytes":2,	"type":"int",		"typeFinal":"float,1",	"factor":0.1,	"trigValue":0.02,	"unit":"V",		"mapVtoText":{}									},
			"44":{"name":"tvoc",			"bytes":2,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0.02,	"unit":"ug/m3",	"mapVtoText":{}									},
			"44":{"name":"speed",			"bytes":2,	"type":"int",		"typeFinal":"float,2",	"factor":0.01,	"trigValue":0.02,	"unit":"m/s",	"mapVtoText":{}									},
			"05":{"name":"Illuminance",		"bytes":3,	"type":"int",		"typeFinal":"float,1",	"factor":0.001,	"trigValue":0.05,	"unit":"Lux",	"mapVtoText":{}									},
			"3F":{"name":"rotation",		"bytes":2,	"type":"sint",		"typeFinal":"int",		"factor":0.1,	"trigValue":0.02,	"unit":"D",		"mapVtoText":{}									},
			"09":{"name":"count",			"bytes":1,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0,		"unit":"",		"mapVtoText":{}									},
			"3D":{"name":"count",			"bytes":2,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0,		"unit":"",		"mapVtoText":{}									},
			"3E":{"name":"count",			"bytes":4,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0,		"unit":"",		"mapVtoText":{}									},
			"3C":{"name":"dimmer",			"bytes":2,	"type":"intLR",		"typeFinal":"int",		"factor":1,		"trigValue":0,		"unit":"",		"mapVtoText":{}									}, # need to fix
			"21":{"name":"motion",			"bytes":1,	"type":"char",		"typeFinal":"char",		"factor":1,		"trigValue":0,		"unit":"",		"mapVtoText":{"00":"None","01":"motion"}		},
			"2D":{"name":"isOpen",			"bytes":1,	"type":"char",		"typeFinal":"char",		"factor":1,		"trigValue":0,		"unit":"",		"mapVtoText":{"00":"isClosed","01":"isOpen"}	},
			"3A":{"name":"button",			"bytes":1,	"type":"char",		"typeFinal":"char",		"factor":1,		"trigValue":0,		"unit":"",		"mapVtoText":{"00":"None","01":"press","02":"double_press","03":"tripple_press","04":"long_press","05":"long_double_press","06":"long_triple_press","80":"hold_press","FE":"button_hold"}	}
		}


#################################
def tryDeltaTime(test, oneDigit = False):
	try: 
		dt = time.time() - test
		if oneDigit: dt = round(dt,1)
		return dt
	except: return - 999.

#

def hex2str(inString):
	try:
		if sys.version[0] == "3":
			return codecs.decode(inString,"hex").decode("utf-8")
		else:
			return  inString.decode("hex")
	except Exception as e:
		U.logger.log(20,"hexstring: >>{}<< can not be converted,ret 00".format(inString))
	return "00"
	
####-------------------------------------------------------------------------####
def readPopen(cmd):
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode("utf_8"), err.decode("utf_8")
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


def signedintfromhexR(string, n): # eg aabbccdd, 4
	try:
		ss = ""
		for i in range(n):
			ss += string[(n-i-1)*2:(n-i)*2]

		intNumber = int(ss,16)
		if intNumber > 2**(n*8-1)-1: intNumber -= (2**(n*8-1) +2)
	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
		return 0
	return intNumber

def intfromhexR(string, n): # eg aabbccdd, 4
	try:
		ss = ""
		for i in range(n):
			ss += string[(n-i-1)*2:(n-i)*2]

		intNumber = int(ss,16)
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
	addr = bdaddr_string.split(":")
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
	global HCIs, useHCIForBeacon

	myBLEmac = ""
	devId	 = 0
	useHCIForBeacon	 = ""
	bus 	 = ""
	sock = ""
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
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime))  )
				#cmd = "sudo rmmod btusb"
				#ret = subprocess.Popen(cmd, shell=True,stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate() # enable bluetooth
				#U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)  )
				#cmd = "sudo modprobe btusb"
				#ret = subprocess.Popen(cmd, shell=True,stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate() # enable bluetooth
				#U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)  )
				cmd = "sudo invoke-rc.d bluetooth restart"
				ret = readPopen(cmd) # enable bluetooth
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime))  )
				cmd = "sudo hciconfig {} up".format(hci)
				ret = readPopen(cmd) # enable bluetooth
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime) ) )

			elif reUse:
				cmd = "sudo hciconfig "+hci+" reset"
				ret = readPopen(cmd) # 
				U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )

			else:
				cmd = "sudo hciconfig "+hci+" reset"
				ret =readPopen(cmd)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )
				if ret[1] != "":
					time.sleep(0.2)
					ret = readPopen(cmd)
					U.logger.log(logLevelStart,"resetting {} bluetooth".format(hci))

				cmd = "hciconfig "
				ret = readPopen(cmd) # test bluetooth
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )

				cmd = "sudo hciconfig "+hci+" up"
				ret = readPopen(cmd) # enable bluetooth
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime))  )
				if ret[1] != "":
					time.sleep(0.2)
					ret = readPopen(cmd) # enable bluetooth
					U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )
					cmd = "hciconfig "
					ret = readPopen(cmd) # test bluetooth
					U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )

			if rpiDataAcquistionMethod.find("hcidump") == 0:
				cmd	 = "sudo hciconfig {} noleadv &\n sudo hciconfig {} noscan &".format(hci, hci)
				ret = readPopen(cmd)
				U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd.replace("\n",";"), ret, tryDeltaTime(startTime))  )

		time.sleep(1)

		#### selct the proper hci bus: if just one take that one, if 2, use bus="uart", if no uart use hci0, or use last one
		if not reUse: HCIs = U.whichHCI()
		if HCIs !={} and "hci" in  HCIs and HCIs["hci"] !={}:

			U.logger.log(30,"myBLEmac HCIs{}".format( HCIs))
			useHCIForBeacon,  myBLEmac, devId, bus = U.selectHCI(HCIs["hci"], G.BeaconUseHCINo,"USB", tryBLEmac=trymyBLEmac)
			U.writeFile("temp/beaconloop.hci", json.dumps({"usedHCI":useHCIForBeacon, "myBLEmac": myBLEmac, "usedBus":bus,"pgm":"beaconloop"}))
			U.writeFile("beaconloop.hci", json.dumps({"usedHCI":useHCIForBeacon, "myBLEmac": myBLEmac, "usedBus":bus,"pgm":"beaconloop"}))
			oText = ""
			for iii in range(0,5):
				hciX = "hci"+str(iii) 
				if hciX in HCIs["hci"]:
					oText += "{}-{}-{}-{},".format( hciX, HCIs["hci"][hciX]["upDown"] , HCIs["hci"][hciX]["bus"],  HCIs["hci"][hciX]["BLEmac"])
			#U.logger.log(20,"myBLEmac sending : otext:{}".format(otext))
			U.sendURL( data={"data":{"hciInfo":oText.strip(","), "hciInfo_beacons":"{}-{}-{}".format(useHCIForBeacon, bus, myBLEmac) }}, squeeze=False, wait=False )

			if myBLEmac ==  -1:
				U.logger.log(20,"myBLEmac wrong: myBLEmac:{}, HCIs:{}".format( myBLEmac, HCIs))
				return 0,  0, -1
			U.logger.log(20,"Beacon Use HCINo {};  useHCIForBeacon:{};  myBLEmac:{}; devId:{}, bus:{};  DT:{:.3f}" .format(G.BeaconUseHCINo, useHCIForBeacon, myBLEmac, devId, bus, tryDeltaTime(startTime)))
			
			if 	rpiDataAcquistionMethod.find("hcidump") == 0:
				cmd	 = "sudo hciconfig {} leadv 3 &".format(useHCIForBeacon)
				ret = readPopen(cmd)
				U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )

			OGF						= " 0x08"
			if	True:
				# setup broadcast message
				OCF					= " 0x0008"
				iBeaconPrefix		= " 1E 02 01 1A 1A FF 4C 00 02 15"
				uuid				= " 2f 23 44 54 cf 6d 4a 0f ad f2 f4 91 1b a9 ff a6"
				MAJ					= " 00 01"
				MIN					= " 00 "+"0%x"%(int(pi))
				txP					= " C5 00"
				#cmd	 = "hcitool -i "+useHCIForBeacon+" cmd" + OGF + OCF + iBeaconPrefix + uuid + MAJ + MIN + txP
				cmd	 = "hcitool -i {} cmd{}{}{}{}{}{}{} &".format(useHCIForBeacon, OGF, OCF, iBeaconPrefix, uuid,  MAJ, MIN, txP)
				ret = readPopen(cmd)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )


			if 	rpiDataAcquistionMethod .find("hcidump" ) == 0:
				restartLESCAN(useHCIForBeacon, logLevelStart, force=True )

			if	True or rpiDataAcquistionMethod == "socket":
				####################################set adv params		minInt	 maxInt		  nonconectable	 +??  <== THIS rpi to send beacons every 10 secs only 
				#											   00 40=	0x4000* 0.625 msec = 16*4*256 = 10 secs	 bytes are reverse !! 
				#											   00 10=	0x1000* 0.625 msec = 16*1*256 = 2.5 secs
				#											   00 04=	0x0400* 0.625 msec =	4*256 = 0.625 secs
				#cmd	 = "hcitool -i "+useHCIForBeacon+" cmd" + OGF + " 0x0006"	  + " 00 10"+ " 00 20" +  " 03"			   +   " 00 00 00 00 00 00 00 00 07 00"
				cmd	 = "hcitool -i {} cmd{} 0x0006 00 10 00 20 03 00 00 00 00 00 00 00 00 07 00 &".format(useHCIForBeacon, OGF)
				## maxInt= A0 00 ==	 100ms;	 40 06 == 1000ms; =0 19 = 4 =seconds  (0x30x00	==> 64*256*0.625 ms = 10.024secs  use little endian )
				ret = readPopen(cmd)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime))  )
				####################################LE Set Advertise Enable
				#cmd	 = "hcitool -i "+useHCIForBeacon+" cmd" + OGF + " 0x000a" + " 01"
				time.sleep(0.1)
				cmd	 = "hcitool -i {} cmd{} 0x000a 01 &".format(useHCIForBeacon, OGF)
				ret = readPopen(cmd)
				U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )
				time.sleep(0.1)


			ret = HCIs["ret"]
		else:
			ret =["",""]

		if ret[1] != "":	
			U.logger.log(20,"BLE start returned:\n{}error:>>{}<<".format(ret[0],ret[1]))
			U.sendURL( data={"data":{"hciInfo":"err-BLE-start"}}, squeeze=False, wait=False )

		else:
				U.logger.log(20,"BLE start returned:\n{}my BLE mac# is >>{}<<, on bus:{}".format(ret[0], myBLEmac, bus))
				if useHCIForBeacon in HCIs["hci"]:
					if HCIs["hci"][useHCIForBeacon]["upDown"] == "DOWN":
						if downCount > 1:
							U.logger.log(20,"reboot requested,{} is DOWN using hciconfig ".format(useHCIForBeacon))
							U.writeFile("temp/rebootNeeded","bluetooth_startup {} is DOWN using hciconfig FORCE".format(useHCIForBeacon))
							U.sendURL( data={"data":{"hciInfo":"err-BLE-down"}}, squeeze=False, wait=False )
							time.sleep(10)
						downCount +=1
						time.sleep(10)
						return 0,  "", -1
				else:
					U.logger.log(30," {}  not in hciconfig list".format(useHCIForBeacon))
					downCount += 1
					if downCount > 1:
						U.sendURL( data={"data":{"hciInfo":"err-BLE-channel-missing"}}, squeeze=False, wait=False )
						U.logger.log(30,"reboot requested,{} is DOWN using hciconfig ".format(useHCIForBeacon))
						U.writeFile("temp/rebootNeeded","bluetooth_startup {} is DOWN using hciconfig FORCE".format(useHCIForBeacon))
						time.sleep(10)
					downCount += 1
					time.sleep(10)
					return 0,  "", -1
					
				
		if myBLEmac == "":
			U.sendURL( data={"data":{"hciInfo":"err-BLE-start-mac-empty"}}, squeeze=False, wait=False )
			return 0, "", -1

	except Exception as e: 
		U.logger.log(30,"", exc_info=True)
		U.sendURL( data={"data":{"hciInfo":"err-BLE-start"}}, squeeze=False, wait=False )
		time.sleep(10)
		U.writeFile("temp/restartNeeded","bluetooth_startup.ERROR:{}".format(e))
		downHCI(useHCIForBeacon)
		time.sleep(0.2)
		return 0, "", -5


	U.writeFile("temp/beaconloop.hci", json.dumps({"usedHCI":useHCIForBeacon, "myBLEmac": myBLEmac, "usedBus":bus,"pgm":"beaconloop"}))
	U.writeFile("beaconloop.hci", json.dumps({"usedHCI":useHCIForBeacon, "myBLEmac": myBLEmac, "usedBus":bus,"pgm":"beaconloop"}))


	if rpiDataAcquistionMethod.find("hcidump" ) == 0:
		return "", myBLEmac, 0


	if rpiDataAcquistionMethod == "socket":
		try:
			sock = bluez.hci_open_dev(devId)
			U.logger.log(30, "ble thread started")
		except	Exception as e:
			U.logger.log(30,"error accessing bluetooth device...".format(e))
			if downCount > 2:
				U.writeFile("temp/rebootNeeded","bluetooth_startup.ERROR:{} FORCE ".format(e))
				downHCI(useHCIForBeacon)
			downCount +=1
			return 0,  "", -1
		
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
			downHCI(useHCIForBeacon)
			return 0, "", -1

	return sock, myBLEmac, 0



#################################
def restartLESCAN(hciUse, loglevel, force=False):
	global rpiDataAcquistionMethod
	global lastLESCANrestart
	try:
		if rpiDataAcquistionMethod == "socket": return 
		if tryDeltaTime(lastLESCANrestart) > 5 or force:
			tt = time.time()
			lastLESCANrestart = tt
			#cmd	 = "sudo hciconfig {} reset".format(hciUse,G.homeDir)
			#ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE).communicate()
			#U.logger.log(20,"cmd:{} .. ret:{}...  startuptime: dT:{:.3f}".format(cmd, ret, tryDeltaTime( tt) )
			#U.killOldPgm(-1,"lescan") # will kill the launching sudo parent process, lescan still running
			#cmd = "sudo hciconfig {} reset".format(hciUse)
			#U.logger.log(20,cmd) 
			#ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE).communicate()
			# --privacy and -- duplicates does not work on some RPI / USB devices
			U.killOldPgm(-1,"hcitool") # will kill the launching sudo parent process, lescan still running
			cmd	 = "sudo hcitool -i {} lescan --duplicates  > /dev/null 2>&1 &".format(hciUse,G.homeDir)
			#cmd	 = "sudo hcitool -i {} lescan --privacy --passive --discovery=l  > /dev/null 2>&1 &".format(hciUse,G.homeDir)
			#cmd	 = "sudo hcitool -i {} lescan --passive --discovery=l  > /dev/null 2>&1 &".format(hciUse,G.homeDir)
			#cmd	 = "sudo hcitool -i {} lescan > /dev/null 2>&1 &".format(hciUse,G.homeDir)
			ret = readPopen(cmd)
			U.logger.log(loglevel,"cmd:{} .. ret:{}...  dT:{:.3f}".format(cmd, ret, tryDeltaTime(tt)) )
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return


#################################
def downHCI(hciUse):
	try:
		subprocess.Popen("sudo hciconfig {} down &".format(hciUse),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE) # enable bluetooth
		time.sleep(0.2)
		subprocess.Popen("sudo service bluetooth restart &",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(0.2)
		subprocess.Popen("sudo service dbus restart &",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(0.2)
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return



#################################
def startHCUIDUMPlistnr(hciUse):
	global myBLEmac
	global ListenProcessFileHandle
	global readFrom

	retMSG = ""
	try:
		if readFrom != "": return ""
		if ListenProcessFileHandle != "":
			stopHCUIDUMPlistener()

		for ii in range(3):
			cmd = "sudo hcidump -i {} --raw".format(hciUse)
			U.logger.log(20,"starting hcidump w cmd {}".format(cmd))
			ListenProcessFileHandle = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			pid = ListenProcessFileHandle.pid
			msg = "{}".format(ListenProcessFileHandle.stderr)
			if msg.find("open file") == -1 and msg.find("io.BufferedReader") == -1:	# try this again
				U.logger.log(20,"hci#: {}; error connecting {}".format(hci, msg) )
				time.sleep(5)
				retMSG = "error {}".format(msg)
				continue  
	
			time.sleep(0.5)
			if not U.pgmStillRunning("hcidump -i", notPresent="sudo", verbose=True):
				U.logger.log(20,"hcidump not running ")
				retMSG = "error hcidump not running "
				U.killOldPgm(-1,"hcidump")
				time.sleep(5)
				continue

			retMSG = ""
			# set the O_NONBLOCK flag of ListenProcessFileHandle.stdout file descriptor:
			flags = fcntl.fcntl(ListenProcessFileHandle.stdout, fcntl.F_GETFL)  # get current p.stdout flags
			fcntl.fcntl(ListenProcessFileHandle.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
			time.sleep(0.1)
			U.logger.log(20,"starting hcidump succeeded, pid = {}".format(pid))
			return  retMSG
	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
	return  retMSG

#################################
def stopHCUIDUMPlistener():
	global readFrom
	global ListenProcessFileHandle
	if readFrom =="": return 
	try:
		U.logger.log(20, "stopping hcidump --raw  and hcitool -i xxx lescan procs and handles")
		U.killOldPgm(-1,"hcidump")
		U.killOldPgm(-1,"hcitool")
		U.killOldPgm(-1,"lescan")
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

	if readFrom != "": # read from file
		messages = []
		try:
			if os.path.isfile(readFrom):
				f = openEncoding(readFrom,"r")
				messages = f.read()
				f.close()
				subprocess.call("rm {}".format(readFrom), shell=True)
				if len(messages) > 5:
					messages = [messages.strip("\n")]
				
		except	Exception as e:
			U.logger.log(20,"", exc_info=True)
			messages = []

		if len(messages) > 0: 
			U.logger.log(20, "TestMode: read {}".format(Msgs))
		else:
			time.sleep(5)
		return messages

	### normal read 
	try:
		lines = (os.read(ListenProcessFileHandle.stdout.fileno(),readBufferSize)).decode("utf8") 
		#U.logger.log(20, "{}".format(lines))
		if len(lines) == 0: return []
		messages = combineLines(lines)
		#U.logger.log(20, "readHCUIDUMPlistener lines:\n{}".format(lines))
		#U.logger.log(20, "readHCUIDUMPlistener messages\n{}".format(json.dumps(messages).replace(",","\n")))
		return messages
	except	Exception as e:
		if "{}".format(e).find("[Errno 35]") > -1:	 # "Errno 35" is the normal response if no data, if other error stop and restart
			pass
			#U.logger.log(20, "Errno 35")
		if "{}".format(e).find("[Errno 1]") > -1:	 
			pass
			#U.logger.log(20, "Errno 1")
		if "{}".format(e).find("temporarily") > -1:
			pass
			#U.logger.log(20, "Errno 11")
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
		MSGs = []
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
			nn += 1
			if len(line) < 40 and nn < ll: continue
			MSGs.append(line) 
		if len(MSGs) == 0: return []

		if len(MSGs[-1]) < 40:
			readbuffer = MSGs[-1]
			#U.logger.log(20, "readHCUIDUMPlistener leftover>{}<, >{}<".format(readbuffer,MSGs[-1] ))
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
	global onlyTheseMAC,enableiBeacons, BLEsensorMACs, minSignalOff, minSignalOn, knownBeaconTags
	global acceptNewiBeacons, acceptNewBeaconMAC, acceptNewTagiBeacons, acceptNewMFGNameBeacons
	global oldRaw, lastRead
	global rpiDataAcquistionMethod
	global batteryLevelUUID
	global fastBLEReaction, output
	global ignoreBeaconsIfRssiLessThan

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
			if "rebootSeconds"					in inp:	 rebootSeconds =			int(inp["rebootSeconds"])
			if "acceptNewiBeacons"				in inp:	 acceptNewiBeacons =		int(inp["acceptNewiBeacons"])
			if "acceptNewTagiBeacons"			in inp:	 acceptNewTagiBeacons =		(inp["acceptNewTagiBeacons"])
			if "acceptNewBeaconMAC"				in inp:	 acceptNewBeaconMAC =		(inp["acceptNewBeaconMAC"])
			if "acceptNewMFGNameBeacons"		in inp:	 acceptNewMFGNameBeacons =	(inp["acceptNewMFGNameBeacons"])
			if "ignoreBeaconsIfRssiLessThan"	in inp:	 ignoreBeaconsIfRssiLessThan =	(inp["ignoreBeaconsIfRssiLessThan"])


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
						#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,"mac {} passed 1".format(mac))
						if sensors[sensor][devId].get("isBLESensorDevice",False):
							#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,"mac {} passed 2".format(mac))
							if mac not in BLEsensorMACs: 
								BLEsensorMACs[mac] = {}
								#U.logger.log(20,"init mac for sensor:{}".format(mac))

							BLEsensorMACs[mac]["sensor"] 						= sensor 

							BLEsensorMACs[mac]["devId"] 						= devId
							try:	BLEsensorMACs[mac]["offsetPress"]   		= float(sensD["offsetPress"])
							except: BLEsensorMACs[mac]["offsetPress"]			= 0.
							try:	BLEsensorMACs[mac]["offsetHum"]   			= float(sensD["offsetHum"])
							except: BLEsensorMACs[mac]["offsetHum"]				= 0.
							try:	BLEsensorMACs[mac]["offsetTemp"]   			= float(sensD["offsetTemp"])
							except: BLEsensorMACs[mac]["offsetTemp"]			= 0.
							try:	BLEsensorMACs[mac]["multTemp"] 				= float(sensD["multTemp"])
							except: BLEsensorMACs[mac]["multTemp"] 				= 1.
							try:	BLEsensorMACs[mac]["updateIndigoTiming"] 	= float(sensD["updateIndigoTiming"])
							except: BLEsensorMACs[mac]["updateIndigoTiming"] 	= 20.
							try:	BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"]	= float(sensD["updateIndigoDeltaAccelVector"])
							except: BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"] = 30. # % total abs of vector change
							try:	BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"] = float(sensD["updateIndigoDeltaMaxXYZ"])
							except: BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"] = 30. # N/s*s *1000 
							try:	BLEsensorMACs[mac]["updateIndigoDeltaTemp"] = float(sensD["updateIndigoDeltaTemp"])
							except: BLEsensorMACs[mac]["updateIndigoDeltaTemp"] = 1 # =1C 
							try:	BLEsensorMACs[mac]["minSendDelta"] 			= float(sensD["minSendDelta"])
							except: BLEsensorMACs[mac]["minSendDelta"] 			= 4 #  seconds betwen updates
							try:	BLEsensorMACs[mac]["numberOfMeasurementToAverage"] 			= int(sensD["numberOfMeasurementToAverage"])
							except: BLEsensorMACs[mac]["numberOfMeasurementToAverage"] 			= 4 #  number of averages

							try:	
									xx = int(sensD["numberOfMeasurementToAverage"])
									if "numberOfMeasurementToAverage" in BLEsensorMACs[mac]: 
										if BLEsensorMACs[mac]["numberOfMeasurementToAverage"] != xx:
											BLEsensorMACs[mac]["nMessages"] = 0
							except: 
									xx = 4 #  number of averages
							BLEsensorMACs[mac]["numberOfMeasurementToAverage"] = xx

							if "accelerationTotal" not in BLEsensorMACs[mac]:
								#U.logger.log(20,"init values for sensor:{}".format(mac))
								BLEsensorMACs[mac]["batteryVoltage"]				= 0.
								BLEsensorMACs[mac]["batteryLevel"]					= ""
								BLEsensorMACs[mac]["accelerationTotal"]				= 0
								BLEsensorMACs[mac]["accelerationX"]				 	= 0
								BLEsensorMACs[mac]["accelerationY"]				 	= 0
								BLEsensorMACs[mac]["accelerationZ"]				 	= 0
								BLEsensorMACs[mac]["light"]				 			= -1
								BLEsensorMACs[mac]["lastUpdate"]				 	= tryDeltaTime( 50)
								BLEsensorMACs[mac]["lastUpdate1"]				 	= 0
								BLEsensorMACs[mac]["lastUpdate2"]				 	= 0
								BLEsensorMACs[mac]["lastUpdate3"]				 	= 0
								BLEsensorMACs[mac]["SOS"]				 			= False
								BLEsensorMACs[mac]["hum"]				 			= -100
								BLEsensorMACs[mac]["Formaldehyde"]				 	= -100
								BLEsensorMACs[mac]["temp"]				 			= -100.
								BLEsensorMACs[mac]["tempAve"]				 		=[-100,-100,-100]
								BLEsensorMACs[mac]["humAve"]				 		=[-100,-100,-100]
								BLEsensorMACs[mac]["hum"]				 			= -100
								BLEsensorMACs[mac]["Illuminance"]					= -100
								BLEsensorMACs[mac]["AmbientTemperature"] 			= -100
								BLEsensorMACs[mac]["t1"]		 					= 0
								BLEsensorMACs[mac]["t2"]		 					= 0
								BLEsensorMACs[mac]["t3"]		 					= 0
								BLEsensorMACs[mac]["modelId"]		 				= ""
								BLEsensorMACs[mac]["onOff"]		 					= False
								BLEsensorMACs[mac]["onOff1"]		 				= False
								BLEsensorMACs[mac]["onOff2"]		 				= False
								BLEsensorMACs[mac]["onOff3"]		 				= False
								BLEsensorMACs[mac]["onOff4"] 						= False
								BLEsensorMACs[mac]["onOff5"] 						= False
								BLEsensorMACs[mac]["onOff6"] 						= False
								BLEsensorMACs[mac]["onOffR1"] 						= -999
								BLEsensorMACs[mac]["onOffR2"] 						= -999
								BLEsensorMACs[mac]["onOffR3"] 						= -999
								BLEsensorMACs[mac]["mfg_info"] 						= ""
								BLEsensorMACs[mac]["trigx"] 						= ""
								BLEsensorMACs[mac]["alive"] 						= False
								BLEsensorMACs[mac]["counter"] 						= "-1"
								BLEsensorMACs[mac]["batteryVoltage"] 	 	 		= -1
								BLEsensorMACs[mac]["chipTemperature"] 	 	 		= -1
								BLEsensorMACs[mac]["secsSinceStart"] 	 	 		= -1
								BLEsensorMACs[mac]["nMessages"] 	 	 			= 0
								BLEsensorMACs[mac]["lastMotion"]   					= -1
								BLEsensorMACs[mac]["motion"]   						= False
								BLEsensorMACs[mac]["motionDuration"]   				= -1
								BLEsensorMACs[mac]["secsSinceLastM"]   				= -1
								BLEsensorMACs[mac]["batteryLevel"]  				= ""
								BLEsensorMACs[mac]["closed"]  						= -1
								BLEsensorMACs[mac]["shortOpen"]  					= -1
								BLEsensorMACs[mac]["longOpen"]  					= -1
								BLEsensorMACs[mac]["pressCounter"]  				= -1
								BLEsensorMACs[mac]["marker"]  						= ""
								BLEsensorMACs[mac]["txPower"]  						= ""


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
		xx = json.loads(f.read().strip("\n"))
		f.close()
		knownBeaconTags = xx["input"]
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
			beaconsThisReadCycle[mac]={"typeOfBeacon":"", "txPower":0, "rssi":0, "timeSt":0,"batteryLevel":"","mfg_info":"","mode":"","onOffState":"", "iBeacon":"","trigger":0,"TLMenabled":"","inMotion":"","calibrated":"","position":"","light":"","allowsConnection":""}
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
	if tryDeltaTime(lastWriteHistory ) < 30: return
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
				del beacon_ExistingHistory[mac]["trigger"][0]

		ll = len(beacon_ExistingHistory[mac]["rssi"])
		for kk in range(ll):
			if len(beacon_ExistingHistory[mac]["rssi"]) > 1:
				if tryDeltaTime(beacon_ExistingHistory[mac]["timeSt"][0]) > deleteHistoryAfterSeconds:
					del beacon_ExistingHistory[mac]["rssi"][0]
					del beacon_ExistingHistory[mac]["timeSt"][0]
					del beacon_ExistingHistory[mac]["trigger"][0]
				else:
					break
	return 

#################################
def emptyHistory(mac):
	global	beacon_ExistingHistory
	try:
		if  mac in beacon_ExistingHistory:
			beacon_ExistingHistory[mac]["rssi"]		= []
			beacon_ExistingHistory[mac]["timeSt"]	= []
			beacon_ExistingHistory[mac]["trigger"]	= []
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
		beacon_ExistingHistory[mac]["trigger"]		= []
		beacon_ExistingHistory[mac]["txPower"]		= ""
		beacon_ExistingHistory[mac]["count"]		= 1

		#U.logger.log(30,"mac:{}; beacon_ExistingHistory:{}".format(mac, beacon_ExistingHistory[mac]))

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
		beacon_ExistingHistory[mac]["trigger"].append(beaconsThisReadCycle[mac]["trigger"])
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
		#U.logger.log(20,"mac {} beaconsThisReadCycle{}".format(mac,beaconsThisReadCycle[mac] ))
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
				if tryDeltaTime(beacon_ExistingHistory[mac]["timeSt"][-1]) < 60: on = True

		if not on and  mac in minSignalOn   and rssi < minSignalOn[mac]:	return False
		if     on and  mac in minSignalOff  and rssi < minSignalOff[mac]:	return False
			
		return True

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

		
	
#################################
def composeMSG(timeAtLoopStart):
	global collectMsgs, loopMaxCallBLE
	global myBLEmac, mapReasonToText, downCount, beaconsOnline
	global beaconsThisReadCycle, beacon_ExistingHistory
	global reasonMax
	global onlyTheseMAC
	global trackMac, logCountTrackMac, beaconLastMessageTS
	global dataFromSensors, waitforcheckIfDelaySend
	global messageStats, clearmessageStats

	try:
		nMessages = 0
		if myBLEmac == "00:00:00:00:00:00":
			time.sleep(2)
			U.restartMyself(param="", reason="bad BLE  =00..00", python3=usePython3)

		data = []
		for mac in beaconsThisReadCycle:
			verbose = mac == "xE4:7E:5F:23:82:1C"
			if verbose: U.logger.log(20," mac:{}, in use:{},  in  beacon_ExistingHistory:{}".format(mac, mac in onlyTheseMAC ,mac in beacon_ExistingHistory))
			if mac not in beacon_ExistingHistory: continue
			if beacon_ExistingHistory[mac]["fastDown"] : continue
			if len(beacon_ExistingHistory[mac]["rssi"]) == 0: continue
			if tryDeltaTime(beacon_ExistingHistory[mac]["timeSt"][-1]) > 55: continue # do not resend old data
			try:
				if beacon_ExistingHistory[mac]["count"] != 0:

					try: 	avePower = int(beacon_ExistingHistory[mac]["txPower"]) #  /max(1,beacon_ExistingHistory[mac]["count"]-1)
					except: avePower = -60
					if verbose: U.logger.log(20, "mac:{}, avePower:{},  beacon_ExistingHistory txp:{}".format(mac, avePower, beacon_ExistingHistory[mac]["txPower"]))

					#avePower	=int(beacon_ExistingHistory[mac]["txPower"]   /max(1,beacon_ExistingHistory[mac]["count"]))
					if False and mac not in onlyTheseMAC:
						U.logger.log(20," mac:{}, not in use,  sending".format(mac))

					if beacon_ExistingHistory[mac]["fastDown"]:	aveSignal = -999 
					else:											aveSignal = int(sum(beacon_ExistingHistory[mac]["rssi"]) /max(1,len(beacon_ExistingHistory[mac]["rssi"])))
					if avePower > -200:								beaconsOnline[mac] = int(time.time())
					beacon_ExistingHistory[mac]["trigger"][-1] = max(1, beacon_ExistingHistory[mac]["trigger"][-1] )
					r  = min(8,beacon_ExistingHistory[mac]["trigger"][-1])
					rr = mapReasonToText[r]
					newData = {"mac": mac,
						"trigger": rr, 
						"rssi": aveSignal, 
						"txPower": avePower, 
						"lastMessageReceived":round(beaconLastMessageTS.get(mac,0),1),
						"count": beacon_ExistingHistory[mac]["count"]-1,
						"typeOfBeacon": beacon_ExistingHistory[mac]["typeOfBeacon"]
						}
					for xx in extraStates:
						if xx in beacon_ExistingHistory[mac] and beacon_ExistingHistory[mac][xx] !="": newData[xx]	= beacon_ExistingHistory[mac][xx]
					if aveSignal > -200: setBeaconLastMsgSendTS(mac)
					downCount = 0
					data.append(newData)
					if verbose: U.logger.log(20,"mac:{}  data:{} ".format(mac, data))
					if verbose: U.logger.log(20,"mac:{}  exH :{} ".format(mac, beacon_ExistingHistory[mac]))

					if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
						writeTrackMac("MSG===  ","data:{}".format(newData), beacon)
					beacon_ExistingHistory[mac]["count"] = 1
					beacon_ExistingHistory[mac]["lastMessageSend"] = time.time()
			except	Exception as e:
				U.logger.log(30,"", exc_info=True)
				U.logger.log(30, " error composing mac:{}, beaconsThisReadCycle \n{}".format(mac, beaconsThisReadCycle[mac]))

		nMessages = len(data)
		if nMessages >1: downCount = 0
		#U.logger.log(20," msending data:{}, sensor:{}".format(nMessages, len(dataFromSensors)))

		for ii in range(messageStats["max"]):
			messageStats["numberOfMessagesperRead"][ii] /= (max(1., messageStats["countTotal"])/100.)
			messageStats["numberOfMessagesperRead"][ii] = int(messageStats["numberOfMessagesperRead"][ii])

		if dataFromSensors != {}:
			if waitforcheckIfDelaySend: time.sleep(0.05)
			U.sendURL({"sensors":dataFromSensors, "msgs":data,"stats":{"nMsgDistribution":messageStats["numberOfMessagesperRead"], "total":messageStats["countTotal"]},"pi":str(G.myPiNumber),"piMAC":myBLEmac,"secsCol":int(tryDeltaTime(timeAtLoopStart)),"trigger":mapReasonToText[reasonMax]})
			dataFromSensors = {}
		else:
			U.sendURL({"msgs":data,"stats":{"nMsgDistribution":messageStats["numberOfMessagesperRead"], "total":messageStats["countTotal"]},"pi":str(G.myPiNumber),"piMAC":myBLEmac,"secsCol":int(tryDeltaTime(timeAtLoopStart)),"trigger":mapReasonToText[reasonMax]})
		messageStats 			= {"numberOfMessagesperRead":copy.copy(clearmessageStats),"countTotal":0}
		messageStats["max"]		= len(messageStats["numberOfMessagesperRead"])
		#U.logger.log(20, "beacons collected:{}".format(len(data)))

		# save active iBeacons for getbeaconparameters() process
		copyBE = copy.copy(beaconsOnline)
		for be in copyBE:
			if tryDeltaTime(copyBE[be]) > 90:
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
	global extraStates, beaconLastMessageTS

	try:
		try: 	avePower = int(beacon_ExistingHistory[mac]["txPower"]) #  /max(1,beacon_ExistingHistory[mac]["count"]-1)
		except: avePower = -60
		if beacon_ExistingHistory[mac]["fastDown"]:	aveSignal = -999 
		else:										aveSignal = int(beacon_ExistingHistory[mac]["rssi"][-1])
		if avePower > -200:
			beaconsOnline[mac] = int(time.time())
		beacon_ExistingHistory[mac]["trigger"][-1] = max(1, beacon_ExistingHistory[mac]["trigger"][-1] )
		r  = min(10,beacon_ExistingHistory[mac]["trigger"][-1])
		rr = mapReasonToText[r]
		data = {"mac": mac,
			"trigger": rr, 
			"rssi": aveSignal, 
			"txPower": avePower, 
			"lastMessageReceived":beaconLastMessageTS.get(mac,0),
			"count": max(1,beacon_ExistingHistory[mac]["count"]-1),
			"typeOfBeacon": beacon_ExistingHistory[mac]["typeOfBeacon"]
			}
		for xx in extraStates: 
			if beacon_ExistingHistory[mac].get(xx,"") != "": data[xx]	= beacon_ExistingHistory[mac][xx]
		if aveSignal > -200: setBeaconLastMsgSendTS(mac)

		beacon_ExistingHistory[mac]["lastMessageSend"] = time.time()
		U.sendURL({"msgs":[data],"pi":str(G.myPiNumber),"piMAC":myBLEmac,"secsCol":1,"trigger":rr})
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
		if mac not in beacon_ExistingHistory: 			return False
		if mac not in beaconsThisReadCycle: 			return False
		if tag not in knownBeaconTags:					return False
		if beacon_ExistingHistory[mac]["count"] <1:		return False # need at least 1 messages

		if "inMotion" not in beaconsThisReadCycle[mac] or "inMotion" not in beacon_ExistingHistory[mac]:
														return False

		if beaconsThisReadCycle[mac]["inMotion"] == "": return False

		if "lastMessageSend" not in beacon_ExistingHistory[mac]:
														return False
		#U.logger.log(20,"mac:{} pasesd-1".format(mac))

		if tryDeltaTime(beacon_ExistingHistory[mac]["lastMessageSend"]) < 1.1: 
														return False
		#U.logger.log(20,"mac:{} passed-2 beaconsThisReadCycle:{} ".format(mac, beaconsThisReadCycle[mac]))


		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("motion? ", " beaconsThisReadCycle[inMotion]:{}".format(beaconsThisReadCycle[mac]["inMotion"]),mac)

		if (
			( beaconsThisReadCycle[mac]["inMotion"] or beaconsThisReadCycle[mac]["inMotion"] != beacon_ExistingHistory[mac]["inMotion"] ) or 
			( "position" in beacon_ExistingHistory[mac] and "position" in beaconsThisReadCycle[mac] and beaconsThisReadCycle[mac]["position"] != beacon_ExistingHistory[mac]["position"])
			) :
			beacon_ExistingHistory[mac]["trigger"][-1] = 9 
			beacon_ExistingHistory[mac]["inMotion"] = beaconsThisReadCycle[mac]["inMotion"]
			if "position" in beaconsThisReadCycle[mac]:
				beacon_ExistingHistory[mac]["position"] = beaconsThisReadCycle[mac]["position"]
			composeMSGForThisMacOnly(mac)	
			U.logger.log(20,"mac:{} detected move/stop to pos:{}, inMotion:{}".format(mac, beacon_ExistingHistory[mac]["position"], beacon_ExistingHistory[mac]["inMotion"]))
			return True

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,"mac:{}\nbeaconsThisReadCycle:{}".format(mac, beaconsThisReadCycle ))

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
			beacon_ExistingHistory[mac]["trigger"][-1] = 7
			composeMSGForThisMacOnly(mac)	
			return True

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,"mac:{}\nbeaconsThisReadCycle:{}".format(mac, beaconsThisReadCycle ))

	return False


#################################
def checkIfFastDownForAll(iWhile, nMsgs, dtSend, lastMSGwithGoodData):
	global fastDownList, beacon_ExistingHistory, trackMac, logCountTrackMac
	global beaconsThisReadCycle
	global reasonMax 
	global trackMacNumber

	try:
	## ----------  check if this is a fast down device
		tt = time.time()
		for mac in fastDownList:  

			if mac not in beacon_ExistingHistory: 												continue # not in history never had an UP signal is already gone
			if len(beacon_ExistingHistory[mac]["timeSt"]) == 0: 									continue #  have not received anything this period, give it a bit more time
			if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("FstDA-c ", "checking if fastDown, dt:{:.2f}, Nrecs:{:}, iwhile:{:}, nMSGs:{:}, DT Bf Send:{:.1f},lastTimew data:{:.1f}".format(tt- beacon_ExistingHistory[mac]["timeSt"][-1], len(beacon_ExistingHistory[mac]["timeSt"]), iWhile, nMsgs, dtSend, time.time()-lastMSGwithGoodData), mac)

			if tt - beacon_ExistingHistory[mac]["timeSt"][-1] < fastDownList[mac]["seconds"]:	continue #  have not received anything this period, give it a bit more time
			if beacon_ExistingHistory[mac]["fastDown"]: 											continue # already fast down send

			if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("FstDA-Y ", "set to fastDown Active , dt:{:.2f}, Nrecs:{:}, iwhile:{:}, nMSGs:{:}, DT Bf Send:{:.1f} ".format(tt- beacon_ExistingHistory[mac]["timeSt"][-1], len(beacon_ExistingHistory[mac]["timeSt"]), iWhile, nMsgs, dtSend ), mac)
			if mac == trackMacNumber:
					U.logger.log(20, "{} =====mac:{:} fastdown =========\n".format(datetime.datetime.now().strftime("%H:%M:%S.%f")[:-5], mac))
	
			beacon_ExistingHistory[mac]["trigger"][-1] = 3 
			beacon_ExistingHistory[mac]["fastDown"]	= True
			composeMSGForThisMacOnly(mac)	
			emptyHistory(mac)

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,"mac {}:  beacon_ExistingHistory={}".format(mac, beacon_ExistingHistory[mac]))

	return

################################, check if signal strength is acceptable for fastdown 
def checkIfBeaconIsBack(mac):
	global trackMac, logCountTrackMac, findMAC
	global beacon_ExistingHistory 
	global trackMacNumber
	global sendAfterSecsOfLastMsg
	global beaconLastMessageTS, beaconLastMessageSendTS

	try:
		#U.logger.log(20,"mac{} checkIfBeaconIsBack trackMac:{}  logCountTrackMac:{}".format(mac, trackMac, logCountTrackMac))
		if  ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
			U.logger.log(20, "mac:{} New?  checking if Beacon is back " .format(mac))
		if mac in findMAC: U.logger.log(20,"mac{} checkIfBeaconIsBack start".format(mac))

		if  mac not in beacon_ExistingHistory: return False

		if  len(beacon_ExistingHistory[mac]["timeSt"]) == 0 or mac not in beaconLastMessageTS:
			if ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
				U.logger.log(30,"mac{} checkIfBeaconIsBack empty history".format(mac))
			if mac in findMAC: U.logger.log(20,"mac{} checkIfBeaconIsBack empty history".format(mac))
			return False

		if not beacon_ExistingHistory[mac]["fastDown"]:

			if mac in beaconLastMessageSendTS and tryDeltaTime(beaconLastMessageSendTS[mac]) < sendAfterSecsOfLastMsg:
				if  ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
					U.logger.log(20, "mac:{} ==> no DT:{}  send " .format(mac, tryDeltaTime(beaconLastMessageSendTS[mac])))
				return False

		if   ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
			U.logger.log(20, "mac:{} first test dt: {} , FD:{}".format(mac, tryDeltaTime(beaconLastMessageTS[mac]), beacon_ExistingHistory[mac]["fastDown"]) )

		nTimeStamp = len(beacon_ExistingHistory[mac]["timeSt"])
		if ( mac == trackMacNumber):
					U.logger.log(20, "mac:{} fastdown back test fd:{}?  dt-1:{:.1f}, DT-2:{:.1f} nHist:{}, count:{}, tests:{}, {}, {} ".format(
							mac, 
							beacon_ExistingHistory[mac]["fastDown"], 
							tryDeltaTime(beacon_ExistingHistory[mac]["timeSt"][-1]),
							tryDeltaTime(beacon_ExistingHistory[mac]["timeSt"][-min(nTimeStamp,2)]),
							nTimeStamp, 
							beacon_ExistingHistory[mac]["count"],
							beacon_ExistingHistory[mac]["count"] == 1, 
							nTimeStamp < 2 , 
							tryDeltaTime(beacon_ExistingHistory[mac]["timeSt"][- min(nTimeStamp,2)]) > sendAfterSecsOfLastMsg, 
						) 
					)
		if 	(	
				beacon_ExistingHistory[mac]["count"] == 1 or 
				nTimeStamp < 2 or 
				tryDeltaTime(beacon_ExistingHistory[mac]["timeSt"][-2]) > sendAfterSecsOfLastMsg  or  # if last recorded msg is older than ~ 60*0.9 (send every 60 secs, use 90%) ~ 54secs 
				beacon_ExistingHistory[mac]["fastDown"] or
				(mac in fastDownList and not beacon_ExistingHistory[mac]["fastDown"] and  tryDeltaTime(beacon_ExistingHistory[mac].get("lastMessageSend",0)) > min(10, max (3., fastDownList[mac]["seconds"]*0.7))  )
			):
			if   ( (mac == trackMac or trackMac == "*") and logCountTrackMac >0):
				U.logger.log(20, "{} NEW!  beacon is back, send message" .format(mac))
			if mac in findMAC: U.logger.log(20,"mac{} checkIfBeaconIsBack back".format(mac))

			if mac in beacon_ExistingHistory: 
				if mac in fastDownList: 		beacon_ExistingHistory[mac]["trigger"][-1] = 4 # beacon_fastdown is back
				else: 							beacon_ExistingHistory[mac]["trigger"][-1] = 5 # beacon is back
			else:								beacon_ExistingHistory[mac]["trigger"][-1] = 2 # beacon is new
			beacon_ExistingHistory[mac]["fastDown"] = False
			if   ( (mac == trackMac or trackMac =="*") and logCountTrackMac > 0 ):
				U.logger.log(20, "mac:{} New!!   fastdown back =========, dt:{:.0f} hist: {:}, count:{}, reason:{}".format(mac, tryDeltaTime(beacon_ExistingHistory[mac]["timeSt"][0]), beacon_ExistingHistory[mac]["timeSt"] , beacon_ExistingHistory[mac]["count"] ,beacon_ExistingHistory[mac]["trigger"][-1] ))
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
		fastBLEReaction::fastBLEReaction:{"B8:7C:6F:1A:D9:65"": 
			{'cmd': {'pulseLengthOn': '0', 'repeat': '2', 'pulseLengthOff': '0.0', 'cmd': 'pulses', 'repeatDelay': '0', 'mac': 'F9:A6:49:9A:DF:85', 'pulses': '1', 'mode': 'batch', 'pulseDelay': '0.0', 'outputDev': 1323447574," 'sensorTriggerValue': 'on'}, 'indigoIdOfSwitchbot': 1323447574, 'pwdOfSwitchbotRPI': 'karl123.',
			 'IdOfSwitchbotRPI': 'pi', 'macOfSwitchbot': 'F9:A6:49:9A:DF:85', 'pi': '12', 'IPOfSwitchbotRPI': '192.168.1.35'}}
		"""
		#U.logger.log(20,"mac:{}, trigOnOff:{}, fastBLEReaction:{}".format(mac, trigOnOff, fastBLEReaction)) 
		if mac not in fastBLEReaction: return 
		if mac in fastBLEReactionLastAction and tryDeltaTime(fastBLEReactionLastAction[mac]) < 2: return 
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
			U.logger.log(20,"... send yes: {}-{}".format(expC.before,expC.after))
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
			U.logger.log(20,"... failed: {}-{}".format(expC.before,expC.after))
			return 
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 



#################################
#################################
######## BLE SENSORS ############
#################################
######################import bluetooth._bluetooth###########
def doSensors( mac, macplain, macplainReverse, rx, tx, hexData):
	global BLEsensorMACs
	bl = ""
	try:

		if mac == "xxxBC:57:29:00:A5:14": 
			U.logger.log(20,"mac:{}; checking  in BLEsensorMACs:{}\n".format(mac, mac in BLEsensorMACs)) 
		if mac not in BLEsensorMACs:
			return "", tx, bl

 

		if "sensor" in BLEsensorMACs[mac]:
			sensor = BLEsensorMACs[mac]["sensor"]
			if sensor == "BLEmyBLUEt":  								
				return  domyBlueT( mac, rx, tx, hexData, sensor)


			if sensor.find("BLEiTrackButton") >-1:
				return  doBLEiTrack( mac, macplain, macplainReverse, rx, tx, hexData, sensor)


			if sensor == "BLEThermopro":
				return   doThermopro( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor == "BLETempspike":
				return   doTempspike( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor == "BLERuuviTag":
				return   doRuuviTag( mac, rx, tx, hexData, sensor)

			if sensor == "BLEKKMsensor":
				return  doBLEKKMsensor( mac, rx, tx, hexData, sensor)

			if sensor.find("BLEiBS") > -1:
				return   doBLEiBSxx( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEminew") > -1:
				return   doBLEminew( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEiSensor") > -1:
				return   doBLEiSensor( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLESatech") > -1:
				return   doBLESatech( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEapril") > -1:
				return   doBLEapril( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEswitchbotTempHum") > -1:
				return   doBLEswitchbotTempHum( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor in ["BLEswitchbotContact","BLEswitchbotMotion"]:
				return   doBLEswitchbotSensor( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEXiaomiMiTempHumRound") > -1:
				return   doBLEXiaomiMi( mac, macplain, macplainReverse, rx, tx, hexData, sensor)
			if sensor.find("BLEXiaomiMiTempHumClock") > -1:
				return   doBLEXiaomiMi( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEXiaomiMiformaldehyde") > -1:
				return   doBLEXiaomiMi( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEgoveeTempHum") > -1:
				return   doBLEgoveeTempHum( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEblueradio") > -1:
				return   doBLEBLEblueradio( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEthermoBeacon") > -1:
				return   doBLEthermoBeacon( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEShelly") > -1:
				return   doBLEShelly( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEHunterNodeBT") > -1:
				return   doBLEHunterNodeBT( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEmeeblue") > -1:
				return   doBLEmeeblue( mac, macplain, macplainReverse, rx, tx, hexData, sensor)


	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return "", tx, bl

#################################


#################################
def doBLEHunterNodeBT(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	global parsedData, outLast
	global bleServiceSections, bleServiceSectionsReverse


	# complete package 
	#			         00 8A   01 64   05 EC C2 00    2D 01   3F 01 00    C8
	bl = ""
	try:
		if False and mac in findMAC: doPrint = True 
		else: doPrint = False
		if len(hexData) < 20: return sensor, tx,  bl
		
		hexData = hexData[12:]
		if hexData.find("121107") == -1: return sensor, tx,  bl
		nn = 2
		#hexData = hexData[:-2]
		#out = ' '.join(hexData[i:i+2] for i in range(0, len(hexData), 2))
		#countP = "01 23 45 67 89 A1 23 45 67 89 B1 23 45 67 89 C1 23 45 67 89 "
		#if out != outLast:countP += " change"
		#if out != outLast:
		#	outLast = out
		#	out += " change"
		#else:
		#	outLast = out

		#if doPrint: U.logger.log(20, "mac:{}, hexdata:{}".format(mac, out))
		#if doPrint: U.logger.log(20, "mac:{}, countP :{}".format(mac, countP))

		return sensor, tx, bl

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

	return sensor, tx, bl	


#################################
def doBLEShelly(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	#let ALLTERCO_MFD_ID_STR = "0ba9";  see: https://bthome.io/format/
	#let BTHOME_SVC_ID_STR = "fcd2";
	#  01  23 45 67 89 11 		  23 45 67 89 21 23 45 67 89
	#  0E  02 01 06 0A 16 		  D2 FC 44 00 32 01 64 3A 02 
	# 									   data-------------
	#  ll  flag
	#            =  not encr, cont bc    
	#               ll   
	#                     		  tag--
	#                             	  44= no encr BC on  BThome v 2
	#                                      == counter is following: 
	#                                         32 is the counter number 
	#                                    		01: bat is following
	#                                          		   3A button press event
	#                                           		  01 = press
	#                                           		  02 = double press
	#                                           		  03 = tripple press
	#                                           		  04 = long press
	#                                           		  FE = button Hold
	
	#
	#  14  02 01 06  10 16 D2 FC 44 	00 0E  01 64   05 00 00 00  21 01 3A 01  
	#  15  02 01 06  11 16 D2 FC 44 	00 09  01 64   05 B8 50 01  2D 01  3F 00 00  
	#  15  02 01 06  11 16 D2 FC 44		00 F1  01 64   05 B0 04 00  2D 00  3F 00 00   shelly door
	#			         00 8A   01		64   05 EC C2 00    2D 01   3F 01 00    C8

	try:
		doPrint =  False #mac == "60:EF:AB:4B:29:4A"

		if mac not in parsedData: return sensor, tx,  ""
		data16 = parsedData[mac]["analyzed"]["code"].get("16","")
		if  doPrint: U.logger.log(20, "mac:{}, hexdata:{}".format(mac, data16))
		if data16 == "": return sensor, tx,  ""
		start = data16.find("D2FC")
		if start < 0: return sensor, tx,  ""
		data = data16[start+6:] # = 44 00 32 01 64 3A 02 



		BLEsensorMACs[mac]["updateIndigoTiming"] = 90

		jj = 0
		itemsValues = {"batteryLevel":""}
		trigValue = {}
		packetId = -99
		trig = ""

		while True:
			if jj+2 >= len(data): break

			tag = shellyTagToProperty.get(data[jj:jj+2],{})
			if doPrint: U.logger.log(20, "mac:{}, tag:{}, data:{}".format(mac, tag, data))
			if tag.get("name","") == "": 
				jj += 2
				continue

			ii = jj + 2
			nn = tag["bytes"] *2
			if tag["name"] not in BLEsensorMACs[mac]: 
				BLEsensorMACs[mac][tag["name"]] = -99999
			if tag["name"] not in trigValue: 
				trigValue[tag["name"]] =  0


			if  tag["type"] == "char":
					itemsValues[tag["name"]] = tag["mapVtoText"].get(data[ii:ii+nn],"None")
					trigValue[tag["name"]] =  tag["trigValue"]
					jj =  ii + nn 
					continue

			if  tag["type"] == "int":
					itemsValues[tag["name"]] = intfromhexR( data[ii:], tag["bytes"])
					if tag["name"] == "packetId": 
						packetId = itemsValues[tag["name"]] 
						if packetId ==  BLEsensorMACs[mac]["packetId"]:  
							return sensor, tx,  ""	

					if tag["factor"] != 1: itemsValues[tag["name"]]  = itemsValues[tag["name"]] * tag["factor"] 

					if tag["typeFinal"].find("float,") == 0:
						roundvalue = int(tag["typeFinal"].split(",")[1])
						itemsValues[tag["name"]] = round(itemsValues[tag["name"]],roundvalue)

					elif tag["typeFinal"].find("int") == 0:
						itemsValues[tag["name"]] = int(itemsValues[tag["name"]])

					trigValue[tag["name"]] =  tag["trigValue"]
					jj =  ii + nn 
					continue

			if  tag["type"] == "intLR":
					itemsValues[tag["name"]] = intfrom8( data[ii+2:],0)
					if data[ii:ii+2] == "02": itemsValues[tag["name"]] = -itemsValues[tag["name"]]

					if tag["factor"] != 1: itemsValues[tag["name"]]  = itemsValues[tag["name"]] * tag["factor"] 

					trigValue[tag["name"]] =  tag["trigValue"]
					jj =  ii + nn 
					continue


			if  tag["type"] == "sint":
					itemsValues[tag["name"]] = signedintfromhexR( data[ii:], tag["bytes"])

					if tag["factor"] != 1: itemsValues[tag["name"]]  = itemsValues[tag["name"]] * tag["factor"] 

					if tag["typeFinal"].find("float,") == 0:
						roundvalue = int(tag["typeFinal"].split(",")[1])
						itemsValues[tag["name"]] = round(itemsValues[tag["name"]],roundvalue)

					elif tag["typeFinal"].find("int") > -1:
						itemsValues[tag["name"]] = int(itemsValues[tag["name"]])
					if doPrint and  tag["name"] == "rotation": U.logger.log(20, "mac:{}, jj:{}, code:{}, name:{:12s}, ll:{},  data:{}, value:{}".format(mac,  jj, data[jj:jj+2] , tag["name"] ,  len(data),  data[jj+2:jj+6] , itemsValues[tag["name"]]  ))

					trigValue[tag["name"]] =  tag["trigValue"]
					jj =  ii + nn 
					continue


			

		# button is special case, needs to be reset
		if tryDeltaTime(BLEsensorMACs[mac]["lastUpdate"]) > 2 and  BLEsensorMACs[mac].get("button","None") != "None":  BLEsensorMACs[mac]["button"] = "xxx"

		if tryDeltaTime(BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: trig = "Time/" 			# send min every xx secs

		# if same packet id and not time update, return 
		if packetId ==  BLEsensorMACs[mac]["packetId"] and trig == "":  
			return sensor, tx,  itemsValues["batteryLevel"]

		dd = {   # the data dict to be send 
						"mac": 			mac,
						"rssi":			int(rx)
				}


		for tt in itemsValues:
			if tt in ["packetId","rotation", "Illuminance"]: continue
			if itemsValues[tt] != "" and itemsValues[tt] != BLEsensorMACs[mac][tt]:
				trig = tt+"/"


		if trig.find("isOpen") > -1: 
			if "rotation" in itemsValues:
				itemsValues["rotation"] = ""


		for tt in ["rotation", "Illuminance"]:
			if tt in itemsValues and itemsValues[tt] != "":
				if abs(itemsValues[tt]  - BLEsensorMACs[mac][tt])/max(1,(itemsValues[tt]  + BLEsensorMACs[mac][tt])) > trigValue[tt]: trig += tt+"/"


		for tt in itemsValues:
			if itemsValues[tt] != "":
				dd[tt] = itemsValues[tt]

		BLEsensorMACs[mac]["packetId"]   		= packetId

		trig = trig.replace("None","").replace("//","/")

		trig = trig.strip("/")

		if trig == "batteryLevel": trig = "Time"
		dd ["trigger"] = trig

		for tt in itemsValues:
			if itemsValues[tt] != "":
				dd[tt] = itemsValues[tt]

		if doPrint: U.logger.log(20, "mac:{}, dd:{}, data:{}".format(mac,dd,  data))

		if  trig != "":
					# compose complete message
					checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
					# remember last values
					if  doPrint: U.logger.log(20, "mac:{}---------- send".format( mac)  )
					BLEsensorMACs[mac]["lastUpdate"] 	= time.time()

					for tt in itemsValues:
						if itemsValues[tt] != "": BLEsensorMACs[mac][tt] = itemsValues[tt] 

		return sensor, tx,  itemsValues["batteryLevel"]		

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

	return sensor, tx,  ""	



def doBLEswitchbotSensor(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	global switchbotData
	try:

		if mac not in parsedData: return sensor, tx,  ""
		"""
		type1
                                  MAC#-------- 
											   xx          bright changes counter 00-ff
											      b        brightnesss &b000000010  10=bright; 01 = dim
											     		+ 4 = 5/6
											        V      Version = 1.2? 
											 	      secs motion secs since last int("xxxx",16) event 64k seconds

			11 02 0106 0D  FF6909 D99919AE2A81 4C 6 C 0018      
            11 02 0106 0D  FF6909 D99919AE2A81 32 6 C 000D  BF;
			01 23 4567 89  112345 678921234567 89 3 1 2345
			                 0123 456789112345 67 8 9 2123

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
			    012345678911 23 456789
		type3
							BB:								0-1	int("BB",16)&0b01111111   = battery 0-64 = 0-100 some times first bit  is on, dont know why
							   G:								2	int("G",16)               = mostly 0 ?
							    K:								3	int("K",16)               = closed=x00x, open=x01x, long open=x10x if bright= xxx1
							     ssss							4-7 int("ssss",16)            = secs since ??? restarts once at battery start, or device soft restart = when type4 ssss hight bit is  0-> 1
							         tttt:						8-11int("tttt",16)            = 0-2**16-1 secs since last open / closed 
										 o:						12	int("o",16)&0b1100        =  abxx  ab changes when opened 01 -> 10 -> 11 -> 01
							              C :					13	int("C",16)&0b0001        = 1-15 counter for press button
			0D 0C 16  3D FD 64 00 E4  02  00  180  01  B40                     
			01 23 45  67 89 11 23 45 67 89 21 23 45 67
                      01 23 45 67 89 11 23

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
			14 020106 10 FF6909 C9D180A1AA9C  5B 0C06A106871E   
	msg1-- 2 b   1  2 
	msg2-- 16 b          1 2 3  4 5 6 7 8 9   1 2 3 4 5 6
			01 234567 89 112345 678921234567  89312345678941   
						   0123 456769112345  6789212345678 
                                              01234567891123
		"""
		doPrint = False #mac == "C0:81:FE:CD:CF:9F"
		dataFF = parsedData[mac]["analyzed"]["code"].get("FF","")
		data16 = parsedData[mac]["analyzed"]["code"].get("16","")

		if  doPrint: U.logger.log(20, "mac:{}, sens:{}; len ff:{} 16:{}".format(mac, sensor, len(dataFF), len(data16) ))

		if   "6909"+macplain 	in  dataFF and len(dataFF) == 13*2: 	dType = 1  # for motion sensor
		elif "3DFD73"		 	in  data16:  							dType = 2  # for motion sensor
		elif "3DFD64"		 	in  data16:  							dType = 3  # for contact sensor
		elif "6909"+macplain 	in  dataFF and len(dataFF) == 15*2:		dType = 4  # for contact sensor
		else:											 		    	dType = 0

		if  doPrint and dType in [1,4]: U.logger.log(20, "mac:{}, sens:{};                       dataFF:{};".format(mac, sensor, dataFF ))
		if  doPrint and dType in [2,3]: U.logger.log(20, "mac:{}, sens:{};                 data16:{};".format(mac, sensor, data16 ))


		if dType == 0: 
			if  doPrint:				 U.logger.log(20, "mac:{}, sens:{}; dType:{};  ".format(mac, sensor, dType ))
			return sensor, tx,  ""
		doPrint = doPrint #and (dType == 1 or dType == 2) 
		if  doPrint: U.logger.log(20, "mac:{}, sens:{}; dType:{}; ".format(mac, sensor, dType ))

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
			hData 		    = dataFF[16:]
			lightCounter 	= int(hData[0:2],16)
			flag	  		= int(hData[2],16)
			light	  		= "bright" if flag&0b0011 == 2 else "dim"
			motion			= int(hData[2],16)  & 0b0100 != 0
			dontknow		= (int(hData[3],16) & 0b1110) 
			secsSinceLastM	= int(hData[4:8],16) + ((int(hData[3],16)&0b0001) * 65536)
			if motion:
				lastMotion 		= int(tryDeltaTime(secsSinceLastM)) #epoch time at last motion
				motionDuration 	= secsSinceLastM
				if BLEsensorMACs[mac]["lastMotion"]  > 0:
					lastMotion 	= max(lastMotion, BLEsensorMACs[mac]["lastMotion"] )
					BLEsensorMACs[mac]["lastMotion"] =  lastMotion
				else:
					BLEsensorMACs[mac]["lastMotion"] = lastMotion
			BLEsensorMACs[mac]["secsSinceLastM"] = secsSinceLastM
			if BLEsensorMACs[mac]["motionDuration"] > BLEsensorMACs[mac]["secsSinceLastM"]: BLEsensorMACs[mac]["motionDuration"] = BLEsensorMACs[mac]["secsSinceLastM"]
			if BLEsensorMACs[mac]["motionDuration"] ==-1: BLEsensorMACs[mac]["motionDuration"] = BLEsensorMACs[mac]["secsSinceLastM"]
						
			dd = {   # the data dict to be send 
							"onOffState": 			motion,
							"light": 				light,
							"sensitivity": 			switchbotData[mac]["sensitivity"],
							"lightCounter": 		lightCounter,
							"lastOn": 				lastMotion,
							"motionDuration": 		motionDuration,
							"mac": 					mac,
							"rssi":					int(rx)
					}
			if BLEsensorMACs[mac]["batteryLevel"] != "": 	dd["batteryLevel"] 	 = BLEsensorMACs[mac]["batteryLevel"]
			if lastMotion > -1: 									dd["lastMotion"] 	 = BLEsensorMACs[mac]["lastMotion"]
			if BLEsensorMACs[mac]["motionDuration"] > -1: 	dd["motionDuration"] = BLEsensorMACs[mac]["motionDuration"]

			if motion:	updateEvery = 9
			else:		updateEvery = 40

			#U.logger.log(20, "mac:{},  light:{}-{:08b}".format(mac, light, flag))


			trig = ""
			if						tryDeltaTime(BLEsensorMACs[mac]["lastUpdate"] )  > updateEvery:  	trig += "Time"  	# send min every xx secs
			if  lastMotion > 0	and abs(lastMotion - BLEsensorMACs[mac]["lastMotion"]) > 1:  			trig += "motion/"
			if light != ""		and light != BLEsensorMACs[mac]["light"]:  								trig += "lightChange/"
			if 						motion  != BLEsensorMACs[mac]["motion"]:							trig += "motion/"
			if						tryDeltaTime(BLEsensorMACs[mac]["lastUpdate"] )  > updateEvery:  	trig += "Time"  	# send min every xx secs
			trig = trig.strip("/")

			if True:
										BLEsensorMACs[mac]["motion"]			= motion
										BLEsensorMACs[mac]["light"]				= light
			if lastMotion != -1:		BLEsensorMACs[mac]["lastMotion"]		= lastMotion
			if motionDuration != -1:	BLEsensorMACs[mac]["motionDuration"]	= motionDuration

			if trig != "":
						dd["trigger"] = trig.strip("/")
						if  doPrint: U.logger.log(20, "mac:{} updindigo:{}; dd:{}".format( mac, updateEvery,  dd)  )
						# compose complete message
						checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
						# remember last values
						BLEsensorMACs[mac]["lastUpdate"] 		= time.time()
						fastSwitchBotPress = "on" if motion else ""
						if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)
			if doPrint: U.logger.log(20, "mac:{}, trig:{}, lastMotion:{}".format(mac, trig, updateEvery, lastMotion ))

					
				
			return sensor, tx,  batteryLevel		


		if dType == 2:
			hData3  = data16[8:]
			flags   = int(hData3, 16)
			dimm    = flags & 0b0001
			bright  = flags & 0b0010
			mediumS = flags & 0b0100
			shortS  = flags & 0b1000
			longS   = flags & 0b1100 == 0
			hData1  = data16[12:16]
			secsSinceLastEvent = int(hData1,32)
			hData2 = data16[10:12]
			BL = int(hData2,16)&0b01111111
			if doPrint: U.logger.log(20, "mac:{}, bat:{}-hex:{}, secsSinceLastEvent:{}-hex:{}, flags:{}-{:b}".format(mac, BL, hData2, secsSinceLastEvent, hData1, hData3, flags))
			BLEsensorMACs[mac]["batteryLevel"] = BL
			switchbotData[mac]["brightness"] = "bright" if bright else "dim"
			if mediumS: 	switchbotData[mac]["sensitivity"]  = "long"
			elif shortS:	switchbotData[mac]["sensitivity"]  = "medium"
			else:			switchbotData[mac]["sensitivity"]  = "long"
			switchbotData[mac]["secsSinceLastEvent"] = secsSinceLastEvent
			BLEsensorMACs[mac]["secsSinceLastEvent"] = secsSinceLastEvent
			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		


		## contact sensor

		## for type 3/4 get most of the info from type3, then send out package
		if dType == 3:								#01 2 3 4567 8901 2 3 pos
			hData				= data16[8:]
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
				if  doPrint: U.logger.log(20, "mac:{}, sens:{}; dType:{}; ret 1".format(mac, sensor, dType) )
				return sensor, tx,  BL

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
			if					BL			!= BLEsensorMACs[mac]["batteryLevel"]:																trig += "batLevel/" 
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
			BLEsensorMACs[mac]["batteryLevel"] = BL

		
			dd = {   # the data dict to be send 
							"light": 				light,
							"counter": 				switchbotData[mac]["counter"],
							"onOffState": 			onOff !="",
							"buttonCounter":		switchbotData[mac]["buttonCounter"],
							"shortOpen": 			switchbotData[mac]["shortOpen"],
							"longOpen": 			switchbotData[mac]["longOpen"] ,
							"lastButton": 			switchbotData[mac]["timeButton"] ,
							"lastLightChange": 		switchbotData[mac]["timelightChange"] ,
							"lastOn": 				switchbotData[mac]["timeClosed"] ,
							"lastShortOpen": 		switchbotData[mac]["timeShortOpen"] ,
							"lastLongOpen": 		switchbotData[mac]["timeLongOpen"] ,
							"batteryLevel": 		BL,
							"trigger": 				trig.strip("/"),
							"sensitivity": 			switchbotData[mac]["sensitivity"],
							"mac": 					mac,
							"rssi":					int(rx)
					}

			if trig != "":	updateEvery = 0
			else:			updateEvery = 50
			if switchbotData[mac]["closed"] != closed1 or switchbotData[mac]["counternew"] >1: updateEvery = 0
			if updateEvery >0 and (tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"] )  > updateEvery): trig += "Time"  	# send min every xx secs


			if doPrint: U.logger.log(20, "mac:{}, updateEvery:{:2d}, bin:{:08b} , cl1:{} newC{:3d}, openC:{:3d}, c:{:3d}, resetC:{:3d}, CShort:{}, Bli:{}, st4:{}, flag:{}, dd:{:}, onOff:{}, trig:{}, ".format(mac, updateEvery, int(hData[3],16), closed1, switchbotData[mac]["counternew"] , openCounter, switchbotData[mac]["counter"], resetCounter, switchbotData[mac]["buttonCounter"], BlindicatorBit, switchbotData[mac]["status4"], openCloseInd, dd, onOff, trig))

			if trig != "":
						if False and doPrint: U.logger.log(20, "mac:{} triggers:oneChange:{}; sending data ".format( mac, trig )  )
						# compose complete message
						checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
						# remember last values
						BLEsensorMACs[mac]["lastUpdate"] 		= time.time()
						U.writeFile("temp/switchbot.data",json.dumps(switchbotData))
						switchbotData[mac]["counternew"] = 0

						fastSwitchBotPress = "on" if onOff !="" else "off"
						if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)
					
				
			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		

		if dType == 4:				#01 2 3 4567 8901 2 3 Pos
			hData = dataFF[16:]     #5B 0 C 06A1 0687 1 E 
			switchbotData[mac]["status4"] 		= int(hData[3],16)
			switchbotData[mac]["counternew"] 	= int(hData[0:2],16) - switchbotData[mac]["counter"]
			switchbotData[mac]["counter"] 		= int(hData[0:2],16)
			if  doPrint: U.logger.log(20, "mac:{}, hData= 0-1:{:}; 2b:{:4b}; 3b:{:4b}; 4-7:{}; 8-11:{}; 12b:{:4b}; 13:{:2d}; ".format(mac,  hData[0:2],  int(hData[2],16),   int(hData[3],16), hData[4:8], hData[8:12], int(hData[12],16), int(hData[13],16)) )
			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""




def doBLEswitchbotTempHum(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	try:
		if mac not in parsedData: return sensor, tx,  ""
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
 
       1C  11 07 1B C5 D5 A5 02 00 		B8 9F E6 11 4D 22 00 0D A2 CB   09 16 00 0D 54 10 64 01 99 AD   DA
															adv "09" ==       00 0D 54 10 E4 04 97 3E
																		 start ------------------
																					^^ =type:
																					48 = H = switchbot (Hand),  63 = c = curtain,  73=s= motion sensor, 64= d= contactsensor, 54=T= temp , see: https://github.com/Danielhiversen/pySwitchbot/blob/master/switchbot/adv_parser.py
	pos:01 23 45 67 89 11 23 45 67 		89 21 23 45 67 89 31 23 45 67   89 41 23 45 67 89 51 23 45 67   89 
	pos:                                                                      01 23 45 67 89 11 23 45 
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
		data16 = parsedData[mac]["analyzed"]["code"].get("16","")
		if data16 == "" or len(data16) < 16: return sensor, tx,  ""

		model = data16[4:6]
		if model != "54": return sensor, tx,  ""

		if doPrint: U.logger.log(20, "mac:{}, sens:{}; model:{}, lldata16:{}, data16:{}".format(mac, sensor, model,  len(data16), data16))

		mode  = data16[6:8]

		batteryLevel = int(data16[8:10].encode("utf-8"), 16) & 0b01111111

		tempFra = int(data16[10:12].encode("utf-8"), 16) / 10.0
		tempInt = int(data16[12:14].encode("utf-8"), 16)
		if tempInt < 128:
			tempInt *= -1
			tempFra *= -1
		else:
			tempInt -= 128
		temp = tempInt + tempFra

		hum = int(data16[14:16].encode("utf-8"), 16) % 128

		if doPrint: U.logger.log(20, "mac:{}, temp:{},  hum:{}".format(mac,temp,hum ))
		trig = ""
		if abs(temp - BLEsensorMACs[mac]["temp"]) > 0.5: 													trig+= "temp/" 
		if abs(hum - BLEsensorMACs[mac]["hum"]) > 2: 														trig+= "hum/" 
		if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: 	trig+= "Time" 			# send min every xx secs
		trig = trig.strip("/")

		dd = {   # the data dict to be send 
						"temp": 		round(temp+ BLEsensorMACs[mac]["offsetTemp"],1),
						"hum": 			int(hum + BLEsensorMACs[mac]["offsetHum"]),
						"batteryLevel": batteryLevel,
						"model": 		model,
						"mode": 		mode,
						"mac": 			mac,
						"trigger": 		trig,
						"rssi":			int(rx)
				}

		if doPrint: U.logger.log(20, "mac:{}, temp:{}, hum:{}, trig:{}<<".format(mac, temp, hum, trig))

		if  trig !="":
					# compose complete message
					checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
					# remember last values
					if  doPrint: U.logger.log(20, "mac:{} trig:{}; updateIndigoTiming:{}; send:{}".format( mac, trig,BLEsensorMACs[mac]["updateIndigoTiming"] ,  dd)  )
					BLEsensorMACs[mac]["lastUpdate"] 	= time.time()
					BLEsensorMACs[mac]["temp"]    	 	= temp
					BLEsensorMACs[mac]["hum"]    	 	= hum
					BLEsensorMACs[mac]["batteryLevel"]  = batteryLevel
		
		return sensor, tx,  batteryLevel		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""



def doBLEBLEblueradio(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	try:

		if mac not in parsedData: return sensor, tx,  ""
		dataFF = parsedData[mac]["analyzed"]["code"].get("FF","")
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
		if doPrint: U.logger.log(20, "mac:{}, sensor:{} dataFF:{}, tag1:{}".format(mac, sensor,  dataFF, ddataFF.find("FF85000200")))

		if dataFF.find("85000200") <1:  
			return sensor, tx,  ""


		rangeV			= [1000.,  4000., 16000., 64000.]
		rangeText		= [1,  4, 16, 64]
		resolutionMaxV 	= [65535., 4095., 255.,   15.]
		resolutionBits 	= [16, 12, 8,   4]

		onOff 			= BLEsensorMACs[mac]["onOff"]
		temp  			= BLEsensorMACs[mac]["temp"]
		Illuminance 	= BLEsensorMACs[mac]["Illuminance"]
		counter			= BLEsensorMACs[mac]["Illuminance"]
		sensorSetup 	= {"temp":"","Accel":"","Light":""}
		lTot = len(dataFF)

		lDat = len(dataFF) 

		if doPrint: U.logger.log(20, "mac:{}, sens:{}; passed 1".format(mac, sensor ))

		p = 10
		batteryLevel =  min(100,max(0,int( dataFF[p:p+2],16)))

		p = 12
		counter =  min(100,max(0,int( dataFF[p:p+2],16)))

		p = 14
		for nn in range(3):
			if p > lTot -8: break

			dType = dataFF[p:p+2]

			if doPrint: U.logger.log(20, "mac:{}, sens:{}; p:{}, tot char:{}, dType:{}, dataFF:{}".format(mac, sensor, p, lTot, dType, dataFF[p:-2] ))

			if dType == "41":
				if dataFF[p+2:p+4] == "02":
					onOff = dataFF[p+4:p+6] != "02"
					sensorSetup["Accel"] = "Op/Cl"
				p += 6		
				#if doPrint: U.logger.log(20, "mac:{}, sens:{}; onOff:{}".format(mac, sensor, onOff ))

			elif dType == "42":
				testHEX		= dataFF[p+2:p+4]
				testNumber  = int(testHEX ,16) & 0b00111111 
				dataLen 	=              testNumber   & 0b00000011 
				rangeInd 	= max(0,min(3,(testNumber   & 0b00001100) >>2 )) 
				resInd	 	= max(0,min(3,(testNumber   & 0b00110000) >>4 )) 
				if dataLen == 2:
					Illuminance = round(int(dataFF[p+6:p+8] + dataFF[p+4:p+6],16 ) * rangeV[rangeInd] / resolutionMaxV[resInd],1)
					p += 8		
					sensorSetup["Light"] = "range={}k,{}b".format(rangeText[rangeInd],resolutionBits[resInd])
				elif dataLen == 1:
					Illuminance = round(int(dataFF[p+4:p+6],16) * rangeV[rangeInd] / resolutionMaxV[resInd],1)
					sensorSetup["Light"] = "range={}k,{}b;".format(rangeText[rangeInd],resolutionBits[resInd])
					p += 6		
				if doPrint: U.logger.log(20, "mac:{}, sens:{}; Illuminance:{},  dataLen:{}, rangeInd:{}, range:{}, resInd:{} res:{}, testHEX:{},testbin:{:6b} testNumber:{}, rangeX:{}, resX:{}, dataFF".format(mac, sensor, Illuminance, dataLen, rangeInd, rangeV[rangeInd] ,resInd,resolutionMaxV[resInd], testHEX,testNumber, testNumber, testNumber & 0b00001100, testNumber & 0b00110000 , dataFF[p:p+8]))

			elif dType == "43":
				temp = round(signedIntfrom16( dataFF[p+4:p+6] + dataFF[p+2:p+4] )*0.0625,1) + BLEsensorMACs[mac]["offsetTemp"]
				sensorSetup["temp"] = "16b"
				#if doPrint: U.logger.log(20, "mac:{}, sens:{}; temp:{}, hacData:{}".format(mac, sensor, temp,dataFF[p+2:p+6] ))
				p += 6		

			else: # this is not a std tag, skip and try to find next
				nextFound = False
				for ii in [2,4,6,8]:
					if p + ii < lTot -2:
						if dataFF[p+ii:p+ii+2] in ["41","42","43"]:
							p += (ii - 2)
							nextFound = True
							break
				#if doPrint: U.logger.log(20, "mac:{}, sens:{}; p:{}, dType:{} not found, break".format(mac, sensor, p, dType ))
				if not nextFound: break
		ss = ""
		for item in sensorSetup:
			ss += item+":"+sensorSetup[item]+";"
		sensorSetup = ss.strip(";")


		BLEsensorMACs[mac]["nMessages"] +=1 
		trig = ""
		if abs(temp - BLEsensorMACs[mac]["temp"]) > 0.5: 																	trig += "temp/"
		if onOff != BLEsensorMACs[mac]["onOff"]: 																			trig += "onOff/"
		if (Illuminance < 20 and abs(Illuminance - BLEsensorMACs[mac]["Illuminance"]) > 4) or (Illuminance > 20 and abs(Illuminance - BLEsensorMACs[mac]["Illuminance"])/max(2,BLEsensorMACs[mac]["Illuminance"]) > 0.1): trig += "Illuminance/"
		if tryDeltaTime(BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: 			trig += "Time"  			# send min every xx secs
		trig = trig.strip("/")

		dd = {   # the data dict to be send 
						"temp": 		round(temp+ BLEsensorMACs[mac]["offsetTemp"],1),
						"Illuminance":	Illuminance, 
						"onOff": 		onOff, 
						"sensorSetup":	sensorSetup, 
						"batteryLevel": batteryLevel, 
						"mac": 			mac,
						"trigger": 		trig,
						"rssi":			int(rx)
				}


		if doPrint: U.logger.log(20, "mac:{}, temp:{}, Illuminance:{}, counter:{}, triggers:{}".format(mac, temp, Illuminance, counter, trig))

		if  trig != "":
					# compose complete message
					checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

					# remember last values
					if doPrint: U.logger.log(20, "mac:{} triggers: {}, onOff:{}; updateIndigoTiming:{}; send:{}".format( mac, trig, BLEsensorMACs[mac]["updateIndigoTiming"] ,  dd)  )
					BLEsensorMACs[mac]["lastUpdate"]	= time.time()
					BLEsensorMACs[mac]["temp"]			= temp
					BLEsensorMACs[mac]["Illuminance"]	= Illuminance
					BLEsensorMACs[mac]["onOff"]			= onOff
					BLEsensorMACs[mac]["batteryLevel"]	= batteryLevel

		
		return sensor, tx,  batteryLevel		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""

#################################


def doBLEgoveeTempHum(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	try:

		if mac not in parsedData: return sensor, tx,  ""
		dataFF = parsedData[mac]["analyzed"]["code"].get("FF","")
		data09 = parsedData[mac]["analyzed"]["code"].get("09F","")
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

		typeInfo 		= 	{"A":{"pos0":0, "type": "3+1",   "id":"01000101", "ll" : 8*2},
							 "B":{"pos0":0, "type": "3+1",   "id":"88EC00",   "ll" : 7*2},
							 "C":{"pos0":0, "type": "2+2+1", "id":"88EC00",   "ll" : 9*2}
							}

		sens = ""
		dataType 	= ""
		startData 	= -1
		for stype in  typeInfo:
			posTag = dataFF.find(typeInfo[stype]["id"])
			if posTag == 0 and len(dataFF) == typeInfo[stype]["ll"]:
				sens 		= stype
				dataType 	= typeInfo[sens]["type"]
				startData 	= posTag + len(typeInfo[sens]["id"])
				break
		if sens == "": 
			return sensor, tx,  ""


		if doPrint: U.logger.log(20, "mac:{}, sens:{}; startData:{},  type:{}, len(dataFF):{}".format(mac, sens, startData, dataType, len(dataFF) ))
		hData = dataFF[startData:]

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
			if doPrint: U.logger.log(20, "mac:{}, hData:{}, intData:{} + {} + {} = {}, temp:{},  hum:{}".format(mac, hData,  intData1, intData2, intData3, intData,temp,hum ))

		elif dataType == "2+2+1":
			temp		 = int(hData[0:2],16)<<8 + int(hData[2:4],16)
			if temp > 32767: temp -= 65536
			temp		 = round(  temp /100.,  1)
			hum		 	 =  min(100,max(0,float(int(hData[4:6],16)<<8 + int(hData[6:8],16)) /100. + 0.5))
			batteryLevel =  min(100,max(0,int( hData[8:10],16)))

		else:
			return sensor, tx,  ""

		out = ""
		if doPrint:
			for ii in range(0,len(dataFF)-2,2):
				out+= dataFF[ii:ii+2] + " "
				#U.logger.log(20, "mac:{}, sensor:{} data string:{}, {}".format(mac,sensor,  dataFF,  out))
				pass

		BLEsensorMACs[mac]["nMessages"] +=1 

		trig = ""
		if abs(temp - BLEsensorMACs[mac]["temp"]) > 0.5: 															trig += "temp/" 
		if abs(hum - BLEsensorMACs[mac]["hum"]) > 2: 																trig += "hum/" 
		if tryDeltaTime(BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: 	trig += "Time" 			# send min every xx secs
		trig = trig.strip("/")

		dd = {   # the data dict to be send 
						"temp": 		round(temp+ BLEsensorMACs[mac]["offsetTemp"],1),
						"hum": 			int(hum + BLEsensorMACs[mac]["offsetHum"]),
						"batteryLevel": batteryLevel, 
						"counter": 		BLEsensorMACs[mac]["nMessages"], 
						"mac": 			mac,
						"trigger": 		trig,
						"rssi":			int(rx)
				}


		if False and doPrint: U.logger.log(20, "mac:{}, temp:{}, hum:{}, triggers:{};   nMessages:{}".format(mac, temp, hum, trig, BLEsensorMACs[mac]["nMessages"]))

		if BLEsensorMACs[mac]["nMessages"] > 0 and hum > -100. and temp > -100.:
			if  trig != "":
					# compose complete message
					checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

					# remember last values
					if  False and doPrint: U.logger.log(20, "mac:{} triggers:Time:{};temp:{};hum:{}; updateIndigoTiming:{}; send:{}".format( mac, trigTime , trigTemp , trigHum,BLEsensorMACs[mac]["updateIndigoTiming"] ,  dd)  )
					BLEsensorMACs[mac]["lastUpdate"] = time.time()
					BLEsensorMACs[mac]["temp"]    	 = temp
					BLEsensorMACs[mac]["hum"]    	 = hum
					BLEsensorMACs[mac]["batteryLevel"] = batteryLevel
		
		return sensor, tx,  batteryLevel		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""

#################################

def doBLEXiaomiMi(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	try:

		"""

  					   19   0E 09 4D 4A 48 46 44 31 5F 30 30 31 30 46 4309FF8F0352572D424C45B1
 
		## message formats for round sensor - LYWSDCGQ = AA 01 = S-typ
        ##                                       counter                                    data-
        ##                                             S-typ ct   reverse mac -----   Stype ll      1  2  3  4		
		##16 02 01 06                12 16 95 FE 50 20 AA 01 nn   E2 1D 37 34 2D 58   0A 10 01      64      			0A=battery; 	ll= 1 byte
		##17 02 01 06                13 16 95 FE 50 20 AA 01 nn   E2 1D 37 34 2D 58   06 10 02      16 02   			06=hum; 		ll= 2 byte
		##17 02 01 06                13 16 95 FE 50 20 AA 01 nn   E2 1D 37 34 2D 58   04 10 02      DA 02   			04=temp; 		ll= 2 byte
		##17 02 01 06                13 16 95 FE 51 20 DF 02 7D   FC 10 00 43 57 48   06 10 02      0E 02  
		##19 02 01 06                15 16 95 FE 50 20 AA 01 nn   E2 1D 37 34 2D 58   0D 10 04      FC 00   1E 02  		0D=temp + hum;	ll= 4 byte
	pos                                 01 23 45 67 89 11 23 45   67 89 21 23 45 67   89 31 23      45 67   89 41  		pos in tag 
	pos16   							   01 23 45 67 89 11 23   45 67 89 21 23 45   67 89 31      23 45   67 89    	position in data16
		## formaldehyde
		##17 02 01 06                13 16 95 FE 51 20 DF 02 7E   FC 10 00 43 57 48   10 10 02      4200 

		# 
	pos   01 23 45 67                89 11 23 45 67 89 21 23 45   67 89 31 23 45 67   89 41 23      45 67   89 51		position in hexData
	pos16   							   01 23 45 67 89 11 23   45 67 89 21 23 45   67 89 31      23 45   67 89    	position in data16
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
	pos16   							   01 23 45 67 89 11 23   45 67 89 21 23 45   67 89 31 23   45 67           	position in data16


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
		if mac == "xxx48:57:43:00:10:FC": doPrint = True
		#if doPrint: U.logger.log(20, "mac:{}, sensor:{} hexData:{}".format(mac, sensor, hexData))


		if mac not in parsedData: return sensor, tx,  ""
		data16 = parsedData[mac]["analyzed"]["code"].get("16","")
		if data16 == "": return sensor, tx,  "" 

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
		data = data16
		typeInfo 		= 	{ "LYWSDCGQ":{"pos0":0, "pos1":[ 0,12], "pos2":[26,32], "posC":12, "id":"95FE5020AA01"}
							, "MJHFD1":  {"pos0":0, "pos1":[ 0,12], "pos2":[26,32], "posC":12, "id":"95FE5120DF02"}
							, "LYWSD02": {"pos0":0, "pos1":[ 0,12], "pos2":[28,34], "posC":12, "id":"95FE70205B04"}
							}
		found = False
		for stype in  typeInfo:
			if data16.find(typeInfo[stype]["id"]) >-1:
				found = True
				break
		if not found: 
			if doPrint: U.logger.log(20, "mac:{}, stype not found, sensor:{}".format(mac, sensor))
			return sensor, tx,  ""


		sens = ""
		if	 sensor.find("Round") >-1: 			sens = "LYWSDCGQ"
		elif sensor.find("Clock") >-1: 			sens = "LYWSD02"
		elif sensor.find("formaldehyde") >-1: 	sens = "MJHFD1"
		else: 
			if doPrint: U.logger.log(20, "mac:{},sens not found:{}, sensor:{}".format(mac, sens, sensor))
			return sensor, tx,  ""
		if doPrint: U.logger.log(20, "mac:{}, sens:{}, sensor:{} start ========".format(mac, sens, sensor))


		testString		= data16[typeInfo[sens]["pos1"][0]:typeInfo[sens]["pos1"][1]]	+ macplainReverse + data16[typeInfo[sens]["pos2"][0]:typeInfo[sens]["pos2"][1]]
		testStringTEMP 	= typeInfo[sens]["id"] 											+ macplainReverse + TEMPtag
		testStringTH	= typeInfo[sens]["id"] 											+ macplainReverse + TEMPHtag
		testStringHUM	= typeInfo[sens]["id"] 											+ macplainReverse + HUMtag
		testStringFORM	= typeInfo[sens]["id"] 											+ macplainReverse + FORMAtag
		testStringBAT	= typeInfo[sens]["id"] 											+ macplainReverse + BATtag
		dataString		= data16[typeInfo[sens]["pos2"][1]:]
		counter			= int(data16[typeInfo[sens]["posC"]:typeInfo[sens]["posC"]+2],16)

		if BLEsensorMACs[mac]["nMessages"] == 0:
			BLEsensorMACs[mac]["tempAve"] = []
			BLEsensorMACs[mac]["tempHum"] = []
			for ii in range(BLEsensorMACs[mac]["numberOfMeasurementToAverage"]):
				BLEsensorMACs[mac]["tempAve"].append(-100)
				BLEsensorMACs[mac]["tempHum"].append(-100)

		if doPrint:
			out = ""
			for ii in range(10,len(data16)-2,2):
				out+= data16[ii:ii+2] + " "
				U.logger.log(20, "mac:{},sensor:{} data string:{}, count:{}, \nteststr:{}\nformTag:{}\nout:{}".format(mac,sensor,  dataString, counter, testString, testStringFORM, out))


		temp 			= BLEsensorMACs[mac]["temp"]
		hum  			= BLEsensorMACs[mac]["hum"]
		Formaldehyde  	= BLEsensorMACs[mac]["Formaldehyde"]

		if testString == testStringTH: 
			val = int(dataString[0:2],16) + int(dataString[2:4],16)*256
			if val > 32767: val -= 65536
			temp = tralingAv(sensor, mac, "tempAve", val/10.)
			val = int(dataString[4:6],16) + int(dataString[6:8],16)*256+0.5
			if val > 32767: val -= 65536
			hum = int( tralingAv(sensor, mac, "humAve", val/10.))
			if doPrint:
				U.logger.log(20, "mac:{}, typ: TH  {}+{} =tem:{}; {}+{} =hum:{}  dataString:{} ".format(mac, dataString[0:2],dataString[2:4],  temp, dataString[4:6],dataString[6:8], hum, out))
			BLEsensorMACs[mac]["nMessages"] += 1

		elif testString == testStringHUM: 
			val = int(dataString[0:2],16) + int(dataString[2:4],16)*256 +0.5
			if val > 32767: val -= 65536
			hum = int( tralingAv(sensor, mac,"humAve", val/10.) )
			if doPrint:
				U.logger.log(20, "mac:{}, typ: H  {}+{} =Hum:{};   dataString:{}".format(mac, dataString[0:2],dataString[2:4],  hum, out))
			if BLEsensorMACs[mac]["hum"]   == -100: 
				BLEsensorMACs[mac]["hum"]   = hum
			BLEsensorMACs[mac]["nMessages"] += 1

		elif testString == testStringTEMP:
			val = int(dataString[0:2],16) + int(dataString[2:4],16)*256
			if val > 32767: val -= 65536
			temp = tralingAv(sensor, mac, "tempAve", val/10.)  
			if doPrint:
				U.logger.log(20, "mac:{}, typ: T  {}+{} =temp:{};   dataString:{}".format(mac, dataString[0:2],dataString[2:4],  temp, out))
			if BLEsensorMACs[mac]["temp"]   == -100: 
				BLEsensorMACs[mac]["temp"]   = temp
			BLEsensorMACs[mac]["nMessages"] += 1

		elif testString == testStringFORM: 
			Formaldehyde  = (int(dataString[0:2],16) + int(dataString[2:4],16)*256. ) /100.
			if doPrint:
				U.logger.log(20, "mac:{}, typ: B  {}    =Formaldehyde:{};   dataString:{}".format(mac, dataString[0:2],  Formaldehyde, out))
			BLEsensorMACs[mac]["nMessages"] += 1


		elif testString == testStringBAT: 
			BLEsensorMACs[mac]["batteryLevel"]  = int(dataString[0:2],16) 
			if doPrint:
				U.logger.log(20, "mac:{}, typ: B  {}    =bat:{};   dataString:{}".format(mac, dataString[0:2],  BLEsensorMACs[mac]["batteryLevel"] , out))
			BLEsensorMACs[mac]["nMessages"] += 1

		else:
			if doPrint: U.logger.log(20, "mac:{}, tag not found, dataString:{}  hexstr:{} ".format(mac, dataString, out ))
			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]	


		
		dd = {}  # the data dict to be send 
		dd["mac"] =	mac
		if temp > -100: 											dd["temp"] 			= round(temp+ BLEsensorMACs[mac]["offsetTemp"],1)
		if hum > -100: 												dd["hum"]			= int(hum + BLEsensorMACs[mac]["offsetHum"])
		if Formaldehyde > -100: 									dd["Formaldehyde"]	= round(Formaldehyde,2)
		if counter > -100: 											dd["counter"]		= counter 
		if BLEsensorMACs[mac]["batteryLevel"] !="":
			if BLEsensorMACs[mac]["batteryLevel"] >-100:
																	dd["batteryLevel"]	= BLEsensorMACs[mac]["batteryLevel"]
		if rx > -101: 												dd["rssi"]			= int(rx)

		trig = ""
		if abs(temp - BLEsensorMACs[mac]["temp"])  > 0.5: 														trig += "temp/"
		if abs(hum - BLEsensorMACs[mac]["hum"]): 																trig += "hum/"
		if abs(Formaldehyde - BLEsensorMACs[mac]["Formaldehyde"]) > 0.1: 										trig += "formald/"
		if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"] )  > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"  			# send min every xx secs
		trig = trig.strip("/")

		dd["trigger"] = trig

		if doPrint: U.logger.log(20, "mac:{}, temp:{}, hum:{}, form:{}, triggers:{};   nMessages:{}".format(mac, temp, hum, Formaldehyde, trig, BLEsensorMACs[mac]["nMessages"]))

		if BLEsensorMACs[mac]["nMessages"] > 6 and temp > -100.:
			if  trig != "":
					# compose complete message
					checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

					# remember last values
					if doPrint: U.logger.log(20, "mac:{} triggers:{}; updateIndigoTiming:{}; send:{}".format( mac, trig, BLEsensorMACs[mac]["updateIndigoTiming"] ,  dd)  )
					BLEsensorMACs[mac]["lastUpdate"]	= time.time()
					BLEsensorMACs[mac]["counter"]		= counter
					BLEsensorMACs[mac]["temp"]    		= temp
					BLEsensorMACs[mac]["hum"]		 	= hum
					BLEsensorMACs[mac]["Formaldehyde"]	= Formaldehyde
		
		return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""

#################################


#################################
def doTempspike(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	try:
		"""
		id package gives name, used as tag to detect this beacon type 
	    04 3E 27 02 01 00 00   C3 CB 29 B5 D4 FD     1B  02 01 06   0E  08 54 50 33 39 33 53 20 28 43 42 43 33 29   08 FF C2 F8 00 29 22 23 01  
                                                     01  23 45 67   89  01 23 45 67 89 01 23 45 67 89 01 23 45 67   89 01 23 45 67 89 01 23 45
                                                                                                                    01 23 45 67 89 01 23 45 67  
                                                                                                                          01 23 45 67 89 01 23  
                                                                           T  P  3  9  3  S     (  C  B  C  3  )             t1 t0 hh  B                            
	"""
		doPrint 		= False
		if mac == "xxFD:D4:B5:29:CB:C3": doPrint = True
		if mac not in parsedData: return sensor, tx,  ""
		data08 = parsedData[mac]["analyzed"]["code"].get("08","")
		dataFF = parsedData[mac]["analyzed"]["code"].get("FF","")
		out 	= ""
		tag 	= "545033" #39335320284342433329"
		#		=   T P 3
		if data08.find("TP3") !=0: return sensor, tx,  "" 

		dd = {}  # the data dict to be send 

		if doPrint:
			U.logger.log(20, "mac:{}, FF:{}, 08:{} ,".format(mac,dataFF, data08))

		temp 			= BLEsensorMACs[mac]["temp"]
		hum  			= BLEsensorMACs[mac]["hum"]

		val = int(dataFF[2:4],16) + int(dataFF[4:6],16)*256
		if val > 32767: val -= 65536
		temp = round(val / 10.,1) 

		hum = int(dataFF[6:8],16)

		xx = dataFF[9:10]
		if xx == "2":  		BL = 100
		elif xx == "1":  	BL = 50
		elif xx == "0":  	BL = 10
		else:			 	BL = 0
		dd["batteryLevel"]	= BL

		dd["mac"] =	mac
		if temp > -100: 											dd["temp"] 			= round(temp+ BLEsensorMACs[mac]["offsetTemp"],1)
		if hum > -100: 												dd["hum"]			= int(hum + BLEsensorMACs[mac]["offsetHum"])
		if rx > -101: 												dd["rssi"]			= int(rx)

		trig = ""
		if abs(temp - BLEsensorMACs[mac]["temp"]) 			> 0.5:  											trig += "temp/"
		if abs(hum - BLEsensorMACs[mac]["hum"]) 			> 2:  												trig += "hum/"
		if BL !=  BLEsensorMACs[mac]["batteryLevel"] :  														trig += "bat/"
		if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"]) > BLEsensorMACs[mac]["updateIndigoTiming"]:  		trig += "Time"			# send min every xx secs
		trig = trig.strip("/")
		dd["trigger"]			= trig 

		if doPrint: U.logger.log(20, "mac:{}, temp:{}, hum:{}, triggers:{}".format(mac, temp, hum, trig))


		if temp > -100.:
			if  trig !="":
					# compose complete message
					checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

					# remember last values
					if doPrint: U.logger.log(20, "mac:{} triggers:{}; send:{}".format( mac, trig,  dd)  )
					BLEsensorMACs[mac]["trigger"]		= trig
					BLEsensorMACs[mac]["lastUpdate"]	= time.time()
					BLEsensorMACs[mac]["temp"]    		= temp
					BLEsensorMACs[mac]["batteryLevel"]  = BL
					BLEsensorMACs[mac]["hum"]		 	= hum
		
		return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""


#################################
def doThermopro(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	try:

		"""
		id package gives name, used as tag to detect this beacon type 
	    04 3E 27 02 01 00 00   C3 CB 29 B5 D4 FD     1B  02 01 06   0E  08 54 50 33 39 33 53 20 28 43 42 43 33 29   08 FF C2 F8 00 29 22 23 01  
                                                     01  23 45 67   89  01 23 45 67 89 01 23 45 67 89 01 23 45 67   89 01 23 45 67 89 01 23 45
                                                                                                                    01 23 45 67 89 01 23 45 67  
                                                                                                                          01 23 45 67 89 01 23  
                                                                           T  P  3  9  3  S     (  C  B  C  3  )             t1 t0 hh  B                            
	"""
		doPrint 		= False
		if mac == "xxFD:D4:B5:29:CB:C3": doPrint = True
		if mac not in parsedData: return sensor, tx,  ""
		data08 = parsedData[mac]["analyzed"]["code"].get("08","")
		dataFF = parsedData[mac]["analyzed"]["code"].get("FF","")
		if data08.find("TP3") !=0: return sensor, tx,  "" 

		dd = {}  # the data dict to be send 

		if doPrint:
			U.logger.log(20, "mac:{}, FF:{}, 08:{} ,".format(mac,dataFF, data08))

		temp 			= BLEsensorMACs[mac]["temp"]
		hum  			= BLEsensorMACs[mac]["hum"]

		val = int(dataFF[2:4],16) + int(dataFF[4:6],16)*256
		if val > 32767: val -= 65536
		temp = round(val / 10.,1) 

		hum = int(dataFF[6:8],16)

		xx = dataFF[9:10]
		if xx == "2":  		BL = 100
		elif xx == "1":  	BL = 50
		elif xx == "0":  	BL = 10
		else:			 	BL = 0
		dd["batteryLevel"]	= BL

		dd["mac"] =	mac
		if temp > -100: 											dd["temp"] 			= round(temp+ BLEsensorMACs[mac]["offsetTemp"],1)
		if hum > -100: 												dd["hum"]			= int(hum + BLEsensorMACs[mac]["offsetHum"])
		if rx > -101: 												dd["rssi"]			= int(rx)

		trig = ""
		if abs(temp - BLEsensorMACs[mac]["temp"]) 			> 0.5:  											trig += "temp/"
		if abs(hum - BLEsensorMACs[mac]["hum"]) 			> 2:  												trig += "hum/"
		if BL !=  BLEsensorMACs[mac]["batteryLevel"] :  														trig += "bat/"
		if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"]) > BLEsensorMACs[mac]["updateIndigoTiming"]:  		trig += "Time"			# send min every xx secs
		trig = trig.strip("/")
		dd["trigger"]			= trig 

		if doPrint: U.logger.log(20, "mac:{}, temp:{}, hum:{}, triggers:{}".format(mac, temp, hum, trig))

		if temp > -100. and trig !="":
					# compose complete message
					checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

					# remember last values
					if doPrint: U.logger.log(20, "mac:{} triggers:{}; send:{}".format( mac, trig,  dd)  )
					BLEsensorMACs[mac]["trigger"]		= trig
					BLEsensorMACs[mac]["lastUpdate"]	= time.time()
					BLEsensorMACs[mac]["temp"]    		= temp
					BLEsensorMACs[mac]["batteryLevel"]  = BL
					BLEsensorMACs[mac]["hum"]		 	= hum
		
		return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""


#################################
def doBLEthermoBeacon(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	try:
		if mac not in parsedData: return sensor, tx,  ""
		dataFF = parsedData[mac]["analyzed"]["code"].get("FF","")
		"""
		id package gives name, used as tag to detect this beacon type 
		lTot	ll MFG   T  h  e  r  m  o  B  e  a  c  o  n     SlaveConnectionIntervalRange-12    ????????
		17      0D 09   54 68 65 72 6D 6F 42 65 61 63 6F 6E    05 12 18 00 38 01                  02 0A 00 



		long package gives max and min temp and time stamps, not used
		  1F  02 01 06 03 02 F0 FF 17 FF 11 00 00 00 2B 07 00 00 54 E9 C8 01 AF 00 00 00 65 01 A0 11 00 00
		                                                               Tmax- ts--------- Tmin- ts---------

		this package is used here 
		 1  2  3  4    5  6  7  8   9  a  1  2  3  4  5  6  7  8  9  b  1  2  3  4  5  6  7  8  9  c
		1D  02 01 06  03 02 F0 FF  15 FF 11 00 00 00 2B 07 00 00 54 E9 A1 0C 92 01 71 02 19 00 00 00          BC=-68
		1D  02 01 06  03 02 F0 FF  15 FF 11 00 00 00 2B 07 00 00 54 E9 E6 0B B3 01 1E 02 9C 01 00 00  
										 01 23 45 67 89 11 23 45 67 89 21 23 45 67 89 31 23 45 67 89 
		01  23 45 67  89 11 23 45  67 89 21 23 45 67 89 31 23 45 67 89 41 23 45 67 89 51 23 45 67 89 
										    22 
											01 23 45 67 89 11 23 45 67 89 21 23 45 67 89 31 23 45 67 89 
		--- tag ---------------------
									     tp = type 11 = temp + hum 
										    xx xx  always 00 ?? 
												  cc = 00 / 80 if button pressed
												     mac-------------
																	   bb bb  battery voltage in mV
																		     TT TT        /16 
																				   HH HH  / 16
																					     UT UT UT UT uptime in sec since last reset
																	
		06 | 80 if Button is pressed else 00
		08 | mac address
		20 | bb  battery voltage: seems that 3400  in MV > 3000 == 100% 
		24 | TT  temperature    /16 in C
		28 | HH  humidity  /16 in %
		32 | UT  seconds sinse the last reset


	"""
		doPrint =  mac == "xxE9:54:00:00:07:2B"
		tag 	= "11"
		if dataFF.find(tag) != 0 : return sensor, tx,  "" 

		## fixed 2024/12/17, exclude long packages, they have the wrong format 
		ll = 40 # == len("110000002B07000054E9190C5F018A020BFC3300") 
		if len(dataFF) != ll: return sensor, tx,  "" 

		if doPrint:
			U.logger.log(20, "mac:{},sensor:{} data string len:{}, FF:{}".format(mac,sensor, ll,  dataFF))

		temp 			= BLEsensorMACs[mac]["temp"]
		hum  			= BLEsensorMACs[mac]["hum"]
		counter			= BLEsensorMACs[mac]["counter"]

		pp = 6
		buttonPressed  = dataFF[pp:pp+2] == "80"

		pp = 20
		#val = signedIntfrom16(data16[pp])
		val = int(dataFF[pp:pp+2],16) + int(dataFF[pp+2:pp+4],16)*256
		if val > 32767: val -= 65536
		batteryVoltage = val

		pp = 24
		#val = signedIntfrom16(data16[pp])
		val = int(dataFF[pp:pp+2],16) + int(dataFF[pp+2:pp+4],16)*256
		if val > 32767: val -= 65536
		temp = round(val / 16.,1) 

		pp = 28
		#val = signedIntfrom16(data16[pp])
		val = int(dataFF[pp:pp+2],16) + int(dataFF[pp+2:pp+4],16)*256
		if val > 32767: val -= 65536
		hum = int( round(val / 16.,0) )

		pp = 32
		#val = intfrom24(data16[pp])
		val = int(dataFF[pp:pp+2],16) + int(dataFF[pp+2:pp+4],16)*256 + int(dataFF[pp+4:pp+6],16)*256*256 + int(dataFF[pp+6:pp+8],16)*256*256*256
		counter = int(val)

		bl = batLevelTempCorrection(batteryVoltage, temp)
		
		dd = {}  # the data dict to be send 
		dd["mac"] =	mac
		if temp > -100: 											dd["temp"] 			= round(temp+ BLEsensorMACs[mac]["offsetTemp"],1)
		if hum > -100: 												dd["hum"]			= int(hum + BLEsensorMACs[mac]["offsetHum"])
		if counter > -100: 											dd["counter"]		= counter 
		if True:		 											dd["onOff"]			= buttonPressed 
		if bl >-100:
																	dd["batteryLevel"]	= int(bl)
																	dd["batteryVoltage"]= int(batteryVoltage)
		if rx > -101: 												dd["rssi"]			= int(rx)

		trig = ""
		if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])  > BLEsensorMACs[mac]["updateIndigoTiming"]:  trig += "Time/"			# send min every xx secs
		if abs(temp - BLEsensorMACs[mac]["temp"]) 			> 0.5:  											trig += "temp/"
		if abs(hum - BLEsensorMACs[mac]["hum"]) 			> 2:  												trig += "hum/"
		if BLEsensorMACs[mac]["onOff"] != 					buttonPressed:  									trig += "button"
		trig = trig.strip("/")

		if True:		 											dd["trigger"]			= trig 
		if doPrint: U.logger.log(20, "mac:{}, temp:{}, hum:{}, bl:{}, counter:{},  triggers:{}".format(mac, temp, hum, bl, counter, trig))

		BLEsensorMACs[mac]["batteryLevel"]  = bl 
		if temp > -100.:
			if  trig !="":
					# compose complete message
					checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

					# remember last values
					if doPrint: U.logger.log(20, "mac:{} triggers:{}; send:{}".format( mac, trig,  dd)  )
					BLEsensorMACs[mac]["trigger"]		= trig
					BLEsensorMACs[mac]["lastUpdate"]	= time.time()
					BLEsensorMACs[mac]["counter"]		= counter
					BLEsensorMACs[mac]["temp"]    		= temp
					BLEsensorMACs[mac]["hum"]		 	= hum
					BLEsensorMACs[mac]["onOff"]		 	= buttonPressed
					BLEsensorMACs[mac]["batteryLevel"]  = bl 
					BLEsensorMACs[mac]["batteryVoltage"] = batteryVoltage 
		
		return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		



	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""

#################################
def tralingAv(sensor, mac, avType, retVal):
	global BLEsensorMACs
	try:
		BLEsensorMACs[mac][avType].append(retVal)
		BLEsensorMACs[mac][avType].pop(0)
		yy = 0
		nn = 0.
		#U.logger.log(20, " mac:{}  avType:{}; retVal:{}; BLEsensorMACs: {} ".format( mac, avType, retVal, BLEsensorMACs[mac][avType])  )

		#build averages and exclude max and min values, only works for nn >2

		maxV = max(BLEsensorMACs[mac][avType])
		minV = min(BLEsensorMACs[mac][avType])
		mm   = len(BLEsensorMACs[mac][avType])

		for xx in BLEsensorMACs[mac][avType]:
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
def doBLEiSensor(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors



	""" 
 manufacturer  KAIPULE 

format:
																							
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
		batL = ""
		doPrint = mac in ["xxxB8:7C:6F:1A:D9:65"]
		if mac not in parsedData: return sensor, tx,  batL
		data08 = parsedData[mac]["analyzed"]["code"].get("08","")
		dataFF = parsedData[mac]["analyzed"]["code"].get("FF","")
		if len(dataFF) < 16: return sensor, tx,  batL
		llFF = len(dataFF)//2
#				   0123456789  1123456789213456 78931234567894123456
#		           0201060908    iSensor        xxFF1065D91A360201A1

		sensorName 	= data08  ## on off sensor
		if   len(dataFF) == 8*2:	sensorType = "onOff" 
		elif len(dataFF) == 15*2:	sensorType = "tempHum" 
		else: 						sensorType = "" 

		trig = "" 
		deviceByte			= intFrom8(dataFF,8)
		typeID				= deviceByte & 0b00011111
		if    deviceByte &  0b00010000 !=0: remote = True
		else:								remote = False

		#if  doPrint: U.logger.log(20, " mac:{}  deviceByte:{:08b}=={}, d18L:{},d18:{}, typeID:{}, remote:{}, sensorType:{}, ".format( mac,  deviceByte, deviceByte,  len(dataFF) , dataFF, typeID, remote, sensorType, ) )

		if sensorType == "": return sensor, tx,  batL
		


		fastSwitchBotPress = "" 

		if sensorType == "tempHum" : 
				out =""
				for ii in range(0,len(dataFF),2):
					out += dataFF[ii:ii+2]+" "
				firmWare	= intFrom8(dataFF,0)
				devId1		= intFrom8(dataFF,2)
				devId2		= intFrom8(dataFF,4)
				devId3		= intFrom8(dataFF,6)
				eventData 	= intFrom8(dataFF,10)
				counter		= intFrom8(dataFF,12)
				cData		= intFrom8(dataFF,14)
				temp1   	= intFrom8(dataFF,16)
				temp2   	= intFrom8(dataFF,18)
				hum1	   	= intFrom8(dataFF,20)
				hum2	   	= intFrom8(dataFF,22)
				empty1	   	= intFrom8(dataFF,24)
				empty2	   	= intFrom8(dataFF,26)
				empty3	   	= intFrom8(dataFF,28)
				checkSum	= intFrom8(dataFF,30)
				checkSumCalc= (firmWare + devId1 + devId2 + devId3 + deviceByte + eventData + counter + cData + temp1 + temp2 +hum1 + hum2 + empty1 + empty2 + empty2) & 255 # only one byte
						
				temp   		= float(temp1)
				if temp > 127: temp -= 256
				temp 		+= temp2/256. + BLEsensorMACs[mac]["offsetTemp"]

				hum 		= float(hum1)
				if hum > 127: hum -= 256
				hum 		+= hum2/256.+ BLEsensorMACs[mac]["offsetHum"] +0.5

				sendsAlive	= eventData & 0b00001000 != 0
				lowVoltage	= eventData & 0b00000100 != 0
				alarm		= eventData & 0b00000010 != 0
				tampered	= eventData & 0b00000001 != 0
				batL = 10 if lowVoltage else 100
				sensorType = "undefined"
				if    typeID == 0b00001100: sensorType = "TempHum"
				else: return sensor, tx,  batL

				#U.logger.log(20, " mac:{} counter:{}, hum:{:5.2f}; temp:{:9.3f}; sendsAlive:{}, lowVoltage:{}, alarm:{}, tampered:{}, checkSum:{}, csCalc:{},  hex:{}".format( mac, counter, hum, temp, sendsAlive, lowVoltage, alarm, tampered, checkSum, checkSumCalc, out)  )
				if  sensorType == "TempHum":
					dd = {   # the data dict to be send 
							"lowVoltage": 	lowVoltage,
							"batterylevel": batL,
							"temp": 		round(temp,2),
							"hum": 			int(hum),
							"tampered": 	eventData & 0b00000001 != 0,
							"counter": 		counter, # changes only when pressed twice or ~1 sec after the last
							"sensorType": 	sensorType,
							"sendsAlive": 	sendsAlive,
							"mac": 			mac,
							"rssi":			int(rx)
					}

				
				if False and counter != BLEsensorMACs[mac]["counter"]: 													trig += "count/" 			# send min every xx secs
				if abs(temp - BLEsensorMACs[mac]["temp"]) > 0.5: 														trig += "temp/"
				if abs(hum - BLEsensorMACs[mac]["hum"]) > 1: 															trig += "hum/"
				if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]:		trig += "Time" 			# send min every xx secs
				trig = trig.strip("/")
				if  trig != "":
					dd["trigger"] = trig
					# compose complete message
					checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

					# remember last values
					BLEsensorMACs[mac]["lastUpdate"] = time.time()
					BLEsensorMACs[mac]["counter"]    = counter
					BLEsensorMACs[mac]["temp"]    	 = temp
					BLEsensorMACs[mac]["hum"]    	 = hum

				else:
					return sensor, tx,  batL		


		elif sensorType == "onOff": 
			firmWare	= intFrom8(dataFF,0)
			devId1		= intFrom8(dataFF,2)
			devId2		= intFrom8(dataFF,4)
			devId3		= intFrom8(dataFF,6)
			eventData 	= intFrom8(dataFF,10)
			counter		= intFrom8(dataFF,12)
			checkSum	= intFrom8(dataFF,14)

			checkSumCalc 		= (firmWare + devId1 + devId2 + devId3 + deviceByte + eventData + counter) & 255 # only one byte

			if False and checkSum != checkSumCalc:
				U.logger.log(20, " mac:{}   checksum error  hex:{}, chs:{} chscalc:{}".format( mac, dataFF, checkSum, checkSumCalc) )
				U.sendURL( {"sensors":{sensor: {BLEsensorMACs[mac]["devId"]: {"badsensor":True, "rssi":int(rx)} }}} )
				return sensor, tx,  "" 


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

			if  doPrint: U.logger.log(20, " mac:{}   typeID:{}, eventData:{:08b}, sensorType:{}, remote:{}".format( mac, typeID, eventData, sensorType, remote) )

			if sensorType in ["DoorBell", "RemoteKeyFob", "RemoteSwitch",  "Door", "WaterLevel",  "Panic"]:
				if 	tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])  > 1.: trig += "remote/"
				if  sensorType == "DoorBell":
					lowVoltage	= eventData & 0b00000100 != 0
					batL = 10 if lowVoltage else 100
					dd = {   # the data dict to be send 
							"lowVoltage": 	lowVoltage,
							"batterylevel": batL,
							"onOff": 		eventData & 0b00000010 != 0,
							"tampered": 	eventData & 0b00000001 != 0,
							"counter": 		counter, # changes only when pressed twice or ~1 sec after the last
							"sensorType": 	sensorType,
							"sendsAlive": 	sendsAlive,
							"mac": 			mac,
							"rssi":			int(rx)
					}
					if eventData & 0b00000010 != 0: fastSwitchBotPress =  "on"
					else: 							fastSwitchBotPress =  "off"
				elif  sensorType == "RemoteKeyFob":
					anybutton = eventData & 0b00001000 != 0 or eventData & 0b00000100 != 0 or eventData & 0b00000010 != 0 or eventData & 0b00000001 != 0
					dd = {   # the data dict to be send 
							"SOS": 			eventData & 0b00001000 != 0,
							"home": 		eventData & 0b00000100 != 0,
							"away": 		eventData & 0b00000010 != 0,
							"disarm": 		eventData & 0b00000001 != 0,
							"counter": 		counter, # not used always 1
							"sensorType": 	sensorType,
							"sendsAlive": 	sendsAlive, # should be false always
							"mac": 			mac,
							"rssi":			int(rx)
					}
					if anybutton: fastSwitchBotPress =  "on"
					else: 		  fastSwitchBotPress =  "off"
				elif sensorType == "RemoteSwitch":
					dd = {   # the data dict to be send 
							"state": 		eventData & 0b00000100 != 0,
							"onOff": 		eventData & 0b00000010 != 0,
							"counter": 		counter,
							"sensorType": 	sensorType,
							"sendsAlive": 	sendsAlive,
							"mac": 			mac,
							"rssi":			int(rx)
					}
					if eventData & 0b000000010 != 0: fastSwitchBotPress = "on"
					else: 						 	 fastSwitchBotPress = "off"
				elif sensorType == "Door":
					dd = {   # the data dict to be send 
							"state": 		(eventData & 0b00000100) != 0,
							"onOff": 		(eventData & 0b00000010) == 0, # this one is on if disconnected, off if mag is close, reversing logic 
							"counter": 		counter,
							"sensorType": 	sensorType,
							"sendsAlive": 	sendsAlive,
							"mac": 			mac,
							"rssi":			int(rx)
					}
					if eventData & 0b000000010 != 0: fastSwitchBotPress = "on"
					else: 						 	 fastSwitchBotPress = "off"
				elif sensorType == "WaterLevel":
					dd = {   # the data dict to be send 
							"onOff": 		(eventData & 0b00000010) == 0,
							"counter": 		counter,
							"sensorType": 	sensorType,
							"sendsAlive": 	sendsAlive,
							"tampered": 	eventData & 0b00000001 != 0,
							"mac": 			mac,
							"rssi":			int(rx)
					}
					if eventData & 0b000000010 != 0: fastSwitchBotPress = "on"
					else: 						 	 fastSwitchBotPress = "off"
					if  doPrint: U.logger.log(20, " mac:{}  in waterlevel;".format(mac))

				elif  sensorType == "Panic":
					dd = {   # the data dict to be send 
							"onOff": 		eventData & 0b00000010 != 0,
							"counter": 		counter,
							"sensorType": 	sensorType,
							"sendsAlive": 	sendsAlive,
							"mac": 			mac,
							"rssi":			int(rx)
						}
					if eventData & 0b000000010 != 0: fastSwitchBotPress = "on"

			else: # all other type onOff
					lowVoltage	= eventData & 0b00000100 != 0
					batL = 10 if lowVoltage else 100
					dd = {   
							"bits": 		"{:b}".format(eventData),
							"alive": 		eventData & 0b00001000 != 0,
							"lowVoltage": 	lowVoltage,
							"batterylevel": batL,
							"onOff": 		eventData & 0b00000010 != 0,
							"tampered": 	eventData & 0b00000001 != 0,
							"counter": 		counter,
							"sensorType": 	sensorType,
							"sendsAlive": 	sendsAlive,
							"mac": 			mac,
							"rssi":			int(rx)
						}
					if eventData & 0b000000010 != 0: fastSwitchBotPress = "on"
					else: 						 	 fastSwitchBotPress = "off"


		#U.logger.log(20, " .... checking  data:{} counter hex:{}".format( dd , hexData[42:42+5]) )
		if counter != BLEsensorMACs[mac]["counter"]:		 													trig += "count"# send min every xx secs
		if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"			# send min every xx secs

		if  doPrint: U.logger.log(20, " mac:{}  sending dd:{};".format(mac, dd))

		trig = trig.strip("/")
		if  trig != "":
			dd["trigger"] = trig.strip("/")   
			dd["mac"] = mac   
			# compose complete message
			checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
			#U.logger.log(20,"sensor pressed {}-{} :{}".format(mac,sensor, dd))
			# remember last values
			BLEsensorMACs[mac]["lastUpdate"] = time.time()
			BLEsensorMACs[mac]["counter"]    = counter

			if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)

		return sensor, tx, batL

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  batL


#################################
def doBLEmeeblue(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors



	""" 
 manufacturer  KAIPULE 

format:
																							
- on/off sensors 
									pos#      01   23 45 67   89 01 23 45    67 89 01 23   45 67 89 01 23 45   67 89  01 23 45 67 89   01 23   45 67 89 01 23   RSSI
									pos#                                           01 23   45 67 89 01 23 45   67 89  01 23 45 67 89   01 23   45 67 89 01 23   RSSI
											  1F   02 01 06   03 03 00 40    17 16 00 40   F5 79 3C 4E 7D 50   43 0C  D3 5B 76 E2 E0   1C 52   2D8466FFFFBC																													 
																			 		       MAC--------------   bat    ?? ?? ?? ?? ??   count   ????????????


																			08 09 6D 65 65 62 6C 75 65

	"""

	try:
		bl = ""
		doPrint = mac == "xxF5:79:3C:4E:7D:50"
		if mac not in parsedData: return sensor, tx,  ""
		data16 = parsedData[mac]["analyzed"]["code"].get("16","")
		data08 = parsedData[mac]["analyzed"]["code"].get("08","")


		TagPos1 	= data16.find("0040") == 0  						# regular msg, get battery voltage
		TagPos2 	= data08.find("meeblue") == 0						# is button on, is string meeblue
		if doPrint: U.logger.log(20,"mac:{}, -0- TagPos1:{} , TagPos2:{}, ".format(mac, TagPos1, TagPos2))
		#                                        i S e n s o r _
		if not TagPos1  and not TagPos2: return sensor, tx,  bl

		if TagPos1:
			# REGULAR MESSAGE, get battery voltage and calc bat level	
			batVoltage = int(data16[18:20] + data16[16:18],16)
			BLEsensorMACs[mac]["batteryVoltage"]   = batVoltage

			bl = batLevelTempCorrection(batVoltage,23)
			BLEsensorMACs[mac]["batteryLevel"]    = bl

			if time.time() - BLEsensorMACs[mac]["lastUpdate2"] > 20: # send off msg and batterylevel voltage as part of normal msg packet 
				dd = {   # the data dict to be send 
								"mac": 				mac,
								"onOff": 			False,
								"trigger": 			"Time" ,
								"batteryVoltage": 	BLEsensorMACs[mac]["batteryVoltage"],
								"batteryLevel": 	BLEsensorMACs[mac]["batteryLevel"],
								"rssi":				int(rx)
						}
				if doPrint: U.logger.log(20,"mac:{}, -2- dd:{}".format(mac, dd))
				checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
				BLEsensorMACs[mac]["lastUpdate2"] = time.time()

			return sensor, tx,  bl

		if doPrint: U.logger.log(20,"mac:{},  DT:{}".format(mac, time.time() - BLEsensorMACs[mac]["lastUpdate1"]))


		if time.time() - BLEsensorMACs[mac]["lastUpdate1"] < 15.5: return sensor, tx,  "" # on messages come for about 14.8 secs, so do 15.5 secs no ON messages

		if TagPos2:
			dd = {   # the data dict to be send 
							"mac": 				mac,
							"onOff": 			True,
							"trigger": 			"buttonp-press" ,
							"batteryVoltage": 	BLEsensorMACs[mac]["batteryVoltage"],
							"batteryLevel": 	BLEsensorMACs[mac]["batteryLevel"],
							"rssi":				int(rx)
					}
			if doPrint: U.logger.log(20,"mac:{}, -3- dd:{}".format(mac, dd))
			checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
			BLEsensorMACs[mac]["lastUpdate1"] = time.time()
			BLEsensorMACs[mac]["lastUpdate2"] = time.time()

			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"] 

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  bl



#################################
def doBLEiBSxx( mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs
	global fastBLEReaction

	try:
		HexStr0 				= hexData[12:] # skip mac  + length
		if len(HexStr0) < 40: 
			return sensor, tx,  ""

		verbose = mac == "xxCF:85:DE:C6:90:55"

		posFound, dPos, subtypeOfBeacon =  testComplexTag(HexStr0, "iBSxx", mac, macplain, macplainReverse,  calledFrom="doBLEiBSxx" )
		#U.logger.log(20, "mac:{}   posFound:{}, dPos:{}, subtypeOfBeacon:{}, HexStr:{}".format(mac, posFound, dPos, subtypeOfBeacon, HexStr0) )	

		if dPos !=0:
			return sensor, tx,  ""

		infostart 			= 7*2   #  
		HexStr				= hexData[infostart:]
		devId				= BLEsensorMACs[mac]["devId"]
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
		#if mac =="00:81:F9:86:02:52": U.logger.log(20,"{} bat v:{:4}, batL:{:3}, Bstring:{}".format(mac, batteryVoltage, batteryLevel, Bstring))

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
		if verbose: U.logger.log(20, "{} sensor:{:10s}, iBSType:{:10s},  pFormat:{:4s}, st:{:2s}, HexStr:{}".format(mac, sensor, iBSType, pFormat, st, HexStr) )	
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

		trig 				= ""
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
			if BLEsensorMACs[mac]["onOff1"] 	!= button: trig += "button/"
			if BLEsensorMACs[mac]["onOff2"] 	!= moving: trig += "moving/"
			if BLEsensorMACs[mac]["onOff3"] 	!= hallSensor: trig += "hallSensor/"
			if BLEsensorMACs[mac]["onOff4"] 	!= freeFall: trig += "freeFall/"
			if BLEsensorMACs[mac]["onOff5"] 	!= PIR: trig += "pir/"
			if BLEsensorMACs[mac]["onOff6"] 	!= IR: trig += "ir/"
			fastSwitchBotPress = "on" if onOff else "off"
			if verbose: U.logger.log(20, "mac:{}   HexStr[p:p+2]:{}, old01:{};  new01:{}, trig:{}".format(mac, HexStr[p:p+2], BLEsensorMACs[mac], onOff, trig ) )

		elif  sensor == "BLEiBS03G": 	
			if BLEsensorMACs[mac]["onOff"]  != onOff: trig += "switch/"
			data[sensor][devId]["onOff"] = onOff
			if BLEsensorMACs[mac]["onOff1"] != onOff1: trig += "switch1/"
			data[sensor][devId][sensor]["onOff1"] = onOff1

		elif  sensor == "BLEiBS03T": 	
			p = sens1Pos # start of temp
			temp = ( signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100. + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multTemp"]
			if abs(BLEsensorMACs[mac]["temp"] - temp) >= BLEsensorMACs[mac]["updateIndigoDeltaTemp"]: trig +=  "temp/"
			data[sensor][devId]["temp"] 		= temp 
			batteryLevel 						= batLevelTempCorrection(batteryVoltage, temp)
			data[sensor][devId]["batteryLevel"] = batteryLevel


		elif  sensor == "BLEiBS03TP": 	
			p = sens1Pos# start of temp
			temp = (signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100. + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multTemp"]
			if abs(BLEsensorMACs[mac]["temp"] - temp) >= BLEsensorMACs[mac]["updateIndigoDeltaTemp"]: trig +=  "temp/"
			data[sensor][devId]["temp"] 		= temp 
			batteryLevel 						= batLevelTempCorrection(batteryVoltage, temp)
			data[sensor][devId]["batteryLevel"] = batteryLevel
			p = sens2Pos# start of temp probe
			AmbientTemperature = signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100.
			if abs(BLEsensorMACs[mac]["AmbientTemperature"] - AmbientTemperature) >=1: trig +=  "Ambient-Temp/"
			data[sensor][devId]["AmbientTemperature"] = AmbientTemperature


		elif  sensor == "BLEiBS01T": 	
			data[sensor][devId]["onOff"] = button

			p = sens1Pos# start of temp
			temp = (signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] )/100. + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multTemp"]
			data[sensor][devId]["temp"] 		= temp 

			batteryLevel 						= batLevelTempCorrection(batteryVoltage, temp)
			data[sensor][devId]["batteryLevel"] = batteryLevel

			p = sens2Pos# start of hum probe
			hum = int( signedIntfrom16( HexStr[p+2:p+4] + HexStr[p:p+2] ) + BLEsensorMACs[mac]["offsetHum"] +0.5 )
			data[sensor][devId]["hum"] = hum

			if abs(BLEsensorMACs[mac]["temp"] - temp) >= 1: trig +=  "temp/"
			if abs(BLEsensorMACs[mac]["hum"] -   hum) >1 :  trig +=  "hum/"
			if onOff != BLEsensorMACs[mac]["onOff"] :		trig +=  "onOff"
			if verbose: U.logger.log(20, "mac:{}   sens1Pos:{}, sens2Pos:{}, Bstring:{}, iVAL:{:016b}, batteryVoltage:{}  onOff:{}, trig:{}; data:{}".format(mac, sens1Pos, sens2Pos, Bstring, iVAL,batteryVoltage,  onOff, trig, data[sensor][devId]) )
			fastSwitchBotPress = "on" if onOff else "off"


		elif  sensor in["BLEiBS01RG","BLEiBS03RG"]:
			p = accelPos # there are 3 measuremenst send, take the middle 
			#U.logger.log(20, "{} hex[p]:{} x:{}, y:{},z:{} ".format(mac,HexStr[p:], HexStr[ p :p+4 ],HexStr[ p+4 :p+8 ],HexStr[ p+8 :p+12 ]) )
			accelerationX 	= signedIntfrom16(hexData[p+2 :p+4 ]+HexStr[p  :p+2 ])*(4) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationY 	= signedIntfrom16(hexData[p+6 :p+8 ]+HexStr[p+4:p+6 ])*(4) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationZ 	= signedIntfrom16(hexData[p+10:p+12]+HexStr[p+8:p+10])*(4) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)
		# make deltas compared to last send 
			dX 			= abs(BLEsensorMACs[mac]["accelerationX"]		- accelerationX)
			dY 			= abs(BLEsensorMACs[mac]["accelerationY"]		- accelerationY)
			dZ 			= abs(BLEsensorMACs[mac]["accelerationZ"]		- accelerationZ)

			dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
			deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000
			trigAccel 	= dTot			> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"] 	# acceleration change triggers 
			trigDeltaXZY= deltaXYZ		> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]			# acceleration-turn change triggers 
			if trigAccel:    							trig += "accel/"
			if trigDeltaXZY: 							trig += "deltaXYZ/"
			if onOff != BLEsensorMACs[mac]["onOff"]:	trig += "onOff/" 
			data[sensor][devId]["accelerationTotal"] 		= int(accelerationTotal)
			data[sensor][devId]["accelerationX"] 			= int(accelerationX)
			data[sensor][devId]["accelerationY"] 			= int(accelerationY)
			data[sensor][devId]["accelerationZ"] 			= int(accelerationZ)
			data[sensor][devId]["accelerationXYZMaxDelta"]  = int(deltaXYZ)
			data[sensor][devId]["accelerationVectorDelta"]  = int(dTot)
			data[sensor][devId]["onOff"]  					= onOff
			data[sensor][devId]["onOff1"]  					= onOff1
			if verbose: U.logger.log(20, "{} Bstring:{}, iVAL:{:016b},  onOff:{}, trig:{}; data:{}".format(mac,Bstring, iVAL,  onOff, trig, data[sensor][devId]) )
			fastSwitchBotPress = "on" if onOff or onOff1 else "off"

		else:
			return sensor, tx,  ""

		# check if we should send data to indigo
		if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])  > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"  			# send min every xx secs
		#U.logger.log(20, "mac:{}    HexStr20-23:{}- 24-26{} irOnOff:{}, batteryVoltage:{}".format(mac, HexStr[20:24],  HexStr[24:26], irOnOff, batteryVoltage) )

		#U.logger.log(20, "{}   trigTime:{},  trig:{}, deltaTime:{};  updateIndigoTiming:{}, dada:{}".format(mac, trigTime, trig, deltaTime, BLEsensorMACs[mac]["updateIndigoTiming"], data[sensor][devId]) )
		trig = trig.strip("/")
		if  trig != "":
			data[sensor][devId]["trigger"]  							= trig.strip("/")
			checkIfDelaySend({"sensors":data})
			# save last values to comapre at next round, check if we should send if delta  > paramter
			BLEsensorMACs[mac]["lastUpdate"] 					= time.time()
			BLEsensorMACs[mac]["onOff"] 	 					= onOff#  = ALL OR JUST BUTTON 
			BLEsensorMACs[mac]["onOff1"] 	 					= onOff1# == button
			BLEsensorMACs[mac]["onOff2"] 	 					= moving
			BLEsensorMACs[mac]["onOff3"] 	 					= hallSensor
			BLEsensorMACs[mac]["onOff4"] 	 					= freeFall
			BLEsensorMACs[mac]["onOff5"] 	 					= PIR
			BLEsensorMACs[mac]["onOff6"] 	 					= IR
			BLEsensorMACs[mac]["temp"] 	 	 					= temp
			BLEsensorMACs[mac]["hum"] 	 	 					= hum
			BLEsensorMACs[mac]["AmbientTemperature"] 			= AmbientTemperature
			BLEsensorMACs[mac]["accelerationX"] 				= accelerationX
			BLEsensorMACs[mac]["accelerationY"] 				= accelerationY
			BLEsensorMACs[mac]["accelerationZ"] 				= accelerationZ

			if fastSwitchBotPress != "": doFastSwitchBotPress(mac, fastSwitchBotPress)

		return sensor, tx,  batteryLevel
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return sensor, tx,  ""



#################################
def doBLEiTrack( mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs
	global fastBLEReaction, trackMacNumber
	global bleServiceSections, bleServiceSectionsReverse, parsedData


	try:

		# 01 23 45 67   89 01 23 45   67  89 01 23 45 67 89 01 23 45 67 89   01 23 45 67 89 01 23 45  position characters
		#  1  2  3  4    5  6  7  8    9  10 11 1  13 14 15 16 17 18 19 20   21 22 23 24 25 26 27 28  position bytes 

		# after beep
		# 1B 02 01 05   03 02 02 18   0B  FF 4B 4D 00 6C BF C7 3B C5 DD 6D   07 09 69 54 72 61 63 6B  BC
		# IGNORE APP OFF:                             r MAC ----------- cc
		# 1B 02 01 05   03 02 02 18   0B  FF 4B 4D 42 28 89 F9 A7 DD E2 65         i   T  r  a  c  k    
		# 1B 02 01 06   03 02 02 18   0B  FF 4B 4D 42 28 89 F9 A7 DD E2 66   07 09 69 54 72 61 63 6B  BC
		# LL ll tp fl   ll tp
		#    id1---     id2--------
		#          wx                 ll           yz                        ll tp
		# regular on / button press:
		# 1B 02 01 05   03 02 02 18   0B  FF 4B 4D 30 EC 36 5E 3F CA DB 64   07 09 69 54 72 61 63 6B  BC
		# regular off 
		# 1B 02 01 06   03 02 02 18   0B  FF 4B 4D 42 28 89 F9 A7 DD E2 65   07 09 69 54 72 61 63 6B  C5
		#          wx                 ll  TP       yz                   bat  ll TP  i  T  r  a  c  k
		#                             11  FF ---------------------------??   07 09 -----------------
		# ll = length of next section 
		# TP = type, 
		#    FF = manufacturing specific .. the 2 bytes for ID: 4B 4D = itrack, rest is coded data 
		#    01 = flag
		#    09 = name,  convert hex to ascii
		#					 beep: x=5, y=0 
		# 					 normal off: x=5,6, z=2
		#   				 back from app rule (a) 30+sec : x=5, z=2
		#   				 back from app rule after (a) off : x=6, z=2
		#   				 y= type of device 1..F

		if mac not in parsedData: return sensor, tx,  ""
		if "analyzed" not in parsedData[mac]: return sensor, tx,  ""
		NameData 		=  parsedData[mac]["analyzed"]["code"].get("09","") # 69 54 72 61 63 6B  BC
		if NameData != "iTrack": 	return sensor, tx,  "" 

		mfgData  		=  parsedData[mac]["analyzed"]["code"].get("FF","") 
		if len(mfgData) < 20: 		return sensor, tx,  "" 
		itrackID 		= mfgData[0:4] # == 4B 4D
		rMAC     		= mfgData[6:18] # == 28 89 F9 A7 DD E2
		bat      		= mfgData[18:20] # == 28 89 F9 A7 DD E2
		bPressed		= mfgData[5:6]   # == z
		typeCode 		= mfgData[4:5]   # == y
		backFromConnect	= typeCode == "0" # ==y
		flagData 		= parsedData[mac]["analyzed"]["code"].get("01","") 

		#if itrackID != "4B4D"   	return sensor, tx,  "" 
		if rMAC != macplainReverse:	return sensor, tx,  "" 

		infostart 			= 12 #EC365E3FCADB1B02   #  
		HexStr				= hexData[12:]

		doprint = mac in findMAC
		if  doprint:
			U.logger.log(20, "mac:{} {}, rMAC:{}, itrackID:{},  flagData:{}, bat:{}, bPressed:{}, typeCode:{} NameData:{}, hex:{}".format(mac, datetime.datetime.now().strftime("%H:%M:%S.%f")[:-5],  rMAC, itrackID,  flagData, bat, bPressed, typeCode, NameData, HexStr))

		batLevel = intFrom8(bat,0)

		devId				= BLEsensorMACs[mac]["devId"]
		data   = {sensor:{devId:{}}}


		#if bPressed == "0" and flagData[1] == "5" and not backFromConnect:	onOff = True

		if bPressed == "0" and not backFromConnect:	onOff = True
		else:										onOff = False

		stateOfBeacon = flagData + "-" + bPressed
		if backFromConnect: stateOfBeacon += "-back_from_connect_state"
		devType = iTrackDevTypes.get(typeCode,typeCode)

		trig 				= ""
		if BLEsensorMACs[mac]["trigx"]  != stateOfBeacon:		trig = "stateOfBeacon"
		if BLEsensorMACs[mac]["onOff"]  != onOff:				trig = "onOff"
		if BLEsensorMACs[mac]["lastUpdate1"] == 0:				trig = "onOff"

		# check if we should send data to indigo
		deltaTime 			= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])
		trigTime 			= deltaTime   > BLEsensorMACs[mac]["updateIndigoTiming"]  			# send min every xx secs
		data[sensor][devId]["onOff"] =  onOff
		data[sensor][devId]["stateOfBeacon"] =  stateOfBeacon
		if not backFromConnect:
			data[sensor][devId]["devType"] =  devType

		data[sensor][devId]["batteryLevel"] =  batLevel
		if  doprint: U.logger.log(20, "mac:{} trig:{},  data:{},".format(mac, trig, data[sensor][devId] ))

		if onOff:
			if BLEsensorMACs[mac]["lastUpdate2"] == 0:
				BLEsensorMACs[mac]["lastUpdate3"] 	= time.time()
			BLEsensorMACs[mac]["lastUpdate2"] 	+=1
			if  doprint: U.logger.log(20, "mac:{} {}, onOff:{:1}, count:{:3}\n".format(mac, datetime.datetime.now().strftime("%H:%M:%S.%f")[:-5], onOff, BLEsensorMACs[mac]["lastUpdate2"]))
		else:
			if  doprint and BLEsensorMACs[mac]["lastUpdate2"] !=0:
				U.logger.log(20, "mac:{} {}, onOff:{:1}, count:{:3}\n".format(mac, datetime.datetime.now().strftime("%H:%M:%S.%f")[:-5], onOff, BLEsensorMACs[mac]["lastUpdate2"]))
			BLEsensorMACs[mac]["lastUpdate2"] 	= 0


		if  trigTime or trig != "":
			if trigTime:	 trig  += "/Time"
			data[sensor][devId]["trigger"]  					= trig.strip("/")
			checkIfDelaySend({"sensors":data})
			# save last values to comapre at next round, check if we should send if delta  > paramter
			BLEsensorMACs[mac]["lastUpdate"] 					= time.time()
			BLEsensorMACs[mac]["lastUpdate1"] 					= time.time()
			BLEsensorMACs[mac]["onOff"] 	 					= onOff#  = ALL OR JUST BUTTON 
			BLEsensorMACs[mac]["trigx"] 	 					= stateOfBeacon#  = ALL OR JUST BUTTON 
			BLEsensorMACs[mac]["batteryLevel"] 	 				= batLevel#  = ALL OR JUST BUTTON 

		return sensor, tx,  batLevel
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return sensor, tx,  ""



#################################
def doBLESatech( mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs
	"""
Assuming the following BL:E messages (starting directly afetr the reverse MAC #)
HexStr:1A  020106  0303E1FF  12 16 E1 FF A1 03 5D 00 00 00 00 00 F2  DD 04 BD 1D D4 F7  B2 #accel
HexStr:18  020106  0303E1FF  10 16 E1 FF A1 04 5D 1A 17 34 56 DD 04 BD 1D D4 F7  AF  # temp
HexStr:18  020106  0303E1FF  10 16 E1 FF A1 08 5D DD 04 BD 1D D4 F7 50 4C 55 53  AD  # # battery % and PLUS name
HexStr:17  020106  0303AAFE  11 16 AA FE 20 00 0B6D  16 00 00 00 08 D4 00 00 0D  E8  B7 # gen info
	   01  234567  89112345  67 89 21 23 45 67 89 31 23 45 67 89 

HexStr:0E  020106            0A 09 42 65 61 63 6F 6E 66 69 67 == Beaconfig

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
		if mac not in parsedData: return sensor, tx,  ""
		if "analyzed" not in parsedData[mac]: return sensor, tx,  ""
		data16 		=  parsedData[mac]["analyzed"]["code"].get("16","") 

		devId				= BLEsensorMACs[mac]["devId"]

		subType = ""
		if     data16.find("E1FFA104") == 2:	subType 	= "tempHum"
		elif   data16.find("E1FFA103") == 2:	subType 	= "accel"
		elif   data16.find("AAFE2000") == 2:	subType 	= "genInfo"
		elif   data16.find("E1FFA1FF") == 2:	subType 	= "sos"
		else:  return sensor, tx,  ""

		data   = {sensor:{devId:{}}}
		data[sensor][devId] = {"type":sensor,"mac":mac,"rssi":float(rx),"txPower":-60}

		if BLEsensorMACs[mac]["SOS"] and subType != "sos":
			data[sensor][devId]["trigger"] = "SOS_Off"
			checkIfDelaySend({"sensors":data})
			BLEsensorMACs[mac]["SOS"] 	= False

		if subType == "":
			return sensor, tx,  ""


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
		trig 					= ""


		if  subType == "sos": 	
			#U.logger.log(20, "mac:{}   sos:  HexStr:{}".format(mac, HexStr[2:] ) )	
			if  not  BLEsensorMACs[mac]["SOS"]:
				data[sensor][devId]["trigger"] = "SOS_button_pressed@"+datetime.datetime.now().strftime("%Y-%m%d-%H:%M:%S")
				checkIfDelaySend({"sensors":data})
			BLEsensorMACs[mac]["SOS"] 	= True
			return sensor, tx,  ""


		elif  subType == "genInfo": 
			dataString 	= data16.split("AAFE2000")[1]  ## + mV-- C- Cp- adC----- secs-strt"
			p = 0; bv	= dataString[p  :p+4];	batteryVoltage 	= int(bv,16)
			p = 4 ;	ct	= dataString[p  :p+4];	chipTemperature	= round(float(int(ct,16))/255.,1)
			p = 8 ;	c	= dataString[p  :p+8];	counter 		= int(c,32)
			p = 16; ss	= dataString[p  :p+8];	secsSinceStart 	= int(ss,32)

			data[sensor][devId]["chipTemperature"] 	= chipTemperature 
			data[sensor][devId]["secsSinceStart"] 	= secsSinceStart 
			data[sensor][devId]["counter"] 			= counter 
			data[sensor][devId]["batteryVoltage"] 	= batteryVoltage
			if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate2"])  > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"			# send min every xx secs
			trig = trig.strip("/")
			if  trig:
				data[sensor][devId]["trigger"]  = trig.strip("/")
				checkIfDelaySend({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac]["lastUpdate2"] 					= time.time()
				BLEsensorMACs[mac]["chipTemperature"] 	 	 		= chipTemperature
				BLEsensorMACs[mac]["secsSinceStart"] 	 	 		= secsSinceStart
				BLEsensorMACs[mac]["counter"] 	 	 				= counter
				BLEsensorMACs[mac]["batteryVoltage"] 	 	 		= batteryVoltage

		elif  subType == "tempHum": 	
			dataString 	= data16.split("E1FFA1")[1][2:]
			dataString 	= dataString.split(macplain)[0]
			p = 2; 	temp = round(signedIntfrom16(dataString[p :p+4]) /255.,2)   + BLEsensorMACs[mac]["offsetTemp"]
			p = 6;	hum  = int(signedIntfrom16(dataString[p :p+4]) /255. + 0.5) + BLEsensorMACs[mac]["offsetHum"]
			if abs(BLEsensorMACs[mac]["temp"] - temp) >= BLEsensorMACs[mac]["updateIndigoDeltaTemp"]: 	trig +=  "temp/"
			if abs(BLEsensorMACs[mac]["hum"] - hum)   >= 2: 													trig +=  "hum/"
			batteryLevel 	= int(dataString[0:2],16)
			data[sensor][devId]["temp"] 		= temp 
			data[sensor][devId]["hum"] 			= hum 
			data[sensor][devId]["batteryLevel"] = batteryLevel

			if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate2"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"			# send min every xx secs
			trig = trig.strip("/")
			if  trig:
				data[sensor][devId]["trigger"]  = trig.strip("/")
				checkIfDelaySend({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac]["lastUpdate1"] 					= time.time()
				BLEsensorMACs[mac]["temp"] 	 	 					= temp
				BLEsensorMACs[mac]["hum"] 	 	 					= hum

		elif  subType  == "accel":
			dataString 	= data16.split("E1FFA1")[1][2:]
			dataString 	= dataString.split(macplain)[0]
			p = 2 
			accelerationX 	= signedIntfrom16(dataString[p  :p+4 ]) *4
			accelerationY	= signedIntfrom16(dataString[p+4:p+8 ]) *4
			accelerationZ 	= signedIntfrom16(dataString[p+8:p+12]) *4
			accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)
		# make deltas compared to last send 
			dX 			= abs(BLEsensorMACs[mac]["accelerationX"]		- accelerationX)
			dY 			= abs(BLEsensorMACs[mac]["accelerationY"]		- accelerationY)
			dZ 			= abs(BLEsensorMACs[mac]["accelerationZ"]		- accelerationZ)

			dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
			deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000
			if dTot			> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"]: 	trig += "accel/" 	# acceleration change triggers 
			if deltaXYZ		> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]:		trig += "deltaXYZ/"			# acceleration-turn change triggers 
			data[sensor][devId]["accelerationTotal"] 		= int(accelerationTotal)
			data[sensor][devId]["accelerationX"] 			= int(accelerationX)
			data[sensor][devId]["accelerationY"] 			= int(accelerationY)
			data[sensor][devId]["accelerationZ"] 			= int(accelerationZ)
			data[sensor][devId]["accelerationXYZMaxDelta"]  = int(deltaXYZ)
			data[sensor][devId]["accelerationVectorDelta"]  = int(dTot)
			trig = trig.strip("/")

			if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate2"] )  > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"			# send min every xx secs
			trig = trig.strip("/")
			if  trig !="":
				data[sensor][devId]["trigger"]  = trig.strip("/")
				checkIfDelaySend({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac]["lastUpdate"] 					= time.time()
				BLEsensorMACs[mac]["accelerationX"] 				= accelerationX
				BLEsensorMACs[mac]["accelerationY"] 				= accelerationY
				BLEsensorMACs[mac]["accelerationZ"] 				= accelerationZ

		return sensor, tx,  batteryLevel


	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return sensor, tx,  ""


#################################
def batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=3000., batteryVoltAt0=2700.):
	try:
		## correction  formula voltage & temp --> level 
		## at >=10C:correction = 0                 --> 100*(VB -2700)/(300)   ==>  > 3000 --> 100%  < 2.7 == 0%
		## at 0C:   1-0.07 = 0.93 * 2700 = 2.5 V --> 100*(VB -2500)/(500)   ==>  > 3000 --> 100%  < 2.5== 0%
		## at -10C: 1-0.14  = 0.86 * 2700 = 2.3 V --> 100*(VB -2.3)/(1110)   ==>  > 3000 --> 100%  < 2.3 == 0%
		##   
		batteryLowVsTemp			= (1. + 0.7*min(0.,(temp-10.)/100.)) * batteryVoltAt0  
		batteryLevel 				= int(min(100.,max(0.,100.* (batteryVoltage - batteryLowVsTemp)/(batteryVoltAt100-batteryLowVsTemp))))
		return batteryLevel
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 0

#################################
def domyBlueT( mac, rx, tx, hexData,sensor):
	global BLEsensorMACs
	return sensor, tx,  ""


#################################
def doBLEapril(mac, macplain, macplainReverse, rx, tx, hexData,sensor):
	global BLEsensorMACs, sensors
	try:
		

		#if   hexData.find("1F020106030359FE171659FEAB0103"+macplainReverse) ==0: sensType = "TAccel"
		#elif hexData.find("1A020106030359FE121659FEAB03"+macplainReverse)   ==0: sensType = "THL"
		#else:						return sensor, tx,  ""

		if "analyzed" not in parsedData[mac]: return sensor, tx,  ""

		data16 = parsedData[mac]["analyzed"]["code"].get("16","") 
		if   data16.find("59FEAB0103"+macplainReverse) == 0: sensType = "TAccel"
		if   data16.find("59FEAB03"+macplainReverse)   == 0: sensType = "THL"
		else:						return sensor, tx,  ""

		if sensType == "TAccel":
			"""  16 adv		        01 23 45 67 89 11 23 45 67 89 21 23 45 67 89 31 23 45 67 89 41 23
  pos        01234567 89112345   67 89 21 23 45 67 89 31 23 45 67 89 41 23 45 67 89 51 23 45 67 89 61 23                  
			 1F020106 030359FE   17 16 59 FE AB 01 03 D9 7E 3D 2E CA D2 5A 00 01 F9 D7 29 04 16 64 00 00 D2 
                                                      rmac------------- tt tt SM xx yy zz cd ld BB TX BS RX
			"""

			p = 22
			onOff1 			= intFrom8(data16[p+4:p+6 ],0) !=0 # move
			accelerationX 	= signedIntfrom8(data16[p+6:p+8 ])*16*.95
			accelerationY 	= signedIntfrom8(data16[p+8:p+10])*16*.95
			accelerationZ 	= signedIntfrom8(data16[p+10:p+12])*16*.95
			currEvSecs		= intFrom8(data16[p+12:p+14],0)
			prevEvSec		= intFrom8(data16[p+14:p+16],0)
			batteryLevel	= intFrom8(data16[p+16:p+18],0)
			TXint	  		= intFrom8(data16[p+18:p+20],0)
			onOff			= intFrom8(data16[p+20:p+22],0) !=0 # button

			accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)

			# make deltas compared to last send 
			#dT 			= abs(BLEsensorMACs[mac]["temp"]				- temp)
			dX 			= abs(BLEsensorMACs[mac]["accelerationX"]		- accelerationX)
			dY 			= abs(BLEsensorMACs[mac]["accelerationY"]		- accelerationY)
			dZ 			= abs(BLEsensorMACs[mac]["accelerationZ"]		- accelerationZ)

			dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
			deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000

			deltaTime 	= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])

			# check if we should send data to indigo
			trig = ""
			trigMinTime	= deltaTime 	> BLEsensorMACs[mac]["minSendDelta"] 				# dont send too often
			if dTot			> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"]:					trig += "Acc-Total/" 	# acceleration change triggers 
			if onOff != BLEsensorMACs[mac]["onOff"] or  onOff1 != BLEsensorMACs[mac]["onOff1"]:trig += "onOff/"
			if deltaXYZ		> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]:						trig += "Acc-delta/"		# acceleration-turn change triggers 
			if deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"] :							trig += "Time" 			# send min every xx secs
			trig = trig.strip("/")

			if trigMinTime and trig != "":
				dd = {   # the data dict to be send 
					"accelerationTotal": 	int(accelerationTotal),
					"accelerationX": 		int(accelerationX),
					"accelerationY": 		int(accelerationY),
					"accelerationZ": 		int(accelerationZ),
					"accelerationXYZMaxDelta":int(deltaXYZ),
					"accelerationVectorDelta":int(dTot),
					"onOff": 				onOff,
					"onOff1": 				onOff1,
					"batteryLevel": 		int(batteryLevel),
					"trigger": 				trig.strip("/"),
					"mac": 					mac,
					"rssi":					int(rx)
				}

				## compose complete message
				checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
				fastSwitchBotPress = "on" if (onOff or onOff1) else ""
				if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)

				# remember last values
				BLEsensorMACs[mac]["lastUpdate"] 			= time.time()
				BLEsensorMACs[mac]["accelerationX"] 		= accelerationX
				BLEsensorMACs[mac]["accelerationY"] 		= accelerationY
				BLEsensorMACs[mac]["accelerationZ"] 		= accelerationZ
				BLEsensorMACs[mac]["onOff"] 				= onOff
				BLEsensorMACs[mac]["onOff1"] 				= onOff1
			return sensor, tx,  batteryLevel


		elif sensType == "THL":

			""" format:
	16 adv		                            01 23 45 67 89 11 23 45 67 89 21 23 45 67 89 31 23 
	pos		 01 23 45 67 89 11 23 45  67 89 21 23 45 67 89 31 23 45 67 89 41 23 45 67 89 51 23
			 1A 02 01 06 03 03 59 FE  12 16 59 FE AB 03 57 C1 56 C5 9C EF 64 D8 00 5F 00 18 00 AC
                                                        RMAC ------------ BB t2 t1 h2 h1 l2 l1 RX
			"""

			# unpack   sensor data 
			#p = 42
			#batteryLevel	= intFrom8(hexData[p-2:p],0)
			#temp 			= signedIntfrom16(hexData[p+2:p+4]+hexData[p+0:p+2])/8. + BLEsensorMACs[mac]["offsetTemp"]
			#hum  			= intFrom16(hexData[p+6:p+8]+hexData[p+4:p+6],0)/2.
			#Illuminance		= intFrom16(hexData[p+10:p+12]+hexData[p+8:p+10],0)

			p = 22
			batteryLevel	= intFrom8(data16[p-2:p],0)
			temp 			= signedIntfrom16(data16[p+2:p+4]+data16[p+0:p+2])/8. + BLEsensorMACs[mac]["offsetTemp"]
			hum  			= intFrom16(data16[p+6:p+8]+data16[p+4:p+6],0)/2.
			Illuminance		= intFrom16(data16[p+10:p+12]+data16[p+8:p+10],0)


			# make deltas compared to last send 
			trig = ""
			if	abs(BLEsensorMACs[mac]["temp"]			- temp) > 0.5: 			trig += "temp/"
			if 	abs(BLEsensorMACs[mac]["hum"]			- hum) > 2.: 			trig += "hum/"
			if 	abs(BLEsensorMACs[mac]["Illuminance"]	- Illuminance) > 10.: 	trig += "Illuminance/"

			deltaTime 	= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])
			# check if we should send data to indigo
			trigMinTime =  deltaTime 	> BLEsensorMACs[mac]["minSendDelta"]	# dont send too often
			if deltaTime > BLEsensorMACs[mac]["updateIndigoTiming"]: 			trig += "Time"  			# send min every xx secs
			trig = trig.strip("/")

			if trigMinTime and trig != "":
				dd = {   # the data dict to be send 
					"hum": 					int(hum),
					"temp": 				round(temp,1),
					"Illuminance": 			Illuminance,
					"batteryLevel": 		int(batteryLevel),
					"mac": 					mac,
					"trigger": 				trig,
					"rssi":					int(rx)
				}

				## compose complete message
				checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

				# remember last values
				BLEsensorMACs[mac]["lastUpdate"] 			= time.time()
				BLEsensorMACs[mac]["temp"] 					= temp
				BLEsensorMACs[mac]["hum"] 					= hum
				BLEsensorMACs[mac]["Illuminance"] 			= Illuminance
			return sensor, tx,  batteryLevel

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""


#################################
def doBLEminew(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	global BLEsensorMACs, sensors
	try:
		
		hexData = hexData[12:]
		if len(hexData) < 44: 							return sensor, tx,  ""

		#U.logger.log(20,"doBLEminew {}  hexData:{}; x:{} y:{}, z:{}".format(mac, hexData, hexData[30:34], hexData[34:38], hexData[38:42]))

		if "analyzed" not in parsedData[mac]: return sensor, tx,  ""

		sensType =""
		data16 = parsedData[mac]["analyzed"]["code"].get("16","") 
		if   data16.find("E1FFA103") == 0: sensType = "ACC"
		elif data16.find("E1FFA101") == 0: sensType = "TH"
		elif data16.find("E1FFA102") == 0: sensType = "light"
		elif data16.find("AAFE2000") == 0: sensType = "batteryVoltage"
		else:						return sensor, tx,  ""

		"""
						   01234567890123456789012345678
		if   hexData.find("1A0201060303E1FF1216E1FFA103") ==0: sensType = "ACC"
		elif hexData.find("180201060303E1FF1016E1FFA101") ==0: sensType = "TH"
		elif hexData.find("150201060303E1FF0D16E1FFA102") ==0: sensType = "light"
		elif hexData.find("190201060303AAFE1116AAFE2000") ==0: sensType = "batteryVoltage"
		else:						return sensor, tx,  ""
		#batteryLevel	= intFrom8(hexData, 28)
		"""
		batteryLevel	= intFrom8(data16, 8)

		#U.logger.log(20,"doBLEminew {}  sensType:{},  hexdata:{} ".format(mac,sensType, hexData))
		if sensType == "batteryVoltage":
			p = 8
			BLEsensorMACs[mac]["batteryVoltage"] = signedIntfrom16(data16[ p :p+4 ]) # in mV
			#U.logger.log(20,"doBLEminews1TH {}  sensType:{},  batteryVoltage:{}, hexdata:{} {} ".format(mac,sensType, BLEsensorMACs[mac]["batteryVoltage"],hexData[p:p+2],hexData[p+2:p+4]))


		elif sensType == "light":
			""" format:
			   pos: 01 23 45 67   89 11 23 45   67 89 21 23 45 67 89 31 23 45 67 89 41 23 
			hexData:15 02 01 06   03 03 E1 FF   0D 16 E1 FF A1 02 64 00 74 35 A4 3F 23 AC 
					15 02 01 06   03 03 E1 FF   0D 16 E1 FF A1 02 64 01 74 35 A4 3F 23 AC 
												                  BB  = Battery
														             li = light  is 00 or 01
			"""

			# unpack   sensor data 
			#p = 30;	onOff 			= int(hexData[ p :p+2 ]) !=0
			#p = 28;	batteryLevel 	= int(hexData[ p :p+2 ])
			p = 10;	onOff 			= int(data16[ p :p+2 ]) !=0
			p = 8;	batteryLevel 	= int(data16[ p :p+2 ])

			deltaTime 	= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])
			deltaonOff 	= onOff != BLEsensorMACs[mac]["onOff"]

			# check if we should send data to indigo
			trigMinTime	= deltaTime 	> BLEsensorMACs[mac]["minSendDelta"] 				# dont send too often
			trigTime 	= deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"]  			# send min every xx secs
#U.logger.log(20, "mac:{}    trigMinTime:{} deltaXYZ:{}, trig:{} acc xyz:{};{};{}".format(mac, trigMinTime, deltaXYZ, trig, accelerationX, accelerationY, accelerationZ) )

			if trigMinTime and trigTime:
				dd = {   # the data dict to be send 
					"onOff": 				onOff,
					"batteryLevel": 		int(batteryLevel),
					"rssi":					int(rx),
				}
				if BLEsensorMACs[mac]["batteryVoltage"] != -1:
					dd["batteryVoltage"] = BLEsensorMACs[mac]["batteryVoltage"]
				#U.logger.log(20, " .... sending  data:{}".format( dd ) )

				## compose complete message
				checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

				# remember last values
				BLEsensorMACs[mac]["lastUpdate"] 			= time.time()
				BLEsensorMACs[mac]["onOff"] 				= onOff
				fastSwitchBotPress = "on" if onOff else "off"
				if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)

			return sensor, tx,  batteryLevel

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

			# unpack   sensor data 
			#p = 30
			#accelerationX 	= signedIntfrom16(hexData[ p :p+4 ])*(10./2.45) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			#accelerationY 	= signedIntfrom16(hexData[p+4:p+8 ])*(10./2.45)
			#accelerationZ 	= signedIntfrom16(hexData[p+8:p+12])*(10./2.45)
			p = 10
			accelerationX 	= signedIntfrom16(data16[p  :p+4 ])*(10./2.45) # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540  
			accelerationY 	= signedIntfrom16(data16[p+4:p+8 ])*(10./2.45)
			accelerationZ 	= signedIntfrom16(data16[p+8:p+12])*(10./2.45)
			accelerationTotal= math.sqrt(accelerationX * accelerationX + accelerationY * accelerationY + accelerationZ * accelerationZ)

			# make deltas compared to last send 
			dX 			= abs(BLEsensorMACs[mac]["accelerationX"]		- accelerationX)
			dY 			= abs(BLEsensorMACs[mac]["accelerationY"]		- accelerationY)
			dZ 			= abs(BLEsensorMACs[mac]["accelerationZ"]		- accelerationZ)

			dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
			deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000

			deltaTime 	= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate1"])

			# check if we should send data to indigo
			trigMinTime	= deltaTime 	> BLEsensorMACs[mac]["minSendDelta"] 				# dont send too often
			trig = ""
			if dTot			> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"]:	trig += "Acc-Vect/"	 	# acceleration change triggers 
			if deltaXYZ		> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]	:		trig += "Acc-max/"			# acceleration-turn change triggers 
			if deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"]:				trig += "Time"	 			# send min every xx secs

			trig = trig.strip("/")

			if trigMinTime and trig != "":
				dd = {   # the data dict to be send 
					"accelerationTotal": 	int(accelerationTotal),
					"accelerationX": 		int(accelerationX),
					"accelerationY": 		int(accelerationY),
					"accelerationZ": 		int(accelerationZ),
					"accelerationXYZMaxDelta":int(deltaXYZ),
					"accelerationVectorDelta":int(dTot),
					"batteryLevel": 		int(batteryLevel),
					"trigger": 				trig.strip("/"),
					"mac": 					mac,
					"rssi":					int(rx)
				}
				if BLEsensorMACs[mac]["batteryVoltage"] != -1:
					dd["batteryVoltage"] = BLEsensorMACs[mac]["batteryVoltage"]
				#U.logger.log(20, " .... sending  data:{}".format( dd ) )

				## compose complete message
				checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

				# remember last values
				BLEsensorMACs[mac]["lastUpdate1"] 			= time.time()
				BLEsensorMACs[mac]["accelerationX"] 		= accelerationX
				BLEsensorMACs[mac]["accelerationY"] 		= accelerationY
				BLEsensorMACs[mac]["accelerationZ"] 		= accelerationZ
			return sensor, tx,  batteryLevel


		if sensType == "TH":

			""" format:

		   pos: 01 23 45 67 89 11 23 45 67 89 21 23 45 67 89 31 23 45 67 89 41 23 45 67  
		hexData:18 02 01 06 03 03 E1 FF 10 16 E1 FF A1 01 64 15 91 41 9C 79 B8 A1 3F 23 
														  BB  = Battery
															 temp- 
																   HUM-- 
		hexData:18 02 01 06 03 03 E1 FF 10 16 E1 FF A1 01 64 15 91 41 9C  rmac############
			"""

			# unpack   sensor data 
			#p = 30
			#temp 				= float(signedIntfrom8(hexData[ p   :p+2 ]))  + intFrom8(hexData[p+2:p+4],0)/256. + BLEsensorMACs[mac]["offsetTemp"]
			#hum				 	= float(signedIntfrom8(hexData[ p+4 :p+6 ]))  + intFrom8(hexData[p+6:p+8],0)/256. + BLEsensorMACs[mac]["offsetHum"]
			p = 10
			temp 				= float(signedIntfrom8(data16[ p   :p+2 ]))  + intFrom8(data16[p+2:p+4],0)/256. + BLEsensorMACs[mac]["offsetTemp"]
			hum				 	= float(signedIntfrom8(data16[ p+4 :p+6 ]))  + intFrom8(data16[p+6:p+8],0)/256. + BLEsensorMACs[mac]["offsetHum"]
			#U.logger.log(20,"doBLEminews1TH {}  pos:{}, temp:{}, hum:{}, hexdata:{} {} {} {}".format(mac,TagPos, temp, hum, hexData[p:p+2],hexData[p+2:p+4],hexData[p+4:p+6],hexData[p+6:p+8]))

			# make deltas compared to last send 
			trig = ""
			deltaTime 	= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])
			# check if we should send data to indigo
			trigMinTime	= deltaTime 	> BLEsensorMACs[mac]["minSendDelta"]
			if abs(BLEsensorMACs[mac]["temp"]		- temp) > 0.5: 			trig += "temp/"
			if abs(BLEsensorMACs[mac]["hum"]		- hum) > 2.: 			trig += "hum/"
			if deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"]: 	trig += "Time"  			# send min every xx secs
			trig = trig.strip("/")


			if trig !="" and trigMinTime:
				dd = {   # the data dict to be send 
					"hum": 					int(hum),
					"temp": 				round(temp,1),
					"batteryLevel": 		int(batteryLevel),
					"mac": 					mac,
					"trigger": 				trig,
					"rssi":					int(rx)
				}
				if BLEsensorMACs[mac]["batteryVoltage"] != -1:
					dd["batteryVoltage"] = BLEsensorMACs[mac]["batteryVoltage"]
				#U.logger.log(20, " .... sending  data:{}".format( dd ) )

				## compose complete message
				checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

				# remember last values
				BLEsensorMACs[mac]["lastUpdate"] 			= time.time()
				BLEsensorMACs[mac]["temp"] 					= temp
				BLEsensorMACs[mac]["hum"] 					= hum
			return sensor, tx,  batteryLevel

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,"mac#{}; sensor:{}, sensType:{}, hexdata:{}".format(mac, sensor, sensType, hexData))
	# return incoming parameetrs
	return sensor, tx,  ""



#################################
#################################
## Ruuvi ########################
#################################
def doRuuviTag( mac, rx, tx, hexData,sensor):
	global BLEsensorMACs, sensors
	global bleServiceSections, bleServiceSectionsReverse, parsedData


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
		
		#if mac == "C5:5F:FA:70:F9:69": U.logger.log(20, "mac:{}  doRuuviTag :{}".format(mac, hexData ))
		if len(hexData) < 44: 	
			#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,"mac:{};  < 44..{} ".format(mac, len(hexData))) 
			return sensor, tx,  ""
		#        mac---------  ll flag   ll tag    version
		#        012345678911  23 4567 89 21 234567 89 
		#		 012345678901  1F 0201 06 1B FF9904 05
		#		 012345678901  1F 0201 04 1B FF9904 05
		#                                           04 03 06 not supported
		#                         0201 06 1B FF9904 05
		"""
		igbore packets like:
		                                                                                        R  u  u  v  i     1  7  E  B
				69F970FA5FC5  1E 11 07 9E CA DC 24 0E E5 A9 E0 93 F3 A3 B5 01 00 40 6E   0B 09 52 75 75 76 69 20 46 39 36 39 C0		use:
		use:								   MFG Ruuv ID    vers  data ----------------------------------------------
			    69F970FA5FC5  1F 02 01 06   1B FF  99 04      05    129F4ADABBCC0010FFD004009AB60BAFDCC55FFA70F969BC
		"""


		tag 			= "9904"
		if mac not in parsedData: return sensor, tx,  ""
		if "analyzed" not in parsedData[mac]: return sensor, tx,  ""

		#if mac == "C5:5F:FA:70:F9:69": U.logger.log(20, "mac:{}   parsedData:{}".format(mac,  parsedData[mac]["analyzed"]["text"]))
		data =  parsedData[mac]["analyzed"]["code"].get("FF","") 

		if data == "": 
			#if mac == "C5:5F:FA:70:F9:69": U.logger.log(20, "mac:{}  data = empty".format(mac ))
			return sensor, tx,  ""
		if data.find(tag) !=0: 
			#if mac == "C5:5F:FA:70:F9:69": U.logger.log(20, "mac:{}  tag not found, data:{} ".format(mac, data ))
			return sensor, tx,  ""

		# make data into right format (bytes)
		byte_data = bytearray.fromhex(data[len(tag):])

		sensor 		= "BLERuuviTag"
		dataFormat	= byte_data[0]

		# sensor is active, get all data and send if conditions ok
		# unpack  rest of sensor data 
		accelerationTotal, accelerationX, accelerationY, accelerationZ 	= doRuuviTag_magValues(byte_data)
		temp 					= (doRuuviTag_temperature(byte_data)+ BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multTemp"]
		batteryVoltage, txPower = doRuuviTag_powerinfo(byte_data, doLog= mac in ["xxD1:FC:38:C4:57:75"])
		batteryLevel 			= batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=3000., batteryVoltAt0=2200.)
		#if mac == "F3:4C:96:A2:CC:13": U.logger.log(20, "mac:{}  in sens 1  BL:{}, batteryVoltage:{}".format(mac, batteryLevel, batteryVoltage ))

		# make deltas compared to last send 
		dX 			= abs(BLEsensorMACs[mac]["accelerationX"]		- accelerationX)
		dY 			= abs(BLEsensorMACs[mac]["accelerationY"]		- accelerationY)
		dZ 			= abs(BLEsensorMACs[mac]["accelerationZ"]		- accelerationZ)
		dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
		deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000

		deltatemp 	= abs(BLEsensorMACs[mac]["temp"] - temp)  
		deltaTime 	= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])

		# check if we should send data to indigo
		trig = ""
		trigMinTime	= deltaTime 	> BLEsensorMACs[mac]["minSendDelta"] 				# dont send too often
		if deltatemp 	> BLEsensorMACs[mac]["updateIndigoDeltaTemp"]:  		trig += "temp/" 			# temp change triggers
		if dTot			> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"]:  	trig += "Acc-Vec/" 	# acceleration change triggers 
		if deltaXYZ		> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]	:  		trig += "Acc-delta/"		# acceleration-turn change triggers 
		if deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"]:  			trig += "Time"		# send min every xx secs

		if trigMinTime and trig !="":
			dd = {   # the data dict to be send 
				"data_format": 			dataFormat,
				"hum": 					int(doRuuviTag_humidity(byte_data)	 + BLEsensorMACs[mac]["offsetHum"] + 0.5),
				"temp": 				round(temp							 + BLEsensorMACs[mac]["offsetTemp"],1),
				"press": 				int(doRuuviTag_pressure(byte_data) + BLEsensorMACs[mac]["offsetPress"]),
				"accelerationTotal": 	int(accelerationTotal),
				"accelerationX": 		int(accelerationX),
				"accelerationY": 		int(accelerationY),
				"accelerationZ": 		int(accelerationZ),
				"accelerationXYZMaxDelta":int(deltaXYZ),
				"accelerationVectorDelta":int(dTot),
				"batteryLevel": 		int(batteryLevel),
				"batteryVoltage": 		int(batteryVoltage),
				"movementCount": 		int(doRuuviTag_movementcounter(byte_data)),
				"measurementCount": 	int(doRuuviTag_measurementsequencenumber(byte_data)),
				"trigger": 				trig.strip("/"),
				"txPower": 				int(txPower),
				"mac": 					mac,
				"rssi":					int(rx)
			}
			#if mac in ["D1:FC:38:C4:57:75"] :U.logger.log(20, " .... sending  data:{}".format( dd ) )

			## compose complete message
			checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

			# remember last values
			BLEsensorMACs[mac]["lastUpdate"] 			= time.time()
			BLEsensorMACs[mac]["accelerationTotal"] 	= accelerationTotal
			BLEsensorMACs[mac]["accelerationX"] 		= accelerationX
			BLEsensorMACs[mac]["accelerationY"] 		= accelerationY
			BLEsensorMACs[mac]["accelerationZ"] 		= accelerationZ
			BLEsensorMACs[mac]["temp"] 					= temp

		return sensor, str(txPower), batteryLevel

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""


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
def doRuuviTag_powerinfo( data, doLog=False):
	"""Return battery voltage and tx power"""
	power_info = (data[13] & 0xFF) << 8 | (data[14] & 0xFF)
	battery_voltage = rshift(power_info, 5) + 1600
	tx_power = (power_info & 0b11111) * 2 - 40

	if rshift(power_info, 5) == 0b11111111111:
		battery_voltage = 0
	if (power_info & 0b11111) == 0b11111:
		tx_power = -9999
	#if doLog: U.logger.log(20, f" v:{battery_voltage}, data 13:{data[13]}  14:{data[14]}, powerinfo:{power_info} , r5: {rshift(power_info, 5)} ")

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
#################################
## MKK ########################
#################################
def doBLEKKMsensor( mac, rx, tx, hexData,sensor):
	global BLEsensorMACs, sensors, findMAC

	
	"""

KKM beacons structure  --   normal eddystone format for TLM is not listed here already covered somewhere else

LL = length of following data 

1. k sensor 
make this general for eddystone sensor
													   01  23 45 67 89 A1 23 45 67 		89 b1 23 45 67 89 C1 23 45 67 89 D1 23 45 67 89
           04 3E 24 02 01 00 00   14 A5 00 29 57 BC    18  02 01 06 03 03 AA FE LL 		16 AA FE 21 01 0B 0F 7B 1B 00 00 EA 00 FA FB 9B                         BC=-68
													   19  02 01 06 03 03 AA FE 11 		16 AA FE 20 00 0C 3D 1A 80 00 00 01 E0 00 00 37 D1 BC  TLM
																								 xx frame type  20 = TLM not handled here 
																								    xx version
																								 	  xx 0=volt,   0B = 00001011 = volt, temp, accel
																								 	  xx 1=temp, 
																								 	  xx 2=humidity, 
																								 	  xx 3=acceleration, 
																								 	  xx 4=cutoff, ==?? 
																								 	  xx 5= PIR, 
																								 	  xx 6= 
																								 	  xx 7= 
																										 xx xx  big endian volt in 0.1mV here 7B0F == 31503
																										       xx xx  temp fixed point 8.8
																									                 xx xx   big endian acc x
																									                       xx xx big endian acc y
																									                             xx xx   big endian acc z

system: 
														01 	23 45 67 	89 A1 23 45 	67 		89 		b1 23 45 67 89 C1 23 45 67 89 D1 23 45 67 89
 														16	02 01 06 	03 03 AA FE 	LL 		16 		AA FE 22 0F 62 BC 57 29 00 A5 14 06 38       
													    16	02 01 06 	03 03 AA FE		0E 		16 		AA FE 22 0D 71 BC 57 29 00 5B FB 06 37 BC
																											     xx modelId
																											        bb = bat level
																													   xx xx xx xx xx xx  mac
																						                         						 aa bb software version = aa.bb
and this general for eddystone UID
UID message
														01  23 45 67 89 A1 23 45 67 	89 b1 23 45 67 89 C1 23 45 67 89 D1 23 45 67   89 E1 23 45 67 89 
           04 3E 2B 02 01 00 00   FB 5B 00 29 57 BC     1F  02 01 06 03 03 AA FE LL 	16 AA FE 00 DA 00 00 00 00 00 00 00 00 00 01   00 00 00 00 00 01   02 00    BA=-70    single click
           04 3E 2B 02 01 00 00   FB 5B 00 29 57 BC     1F  02 01 06 03 03 AA FE LL 	16 AA FE 00 DA 00 00 00 00 00 00 00 00 00 02   00 00 00 00 00 02   02 00    BA=-70    double click
           04 3E 2B 02 01 00 00   FB 5B 00 29 57 BC     1F  02 01 06 03 03 AA FE LL 	16 AA FE 00 DA 00 00 00 00 00 00 00 00 00 03   00 00 00 00 00 03   02 00    BA=-70    long click
														                            	         01 23 45 67 89 A1 23 45 67 89 b1 23   45 67 89 C1 23 45   67 89 
														    										   xx  -----------------------xx UID 1  10 bytes
																										                                xx  ----------xx UID 2 6 bytes


and this for mfg info, not done here 
														01  23 45 67 89 A1 23 45 67 89 b1 23 45 67 89 C1 23 45 67 89 D1 23 45 67 89 E1 23 45 67 89 
														18  09 16 80 20 67 01 00 00 00 00 0D 09 4B 42 50 72 6F 5F 32 39 31 33 37 31 BF
														18  09 16 80 20 71 2A 00 00 00 00 0D 09 4B 42 50 72 6F 5F 32 37 32 36 35 36 C4
																  ?? ?? ?? ??			  LL	K  B  P  r  o  _  2  9  1  3  7  1
																  ?? ?? ?? ??			  LL	K  B  P  r  o  _  xxxxx
	"""


	try:
		
		if len(hexData) < 20: 	
			return sensor, tx,  ""

		doPrint = False # mac in findMAC


		data16  = parsedData[mac]["analyzed"]["code"].get("16","") 
		dataMFG = parsedData[mac]["analyzed"]["text"].get("mfg_info","") 
		dataTLM = parsedData[mac]["analyzed"]["text"].get("TLM","") 

		sensor 				= "BLEKKMsensor"
		hexData  			= hexData[12:]
		tag16 				= "AAFE"
		tagSensor 			= "21"
		tagSystem			= "22"
		tagUID				= "00"
		pressPos 			= 21
		waitWithButtonSend = 15 # secs
		if doPrint: U.logger.log(20,"")
		if doPrint: U.logger.log(20,"mac:{}; -0-  dataMFG:{}, dataTLM:{}, data16:{}, ll:{:2}, hexData:{}".format(mac,   dataMFG, dataTLM,  data16,  len(hexData), hexData))

		if dataMFG != "":
			BLEsensorMACs[mac]["mfg_info"]  = dataMFG
			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"] 

		if  dataTLM != "": 
			BLEsensorMACs[mac]["batteryVoltage"]	= dataTLM.get("batteryVoltage","")
			BLEsensorMACs[mac]["batteryLevel"]		= batLevelTempCorrection(BLEsensorMACs[mac]["batteryVoltage"] , 23)
			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"] 

		if data16 == "": return sensor, tx,  ""

		if data16.find(tag16) != 0 : return sensor, tx,  ""

		data16 		= data16[len(tag16):]
		sensSensor 	= data16[0:len(tagSensor)] == tagSensor
		sensSystem  = data16[0:len(tagSensor)] == tagSystem
		sensUID  	= data16[0:len(tagSensor)] == tagUID
		data16 		= data16[len(tagSensor):]

		if doPrint:U.logger.log(20,"mac:{}; -2- sensSensor:{}, sensSystem:{}, sensUID:{}, hexDataRest:{}".format(mac, sensSensor, sensSystem, sensUID, data16 )) 

		# make data into right format (bytes)

		if BLEsensorMACs[mac].get("SupportsSensorValue","") == "":
			BLEsensorMACs[mac]["SupportsSensorValue"] = False

		dd = {"mac": mac, "rssi" : int(rx), "mfg_info": BLEsensorMACs[mac]["mfg_info"] } # , "SupportsSensorValue": BLEsensorMACs[mac]["SupportsSensorValue"] }
		trig = ""
		hum  = ""
		temp = ""
		accelerationTotal = ""
		batteryVoltage 		= ""
		batteryLevel 		= ""

		if sensSystem:  # this just save 2 items to be send with other packages 
			BLEsensorMACs[mac]["modelId"] 			= data16[0:2]
			##BLEsensorMACs[mac]["batteryLevel"] 		= max(0,min(100,int(data16[2:4],16)))
			BLEsensorMACs[mac]["softwareVersion"] 	= "{}.{}".format( int(data16[16:18],16), int(data16[18:20],16) )

			if doPrint: U.logger.log(20,"mac:{}; -3- modelId:{}, batLevel:{}, batteryVoltage:{}, softwareVersion:{}, ll16:{}".format(mac,BLEsensorMACs[mac]["modelId"], BLEsensorMACs[mac]["batteryLevel"], BLEsensorMACs[mac]["batteryVoltage"], BLEsensorMACs[mac]["softwareVersion"], len(data16) )) 
			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"] 

		if BLEsensorMACs[mac].get("softwareVersion","") != "":
				dd["softwareVersion"]  =  BLEsensorMACs[mac]["softwareVersion"] 
		if BLEsensorMACs[mac].get("modelId","") != "":
				dd["modelId"]  =  BLEsensorMACs[mac]["modelId"] 
		if  BLEsensorMACs[mac]["batteryVoltage"] not in ["","-1"]:
				dd["batteryVoltage"]  =  BLEsensorMACs[mac]["batteryVoltage"]
		if  BLEsensorMACs[mac]["batteryLevel"] not in ["","-1"]:
				dd["batteryLevel"]  =  BLEsensorMACs[mac]["batteryLevel"]

		if sensUID: # this is for button press 
			if len(data16) < pressPos-1: return sensor, tx,  ""
			BLEsensorMACs[mac]["txPower"] = data16[0:2]
			dd["txPower"] 		= BLEsensorMACs[mac]["txPower"] 
			dd["mfg_info"]		= BLEsensorMACs[mac]["mfg_info"]
			onOff		= data16[pressPos] == "1"
			onOff1 		= data16[pressPos] == "2"
			onOff2		= data16[pressPos] == "3"
			if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate1"]) > waitWithButtonSend and onOff:		dd["onOff"]  = True;	trig += "press/"
			if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate2"]) > waitWithButtonSend and onOff1:	dd["onOff1"] = True; 	trig += "doublePress/"
			if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate3"]) > waitWithButtonSend and onOff2:	dd["onOff2"] = True; 	trig += "longPress/"
			if  doPrint: U.logger.log(20,"mac:{}; -4- Button press txPower:{}, onOff:{},  onOff1:{}, onOff2:{}, t1:{:.1f}, t2:{:.1f}, t3:{:.1f} dd:{}".format(mac, dd["txPower"] , onOff,  onOff1, onOff2 , tryDeltaTime( BLEsensorMACs[mac]["t1"]) , tryDeltaTime(BLEsensorMACs[mac]["t2"]) , tryDeltaTime( BLEsensorMACs[mac]["t3"]), dd )) 
			trig = trig.strip("/")

			if trig != "":
				if onOff: 
						BLEsensorMACs[mac]["lastUpdate1"]  = time.time()
						BLEsensorMACs[mac]["onOff"] = "onOff1"
				elif onOff1: 
						BLEsensorMACs[mac]["lastUpdate2"]  = time.time()
						BLEsensorMACs[mac]["onOff"] = "onOff2"
				elif onOff2: 
						BLEsensorMACs[mac]["lastUpdate3"]  = time.time()
						BLEsensorMACs[mac]["onOff"] = "onOff3"

				dd["trigger"] = trig
				if doPrint: U.logger.log(20, " .... sending  data:{}".format( dd ) )
				checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
				# remember last values

			return sensor, tx,  ""




		if sensSensor:
			BLEsensorMACs[mac]["SupportsSensorValue"] = True
			dd ["SupportsSensorValue"] =  BLEsensorMACs[mac]["SupportsSensorValue"] 
			version = data16[0:2]
			data16 = data16[2:]

			typesPresent 	=  int(data16[0:2],16)
			voltPresent 	= typesPresent & 0b00000001
			tempPresent		= typesPresent & 0b00000010
			humPresent 		= typesPresent & 0b00000100
			accPresent 		= typesPresent & 0b00001000
			data16 = data16[2:]



			if voltPresent:
				#U.logger.log(20,"mac:{};  volt calc:{}  data16:{}".format(mac,signedIntfrom16(data16[0:4]), data16[0:4]))
				batteryVoltage = signedIntfrom16(data16[0:4])
				data16 = data16[4:]
				if BLEsensorMACs[mac]["batteryLevel"] != "":
					dd["batteryLevel"]  =  BLEsensorMACs[mac]["batteryLevel"]
					batteryLevel		= dd["batteryLevel"] 
				else:
					batteryLevel 			= batLevelTempCorrection(batteryVoltage, 23.)
					BLEsensorMACs[mac]["batteryLevel"] 	= int(batteryLevel)

				BLEsensorMACs[mac]["batteryVoltage"] 	= int(batteryVoltage)
				dd["batteryVoltage"]  =  int(batteryVoltage)


			if tempPresent:
				temp = signedIntfrom16(data16[0:2])
				temp += float(int(data16[2:4],16))/256.
				#U.logger.log(20,"mac:{};  temp calc  temp:{},  t1:{}, t2:{}  data16:{}".format(mac,temp, signedIntfrom16(data16[2:4]), signedIntfrom16(data16[0:2]), data16[0:4]))
				data16 = data16[4:]
				dd["temp"] 		= round(temp + BLEsensorMACs[mac]["offsetTemp"], 1)
				if abs(BLEsensorMACs[mac]["temp"] - temp)  > 0.5: trig += "Temp/"


			if humPresent:
				hum = signedIntfrom16(data16[0:4])
				data16 = data16[4:]
				dd["hum"] 		= int(hum + BLEsensorMACs[mac]["offsetHum"] + 0.5)
				if abs(BLEsensorMACs[mac]["hum"] - hum)   > 1: trig += "Hum/"

			if accPresent:
				accelerationX = signedIntfrom16(data16[0:4])
				#U.logger.log(20,"mac:{};  acceleration  x:{}, data16:{}".format(mac, accelerationX, data16[0:12]))
				data16 = data16[4:]
				accelerationY = signedIntfrom16(data16[0:4])
				data16 = data16[4:]
				accelerationZ = signedIntfrom16(data16[0:4])
				data16 = data16[4:]
				accelerationTotal = math.sqrt(accelerationX*accelerationX + accelerationY*accelerationY + accelerationZ*accelerationZ)
				# make deltas compared to last send 
				dX 			= abs(BLEsensorMACs[mac]["accelerationX"]		- accelerationX)
				dY 			= abs(BLEsensorMACs[mac]["accelerationY"]		- accelerationY)
				dZ 			= abs(BLEsensorMACs[mac]["accelerationZ"]		- accelerationZ)
				dTot 		= math.sqrt(dX*dX +dY*dY +dZ*dZ) # in N/s**2 *1000
				deltaXYZ	= int(max(dX, dY, dZ))  # in N/s**2 *1000
				dd["accelerationX"] =  					int(accelerationX)
				dd["accelerationY"] =  					int(accelerationY)
				dd["accelerationZ"] =  					int(accelerationZ)
				dd["accelerationTotal"] =  				round(accelerationTotal,0)
				dd["accelerationXYZMaxDelta"] = 		int(deltaXYZ)
				dd["accelerationVectorDelta"] = 		int(dTot)
				if dTot	> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"]: trig += "AccTot/"	# acceleration change triggers 
				if deltaXYZ	> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]: trig += "AccDir/"			# acceleration-turn change triggers 
				#U.logger.log(20,"mac:{};  dd :{}".format(mac, dd))

			# check if we should send data to indigo
			deltaTime 	= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])
			trigMinTime	= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"]) > BLEsensorMACs[mac]["minSendDelta"] 				# dont send too often
			if deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time" 			# send min every xx secs
	
			trig = trig.strip("/")

			if trigMinTime and trig != "":
				dd["trigger"] =   trig.strip("/")
				if "txPower" not in dd and BLEsensorMACs[mac]["txPower"] != "":
					dd["txPower"]  =  BLEsensorMACs[mac]["txPower"] 

				if doPrint: U.logger.log(20, " .... sending  data:{}".format( dd ) )

				## compose complete message
				checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})

				# remember last values
				BLEsensorMACs[mac]["lastUpdate"] 			= time.time()
				if accelerationTotal != "":
					BLEsensorMACs[mac]["accelerationTotal"] 	= accelerationTotal
					BLEsensorMACs[mac]["accelerationX"] 		= accelerationX
					BLEsensorMACs[mac]["accelerationY"] 		= accelerationY
					BLEsensorMACs[mac]["accelerationZ"] 		= accelerationZ
				if temp != "":
					BLEsensorMACs[mac]["temp"] 	= temp
				if hum != "":
					BLEsensorMACs[mac]["hum"] 	= hum

		return sensor, str(tx), batteryLevel

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""


#################################

def checkIfDelaySend(packet):
	global dataFromSensors, waitforcheckIfDelaySend
	### delay send  if only update for tim reason, thne hand it over to regular send msgs 
	try:
		if "sensors" not in packet:
			U.sendURL(packet)
			return 
		for sensor in packet["sensors"]:
			for devId in packet["sensors"][sensor]:
				if "trigger" not in packet["sensors"][sensor][devId]:
					U.sendURL(packet)
					return 

				if packet["sensors"][sensor][devId]["trigger"].lower() != "time":
					U.sendURL(packet)
					return 

				if sensor not in dataFromSensors:
					dataFromSensors[sensor] = {}
				for devId in packet["sensors"][sensor]:
					if devId not in dataFromSensors[sensor] :
						dataFromSensors[sensor][devId] = {}
					waitforcheckIfDelaySend = True
					dataFromSensors[sensor][devId] = packet["sensors"][sensor][devId]
					waitforcheckIfDelaySend = False

					#U.logger.log(20, "checkIfDelaySend sensor:{}, devId:{}, data:{} ".format(sensor, devId, packet["sensors"][sensor][devId]))
				#U.logger.log(20, "checkIfDelaySend dataFromSensors:{} ".format(dataFromSensors))
				return 

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

	U.sendURL(packet)

#################################
## BLE Sensors     ###########
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
		nLogMgsTrackMac		= 30 # # of message logged for sepcial mac 
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
			
		if logCountTrackMac == 0 or (startTimeTrackMac > 0 and tryDeltaTime( startTimeTrackMac) > collectTime):
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
	global bleServiceSections, bleServiceSectionsReverse, BLEanalysisdataCollectionTime, BLEcollectStartTime
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

		## now listen to BLE
		BLEcollectStartTime = time.time()
		U.logger.log(20, "starting  BLEAnalysis, rssi cutoff= {}[dBm]".format(BLEanalysisrssiCutoff))
		U.logger.log(20, "sudo hciconfig {} reset".format(hci))
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
		U.logger.log(20, "prep done; after@: {:.1f} secs".format(tryDeltaTime(BLEcollectStartTime)))
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
	global bleServiceSections, bleServiceSectionsReverse, BLEanalysisdataCollectionTime, BLEcollectStartTime, BLEanalysisrssiCutoff
	global rpiDataAcquistionMethod
	try:
		if BLEcollectStartTime == -1 and os.path.isfile(G.homeDir+"temp/beaconloop.BLEAnalysis"): 
			f = open(G.homeDir+"temp/beaconloop.BLEAnalysis","r")
			try: 	BLEanalysisrssiCutoff = int(f.read().strip("\n"))
			except: BLEanalysisrssiCutoff = -99.
			f.close()
			subprocess.call("rm {}temp/beaconloop.BLEAnalysis".format(G.homeDir), shell=True)
			BLEcollectStartTime = time.time()

			U.logger.log(20,"starting ble analysis with rssi cutoff:{}  using method:{}, for  {} secs, starttimeStamp:{}".format(BLEanalysisrssiCutoff, rpiDataAcquistionMethod, BLEanalysisdataCollectionTime, BLEcollectStartTime))
			if os.path.isfile(G.homeDir+"temp/hcidump.data"):
				subprocess.call("rm {}temp/hcidump.data".format(G.homeDir), shell=True)

			if rpiDataAcquistionMethod == "socket": 
				if BLEAnalysisSocket(hci): return True
			return False

		elif  BLEcollectStartTime >0:
			#U.logger.log(20,"testing ble analysis :{}".format(tryDeltaTime( BLEcollectStartTime)))
			if tryDeltaTime( BLEcollectStartTime) >= BLEanalysisdataCollectionTime: 
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
	global bleServiceSections, bleServiceSectionsReverse, BLEanalysisdataCollectionTime, BLEanalysisrssiCutoff, BLEcollectStartTime
	try:
		if tryDeltaTime( BLEcollectStartTime) <= BLEanalysisdataCollectionTime: return 
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
		collectionTime = tryDeltaTime( BLEcollectStartTime)
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
				for code in bleServiceSections:
					textF  = bleServiceSections[code]
					try:
						if code in parsedData[mac]["analyzed"]["code"]: 
							MACs[mac][textF].append(parsedData[mac]["analyzed"]["code"][code])
						else:										
							MACs[mac][textF].append("")
					except	Exception as e:
						U.logger.log(20,"", exc_info=True)
						U.logger.log(20, "finished  hcidump: mac:{}, code:{}, text:{}, parsedData:{}   ".format(mac, code, textF, parsedData[mac]["analyzed"]["code"] ))

				for ee in extraLists:
					if ee in parsedData[mac]["analyzed"]["text"]:
							MACs[mac][ee].append(parsedData[mac]["analyzed"]["text"][ee])
					else:
							MACs[mac][ee].append("")

			MACs[mac]["nMessages"][nMsgNumber]+=1
			if "TxPowerLevel" in parsedData[mac]["analyzed"]["text"]:
				try:
					tx = signedIntfrom8(parsedData[mac]["analyzed"]["text"]["TxPowerLevel"])
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
						posFound, dPostest,  subtypeOfBeacon = testComplexTag(hexStr[12:-2], tag, mac, mac.replace(":",""), hexStr[0:12],"","", calledFrom="BLEAnalysis")
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
						posFound, dPostest, subtypeOfBeacon  = testComplexTag(hexStr[12:-2], tag, mac, mac.replace(":",""), hexStr[0:12], "", "", calledFrom="BLEAnalysis" )
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
		U.logger.log(20, "finished  BLEAnalysis: {:.1f} secs, waiting for sending bytes:{}; :\n{}".format(tryDeltaTime(BLEcollectStartTime), ldd, "{}".format(dd)[0:300]))
		subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		U.sendURL(dd, squeeze=False, verbose=True, wait=True)
		time.sleep(5.+ min(10,ldd/20000.))
		U.logger.log(20, "========== BLEanalysis finished ========\n")

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	BLEcollectStartTime = -1
	return


#################################
def updateTimeAndZone(hciUse):
	global beaconsOnline
	'''
	============
	for XiaomiTimeLYWSD02 
	cmd = "gatttool -i {} -I -b {}".format(hciUse, MAC)
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
			U.logger.log(20,"updateTimeAndZone deviceList:{}".format(deviceList))

			# devices: '{"24:DA:11:21:2B:20": "xxx"}'
			for devices1 in deviceList:
				if len(devices1) == 0: continue
				devices = json.loads(devices1)
				if len(devices) == 0: continue
				expCommands = ""
				stopHCUIDUMPlistener()
				restart = True
				cmd = "sudo /bin/hciconfig {} reset".format(hciUse)
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

						cmd = "sudo /usr/bin/gatttool -i {} -b {} -I".format(hciUse, mac) 
						U.logger.log(20,cmd)
						expCommands = pexpect.spawn(cmd)
						ret = expCommands.expect([">","error",pexpect.TIMEOUT], timeout=10)
						if ret == 0:
							U.logger.log(20,"... successful: {}-{}".format(expCommands.before,expCommands.after))
							connected = True
						else:
							if ii < ntriesConnect-1:
								if ret == 1:	U.logger.log(20, "... error, giving up: {}-{}".format(expCommands.before,expCommands.after))
								elif ret == 2:	U.logger.log(20, "... timeout, giving up: {}-{}".format(expCommands.before,expCommands.after))
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
									U.logger.log(20,"expect connect ")
									expCommands.sendline("connect ")
									ret = expCommands.expect(["Connection successful","Error", pexpect.TIMEOUT], timeout=15)
									if ret == 0:
										U.logger.log(20,"... successful: {}".format(expCommands.after))
										connected = True
										break
									else:
										if ii < ntriesConnect-1: 
											if ret == 1:	U.logger.log(20, "... error, try again: {}-{}".format(expCommands.before,expCommands.after))
											elif ret == 2:	U.logger.log(20, "... timeout, try again: {}-{}".format(expCommands.before,expCommands.after))
											else:			U.logger.log(20, "... unexpected, try again: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(1)

								except Exception as e:
									U.logger.log(20,"", exc_info=True)
									if ii < ntriesConnect-1: 
										U.logger.log(20, "... error, try again")
										time.sleep(1)

							if not connected:
								U.logger.log(20, "connect error, giving up")
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
												U.logger.log(20,"... successful: {}-{}".format(expCommands.before,expCommands.after))
												success = True
												break
											else:
												if ii < ntriesConnect-1: 
													if ret in[1,2]:	U.logger.log(20, "... error, quit: {}-{}".format(expCommands.before,expCommands.after))
													elif ret == 3:	U.logger.log(20, "... timeout, quit: {}-{}".format(expCommands.before,expCommands.after))
													else:			U.logger.log(20, "... unexpected, quit: {}-{}".format(expCommands.before,expCommands.after))
											time.sleep(1)
											success = False
										if success: break 

								expCommands.sendline("disconnect" )
								U.logger.log(20,"sendline disconnect ")
								ret = expCommands.expect([">","Error",pexpect.TIMEOUT], timeout=5)
								if ret == 0:
									U.logger.log(20,"... successful: {}".format(expCommands.after))
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
def beep(hciUse, resetBLE=False):
	global beaconsOnline, beepBatteryBusy
	try:	
		restart = 0
		beepBatteryBusy  = min(beepBatteryBusy,1)
		while True: 
			if not os.path.isfile(G.homeDir+"temp/beaconloop.beep"): break
			beepBatteryBusy  = min(beepBatteryBusy,1)

			f = open(G.homeDir+"temp/beaconloop.beep","r")
			deviceList = f.read().strip("\n").split("\n")
			f.close()
			subprocess.call("rm {}temp/beaconloop.beep".format(G.homeDir), shell=True)
			U.logger.log(20,"beepBeacon deviceList:{}".format(deviceList))

			# devices: "{'24:DA:11:21:2B:20': {'cmdOff': 'char-write-cmd 0x0011 00', 'cmdON': 'char-write-cmd  0x0011  02', 'beepTime': 2.0}}"
			if beepBatteryBusy >0: beepBatteryBusy = 2
			for devices in deviceList:
				if len(devices) == 0: continue
				devices = json.loads(devices)
				if len(devices) == 0: continue
				expCommands = ""
				timestart = time.time()

				if resetBLE:
					stopHCUIDUMPlistener()
					time2 = tryDeltaTime(timestart)
					restart = 1
					time3 = tryDeltaTime(timestart)
					cmd = "sudo /bin/hciconfig {} reset".format(hciUse)
					ret =  ["",""] # readPopen(cmd)
					time4 = tryDeltaTime(timestart)
					if ret[1] !="":
						U.logger.log(20,"beepBeacon redo reset")
						ret = readPopen(cmd)
					U.logger.log(20,"beepBeacon reset:{}, exetime:{:.2f} {:.2f} {:.2f}".format(ret, time2,time3, time4))

				for mac in devices:
					#U.logger.log(20,"beepBeacon mac:{}".format(mac))
					if len(mac) < 10: continue
					params		= devices[mac]
					if "mustBeUp" in params and params["mustBeUp"]: force = False
					else:											force = True
					if  not force and mac not in beaconsOnline:
						U.logger.log(20,"mac: {}; skipping, not online or not in range".format(mac) )
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
						cmd = "sudo /usr/bin/gatttool -i {} {} -b {} -I".format(hciUse, random, mac) 
						U.logger.log(20,cmd)
						expCommands = pexpect.spawn(cmd)
						ret = expCommands.expect([">","error",pexpect.TIMEOUT], timeout=10)
						if ret == 0:
							U.logger.log(20,"... successful: {}-{}".format(expCommands.before,expCommands.after))
							connected = True
						else:
							if ii < ntriesConnect-1:
								if ret == 1:	U.logger.log(20, "... error, giving up: {}-{}".format(expCommands.before,expCommands.after))
								elif ret == 2:	U.logger.log(20, "... timeout, giving up: {}-{}".format(expCommands.before,expCommands.after))
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
									U.logger.log(20,"expect connect ")
									expCommands.sendline("connect ")
									ret = expCommands.expect(["Connection successful","Error", pexpect.TIMEOUT], timeout=15)
									if ret == 0:
										U.logger.log(20,"... successful: {}".format(expCommands.after))
										connected = True
										break
									else:
										if ii < ntriesConnect-1: 
											if ret == 1:	U.logger.log(20, "... error, try again: {}-{}".format(expCommands.before,expCommands.after))
											elif ret == 2:	U.logger.log(20, "... timeout, try again: {}-{}".format(expCommands.before,expCommands.after))
											else:			U.logger.log(20, "... unexpected, try again: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(1)

								except Exception as e:
									U.logger.log(20,"", exc_info=True)
									if ii < ntriesConnect-1: 
										U.logger.log(20, "... error, try again")
										time.sleep(1)

							if not connected:
								U.logger.log(20, "connect error, giving up")
								tryAgain = 0
					
							else:
								startbeep = time.time()
								lastBeep = 0
								success = True
								if beepTime > 0:
									for ii in range(50):
										if tryDeltaTime( lastBeep) > 10:
											for cc in cmdON:
												U.logger.log(20,"sendline  cmd{}".format( cc))
												expCommands.sendline( cc )
												ret = expCommands.expect([mac,"Error","failed",pexpect.TIMEOUT], timeout=5)
												if ret == 0:
													U.logger.log(20,"... successful: {}-{}".format(expCommands.before,expCommands.after))
													time.sleep(0.1)
													continue
												else:
													if ii < ntriesConnect-1: 
														if ret in[1,2]:	U.logger.log(20, "... error, quit: {}-{}".format(expCommands.before,expCommands.after))
														elif ret == 3:	U.logger.log(20, "... timeout, quit: {}-{}".format(expCommands.before,expCommands.after))
														else:			U.logger.log(20, "... unexpected, quit: {}-{}".format(expCommands.before,expCommands.after))
												success = False
												break
											lastBeep = time.time()
										if tryDeltaTime( startbeep) > beepTime: break
										time.sleep(1)
								if success:
									for cc in cmdOff:
										U.logger.log(20,"sendline  cmd{}".format( cc))
										expCommands.sendline( cc )
										ret = expCommands.expect([mac,"Error","failed",pexpect.TIMEOUT], timeout=5)
										if ret == 0:
											U.logger.log(20,"... successful: {}-{}".format(expCommands.before,expCommands.after))
											time.sleep(0.1)
										else:
											if ret in[1,2]:	U.logger.log(20, "... error: {}-{}".format(expCommands.before,expCommands.after))
											elif ret == 3:	U.logger.log(20, "... timeout: {}-{}".format(expCommands.before,expCommands.after))
											else:			U.logger.log(20, "... unknown: {}-{}".format(expCommands.before,expCommands.after))
										tryAgain = -1

								restart = 2
								expCommands.sendline("quit" )
								U.logger.log(20,"sendline quit ")
								ret = expCommands.expect([">","Error",pexpect.TIMEOUT], timeout=5)
								if ret == 0:
									U.logger.log(20,"... successful: {}".format(expCommands.after))
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
def getBeaconParameters(hciUse, resetBLE=True):
	global beaconsOnline
	#if G.getBatteryMethod == "batch":	getBeaconParametersBatch(hciUse, resetBLE=resetBLE)
	if True:							getBeaconParametersInteractive(hciUse,resetBLE=resetBLE)
	return 


#################################
def getBeaconParametersBatch(hciUse, resetBLE=True):
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

		if resetBLE:
			U.killOldPgm(-1,"hcidump")
			U.killOldPgm(-1,"hcitool")
			U.killOldPgm(-1,"lescan")
			time.sleep(0.2)

			cmd = "sudo /bin/hciconfig {} restart".format(hciUse)
			ret = readPopen(cmd)

		timeoutSecs = 15
		nTries = 3
		if "sensors" not in data: data["sensors"] = {}
		if "getBeaconParameters" not in data["sensors"]: data["sensors"]["getBeaconParameters"] ={}
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
#					devices:{'24:DA:11:21:2B:20': {'battCmd': {'random': 'public', 'bits': 63, 'uuid': '2A19', 'norm': 36}}}
#					after connect: 
#					char-read-uuid 2A19 

				cmd = "/usr/bin/timeout -s SIGKILL {}   /usr/bin/gatttool -i {} -b {} {} --char-read --uuid={}".format(timeoutSecs, hciUse, mac, random, uuid)
				# interactive cmd = "/usr/bin/timeout -s SIGKILL {}   /usr/bin/gatttool -i {} -b {} {} --char-read --uuid={}".format(timeoutSecs, hciUse, mac, random, uuid)
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
					U.logger.log(20,"try#:{}/{} ... ret: {}--{}; bits: {}; norm:{}; value-I: {}; B: {}; C: {}; d: {};  F: {} ".format(ii+1, nTries, ret[0], ret[1], bits, norm, valueI, valueB, valueC, valueD, valueF) )
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
def getBeaconParametersInteractive(hciUse, resetBLE=True):
	global beaconsOnline
	global beepBatteryBusy

	data = {} 
	try:	
		if not os.path.isfile(G.homeDir+"temp/beaconloop.getBeaconParameters"): return False

		f = open(G.homeDir+"temp/beaconloop.getBeaconParameters","r")
		devices = f.read().strip("\n")
		f.close()

		subprocess.call("rm {}temp/beaconloop.getBeaconParameters".format(G.homeDir), shell=True)

		devices = json.loads(devices)
		U.logger.log(20,"getBeaconParameters devices:{}".format(devices))
		if len(devices) ==0: return False

		if beepBatteryBusy >0: beepBatteryBusy = 2

		if resetBLE:
			stopHCUIDUMPlistener()
			U.logger.log(20,"stopped hcitools...")

			cmd = "sudo /bin/hciconfig {} restart".format(hciUse)
			ret = readPopen(cmd)
			U.logger.log(20,"restarted hcitools")

		timeoutSecs = 15
		nTries = 3
		if len(devices) > 1: 
			nTries = 2
			ntriesConnect = 2
		else:
			nTries = 3
			ntriesConnect = 5

		nsuccess = 0
		sendIfMoreThanSucess = 1
		if "sensors" not in data: data["sensors"] = {}
		if "getBeaconParameters" not in data["sensors"]: data["sensors"]["getBeaconParameters"] = {}
		success = False
		expCommands = ""
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
				batCMDs = params["gattcmd"]
				bits   = params["bits"]
				shift  = params["shift"]
				norm   = params["norm"]
				offset = params["offset"]
				if  params.get("startDelay","") !="":
					try: time.sleep(float(params["startDelay"]))
					except: pass			
#					devices:{'24:DA:11:21:2B:20': {'battCmd': {'random': 'public', 'bits': 63, 'uuid': '2A19', 'norm': 36}}}
#					after connect: 
#					char-read-uuid 2A19 

				tryAgain = nTries +1
				valueF = -2
				sucess = False
				expCommands = ""
				for kk in range(nTries):
					tryAgain -= 1
					if tryAgain < 0: break
					if tryAgain != 2 and expCommands != "":
						try: 
							expCommands.sendline("exit")	
						except: pass	

					if "random" in params and params["random"] == "randomON":	random = " -t random"
					else:					 									random = " "
					if expCommands != "":
						try: 
							expCommands.sendline("exit" )
							expCommands.kill(0)
							expCommands = ""
						except: pass

					cmd = "sudo /usr/bin/gatttool -i {} {} -b {} -I".format(hciUse, random, mac) 
					U.logger.log(20,cmd)
					expCommands = pexpect.spawn(cmd)
					ret = expCommands.expect([">","error",pexpect.TIMEOUT], timeout=10)
					if ret == 0:
						U.logger.log(10,"... successful: {}-{}".format(expCommands.before,expCommands.after))
						connected = True
					else:
						if ii < ntriesConnect-1:
							if ret == 1:	U.logger.log(20, "... error, giving up: {}-{}".format(expCommands.before,expCommands.after))
							elif ret == 2:	U.logger.log(20, "... timeout, giving up: {}-{}".format(expCommands.before,expCommands.after))
							else:			U.logger.log(20, "... unexpected, giving up: {}-{}".format(expCommands.before,expCommands.after))
						expCommands.kill(0)
						expCommands = ""
						time.sleep(0.1)
						break

					time.sleep(0.1)

					connected = False
					for ii in range(ntriesConnect):
						try:
							U.logger.log(20,"expect connect ")
							expCommands.sendline("connect ")
							ret = expCommands.expect(["Connection successful","Error","Function not implemented", pexpect.TIMEOUT], timeout=4)
							if ret == 0:
								U.logger.log(20,"... successful: {}".format(expCommands.after))
								connected = True
								break
							else:
								if ii < ntriesConnect-1: 
									if ret == 1:	U.logger.log(20, "... error, try again: {}-{}".format(expCommands.before,expCommands.after))
									elif ret == 2:	U.logger.log(20, "... timeout, try again: {}-{}".format(expCommands.before,expCommands.after))
									elif ret == 3:	U.logger.log(20, "... Function not implemented, try again: {}-{}".format(expCommands.before,expCommands.after))
									else:			U.logger.log(20, "... unexpected, try again: {}-{}".format(expCommands.before,expCommands.after))
							time.sleep(1)

						except Exception as e:
							U.logger.log(20,"", exc_info=True)
							if ii < ntriesConnect-1: 
								U.logger.log(20, "... error, try again")
								time.sleep(1)

					if not connected:
						U.logger.log(20, "connect error, giving up")
						tryAgain = 0
						break 

					success = False
					for ii in range(nTries):
						valueF = -2
						for cc in batCMDs:
							U.logger.log(20,"sendline  cmd:{}".format(cc))
							try: 
								time.sleep(float(cc)) 
								continue
							except:pass

							expCommands.sendline( cc )
							if cc.find("uuid") == -1: 
								retVal = expCommands.expect(["successful","Error","failed",pexpect.TIMEOUT], timeout=5)
								#U.logger.log(20,"{}... b successful:  before:>>{}<<".format(ii,expCommands.before))
								#U.logger.log(20,"{}... b successful:  after:>>{}<<".format(ii, expCommands.after))
								time.sleep(0.01)
								if retVal !=0: break
								continue

							retVal = expCommands.expect(["value: ","Error","failed",pexpect.TIMEOUT], timeout=5)
							if retVal == 0:
								U.logger.log(20,"{}... 1 successful:  before:>>{}<<".format(ii,expCommands.before.decode('utf_8')))
								U.logger.log(20,"{}... 1 successful:  after:>>{}<<".format(ii, expCommands.after.decode('utf_8')))
								retVal = expCommands.expect(["\r","Error","failed",pexpect.TIMEOUT], timeout=5)
								U.logger.log(20,"{}... 2 successful:  before:>>{}<<".format(ii,expCommands.before))
								U.logger.log(20,"{}... 2 successful:  after:>>{}<<".format(ii, expCommands.after))

								#U.logger.log(20,"... successful:  after:{}".format(expCommands.after))
								check = expCommands.before.decode("utf_8").split("\r")[0].strip()
								try:
									valueI = int(check,16)
								except:
									U.logger.log(20,"back data returned:>>{}<<".format(check))
									continue
								try:
										valueB = valueI & bits 
										valueC = valueB
										if   shift > 0: valueC *= shift 
										elif shift < 0:	valueC /= -shift
										valueD = max(0,valueC + offset)
										valueF = min(100, int( ( valueD *100. )/norm ))
								except Exception as e:
									U.logger.log(20,"", exc_info=True)
									continue
								U.logger.log(20,"try#:{}/{} ... check:'{}'; bits: {}; norm:{}; value-I: {}; B: {}; C: {}; d: {};  F: {} ".format(ii+1, nTries, check, bits, norm, valueI, valueB, valueC, valueD, valueF) )
								data["sensors"]["getBeaconParameters"][mac] = {"batteryLevel":valueF}
								if nsuccess > sendIfMoreThanSucess:
									if data != {}:
										U.sendURL(data, wait=True, squeeze=False)
										nsuccess = 0
										data["sensors"]["getBeaconParameters"] = {}

								if valueF != -2: 
									success = True
									if expCommands != "":
										expCommands.sendline("exit" )
										expCommands.kill(0)
									expCommands = ""
									break

							else:
								if ii < ntriesConnect-1: 
									if ret in [1,2]:	U.logger.log(20, "... error, quit: {}-{}".format(expCommands.before,expCommands.after))
									elif ret == 3:	U.logger.log(20, "... timeout, quit: {}-{}".format(expCommands.before,expCommands.after))
									else:			U.logger.log(20, "... unexpected, quit: {}-{}".format(expCommands.before,expCommands.after))

						if success: break
						if ii < nTries-1: time.sleep(0.2)
					if success: 
						break
					else:
						try: 
							if expCommands != "":
								expCommands.sendline("exit" )
								expCommands.kill(0)
								expCommands = ""
						except: pass
						expCommands = ""

		
			except Exception as e:
					U.logger.log(30,"", exc_info=True)

	except Exception as e:
			U.logger.log(30,"", exc_info=True)

	if data != {}:
		U.sendURL(data, wait=True, squeeze=False)
		time.sleep(0.5)
	try:
		if expCommands != "":
			expCommands.sendline("exit" )
			expCommands.kill(0)
	except:
		pass
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

def testComplexTag(hexstring, tag, mac, macplain, macplainReverse,  tagPos="", tagString="", calledFrom="" ):
	global knownBeaconTags, logCountTrackMac, trackMac
	try:
		doPrint = mac.find("xxB8:7C:6F:1A:") >-1 and tag.lower().find("isensor") >-1
		subtypeOfBeacon = ""
		inputString = copy.copy(hexstring)
		if tag != ""		: tagPos 		= int(knownBeaconTags[tag].get("pos",0))
		if tagString == ""	: tagString 	= knownBeaconTags[tag].get("hexCode","").upper()
		dPos 	 = 0
		posFound = -1

		tagString2						 	= knownBeaconTags[tag].get("hexCode2","").upper()
		matchString					 		= knownBeaconTags[tag].get("match",False)

		if tagString.find("-") > -1: # 
			tagString = tagString[:-1]
		lTag = len(tagString)
		lTag2 = len(tagString2)

		if doPrint:	U.logger.log(20,"mac:{}, tag:{}, tagString:{}, hexstr:{}".format(mac, tag, tagString, hexstring[12:]))

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			if tag == "":
				writeTrackMac("tst-0   ","matchString:{}; tagPos:{}; lTag:{} tagString: {}; tagString2:{} ".format(matchString, tagPos, lTag, tagString, tagString2 ), mac)
			else:
				writeTrackMac("tst-0   ","matchString:{}; tagPos:{}; lTag:{}, tag:{}; tagString: {}; tagString2:{} ".format(matchString, tagPos, lTag, tag, tagString,tagString2 ), mac)

		if lTag > len(inputString): 
			if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("tst-L1  "," reject length ", mac)
			return posFound, dPos, subtypeOfBeacon

		elif lTag + lTag2 > len(inputString): 
			if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("tst-L2  "," reject length ", mac)
			return posFound, dPos, subtypeOfBeacon


		if tagString.find("X") >-1:
			indexes = [n for n, v in enumerate(tagString) if v == "X"] 
			inputString 	= list(inputString.upper())
			#writeTrackMac("tag-0   ","indexes:{}".format(indexes), mac)
			for ii in indexes:
				if ii+tagPos < len(inputString):
					inputString[ii+tagPos] = "X"
				else: return -1, 100, ""
			inputString = ("").join(inputString)

		if tagString.find("RMAC########") >-1:
			tagString = tagString.replace("RMAC########", macplainReverse)

		elif tagString.find("MAC#########") >-1:
			tagString = tagString.replace("MAC#########", macplain)

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tst-1   ","tagString   fin: {} + {} ".format(tagString, tagString2), mac)
			writeTrackMac("tst-1   ","inputString:     {}".format(inputString), mac)


		if matchString: 
			if inputString[:lTag] != tagString:
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

		if lTag2 > 0 and posFound > -1 and dPos == 0:
			if inputString.find(tagString2) == -1: posFound = -1; dPos = 99

		if len(inputString) < lTag + tagPos: posFound =-1; dPos = 100

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("tst-F   ","posFound: {}, dPos: {}, tag: {}, tagString: {}".format(posFound, dPos, tag, tagString), mac)
		if doPrint:	U.logger.log(20,"mac:{}, taginKnow:{}, posFound:{}, tag:{}, tagString:{}, inputString:{}, hexstr:{}".format(mac, tag in knownBeaconTags, posFound, tag, tagString, inputString, hexstring[12:]))
		if  posFound > -1 and dPos == 0 and tag !="" and tag in knownBeaconTags :
			#if tag == "iBSxx":U.logger.log(20,"{} tag:{}==\n  {},\n{} ".format(mac, tag,  tagString, hexstring))
			if "subtypeOfBeacon" in knownBeaconTags[tag] and knownBeaconTags[tag]["subtypeOfBeacon"] != {}:
				subtypeOfBeacon = knownBeaconTags[tag]["subtypeOfBeacon"]
				if doPrint: U.logger.log(20," {} posFound:{},   has subDevtype:{}, calledFrom:{}, hexstring:{}".format(mac,posFound, subtypeOfBeacon, calledFrom, hexstring))
				pos = subtypeOfBeacon["pos"]
				mask = subtypeOfBeacon["mask"]
				intHex = subtypeOfBeacon["intHex"]
				length = subtypeOfBeacon["length"]
				if len(hexstring) > pos+length:
					if intHex == "int":
						dataTAG = intFrom8(hexstring, pos)& mask
					else:
						dataTAG = hexstring[pos:pos+length]

					if doPrint:U.logger.log(20,"{} has  compare:{}-{}".format(mac, hexstring[pos:pos+length], dataTAG))
					for devTypeID in subtypeOfBeacon["devTypeID"]:
						if intHex == "int":
							searchTAG = intFrom8(devTypeID,0)
						else:
							searchTAG = devTypeID
						if doPrint:U.logger.log(20,"{}           to:{}-{}".format(mac, devTypeID, searchTAG))
						if dataTAG == searchTAG:
							subtypeOfBeacon = subtypeOfBeacon["devTypeID"][devTypeID]
							if doPrint:U.logger.log(20," {} has subtypeOfBeacon is :{}".format(mac, subtypeOfBeacon))
							break

		return posFound, dPos, subtypeOfBeacon
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,"Mac#:{}, tag:{}".format(mac, tag, ))
	return -1,100, ""


#################################
def parsePackage(mac, hexstring, logData=False): # hexstring starts after mac#
	global bleServiceSections, bleServiceSectionsReverse, parsedData

	# 16 02 01 06   12 FF 0D 00 83 BC 20 01 00 AA AA FF FF 00 00 19 06 00 00 C6
	# LL ll tp fl   ll  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 rssi
	# LL= 22
	#    ll = 2, tp = 01= flags flag = 06
	#               ll = 18; tp = FF = UUID
	#  rssi =  C6


	# 1C 11 07 1B C5 D5 A5 02 00 B8 9F E6 11 4D 22 00 0D A2 CB   09 16 00 0D 63 D0 CE 00 11 04
	# LL ll tp  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17   ll tp  2  3  4  5  6  7  8  9
	# LL = 16+13 = 29
	#    ll= 17, tp = 07 = 128BServClcmplt
	#                                                            ll = 9,  tp = ServiceData 
	try:
		doPrint = mac.find("xxB8:7C:6F:1A:") > -1

		totalLength = int(hexstring[0:2],16)

		if totalLength < 6: return {}
		parsedData[mac] = {"len": totalLength, "sections":[], "analyzed":{"code":{},"text":{}}, "posFound":-1, "dPos":100, "subtypeOfBeacon":"", "testTag":""}
		sectionsData = []
		analyzed = {"text":{},"code":{}}
		startOfSection = 0
		lenSection = 0
		if ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
				writeTrackMac("pars0   ","totalLength:{}; hexstring: {}; ".format(totalLength,  hexstring ), mac)

		if doPrint:  U.logger.log(20," mac:{:}, parsedData:{}".format(mac, hexstring))
		for ii in range(8):


			startOfSection = startOfSection + lenSection*2 +2 #  from previous section
			if startOfSection > totalLength*2: break

			try: lenSection  = int(hexstring[startOfSection:startOfSection+2],16)
			except: continue

			if lenSection > 0: 
				sectionCode = hexstring[startOfSection+2:startOfSection+4]
				sectionName = bleServiceSections.get(sectionCode,"unknown")

				section = hexstring[startOfSection+4: startOfSection+4 + lenSection*2 -2]

				analyzed["code"][sectionCode] = section
				analyzed["text"][sectionName] = section
				if doPrint:  U.logger.log(20," mac:{:}, startOfSection:{}, lenSection:{}, sectionCode:{}, section:{}".format(mac, startOfSection, lenSection, sectionCode, section))

				# special cases: 08, 09, FF  16 overwrite hex strings 
				if sectionCode in ["08","09"]: # names translate to ascii 
					dd = ""
					ll = int(len(section)/2)
					for kk in range(ll):
						x = section[kk*2:kk*2+2]
						if x == "00":  dd += "~"
						else:
							x = hex2str(x)
							if x == "00": 	dd += "~"
							else:			dd += x
					if  logData or ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
						writeTrackMac("parsM   ","Name: section:{}, dd:{}, ll:{}".format( section, dd, ll ), mac)

					analyzed["text"]["mfg_info"] = dd
					analyzed["text"][sectionName] = dd
					analyzed["code"][sectionCode] = dd

				elif sectionCode ==  "FF": # ManufacturerSpecificData
					if section[0:8] =="4C00":
						try:
							uuidEnd = 8+2*16
							iBeacon = section[8:uuidEnd] +"-"+str(int(section[uuidEnd:uuidEnd+4],16)) +"-"+str(int(section[uuidEnd+4:uuidEnd+4+4],16))
							analyzed["text"]["iBeacon"] = iBeacon
						except:
							continue

				elif sectionCode == "16": #ServiceData-16-bitUUID
					xxx = getTLMdata(mac, section, verbose=False)
					if xxx != {}:
						analyzed["text"]["TLM"] = xxx


				if  ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
						writeTrackMac("parsT   "," startOfSection:{:2d}, sectionCode:{},  sectionsData:{}".format( startOfSection, sectionCode, section), mac)

		if  ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
			writeTrackMac("parsE   "," lenTotal:{}, data:{}, hexstr:{}".format( totalLength, analyzed, hexstring), mac)

		parsedData[mac]["analyzed"] = analyzed
		if doPrint: 
			U.logger.log(20," mac:{:}, parsedData:{}".format(mac, parsedData[mac]))

		return 	
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30," hexstr:{}".format(hexstring))
	return 



#################################
def getTLMdata(mac, section, verbose = False):
	try:
		retData = {}
		tagPos = section.find("AAFE2000") # tag for TLM data 

		if tagPos == -1: 					return retData

		section = section[tagPos:]

		if verbose: 
			U.logger.log(20," mac:{:}, llsec:{} section:{}".format(mac, len(section), section))

		if  len(section) < 32:	return retData

		startNext	= 8

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
			U.logger.log(20," mac:{:}, Vbat:{:}={:4d}; temp:{:}={:.2f}, advCount:{:}={:10d}, timeSince:{:}={:12.1f}, hex:{:}".format(mac, VbatH, Vbat, tempH, temp, advCountH, advCount, timeSinceH, timeSince, section))

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30," hexstr:{}".format(hexstring))
	return retData


#################################
def checkForValueInfo( tag, tagFound, mac, hexstr ):
	global knownBeaconTags
	global trackMac, logCountTrackMac
	global getMsgInfoCmds
	try:


		if mac == trackMac and logCountTrackMac >0:
			writeTrackMac("Val-0   ","tag:{}; tagFound:{}; tagin:{}; hexstr:{}".format(tag, tagFound, tag in knownBeaconTags, hexstr), mac )
		decodedData = {}
		verbose = mac == "xxD1:AD:6B:3D:AB:2D"
		if verbose:	U.logger.log(20,"mac:{}, tag:{}, tagFound:{}, hexstr:{}".format(mac, tag, tagFound, hexstr[12:]))
		if tag in knownBeaconTags and tagFound == "found" and "commands" in knownBeaconTags[tag]:
			for cmdName in knownBeaconTags[tag]["commands"]:
				cmdDict = knownBeaconTags[tag]["commands"][cmdName]
				if cmdDict is None: continue
				if cmdDict == "": continue
				if cmdDict == {}: continue
				if type(cmdDict) == type(""): continue
				if cmdDict.get("type","") != "msgGet": continue
				if "params" not in cmdDict: continue
				params = cmdDict["params"]
				decodedData[cmdName] = ""
				useAdv = cmdDict.get("useAdv","") 
				try:
					if  verbose:
						#U.logger.log(20,"mac:{}, tag:{}, cmd:{}, params:{}".format(mac, tag, cmdName, params))
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

						if useAdv == "":
							bHexStr = hexstr[12:]
							Bstring =  bHexStr[pos:pos+length*2]
						else:
							bHexStr = parsedData[mac]["analyzed"]["code"].get(useAdv,"")
							if bHexStr == "": continue
							Bstring = bHexStr[pos:pos+length*2]

						if reverse:
							Bstring = Bstring[2:4]+Bstring[0:2]
						if nType =="float":	decodedData[cmdName] = float(int(Bstring,16)&andWith)/norm
						else:				decodedData[cmdName] = (int(Bstring,16)&andWith)//norm

						if nType == "int": 		decodedData[cmdName] = int(decodedData[cmdName]+0.5)
						if nType == "bool": 	decodedData[cmdName] = decodedData[cmdName] != 0
						if nType == "float": 	decodedData[cmdName] = float(decodedData[cmdName])
						if nType == "string": 	decodedData[cmdName] = resultON if decodedData[cmdName] else resultOFF
						if nType == "bits": 	decodedData[cmdName] = "{:08b}".format(decodedData[cmdName])
						if verbose:  U.logger.log(20,"{}: cmdName:{:15s}, bHexStr:{} pos:{}, hex:{}, norm:{}, length:{}, andWith:{}, reverse:{}, Bstring:{}, andResult:{}, resultON:{}, resultOFF:{}, res:{}".format(mac, cmdName, bHexStr, pos, Bstring, norm, length, andWith, reverse, Bstring, int(Bstring,16)&andWith, resultON, resultOFF, decodedData[cmdName] ) )
						if mac == trackMac and logCountTrackMac >0:
							writeTrackMac(cmd[0:3]+"-4   ", "val:{}".format(cmd[0:3],decodedData[cmdName] ),  mac )

				except	Exception as e:
					U.logger.log(30,"", exc_info=True)
					if mac == trackMac and logCountTrackMac >0:
						U.logger.log(20,"", exc_info=True)
					decodedData[cmdName] = ""

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return decodedData


#################################
def checkIfTagged(mac, macplain, macplainReverse, hexstr, batteryLevel, rssi, txPower):
	global trackMac, logCountTrackMac, onlyTheseMAC, knownBeaconTags
	global beaconNew, beacon_ExistingHistory, ignoreMAC
	global acceptNewiBeacons, acceptNewBeaconMAC, acceptNewTagiBeacons, acceptNewMFGNameBeacons
	global batteryLevelUUID
	global parsedData
	try:
		prio  				= -1
		dPos  				= -100
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
		tagOld				= ""

		iBeacon  = parsedData[mac]["analyzed"]["text"].get("iBeacon","")
		mfg_info = parsedData[mac]["analyzed"]["text"].get("mfg_info","")

		if "TLM" in parsedData[mac]["analyzed"]["text"] and "batteryVoltage" in  parsedData[mac]["analyzed"]["text"]["TLM"]:
			batteryVoltage = parsedData[mac]["analyzed"]["text"]["TLM"]["batteryVoltage"]
			temp = parsedData[mac]["analyzed"]["text"]["TLM"]["temp"]
			TLMenabled = True
		else:
			TLMenabled = ""
			batteryVoltage = 0
			temp = 20.
			
		doPrint = mac.find("xxB8:7C:6F:1A:") > -1
		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("parse   ", "parsedData {}".format(parsedData[mac]), mac)

		setEmptybeaconsThisReadCycle(mac)
		if doPrint: U.logger.log(20,"{} pass1 tagFound:{}, tagOld:{}".format(mac, tagFound, tagOld) )

		### is this a know beacon with a known tag ?
		rejectThisMessage 	= "reject"
		tagFound 			= "failed"
		if existing:  
			tagOld 			= onlyTheseMAC[mac].get("typeOfBeacon","")
			useOnlyIfTagged = onlyTheseMAC[mac].get("useOnlyIfTagged",0) # this is from props, device edit settings, overwrites default

			if useOnlyIfTagged == 0: 
				rejectThisMessage = "all"

			if tagOld not in ["", "other"]:
				if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
					writeTrackMac("tag-1   ", "tag:{}, useOnlyIfTagged: {}".format(tagOld, useOnlyIfTagged), mac)

				if  tagOld in knownBeaconTags:
					posFound, dPos, subtypeOfBeacon = testComplexTag(hexstr[12:-2], tagOld, mac, macplain, macplainReverse, calledFrom="checkIfTagged-1")
					if tagOld == "iBeacon" and iBeacon != "":
						rejectThisMessage = tagOld

					if posFound == -1 or abs(dPos) > knownBeaconTags[tagOld]["posDelta"]:
						tagFound = "failed"
					else: 
						tagFound = "found"
						rejectThisMessage = tagOld
						typeOfBeacon = tagOld

				else: 
					tagFound = "failed"

			if tagFound == "found": 
				parsedData[mac]["posFound"] = posFound
				parsedData[mac]["dPos"] = dPos
				parsedData[mac]["subtypeOfBeacon"] = subtypeOfBeacon
				parsedData[mac]["testTag"] = tagOld

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-5   ", "rejectThisMessage:{}, tagFound:{};".format(rejectThisMessage, tagFound),mac)

		if doPrint: U.logger.log(20,"{} pass1 tagFound:{}, tagOld:{}".format(mac, tagFound, tagOld) )

		## mac not in current list, check if should look for it = accept new beacons?
		# 1. not existing: accept  if match w acceptNewTagiBeacons or mfg tag match 
		# 2. if exists check for tag other than "other"

		if not existing and acceptNewMFGNameBeacons not in ["","off"]:
			## check if in tag list
			if  mfg_info.lower()[0:len(acceptNewMFGNameBeacons)].find(acceptNewMFGNameBeacons.lower()) == 0: 
				rejectThisMessage = mfg_info
				mfgTagged = True

		testTag = ""
		if doPrint:  U.logger.log(20,"{} testing  .. acceptNewMFGNameBeacons:{}, mfg_info:{}, acceptNewTagiBeacons:{}, tagOld:{}, existing:{},".format(mac, acceptNewMFGNameBeacons, mfg_info, acceptNewTagiBeacons, tagOld, existing) )
		if (
			(existing and tagOld in ["", "other"]) or  # check if we find a better tag than "other"
			( not existing  and  (acceptNewTagiBeacons != "off"  or mfgTagged)   ) # if not existing try to find tag if enabled 
			):

			for testTag in knownBeaconTags:
				if doPrint and testTag.lower().find("isensor") >-1:  U.logger.log(20,"{} testing  testTag:{}=={}, ".format(mac, testTag, knownBeaconTags.get(testTag,"")) )
				if testTag in ["other", tagOld, "iBeacon"]: 		continue
				if knownBeaconTags[testTag]["pos"] == -1: 			continue
				posFound, dPos, subtypeOfBeacon = testComplexTag(hexstr[12:-2], testTag, mac, macplain, macplainReverse, calledFrom="checkIfTagged-2")
				if posFound == -1: 									continue
				if abs(dPos) > knownBeaconTags[testTag]["posDelta"]:continue
				if doPrint and testTag.lower().find("isensor") >-1:  U.logger.log(20,"{} 2 tagOld:{}, testing  testTag:{}, posFound:{}, check:{}".format(mac, tagOld, testTag, posFound, acceptNewTagiBeacons == "all" or acceptNewTagiBeacons == testTag or tagOld in ["", "other"]) )
				if acceptNewTagiBeacons == "all" or acceptNewTagiBeacons == testTag or (existing and tagOld in ["", "other"]):
					typeOfBeacon 		= testTag
					tagFound 			= "found"
					rejectThisMessage 	= testTag
					parsedData[mac]["posFound"] = posFound
					parsedData[mac]["dPos"] = dPos
					parsedData[mac]["subtypeOfBeacon"] = subtypeOfBeacon
					parsedData[mac]["testTag"] = testTag
					break
				if tagFound == "found": break

		if tagFound != "found" and acceptNewTagiBeacons == "all":
			tagFound = "found"
			typeOfBeacon = "other"
			rejectThisMessage = "other"

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-6   ", "  batteryLevel:{} tagFound: {}, rejectThisMessage: {}".format( batteryLevel, tagFound, rejectThisMessage) ,mac)

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

		decodedDatas = checkForValueInfo( typeOfBeacon, tagFound, mac, hexstr )
		if batteryLevel != "" or "batteryLevel" not in decodedDatas: decodedDatas["batteryLevel"] = batteryLevel

		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-9   ", "batteryLevel>{}<".format(decodedDatas["batteryLevel"]) ,mac)

		if decodedDatas["batteryLevel"] == "" and batteryVoltage !=0: 
			batteryVoltAt100 = 3000.
			batteryVoltAt0   = 2700.
			if mac in  batteryLevelUUID and batteryLevelUUID[mac].find("TLM") == 0: # format is TLM-Vol@0-Volt@100%
				levels = batteryLevelUUID[mac].split("-")
				if len(levels) == 3:
					batteryVoltAt100 = float(levels[1]) 
					batteryVoltAt0   = float(levels[2]) 
				#if mac =="C1:68:AC:83:13:FD": U.logger.log(20,"mac {}; 0:{};  100:{}".format(mac, batteryVoltAt0,batteryVoltAt100))
			decodedDatas["batteryLevel"] = batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=batteryVoltAt100, batteryVoltAt0=batteryVoltAt0)

		if doPrint:  U.logger.log(20,"mac {}; decodedDatas[]:{};  batteryLevel:{}".format(mac, decodedDatas["batteryLevel"] , batteryLevel))
		fillbeaconsThisReadCycle(mac, rssi, txPower, iBeacon, mfg_info, typeOfBeacon, subtypeOfBeacon, TLMenabled, decodedDatas, parsedData[mac]["analyzed"]["text"])

		if not checkMinMaxSignalAcceptMessage(mac, rssi): rejectThisMessage = "reject"

		if rejectThisMessage != "reject" and mac in beaconsThisReadCycle: fillHistory(mac)

		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-E   ", "beaconsThisReadCycle ..mfg_info: {}, rejectThisMessage:{},  iBeacon: {}, batteryLevel>{}<".format(mfg_info, rejectThisMessage, iBeacon, batteryLevel) ,mac)
		if doPrint:  U.logger.log(20, "mac:{}  after end of  decodedDatas:{}".format(mac, decodedDatas ))


	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	if rejectThisMessage == mfg_info:
		pass
		#U.logger.log(20,"{} accepted .. rejectThisMessage:{}".format(mac, rejectThisMessage) )
	if doPrint:  U.logger.log(20,"{} 5 rejectThisMessage:{}, typeOfBeacon:{}, ".format(mac, rejectThisMessage, typeOfBeacon) )
	return rejectThisMessage


#################################
def getStdIbeacon(hexstr):
	try:
		macplainReverse = hexstr[0:12]
		macplain 		= macplainReverse[10:12]+macplainReverse[8:10]+macplainReverse[6:8]+macplainReverse[4:6]+macplainReverse[2:4]+macplainReverse[0:2]
		mac 			= macplain[0:2]+":"+macplain[2:4]+":"+macplain[4:6]+":"+macplain[6:8]+":"+macplain[8:10]+":"+macplain[10:12]
		txPower	 		= signedIntfrom8(str(signedIntfrom8(hexstr[-4:-2])))
		rssi			= signedIntfrom8(hexstr[-2:])
		msgStart		= 14

		return 	  rssi, txPower, macplainReverse, macplain, mac
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return    rssi, txPower, macplainReverse, macplain, mac




#################################
def fillbeaconsThisReadCycle(mac, rssi, txPower, iBeacon, mfg_info, typeOfBeacon, subtypeOfBeacon, TLMenabled, decodedData, analyzed):
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

		for  ii in decodedData:
			if decodedData[ii] != "":		beaconsThisReadCycle[mac][ii]				= decodedData[ii]
		beaconsThisReadCycle[mac]["analyzed"]				= analyzed
		if mac == "xxC6:8F:F7:A5:8C:14":
			U.logger.log(20,"mac:{}, decodedData:{}".format(mac, decodedData))

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 

#################################

def checkIfBLEprogramIsRunning(hciUse):
	global rpiDataAcquistionMethod

	try:
		if not U.checkIfHCiUP(hciUse, verbose=True):
			U.logger.log(30,"{} not up".format(hciUse))
			return False

		if  rpiDataAcquistionMethod.find("socket") == 0: 
			return True

		if not U.pgmStillRunning("hcidump -i", verbose=True): # and U.pgmStillRunning("hcitool -i", verbose=True):
			U.logger.log(30,"hcidump  not up")
			return False

		return True

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return False


#################################
#################################
######## BLE SENSORS END  #######
#################################
#################################




#################################
def startHCIcmdThread():
	global threadCMD

	U.logger.log(20, "start cmd thread ")
	try:
		threadCMD = {}
		threadCMD["state"]   = "start"
		threadCMD["thread"]  = threading.Thread(name='loopCheck', target=loopCheckBeepBattery)
		threadCMD["thread"].start()
		threadCMD["state"]   = "running"

	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 



#################################
def loopCheckBeepBattery():
	global threadCMD
	global hciCheckLastTime, useHCIForBeep, useHCIForBeacon
	global beepBatteryBusy


	resetBLE = False
	while threadCMD != "stop":
		try:
			checkIfBeep = beep(useHCIForBeep, resetBLE = resetBLE)
			checkIfBat =  getBeaconParametersInteractive(useHCIForBeep, resetBLE = checkIfBeep <2 and resetBLE)
			if  ( checkIfBeep > 0 or checkIfBat) and  useHCIForBeep == useHCIForBeacon:
				U.restartMyself(param="", reason="beep/bat", python3=usePython3)

			time.sleep(0.1)

			checkWhichHCIForBeep()	
			if beepBatteryBusy >0: beepBatteryBusy = 1

		except  Exception as e:
			U.logger.log(30,"", exc_info=True)
			time.sleep(20)
	return 

#################################
def checkWhichHCIForBeep():
	global hciCheckLastTime, useHCIForBeep, useHCIForBeacon
	global HCIs
	global beepBatteryBusy

	try:
		if tryDeltaTime( hciCheckLastTime) < 0:
			return 

		if useHCIForBeep == "": 
			useHCIForBeep = useHCIForBeacon
			beepBatteryBusy = 1

		hciCheckLastTime = time.time() + 50.
		hciUsedByBLEconnect, raw  = U.readJson("{}temp/BLEconnect.hci".format(G.homeDir))
		#hciUsedBybeep, raw  = U.readJson("{}temp/beaconbeep.hci".format(G.homeDir))  # not needed 
		#{'hci': {'hci1': {'bus': 'USB', 'numb': 1, 'upDown': 'UP', 'BLEmac': '5C:F3:70:6D:D9:4A'}, 'hci0': {'bus': 'USB', 'numb': 0, 'upDown': 'UP', 'BLEmac': '5C:F3:70:6D:D9:4D'}, 'hci2': {'bus': 'UART', 'numb': 2, 'upDown': 'UP', 'BLEmac': 'B8:27:EB:F4:B0:82'}}, 'ret': ['hci1:\tType: Primary  Bus: USB\n\tBD Address: 5C:F3:70:6D:D9:4A  ACL MTU: 1021:8  SCO MTU: 64:1\n\tUP RUNNING \n\tRX bytes:3527 acl:0 sco:0 events:212 errors:0\n\tTX bytes:6047 acl:0 sco:0 commands:212 errors:0\n\nhci0:\tType: Primary  Bus: USB\n\tBD Address: 5C:F3:70:6D:D9:4D  ACL MTU: 1021:8  SCO MTU: 64:1\n\tUP RUNNING \n\tRX bytes:161825 acl:47 sco:0 events:5462 errors:0\n\tTX bytes:8170 acl:40 sco:0 commands:336 errors:0\n\nhci2:\tType: Primary  Bus: UART\n\tBD Address: B8:27:EB:F4:B0:82  ACL MTU: 1021:8  SCO MTU: 64:1\n\tUP RUNNING \n\tRX bytes:72804 acl:0 sco:0 events:4552 errors:0\n\tTX bytes:83050 acl:0 sco:0 commands:4552 errors:0\n\n', '']}	

		HCIList = HCIs["hci"]
		for hci in HCIList:
			#U.logger.log(30,"hci:{}".format(hci))
			if hci == useHCIForBeacon: continue
			if hci == hciUsedByBLEconnect.get("usedHCI",""): continue
			if HCIList[hci]["upDown"] != "UP": continue
			beepBatteryBusy = 0
			if useHCIForBeep != hci:
				#U.logger.log(20,"use for beep:{}".format(hci))
				U.logger.log(20,"useHCIForBeacon:{}, hciUsedByBLEconnect:{}, HCIList:{}".format(useHCIForBeacon, hciUsedByBLEconnect,HCIList))
				data = {"data":{"hciInfo_beep":"{}-{}-{}".format(hci, HCIList[hci]["bus"], HCIList[hci]["BLEmac"]) }}
				if hciUsedByBLEconnect.get("usedHCI","") == "":
					data["data"]["hciInfo_BLEconnect"] = ""
				U.sendURL( data=data, squeeze=False, wait=False )

			useHCIForBeep = hci
			cmd = "sudo hciconfig "+useHCIForBeep+" reset &"
			readPopen(cmd)
			U.writeFile("temp/beaconbeep.hci", json.dumps({"usedHCI":useHCIForBeep, "myBLEmac": HCIList[hci]["BLEmac"], "usedBus": HCIList[hci]["bus"],"pgm":"beaconbeep"}))
			#U.logger.log(20,"useHCIForBeacon:reset {}".format(useHCIForBeep))
			return 


	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30," HCIs:{}".format(HCIs))

	useHCIForBeep = useHCIForBeacon
	U.writeFile("temp/beaconbeep.hci", json.dumps({"usedHCI":useHCIForBeep, "myBLEmac": HCIList[useHCIForBeacon]["BLEmac"], "usedBus": HCIList[useHCIForBeacon]["bus"]}))
	beepBatteryBusy = 1
	return 




#################################
def doLoopCheck(sensor):
	global reasonMax
	global sensCheckLastTime, paramCheckLastTime
	global useHCIForBeacon

	try:		
		resetBLE = False

		if tryDeltaTime( sensCheckLastTime) > 0:
			sensCheckLastTime =  time.time() +2		

			checkIFtrackMacIsRequested()

			if U.checkNowFile(sensor): reasonMax = max(reasonMax, 7)

			if BLEAnalysisStart(useHCIForBeacon):
				U.restartMyself(param="", reason="BLEanalysis", python3=usePython3)

			if updateTimeAndZone(useHCIForBeacon):
				U.restartMyself(param="", reason="updateTimeAndZone", python3=usePython3)
	

		if  tryDeltaTime(paramCheckLastTime )> 0:
			if readParams(): reasonMax = max(reasonMax, 8) # new params
			paramCheckLastTime = time.time() +10 


		return 

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 


def getSocketData(sock):
	Msgs = []
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

		U.logger.log(30,"", exc_info=True)
		time.sleep(1)
		U.restartMyself(param="", reason="sock.recv error", python3=usePython3)
		return []
	return Msgs

def setupSOCKET(sock):
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
	return old_filter


def setBeaconLastMsgTS(mac, setBy=""):
	global beaconLastMessageTS
	global findMAC, trackMac, logCountTrackMac

	beaconLastMessageTS[mac] = time.time()
	if  ((mac == trackMac or trackMac =="*") and logCountTrackMac > 0):
		U.logger.log(20, "mac:{} set  beaconLastMessageTS by:{}" .format(mac, setBy))


def setBeaconLastMsgSendTS(mac, setBy=""):
	global beaconLastMessageSendTS
	global findMAC, trackMac, logCountTrackMac

	beaconLastMessageSendTS[mac] = time.time()
	if  ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
		U.logger.log(20, "mac:{} set  beaconLastMessageSendTS by:{}" .format(mac, setBy))




####### main pgm / loop through package set  ############
def loopThroughMessagesInThisSet(Msgs, timeAtLoopStart, sendAfter, tt):
	global lastMSGwithGoodData, lastMSGwithDataPlain, nMessagesSend, nMsgs, lastMessageOK, lastMSGwithDataPassed, lastTimeMAC
	global trackMac, logCountTrackMac, beaconLastMessageTS
	global BLEsensorMACs, onlyTheseMAC, acceptNewBeaconMAC, acceptNewMFGNameBeacons, acceptNewiBeacons, acceptNewTagiBeacons, messageStats
	global ignoreBeaconsIfRssiLessThan
	global findMAC

	messageBad = False
	for hexstr in Msgs: 
		try:
			if tt - timeAtLoopStart	 > sendAfter: 
				#U.logger.log(20,  "dt inner :{:.1f} limit:{},  ".format(tt - timeAtLoopStart, sendAfter))
				break # send curl msgs after collecting for xx seconds
			hexstr = fillHCIdump(hexstr)
			nCharThisMessage	= len(hexstr)
			#dtinner[4][1] = max(dtinner[1], tryDeltaTime( startofInnerLoop, oneDigit=True ))
	
			lastMessage = hexstr
			# restart if junk data 
			if nCharThisMessage < 16: 
				return True
			if nCharThisMessage > 110:  # 55 bytes cutoff normally max 31 bytes 
				return  True
	
			lastMessageOK = hexstr
			startHCITries = 0 # reset simple hci startup to ok
	
			#dtinner[4][2] = max(dtinner[2], tryDeltaTime( startofInnerLoop, oneDigit=True ))
			lastMSGwithDataPlain = time.time()


			rssi, txPower, macplainReverse, macplain, mac  = getStdIbeacon(hexstr)

			doPrint = mac.find("xxB8:7C:6F:1A:") >-1

			if doPrint : #or mac in findMAC: 
				U.logger.log(20,  "mac:{:}, hexstr:{:}\n".format(mac,  hexstr[12:]))

			if mac not in parsedData:
				parsedData[mac] = {}
			if mac in BLEsensorMACs or mac in onlyTheseMAC or mac in acceptNewBeaconMAC  or acceptNewMFGNameBeacons not in ["","off"] or acceptNewiBeacons > -200 or acceptNewTagiBeacons not in ["","off"]:
				try:  parsePackage(mac, hexstr[12:], logData=False)
				except: continue


			setBeaconLastMsgTS(mac, "received")

			if mac == trackMacNumber:# or mac in findMAC:
				U.logger.log(20,  "mac:{:}, DT:{:4.1f}, new data: rssi:{}>{}?, hexstr:{:}\n".format(mac, tryDeltaTime(lastTimeMAC), rssi, ignoreBeaconsIfRssiLessThan, hexstr[12:]))
				lastTimeMAC = time.time()

			if readFrom != "":
				U.logger.log(20, "mac:{}, data:{}".format(mac, hexstr[12:]))

			########  track mac  start / end ############
			trackMacStopIf(hexstr, mac)
			#dtinner[4][2] = max(dtinner[2], tryDeltaTime( startofInnerLoop,oneDigit=True ))

			if rssi < ignoreBeaconsIfRssiLessThan: continue

			if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("basic   ","  RX :{}, TX: {}".format( rssi, txPower) ,mac)


			# check if this is a sensor, will send its own msg to mac, and will return battery level if present 
			sensor = ""
			batteryLevel = ""

			# do sensor macs, also for ignored beacons, use only sensor info
			if mac  in BLEsensorMACs:
				sensor, txPower, batteryLevel = doSensors( mac, macplain, macplainReverse, rssi, txPower, hexstr)

			if sensor != "": nMessagesSend +=1
			# check if known rejected mac
			if mac in ignoreMAC: 
				if readFrom !="":
					U.logger.log(20, "TestMode: ignored mac:{}".format(mac))
				continue # set to ignore in plugin

			if  not (mac in onlyTheseMAC): 
				# 		accept if rssi				accept spec mac				accept tag							accept mfg tag			if one is tru do not skip	
				if not ( rssi > acceptNewiBeacons or  acceptNewBeaconMAC != "" or  acceptNewTagiBeacons != "off" or  acceptNewMFGNameBeacons not in ["","off"] ):
				#U.logger.log(20,  "{} {:.1f}  mac:{:}, rejecting {} {} {} {} {} {}".format( datetime.datetime.now().strftime("%H:%M:%S.%f")[:-5], tryDeltaTime( lastTimeMAC), mac,  mac not in onlyTheseMAC, rssi < acceptNewiBeacons,  acceptNewBeaconMAC == "",  acceptNewTagiBeacons == "off", acceptNewMFGNameBeacons in ["","off"],  mac  not in BLEsensorMACs))
					continue

			rejectMac = checkIfTagged(mac, macplain, macplainReverse, hexstr, batteryLevel, rssi, txPower)

			if rejectMac == "reject": 
				setBeaconLastMsgTS(mac, "reject")
				continue

			#dtinner[4] = max(dtinner[4], tryDeltaTime( startofInnerLoop,oneDigit=True ))
			nMessagesSend += 1

			if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("A-Sens  ", " RX :{}, TX: {}, batteryLevel:{}".format(rssi, txPower, batteryLevel) ,mac)
			#dtinner[4][5] = max(dtinner[5], tryDeltaTime( startofInnerLoop,oneDigit=True ))

			if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("A-tag   ", "after checkIfTagged, msg accepted, checking for new, changed signal,... ",mac)

			lastMSGwithDataPassed = int(time.time())

			if tryDeltaTime( G.tStart) > 31: # wee need some history first 
				#U.logger.log(50, "tryDeltaTime( G.tStart):{}".format(tryDeltaTime( G.tStart)) )
				if checkIfBeaconIsBack(mac): 
					setBeaconLastMsgTS(mac, "beaconback")
					continue

				if checkIfDeltaSignal(mac): 
					setBeaconLastMsgTS(mac, "motion")
					continue

				if checkIfinMotion(mac, rejectMac): 
					setBeaconLastMsgTS(mac, "checkIfDeltaSignal")
					continue

			if  (mac == trackMac or trackMac =="*") and logCountTrackMac > 0:
				writeTrackMac("Accpt   ", "{}".format(beaconsThisReadCycle[mac]) ,mac)

			setBeaconLastMsgTS(mac, "loop")

		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
			continue

	return  False	



####### main pgm / loop ############

def execbeaconloop(test):
	global collectMsgs, sendAfterSeconds, sendAfterSecsOfLastMsg, loopMaxCallBLE, deleteHistoryAfterSeconds,lastWriteHistory
	global onlyTheseMAC,enableiBeacons, minSignalOff, minSignalOn, knownBeaconTags
	global acceptNewiBeacons, acceptNewBeaconMAC, acceptNewTagiBeacons, acceptNewMFGNameBeacons
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
	global bleServiceSections, bleServiceSectionsReverse
	global BLEcollectStartTime
	global BLEanalysisdataCollectionTime
	global writeDumpDataHandle
	global switchbotData
	global fastBLEReaction, output, fastBLEReactionLastAction
	global trackRawOnly 
	global extraStates
	global trackMacNumber
	global sensCheckLastTime, paramCheckLastTime, hciCheckLastTime, hciAvailableForBeep, useHCIForBeep, useHCIForBeacon, HCIs
	global beepBatteryBusy, startTimeOfBeaconloop
	global ignoreBeaconsIfRssiLessThan
	global parsedData
	global beaconLastMessageTS
	global beaconLastMessageSendTS
	global outLast
	global dataFromSensors, waitforcheckIfDelaySend
	global lastMSGwithGoodData, lastMSGwithDataPlain, nMessagesSend, nMsgs, lastMessageOK, lastMSGwithDataPassed, lastTimeMAC, messageStats, clearmessageStats


	clearmessageStats		= [0,0,0,0,0,0,0,0,0,0,0,0]
	messageStats			= {"numberOfMessagesperRead":copy.copy(clearmessageStats),"countTotal":0}
	messageStats["max"]		= len(messageStats["numberOfMessagesperRead"])
	waitforcheckIfDelaySend = False
	dataFromSensors			= {}
	extraStates 			= ["calibrated","position","light","mode","onOffState", "mfg_info","iBeacon","batteryLevel","subtypeOfBeacon","TLMenabled","inMotion","allowsConnection","analyzed"]
	acceptNewMFGNameBeacons = ""
	outLast					= ""
	beaconLastMessageTS 	= {}
	beaconLastMessageSendTS = {}
	parsedData				= {}
	ignoreBeaconsIfRssiLessThan	= -999
	beepBatteryBusy			= 0
	useHCIForBeacon			= ""
	useHCIForBeep			= ""
	hciAvailableForBeep 	= ""
	trackRawOnly 			= False
	fastBLEReactionLastAction = {}
	output					= {}
	fastBLEReaction			= {}
	BLEanalysisdataCollectionTime = 25 # secs 
	deleteHistoryAfterSeconds = 600
	switchbotData 			= {}
	writeDumpDataHandle 	= ""
	BLEcollectStartTime		= -1
	sendAfterSeconds		= 60.
	sendAfterSecsOfLastMsg	= sendAfterSeconds*1.0
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
	#						0			1		2				3			4			5				6				7			8			9    10
	mapReasonToText			= ["init","timer","new_mac","fastDown","fastDown_back","mac_is_back","delta_signal","quickSens","newParams","inMotion","","",""]
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
	badMacs					= ["00:00:00:00:00:00"]



	if test != "normal": readFrom = test
	else: 				 readFrom = ""

	bleServiceSections = {
		"01":"Flags",
		"02":"IncompleteListof16-bitServiceorServiceClassUUIDs",
		"03":"CompleteListof16-bitServiceorServiceClassUUIDs",
		"04":"IncompleteListof32-bitServiceorServiceClassUUIDs",
		"05":"CompleteListof32-bitServiceorServiceClassUUIDs",
		"06":"IncompleteListof128-bitServiceorServiceClassUUIDs",
		"07":"CompleteListof128-bitServiceorServiceClassUUIDs",
		"08":"ShortName",
		"09":"Name",
		"0A":"TxPowerLevel",
		"0D":"ClassofDevice",
		"0E":"SimplePairingHashC-192",
		"0F":"SimplePairingRandomizerR-192",
		"10":"DeviceID",
		"10":"SecurityManagerTKValue",
		"11":"SecurityManagerOutofBandFlags",
		"12":"PeripheralConnectionIntervalRange",
		"14":"Listof16-bitServiceSolicitationUUIDs",
		"15":"Listof128-bitServiceSolicitationUUIDs",
		"16":"ServiceData-16-bitUUID",
		"17":"PublicTargetAddress",
		"18":"RandomTargetAddress",
		"19":"Appearance",
		"1A":"AdvertisingInterval",
		"1B":"LEBluetoothDeviceAddress",
		"1C":"LERole",
		"1D":"SimplePairingHashC-256",
		"1E":"SimplePairingRandomizerR-256",
		"1F":"Listof32-bitServiceSolicitationUUIDs",
		"20":"ServiceData-32-bitUUID",
		"21":"ServiceData-128-bitUUID",
		"22":"LESecureConnectionsConfirmationValue",
		"23":"LESecureConnectionsRandomValue",
		"24":"URI",
		"25":"IndoorPositioning",
		"26":"TransportDiscoveryData",
		"27":"LESupportedFeatures",
		"28":"ChannelMapUpdateIndication",
		"29":"PB-ADV",
		"2A":"MeshMessage",
		"2B":"MeshBeacon",
		"2C":"BIGInfo",
		"2D":"Broadcast_Code",
		"2E":"ResolvableSetIdentifier",
		"2F":"AdvertisingInterval-long",
		"30":"Broadcast_Name",
		"31":"EncryptedAdvertisingData",
		"32":"PeriodicAdvertisingResponseTimingInformation",
		"34":"ElectronicShelfLabel",
		"3D":"3DInformationData",
		"FF":"ManufacturerSpecificData"
		}

	bleServiceSectionsReverse = {}
	for ii in bleServiceSections:
		bleServiceSectionsReverse[bleServiceSections[ii]]= ii

	myPID				= str(os.getpid())
	#kill old G.programs

	U.setLogging()

	count = U.killOldPgm(-1,"hciconfig")
	if count > 4:
		U.logger.log(50,"beaconloop exit, hciconfig, to many ghost hciconfig processes running:{}".format(count))
		U.sendRebootHTML("bluetooth_startup is DOWN  too many  ghost hciconfig processes running ",reboot=True, force=True)
		time.sleep(10)

	readParams(init=True)



	U.killOldPgm(myPID,G.program+".py")
	U.logger.log(30,"======= starting beaconloop v:{}".format(VERSION))
	U.killOldPgm(-1,"hcidump")
	U.killOldPgm(-1,"hcitool")
	U.killOldPgm(-1,"lescan")


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
	#  = {"usedHCI":useHCIForBeacon, "myBLEmac": myBLEmac, "usedBus":bus}
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
		sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber, thisHCI=thisHCI, trymyBLEmac=trymyBLEmac)  
		if retCode == 0: break 
		time.sleep(3)
	if retCode != 0: 
		U.logger.log(30,"beaconloop exit, recode from getting BLE stack >0, after 3 tries:")
		return

 

	if rpiDataAcquistionMethod.find("hcidump") == 0:
		retCode = startHCUIDUMPlistnr(useHCIForBeacon)
		if retCode != "":
			U.logger.log(30,"beaconloop exit, === error in starting HCIdump listener, exit beaconloop ===")
			return

	U.logger.log(30,"using >{}< for data read method testMode:>{}< ".format(rpiDataAcquistionMethod, readFrom!=""))
	
	loopCount				= 0
	logfileCheck			= time.time() + 10
	paramCheckLastTime		= time.time() + 10
	sensCheckLastTime 		= time.time() + 1
	hciCheckLastTime		= time.time() + 0
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
	lastMSGwithGoodData = time.time()
	startTimeOfBeaconloop = time.time()
	lastTimeMAC = time.time()
	
	startHCIcmdThread()

	lastMessageOK = ""
	lastMessage = ""
	startHCITries = 0

	trackMacNumber	=  "xxE9:54:00:00:07:2B"
	U.logger.log(20, "starting loop")

	U.echoText(G.restartLogfileName, "starting beaconloop")

	try:
		while True:
			messageBad = False
			loopCount += 1
			# max every 5 minutes  .. restart BLE hcidump to clear out temp files if accumulated, takes ~1 secs 
			if tryDeltaTime(restartBLE) > 300 and rpiDataAcquistionMethod == "hcidumpWithRestart":
				restartBLE = time.time()
				sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber, reUse=True, thisHCI=useHCIForBeacon, trymyBLEmac=myBLEmac) 
				retCode = startHCUIDUMPlistnr(useHCIForBeacon)
				U.logger.log(20, "time needed to restartBLE:{:.2f}[secs]".format(tryDeltaTime(restartBLE)))
				if debugRestarts: U.echoText(G.restartLogfileName,"restart due to rpiDataAcquistionMethod:{} time > 300".format(rpiDataAcquistionMethod))

			tt = time.time()
			if tt - checkIPConnection > 600: # check once per 10 minutes
				checkIPConnection = tt
				eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
	
			beaconsThisReadCycle = {}
			timeAtLoopStart = tt
			U.echoLastAlive(G.program)
			reasonMax = 1

			if checkIfBLErestart():
				bleRestartCounter += 1
				if bleRestartCounter > 10: 
					U.restartMyself(param="", reason="bad BLE restart", python3=usePython3)
					if debugRestarts: U.echoText(G.restartLogfileName,"restart due to bleRestartCounter:{}".format(bleRestartCounter))
					time.sleep(1)
					sys.exit(4)

				sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber, thisHCI=useHCIForBeacon, trymyBLEmac=myBLEmac) 
				restartBLE = time.time()
				if rpiDataAcquistionMethod == "hcidump":
					retCode = startHCUIDUMPlistnr(useHCIForBeacon)
				if retCode != 0:
					U.logger.log(30,"stopping {} bad BLE start retCode= {}".format(G.program, retCode) )
					if downCount > 1: sys.exit(5)
					time.sleep(2)
					continue

			if rpiDataAcquistionMethod == "socket":
				old_filter = setupSOCKET(sock)

			sendAfter = sendAfterSeconds
			iiWhile = maxLoopCount # if 0.01 sec/ loop = 60 secs normal: 10/sec = 600 
			nMsgs = 0
			nMessagesSend = 0
			while iiWhile > 0:
					U.echoLastAlive(G.program)
					startofInnerLoop = time.time()
					iiWhile -= 1
					tt = round(time.time(),2)
	
					#U.logger.log(20,  "dt loop2 :{:.1f} limit:{},  nMsgs:{}".format(tt - timeAtLoopStart, sendAfter, nMsgs))
					if (reasonMax > 1 or loopCount == 1 ) and tt -G.tStart > 30 : break	# only after ~30 seconds after start....  to avoid lots of short messages in the beginning = collect all ibeacons before sending

					if tt - timeAtLoopStart	 > sendAfter: 
						break # send curl msgs after collecting for xx seconds

					if   nMsgs < 2: time.sleep(0.15)
					elif nMsgs < 5: time.sleep(0.1)
					else: 			time.sleep(0.05)

					if rpiDataAcquistionMethod.find("hcidump") == 0:
						Msgs = readHCUIDUMPlistener()

					else:
						Msgs = getSocketData(sock)

					#### check new messages
					#dtinner[4][0] = max(dtinner[0], tryDeltaTime( startofInnerLoop, oneDigit=True))

					nLast = nMsgs
					nMsgs = len(Msgs)

					messageStats["numberOfMessagesperRead"][min(nMsgs, messageStats["max"]-1)] += 1
					messageStats["countTotal"] += 1
					if nMsgs == 0: 
						zeroInARow += 1
						if zeroInARow > zeroInARowMax or tryDeltaTime( lastmsg) > lastmsgMaxDelta:
							zeroInARow  = 0
							break
					else:
						zeroInARow = 0
						lastmsg    = time.time()

					messageBad = loopThroughMessagesInThisSet(Msgs, timeAtLoopStart, sendAfter, tt)
					if messageBad: break
	
					#dtinner[4][6] = max(dtinner[6], tryDeltaTime( startofInnerLoop,oneDigit=True ))
					doLoopCheck( sensor )
					#dtinner[4][7] = max(dtinner[7], tryDeltaTime( startofInnerLoop,oneDigit=True ))

					if tryDeltaTime( G.tStart) > 31: checkIfFastDownForAll(iiWhile, nMsgs, tryDeltaTime( timeAtLoopStart), lastMSGwithGoodData) # send -999 if gone 
					#dtinner[4][8] = max(dtinner[8], tryDeltaTime( startofInnerLoop,oneDigit=True ))

					if nMsgs > 0: lastMSGwithGoodData = time.time() 

					#check if beep or battery process is blocking beaconloop hci channel, if so wait , max 100 sec
					if beepBatteryBusy > 1:
						U.logger.log(20, "beep or battery process is blocking beaconloop, wait. Level={}".format(beepBatteryBusy) )
						for ii in range(1000):
							if beepBatteryBusy < 2: break
							time.sleep(0.1)



			if rpiDataAcquistionMethod == "socket":
				sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
		
			if readFrom != "":
				lastMSGwithDataPlain  = time.time()
				lastMSGwithDataPassed = time.time()
				nEmptyMessagesInARow = 0
				U.echoLastAlive(G.program)
				if len(Msgs) > 0:
					nMessagesSend = composeMSG(timeAtLoopStart)
					handleHistory() 
				U.logger.log(20, "TestMode: {}".format(beacon_ExistingHistory))
				time.sleep(5)
				continue

			nMessagesSend = composeMSG(timeAtLoopStart)
			handleHistory() 
			U.echoLastAlive(G.program)


			dt1 = int(tryDeltaTime( lastMSGwithDataPlain))
			dt2 = int(tryDeltaTime( lastMSGwithDataPassed))

			if  nMessagesSend > 0:
				nEmptyMessagesInARow = 0
			else:
				nEmptyMessagesInARow += 1

				
			if dt1 > 10 or nEmptyMessagesInARow > 9  or messageBad or  (dt1 > 10  and not checkIfBLEprogramIsRunning(useHCIForBeacon)):
					cmd = "rfkill list"
					blocked = readPopen(cmd)[0]
					if blocked.find(" blocked: yes") ==-1:	blocked = ""
					else:									blocked = "\nrfkill list: "+blocked

					out =  "startHCITries:{}, lastmsg {}s:bytes:{},{}; okdata: {}s:,bytes:{},{}; loopCount:{}; restartCount:{}, bleRestartCounter:{}, nEmptyMessagesInARow:{}, {} ".format(startHCITries, dt1, len(lastMessage), lastMessage,  dt2, len(lastMessageOK), lastMessageOK, loopCount, restartCount, bleRestartCounter, nEmptyMessagesInARow,  blocked)
					U.logger.log(20, "time w/out any message: "+out)
					if debugRestarts: U.echoText(G.restartLogfileName, out)
					if stackrestartcount < 5:
						U.logger.log(20, "restarting stack  due to no messages " )
						if rpiDataAcquistionMethod == "socket":
							sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber, thisHCI=useHCIForBeacon, trymyBLEmac=myBLEmac) 
							restartBLE = time.time()
							maxLoopCount = 6000
						else:
							startHCITries +=1
							stopHCUIDUMPlistener()
							restartBLETry = False
							if startHCITries > 0:
								sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber, thisHCI=useHCIForBeacon, trymyBLEmac=myBLEmac, hardreset=True) 
								restartBLE = time.time()
								restartBLETry = True
							#restartLESCAN(hciUse, 20, force=True)
							startHCUIDUMPlistnr(useHCIForBeacon)
							if debugRestarts: U.echoText(G.restartLogfileName, "restarted  hcidump restartBLE:{}, startHCITries:{} ".format(restartBLE, startHCITries))
							if restartBLETry: startHCITries = 0
						nEmptyMessagesInARow = 0
						stackrestartcount +=1
					else:
						maxLoopCount = 20
						restartCount += 1
						if restartCount > 0:
							U.logger.log(20, "restarting beaconloop  due to no messages " )
							time.sleep(0.5)
							U.restartMyself(param="", reason="too long a time w/o message", python3=usePython3)
							if debugRestarts: U.echoText(G.restartLogfileName, "restarting beaconloop ")

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30, "  exiting loop due to error\n restarting "+G.program)
		stopHCUIDUMPlistener()
		time.sleep(20)
		subprocess.call("/usr/bin/python "+G.homeDir+G.program+".py &", shell=True)
	try: 	G.sendThread["run"] = False; time.sleep(1)
	except: pass


debugRestarts = True

findMAC = ["B8:7C:6F:1A:D9:65"] # ["DD:53:FB:BF:03:40"] #["00:81:F9:86:3E:A0"] # ["CC:48:72:06:40:52","F0:66:AF:D4:9F:C1"] #["EC:44:51:19:C9:44"] # [,"E9:DD:2E:0E:3B:54","F0:D3:EF:76:A1:74"]
trackmacFilter = ""
U.echoLastAlive(G.program)
try: test = sys.argv[1]
except: test = "normal"
execbeaconloop(test)
try: 
	threadCMD["state"]   = "stop"
	time.sleep(0.12)
except: pass
stopHCUIDUMPlistener()
U.logger.log(30,"end of beaconloop.py ") 
sys.exit(0)
