#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  adopted by Karl Wachs Nov27	2015
#
# scans for any kind of BLE message and sends info to indigo plugin
#
# has 2 method: socket and commandline (hcidump) to get info
#
# also scans for sensor devices that send of eg temp/ hum/ acceleration ble messages
#
# can also beep and get battery level w gatttool commands
#
# can also send all  messages parsed to the plugin as requested
#
# can also track a single mac, all messages and all steps to ID these messages
#
# it is now >10< years in development
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
	try:
		import hciRawSocket as bluez	# stdlib fallback for the socket method, py3.3+, no extra libs
		bluezPresent = True
	except:
		bluezPresent = False

SOCKET_RECV_TIMEOUT	= 2.0	# recv timeout [secs] for the "socket" acquisition method
currentBLESocket	= None	# open HCI socket of the "socket" method, used for scan re-enable / cleanup
scanSocketRebuilt	= [False]	# set by reopenScanSocket -> the main loop swaps in the new currentBLESocket
lastScanSocketReopen= [0.]		# time of the last in-place re-open; a 2nd error right after -> full restart
SCAN_REOPEN_WAIT	= 6			# secs to wait for a vanished scan radio to re-enumerate before restarting
import json
import socket as pySocket
import collections

import threading


import math
import fcntl
#import codex

sys.path.append(os.getcwd())
import	piBeaconUtils as U
import	piBeaconGlobals as G

import  pexpect
G.program = "beaconloop"
VERSION   = 21.2

if sys.version[0] == "3": usePython3 = True
else:					  usePython3 = False


try:	import codecs
except:	pass


_debugheartbeat = False

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
			#"03":{"name":"press",			"bytes":3,	"type":"int",		"typeFinal":"float,2",	"factor":0.01,	"trigValue":0.03,	"unit":"hPa",	"mapVtoText":{}									},
			"40":{"name":"distance ",		"bytes":2,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0.03,	"unit":"mm",	"mapVtoText":{}									},
			"41":{"name":"distance ",		"bytes":2,	"type":"int",		"typeFinal":"int",		"factor":0.1,	"trigValue":0.03,	"unit":"m",		"mapVtoText":{}									},
			"12":{"name":"CO2",				"bytes":2,	"type":"int",		"typeFinal":"float,1",	"factor":0.1,	"trigValue":0.03,	"unit":"ppm",	"mapVtoText":{}									},
			"43":{"name":"current",			"bytes":2,	"type":"int",		"typeFinal":"float,3",	"factor":0.001,	"trigValue":0.02,	"unit":"A",		"mapVtoText":{}									},
			"0C":{"name":"voltage",			"bytes":2,	"type":"int",		"typeFinal":"float,3",	"factor":0.001,	"trigValue":0.02,	"unit":"V",		"mapVtoText":{}									},
			"4A":{"name":"voltage",			"bytes":2,	"type":"int",		"typeFinal":"float,1",	"factor":0.1,	"trigValue":0.02,	"unit":"V",		"mapVtoText":{}									},
			"44":{"name":"tvoc",			"bytes":2,	"type":"int",		"typeFinal":"int",		"factor":1,		"trigValue":0.02,	"unit":"ug/m3",	"mapVtoText":{}									},
			#"44":{"name":"speed",			"bytes":2,	"type":"int",		"typeFinal":"float,2",	"factor":0.01,	"trigValue":0.02,	"unit":"m/s",	"mapVtoText":{}									},
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
	"""Computes the elapsed time since a given timestamp, optionally rounded to one decimal, returning -999 on any error.

	Inputs:
	    test (float): Reference epoch timestamp to subtract from now
	    oneDigit (bool): If True, round the delta to one decimal
	Outputs:
	    float: Seconds elapsed since test, or -999. on error
	"""
	try: 
		dt = time.time() - test
		if oneDigit: dt = round(dt,1)
		return dt
	except: return - 999.

#

def hex2str(inString,logLevel=1):
	"""Decodes a hex-encoded string into a UTF-8 text string, handling both Python 2 and 3, and returns '00' (optionally logging) if conversion fails.

	Inputs:
	    inString (str): Hex-encoded input string to decode
	    logLevel (int): If >0, log a warning when decoding fails
	Outputs:
	    str: Decoded UTF-8 string, or '00' on failure
	"""
	try:
		if sys.version[0] == "3":
			return codecs.decode(inString,"hex").decode("utf-8")
		else:
			return  inString.decode("hex")
	except Exception :
		if logLevel >0: U.logger.log(20,"hexstring: >>{}<< can not be converted,ret 00".format(inString))
	return "00"
	
####-------------------------------------------------------------------------####
def readPopen(cmd):
		"""Runs a shell command via subprocess.Popen and returns its decoded stdout and stderr as a tuple of UTF-8 strings, logging on exception.

		Inputs:
		    cmd (str): Shell command line to execute
		Outputs:
		    tuple: (stdout, stderr) as decoded strings, or None on exception
		"""
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode("utf_8"), err.decode("utf_8")
		except Exception :
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
	"""Interprets an unsigned integer as a signed two's-complement value given a bit width, subtracting 2^bits when the sign bit is set.

	Inputs:
	    value (int): Unsigned integer to interpret
	    bits (int): Bit width of the value
	Outputs:
	    int: Signed two's-complement integer
	"""
	if (value & (1 << (bits - 1))) != 0:
		value = value - (1 << bits)
	return value

def signedIntfrom8(string):
	"""Parses a hex string into an 8-bit signed integer, treating values above 127 as negative, returning 0 on parse error.

	Inputs:
	    string (str): Hex string representing an 8-bit value
	Outputs:
	    int: Signed 8-bit integer, or 0 on error
	"""
	try:
		intNumber = int(string,16)
		if intNumber > 127: intNumber -= 256
	except Exception :
		U.logger.log(20,"", exc_info=True)
		return 0
	return intNumber

def signedIntfrom16(string):
	"""Parses a hex string into a 16-bit signed integer, treating values above 32767 as negative, returning 0 on parse error.

	Inputs:
	    string (str): Hex string representing a 16-bit value
	Outputs:
	    int: Signed 16-bit integer, or 0 on error
	"""
	try:
		intNumber = int(string,16)
		if intNumber > 32767: intNumber -= 65536
	except Exception :
		U.logger.log(20,"", exc_info=True)
		return 0
	return intNumber


def signedintfromhexR(string, n): # eg aabbccdd, 4
	"""Parses a little-endian hex string of n bytes into a signed integer by reversing the byte order, converting to int, and applying two's-complement adjustment when the value exceeds the signed positive range; returns 0 on error.

	Inputs:
	    string (str): hex string in little-endian byte order (e.g. 'aabbccdd')
	    n (int): number of bytes to decode
	Outputs:
	    int: signed integer value, or 0 on exception
	"""
	try:
		ss = ""
		for i in range(n):
			ss += string[(n-i-1)*2:(n-i)*2]

		intNumber = int(ss,16)
		if intNumber > 2**(n*8-1)-1: intNumber -= (2**(n*8-1) +2)
	except Exception :
		U.logger.log(20,"", exc_info=True)
		return 0
	return intNumber

def intfromhexR(string, n): # eg aabbccdd, 4
	"""Parses a little-endian hex string of n bytes into an unsigned integer by reversing the byte order and converting to int; returns 0 on error.

	Inputs:
	    string (str): hex string in little-endian byte order (e.g. 'aabbccdd')
	    n (int): number of bytes to decode
	Outputs:
	    int: unsigned integer value, or 0 on exception
	"""
	try:
		ss = ""
		for i in range(n):
			ss += string[(n-i-1)*2:(n-i)*2]

		intNumber = int(ss,16)
	except Exception :
		U.logger.log(20,"", exc_info=True)
		return 0
	return intNumber


def intFrom8(hexString, start):
	"""Reads a single byte (two hex characters) from the given start offset of a hex string and returns its integer value.

	Inputs:
	    hexString (str): hex string to read from
	    start (int): character offset where the byte begins
	Outputs:
	    int: integer value of the 8-bit field
	"""
	return int(hexString[start:start+2],16)

def intFrom16(hexString, start):
	"""Reads a 16-bit value (four hex characters) from the given start offset of a hex string and returns its integer value.

	Inputs:
	    hexString (str): hex string to read from
	    start (int): character offset where the field begins
	Outputs:
	    int: integer value of the 16-bit field
	"""
	return int(hexString[start:start+4],16)


def rshift(val, n):
	"""
	Arithmetic right shift, preserves sign bit.
	https://stackoverflow.com/a/5833119 .
	"""
	return (val % 0x100000000) >> n


def returnnumberpacket(pkt):
	"""Combines the bytes of a packed binary packet into a single integer where the first byte is weighted by 256 and subsequent bytes by 1, effectively forming a two-byte-style number.

	Inputs:
	    pkt (bytes): packed byte string to unpack
	Outputs:
	    int: the computed integer value
	"""
	myInteger = 0
	multiple = 256
	for c in pkt:
		if not isinstance(c, int): c = struct.unpack("B",c)[0]	# py2: str byte, py3: already int
		myInteger +=  c * multiple
		multiple = 1
	return myInteger 

def stringFromPacket(pkt):
	"""Converts a packed binary packet into its hexadecimal string representation by formatting each byte as two hex digits.

	Inputs:
	    pkt (bytes): packed byte string to convert
	Outputs:
	    str: concatenated two-digit-per-byte hex string
	"""
	myString = ""
	for c in pkt:
		if not isinstance(c, int): c = struct.unpack("B",c)[0]	# py2: str byte, py3: already int
		myString +=	 "%02x" % c
	return myString 

def printpacket(pkt):
	"""Writes each byte of a packed binary packet to standard output as space-separated two-digit hex values for debugging.

	Inputs:
	    pkt (bytes): packed byte string to print
	Outputs:
	    None: writes hex bytes to stdout
	"""
	for c in pkt:
		sys.stdout.write("%02x " % struct.unpack("B",c)[0])

def get_packed_bdaddr(bdaddr_string):
	"""Converts a colon-separated Bluetooth device address string into a packed 6-byte little-endian binary structure suitable for HCI commands.

	Inputs:
	    bdaddr_string (str): Bluetooth address like 'AA:BB:CC:DD:EE:FF'
	Outputs:
	    bytes: 6-byte packed address in reversed (little-endian) order
	"""
	packable_addr = []
	addr = bdaddr_string.split(":")
	addr.reverse()
	for b in addr: 
		packable_addr.append(int(b, 16))
	return struct.pack("<BBBBBB", *packable_addr)

def packed_bdaddr_to_string(bdaddr_packed):
	"""Converts a packed 6-byte little-endian Bluetooth address back into a human-readable colon-separated hex string.

	Inputs:
	    bdaddr_packed (bytes): 6-byte packed Bluetooth address
	Outputs:
	    str: colon-separated MAC-style address string
	"""
	return ':'.join('%02x'%i for i in struct.unpack("<BBBBBB", bdaddr_packed[::-1]))

scanExtendedMode = False	# True = the scan adapter supports BT5 extended advertising (LE feature bit 12,
							# probed at socket setup) -> extended scan commands are used and extended
							# advertisements (Ruuvi Air E1 etc.) are received; frames are converted to the
							# legacy report layout (extAdvToLegacyHex) so the whole pipeline stays unchanged
extScanBlockedByAdv    = [False]	# single adapter: the iBeacon broadcast (LEGACY adv cmds) locks the controller
									# to the legacy command set -> extended scanning impossible on the same radio
extScanZeroMsgRestarts = [0]		# consecutive zero-message stack restarts WITH extended scanning active
extScanForceLegacy     = [False]	# 2x zero-message restarts = adapter misreports its BT5 support -> stay legacy
# Accepting EXTENDED mode for the scan radio is judged by COVERAGE, not by raw report rate.
# piBeacon listens ~60 s and then summarises (the rssi it keeps is an AVERAGE), so the question is
# "do I still hear every device often enough", not "do I get as many packets". A BT5 controller in
# extended mode reports BLE4 advs too, but typically fewer of them per device - measured on the ASUS
# 0b05:190e: 29% of the legacy PACKET rate, yet ~80% of the MACS at ~26 reports per mac per minute,
# which is five times what an average needs. The old rule (>=70% of the legacy packet rate) rejected
# exactly that radio and cost the rpi all BLE5 reception.
# Both tests are RELATIVE to what the SAME radio hears in BLE4 mode on the SAME air, because the
# absolute numbers are a property of the neighbourhood, not of the dongle: 60 macs in a block of
# flats, 4 in a quiet house. An absolute "must hear 20 macs" would reject a perfectly good radio in
# a small environment. The only absolute is the SUMMARY floor - a device has to be heard a few times
# within one ~60 s window for its average rssi to mean anything - and that one is about the
# averaging, not about how many neighbours happen to exist.
EXTSCAN_MIN_COVERAGE   = 60.0		# % of the macs the SAME radio hears in BLE4-only mode
EXTSCAN_MIN_PER_MIN    = 5.0		# reports per mac per 60 s summary window (absolute, see above)
EXTSCAN_MIN_REPORTS    = 3			# sanity floor only: fewer than this is not a measurement
extScanLastReported    = [None]		# last scan-mode verdict logged (log only on change, not every BLE restart)
lastBLE5Report         = [""]		# last BLE5 verdict text logged (log only on change)
lastBLE5Reason         = [""]		# why there is no BLE5 reception, from the last probe/role verdict
ble5Pending            = ["", 0.]	# [candidate BLE5 verdict, when it first appeared] - settle window
BLE5_SETTLE            = 60.		# secs a value must hold before it is sent: role assignment, the delivery
									# probe, the listener's first setup and the periodic BLE restart all move
									# it around during the first minute - indigo should see the END state, not
									# every intermediate one
broadcastMAC           = [""]		# BLE mac of the adapter that TRANSMITS our iBeacon - the rpi's identity:
									# the plugin links the rpi device to it and other rpis hear it for
									# online detection. piMAC in messages must be THIS mac, never the
									# scanner's (they differ when the extAdv dongle does the scanning)


def reportBLE5(status):
	"""Records WHY extended advertising is (not) available - the real delivery-test result,
	not the adapter's often-wrong feature-bit claim - and republishes the per-radio states. The
	reason only reaches indigo when no radio actually delivers extended reports; a working
	radio is reported as its own hciN-bus-mac (see sendBLE5State)."""
	lastBLE5Reason[0] = status
	sendBLE5State()


def sendBLE5State():
	"""Publishes the BLE5 (extended-advertising) RADIO to indigo -> rpi device state
	the "scan5" function of that radio in its hci0..hci3 state.
	Replaces the old yes/no "supportsBLE5" state: which radio does BLE5 is the useful fact -
	with 3-4 dongles per rpi a bare "yes" never said WHICH one, and the delivery-test detail
	is in the log anyway.

	The value is DERIVED from the current facts on every call, never a stored verdict string:
	role assignment, a dongle swap, an adoption and a lost radio then all end up with the
	right value and no call order can clobber another.

	SETTLE WINDOW: nothing is sent until the derived value has held for BLE5_SETTLE secs. The
	first minute after a start legitimately flips it around (role assigned -> probe verdict ->
	listener's first successful setup, plus the periodic BLE restart), and indigo has no use
	for that flapping - only for where it ends up. Every change restarts the timer, so this is
	called from doLoopCheck as well: the last change has to be able to age out with no further
	event to trigger the send.

	Inputs:
	    None (reads hciRoles/extListenerCtl/scanExtendedMode).
	Outputs:
	    None: refreshes hci0..hci3 (the BLE5 radio shows "scan5" as its function)
	"""
	try:
		val = ""
		ext = hciRoles.get("extListener", {})
		th  = extListenerCtl.get("thread")
		if "{}".format(ext.get("hci", "")) != "" and th is not None and th.is_alive():
			val = "{}-{}-{}".format(ext.get("hci", ""), ext.get("bus", "USB"), ext.get("mac", ""))
		elif scanExtendedMode:					# no reserved radio, but the SCAN radio delivers extended
			val = "{}-{}-{}-scan".format(useHCIForBeacon, HCIs.get("hci", {}).get(useHCIForBeacon, {}).get("bus", ""), myBLEmac)
		else:
			val = "None"						# no BLE5 reception at all - a plain, testable value;
												# the WHY stays in the log, not in the device state
		if val != ble5Pending[0]:				# new candidate -> restart the settle window
			ble5Pending[0] = val
			ble5Pending[1] = time.time()
		if val == lastBLE5Report[0]:					return		# indigo already has it
		if tryDeltaTime(ble5Pending[1]) < BLE5_SETTLE:	return		# still moving - let it settle
		lastBLE5Report[0] = val
		U.logger.log(20, "BLE5 radio -> {}{} (stable for {:.0f}s, publishing)".format(
						val, " [{}]".format(lastBLE5Reason[0]) if (val == "None" and lastBLE5Reason[0] != "") else "", BLE5_SETTLE))
		sendHciStates()		# the BLE5 verdict shows as the "scan5" function of that radio now
	except Exception:
		pass


def currentAdapterMacs():
	"""Sorted list of the BLE macs of all adapters (from the last whichHCI enumeration)."""
	try:	return sorted("{}".format(HCIs["hci"][h].get("BLEmac","")) for h in HCIs["hci"])
	except Exception:	return []


hciRoles = {"scan":{}, "broadcast":{}, "BLEconnect":{}}		# current radio-role assignment, persisted in beaconloop.hci
# per-channel role PINS from the rpi device dialog ("Pin a role to a specific BLE radio"), shipped in
# the parameters file as {"hci0":"scanBLE45", "hci2":"bleconnect", ...}. Empty = the auto policy
# decides everything, which is the default and the recommended setup.
hciRolesPinned = {}
lastHciStates  = {}		# last per-radio state strings SENT (hci0..hci3) - send only on change


def writeBeaconloopHci():
	"""Writes beaconloop.hci (+ temp copy) in the CLEAR role format:
	{"scan":{mac,hci,bus,BLE5[,allMacs]}, "broadcast":{mac,hci}, "BLEconnect":{mac,hci}}
	scan.BLE5 = the persisted delivery-test verdict; scan.allMacs = the adapter set it
	was proven with (any change forces a fresh proof)."""
	try:
		dd = {"pgm":"beaconloop", "scan": hciRoles["scan"], "broadcast": hciRoles["broadcast"], "BLEconnect": hciRoles["BLEconnect"], "extListener": hciRoles.get("extListener", {})}
		U.writeFile("temp/beaconloop.hci", json.dumps(dd))
		U.writeFile("beaconloop.hci", json.dumps(dd))
	except Exception:
		pass


def loadExtScanVerdict():
	"""True when beaconloop.hci carries a positive delivery-test verdict for EXACTLY this
	hardware (same scan adapter mac + same full adapter mac set) -> the 2.5s proof
	window can be skipped; the setup commands still run (a reset wipes controller
	state). Any mac change (dongle added/removed/swapped) invalidates the trust."""
	try:
		sc = json.load(open(G.homeDir + "beaconloop.hci")).get("scan", {})
		return (sc.get("BLE5", False)
				and sc.get("testVer", 1) == 3
				and "{}".format(sc.get("mac","")) == "{}".format(myBLEmac)
				and sc.get("allMacs",[]) == currentAdapterMacs())
	except Exception:
		return False


def saveExtScanVerdict(ok):
	"""Records the delivery-test verdict in the scan role of beaconloop.hci."""
	hciRoles["scan"]["BLE5"] = bool(ok)
	hciRoles["scan"]["testVer"] = 3			# 3 = comparative rate test w/ per-phase HCI reset (v15.4); older verdicts re-prove
	if ok:	hciRoles["scan"]["allMacs"] = currentAdapterMacs()
	else:	hciRoles["scan"].pop("allMacs", None)
	writeBeaconloopHci()


def hci_enable_le_scan(sock):
	"""Enables BLE scanning on the given HCI socket by calling hci_toggle_le_scan with the enable flag set.

	Inputs:
	    sock (socket.socket): open Bluetooth HCI socket
	Outputs:
	    None: sends an HCI command to enable LE scan
	"""
	hci_toggle_le_scan(sock, 0x01)

def hci_disable_le_scan(sock):
	"""Disables BLE scanning on the given HCI socket by calling hci_toggle_le_scan with the enable flag cleared.

	Inputs:
	    sock (socket.socket): open Bluetooth HCI socket
	Outputs:
	    None: sends an HCI command to disable LE scan
	"""
	hci_toggle_le_scan(sock, 0x00)

def hci_toggle_le_scan(sock, enable):
	"""Sends a Bluetooth HCI LE_SET_SCAN_ENABLE command over the socket, packing the enable flag and a zero filter-duplicates byte to turn LE scanning on or off.

	Inputs:
	    sock (socket.socket): open Bluetooth HCI socket
	    enable (int): scan enable flag (0x01 on, 0x00 off)
	Outputs:
	    None: transmits the HCI command via bluez.hci_send_cmd
	"""
	if scanExtendedMode:
		# LE Set EXTENDED Scan Enable: enable, filter_dup=0, duration=0 (forever), period=0
		cmd_pkt = struct.pack("<BBHH", enable, 0x00, 0x0000, 0x0000)
		bluez.hci_send_cmd(sock, OGF_LE_CTL, 0x0042, cmd_pkt)
	else:
		cmd_pkt = struct.pack("<BB", enable, 0x00)
		bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_SET_SCAN_ENABLE, cmd_pkt)


def hci_le_set_scan_parameters(sock):
	"""Sets LE scan parameters: ACTIVE scanning (so SCAN_RSP packets with device names/mfg_info
	are received too), interval=window=0x0010 (10ms, 100% duty cycle), public own address,
	accept-all filter policy. Scanning must be off while setting parameters, so it is
	disabled first (ignore errors if it was not running).

	NOTE: this previously packed these 7 parameter bytes but sent them to
	OCF_LE_SET_SCAN_ENABLE (wrong opcode) - the controller stayed on its DEFAULT parameters
	(PASSIVE scan) and never received scan responses; that was why the socket method
	missed the messages with mfg_info/names.

	Inputs:
	    sock (object): Open BlueZ HCI device socket
	Outputs:
	    None: Sends HCI commands to the BLE controller
	"""
	try:	hci_toggle_le_scan(sock, 0x00)		# params are rejected while scanning is enabled
	except:	pass
	time.sleep(0.05)
	if scanExtendedMode:
		# re-assert the LE EVENT MASK first (bit 12 = Extended Advertising Report is OFF in
		# the controller default and any reset reverts to it -> scanning would run but
		# deliver NOTHING); then LE Set EXTENDED Scan Parameters: own addr public,
		# accept-all filter, 1M PHY; ACTIVE scan, interval=window=0x0010 (100% duty)
		bluez.hci_send_cmd(sock, OGF_LE_CTL, 0x0001, struct.pack("<Q", 0x000FFFFF))
		time.sleep(0.02)
		cmd_pkt = struct.pack("<BBBBHH", 0x00, 0x00, 0x01, 0x01, 0x0010, 0x0010)
		bluez.hci_send_cmd(sock, OGF_LE_CTL, 0x0041, cmd_pkt)
	else:
		#                              scan_type  interval  window  own_addr  filter
		cmd_pkt = struct.pack("<BHHBB", 0x01,     0x0010,   0x0010, 0x00,     0x00)
		bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_SET_SCAN_PARAMETERS, cmd_pkt)


#################################
def checkIfHCIIsBlockedAndFix():
	"""Checks whether the HCI Bluetooth interface is rfkill-blocked; if so attempts to unblock it, logs the result, and reports an error via sendURL if it cannot be unblocked.

	Inputs:
	    None.
	Outputs:
	    bool: True if HCI is unblocked/usable, False if still blocked or on error
	"""
	try:
		### test hci blocked?
		blocked, hciDict = U.checkIfHciBlocked(verbose=False)
		if blocked: 
			U.logger.log(20,"hci is blocked, trying to unblock\n{}".format(hciDict ) )
			U.hciUnblock()
			blocked, hciDict = U.checkIfHciBlocked(verbose=True)
			if blocked: 
				U.logger.log(20,"hci is still blocked,  giving up\n{}".format(hciDict ) )
				U.sendURL( data={"ERROR":"bluetooth startup: err-BLE-is blocked"}, squeeze=False, wait=False )
				return False
			else:
				U.logger.log(20,"hci was unblocked")
		else:
			U.logger.log(20,"hci is not blocked")
	except Exception : 
		U.logger.log(20,"", exc_info=True)
		return False
	return True


#################################
def hardresetHCI(hci, startTime):
	"""Performs a hard reset of the given HCI interface by bringing it down, restarting the bluetooth service, and bringing it back up via shell commands, logging each step.

	Inputs:
	    hci (str): HCI interface name, e.g. 'hci0'
	    startTime (float): Start timestamp used for elapsed-time logging
	Outputs:
	    None: Runs hciconfig/service shell commands and logs output
	"""
	try:
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
	except Exception : 
		U.logger.log(20,"", exc_info=True)
	return 

#################################
def normalStartHCI(hci, startTime, logLevelStart):
	"""Performs a normal startup of the given HCI interface by resetting it (retrying on RF-kill), listing hciconfig status, and bringing it up, retrying once if errors occur.

	Inputs:
	    hci (str): HCI interface name, e.g. 'hci0'
	    startTime (float): Start timestamp used for elapsed-time logging
	    logLevelStart (int): Logging level for startup messages
	Outputs:
	    None: Runs hciconfig shell commands and logs output
	"""
	try:
		cmd = "sudo hciconfig "+hci+" reset"
		ret =readPopen(cmd)
		U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )
		if ret[1].find("RF-kill") > -1 or ret[0].find("RF-kill") > -1:
			time.sleep(0.2)
			readPopen(cmd)
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
	except Exception : 
		U.logger.log(20,"", exc_info=True)
	return 


#################################
def startHCIBroadCast(useHCIForBeacon, pi, startTime, logLevelStart):
	"""Configures the HCI controller to broadcast an iBeacon advertisement by sending hcitool commands that set the beacon payload (UUID/major/minor/txpower), advertising parameters, and enable advertising; restarts LE scan if using hcidump mode.

	Inputs:
	    useHCIForBeacon (str): HCI interface to broadcast on, e.g. 'hci0'
	    pi (int): Raspberry Pi number encoded into the beacon minor field
	    startTime (float): Start timestamp used for elapsed-time logging
	    logLevelStart (int): Logging level for startup messages
	Outputs:
	    None: Runs hcitool advertising commands and logs output
	"""
	try:
		OGF						= " 0x08"
		# stop a possibly still-running advertising first: setting adv params while
		# advertising is enabled returns 0x0C Command Disallowed (seen on stack restarts
		# when the broadcast from the previous round was still active)
		readPopen("hcitool -i {} cmd 0x08 0x000a 00 &".format(useHCIForBeacon))
		# setup broadcast message
		OCF					= " 0x0008"
		iBeaconPrefix		= " 1E 02 01 1A 1A FF 4C 00 02 15"
		uuid				= " 2f 23 44 54 cf 6d 4a 0f ad f2 f4 91 1b a9 ff a6"
		MAJ					= " 00 01"
		MIN					= " 00 "+"%02x"%(int(pi))
		txP					= " C5 00"
		#cmd	 = "hcitool -i "+useHCIForBeacon+" cmd" + OGF + OCF + iBeaconPrefix + uuid + MAJ + MIN + txP
		cmd	 = "hcitool -i {} cmd{}{}{}{}{}{}{} &".format(useHCIForBeacon, OGF, OCF, iBeaconPrefix, uuid,  MAJ, MIN, txP)
		ret = readPopen(cmd)
		U.logger.log(20,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )


		if 	rpiDataAcquistionmethod.find("hcidump" ) == 0:
			restartLESCAN(useHCIForBeacon, logLevelStart, force=True )

		####################################set adv params		minInt	 maxInt		  nonconectable	 +??  <== THIS rpi to send beacons every 10 secs only 
		#											   00 40=	0x4000* 0.625 msec = 16*4*256 = 10 secs	 bytes are reverse !! 
		#											   00 10=	0x1000* 0.625 msec = 16*1*256 = 2.5 secs
		#											   00 04=	0x0400* 0.625 msec =	4*256 = 0.625 secs
		#cmd	 = "hcitool -i "+useHCIForBeacon+" cmd" + OGF + " 0x0006"	  + " 00 10"+ " 00 20" +  " 03"			   +   " 00 00 00 00 00 00 00 00 07 00"
		# adv interval min 0x3000 (7.68 s) max 0x4000 (10.24 s = the HCI cap) - the
		# broadcast is only an "rpi is up" indicator + rssi source for distance,
		# ~6 msgs/min is plenty (was 0x1000/0x2000 = 2.5-5 s)
		cmd	 = "hcitool -i {} cmd{} 0x0006 00 30 00 40 03 00 00 00 00 00 00 00 00 07 00 &".format(useHCIForBeacon, OGF)
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

	except Exception : 
		U.logger.log(20,"", exc_info=True)
	return 


#################################
def reuseHCI(hci, startTime, logLevelStart):
	"""Reuses an already-up HCI interface by issuing a single hciconfig reset command and logging the result.

	Inputs:
	    hci (str): HCI interface name, e.g. 'hci0'
	    startTime (float): Start timestamp used for elapsed-time logging
	    logLevelStart (int): Logging level for messages
	Outputs:
	    None: Runs hciconfig reset shell command and logs output
	"""
	try:
				cmd = "sudo hciconfig "+hci+" reset"
				ret = readPopen(cmd) # 
				U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )
	except Exception : 
		U.logger.log(20,"", exc_info=True)
	return 


#################################
def setNoLead(hci, logLevelStart, startTime):
	"""Disables LE advertising and scanning on the given HCI interface by running hciconfig noleadv and noscan commands, logging the outcome.

	Inputs:
	    hci (str): HCI interface name, e.g. 'hci0'
	    logLevelStart (int): Logging level for messages
	    startTime (float): Start timestamp used for elapsed-time logging
	Outputs:
	    None: Runs hciconfig noleadv/noscan shell commands and logs output
	"""
	try:
		cmd	 = "sudo hciconfig {} noleadv &\n sudo hciconfig {} noscan &".format(hci, hci)
		ret = readPopen(cmd)
		U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd.replace("\n",";"), ret, tryDeltaTime(startTime))  )
	except Exception : 
		U.logger.log(20,"", exc_info=True)
	return 


#def hci_le_set_scan_parameters(sock, scan_type=constants.LE_SCAN_ACTIVE,  # 0x01
#								interval=0x10, window=0x10,
#								own_bdaddr_type=constants.LE_RANDOM_ADDRESS, # ==0x01
#								filter_type=constants.LE_FILTER_ALLOW_ALL):	 # ==0x00
#	 # TODO: replace B with appropriate size and remove 0 padding.
#	 cmd_pkt = struct.pack("<BBBBBBB", scan_type, 0x0, interval, 0x0, window,own_bdaddr_type, filter_type)
#	 bluez.hci_send_cmd(sock, constants.OGF_LE_CTL,constants.OCF_LE_SET_SCAN_PARAMETERS, cmd_pkt)

#################################
cloneDongleWarned = False
scanAdapterMTU    = 0		# ACL MTU of the adapter beaconloop is scanning on (<=400 = clone)
scanAdapterMac    = ""
def setScanAdapter(mtu, mac):
	"""Remembers which adapter beaconloop is scanning on (set at selection). A clone
	dongle (low ACL MTU) is NOT warned about just for being present - only if beaconloop
	later runs into real trouble on it (see warnBadScanDongle). A genuine dongle swap
	re-arms the warning."""
	global scanAdapterMTU, scanAdapterMac, cloneDongleWarned
	try:
		if "{}".format(mac).upper() != "{}".format(scanAdapterMac).upper():
			cloneDongleWarned = False		# different adapter now -> allow a fresh assessment
		scanAdapterMTU = int(mtu) if mtu else 0
		scanAdapterMac = mac
	except Exception:
		scanAdapterMTU = 0


def warnBadScanDongle():
	"""Called when beaconloop is in REAL trouble (repeated BLE-stack restarts with no
	messages). Only THEN, and only if beaconloop is scanning on a suspect CSR8510 CLONE
	dongle (ACL MTU <=400; genuine radios ~1021), do we blame the dongle and WARN - a
	clone that scans fine never triggers this. Sent to the Indigo log via the plugin
	'warning' field (level 30); once per adapter."""
	global cloneDongleWarned
	if cloneDongleWarned: return
	if not (0 < scanAdapterMTU <= 400): return		# not on a clone -> do NOT blame the dongle
	text = ("A BLE dongle is not working well and should be REPLACED - beaconloop is not receiving "
			"beacon messages and is running on a cheap dongle that looks faulty. "
			"[likely a CSR8510 clone: mac {}, ACL MTU {}; genuine dongles report ACL MTU ~1021]".format(scanAdapterMac, scanAdapterMTU))
	U.logger.log(20, text)											# Pi's own log
	try:	U.sendURL( data={"data":{"warning":text}}, squeeze=False, wait=False )	# -> Indigo log (plugin logs 'warning' at level 30)
	except Exception: pass
	cloneDongleWarned = True


def startBlueTooth(pi, reUse=False, thisHCI="", trymyBLEmac="", hardreset=False):
	"""Orchestrates full Bluetooth startup: unblocks HCI, selects and initializes the proper HCI interface (hard reset/reuse/normal start), determines the BLE MAC and bus, starts iBeacon broadcasting, and opens a socket or hcidump for data acquisition, handling errors and reboot requests.

	Inputs:
	    pi (int): Raspberry Pi number used for beacon minor and identification
	    reUse (bool): If True, reuse existing HCI rather than full reset
	    thisHCI (str): Specific HCI interface to use, empty for auto-select
	    trymyBLEmac (str): Preferred BLE MAC address to try selecting
	    hardreset (bool): If True, perform a hard reset of the HCI interface
	Outputs:
	    tuple: (socket-or-status, myBLEmac, returnCode) where returnCode 0 is success and negatives indicate errors
	"""
	global myBLEmac, downCount
	global currentBLESocket
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
		### test hci blocked?
		if not checkIfHCIIsBlockedAndFix():
			return 0, "", -1

		HCIs = dropIgnoredRadios(U.whichHCI())

		# the hci NUMBER/name can change between boots - the dongle identity is its BLE mac.
		# resolve the hci name from the pinned mac; a stale stored name would otherwise
		# reset/select the WRONG dongle after the numbering swapped
		if trymyBLEmac != "" and HCIs != {} and "hci" in HCIs:
			foundHCI = ""
			for hciX in HCIs["hci"]:
				if "{}".format(HCIs["hci"][hciX].get("BLEmac","")).upper() == "{}".format(trymyBLEmac).upper():
					foundHCI = hciX
					break
			if foundHCI != "":
				if thisHCI != "" and thisHCI != foundHCI:
					U.logger.log(20,"pinned BLE mac {} is now on {} (was {}) - hci numbering changed, following the mac".format(trymyBLEmac, foundHCI, thisHCI))
				thisHCI = foundHCI
			else:
				if thisHCI != "":
					U.logger.log(20,"pinned BLE mac {} not visible in {} - resetting ALL adapters to find it".format(trymyBLEmac, list(HCIs["hci"])))
				thisHCI = ""

		U.logger.log(20,"thisHCI:{}; HCIs available:{}".format(thisHCI, HCIs)  )
		for hci in HCIs["hci"]:
			if hci == "": continue
			if thisHCI != "" and hci!=thisHCI: continue
			U.logger.log(20,"checking hci:{}".format(hci)  )

			if hardreset: 
				hardresetHCI(hci, startTime)

			elif reUse:
				reuseHCI(hci, startTime, logLevelStart)

			else:
				normalStartHCI(hci, startTime, logLevelStart)

			if rpiDataAcquistionmethod.find("hcidump") == 0:
				setNoLead(hci, logLevelStart, startTime)

		time.sleep(1)

		#### selct the proper hci bus: if just one take that one, if 2, use bus="uart", if no uart use hci0, or use last one
		if not reUse: HCIs = dropIgnoredRadios(U.whichHCI())

		ret = ["",""]
		if HCIs != {} and "hci" in  HCIs and HCIs["hci"] != {}:

			U.logger.log(10,"myBLEmac HCIs{}".format( HCIs))	# debug only - the level-20 summary a few lines down covers it
			# AUTO mode ("-1"): use the deterministic role/quality selection (beaconloop = SCAN role
			# -> takes the clone/other radio, leaving the good one for BLEconnect). No mac-pin needed
			# (deterministic = stable), and dropping it lets a stale pin from before this scheme self-correct.
			# radio roles come from the role-aware auto pick (and the per-channel pins in the device
			# dialog), never from a bus preference typed into the config - BeaconUseHCINo is gone.
			trymyBLEmac = ""
			_pinScan = pinnedRadio(("scanBLE4", "scanBLE45"), HCIs["hci"])
			if _pinScan != "":
				trymyBLEmac = "{}".format(HCIs["hci"][_pinScan].get("BLEmac",""))
				U.logger.log(20,"scan role PINNED to {} ({}, {}) by the device dialog".format(_pinScan, trymyBLEmac, hciRolesPinned.get(_pinScan,"")))
			useHCIForBeacon,  myBLEmac, devId, bus = U.selectHCI(HCIs["hci"], "-1","USB", tryBLEmac=trymyBLEmac, role="scan")

			# if a specific dongle (pinned BLE mac from beaconloop.hci) was requested but not found -
			# e.g. a USB dongle still enumerating right after boot - retry the enumeration before
			# accepting a different dongle; otherwise one bad boot re-pins beaconloop.hci to the
			# wrong dongle and the swap becomes permanent
			if trymyBLEmac != "" and "{}".format(myBLEmac).upper() != "{}".format(trymyBLEmac).upper():
				for retryHCI in range(3):
					U.logger.log(20,"pinned BLE mac {} not found (got {}), re-enumerating adapters ({}/3)".format(trymyBLEmac, myBLEmac, retryHCI+1))
					time.sleep(3)
					HCIs = dropIgnoredRadios(U.whichHCI())
					if HCIs != {} and "hci" in HCIs and HCIs["hci"] != {}:
						useHCIForBeacon,  myBLEmac, devId, bus = U.selectHCI(HCIs["hci"], "-1","USB", tryBLEmac=trymyBLEmac, role="scan")
						if "{}".format(myBLEmac).upper() == "{}".format(trymyBLEmac).upper(): break
				if "{}".format(myBLEmac).upper() != "{}".format(trymyBLEmac).upper():
					U.logger.log(20,"pinned BLE mac {} still not found after retries, switching to {} on {}".format(trymyBLEmac, myBLEmac, useHCIForBeacon))
			# beaconloop.hci role format: {"scan":{mac,hci,bus,BLE5[,allMacs]},"broadcast":{..},"BLEconnect":{..}}
			hciRoles["scan"] = {"mac": myBLEmac, "hci": useHCIForBeacon, "bus": bus, "BLE5": False}
			try:	# carry the persisted BLE5 delivery-test verdict over (same scan mac only; old flat format understood too)
				oldHci  = json.load(open(G.homeDir+"beaconloop.hci"))
				oldScan = oldHci.get("scan", {"mac": oldHci.get("myBLEmac",""), "BLE5": oldHci.get("extAdvVerified", False), "allMacs": oldHci.get("allMacs",[])})
				if oldScan.get("BLE5", False) and "{}".format(oldScan.get("mac","")) == "{}".format(myBLEmac):
					hciRoles["scan"]["BLE5"]    = True
					hciRoles["scan"]["allMacs"] = oldScan.get("allMacs",[])
			except Exception:	pass
			writeBeaconloopHci()
			# first publish: the radio INVENTORY is known here, the roles are not yet (they are assigned
			# below) - so functions still read "-". Sent anyway so the states exist even if the role
			# assignment throws; the call after startExtListener fills the functions in.
			sendHciStates()
			setScanAdapter(HCIs["hci"].get(useHCIForBeacon,{}).get("aclMTU",0), myBLEmac)	# remember scan radio; warn only if it later misbehaves

			if myBLEmac ==  -1:
				U.logger.log(20,"myBLEmac wrong: myBLEmac:{}, HCIs:{}".format( myBLEmac, HCIs))
				return 0,  0, -1
			U.logger.log(20,"scan radio -> useHCIForBeacon:{};  myBLEmac:{}; devId:{}, bus:{};  DT:{:.3f}" .format(useHCIForBeacon, myBLEmac, devId, bus, tryDeltaTime(startTime)))
			
			if 	rpiDataAcquistionmethod.find("hcidump") == 0:
				cmd	 = "sudo hciconfig {} leadv 3 &".format(useHCIForBeacon)
				ret = readPopen(cmd)
				U.logger.log(logLevelStart,"cmd:{} .. ret:{}, DT:{:.3f}".format(cmd, ret, tryDeltaTime(startTime)) )

			# ROLE/RADIO assignment for extended scanning. The iBeacon broadcast uses LEGACY
			# advertising commands and a controller LOCKS to the first command set it sees
			# after reset - so the extAdv SCAN adapter must never see them (live-seen: zero
			# messages otherwise). RULE: BLE5 needs 3 radios, one per role (scan / connect /
			# broadcast) - with fewer, extended scanning stays OFF and everything runs
			# legacy exactly as before. Broadcast prio among the leftovers: CLONE dongle
			# first (advertising is the one job a clone does flawlessly) > internal > good.
			# broadcast rides along with the SCANNER on the same external dongle: the iBeacon
			# advertisement goes out once every ~8-10 s (adv interval 0x3000-0x4000, see
			# startHCIBroadCast), so it costs the scan radio practically nothing, and it keeps
			# the INTERNAL radio free for BLEconnect alone (connects are the job that suffers
			# most from a busy radio). extAdv radios are never used here anyway - they are
			# reserved for the E1 extended listener, and a legacy adv command would lock
			# their controller into the legacy command family.
			broadcastHCI = useHCIForBeacon
			U.logger.log(20,"broadcast role -> {} (with the scanner; ~1 adv per 8-10 s), internal stays free for BLEconnect".format(broadcastHCI))
			extScanBlockedByAdv[0] = False
			connectPick = ""
			try:	connectPick = "{}".format(U.selectHCI(HCIs["hci"], "-1", "USB", role="connect")[0])	# same deterministic pick BLEconnect makes
			except Exception:	pass
			_pinConn = pinnedRadio(("bleconnect",), HCIs["hci"], taken=(useHCIForBeacon,))
			if _pinConn != "" and _pinConn != connectPick:
				U.logger.log(20,"BLEconnect role PINNED to {} by the device dialog (auto pick was {})".format(_pinConn, connectPick if connectPick else "?"))
				connectPick = _pinConn
			if HCIs["hci"].get(useHCIForBeacon,{}).get("extAdv", False):
				upOthers = [h for h in HCIs["hci"] if h != useHCIForBeacon and HCIs["hci"][h].get("upDown","") == "UP"]
				# The ONLY thing extended scanning needs is that the iBeacon BROADCAST moves OFF this
				# radio - a legacy adv command locks the controller into the legacy command family and
				# extended scanning dies. So the question is NOT "are there 3 radios" (that test kept
				# a 2-radio rpi on BLE4 even though the internal was sitting right there, free to
				# advertise): it is "is there a non-BLE5 radio that can carry the broadcast".
				# The internal is the natural one - it already holds BLEconnect and one advertisement
				# every 8-10 s costs it nothing. extAdv radios are never used for broadcast: an adv
				# command would lock THEM out of extended mode too.
				pool   = [h for h in upOthers if h != connectPick] or upOthers
				_noExt = [h for h in pool     if not HCIs["hci"][h].get("extAdv", False)] \
						 or [h for h in upOthers if not HCIs["hci"][h].get("extAdv", False)]
				if _noExt:
					_noExt.sort(key=lambda h: (0 if 0 < HCIs["hci"][h].get("aclMTU",0) <= 400 else (1 if "{}".format(HCIs["hci"][h].get("bus","")).upper() == "UART" else 2), "{}".format(HCIs["hci"][h].get("BLEmac",""))))
					broadcastHCI = _noExt[0]
					U.logger.log(20,"radio roles: scan(EXTENDED):{}  connect:{}  broadcast:{}".format(useHCIForBeacon, connectPick if connectPick else "?", broadcastHCI))
				else:
					extScanBlockedByAdv[0] = True
					U.logger.log(20,"extended scanning NOT enabled: no non-BLE5 radio free to carry the iBeacon broadcast, it would have to stay on the scan radio {} and lock it into the legacy command family -> everything BLE4 as before".format(useHCIForBeacon))
					reportBLE5("no - no radio free to take the broadcast off the BLE5 scan radio")
			# the rpi's IDENTITY mac = the iBeacon TRANSMITTER (this is what other rpis hear
			# for online detection and what the plugin links the rpi device to) - piMAC in
			# every message uses this, NEVER the scanner's mac
			broadcastMAC[0] = "{}".format(HCIs["hci"].get(broadcastHCI,{}).get("BLEmac", myBLEmac))
			hciRoles["broadcast"]  = {"mac": broadcastMAC[0], "hci": broadcastHCI}
			hciRoles["BLEconnect"] = {"mac": "{}".format(HCIs["hci"].get(connectPick,{}).get("BLEmac","")), "hci": connectPick}
			# extended-listener role: a BLE5 radio holding NO other role runs EXTENDED
			# scanning ONLY (Ruuvi Air E1 etc.) - see execExtListener.
			extListenerHCI = ""
			_extReasons = []
			# 2-RADIO RPI: NO BLE5, BLEconnect gets the second radio. With only two adapters the
			# scan and connect roles collapse onto the SAME one (the BLE5 dongle is picked LAST for
			# both), so reserving the other as extended listener leaves BLEconnect with nothing: it
			# refuses beaconloop's scan radio, finds the listener excluded and dies with "BLE STACK
			# is not UP" (live-seen on pi#15, which then flip-flopped between working BLE5 and
			# working beep depending on whether the extAdv probe answered in time). beep/battery/
			# switchbot outrank E1 reception - a THIRD radio is what buys BLE5 back.
			_upRadios = [h for h in HCIs["hci"] if HCIs["hci"][h].get("upDown","") == "UP"]
			# EXCEPTION to the "BLE5 needs 3 radios" rule: a BLE5-ONLY dongle (BLE4 scan commands
			# answered 0x0C, e.g. Barrot/UGREEN 33fa:0012) can do NOTHING else - it cannot scan BLE4
			# and it is the worst possible connect radio. Reserving it for BLE5 therefore takes
			# nothing away from anybody: scan, broadcast and BLEconnect all live on the internal
			# radio anyway, exactly as they would on a 1-radio rpi. The rule exists to stop a USABLE
			# second radio being parked on E1 duty while BLEconnect starves - that is not this case.
			# Requires a UART radio: without one there is no radio left that can scan BLE4 at all.
			_uart     = [h for h in _upRadios if "{}".format(HCIs["hci"][h].get("bus","")).upper() == "UART"]
			_ble5Only = [h for h in _upRadios if HCIs["hci"][h].get("extAdv", False) and not HCIs["hci"][h].get("ble4", True)]
			_ble5OnlyOK = (len(_upRadios) == 2 and len(_uart) > 0 and len(_ble5Only) == 1
							and _ble5Only[0] not in (useHCIForBeacon, broadcastHCI, connectPick))
			if _ble5OnlyOK:
				extListenerHCI = _ble5Only[0]
				U.logger.log(20,"extended-listener role -> {} (mac {}) - BLE5-ONLY dongle on a 2-radio rpi: it cannot scan BLE4 and cannot connect, so BLE5 is the only thing it can contribute; scan/broadcast/BLEconnect stay on {}".format(
								extListenerHCI, HCIs["hci"][extListenerHCI].get("BLEmac",""), _uart[0]))
			elif len(_upRadios) < 3:
				_extReasons.append("only {} radio(s) UP, BLE5 needs 3 - the 2nd one belongs to BLEconnect".format(len(_upRadios)))
				reportBLE5("no - only {} radios, BLE5 needs 3 (BLEconnect gets the 2nd)".format(len(_upRadios)))
			else:
				for _eHH in HCIs["hci"]:
					if _eHH in (useHCIForBeacon, broadcastHCI, connectPick):
						_extReasons.append("{}=busy({})".format(_eHH, "scan" if _eHH==useHCIForBeacon else "broadcast" if _eHH==broadcastHCI else "connect"))
						continue
					if not HCIs["hci"][_eHH].get("extAdv", False):
						_extReasons.append("{}=noBLE5".format(_eHH))
						continue
					if HCIs["hci"][_eHH].get("upDown","") != "UP":
						_extReasons.append("{}=DOWN".format(_eHH))
						continue
					extListenerHCI = _eHH
					break
			_pinL = pinnedRadio(("scanBLE5",), HCIs["hci"], taken=(useHCIForBeacon, broadcastHCI, connectPick))
			if _pinL != "" and _pinL != extListenerHCI:
				# an explicit pin also lifts the "BLE5 needs 3 radios" rule - the user has said which
				# radio does BLE5, so the only question left is whether it is free, which pinnedRadio checked
				U.logger.log(20, "BLE5-listener role PINNED to {} by the device dialog (auto pick was {})".format(_pinL, extListenerHCI if extListenerHCI else "none"))
				extListenerHCI = _pinL
			if extListenerHCI == "":
				U.logger.log(20, "extended-listener role: NO free BLE5 radio -> no E1/extended reception on this rpi ({})".format(", ".join(_extReasons) if _extReasons else "no adapters"))
			else:
				# the negative case has always been logged - say the POSITIVE one too, or a working
				# BLE5 setup is indistinguishable from "no BLE5 radio at all" in the startup log
				U.logger.log(20, "extended-listener role -> {} (mac {}, bus {}, BLE5) - reserved for extended/E1 reception only".format(extListenerHCI, HCIs["hci"][extListenerHCI].get("BLEmac",""), HCIs["hci"][extListenerHCI].get("bus","")))
			hciRoles["extListener"] = {"mac": "{}".format(HCIs["hci"].get(extListenerHCI,{}).get("BLEmac","")), "hci": extListenerHCI,
										"bus": "{}".format(HCIs["hci"].get(extListenerHCI,{}).get("bus",""))}

			# REJECTED SETUP: a BLE5-ONLY dongle (BLE4 scan commands answered 0x0C) and NO uart radio.
			# Then nothing can scan BLE4: that dongle refuses the commands and there is no internal
			# radio to fall back on, so the rpi receives no ordinary beacons at all. WITH a uart
			# radio the same dongle is fine - the internal does the BLE4 work and the dongle becomes
			# the BLE5 listener (see the extended-listener block above), which is why this only
			# fires when the uart is missing.
			try:
				_reject = [h for h in HCIs["hci"]
								if HCIs["hci"][h].get("upDown","") == "UP"
								and HCIs["hci"][h].get("extAdv", False)
								and not HCIs["hci"][h].get("ble4", True)]
				_uartUp = [h for h in HCIs["hci"]
								if HCIs["hci"][h].get("upDown","") == "UP"
								and "{}".format(HCIs["hci"][h].get("bus","")).upper() == "UART"]
				_ble4Cap = [h for h in HCIs["hci"]
								if HCIs["hci"][h].get("upDown","") == "UP" and HCIs["hci"][h].get("ble4", True)]
				if _reject and not _uartUp and not _ble4Cap:
					_msg = ("unsupported radio combination: BLE5-ONLY dongle {} ({}) and no internal (uart) radio."
							" That dongle refuses BLE4 scan commands (0x0C) and there is nothing else that could"
							" scan, so this rpi cannot receive ordinary beacons at all."
							" FIX: add an internal/uart radio or a dongle that does BLE4 (e.g. ASUS/Realtek 0b05:190e)."
							).format(_reject[0], HCIs["hci"][_reject[0]].get("BLEmac",""))
					U.logger.log(20, _msg)
					U.sendURL(data={"ERROR": _msg})
			except Exception:
				U.logger.log(20,"", exc_info=True)
			writeBeaconloopHci()
			sendBLE5State()						# publishes which radio does BLE5 (function "scan5")
			startHCIBroadCast(broadcastHCI, pi, startTime, logLevelStart)
			startExtListener(extListenerHCI)
			# publish AGAIN now that every role is known. The call further up runs before broadcast /
			# BLEconnect / extListener are assigned, so on its own it left those radios showing "-"
			# as their function - and the refresh inside sendBLE5State does not help for the first
			# minute, it returns early during its settle window.
			sendHciStates()
			ret = HCIs["ret"]

		if ret[1] != "":	
			U.logger.log(20,"BLE start returned:\n{}error:>>{}<<".format(ret[0],ret[1]))
			U.sendURL( data={"ERROR":"bluetooth startup: err-BLE-start"}, squeeze=False, wait=False )

		else:
			U.logger.log(20,"BLE start returned:\n{}my BLE mac# is >>{}<<, on bus:{}".format(ret[0], myBLEmac, bus))
			if useHCIForBeacon in HCIs["hci"]:
				if HCIs["hci"][useHCIForBeacon]["upDown"] == "DOWN":
					if downCount > 1:
						U.logger.log(20,"reboot requested,{} is DOWN using hciconfig ".format(useHCIForBeacon))
						U.setRebootRequest("bluetooth_startup {} is DOWN using hciconfig FORCE".format(useHCIForBeacon))
						U.sendURL( data={"ERROR":"bluetooth startup: err-BLE-down"}, squeeze=False, wait=False )
						time.sleep(10)
					downCount +=1
					time.sleep(10)
					return 0,  "", -1
			else:
				U.logger.log(20," {}  not in hciconfig list".format(useHCIForBeacon))
				downCount += 1
				if downCount > 1:
					U.sendURL( data={"ERROR":"bluetooth startup: err-BLE-channel-missing"}, squeeze=False, wait=False )
					U.logger.log(20,"reboot requested,{} is DOWN using hciconfig ".format(useHCIForBeacon))
					U.setRebootRequest("bluetooth_startup {} is DOWN using hciconfig FORCE".format(useHCIForBeacon))
					time.sleep(10)
				downCount += 1
				time.sleep(10)
				return 0,  "", -1
					
				
		if myBLEmac == "":
			U.sendURL( data={"ERROR":"bluetooth startup: err-BLE-start-mac-empty"}, squeeze=False, wait=False )
			return 0, "", -1

	except Exception as e: 
		U.logger.log(20,"", exc_info=True)
		U.sendURL( data={"ERROR":"bluetooth startup: err-BLE-start"}, squeeze=False, wait=False )
		time.sleep(10)
		U.writeFile("temp/restartNeeded","bluetooth_startup.ERROR:{}".format(e))
		downHCI(useHCIForBeacon)
		time.sleep(0.2)
		return 0, "", -5


	# role-format rewrite; a scan-mac CHANGE invalidates a stored BLE5 verdict
	if "{}".format(hciRoles["scan"].get("mac","")) != "{}".format(myBLEmac):
		hciRoles["scan"] = {"mac": myBLEmac, "hci": useHCIForBeacon, "bus": bus, "BLE5": False}
	else:
		hciRoles["scan"].update({"hci": useHCIForBeacon, "bus": bus})
	writeBeaconloopHci()


	if rpiDataAcquistionmethod.find("hcidump" ) == 0:
		return "", myBLEmac, 0


	if rpiDataAcquistionmethod == "socket":
		try:
			try:
				if currentBLESocket is not None: currentBLESocket.close()	# close old socket on stack restart
			except:	pass
			currentBLESocket = None
			sock = bluez.hci_open_dev(devId)
			currentBLESocket = sock
			U.logger.log(20, "ble thread started")
		except Exception as e:
			U.logger.log(20,"error accessing bluetooth device...")
			if downCount > 2:
				U.setRebootRequest("bluetooth_startup.ERROR:{} FORCE ".format(e))
				downHCI(useHCIForBeacon)
			downCount +=1
			return 0,  "", -1
		
		try:
			hci_le_set_scan_parameters(sock)
			hci_enable_le_scan(sock)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
			if "{}".format(e).find("Bad file descriptor") >-1:
				U.setRebootRequest("bluetooth_startup.ERROR:Bad_file_descriptor...SSD.damaged? FORCE ")
			if "{}".format(e).find("Network is down") >-1:
				if downCount > 2:
					U.setRebootRequest("bluetooth_startup.ERROR:Network_is_down...need_to_reboot FORCE ")
				downCount +=1
			downHCI(useHCIForBeacon)
			return 0, "", -1

	return sock, myBLEmac, 0



#################################
def restartLESCAN(hciUse, loglevel, force=False):
	"""Restarts the BLE lescan process on the given HCI interface (skipped in socket mode), throttled to at most once every 5 seconds unless forced, by killing the old hcitool process and launching a new background lescan.

	Inputs:
	    hciUse (str): HCI interface to run lescan on, e.g. 'hci0'
	    loglevel (int): Logging level for messages
	    force (bool): If True, restart even if within the throttle interval
	Outputs:
	    None: Kills/relaunches hcitool lescan background process and logs output
	"""
	global lastLESCANrestart, currentBLESocket
	try:
		if rpiDataAcquistionmethod == "socket":
			# the controller can silently drop LE-scan state (e.g. after a gatttool beep/battery
			# session on the same adapter) -> re-enable scanning on the open socket
			if currentBLESocket is not None and (tryDeltaTime(lastLESCANrestart) > 5 or force):
				lastLESCANrestart = time.time()
				try:
					# set parameters BEFORE enabling: any hciconfig reset reverts the controller
					# to its defaults (PASSIVE scan, no scan responses/mfg_info) - re-enabling
					# alone would silently reintroduce that. set_scan_parameters disables first.
					hci_le_set_scan_parameters(currentBLESocket)
					time.sleep(0.05)
					hci_enable_le_scan(currentBLESocket)
					U.logger.log(loglevel, "socket method: re-set scan params (active) + re-enabled LE scan")
				except Exception as e:
					# the adapter was likely just reset/downed - e.g. a beep/battery gatt session on the
					# SAME adapter in SINGLE-DONGLE mode does "hciconfig reset", which downs the shared
					# radio - so our socket is now stale (ENETDOWN / "Network is down"). Bring the adapter
					# back up and REBUILD the socket, then re-enable scanning; the watchdog restarts only
					# if that also fails.
					U.logger.log(20, "socket method: re-enable LE scan failed ({}) - bringing {} up and rebuilding socket".format(type(e).__name__, hciUse))
					try:
						readPopen("sudo /bin/hciconfig {} up".format(hciUse))
						time.sleep(0.3)
						try:
							if currentBLESocket is not None: currentBLESocket.close()
						except Exception: pass
						currentBLESocket = bluez.hci_open_dev(int("0"+hciUse.replace("hci","")))
						hci_le_set_scan_parameters(currentBLESocket)
						time.sleep(0.05)
						hci_enable_le_scan(currentBLESocket)
						U.logger.log(20, "socket method: socket rebuilt + LE scan re-enabled on {}".format(hciUse))
					except Exception:
						U.logger.log(20, "socket method: socket rebuild failed - the no-message watchdog will restart the stack", exc_info=True)
			return
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
			cmd	 = "sudo hcitool -i {} lescan --duplicates  > /dev/null 2>&1 &".format(hciUse)
			#cmd	 = "sudo hcitool -i {} lescan --privacy --passive --discovery=l  > /dev/null 2>&1 &".format(hciUse,G.homeDir)
			#cmd	 = "sudo hcitool -i {} lescan --passive --discovery=l  > /dev/null 2>&1 &".format(hciUse,G.homeDir)
			#cmd	 = "sudo hcitool -i {} lescan > /dev/null 2>&1 &".format(hciUse,G.homeDir)
			ret = readPopen(cmd)
			U.logger.log(loglevel,"cmd:{} .. ret:{}...  dT:{:.3f}".format(cmd, ret, tryDeltaTime(tt)) )
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return


#################################
def downHCI(hciUse):
	"""Brings the given HCI interface down and restarts the bluetooth and dbus system services via background shell commands to recover the Bluetooth stack.

	Inputs:
	    hciUse (str): HCI interface to bring down, e.g. 'hci0'
	Outputs:
	    None: Runs hciconfig down and service restart shell commands
	"""
	try:
		subprocess.Popen("sudo hciconfig {} down &".format(hciUse),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE) # enable bluetooth
		time.sleep(0.2)
		subprocess.Popen("sudo service bluetooth restart &",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(0.2)
		subprocess.Popen("sudo service dbus restart &",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		time.sleep(0.2)
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return



#################################
def startHCUIDUMPlistnr(hciUse):
	"""Starts an hcidump --raw listener subprocess on the given HCI interface (up to 3 attempts), verifies it is running, sets its stdout to non-blocking, and stores the process handle globally for later reading.

	Inputs:
	    hciUse (str): HCI interface to dump from, e.g. 'hci0'
	Outputs:
	    str: Empty string on success, or an error message describing the failure
	"""
	global ListenProcessFileHandle

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
				U.logger.log(20,"hci#: {}; error connecting {}".format(ii, msg) )
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
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return  retMSG

#################################
def stopHCUIDUMPlistener():
	"""Stops the hcidump and hcitool/lescan listener processes by killing them and terminating the stored subprocess handle; returns early if not reading from hcidump.

	Inputs:
	    None.
	Outputs:
	    None: Kills listener processes and clears the global process handle
	"""
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
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 

####-------------------------------------------------------------------------####
def openEncoding(ff, readOrWrite):
	"""Opens a file with UTF-8 encoding in the given mode, using the built-in open with encoding on Python 3 or codecs.open on Python 2 for compatibility.

	Inputs:
	    ff (str): path to the file to open
	    readOrWrite (str): open mode such as 'r' or 'w'
	Outputs:
	    file object: open UTF-8 encoded file handle
	"""
	if sys.version_info[0]  > 2:
		return open( ff, readOrWrite, encoding="utf-8")
	else:
		return codecs.open( ff ,readOrWrite, "utf-8")

def toBytesIfPy3(text):
	"""Encodes a string to UTF-8 bytes when running under Python 3, otherwise returns the text unchanged for Python 2 compatibility.

	Inputs:
	    text (str): text to convert to bytes on Python 3
	Outputs:
	    bytes or str: UTF-8 bytes on Python 3, original string on Python 2
	"""
	if sys.version_info[0]  > 2:
		return bytes(text,"utf8")
	else:
		return text


#################################
def readHCUIDUMPlistener():
	"""Reads BLE advertisement data either from a test file (test mode) or from the live hcidump listener subprocess stdout, decodes it, assembles it into complete messages via combineLines, and handles transient read errors gracefully.

	Inputs:
	    None.
	Outputs:
	    list: list of raw assembled HCI dump message strings, empty on no data or error
	"""

	if readFrom != "": # read from file
		messages = []
		try:
			if os.path.isfile(readFrom):
				f = openEncoding(readFrom,"r")
				messages = f.read()
				f.close()
				U.removeFile("{}".format(readFrom))
				if len(messages) > 5:
					messages = [messages.strip("\n")]
				
		except Exception :
			U.logger.log(20,"", exc_info=True)
			messages = []

		if len(messages) > 0: 
			U.logger.log(20, "TestMode: read {}".format(messages))
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
	except Exception as e:
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
#################################
def combineLines(lines):
	"""Accumulates raw hcidump output lines into a persistent buffer, filtering out non-data lines, splits on the '>' record marker, and returns complete fixed-length messages while retaining any incomplete trailing fragment in the buffer.

	Inputs:
	    lines (str): raw text chunk read from the hcidump listener
	Outputs:
	    list: list of complete message strings, empty if none ready or on error
	"""
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
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return []


#################################
def fixOldNames():

	"""Migrates a legacy history file by renaming 'beaconsExistingHistory' to the current 'beacon_ExistingHistory' filename if the old file still exists.

	Inputs:
	    None.
	Outputs:
	    None: renames file on disk via shell mv
	"""
	if os.path.isfile(G.homeDir+"beaconsExistingHistory"):
		subprocess.call("sudo mv "+G.homeDir+"beaconsExistingHistory " + G.homeDir+"beacon_ExistingHistory", shell=True)

def readParams(init=False):
	"""Reads the plugin parameter/config input and populates many module-level globals controlling BLE scanning, acceptance rules, and per-MAC BLE sensor settings/defaults; initializes globals on first call, restarts on data-acquisition-method change, and loads known beacon tags and beacon parameter files.

	Inputs:
	    init (bool): if True, initialize default global state before reading params
	Outputs:
	    None: updates many module globals and reads config/known-tag/parameter files
	"""
	global collectMsgs, loopMaxCallBLE, signalDelta, fastDownList, ignoreMAC
	global onlyTheseMAC, enableiBeacons, minSignalOff, minSignalOn, knownBeaconTags
	global acceptNewBeaconsMinSIgnal, acceptNewBeaconMAC, acceptNewTagiBeacons, acceptNewMFGNameBeacons
	global oldRaw, lastRead
	global rpiDataAcquistionmethod
	global batteryLevelUUID
	global fastBLEReaction, output
	global ignoreBeaconsIfRssiLessThan

	if init:
		collectMsgs			= 10  # in parse loop collect how many messages max	  ========	all max are an "OR" : if one hits it stops
		loopMaxCallBLE		= 900 # max loop count	in main pgm to collect msgs
		G.ipOfServer	  	= ""
		G.passwordOfServer	= ""
		G.userIdOfServer  	= ""
		G.myPiNumber	  	= "0"
		lastRead			= 0
		oldRaw				= "xxx"

	inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
	doParams = True
	if inp == "":				doParams = False
	if lastRead2 == lastRead:	doParams = False
	lastRead   = lastRead2
	# ignore the plugin's per-build "configured" timestamp: a cosmetic resend (nothing substantive
	# changed) must not force a full param reprocess (rebuild macList etc.)
	if U.stripConfigured(inpRaw) == U.stripConfigured(oldRaw):	doParams = False
	oldRaw	   = inpRaw

	if doParams:
		try:
			if "output" in inp: output = copy.deepcopy(inp["output"])
			else: output = {}
			if "enableiBeacons"		in inp:	 enableiBeacons =	   (inp["enableiBeacons"])
			if enableiBeacons == "0":
				U.logger.log(50," termination ibeacon scanning due to parameter file")
				time.sleep(0.5)
				stopHCUIDUMPlistener()
				sys.exit(3)
			U.getGlobalParams(inp)

			acceptNewMFGNameBeacons = ""
			if "acceptNewBeaconsMinSIgnal"				in inp:	 acceptNewBeaconsMinSIgnal =		int(inp["acceptNewBeaconsMinSIgnal"])
			if "acceptNewTagiBeacons"			in inp:	 acceptNewTagiBeacons =		(inp["acceptNewTagiBeacons"])
			if "acceptNewBeaconMAC"				in inp:	 acceptNewBeaconMAC =		(inp["acceptNewBeaconMAC"])
			if "acceptNewMFGNameBeacons"		in inp:	 acceptNewMFGNameBeacons =	(inp["acceptNewMFGNameBeacons"])
			if "ignoreBeaconsIfRssiLessThan"	in inp:	 ignoreBeaconsIfRssiLessThan =	(inp["ignoreBeaconsIfRssiLessThan"])


			global hciRolesPinned
			_pins = inp.get("hciRolesPinned", {}) if isinstance(inp.get("hciRolesPinned", {}), dict) else {}
			if _pins != hciRolesPinned:
				U.logger.log(20,"radio role pins from the device dialog: {}".format(_pins if _pins else "none - the rpi decides"))
			hciRolesPinned = _pins

			if bluezPresent:
				if "rpiDataAcquistionmethod" in inp:	 
					xx =			 								(inp["rpiDataAcquistionmethod"])
					if xx != rpiDataAcquistionmethod and rpiDataAcquistionmethod != "":
						U.restartMyself(param="", reason="new data aquisition method", python3=usePython3)
					rpiDataAcquistionmethod = xx
				else:
					rpiDataAcquistionmethod = "socket"		# key missing (stale params file) -> new default
			else:
					rpiDataAcquistionmethod = "hcidump"

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
							try:	BLEsensorMACs[mac]["offsetCO2"]   			= float(sensD["offsetCO2"])
							except: BLEsensorMACs[mac]["offsetCO2"]				= 0.
							try:	BLEsensorMACs[mac]["multTemp"] 				= float(sensD["multTemp"])
							except: BLEsensorMACs[mac]["multTemp"] 				= 1.
							try:	BLEsensorMACs[mac]["multHump"] 				= float(sensD["multHump"])
							except: BLEsensorMACs[mac]["multHump"] 				= 1.
							try:	BLEsensorMACs[mac]["multCO2"] 				= float(sensD["multCO2"])
							except: BLEsensorMACs[mac]["multCO2"] 				= 1.
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
								BLEsensorMACs[mac]["accelerationX"]					= 0
								BLEsensorMACs[mac]["accelerationY"]					= 0
								BLEsensorMACs[mac]["accelerationZ"]					= 0
								BLEsensorMACs[mac]["light"]							= -1
								BLEsensorMACs[mac]["lastUpdate"]					= tryDeltaTime( 50)
								BLEsensorMACs[mac]["lastUpdate1"]					= 0
								BLEsensorMACs[mac]["lastUpdate2"]					= 0
								BLEsensorMACs[mac]["lastUpdate3"]					= 0
								BLEsensorMACs[mac]["SOS"]							= False
								BLEsensorMACs[mac]["hum"]							= -100
								BLEsensorMACs[mac]["CO2"]							= -100
								BLEsensorMACs[mac]["Formaldehyde"]					= -100
								BLEsensorMACs[mac]["temp"]							= -100.
								BLEsensorMACs[mac]["tempAve"]						=[-100,-100,-100]
								BLEsensorMACs[mac]["humAve"]						=[-100,-100,-100]
								BLEsensorMACs[mac]["hum"]							= -100
								BLEsensorMACs[mac]["Illuminance"]					= -100
								BLEsensorMACs[mac]["AmbientTemperature"] 			= -100
								BLEsensorMACs[mac]["t1"]							= 0
								BLEsensorMACs[mac]["t2"]							= 0
								BLEsensorMACs[mac]["t3"]							= 0
								BLEsensorMACs[mac]["modelId"]						= ""
								BLEsensorMACs[mac]["onOff"]							= False
								BLEsensorMACs[mac]["onOff1"]						= False
								BLEsensorMACs[mac]["onOff2"]						= False
								BLEsensorMACs[mac]["onOff3"]						= False
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
								BLEsensorMACs[mac]["batteryVoltage"] 		 		= -1
								BLEsensorMACs[mac]["chipTemperature"] 		 		= -1
								BLEsensorMACs[mac]["secsSinceStart"] 		 		= -1
								BLEsensorMACs[mac]["nMessages"] 		 			= 0
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


		except Exception :
			U.logger.log(20,"", exc_info=True)



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
		signalDelta		 = InParams.get("signalDelta", {})
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
	"""Initializes the per-cycle beacon data dictionary entry for a given MAC with a fresh template of default beacon fields (txPower, rssi, timeSt, batteryLevel, etc.).

	Inputs:
	    mac (str): beacon MAC address key to reset for this read cycle
	Outputs:
	    None: resets beaconsThisReadCycle[mac] global entry
	"""
	try:
			#beaconsThisReadCycle[mac]={"typeOfBeacon":"", "txPower":0, "rssi":0, "timeSt":0,"batteryLevel":"","mfg_info":"","mode":"","onOffState":"", "iBeacon":"","trigger":0,"TLMenabled":"","inMotion":"","calibrated":"","position":"","light":"","allowsConnection":""}
			beaconsThisReadCycle[mac]={"typeOfBeacon":"", "txPower":0, "rssi":0, "timeSt":0,"batteryLevel":"","mfg_info":"","mode":"","onOffState":"", "trigger":0,"TLMenabled":"","inMotion":"","calibrated":"","position":"","light":"","allowsConnection":""}
	except Exception :
		U.logger.log(20,"", exc_info=True)

#################################
def readbeacon_ExistingHistory():
	"""Loads the persisted beacon history from the beacon_ExistingHistory file into the global dict, discarding it entirely if any entry lacks the expected 'fastDown' field, and resets the last-write timestamp.

	Inputs:
	    None.
	Outputs:
	    None: populates beacon_ExistingHistory global from file
	"""
	global	beacon_ExistingHistory, lastWriteHistory
	try:
		fg = open("{}temp/beacon_ExistingHistory".format(G.homeDir),"r")
		beacon_ExistingHistory = json.loads(fg.read())
		fg.close()
		reset = False
		for beacon in beacon_ExistingHistory:
			if "fastDown" not in beacon_ExistingHistory[beacon]:
				reset=True
				break				
		if reset:
			beacon_ExistingHistory = {}
	except: 
		beacon_ExistingHistory = {}
	lastWriteHistory=time.time()
	return
	

#################################
def writebeacon_ExistingHistory():
	"""Writes the in-memory beacon history dictionary to the beacon_ExistingHistory file as JSON, but only if at least 30 seconds have passed since the last write; triggers a reboot if the filesystem is read-only.

	Inputs:
	    None.
	Outputs:
	    None: writes history JSON to file, may reboot on read-only filesystem
	"""
	global lastWriteHistory
	if tryDeltaTime(lastWriteHistory ) < 30: return
	lastWriteHistory=time.time()
	try:
		fg = open("{}temp/beacon_ExistingHistory".format(G.homeDir),"w")
		fg.write(json.dumps(beacon_ExistingHistory))
		fg.close()
		U.makeOwnFileWritable("{}temp/beacon_ExistingHistory".format(G.homeDir))	# we run as root - do not leave it root-owned
	except Exception as e:
		if "{}".format(e).find("Read-only file system:") >-1:
			U.doReboot(tt=0)
	return 

#################################
def stripOldHistory(mac):
	"""Trims a beacon's stored RSSI/timestamp/trigger history for a MAC, dropping oldest entries to keep at most a small recent window and removing entries older than the configured retention period.

	Inputs:
	    mac (str): beacon MAC whose history lists to prune
	Outputs:
	    None: mutates beacon_ExistingHistory[mac] lists in place
	"""

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
	"""Clears all accumulated history for a given beacon MAC by emptying its rssi, timeSt, and trigger lists and zeroing its count.

	Inputs:
	    mac (str): beacon MAC whose history to clear
	Outputs:
	    None: resets beacon_ExistingHistory[mac] history fields
	"""
	try:
		if  mac in beacon_ExistingHistory:
			beacon_ExistingHistory[mac]["rssi"]		= []
			beacon_ExistingHistory[mac]["timeSt"]	= []
			beacon_ExistingHistory[mac]["trigger"]	= []
			beacon_ExistingHistory[mac]["count"]	= 0

	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 

#################################
def handleHistory():
	"""Performs periodic history maintenance by pruning old entries for every tracked beacon and then persisting the history to disk.

	Inputs:
	    None.
	Outputs:
	    None: strips old history per beacon and saves to file
	"""

	for beacon in beacon_ExistingHistory:
		stripOldHistory(beacon)
	# save history to file
	writebeacon_ExistingHistory() 
	return

#################################, check if signal strength is acceptable for fastdown 
def copyToHistory(mac):
	"""Initializes (or resets) the running-history record for a given beacon MAC by copying its current read-cycle entry into beacon_ExistingHistory and clearing the accumulating fields (rssi, timeSt, trigger lists, txPower, fastDown flag, count).

	Inputs:
	    mac (str): Beacon MAC address key into the history dictionaries
	Outputs:
	    None: mutates the global beacon_ExistingHistory dict; logs on exception
	"""
	try:
		if mac not in beacon_ExistingHistory:
			beacon_ExistingHistory[mac]= copy.copy(beaconsThisReadCycle[mac])
		beacon_ExistingHistory[mac]["fastDown"]		= False
		beacon_ExistingHistory[mac]["rssi"]			= []
		beacon_ExistingHistory[mac]["timeSt"]		= []
		beacon_ExistingHistory[mac]["trigger"]		= []
		beacon_ExistingHistory[mac]["txPower"]		= ""
		beacon_ExistingHistory[mac]["count"]		= 1

		#U.logger.log(20,"mac:{}; beacon_ExistingHistory:{}".format(mac, beacon_ExistingHistory[mac]))

	except Exception :
		U.logger.log(20,"", exc_info=True)


#################################, check if signal strength is acceptable for fastdown 
def fillHistory(mac):
	"""Appends the current read-cycle's rssi, timestamp and trigger to the beacon's accumulated history, increments its message count, copies other state fields, and detects whether any monitored field changed so the message should be sent immediately; then trims old history.

	Inputs:
	    mac (str): Beacon MAC address key into the history dictionaries
	Outputs:
	    bool: True if a monitored field changed and the message should be sent now, else False
	"""
	try:
		sendNowdDataWasChanged = False
		if mac not in beacon_ExistingHistory: 
			copyToHistory(mac) 
		beacon_ExistingHistory[mac]["rssi"].append(beaconsThisReadCycle[mac]["rssi"])
		beacon_ExistingHistory[mac]["timeSt"].append(beaconsThisReadCycle[mac]["timeSt"])
		beacon_ExistingHistory[mac]["trigger"].append(beaconsThisReadCycle[mac]["trigger"])
		beacon_ExistingHistory[mac]["count"] += 1
		sendImmediatelyIfChanged = beaconsThisReadCycle[mac].get("sendImmediatelyIfChanged",False)
		testList = {"batteryLevel":1, "calibrated":1, "position":1, "mode":1, "onOffState":1, "light":1, "TLMenabled":1, "mfg_info":1, "subtypeOfBeacon":1, "inMotion":1, "allowsConnection":1, "analyzed":1, "txPower":1}
		for xx in beaconsThisReadCycle[mac]:
			if xx in ["rssi","timeSt","trigger"]: continue
			testList[xx] = 1
		if 	"sendImmediatelyIfChanged" in testList: del testList["sendImmediatelyIfChanged"]

		doNotTestForChange = ["typeOfBeacon", "subtypeOfBeacon", "TLMenabled", "mfg_info", "analyzed", "subtypeOfBeacon", "timeSt", "txPower"]

		for xx in testList:
			if sendImmediatelyIfChanged:
				if beaconsThisReadCycle[mac][xx] != "":
					if xx not in doNotTestForChange and beacon_ExistingHistory[mac][xx] != beaconsThisReadCycle[mac][xx]:
						sendNowdDataWasChanged = True
			beacon_ExistingHistory[mac][xx]	 = beaconsThisReadCycle[mac][xx]

		if "typeOfBeacon" not in beacon_ExistingHistory:
			if beaconsThisReadCycle[mac]["typeOfBeacon"] != "":	
				beacon_ExistingHistory[mac]["typeOfBeacon"]		= beaconsThisReadCycle[mac]["typeOfBeacon"]
		elif beaconsThisReadCycle[mac]["typeOfBeacon"]  not in ["", "other"]:
				beacon_ExistingHistory[mac]["typeOfBeacon"]		= beaconsThisReadCycle[mac]["typeOfBeacon"]

		if mac =="xB0:E9:FE:A4:58:82":  U.logger.log(20,"mac {}; \nbeacon_ExistingHistory:{}; \nbeaconsThisReadCycle{}".format(mac, beacon_ExistingHistory[mac], beaconsThisReadCycle[mac]))
				
		stripOldHistory(mac)
		#U.logger.log(20,"mac {} beaconsThisReadCycle{}".format(mac,beaconsThisReadCycle[mac] ))
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return sendNowdDataWasChanged


#################################
def checkMinMaxSignalAcceptMessage(mac, rssi):
	"""Applies per-beacon minimum-signal hysteresis: returns whether an RSSI reading is strong enough to be accepted, requiring it to exceed minSignalOn to switch on and stay above minSignalOff while already on (based on recent activity within 60 seconds).

	Inputs:
	    mac (str): Beacon MAC address used to look up signal thresholds
	    rssi (int): Measured signal strength in dBm to test against thresholds
	Outputs:
	    bool: True if the signal passes the on/off threshold check (or no threshold set), else False
	"""
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

	except Exception :
		U.logger.log(20,"", exc_info=True)

		
	
#################################
def composeMSG(timeAtLoopStart):
	"""Builds the aggregated outbound message for all beacons seen this read cycle: averages RSSI/txPower per MAC, maps the trigger reason to text, assembles per-beacon data records plus any sensor data and message statistics, sends them via U.sendURL, updates online-beacon tracking and persists beaconsOnline to disk.

	Inputs:
	    timeAtLoopStart (float): Epoch time at the start of the read loop, used to compute collection seconds
	Outputs:
	    int: Number of beacon messages assembled and sent (0 on error)
	"""
	global downCount
	global dataFromSensors
	global messageStats

	try:
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
						writeTrackMac("MSG===  ","data:{}".format(newData), mac)
					beacon_ExistingHistory[mac]["count"] = 1
					beacon_ExistingHistory[mac]["lastMessageSend"] = time.time()
			except Exception :
				U.logger.log(20,"", exc_info=True)
				U.logger.log(20, " error composing mac:{}, beaconsThisReadCycle \n{}".format(mac, beaconsThisReadCycle[mac]))

		nMessages = len(data)
		if nMessages >1: downCount = 0
		#U.logger.log(20," msending data:{}, sensor:{}".format(nMessages, len(dataFromSensors)))

		for ii in range(messageStats["max"]):
			messageStats["numberOfMessagesperRead"][ii] /= (max(1., messageStats["countTotal"])/100.)
			messageStats["numberOfMessagesperRead"][ii] = int(messageStats["numberOfMessagesperRead"][ii])

		if dataFromSensors != {}:
			if waitforcheckIfDelaySend: time.sleep(0.05)
			U.sendURL({"sensors":dataFromSensors, "msgs":data,"stats":{"nMsgDistribution":messageStats["numberOfMessagesperRead"], "total":messageStats["countTotal"]},"pi":str(G.myPiNumber),"piMAC":(broadcastMAC[0] if broadcastMAC[0] != "" else myBLEmac),"secsCol":int(tryDeltaTime(timeAtLoopStart)),"trigger":mapReasonToText[reasonMax]})
			dataFromSensors = {}
		else:
			U.sendURL({"msgs":data,"stats":{"nMsgDistribution":messageStats["numberOfMessagesperRead"], "total":messageStats["countTotal"]},"pi":str(G.myPiNumber),"piMAC":(broadcastMAC[0] if broadcastMAC[0] != "" else myBLEmac),"secsCol":int(tryDeltaTime(timeAtLoopStart)),"trigger":mapReasonToText[reasonMax]})
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
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 0



#################################
def composeMSGForThisMacOnly(mac):
	"""Builds and immediately sends a single-beacon message for one MAC using its latest RSSI and txPower, mapping the trigger to text and attaching extra state fields; used for urgent/out-of-band sends rather than the batched compose.

	Inputs:
	    mac (str): Beacon MAC address whose single message is composed and sent
	Outputs:
	    int: 1 if the message was sent, 0 on error
	"""

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
		U.sendURL({"msgs":[data],"pi":str(G.myPiNumber),"piMAC":(broadcastMAC[0] if broadcastMAC[0] != "" else myBLEmac),"secsCol":1,"trigger":rr})
		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("MSG-s   ", "sending single msg:{}".format(data),mac)
		return 1
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 0



#################################
def checkIfinMotion(mac, tag):
	"""Detects whether a beacon's motion or position state changed since the last reading and, if so, sets its trigger to 9, updates the stored motion/position, and sends an immediate single-beacon message reporting the change.

	Inputs:
	    mac (str): Beacon MAC address to test for motion change
	    tag (str): Beacon tag/type that must be in knownBeaconTags to qualify
	Outputs:
	    bool: True if a motion/position change was detected and reported, else False
	"""

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

	except Exception :
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20,"mac:{}\nbeaconsThisReadCycle:{}".format(mac, beaconsThisReadCycle ))

	return False


#################################
def checkIfDeltaSignal(mac):
	"""Checks whether the latest RSSI deviates from the running average by more than the configured per-beacon signalDelta threshold and, if so, sets trigger 7 and sends an immediate single-beacon message.

	Inputs:
	    mac (str): Beacon MAC address to test for an RSSI delta event
	Outputs:
	    bool: True if the signal delta exceeded the threshold and a message was sent, else False
	"""

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

	except Exception :
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20,"mac:{}\nbeaconsThisReadCycle:{}".format(mac, beaconsThisReadCycle ))

	return False


#################################
def checkIfFastDownForAll(iWhile, nMsgs, dtSend, lastMSGwithGoodData):
	"""Iterates over fast-down beacons and, for any whose last timestamp is older than its configured seconds and not already marked fastDown, sets trigger 3 and the fastDown flag, sends an immediate down message, and empties that beacon's history.

	Inputs:
	    iWhile (int): Current loop iteration counter, used only for tracking logs
	    nMsgs (int): Number of messages this cycle, used only for tracking logs
	    dtSend (float): Seconds until next send, used only for tracking logs
	    lastMSGwithGoodData (float): Epoch time of last good-data message, used only for tracking logs
	Outputs:
	    None: mutates beacon_ExistingHistory, sends messages and empties histories; logs on exception
	"""

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

	except Exception :
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20,"mac {}:  beacon_ExistingHistory={}".format(mac, beacon_ExistingHistory[mac]))

	return

################################, check if signal strength is acceptable for fastdown 
def checkIfBeaconIsBack(mac):
	"""Determines whether a beacon that had gone down/quiet is now back, based on count, history gaps versus sendAfterSecsOfLastMsg, fastDown state and fast-down timing; if so sets the appropriate trigger (4 fastdown-back, 5 back, 2 new), clears fastDown and sends an immediate message.

	Inputs:
	    mac (str): Beacon MAC address to test for re-appearance
	Outputs:
	    bool: True if the beacon was determined to be back and a message was sent, else False
	"""

	try:
		#U.logger.log(20,"mac{} checkIfBeaconIsBack trackMac:{}  logCountTrackMac:{}".format(mac, trackMac, logCountTrackMac))
		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			U.logger.log(20, "mac:{} New?  checking if Beacon is back " .format(mac))
		if False and mac in findMAC: U.logger.log(20,"mac{} checkIfBeaconIsBack start".format(mac))

		if  mac not in beacon_ExistingHistory: return False

		if  len(beacon_ExistingHistory[mac]["timeSt"]) == 0 or mac not in beaconLastMessageTS:
			if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				U.logger.log(20,"mac{} checkIfBeaconIsBack empty history".format(mac))
			if mac in findMAC: U.logger.log(20,"mac{} checkIfBeaconIsBack empty history".format(mac))
			return False

		if not beacon_ExistingHistory[mac]["fastDown"]:

			if mac in beaconLastMessageSendTS and tryDeltaTime(beaconLastMessageSendTS[mac]) < sendAfterSecsOfLastMsg:
				if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
					U.logger.log(20, "mac:{} ==> no DT:{}  send " .format(mac, tryDeltaTime(beaconLastMessageSendTS[mac])))
				return False

		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			U.logger.log(20, "mac:{} first test dt: {} , FD:{}".format(mac, tryDeltaTime(beaconLastMessageTS[mac]), beacon_ExistingHistory[mac]["fastDown"]) )

		nTimeStamp = len(beacon_ExistingHistory[mac]["timeSt"])
		if mac == trackMacNumber:
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
			if   (mac == trackMac or trackMac == "*") and logCountTrackMac >0:
				U.logger.log(20, "{} NEW!  beacon is back, send message" .format(mac))
			if mac in findMAC: U.logger.log(20,"mac{} checkIfBeaconIsBack back".format(mac))

			if mac in beacon_ExistingHistory: 
				if mac in fastDownList: 		beacon_ExistingHistory[mac]["trigger"][-1] = 4 # beacon_fastdown is back
				else: 							beacon_ExistingHistory[mac]["trigger"][-1] = 5 # beacon is back
			else:								beacon_ExistingHistory[mac]["trigger"][-1] = 2 # beacon is new
			beacon_ExistingHistory[mac]["fastDown"] = False
			if   (mac == trackMac or trackMac =="*") and logCountTrackMac > 0:
				U.logger.log(20, "mac:{} New!!   fastdown back =========, dt:{:.0f} hist: {:}, count:{}, reason:{}".format(mac, tryDeltaTime(beacon_ExistingHistory[mac]["timeSt"][0]), beacon_ExistingHistory[mac]["timeSt"] , beacon_ExistingHistory[mac]["count"] ,beacon_ExistingHistory[mac]["trigger"][-1] ))
			composeMSGForThisMacOnly(mac)
			return True

	except Exception :
		U.logger.log(20,"", exc_info=True)
	return False
		


#################################
def checkIfBLErestart():
	"""Checks for a temp/BLErestart marker file; if present it deletes the file, logs the request and reports that a BLE stack restart was requested.

	Inputs:
	    None.
	Outputs:
	    bool: True if the restart marker file existed (restart requested), else False
	"""
	if os.path.isfile(G.homeDir + "temp/BLErestart") :
		os.remove(G.homeDir + "temp/BLErestart")
		U.logger.log(20," restart of BLE stack requested") 
		return True
	return False



#################################
def doFastSwitchBotPress(mac, trigOnOff):
	"""Triggers a fast SwitchBot press reaction for a beacon: validates the MAC is configured and not debounced, checks the trigger value matches, writes the SwitchBot command to a temp file, then either runs it locally or transfers it via sftp/pexpect to the remote SwitchBot Raspberry Pi.

	Inputs:
	    mac (str): Beacon MAC address whose fast-reaction config is looked up
	    trigOnOff (str): Trigger state string matched against the configured sensorTriggerValue
	Outputs:
	    None: writes a command file and optionally sends it over sftp; logs progress and exceptions
	"""
	try:

		"""
		fastBLEReaction::fastBLEReaction:{"B8:7C:6F:1A:D9:65"": 
			{'cmd': {'pulseLengthOn': '0', 'repeat': '2', 'pulseLengthOff': '0.0', 'cmd': 'pulses', 'repeatDelay': '0', 'mac': 'F9:A6:49:9A:DF:85', 'pulses': '1', 'mode': 'batch', 'pulseDelay': '0.0', 'outputDev': 1323447574," 'sensorTriggerValue': 'on/off/counter'}, 'indigoIdOfSwitchbot': 1323447574, 'pwdOfSwitchbotRPI': 'karl123.',
			 'IdOfSwitchbotRPI': 'pi', 'pi': '12', 'IPOfSwitchbotRPI': '192.168.1.35'}}
		"""
		#U.logger.log(20,"mac:{}, trigOnOff:{}, fastBLEReaction:{}".format(mac, trigOnOff, fastBLEReaction)) 
		if mac not in fastBLEReaction: return 
		if mac in fastBLEReactionLastAction and tryDeltaTime(fastBLEReactionLastAction[mac]) < 2: return 
		fastBLEReactionLastAction[mac] = time.time()

		IPOfSwitchbotRPI 	= fastBLEReaction[mac].get("IPOfSwitchbotRPI","")
		IdOfSwitchbotRPI	= fastBLEReaction[mac].get("IdOfSwitchbotRPI","")
		pwdOfSwitchbotRPI 	= fastBLEReaction[mac].get("pwdOfSwitchbotRPI","")
		swbotcmd 			= fastBLEReaction[mac]["cmd"]
		fileName			= swbotcmd.get("fileName","switchbot.cmd")
		sensorTriggerValue 	= swbotcmd.get("sensorTriggerValue","on")
		if trigOnOff.find(sensorTriggerValue) == -1:
			#U.logger.log(20,"mac:{}, rejected due to trigOnOff:{}!={}:sensorTriggerValue ".format(mac, trigOnOff, sensorTriggerValue)) 
			return 

		# local action:
		#swbotcmd = '{{"mac":"{}","cmd":"onOff","onOff":1,"mode":"batch","source":"doFastSwitchBotPress"}}'.format(macOfSwitchbot)
		#cmd = '{{"mac":"{}","pulses":1,"pulseLengthOn":2,"pulseLengthOff":2,"source":"doFastSwitchBotPress"}}'.format(switchBotMAC)
		U.logger.log(20,"switchbot input ip# from:{}, to:{}; command: {}".format(G.ipAddress, IPOfSwitchbotRPI, swbotcmd) )
		if IPOfSwitchbotRPI == G.ipAddress: fName = "{}temp/{}".format(G.homeDir,fileName)
		else:								fName = "{}temp/temp1".format(G.homeDir)

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
			expC.sendline("put /home/pi/pibeacon/temp/temp1 /home/pi/pibeacon/temp/"+fileName)
			ret = expC.expect(["/home/pi/pibeacon/temp/"+fileName,pexpect.TIMEOUT], timeout=10)
			U.logger.log(20,"ret4:{}".format(ret) )
			if ret == 0:
				U.logger.log(20,"file send to {} ".format(IPOfSwitchbotRPI)) 
				expC.sendline("quit")
				return 

			expC.sendline("quit")
			U.logger.log(20,"... failed: {}-{}".format(expC.before,expC.after))
			return 
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 



#################################
#################################
######## BLE SENSORS ############
#################################
######################import bluetooth._bluetooth###########
def doSensors( mac, macplain, macplainReverse, rx, tx, hexData):
	"""Dispatches a BLE sensor reading to the correct decoder: if the MAC is a known BLE sensor, it matches the configured sensor type and calls the matching do<SensorType> parser (Ruuvi, SwitchBot, Xiaomi, Govee, Shelly, etc.) returning its result.

	Inputs:
	    mac (str): Beacon MAC address used to look up the sensor config
	    macplain (str): MAC without separators, passed to sensor decoders
	    macplainReverse (str): Byte-reversed plain MAC, passed to sensor decoders
	    rx (str): Received raw advertisement data passed to decoders
	    tx (str): Transmit/txPower data passed through to decoders
	    hexData (str): Hex-encoded advertisement payload to decode
	Outputs:
	    tuple: Result of the matched sensor decoder, or ("", tx, "") if MAC is unknown or no type matches
	"""
	bl = ""
	try:

		doPrint 		= mac == "xxB0:E9:FE:D2:0D:73"
		if doPrint:	
			U.logger.log(20,"mac:{}; checking  in BLEsensorMACs:{}\n".format(mac, mac in BLEsensorMACs)) 
			
		if mac not in BLEsensorMACs:
			return "", tx, bl

 

		if "sensor" in BLEsensorMACs[mac]:
			if doPrint:
				U.logger.log(20,"mac:{}; sensor:{}\n".format(mac, BLEsensorMACs[mac]["sensor"])) 

			sensor = BLEsensorMACs[mac]["sensor"]
			if sensor == "BLEmyBLUEt":  								
				return  domyBlueT( mac, rx, tx, hexData, sensor)


			if sensor.find("BLEiTrackButton") >-1:
				return  doBLEiTrack( mac, macplain, macplainReverse, rx, tx, hexData, sensor)


			if sensor == "BLEThermopro":
				return   doThermopro( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor == "BLETempspike":
				return   doTempspike( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor in ("BLERuuviTag", "BLERuuviAir"):		# ONE combined entry - dispatches on the data-format byte (05/06/E1)
				return   doRuuvi( mac, rx, tx, hexData, sensor)

			if sensor == "BLEKKMsensor":
				return  doBLEKKMsensor( mac, rx, tx, hexData, sensor)

			if sensor.find("BLEiBS") > -1:
				return   doBLEiBSxx( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEminew") > -1:
				return   doBLEminew( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("iSensor") > -1:
				return   doBLEiSensor( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLESatech") > -1:
				return   doBLESatech( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEapril") > -1:
				return   doBLEapril( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEswitchbotTempHumCO2") > -1:
				return   doBLEswitchbotTempHumCO2( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEswitchbotTempHum") > -1:
				return   doBLEswitchbotTempHum( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor in ["BLEswitchbotContact","BLEswitchbotMotion","BLEswitchbotMMWaveMotion", "BLEswitchbotHumidifierEvap"]:
				return   doBLEswitchbotSensor( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEXiaomiMiTempHumRound") > -1:
				return   doBLEXiaomiMi( mac, macplain, macplainReverse, rx, tx, hexData, sensor)

			if sensor.find("BLEXiaomiMiTempHumRound") > -1:
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


	except Exception :
		U.logger.log(20,"", exc_info=True)
	return "", tx, bl

#################################


#################################
def doBLEHunterNodeBT(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parser stub for the BLEHunter Node BT beacon: trims the leading header bytes of the advertisement and checks for the '121107' service marker, but the actual value extraction is commented out so it currently does nothing beyond validation and returns unchanged values.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key
	Outputs:
	    tuple: (sensor, tx, batteryLevel-string) tuple, with battery string empty in this stub
	"""


	# complete package 
	#			         00 8A   01 64   05 EC C2 00    2D 01   3F 01 00    C8
	bl = ""
	try:
		if False and mac in findMAC: doPrint = True 
		else: doPrint = False
		if len(hexData) < 20: return sensor, tx,  bl
		
		hexData = hexData[12:]
		if hexData.find("121107") == -1: return sensor, tx,  bl
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

	except Exception :
		U.logger.log(20,"", exc_info=True)

	return sensor, tx, bl	


#################################
def doBLEShelly(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parses a Shelly BTHome-v2 BLE advertisement (service FCD2): walks the tag/value byte stream using shellyTagToProperty mapping, decoding char/int/intLR/sint fields into named values (battery, temperature, button, rotation, etc.), determines a trigger string from changed values or elapsed time, and if anything triggers, sends the data dict to Indigo via checkIfDelaySend and stores last values.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key
	Outputs:
	    tuple: (sensor, tx, batteryLevel) tuple; battery level (or empty string) of the last decoded packet
	"""
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
						itemsValues[tag["name"]] = round(itemsValues[tag["name"]], roundvalue)

					elif tag["typeFinal"].find("int") == 0:
						itemsValues[tag["name"]] = int(itemsValues[tag["name"]])

					trigValue[tag["name"]] =  tag["trigValue"]
					jj =  ii + nn 
					continue

			if  tag["type"] == "intLR":
					itemsValues[tag["name"]] = intFrom8(data[ii+2:],0)
					if data[ii:ii+2] == "02": itemsValues[tag["name"]] = -itemsValues[tag["name"]]

					if tag["factor"] != 1: itemsValues[tag["name"]]  = itemsValues[tag["name"]] * tag["factor"] 

					trigValue[tag["name"]] =  tag["trigValue"]
					jj =  ii + nn 
					continue


			if  tag["type"] == "sint":
					itemsValues[tag["name"]] = signedintfromhexR(data[ii:], tag["bytes"])

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

	except Exception :
		U.logger.log(20,"", exc_info=True)

	return sensor, tx,  ""	



def doBLEswitchbotSensor(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parses SwitchBot motion/contact/humidifier BLE advertisements: classifies the packet into a device subtype from the FF/16 manufacturer data and length, lazily loads/initializes per-MAC state in switchbotData, and decodes motion, brightness, open/close, button and humidifier fields. The shown portion sets up persistent per-device state before the decoding logic.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key
	Outputs:
	    tuple: (sensor, tx, value) tuple; value/battery string, empty when MAC absent or subtype unmatched
	"""
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

		type11
			mm Wave detect        MAC========= count FL sec
			13 02 0106 0F  FF6909 B0E9FEA45882 08 8C 00 C700 88
			01 23 4567 89  112345 678921234567 89 31 23  45
			                 0123 456789112345 67 89 21  23
			                                   01 23 456789112345 67 8 9 2123


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
											  pp 				0-1	int(w,16)                 = 0-255  any change message counter 
											     WW				2	int(w,16)  RAyz=  R =1xxx = 10 secs after boot stays ?? until ?? powersave ..?, some times just switches
											     WW				2	int(w,16)  0A00 , A= x1xx = 1=bright, 0=dim    
											     WW				2	int(w,16)  b0yz=  y= xx10 = left open
											     WW				2	int(w,16)  b0yz=  z= xx01 = open
											     WW				2	int(w,16)  b0yz=  z= xx00 = close
										  		  H 				3	int("H"")                 = ??  1100  ???   using  last 2 bits for operflow for ssss or tttt
												    ssss:		    4-7	int("ssss",16)            = secs since ??? restarts once at battery start, or device soft restart = when type4 ssss hight bit is  0-> 1
													      tttt :	8-11int("tttt",16)&0b00000000 = 0-2**16-1 secs since last open/close/left open  
														        o:	12	int("o",16)&0b1100        =  abxx  ab changes when opened 
														        C:	13	int("b",16)&0b0011        = 01 -> 10 -> 11 -> 01 for press button
			14 020106 10 FF6909 C9D180A1AA9C  5B 0C 06 A1 06 87 1E   
								MAC#-------- 
	msg1-- 2 b   1  2 
	msg2-- 16 b          1 2 3  4 5 6 7 8 9   1  2  3  4  5  6
			01 234567 89 112345 678921234567  89 31 23 45 67 89 41   
                                              01 23 45 67 89 11 23


	humidity evaporator
		   							0  1  2  3	4  5   6  	7    8  9  10    11	  12 13 14 15 	16 	
					ff pos  01 23 	45 67 89 11 23 45  67 	89 	21 	23 45 	 67	  89 31	23 45   67 
					datapos                            01   23 	45  67 89    11   23 45 67 89 	21
	pos:01 23 45 67 89   11 23 45   67 89 21 23 45 67  89 	31	23 	45 67    89   41 23 45 67 	89  
 		18 02 01 06 14   FF 69 09   D0 EF 76 6E FC 5E  0A 	83  80 	7F FF    F2	  10 02 00 02 	3C 
 		                 id -----
 									rmac-------------  |
													   seqNr
													      	|  hum mode: 			HumidifierMode(dataFF[7] & 0b00001111)
															  	|  over_humidify_protection = bool(dataFF[8] & 0b10000000) 
															  	|  child_lock 				= bool(dataFF[8] & 0b00100000)
															  	|  tank_removed 			= bool(dataFF[8] & 0b00000100)
															  	|  tilted_alert 			= bool(dataFF[8] & 0b00000010)
															  	|  filter_missing 			= bool(dataFF[8] & 0b00000001)
																   	|  is_meter_binded 		= bool(dataFF[9] & 0b10000000)
	
																   	|	humidity = data[9] & 0b01111111
																		if humidity > 100:
																			return None, None, None
																	
																		_temp_sign = 1 if data[10] & 0b10000000 else -1
																		_temp_c = _temp_sign * ((data[10] & 0b01111111) + ((data[11] >> 4) / 10))
   																	         | water_level = HumidifierWaterLevel(dataFF[11] & 0b00000011).name.lower()
																					|  filter_run_time = datetime.timedelta(hours=int.from_bytes(dataFF[12:14], byteorder="big") & 0xFFF)

																				    			  | target_humidity = dataFF[16] & 0b01111111



		"""
		
		
		doPrint 	= False # debug: mac in ["FC:D9:E2:5D:01:30"]
		Verbose		= False
		
		dataFF = parsedData[mac]["analyzed"]["code"].get("FF","")
		data16 = parsedData[mac]["analyzed"]["code"].get("16","")


		#   025-12-03-19:47:52 beaconloop        doBLEswitchbotSensor   L:2108 Lv:20 mac:D0:EF:76:6F:18:96, sens:BLEswitchbotHumidifierEvap; dType:0; 
		# dataFF:  6909 D0EF766F1896 938788AD95121015001532, 
		# data:96186F76EF D01802010614FF69 09D0 EF766F1896 938788AD95121015001532A4 



		if   "6909"+macplain 			in  dataFF 		and len(dataFF) == 13*2: 	dType = 1  # for motion sensor
		elif "6909"+macplain 			in  dataFF 		and len(dataFF) == 14*2: 	dType = 11  # for motion sensor mm wave
		elif "6909"+macplain			in  dataFF      and len(dataFF) == 19*2:	dType = 9  # for evap humiditifier
		elif "3DFD64"					in  data16:  								dType = 3  # for contact sensor
		elif "6909"+macplain 			in  dataFF 		and len(dataFF) == 15*2:	dType = 4  # for contact sensor
		elif "3DFD00"					in  data16:  								dType = 31  # for motion sensor mm wave
		else:													    				dType = 0

		if  doPrint: U.logger.log(20, "mac:{}, dType:{}; len ff:{} 16:{}".format(mac, dType, len(dataFF), len(data16) ))

		motionDuration	= -1
		batteryLevel	= ""
		lastMotion		= -1
		dontknow		= 0
		counter			= 0
		light			= 0
		buttonCounter	= 0
		secSinceLastOff	= 0
		offEvent		= 0
		onState			= 0
		offState		= 0
		closeInd		= 0
		trigType		= ""
		

		if switchbotData == {}:
			jData, raw  = U.readJson("{}temp/switchbot.data".format(G.homeDir))
			if len(raw) > 10:
				switchbotData = jData

		if mac not in initSensor:
			if mac not in switchbotData:
				switchbotData[mac] = {}		
			switchbotData[mac]["init0"]				= False
			switchbotData[mac]["init1"]				= False
			switchbotData[mac]["init2"]				= False
			switchbotData[mac]["init3"]				= False
			switchbotData[mac]["init4"]				= False
	
			switchbotData[mac]["onOffState3"]		= None
			switchbotData[mac]["status4"]			= False
			switchbotData[mac]["onOff"]				= ""
			switchbotData[mac]["brightness"] 		= "dim"
			switchbotData[mac]["BlindicatorBit"]	= -1
			switchbotData[mac]["openCounter"]		= -1
			switchbotData[mac]["resetCounter"]		= -1
			switchbotData[mac]["closed"]			= -1
			switchbotData[mac]["openCloseInd"]		= -1
			switchbotData[mac]["shortOpen"]			= -1
			switchbotData[mac]["sensitivity"] 		= ""
			switchbotData[mac]["batteryLevel"] 		= ""
			switchbotData[mac]["light"]				= ""
			switchbotData[mac]["closeInd"] 			= None
			switchbotData[mac]["counter"] 			= -1
			switchbotData[mac]["buttonCounter"]		= ""
			switchbotData[mac]["buttonCounter3"]	= ""
		
			switchbotData[mac]["offEvent"] 			= 0
			switchbotData[mac]["onState"] 			= None
			switchbotData[mac]["offState"] 			= None
			switchbotData[mac]["secSinceLastOff"]	= -1
			switchbotData[mac]["onOffState3"]		= None
			switchbotData[mac]["status4"]			= False
			switchbotData[mac]["last4"]				= 0
			switchbotData[mac]["last3"]				= 0
			switchbotData[mac]["last2"]				= 0
			switchbotData[mac]["last1"]				= 0
			switchbotData[mac]["lastChange3"]		= time.time()	
			switchbotData[mac]["lastChange"] 		= time.time()

			switchbotData[mac]["temp"] 				= 0
			switchbotData[mac]["hum"] 				= 0
			switchbotData[mac]["humMode"] 			= 0
			switchbotData[mac]["overHumidifyProtection"] = 0
			switchbotData[mac]["childLock"] 		= 0
			switchbotData[mac]["tankRemoved"] 		= 0
			switchbotData[mac]["tiltedAlert"] 		= 0
			switchbotData[mac]["filterMissing"] 	= 0
			switchbotData[mac]["meterBound"] 		= 0
			switchbotData[mac]["hum"] 				= 0
			switchbotData[mac]["temp"] 				= 0
			switchbotData[mac]["waterLevel"] 		= 0
			switchbotData[mac]["filterRunTime"] 	= 0
			switchbotData[mac]["targetHumidity"] 	= 0
			switchbotData[mac]["lastUpdate"] 		= 0
			switchbotData[mac]["lightLevel"]		= 0

		initSensor[mac] = True

		if False and dType == 0: 
			if  doPrint or not switchbotData[mac]["init1"]:		 U.logger.log(20, "mac:{}, sens:{}; dType:{}; len:{}; 9609:{}, first16:{}; dataFF:{}, data:{} ".format(mac, sensor, dType , len(dataFF),  "6909"+macplainReverse	in  dataFF, dataFF[0:16], dataFF, hexData))
			switchbotData[mac]["init0"]				= True
			return sensor, tx,  ""

		## motion Sensor
		if dType == 11:
			hData 		    = dataFF[16:]
			pr = ""
			ll = len(hData)
			for ii in range(0,ll,2):
				pr += hData[ii:ii+2]+" "
				
			counter 		= int(hData[0:2],16)
			flag	  		= int(hData[2:4],16)
			occupied		= (flag & 0b01000000) !=0
			stateChange		= int(hData[4:8],16) + ((int(hData[3],16)&0b0001) * 65536)
			rest1			= int(hData[8:10],16) 
			rest2			= int(hData[10:11],16) 
			lightLevel 		= int(hData[11:12],16) 
			#if  doPrint:	 U.logger.log(20, "mac:{}, pr:{} counter:{:6d},  flag:{:8b}   occupied:{:1}, stateChange:{:8d}, rest:{:8}, {:8b}, light:{:3d}".format(mac, pr, counter, flag,  occupied, stateChange , rest1, rest2, light))
			lastPresenceChange = ""
			trig = ""
			if time.time() - switchbotData[mac]["lastUpdate"] > 90: trig = "time"
			if occupied:
				if not switchbotData[mac]["onState"]:
					lastPresenceChange = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
					trig = "occupied"
			else:
				if switchbotData[mac]["onState"]:
					lastPresenceChange = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
					trig = "unoccupied"
					
			switchbotData[mac]["onState"] =  occupied
						
			if lightLevel - switchbotData[mac]["lightLevel"] != 0: trig  +=";light"
			
			if trig != "":
				trig = trig.strip(";")	
				dd = {   # the data dict to be send 
							"onOffState": 			occupied,
							"lightLevel": 			lightLevel,
							"trigger": 				trig,
							"mac": 					mac,
							"rssi":					int(rx)
					}
				if lastPresenceChange != "":
					dd["lastPresenceChange"] = 	lastPresenceChange
				if BLEsensorMACs[mac]["batteryLevel"] != "": 
					dd["batteryLevel"]  = BLEsensorMACs[mac]["batteryLevel"]
				# compose complete message
				checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
				if  doPrint:	 U.logger.log(20, "dd:{}".format(dd))
				# remember last values
				switchbotData[mac]["lastUpdate"] 		= time.time()
				switchbotData[mac]["lightLevel"] 		= lightLevel
			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]



		## motion Sensor MM wave
		if dType == 31:
			hData 	    = data16[4:]
			BL	  		= int(hData[4:6],16)& 0b01111111
			BLEsensorMACs[mac]["batteryLevel"] = BL
			return sensor, tx,  BL

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
			if lastMotion > -1: 							dd["lastMotion"] 	 = BLEsensorMACs[mac]["lastMotion"]
			if BLEsensorMACs[mac]["motionDuration"] > -1: 	dd["motionDuration"] = BLEsensorMACs[mac]["motionDuration"]

			if motion:	updateEvery = 9
			else:		updateEvery = 40

			#U.logger.log(20, "mac:{},  light:{}-{:08b}".format(mac, light, flag))


			trig = ""
			if  lastMotion > 0	and abs(lastMotion - BLEsensorMACs[mac]["lastMotion"]) > 1:  			trig += "motion/Force/"
			if light != ""		and light != BLEsensorMACs[mac]["light"]:  								trig += "lightChange/"
			if 						motion  != BLEsensorMACs[mac]["motion"]:							trig += "motion/Force/"
			if	trig == "" 		and	tryDeltaTime(BLEsensorMACs[mac]["lastUpdate"] )  > updateEvery:  	trig += "Time"  	# send min every xx secs
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
			if doPrint or not switchbotData[mac]["init1"]: U.logger.log(20, "mac:{}, 1 trig:{}, updateEvery:{}, lastMotion:{}, dd:{}".format(mac, trig, updateEvery, lastMotion, dd ))

			switchbotData[mac]["init1"]	 = True		
			switchbotData[mac]["last1"] = time.time()
				
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
			BLEsensorMACs[mac]["batteryLevel"] = BL
			switchbotData[mac]["brightness"] = "bright" if bright else "dim"
			if mediumS: 	switchbotData[mac]["sensitivity"]  = "long"
			elif shortS:	switchbotData[mac]["sensitivity"]  = "medium"
			else:			switchbotData[mac]["sensitivity"]  = "long"
			switchbotData[mac]["secsSinceLastEvent"] = secsSinceLastEvent
			BLEsensorMACs[mac]["secsSinceLastEvent"] = secsSinceLastEvent
			if doPrint or not switchbotData[mac]["init2"]: U.logger.log(20, "mac:{} 2 bat:{}-hex:{}, secsSinceLastEvent:{}-hex:{}, flags:{}-{:b}".format(mac, BL, hData2, secsSinceLastEvent, hData1, hData3, flags))
			switchbotData[mac]["init2"]	 = True		
			switchbotData[mac]["last2"] = time.time()

			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		


		## contact sensor

		############ type 3 ##################
		## for type 3/4 get most of the info from type3, then send out package
		if dType == 3:								#01 2 3 4567 8901 2 3 pos
			hData				= data16[8:]
			BL					= int(hData[0:2],16)&0b01111111
			BlindicatorBit		= int(hData[0:2],16)&0b10000000 == 0b10000000
			onState				= int(hData[3],16)&0b00000110 == 0b00000000
			shortOpen 			= int(hData[3],16)&0b00000110 == 0b00000010
			longOpen 			= int(hData[3],16)&0b00000110 == 0b00000100
			light 				= "bright" if int(hData[3],16)&0b00000001 == 1 else "dim"
			resetCounter 		= int(hData[4:8],16)
			openCounter 		= int(hData[8:12],16)
			openInd				= int(hData[12],16)>>2
			buttonCounter		= int(hData[13],16)
			trig = ""

			if onState != switchbotData[mac]["onOffState3"]:
				switchbotData[mac]["lastChange3"] = time.time()
				trig = "onOff3"	

			if buttonCounter != switchbotData[mac]["buttonCounter3"]:
				trig += "button3"	
			
			switchbotData[mac]["buttonCounter3"]	= buttonCounter
			switchbotData[mac]["onOffState3"]		= onState
			switchbotData[mac]["BlindicatorBit"] 	= BlindicatorBit
			BLEsensorMACs[mac]["batteryLevel"] 		= BL
			switchbotData[mac]["batteryLevel"] 		= BL
			
			if trig != "":		
				dd = {   # the data dict to be send 
					"dType":				3, 
					"light": 				light,
					"batteryLevel":			BL,
					"onOffState": 			onState,
					"buttonCounter":		buttonCounter,
					"trigger": 				trig.strip("/"),
					"mac": 					mac,
					"rssi":					int(rx)
					}
				U.sendURL( {"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}}, verbose=Verbose)
				switchbotData[mac]["buttonCounter"] = buttonCounter
				switchbotData[mac]["onState"] = onState
				switchbotData[mac]["offState"] = not onState

			#if trig.find("flag") or trig.find("onOff") or trig.find("cl") or trig.find("button"): trig += "force/"
			if onState != switchbotData[mac]["onState"]: noteq = "!=! "
			else: noteq = ""
			#if  doPrint or not switchbotData[mac]["init3"]: U.logger.log(20, "mac:{}, 3 On:{:1}/{:1} {}sO:{:1}, lO:{:1}, Oi:{:1}; bC:{:2}, oC:{:3}, rC:{:3}, BB:{:1}, bl:{}, trig>{}<".format(mac, onState, switchbotData[mac]["onOffState3"], noteq, shortOpen, longOpen, openInd, buttonCounter, openCounter, resetCounter, BlindicatorBit, BL, trig ) )

			switchbotData[mac]["init3"] = True					
			switchbotData[mac]["last3"] = time.time()
				
			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		


		############ type 4 ##################
		if dType == 4:				# is faster than dType 4 sometimes by 4 secs 
			hData = dataFF[16:]     
			
			# is data from dType3 ready?
			if switchbotData[mac]["onOffState3"] is None: return sensor, tx, ""


			#  go through byts and extract meanings
			counter 			= int(hData[0:2],16) 
			secSinceLastEV  	= int(hData[4:8],16) 							# brightness change and on event changes this, can be > 8000
			secSinceLastOff 	= int(hData[8:12],16) 							# can be configured in app to 1 minute ...
			offEvent  			= int(hData[12],16)&0b00001111 					# 0001  0010 0011   0100 1000 1100 
			#shortOff			= offEvent != 0b00000000
			#longOff				= offEvent != 0b00000000
			valid 				= int(hData[2],16)&0b00001010 == 0b00001000		# does not show on bit 
			lightON				= int(hData[2],16)&0b00000100					# 
			closeInd	 		= int(hData[2],16)&0b00000001 == 0b00000000		# 
			light 				= "bright" if lightON == 0b00000100 else "dim"
			byte3		 		= int(hData[3],16)						 		# dont know looks like mostly 1100
			# nibble 13 of a TYPE-4 frame is a 2-bit ROTATING OPEN INDICATOR (01 -> 10 -> 11 -> 01),
			# NOT a button counter - type 4 carries no button counter at all, only type 3 does
			# (int(hData[13],16) there = 1-15 press counter). Reading the whole nibble here and
			# sending it as "buttonCounter" wrote 0/1/4/8/14 into indigo about ten times an hour,
			# each one corrected by the next type-3 frame a second later: two state changes and two
			# triggers per occurrence, with no button ever pressed. It also clobbered the real
			# counter, because both flavors stored into switchbotData[mac]["buttonCounter"].
			openInd4			= int(hData[13],16)&0b0011
			trigType 			= " "
			trig	 			= " "

			## init past from dType3 
			if not switchbotData[mac]["init3"]:
				return sensor, tx,  ""

			if not switchbotData[mac]["status4"]:
				onState = switchbotData[mac]["onOffState3"]
				offState = not onState
				if  doPrint: U.logger.log(20, "mac:{}, 4 init onstate with >{}< from dType3 at init ".format(mac, onState) ) 

			#regular process 
			else:
				DT4 = time.time() - switchbotData[mac]["last4"]
				DT3 = time.time() - switchbotData[mac]["last3"]
				if  DT4 > 4:
					# resync from the LAST KNOWN dType3 state - do NOT require it to be
					# < 2 secs fresh: type-3 frames ride scan responses and can be sparse,
					# and the old "else: return" dropped the packet WITHOUT updating
					# last4, so every following type-4 packet hit the same dead gate and
					# contact changes waited 30+ secs for the next type-3 frame.
					# Resyncing from the stored state matches the init branch; the next
					# type-4 packet of the event burst then goes through full processing
					# and fires the trigger within ~1-2 secs.
					onState = switchbotData[mac]["onOffState3"]
					offState = not onState
					if  doPrint: U.logger.log(20, "mac:{}, 4 resync onstate with {} from dType3; last 4 message was {:.1f} secs ago; Dtype 3 was {:.1f} secs ago".format(mac, onState, DT4, DT3) ) 
				
				else:
					onState  =  False
					offState =  False
					onStateTrig = False

					newOffState 	=  (offEvent != switchbotData[mac]["offEvent"] )
	
					onState = False
					onStateTrig = False
	
					if 	True or counter != switchbotData[mac]["counter"]:
	
						if 	offEvent == switchbotData[mac]["offEvent"]:
							if secSinceLastOff < 3 and 	closeInd and valid:
								trigType += "1;"
								onState = True
								if switchbotData[mac]["onState"] != onState:
									onStateTrig = True
	
							elif switchbotData[mac]["onState"]:
								trigType += "2;"
								onState = True
	
						else: # !=
							if offEvent == 0: 
									trigType += "3;"
									onState = False
									offState = True
									onStateTrig = True
									
							elif secSinceLastOff < 2: 
								if not switchbotData[mac]["onState"]:
									trigType += "4;"
									onStateTrig = True
									onState = True
									offState = False
									offEvent = 0
								else:
									trigType += "5;"
									onState = False
									offState = True
									onStateTrig = True
							else:
									trigType += "6;"
									onState = False
									offState = True
									onStateTrig = True
								
		
				
				
					trig = ""
					if onStateTrig:  								trig = "on"
					if offState: 									trig = "off"
					if light != switchbotData[mac]["light"] : 		trig = "light"
		
					if trig == "":
						if time.time() - switchbotData[mac]["lastChange3"] < 2 and switchbotData[mac]["onOffState3"] != onState:
							if  doPrint: U.logger.log(20, "mac:{}, 4 change onstate from >{}<  to >{}<  from dType 3".format(mac, onState, switchbotData[mac]["onOffState3"]) ) 
							onState = switchbotData[mac]["onOffState3"]
							offState = not onState
							if onState: onStateTrig  = True; trig = "on"
							else:		offStateTrig = True; trig = "off"
			
					if time.time() - BLEsensorMACs[mac]["lastUpdate"] > 90: trig += "time"
						
					if trig != "":
						dd = {   # the data dict to be send 
							"dType":				4, 
							"light": 				light,
							"counter": 				counter,
							"onOffState": 			onState,
							"trigger": 				trig.strip("/"),
							"mac": 					mac,
							"rssi":					int(rx)
							}
						if switchbotData[mac]["sensitivity"] != "": dd["sensitivity"] = switchbotData[mac]["sensitivity"]
						if   BLEsensorMACs[mac]["batteryLevel"] != "": dd["batteryLevel"] = BLEsensorMACs[mac]["batteryLevel"]
						elif switchbotData[mac]["batteryLevel"] != "": dd["batteryLevel"] = switchbotData[mac]["batteryLevel"]
						U.sendURL( {"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}}, verbose=Verbose)
						if doPrint: U.logger.log(20, "mac:{} triggers:{}; dd:{} ".format( mac, trig , dd)  )
						# remember last values
						BLEsensorMACs[mac]["lastUpdate"] 		= time.time()
						U.writeFile("temp/switchbot.data", json.dumps(switchbotData))
						
						fastSwitchBotPress = ""
						if onState: 					fastSwitchBotPress += "on"
						if offState: 					fastSwitchBotPress += "off"
						if fastSwitchBotPress != "" : 	doFastSwitchBotPress(mac, fastSwitchBotPress)

			# --- dType 4 tail: persist state, arm status4, return -------------
			# This block MUST stay inside "if dType == 4:".  It was accidentally
			# swallowed by the "if dType == 9:" block when the humidifier section
			# was inserted, so status4/last4 were never set - every type-4 packet
			# ran the init branch as a no-op and contact triggers only came from
			# the rare type-3 frames (30+ secs latency).
			switchbotData[mac]["last4"] 			= time.time()
			switchbotData[mac]["light"] 			= light
			switchbotData[mac]["counter"] 			= counter
			switchbotData[mac]["closeInd"] 			= closeInd
			switchbotData[mac]["secSinceLastOff"]	= secSinceLastOff
			switchbotData[mac]["offEvent"]			= offEvent
			switchbotData[mac]["onState"]			= onState
			switchbotData[mac]["offState"]			= offState

			if onState != switchbotData[mac]["onOffState3"]: noteq = "!=! "
			else: noteq = ""

			if trigType != " ": trigType = trigType.strip().strip(";")
			if switchbotData[mac]["status4"] :
				if False and  doPrint: U.logger.log(20, "mac:{}, 4 On:{:1}/{:1} {}Of:{:1}, oI4:{:1}, CI:{:1}, br:{:} tr>{}-{}< hData= [0:2], i:{:03d}; [2]b:{:04b}; [3]b:{:04b}; [4:8]secsEV:{:5d}; [8:12]secSO:{:3d}; [12]offEV:{:04b}; [13]openInd4:{:4d}; {}".format(mac, onState, switchbotData[mac]["onOffState3"], noteq, offState, openInd4, closeInd,  light[0], trigType, trig, int(hData[0:2],16),  int(hData[2:3],16), int(hData[3:4],16), secSinceLastEV, secSinceLastOff, offEvent, openInd4, hData ) )
			switchbotData[mac]["status4"] = True
			switchbotData[mac]["init4"] = time.time()					

			return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]
				
		############ type 9 hum evap ##################
		if dType == 9:		
			doPrint = False		
			hData = dataFF[16:]   
			
			#  go through bytes and extract meanings
			counter 					= int(hData[0:2],16) 
			humMode 					= ["0","high", "medium","low","quite","target humidity","sleep","auto","drying filter",">8"][min(int(hData[2:4],16) & 0b00001111, 9)]
			overHumidifyProtection 		= int(hData[4:6],16) & 0b10000000 != 0
			childLock 					= int(hData[4:6],16) & 0b00100000 != 0
			tankRemoved 				= int(hData[4:6],16) & 0b00000100 != 0
			tiltedAlert 				= int(hData[4:6],16) & 0b00000010 != 0
			filterMissing 				= int(hData[4:6],16) & 0b00000001 != 0
			meterBound 					= int(hData[6:8],16) & 0b10000000 != 0
			hum 						= int(hData[6:8],16) & 0b01111111 
			tempSign 					= 1. if int(hData[8:10],16) & 0b10000000 !=0 else -1.
			temp1 						= int(hData[8:10],16) & 0b01111111 
			temp2 						= (int(hData[10:12],16) >>4) / 10.
			temp 						= tempSign * (   temp1  + temp2 )
			waterLevel					= ["empty","low", "medium","high","4"][int(hData[10:12],16) & 0b00000011]
			fr1 						= int(hData[12:14],16)<<8 
			fr2							= int(hData[14:16],16) 
			filterRunTime 				= (  fr1 + fr2  ) &  4095
			targetHumidity 				= int(hData[20:22],16) & 0b01111111


			DT = time.time() - switchbotData[mac]["lastChange"] 
		
			trig = ""
	
			if DT > 90:	trig = "time/"
			for xx in ["hum", "temp", "overHumidifyProtection", "childLock", "tankRemoved", "tiltedAlert", "filterMissing", "meterBound", "waterLevel", "filterRunTime", "targetHumidity" ]:
				if eval(xx) != switchbotData[mac][xx]: trig += xx+"/"
				
			if trig != "":
					dd = {   # the data dict to be send 
						"counter":					counter, 
						"humidityMode": 			humMode,
						"overHumidifyProtection": 	overHumidifyProtection,
						"childLock": 				childLock,
						"tankRemoved":				tankRemoved,
						"tiltedAlert":				tiltedAlert,
						"filterMissing":			filterMissing,
						"meterBound":				meterBound,
						"hum":						hum,
						"temp":						temp,
						"waterLevel":				waterLevel,
						"filterRunTime":			filterRunTime,
						"targetHumidity":			targetHumidity,
						"trigger": 					trig.strip("/"),
						"mac": 						mac,
						"rssi":						int(rx)
						}
					U.sendURL( {"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}}, verbose=Verbose)
					if doPrint: U.logger.log(20, "mac:{} (2)  frhex:{}, fr1:{},  fr2:{}; filterRunTime:{},  dd:{} ".format( mac,  hData[12:16], fr1,  fr2, filterRunTime,   dd)  )
					# remember last values
					switchbotData[mac]["lastChange"] 		= time.time()
					
					for xx in ["hum", "temp", "overHumidifyProtection", "childLock", "tankRemoved", "tiltedAlert", "filterMissing", "meterBound", "waterLevel", "filterRunTime", "targetHumidity" ]:
						switchbotData[mac][xx] = eval(xx)
				





	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""




def doBLEswitchbotTempHum(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parses a SwitchBot temperature/humidity meter (model byte '54') from the type-16 service data: decodes battery level, signed temperature and humidity, applies configured offsets, builds a trigger string when temp/hum change beyond thresholds or the update interval elapses, and sends the reading to Indigo via checkIfDelaySend.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key
	Outputs:
	    tuple: (sensor, tx, batteryLevel) tuple; battery int or empty string when unmatched
	"""
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
	pos:                                                                16    01 23 45 67 89 11 23 45 
	old																			          BB tt TT HH 	
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

		doPrint 		= False # mac in findMAC
		#if mac == "A4:C1:38:98:15:CB": doPrint 		= True
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
		if trig == "" and tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: 	trig+= "Time" 			# send min every xx secs
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
					BLEsensorMACs[mac]["temp"]    		= temp
					BLEsensorMACs[mac]["hum"]    		= hum
					BLEsensorMACs[mac]["batteryLevel"]  = batteryLevel
		
		return sensor, tx,  batteryLevel		



	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""





def doBLEswitchbotTempHumCO2(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parses a SwitchBot temperature/humidity/CO2 meter from the FF manufacturer data: decodes a change counter, battery, signed temperature, humidity, CO2 (high+low bytes) and alarm flag bits, applies offsets, builds a trigger string from value changes/counter/elapsed time, and sends the reading to Indigo when triggered.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key
	Outputs:
	    tuple: (sensor, tx, batteryLevel) tuple; battery int or empty string when unmatched
	"""
	try:

		if mac not in parsedData: return sensor, tx,  ""

		"""

===MAC# B0:E9:FE:D2:0D:73  
tag ----------        msg-Type : raw data: preamble->   [-- mac # ------] dat ll   1  2  3  4  5  6  7    8 910111213   14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 .. RSSI
																													    30 64 00 96 58 02 08 02 B8 00
																							     69 09   B0E9FED20D73   24 64 05 94 2F 00 08 02 B2 00						
other                   Nmsg: 9: 04 3E 23 02 01 00 00   73 0D D2 FE E9 B0     17  02 01 06 13 FF 69 09   B0E9FED20D73   0B 64 05 93 33 00 04 02 6D 00                            BC=-68
																							 swbot---  mac
																													       BB tt TT HH       CC cc
																								 01 23   456789012345   67 89 21 23 45 67 89 31 23	pos					 		   	
                    pos_of_MAC : 8.0
other                   Nmsg: 8: 04 3E 13 02 01 04 00   73 0D D2 FE E9 B0     07  06 16 3D FD 35 00 64                                                                            C5=-59

		"""

		doPrint 		= mac == "xxB0:E9:FE:D2:0D:73"

		dataFF = parsedData[mac]["analyzed"]["code"].get("FF","")
		if dataFF == "" or dataFF == {} or len(dataFF) < 16: return sensor, tx,  ""


		model = ""


		#if model != "0B": return sensor, tx,  ""


		counter = int(dataFF[16:18].encode("utf-8"), 16) # changes if new changed data 

		batteryLevel = int(dataFF[18:20].encode("utf-8"), 16) & 0b01111111

		tempFra = int(dataFF[20:22].encode("utf-8"), 16) / 10.0
		tempInt = int(dataFF[22:24].encode("utf-8"), 16)
		if tempInt < 128:
			tempInt *= -1
			tempFra *= -1
		else:
			tempInt -= 128
		temp = tempInt + tempFra

		hum = int(dataFF[24:26].encode("utf-8"), 16) 

		CO2H = int(dataFF[30:32].encode("utf-8"), 16) * 256
		CO2L = int(dataFF[32:34].encode("utf-8"), 16)
		CO2 = CO2L + CO2H
		flag1 = bin(int(dataFF[26:28],16))[2:].zfill(8)
		flag2 = bin(int(dataFF[28:30],16))[2:].zfill(8)

		flag1 = flag1[0:4] +"-"+flag1[4:]
		flag2 = flag2[0:4] +"-"+flag2[4:]
		alarmBits = flag1+"-"+flag2

		if doPrint: U.logger.log(20, "mac:{}, counter:{}; , alarmBits: {} ,  dataFF:{}".format(mac, counter,alarmBits, dataFF[16:]))
		trig = ""
		if abs(temp - BLEsensorMACs[mac]["temp"]) > 0.5: 													trig+= "temp/" 
		if abs(hum - BLEsensorMACs[mac]["hum"]) > 2: 														trig+= "hum/" 
		if abs(CO2 - BLEsensorMACs[mac]["CO2"]) > 2: 														trig+= "CO2/" 
		if     counter !=  BLEsensorMACs[mac]["counter"]: 													trig+= "Counter/" 
		if trig == "" and tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: 	trig+= "Time" 			# send min every xx secs
		trig = trig.strip("/")



		if  trig !="":
					dd = {   # the data dict to be send 
						"alarmBits": 	alarmBits,
						"counter": 		counter,
						"temp": 		round(temp+ BLEsensorMACs[mac]["offsetTemp"],1),
						"hum": 			int(hum + BLEsensorMACs[mac]["offsetHum"]),
						"CO2": 			int(CO2 + BLEsensorMACs[mac]["offsetCO2"]),
						"batteryLevel": batteryLevel,
						"mac": 			mac,
						"trigger": 		trig,
						"rssi":			int(rx)
					}
					# compose complete message
					checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
					# remember last values
					if  doPrint: U.logger.log(20, "mac:{} trig:{}; updateIndigoTiming:{}; send:{}".format( mac, trig,BLEsensorMACs[mac]["updateIndigoTiming"] ,  dd)  )
					BLEsensorMACs[mac]["counter"] 		= counter
					BLEsensorMACs[mac]["lastUpdate"] 	= time.time()
					BLEsensorMACs[mac]["temp"]    		= temp
					BLEsensorMACs[mac]["hum"]    		= hum
					BLEsensorMACs[mac]["CO2"]    		= CO2
					BLEsensorMACs[mac]["batteryLevel"]  = batteryLevel
					if doPrint: U.logger.log(20, "mac:{}, dd:{}<<".format(mac, dd))
		
		return sensor, tx,  batteryLevel		



	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""



def doBLEBLEblueradio(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parses a BlueRadios SensorBug BLE advertisement: after matching the manufacturer tag, reads battery and config counter, then iterates over variable-length type tags (41=accel/open-close, 42=light/lux with range+resolution scaling, 43=temperature) to extract onOff, illuminance and temperature, builds a trigger string from changes/elapsed time, and sends the reading to Indigo when triggered.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key
	Outputs:
	    tuple: (sensor, tx, batteryLevel) tuple; battery int or empty string when unmatched
	"""
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
		if doPrint: U.logger.log(20, "mac:{}, sensor:{} dataFF:{}, tag1:{}".format(mac, sensor,  dataFF, dataFF.find("FF85000200")))

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
				resInd		= max(0,min(3,(testNumber   & 0b00110000) >>4 )) 
				if dataLen == 2:
					Illuminance = round(int(dataFF[p+6:p+8] + dataFF[p+4:p+6],16 ) * rangeV[rangeInd] / resolutionMaxV[resInd],1)
					p += 8		
					sensorSetup["Light"] = "range={}k,{}b".format(rangeText[rangeInd],resolutionBits[resInd])
				elif dataLen == 1:
					Illuminance = round(int(dataFF[p+4:p+6],16) * rangeV[rangeInd] / resolutionMaxV[resInd],1)
					sensorSetup["Light"] = "range={}k,{}b;".format(rangeText[rangeInd],resolutionBits[resInd])
					p += 6		
				if doPrint: U.logger.log(20, "mac:{}, sens:{}; Illuminance:{},  dataLen:{}, rangeInd:{}, range:{}, resInd:{} res:{}, testHEX:{},testbin:{:6b} testNumber:{}, rangeX:{}, resX:{}, dataFF:{}".format(mac, sensor, Illuminance, dataLen, rangeInd, rangeV[rangeInd] ,resInd,resolutionMaxV[resInd], testHEX,testNumber, testNumber, testNumber & 0b00001100, testNumber & 0b00110000 , dataFF[p:p+8]))

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
		if trig == "" and tryDeltaTime(BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: 			trig += "Time"  			# send min every xx secs
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
					if doPrint: U.logger.log(20, "mac:{} triggers: {}, updateIndigoTiming:{}; send:{}".format( mac, trig, BLEsensorMACs[mac]["updateIndigoTiming"] ,  dd)  )
					BLEsensorMACs[mac]["lastUpdate"]	= time.time()
					BLEsensorMACs[mac]["temp"]			= temp
					BLEsensorMACs[mac]["Illuminance"]	= Illuminance
					BLEsensorMACs[mac]["onOff"]			= onOff
					BLEsensorMACs[mac]["batteryLevel"]	= batteryLevel

		
		return sensor, tx,  batteryLevel		



	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""

#################################


def doBLEgoveeTempHum(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parses Govee temperature/humidity beacons (e.g. GVH5075/5177): identifies one of three packet layouts by manufacturer-data id and length, decodes the packed 3-byte temperature/humidity value (or 2+2+1 layout) and battery level, applies offsets, builds a trigger string from changes/elapsed time, and sends the reading to Indigo when triggered.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key
	Outputs:
	    tuple: (sensor, tx, batteryLevel) tuple; battery int or empty string when unmatched
	"""
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
			hum			 =  min(100,max(0,float(int(hData[4:6],16)<<8 + int(hData[6:8],16)) /100. + 0.5))
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
		if trig == "" and  tryDeltaTime(BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: 	trig += "Time" 			# send min every xx secs
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
					BLEsensorMACs[mac]["lastUpdate"] = time.time()
					BLEsensorMACs[mac]["temp"]    	 = temp
					BLEsensorMACs[mac]["hum"]    	 = hum
					BLEsensorMACs[mac]["batteryLevel"] = batteryLevel
		
		return sensor, tx,  batteryLevel		



	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""

#################################

def doBLEXiaomiMi(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parses Xiaomi Mi (MiJia) BLE sensors from the type-16 service data: matches the device id/type (round LYWSDCGQ, clock LYWSD02, or MJHFD formaldehyde), then by tag decodes temperature, humidity, combined temp+hum, formaldehyde or battery, smoothing temp/hum through tralingAv averaging, and (in the truncated tail) builds the data dict to send to Indigo.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key, used to select round/clock/formaldehyde variant
	Outputs:
	    tuple: (sensor, tx, batteryLevel) tuple; battery value or empty string when unmatched
	"""
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

		MJHFD1_0010FC formaldehyd T H formA mg/m**3

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
		#													ID-tag		sensTypeTag		counter
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
		if trig == "" and  tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"] )  > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"  			# send min every xx secs
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
					BLEsensorMACs[mac]["hum"]			= hum
					BLEsensorMACs[mac]["Formaldehyde"]	= Formaldehyde
		
		return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		



	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""

#################################


#################################
def doTempspike(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parses a MeatStick/TempSpike (TP3...) BLE beacon: matches the 'TP3' name tag in service-08 data, decodes signed temperature and humidity from the FF manufacturer data plus a coarse battery level from a nibble, applies offsets, builds a trigger string from changes/elapsed time, and sends the reading to Indigo when triggered.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key
	Outputs:
	    tuple: (sensor, tx, batteryLevel) tuple; stored battery level or empty string when unmatched
	"""
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
		else:				BL = 0
		dd["batteryLevel"]	= BL

		dd["mac"] =	mac
		if temp > -100: 											dd["temp"] 			= round(temp+ BLEsensorMACs[mac]["offsetTemp"],1)
		if hum > -100: 												dd["hum"]			= int(hum + BLEsensorMACs[mac]["offsetHum"])
		if rx > -101: 												dd["rssi"]			= int(rx)

		trig = ""
		if abs(temp - BLEsensorMACs[mac]["temp"]) 			> 0.5:  											trig += "temp/"
		if abs(hum - BLEsensorMACs[mac]["hum"]) 			> 2:  												trig += "hum/"
		if BL !=  BLEsensorMACs[mac]["batteryLevel"] :  														trig += "bat/"
		if trig == "" and  tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"]) > BLEsensorMACs[mac]["updateIndigoTiming"]:  		trig += "Time"			# send min every xx secs
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
					BLEsensorMACs[mac]["hum"]			= hum
		
		return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		



	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""


#################################
def doThermopro(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parses a ThermoPro (TP3... tagged) BLE beacon, near-identical to doTempspike: matches the 'TP3' name in service-08 data, decodes signed temperature, humidity and a coarse battery level from the FF manufacturer data, applies offsets, builds a trigger string from changes/elapsed time, and sends the reading to Indigo when triggered.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key
	Outputs:
	    tuple: (sensor, tx, batteryLevel) tuple; stored battery level or empty string when unmatched
	"""
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


		val = int(dataFF[2:4],16) + int(dataFF[4:6],16)*256
		if val > 32767: val -= 65536
		temp = round(val / 10.,1) 

		hum = int(dataFF[6:8],16)

		xx = dataFF[9:10]
		if xx == "2":  		BL = 100
		elif xx == "1":  	BL = 50
		elif xx == "0":  	BL = 10
		else:				BL = 0
		dd["batteryLevel"]	= BL

		dd["mac"] =	mac
		if temp > -100: 											dd["temp"] 			= round(temp+ BLEsensorMACs[mac]["offsetTemp"],1)
		if hum > -100: 												dd["hum"]			= int(hum + BLEsensorMACs[mac]["offsetHum"])
		if rx > -101: 												dd["rssi"]			= int(rx)

		trig = ""
		if abs(temp - BLEsensorMACs[mac]["temp"]) 			> 0.5:  											trig += "temp/"
		if abs(hum - BLEsensorMACs[mac]["hum"]) 			> 2:  												trig += "hum/"
		if BL !=  BLEsensorMACs[mac]["batteryLevel"] :  														trig += "bat/"
		if trig == "" and  tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"]) > BLEsensorMACs[mac]["updateIndigoTiming"]:  		trig += "Time"			# send min every xx secs
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
					BLEsensorMACs[mac]["hum"]			= hum
		
		return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		



	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""


#################################
def doBLEthermoBeacon(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Parses a ThermoBeacon BLE advertisement: matches the '11' type tag and the fixed 40-char short-packet length, decodes button-pressed state, battery voltage, temperature (/16), humidity (/16) and an uptime counter, converts voltage to a battery level via batLevelTempCorrection, builds a trigger string from changes/elapsed time, and sends the reading to Indigo when triggered.

	Inputs:
	    mac (str): colon-formatted MAC address of the beacon
	    macplain (str): MAC address without separators
	    macplainReverse (str): byte-reversed plain MAC address
	    rx (int): received signal strength (RSSI)
	    tx (int): transmit power / pass-through value
	    hexData (str): raw advertisement payload as a hex string
	    sensor (str): sensor type name key
	Outputs:
	    tuple: (sensor, tx, batteryLevel) tuple; stored battery level or empty string when unmatched
	"""
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
		if True:													dd["onOff"]			= buttonPressed 
		if bl >-100:
																	dd["batteryLevel"]	= int(bl)
																	dd["batteryVoltage"]= int(batteryVoltage)
		if rx > -101: 												dd["rssi"]			= int(rx)

		trig = ""
		if trig == "" and  tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])  > BLEsensorMACs[mac]["updateIndigoTiming"]:  trig += "Time/"			# send min every xx secs
		if abs(temp - BLEsensorMACs[mac]["temp"]) 			> 0.5:  											trig += "temp/"
		if abs(hum - BLEsensorMACs[mac]["hum"]) 			> 2:  												trig += "hum/"
		if BLEsensorMACs[mac]["onOff"] != 					buttonPressed:  									trig += "button"
		trig = trig.strip("/")

		if True:													dd["trigger"]			= trig 
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
					BLEsensorMACs[mac]["hum"]			= hum
					BLEsensorMACs[mac]["onOff"]			= buttonPressed
					BLEsensorMACs[mac]["batteryLevel"]  = bl 
					BLEsensorMACs[mac]["batteryVoltage"] = batteryVoltage 
		
		return sensor, tx,  BLEsensorMACs[mac]["batteryLevel"]		



	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""

#################################
def tralingAv(sensor, mac, avType, retVal):
	"""Maintains a trailing/rolling average for a sensor value: appends the new reading to the per-MAC fixed-length list in BLEsensorMACs (dropping the oldest), then averages the entries while skipping placeholder -100 values and excluding the single min and max when more than two valid samples exist.

	Inputs:
	    sensor (str): sensor type name key (unused except logging)
	    mac (str): colon-formatted MAC address used to index BLEsensorMACs
	    avType (str): name of the rolling-average list field (e.g. 'tempAve', 'humAve')
	    retVal (float): new sample value to add to the average
	Outputs:
	    float: trimmed average of recent samples, or the input value if too few valid samples
	"""
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
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return retVal


#################################
def doBLEiSensor(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Decodes KAIPULE/iSensor BLE advertisement manufacturer data (type FF) for either an on/off security sensor or a temperature/humidity sensor, extracting device type, event/alarm bits, counter, temperature and humidity (with configured offsets), and battery low flag, then sends the values to Indigo via checkIfDelaySend when a change or update-interval trigger fires.

	Inputs:
	    mac (str): BLE MAC address key into parsedData/BLEsensorMACs
	    macplain (str): MAC address without separators
	    macplainReverse (str): Byte-reversed plain MAC string
	    rx (str): Received signal strength (RSSI) value
	    tx (str): TX power value, passed through and returned
	    hexData (str): Raw advertisement hex payload
	    sensor (str): Indigo sensor/device-type name
	Outputs:
	    tuple: (sensor, tx, batL) with battery level (10/100 or '') after optionally sending data
	"""



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
		doPrint = mac in findMAC
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

		if  doPrint: U.logger.log(20, " mac:{}  deviceByte:{:08b}=={}, d18L:{},d18:{}, typeID:{}, remote:{}, sensorType:{}, ".format( mac,  deviceByte, deviceByte,  len(dataFF) , dataFF, typeID, remote, sensorType ) )

		if sensorType == "": return sensor, tx,  batL
		


		fastSwitchBotPress = "" 
		dd = {}
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
				if trig == "" and  tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]:		trig += "Time" 			# send min every xx secs
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
					else: 							 fastSwitchBotPress = "off"

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
					else: 							 fastSwitchBotPress = "off"

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
					else: 							 fastSwitchBotPress = "off"

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
					else: 							 fastSwitchBotPress = "off"


		#U.logger.log(20, " .... checking  data:{} counter hex:{}".format( dd , hexData[42:42+5]) )
		if counter != BLEsensorMACs[mac]["counter"]:													 trig += "count/"# send min every xx secs
		if trig == "" and  tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time/"	# send min every xx secs
		if tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])   < 1.5: trig = ""

		for test in ["onOff","tampered", "SOS", "home", "away", "disarm"]:
			if test in dd:
				if test not in BLEsensorMACs[mac]: BLEsensorMACs[mac][test] =  not dd[test]
				if dd[test] != BLEsensorMACs[mac][test]: trig += "force/"
		
		if  doPrint: U.logger.log(20, " mac:{}  trig:{}, send? dd:{};".format(mac, trig, dd))

		trig = trig.strip("/")
		if  trig != "":
			dd["trigger"] = trig
			dd["mac"] = mac   
			# compose complete message
			send = checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
			if doPrint:	U.logger.log(20, " mac:{}  trig:{}, send:{},   dd:{};".format(mac, trig, send, dd))

			#U.logger.log(20,"sensor pressed {}-{} :{}".format(mac,sensor, dd))
			# remember last values
			BLEsensorMACs[mac]["lastUpdate"] = time.time()
			BLEsensorMACs[mac]["counter"]    = counter
			
			for test in ["onOff","tampered", "SOS", "home", "away", "disarm"]:
				if test in dd:
					BLEsensorMACs[mac][test] = dd[test]
			   

			if fastSwitchBotPress != "" : doFastSwitchBotPress(mac, fastSwitchBotPress)

		return sensor, tx, batL

	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  batL


#################################
def doBLEmeeblue(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Decodes meeblue BLE beacon advertisements: on a regular service-data (16) packet it reads battery voltage, computes battery level via batLevelTempCorrection and periodically sends an off/battery status; on a button-press (name 'meeblue') packet within the active window it sends an onOff=True button-press event to Indigo.

	Inputs:
	    mac (str): BLE MAC address key into parsedData/BLEsensorMACs
	    macplain (str): MAC address without separators
	    macplainReverse (str): Byte-reversed plain MAC string
	    rx (str): Received signal strength (RSSI) value
	    tx (str): TX power value, passed through and returned
	    hexData (str): Raw advertisement hex payload
	    sensor (str): Indigo sensor/device-type name
	Outputs:
	    tuple: (sensor, tx, bl) with computed battery level or '' on no-update/error
	"""



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

	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  bl



#################################
def doBLEiBSxx( mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Decodes Ingics iBSxx-family BLE beacon advertisements, identifying the specific sub-type from the format/state bytes and extracting battery voltage/level plus per-type values such as on/off switch bits, temperature, humidity, ambient temperature, or 3-axis acceleration, then builds a data dict and sends it to Indigo when a change or timing trigger fires.

	Inputs:
	    mac (str): BLE MAC address key into parsedData/BLEsensorMACs
	    macplain (str): MAC address without separators
	    macplainReverse (str): Byte-reversed plain MAC string
	    rx (str): Received signal strength (RSSI) value
	    tx (str): TX power value, passed through and returned
	    hexData (str): Raw advertisement hex payload
	    sensor (str): Indigo sensor/device-type name selecting the decode branch
	Outputs:
	    tuple: (sensor, tx, batteryLevel) with decoded battery level or '' on early return
	"""

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
			data[sensor][devId]["onOff1"] = onOff1		# was data[...][devId][sensor]["onOff1"] - that sub-dict does not exist (see the init above), every iBS03G frame raised KeyError

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
			accelerationX 	= signedIntfrom16(hexData[p+2 :p+4 ]+HexStr[p  :p+2 ])*4 # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540
			accelerationY 	= signedIntfrom16(hexData[p+6 :p+8 ]+HexStr[p+4:p+6 ])*4 # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540
			accelerationZ 	= signedIntfrom16(hexData[p+10:p+12]+HexStr[p+8:p+10])*4 # in mN/sec882  this sensor is off by a factor of 2.54!! should be 1000  ~ is 2540
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
		if trig == "" and  tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])  > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"  			# send min every xx secs
		#U.logger.log(20, "mac:{}    HexStr20-23:{}- 24-26{} irOnOff:{}, batteryVoltage:{}".format(mac, HexStr[20:24],  HexStr[24:26], irOnOff, batteryVoltage) )

		#U.logger.log(20, "{}   trigTime:{},  trig:{}, deltaTime:{};  updateIndigoTiming:{}, dada:{}".format(mac, trigTime, trig, deltaTime, BLEsensorMACs[mac]["updateIndigoTiming"], data[sensor][devId]) )
		trig = trig.strip("/")
		if  trig != "":
			data[sensor][devId]["trigger"]  							= trig.strip("/")
			checkIfDelaySend({"sensors":data})
			# save last values to comapre at next round, check if we should send if delta  > paramter
			BLEsensorMACs[mac]["lastUpdate"] 					= time.time()
			BLEsensorMACs[mac]["onOff"] 						= onOff#  = ALL OR JUST BUTTON 
			BLEsensorMACs[mac]["onOff1"] 						= onOff1# == button
			BLEsensorMACs[mac]["onOff2"] 						= moving
			BLEsensorMACs[mac]["onOff3"] 						= hallSensor
			BLEsensorMACs[mac]["onOff4"] 						= freeFall
			BLEsensorMACs[mac]["onOff5"] 						= PIR
			BLEsensorMACs[mac]["onOff6"] 						= IR
			BLEsensorMACs[mac]["temp"] 		 					= temp
			BLEsensorMACs[mac]["hum"] 		 					= hum
			BLEsensorMACs[mac]["AmbientTemperature"] 			= AmbientTemperature
			BLEsensorMACs[mac]["accelerationX"] 				= accelerationX
			BLEsensorMACs[mac]["accelerationY"] 				= accelerationY
			BLEsensorMACs[mac]["accelerationZ"] 				= accelerationZ

			if fastSwitchBotPress != "": doFastSwitchBotPress(mac, fastSwitchBotPress)

		return sensor, tx,  batteryLevel
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return sensor, tx,  ""



#################################
def doBLEiTrack( mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Decodes iTrack BLE tracker advertisements by matching the name (09) and manufacturer (FF) fields, extracting battery level, button-press/connect state and device type, then sends onOff and state-of-beacon data to Indigo when the state changes or the update interval elapses.

	Inputs:
	    mac (str): BLE MAC address key into parsedData/BLEsensorMACs
	    macplain (str): MAC address without separators
	    macplainReverse (str): Byte-reversed plain MAC, validated against the embedded MAC
	    rx (str): Received signal strength (RSSI) value
	    tx (str): TX power value, passed through and returned
	    hexData (str): Raw advertisement hex payload
	    sensor (str): Indigo sensor/device-type name
	Outputs:
	    tuple: (sensor, tx, batLevel) with battery level or '' on early/error return
	"""


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
		bat      		= mfgData[18:20] # == 
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
			BLEsensorMACs[mac]["onOff"] 						= onOff#  = ALL OR JUST BUTTON 
			BLEsensorMACs[mac]["trigx"] 						= stateOfBeacon#  = ALL OR JUST BUTTON 
			BLEsensorMACs[mac]["batteryLevel"] 					= batLevel#  = ALL OR JUST BUTTON 

		return sensor, tx,  batLevel
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return sensor, tx,  ""



#################################
def doBLESatech( mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Decodes Satech beacon service-data (16) advertisements, dispatching on sub-type (tempHum, accel, genInfo, sos) to extract temperature/humidity, 3-axis acceleration, general info (battery voltage, chip temperature, counter, uptime) or SOS button state, and sends the values plus SOS on/off triggers to Indigo when changed or after the timing interval.

	Inputs:
	    mac (str): BLE MAC address key into parsedData/BLEsensorMACs
	    macplain (str): MAC without separators, used to trim trailing MAC from data
	    macplainReverse (str): Byte-reversed plain MAC string
	    rx (str): Received signal strength (RSSI) value
	    tx (str): TX power value, passed through and returned
	    hexData (str): Raw advertisement hex payload
	    sensor (str): Indigo sensor/device-type name
	Outputs:
	    tuple: (sensor, tx, batteryLevel) with battery level or '' on early/error return
	"""
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
				data[sensor][devId]["trigger"] = "SOS_button_pressed@"+datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
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
			if trig == "" and  tryDeltaTime( BLEsensorMACs[mac]["lastUpdate2"])  > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"			# send min every xx secs
			trig = trig.strip("/")
			if  trig:
				data[sensor][devId]["trigger"]  = trig.strip("/")
				checkIfDelaySend({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac]["lastUpdate2"] 					= time.time()
				BLEsensorMACs[mac]["chipTemperature"] 		 		= chipTemperature
				BLEsensorMACs[mac]["secsSinceStart"] 		 		= secsSinceStart
				BLEsensorMACs[mac]["counter"] 		 				= counter
				BLEsensorMACs[mac]["batteryVoltage"] 		 		= batteryVoltage

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

			if trig == "" and tryDeltaTime( BLEsensorMACs[mac]["lastUpdate2"])   > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"			# send min every xx secs
			trig = trig.strip("/")
			if  trig:
				data[sensor][devId]["trigger"]  = trig.strip("/")
				checkIfDelaySend({"sensors":data})
				# save last values to comapre at next round, check if we should send if delta  > paramter
				BLEsensorMACs[mac]["lastUpdate1"] 					= time.time()
				BLEsensorMACs[mac]["temp"] 		 					= temp
				BLEsensorMACs[mac]["hum"] 		 					= hum

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

			if trig == "" and  tryDeltaTime( BLEsensorMACs[mac]["lastUpdate2"] )  > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"			# send min every xx secs
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


	except Exception :
		U.logger.log(20,"", exc_info=True)
	return sensor, tx,  ""


#################################
def batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=3000., batteryVoltAt0=2700.):
	"""Computes a 0-100 battery percentage from a battery voltage with a temperature-dependent correction that raises the effective empty threshold as temperature drops below 10C, clamping the result between 0 and 100.

	Inputs:
	    batteryVoltage (float): Measured battery voltage in millivolts
	    temp (float): Temperature in degrees C used for correction
	    batteryVoltAt100 (float): Voltage corresponding to 100% (default 3000)
	    batteryVoltAt0 (float): Voltage corresponding to 0% (default 2700)
	Outputs:
	    int: Battery level percentage 0-100, or 0 on error
	"""
	try:
		## coin cells (CR2450/2477) sag ~12 mV/C below room temperature under load - the WHOLE
		## voltage curve moves down, not just the empty point. So shift BOTH window bounds with
		## temperature (capped at -20C, datasheets flatten out below that). The old version only
		## lowered the FLOOR by 0.7%/C -> a cold-but-healthy cell was reported nearly empty
		## (live: freezer ruuvi 2425mV at 6.8C showed 32% although the cell is ~mid-life).
		##  temp >= 20C: no shift (warm behaviour unchanged)
		##  6.8C : shift 158mV -> window 2042..2842 (ruuvi: At0=2200) -> 2425mV = 48%
		##  -18C : shift 456mV -> window 1744..2544                   -> 2300mV = 70%
		shift			= 12. * min(40., max(0., 20. - temp))
		vLow			= batteryVoltAt0   - shift
		vHigh			= batteryVoltAt100 - shift
		batteryLevel	= int(min(100.,max(0.,100.* (batteryVoltage - vLow)/(vHigh - vLow))))
		return batteryLevel
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 0

#################################
def domyBlueT( mac, rx, tx, hexData,sensor):
	"""Stub handler for myBlueT BLE devices that currently performs no decoding and immediately returns the passthrough values.

	Inputs:
	    mac (str): BLE MAC address
	    rx (str): Received signal strength (RSSI) value
	    tx (str): TX power value, returned unchanged
	    hexData (str): Raw advertisement hex payload (unused)
	    sensor (str): Indigo sensor/device-type name
	Outputs:
	    tuple: (sensor, tx, '') unchanged passthrough
	"""
	return sensor, tx,  ""


#################################
def doBLEapril(mac, macplain, macplainReverse, rx, tx, hexData,sensor):
	"""Decodes April Brother BLE beacon service-data (16) advertisements for the TAccel sub-type (3-axis acceleration, move/button on-off bits, battery level) or the THL sub-type (temperature, humidity, illuminance, battery level), then sends the values to Indigo when deltas exceed thresholds or the update interval elapses, also triggering fast SwitchBot press handling for TAccel.

	Inputs:
	    mac (str): BLE MAC address key into parsedData/BLEsensorMACs
	    macplain (str): MAC address without separators
	    macplainReverse (str): Byte-reversed plain MAC used to match the data prefix
	    rx (str): Received signal strength (RSSI) value
	    tx (str): TX power value, passed through and returned
	    hexData (str): Raw advertisement hex payload
	    sensor (str): Indigo sensor/device-type name
	Outputs:
	    tuple: (sensor, tx, batteryLevel) with battery level or '' on no-match/error
	"""
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
			if trig == "" and deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"] :							trig += "Time" 			# send min every xx secs
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
			if trig == "" and deltaTime > BLEsensorMACs[mac]["updateIndigoTiming"]: 			trig += "Time"  			# send min every xx secs
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

	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""


#################################
def doBLEminew(mac, macplain, macplainReverse, rx, tx, hexData, sensor):
	"""Decodes Minew BLE sensor service-data (16) advertisements, dispatching on sub-type (ACC acceleration, TH temperature/humidity, light on/off, batteryVoltage) to extract the relevant values plus battery level, and sends them to Indigo when deltas or timing thresholds are met, also driving fast SwitchBot press handling for the light type.

	Inputs:
	    mac (str): BLE MAC address key into parsedData/BLEsensorMACs
	    macplain (str): MAC address without separators
	    macplainReverse (str): Byte-reversed plain MAC string
	    rx (str): Received signal strength (RSSI) value
	    tx (str): TX power value, passed through and returned
	    hexData (str): Raw advertisement hex payload (sliced past MAC)
	    sensor (str): Indigo sensor/device-type name
	Outputs:
	    tuple: (sensor, tx, batteryLevel) with battery level or '' on early/error return
	"""
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

			if trigMinTime and trigTime or deltaonOff:
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
			if dTot			> BLEsensorMACs[mac]["updateIndigoDeltaAccelVector"]:	trig += "Acc-Vect/"		# acceleration change triggers 
			if deltaXYZ		> BLEsensorMACs[mac]["updateIndigoDeltaMaxXYZ"]	:		trig += "Acc-max/"			# acceleration-turn change triggers 
			if trig == "" and deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"]:				trig += "Time"				# send min every xx secs

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
			#hum					= float(signedIntfrom8(hexData[ p+4 :p+6 ]))  + intFrom8(hexData[p+6:p+8],0)/256. + BLEsensorMACs[mac]["offsetHum"]
			p = 10
			temp 				= float(signedIntfrom8(data16[ p   :p+2 ]))  + intFrom8(data16[p+2:p+4],0)/256. + BLEsensorMACs[mac]["offsetTemp"]
			hum					= float(signedIntfrom8(data16[ p+4 :p+6 ]))  + intFrom8(data16[p+6:p+8],0)/256. + BLEsensorMACs[mac]["offsetHum"]
			#U.logger.log(20,"doBLEminews1TH {}  pos:{}, temp:{}, hum:{}, hexdata:{} {} {} {}".format(mac,TagPos, temp, hum, hexData[p:p+2],hexData[p+2:p+4],hexData[p+4:p+6],hexData[p+6:p+8]))

			# make deltas compared to last send 
			trig = ""
			deltaTime 	= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])
			# check if we should send data to indigo
			trigMinTime	= deltaTime 	> BLEsensorMACs[mac]["minSendDelta"]
			if abs(BLEsensorMACs[mac]["temp"]		- temp) > 0.5: 			trig += "temp/"
			if abs(BLEsensorMACs[mac]["hum"]		- hum) > 2.: 			trig += "hum/"
			if trig == "" and deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"]: 	trig += "Time"  			# send min every xx secs
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

	except Exception :
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20,"mac#{}; sensor:{}, sensType:{}, hexdata:{}".format(mac, sensor, sensType, hexData))
	# return incoming parameetrs
	return sensor, tx,  ""



#################################
## Ruuvi ########################
#################################
def doRuuvi( mac, rx, tx, hexData,sensor):
	"""COMBINED entry for ALL ruuvi devices (RuuviTag + Ruuvi Air): extracts and
	validates the FF manufacturer section (company id 9904) ONCE, then dispatches on
	the data-format byte:  05 -> RuuviTag RAWv2;  06 -> Ruuvi Air compact;
	E1 -> Ruuvi Air FULL data set (BT5 extended adv, needs an extAdv-capable scan
	dongle). Replaces the old separate doRuuviTag/doRuuviAir entries which each
	duplicated the identical extraction.

	Inputs:
	    mac (str): BLE MAC address key into parsedData/BLEsensorMACs
	    rx (str): RSSI
	    tx (str): TX power passthrough
	    hexData (str): raw advertisement hex payload (unused - the parsed FF section is used)
	    sensor (str): incoming sensor/device-type name (passthrough when nothing decodes)
	Outputs:
	    tuple: (sensor, txPower/tx, batteryLevel or \'\')
	"""
	try:
		if mac not in parsedData:				return sensor, tx,  ""
		if "analyzed" not in parsedData[mac]:	return sensor, tx,  ""
		if mac not in BLEsensorMACs:			return sensor, tx,  ""
		data = parsedData[mac]["analyzed"]["code"].get("FF","")
		if data == "" or data.find("9904") != 0:		return sensor, tx,  ""	# name-only packets etc
		dataUse = data[4:]
		if len(dataUse) < 2 or len(dataUse) % 2 != 0:	return sensor, tx,  ""
		byte_data  = bytearray.fromhex(dataUse)
		dataFormat = dataUse[0:2].upper()
		if   dataFormat == "05" and len(byte_data) >= 22:	return doRuuviTag5( mac, rx, tx, byte_data)
		elif dataFormat == "06" and len(byte_data) >= 17:	return doRuuviAir6( mac, rx, tx, byte_data)
		elif dataFormat == "E1":							return doRuuviAirE1(mac, rx, tx, byte_data, "BLERuuviAir")
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return sensor, tx,  ""


#################################
def doRuuviAir6( mac, rx, tx, byte_data):
	"""Decodes Ruuvi Air data format 6 (compact legacy adv) and sends temp, hum,
	pressure, PM2.5, CO2, VOC, NOx, measurement counter to indigo when the temp delta
	or the update interval triggers. Called by doRuuvi (extraction/validation done there).
	spec: https://github.com/ruuvi/ruuvi-sensor-protocols/blob/master/dataformat_06.md
	layout: 0 df=06; 1-2 temp s16 0.005C; 3-4 hum u16 0.0025%; 5-6 press u16 +50000Pa;
	7-8 PM2.5 u16 0.1ug/m3; 9-10 CO2 u16 ppm; 11/12 VOC/NOx 9bit (LSB in flags bits 6/7);
	13 lumi (always FF); 15 counter u8; 16 flags (bit0=calib); 17-19 mac tail"""
	sensor = "BLERuuviAir"
	try:
		temp		= (doRuuviTag_temperature(byte_data[1:]) + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multTemp"]
		deltatemp	= abs(BLEsensorMACs[mac]["temp"] - temp)
		deltaTime	= tryDeltaTime( BLEsensorMACs[mac]["lastUpdate"])
		trig = ""
		trigMinTime	= deltaTime > BLEsensorMACs[mac]["minSendDelta"]				# dont send too often
		if deltatemp > BLEsensorMACs[mac]["updateIndigoDeltaTemp"]:				trig += "temp/"
		if trig == "" and deltaTime > BLEsensorMACs[mac]["updateIndigoTiming"]:	trig += "Time"
		calib, voc, nox = doRuuviTag_Flags(byte_data[16:])
		if trigMinTime and trig != "":
			dd = {   # the data dict to be send
				"data_format": 			"06",
				"hum": 					int(doRuuviTag_humidity(byte_data[3:])	 + BLEsensorMACs[mac]["offsetHum"] + 0.5),
				"temp": 				round(temp							 	+ BLEsensorMACs[mac]["offsetTemp"],1),
				"press": 				int(doRuuviTag_pressure(byte_data[5:]) + BLEsensorMACs[mac]["offsetPress"]),
				"PM25": 				doRuuviTag_PM25(byte_data[7:]) ,
				"CO2": 					doRuuviTag_CO2(byte_data[9:]) ,
				"VOC": 					doRuuviTag_VOC(byte_data[11:], voc),
				"NOx": 					doRuuviTag_NOX(byte_data[12:], nox),
				"measurementCount": 	int(doRuuviTag_movementcounter(byte_data[15:])),
				"trigger": 				trig.strip("/"),
				"mac": 					mac,
				"rssi":					int(rx)
			}
			checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
			BLEsensorMACs[mac]["lastUpdate"]	= time.time()
			BLEsensorMACs[mac]["temp"]			= temp
		return sensor, 0, ""
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return sensor, tx,  ""


#################################
def doRuuviAirE1(mac, rx, tx, byte_data, sensor):
	"""Decodes Ruuvi data format E1 (Extended v1 - BT5 extended advertisement, 40-byte
	payload = the FULL Ruuvi Air data set): temperature, humidity, pressure, PM 1.0/2.5/
	4.0/10, CO2, VOC, NOx, luminosity and measurement sequence. Only received when the
	scan adapter supports extended advertising (scanExtendedMode); the compact format 6
	keeps arriving via legacy advs in parallel and stays the fallback.
	spec: https://docs.ruuvi.com/communication/bluetooth-advertisements/data-format-e1
	Field layout (payload offset / meaning): 0 format 0xE1; 1-2 temp s16 0.005 C
	(0x8000 invalid); 3-4 hum u16 0.0025 % (0xFFFF inv); 5-6 pressure u16 +50000 Pa
	(0xFFFF inv); 7-8/9-10/11-12/13-14 PM1.0/2.5/4.0/10 u16 0.1 ug/m3 (0xFFFF inv);
	15-16 CO2 u16 ppm (0xFFFF inv); 17/18 VOC/NOx 9bit (MSBs, LSB in flags bits 6/7,
	0x1FF inv); 19-21 luminosity u24 0.01 lux (0xFFFFFF inv); 25-27 measurement seq u24;
	28 flags (bit0 = calibration done); 34-39 mac.

	Inputs:
	    mac (str): BLE MAC address key into BLEsensorMACs
	    rx (str): RSSI
	    tx (str): TX power passthrough
	    byte_data (bytearray): FF-section payload starting at the E1 format byte
	    sensor (str): "BLERuuviAir"
	Outputs:
	    tuple: (sensor, tx, "") passthrough; sends the data dict to Indigo as side effect
	"""
	try:
		if len(byte_data) < 40:			return sensor, tx, ""
		if mac not in BLEsensorMACs:	return sensor, tx, ""
		u16 = lambda i: (byte_data[i] << 8) |  byte_data[i+1]
		u24 = lambda i: (byte_data[i] << 16) | (byte_data[i+1] << 8) | byte_data[i+2]

		tRaw = u16(1)
		if tRaw == 0x8000:				return sensor, tx, ""	# temperature invalid -> skip packet
		if tRaw >  32767: tRaw -= 65536
		temp = (tRaw * 0.005 + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multTemp"]

		# E1 has its OWN send timer (lastUpdateE1), INDEPENDENT of the shared lastUpdate:
		# the compact format-06 arrives via the main (strong) scanner far more often than
		# E1 via the extended listener, and sharing one 60 s clock let 06 always win the
		# race and reset it -> E1 (the full air-quality data) was perpetually starved.
		deltatemp	= abs(BLEsensorMACs[mac].get("tempE1", -100) - temp)
		deltaTime	= tryDeltaTime(BLEsensorMACs[mac].get("lastUpdateE1", 0))
		trig = ""
		trigMinTime	= deltaTime	> BLEsensorMACs[mac]["minSendDelta"]
		if deltatemp > BLEsensorMACs[mac]["updateIndigoDeltaTemp"]:					trig += "temp/"
		if trig == "" and deltaTime > BLEsensorMACs[mac]["updateIndigoTiming"]:		trig += "Time"
		if not (trigMinTime and trig != ""):	return sensor, tx, ""

		flags = byte_data[28]
		dd = {   # the data dict to be send; invalid-marked fields are simply left out
			"data_format":		"E1",
			"temp":				round(temp, 2),
			"measurementCount":	u24(25),
			"trigger":			trig.strip("/"),
			"mac":				mac,
			"rssi":				int(rx)
		}
		if u16(3)  != 0xFFFF:	dd["hum"]	= int(u16(3) * 0.0025 + BLEsensorMACs[mac]["offsetHum"] + 0.5)
		if u16(5)  != 0xFFFF:	dd["press"]	= int(u16(5) + 50000   + BLEsensorMACs[mac]["offsetPress"])
		if u16(7)  != 0xFFFF:	dd["PM1"]	= round(u16(7)  * 0.1, 1)
		if u16(9)  != 0xFFFF:	dd["PM25"]	= round(u16(9)  * 0.1, 1)
		if u16(11) != 0xFFFF:	dd["PM4"]	= round(u16(11) * 0.1, 1)
		if u16(13) != 0xFFFF:	dd["PM10"]	= round(u16(13) * 0.1, 1)
		if u16(15) != 0xFFFF:	dd["CO2"]	= int(u16(15))
		voc = (byte_data[17] << 1) | ((flags >> 6) & 1)
		nox = (byte_data[18] << 1) | ((flags >> 7) & 1)
		if voc != 0x1FF:		dd["VOC"]	= voc
		if nox != 0x1FF:		dd["NOx"]	= nox
		if u24(19) != 0xFFFFFF:	dd["Illuminance"] = round(u24(19) * 0.01, 1)

		checkIfDelaySend({"sensors":{sensor:{BLEsensorMACs[mac]["devId"]:dd}}})
		BLEsensorMACs[mac]["lastUpdateE1"]	= time.time()		# E1's OWN timer
		BLEsensorMACs[mac]["tempE1"]		= temp
		BLEsensorMACs[mac]["lastUpdate"]	= time.time()		# also touch shared clock (keeps 06 from redundant temp sends)
		BLEsensorMACs[mac]["temp"]			= temp
		return sensor, tx, ""
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return sensor, tx, ""


def doRuuviTag5( mac, rx, tx, byte_data):
	"""Decodes RuuviTag data format 5 (RAWv2) and sends temp, hum, pressure, 3-axis
	acceleration, battery, movement + measurement counters to indigo when deltas or the
	update interval trigger. Called by doRuuvi (extraction/validation done there).
	spec: https://github.com/ruuvi/ruuvi-sensor-protocols/blob/master/dataformat_05.md
	layout: 0 df=05; 1-2 temp s16 0.005C; 3-4 hum u16 0.0025%; 5-6 press u16 +50000Pa;
	7-12 accXYZ s16 mg; 13-14 power (11bit battmV+1600 | 5bit txPower); 15 movement u8;
	16-17 measurement seq u16; 18-23 mac"""
	sensor		= "BLERuuviTag"
	dataFormat	= byte_data[0]
	doPrint		= False # = mac == "D1:FC:38:C4:57:75"
	try:
		# sensor is active, get all data and send if conditions ok
		# unpack  rest of sensor data 
		accelerationTotal, accelerationX, accelerationY, accelerationZ 	= doRuuviTag_magValues(byte_data[7:])
		temp 					= (doRuuviTag_temperature(byte_data[1:])+ BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multTemp"]
		batteryVoltage, txPower = doRuuviTag_powerinfo(byte_data[13:], doLog= mac in ["xxD1:FC:38:C4:57:75"])
		batteryLevel 			= batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=3000., batteryVoltAt0=2200.)
		if doPrint: U.logger.log(20, "mac:{}  in sens 1  BL:{}, batteryVoltage:{}".format(mac, batteryLevel, batteryVoltage ))

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
		if trig == "" and deltaTime > BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time"		# send min every xx secs

		if trigMinTime and trig !="":
			dd = {   # the data dict to be send
				"data_format": 			dataFormat,
				"temp": 				round(temp							 + BLEsensorMACs[mac]["offsetTemp"],1),
				"accelerationTotal": 	int(accelerationTotal),
				"accelerationX": 		int(accelerationX),
				"accelerationY": 		int(accelerationY),
				"accelerationZ": 		int(accelerationZ),
				"accelerationXYZMaxDelta":int(deltaXYZ),
				"accelerationVectorDelta":int(dTot),
				"batteryLevel": 		int(batteryLevel),
				"batteryVoltage": 		int(batteryVoltage),
				"movementCount": 		int(doRuuviTag_movementcounter(byte_data[15:])),
				"measurementCount": 	int(doRuuviTag_measurementsequencenumber(byte_data[16:])),
				"trigger": 				trig.strip("/"),
				"txPower": 				int(txPower),
				"mac": 					mac,
				"rssi":					int(rx)
			}
			# a tag that does not HAVE a sensor sends the df5 "invalid" marker FFFF for it
			# (RuuviTag Pro 2in1 = external temperature probe only: no humidity, no pressure).
			# Leave those fields OUT instead of sending the decoded 0 - a real 0% / 0 Pa
			# reading is indistinguishable from "not present" once it is in indigo.
			# Same handling as doRuuviAirE1 uses for its invalid-marked fields.
			if byte_data[3:5] != bytearray.fromhex('FFFF'):
				dd["hum"]	= int(doRuuviTag_humidity(byte_data[3:])  + BLEsensorMACs[mac]["offsetHum"] + 0.5)
			if byte_data[5:7] != bytearray.fromhex('FFFF'):
				dd["press"]	= int(doRuuviTag_pressure(byte_data[5:]) + BLEsensorMACs[mac]["offsetPress"])

			if doPrint :U.logger.log(20, " .... sending  data:{}".format( dd ) )

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

	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""


#################################
def doRuuviTag_temperature( data):
	"""Return temperature in celsius"""
	if data[0:2] == bytearray.fromhex('7FFF'):
		return 0

	temperature = twos_complement((data[0] << 8) + data[1], 16) / 200
	return round(temperature, 1)

#################################
def doRuuviTag_humidity( data):
	"""Return humidity %"""
	if data[0:2] == bytearray.fromhex('FFFF'):
		return 0

	xx = ((data[0] & 0xFF) << 8 | data[1] & 0xFF) / 400
	return round(xx, 1)

#################################
def doRuuviTag_pressure( data):
	"""Return air pressure hPa"""
	if data[0:2] == bytearray.fromhex('FFFF'):
		return 0

	xx = ((data[0] & 0xFF) << 8 | data[1] & 0xFF) + 50000
	return round(xx, 1)

#################################
def doRuuviTag_PM25( data):
	"""Decode the RuuviTag PM2.5 field: returns the particulate-matter 2.5 concentration in ug/m3 from the two raw bytes (scaled by 1/10), or 0 if the field is unset (0xFFFF)."""
	if data[0:2] == bytearray.fromhex('FFFF'):
		return 0

	xx = ((data[0] & 0xFF) << 8 | data[1] & 0xFF)/ 10.
	return round(xx, 1)

#################################
def doRuuviTag_CO2( data):
	"""Decode the RuuviTag CO2 field: returns the CO2 concentration in ppm assembled from the two raw bytes (big-endian), or 0 if the field is unset (0xFFFF)."""
	if data[0:2] == bytearray.fromhex('FFFF'):
		return 0

	xx = (data[0] & 0xFF) << 8 | (data[1] & 0xFF)
	return xx


#################################
def doRuuviTag_VOC( data, bit1):
	"""Decode the RuuviTag VOC index: returns the 9-bit volatile-organic-compound index built from the data byte (shifted left one bit) plus the carried low bit, or 0 if the field is unset (0xFF)."""
	if data[0] == bytearray.fromhex('FF'):
		return 0
	xx = (data[0] << 1) + bit1
	#U.logger.log(20, " doRuuviTag_VOC:{},    data:{},  0:{}, 9:{}, ".format( xx,  data, data[0:2], bit1) )
	return xx


#################################
def doRuuviTag_NOX( data, bit1):
	"""Decode the RuuviTag NOx index: returns the 9-bit nitrogen-oxide index built from the data byte (shifted left one bit) plus the carried low bit, or 0 if the field is unset (0xFF)."""
	if data[0] == bytearray.fromhex('FF'):
		return 0
	xx = (data[0] << 1) + bit1
	#U.logger.log(20, " doRuuviTag_NOX:{} ,  data:{},  0:{}, 9:{}, ".format( xx,  data, data[0:2], bit1) )
	return xx

#################################
def doRuuviTag_Lumi(data):
	"""Decode the RuuviTag luminosity field: maps the single raw byte through a logarithmic scale back to illuminance in lux, or returns 0 if the field is unset (0xFF)."""
	if data == bytearray.fromhex('FF'):
		return 0
	xx = data[0]
	DELTA     = math.log(65535+1., math.e)  / 254.
	CODE      = math.log(xx +1., math.e)  / DELTA
	VALUE     = math.exp(CODE * DELTA) - 1.
	
	return VALUE




#################################
def doRuuviTag_magValues( data):
	"""Return mageration mG"""
	if (	
			data[0:1] == bytearray.fromhex('7FFF') or
			data[2:3] == bytearray.fromhex('7FFF') or
			data[4:5] == bytearray.fromhex('7FFF')
		):
		return 0, 0, 0

	acc_x = twos_complement((data[0] << 8) + data[1], 16)
	acc_y = twos_complement((data[2] << 8) + data[3], 16)
	acc_z = twos_complement((data[4] << 8) + data[5], 16)
	
	return math.sqrt(acc_x * acc_x + acc_y * acc_y + acc_z * acc_z), acc_x, acc_y, acc_z

#################################
def doRuuviTag_powerinfo( data, doLog=False):
	"""Return battery voltage and tx power"""
	power_info = (data[0] & 0xFF) << 8 | (data[1] & 0xFF)
	battery_voltage = rshift(power_info, 5) + 1600
	tx_power = (power_info & 0b11111) * 2 - 40

	if rshift(power_info, 5) == 0b11111111111:
		battery_voltage = 0
	if (power_info & 0b11111) == 0b11111:
		tx_power = -9999
	#if doLog: U.logger.log(20, f" v:{battery_voltage}, data 13:{data[13]}  14:{data[14]}, powerinfo:{power_info} , r5: {rshift(power_info, 5)} ")

	return battery_voltage, tx_power


#################################
def doRuuviTag_Flags( data):
	"""Parses the Ruuvi flags byte, extracting the calibration bit (bit 0), NOx-valid bit (bit 7) and VOC-valid bit (bit 6) as individual 0/1 values.

	Inputs:
	    data (bytearray): Byte slice whose first byte holds the Ruuvi flag bits
	Outputs:
	    list: [calib, voc, nox] list of three 0/1 int flags
	"""
	calib 	=  data[0]      &0b00000001 
	nox 	= (data[0] >> 7)&0b00000001 
	voc 	= (data[0] >> 6)&0b00000001 
	return [calib, voc, nox]


#################################
def doRuuviTag_movementcounter( data):
	"""Extracts the Ruuvi Tag movement counter byte from the decoded payload, returning the first byte masked to 8 bits.

	Inputs:
	    data (list): Decoded Ruuvi Tag payload bytes
	Outputs:
	    int: Movement counter value (0-255)
	"""
	return data[0] & 0xFF


#################################
def doRuuviTag_measurementsequencenumber( data):
	"""Computes the Ruuvi Tag measurement sequence number by combining the first two payload bytes as a big-endian 16-bit value.

	Inputs:
	    data (list): Decoded Ruuvi Tag payload bytes
	Outputs:
	    int: 16-bit measurement sequence number
	"""
	measurementSequenceNumber = (data[0] & 0xFF) << 8 | data[1] & 0xFF
	return measurementSequenceNumber

#################################
def doRuuviTag_mac( data):
	"""Formats the Ruuvi Tag MAC address from payload bytes 18-23 as a lowercase hex string.

	Inputs:
	    data (list): Decoded Ruuvi Tag payload bytes
	Outputs:
	    str: 12-character lowercase hex MAC string
	"""
	return ''.join('{:02x}'.format(x) for x in data[18:24])

## Ruuvi  END   #################
#################################


#################################
#################################
## MKK ########################
#################################
def doBLEKKMsensor( mac, rx, tx, hexData,sensor):
	"""Parses an Eddystone/KKM BLE sensor advertisement for a given MAC, decoding voltage, temperature, humidity, acceleration, button-press, system/model, MFG and TLM frames, updates the per-MAC state, and dispatches changed values to Indigo via checkIfDelaySend based on trigger thresholds and timing.

	Inputs:
	    mac (str): Beacon MAC address key
	    rx (str or int): Received signal strength (RSSI)
	    tx (str or int): Transmit power value
	    hexData (str): Raw advertisement payload hex string
	    sensor (str): Incoming sensor type identifier
	Outputs:
	    tuple: (sensor, tx, batteryLevel) sensor name, tx value, and battery level
	"""

	
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
			if trig == "" and deltaTime 	> BLEsensorMACs[mac]["updateIndigoTiming"]: trig += "Time" 			# send min every xx secs
	
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

	except Exception :
		U.logger.log(20,"", exc_info=True)
	# return incoming parameetrs
	return sensor, tx,  ""


#################################

def checkIfDelaySend(packet):
	"""Decides whether a sensor data packet should be sent to Indigo immediately or buffered; packets without sensors, without a trigger, or triggered by non-time reasons (or with remote/force) are sent at once via sendURL, while time-only updates are stored in dataFromSensors for later batched sending.

	Inputs:
	    packet (dict): Sensor data packet to send or delay
	Outputs:
	    bool: True if sent immediately, False if buffered for delayed send
	"""
	global waitforcheckIfDelaySend
	### delay send  if only update for time reason, then hand it over to regular send msgs
	try:
		if "sensors" not in packet:
			U.sendURL(packet)
			return True

		for sensor in packet["sensors"]:
			for devId in packet["sensors"][sensor]:
				if "trigger" not in packet["sensors"][sensor][devId]:
					U.sendURL(packet)
					return True

				if packet["sensors"][sensor][devId]["trigger"].lower().find("time") == -1:
					U.sendURL(packet)
					return True

				if packet["sensors"][sensor][devId]["trigger"].lower().find("remote") > -1:
					U.sendURL(packet)
					return True
					
				if packet["sensors"][sensor][devId]["trigger"].lower().find("force") > -1:
					U.sendURL(packet)
					return True
					
				if "force" in packet["sensors"][sensor][devId]:
					U.sendURL(packet)
					return True

				if sensor not in dataFromSensors:
					dataFromSensors[sensor] = {}

				if devId not in dataFromSensors[sensor]:
					dataFromSensors[sensor][devId] = {}
					
				waitforcheckIfDelaySend = True
				dataFromSensors[sensor][devId] = packet["sensors"][sensor][devId]
				waitforcheckIfDelaySend = False

					#U.logger.log(20, "checkIfDelaySend sensor:{}, devId:{}, data:{} ".format(sensor, devId, packet["sensors"][sensor][devId]))
				#U.logger.log(20, "checkIfDelaySend dataFromSensors:{} ".format(dataFromSensors))
			return False

	except Exception :
		U.logger.log(20,"", exc_info=True)

	U.sendURL(packet) 
	return True

#################################
## BLE Sensors     ###########
#################################



#################################
def checkIFtrackMacIsRequested():
	"""Checks for a beaconloop.trackmac request file and, if present, parses its MAC, raw/filter options and collection time, initializes trackmac logging globals, writes a START entry, and removes the request and log files.

	Inputs:
	    None.
	Outputs:
	    bool: False if no request file exists; otherwise None after setting up tracking
	"""
	global logCountTrackMac, trackMac, trackRawOnly, trackmacFilter, nLogMgsTrackMac, startTimeTrackMac, trackMacText, collectTime
	try:
		if not os.path.isfile(G.homeDir+"temp/beaconloop.trackmac"): return False

		f = open(G.homeDir+"  > temp/beaconloop.trackmac","r")
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
		U.removeFile("{}temp/beaconloop.trackmac".format(G.homeDir))
		U.removeFile("{}temp/trackmac.log".format(G.homeDir))
		if trackMac =="*": logCountTrackMac *=3
	except Exception :
		U.logger.log(20,"", exc_info=True)


#################################
def trackMacStopIf(hexstr, mac):
	"""During an active trackmac session, logs raw hex data for the tracked MAC (or all MACs with '*') while a counter and time budget remain, and finalizes/sends the collected track log when the count reaches zero or the collection time expires.

	Inputs:
	    hexstr (str): Raw advertisement hex string for this packet
	    mac (str): MAC address of the current packet
	Outputs:
	    None: Writes track entries to log/file and may send the track results via sendURL
	"""
	global logCountTrackMac, trackMac, startTimeTrackMac
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

	except Exception :
		U.logger.log(20,"", exc_info=True)

#################################
def writeTrackMac(textOut0, textOut2, mac):
	"""Appends a formatted trackmac log line to temp/trackmac.log and to the in-memory trackMacText, honoring raw-only and filter options, and also logs it; entries are skipped when they do not match the active raw/filter constraints.

	Inputs:
	    textOut0 (str): Leading label/category tag for the entry
	    textOut2 (str): Main message text
	    mac (str): MAC address associated with the entry
	Outputs:
	    None: Writes to trackmac.log file, logger, and trackMacText global
	"""
	global trackMacText
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
	except Exception :
		U.logger.log(20,"", exc_info=True)


#################################
def fillHCIdump(hexstr):
	"""When BLE collection is active and not using the socket method, appends the space-separated hex dump line to temp/hcidump.data, then returns the hex string with the 14-character preamble stripped so it starts at the MAC.

	Inputs:
	    hexstr (str): Raw advertisement hex string including preamble
	Outputs:
	    str: Hex string with leading 14 chars removed (starts at MAC)
	"""
	global writeDumpDataHandle
	try:
		if BLEcollectStartTime > 0:		# live capture from the running stream - works for hcidump AND socket method
			if not os.path.isfile(G.homeDir+"temp/hcidump.data") or writeDumpDataHandle == "":
				writeDumpDataHandle = open(G.homeDir+"temp/hcidump.data","a")
			outstring = "> " + " ".join([ hexstr[i:i+2] for i in range(0,len(hexstr),2) ])+"\n"
			writeDumpDataHandle.write(outstring)

		checkWatchMACRequest()
		if watchMACReq["active"]:
			tt = time.time()
			if tt > watchMACReq["until"]:
				watchMACReq["active"] = False
			elif len(hexstr) >= 26 and hexstr[6:8] == "02":			# legacy adv report
				connectable = hexstr[10:12] in ("00","01")			# ADV_IND / ADV_DIRECT
				advMacRev   = hexstr[14:26]
				# LIST mode (battery batch): ANY adv counts - online = good enough. The kernel's
				# pending create-connection catches the tag's next CONNECTABLE frame itself, so
				# gating on connectable frames here (a gatttool-era babysit) only starved tags
				# that mostly send non-connectable frames into the 900s patience fallback.
				# SINGLE mode (gatttool engine pre-listen) keeps the connectable gate.
				if watchMACReq["mode"] == "list":					# battery batch: accumulate who is awake, keep watching
					if advMacRev in watchMACReq["macsRev"]:
						mac  = watchMACReq["macsRev"][advMacRev]
						last = watchMACReq["seen"].get(mac, 0.)
						watchMACReq["seen"][mac] = tt
						if tt - last > 2.:							# throttle file writes per mac
							f = open(G.homeDir+"temp/beaconloop.seenMACs","w"); f.write(json.dumps(watchMACReq["seen"])); f.close()
							# first time heard = the interesting event (level 20); the deliberate freshness
							# refreshes every couple of secs only clutter the log -> debug level
							U.logger.log(20 if last == 0. else 10,"watchMAC list: adv of {} -> seenMACs ({} of {} heard{})".format(mac, len(watchMACReq["seen"]), len(watchMACReq["macsRev"]), "" if last == 0. else ", refresh"))
				elif connectable and advMacRev == watchMACReq["macRev"]:
					# report the RSSI too: BLEconnect logs it with "connecting NOW" - a later connect
					# timeout despite STRONG rssi = adapter problem; WEAK rssi (< ~-85) = the tag
					# probably cannot hear our (weak onboard) radio -> range asymmetry, not software
					rssi = 0
					try:
						vv = int(hexstr[-2:], 16);	rssi = vv - 256 if vv > 127 else vv
					except Exception: pass
					f = open(G.homeDir+"temp/beaconloop.seenMAC","w"); f.write(json.dumps({"ts": tt, "rssi": rssi})); f.close()
					U.logger.log(20,"watchMAC: connectable adv seen (rssi {}) -> notified BLEconnect".format(rssi))
					watchMACReq["active"] = False

	except Exception :
		U.logger.log(20,"", exc_info=True)
	return  hexstr[14:] # start w the MAC#, skip the preamble


#################################
def BLEAnalysisSocket(hci):
	"""Runs a BLE analysis scan using the socket acquisition method: cleans up old temp/data files, resets the HCI adapter, launches hcitool lescan and hcidump for the configured collection time, then calls BLEAnalysis to process the captured data.

	Inputs:
	    hci (str): HCI Bluetooth adapter name (e.g. hci0)
	Outputs:
	    bool: False if acquisition method is not socket; True after the scan completes
	"""
	global BLEcollectStartTime
	try:
		if rpiDataAcquistionmethod != "socket": return False

		bluetoothctl = False
		lescanData	 = False
		## init, set dict and delete old files
		U.makeAccessible(G.homeDir+"temp", recursive=True, owner="pi")		# was "chmod +777" - an invalid mode that never applied
		U.removeFile(G.homeDir + "temp/lescan.data")
		U.removeFile(G.homeDir + "temp/hcidump.data")
		U.removeFile(G.homeDir + "temp/hcidump.temp")
		U.removeFile(G.homeDir + "temp/bluetoothctl.data")
		U.removeFile(G.homeDir + "temp/BLEAnalysis-new.json")
		U.removeFile(G.homeDir + "temp/BLEAnalysis-existing.json")
		U.removeFile(G.homeDir + "temp/BLEAnalysis-rejected.json")

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
		U.makeAccessible(G.homeDir+"temp", recursive=True, owner="pi")		# was "chmod +777" - an invalid mode that never applied

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
	except Exception :
		U.logger.log(20,"", exc_info=True)
	
	BLEcollectStartTime = -1
	return True
	
#################################
def BLEAnalysisStart(hci):
	"""Entry point/state machine for BLE analysis: when a beaconloop.BLEAnalysis request file exists it reads the rssi cutoff, starts collection (delegating to BLEAnalysisSocket for socket method), and on a subsequent call after the collection time elapses closes the dump handle and runs BLEAnalysis to finalize results.

	Inputs:
	    hci (str): HCI Bluetooth adapter name (e.g. hci0)
	Outputs:
	    bool: True only when a socket scan started successfully; otherwise False
	"""
	global writeDumpDataHandle
	global BLEanalysisdataCollectionTime, BLEcollectStartTime, BLEanalysisrssiCutoff
	try:
		if BLEcollectStartTime == -1 and os.path.isfile(G.homeDir+"temp/beaconloop.BLEAnalysis"): 
			f = open(G.homeDir+"temp/beaconloop.BLEAnalysis","r")
			try: 	BLEanalysisrssiCutoff = int(f.read().strip("\n"))
			except: BLEanalysisrssiCutoff = -99.
			f.close()
			U.removeFile("{}temp/beaconloop.BLEAnalysis".format(G.homeDir))
			BLEcollectStartTime = time.time()

			U.logger.log(20,"starting ble analysis with rssi cutoff:{}  using method:{}, for  {} secs, starttimeStamp:{}".format(BLEanalysisrssiCutoff, rpiDataAcquistionmethod, BLEanalysisdataCollectionTime, BLEcollectStartTime))
			if os.path.isfile(G.homeDir+"temp/hcidump.data"):
				U.removeFile("{}temp/hcidump.data".format(G.homeDir))

			# socket method uses the same live capture as hcidump (fillHCIdump writes the
			# stream to temp/hcidump.data) - no adapter reset, no hcitool/hcidump session,
			# no blocking wait; BLEAnalysisSocket() is no longer used
			return False

		elif  BLEcollectStartTime >0:
			#U.logger.log(20,"testing ble analysis :{}".format(tryDeltaTime( BLEcollectStartTime)))
			if tryDeltaTime( BLEcollectStartTime) >= BLEanalysisdataCollectionTime: 
				if writeDumpDataHandle !="":
					writeDumpDataHandle.close()
					writeDumpDataHandle = ""
				BLEAnalysis()
				BLEcollectStartTime = -1
			return False

		BLEanalysisdataCollectionTime = 25 # secs 
	except Exception :
		U.logger.log(20,"", exc_info=True)
	BLEcollectStartTime = -1
	return False

#################################
def BLEAnalysis():
	"""Processes the collected temp/hcidump.data file once the collection time has elapsed, parsing each line into MAC and hex payload, deduplicating packets, accumulating per-MAC statistics (RSSI, TX, message counts, beacon types, raw data), and building the BLE analysis result that is written to the BLEAnalysis JSON output files.

	Inputs:
	    None.
	Outputs:
	    None: Reads hcidump.data and writes BLEAnalysis result files / updates parsedData
	"""
	global BLEcollectStartTime
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
		extraLists = {"TLM":[]} 
		#extraLists = {"TLM":[],"iBeacon":[]}
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
					except Exception :
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
			if not MACs[mac]["raw_data"]:
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
		U.makeAccessible(G.homeDir+"temp", recursive=True, owner="pi")		# was "chmod +777" - an invalid mode that never applied
		U.sendURL(dd, squeeze=False, verbose=True, wait=True)
		time.sleep(5.+ min(10,ldd/20000.))
		U.logger.log(20, "========== BLEanalysis finished ========\n")

	except Exception :
		U.logger.log(20,"", exc_info=True)
	BLEcollectStartTime = -1
	return


#################################
def updateTimeAndZone(hciUse):
	"""Reads a queued device list from the beaconloop.updateTimeAndZone temp file and, for each MAC, connects via gatttool/pexpect and writes the current Unix timestamp plus timezone offset to a BLE characteristic (handle 3e) to synchronize the beacon's clock (e.g. Xiaomi time devices), stopping the hcidump listener while doing so.

	Inputs:
	    hciUse (str): HCI adapter identifier (e.g. 'hci0') used in hciconfig/gatttool commands
	Outputs:
	    bool: True if the BLE listener was stopped/reset (needs restart), else False
	"""
	"""
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
	"""
	try:	
		restart = False

		while True: 
			if not os.path.isfile(G.homeDir+"temp/beaconloop.updateTimeAndZone"): break
			f = open(G.homeDir+"temp/beaconloop.updateTimeAndZone","r")
			deviceList = f.read().strip("\n").split("\n")
			f.close()
			U.removeFile("{}temp/beaconloop.updateTimeAndZone".format(G.homeDir))
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
							if kk < 1:
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

								except Exception :
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

						except Exception :
							U.logger.log(20,"", exc_info=True)
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


	except Exception :
			U.logger.log(20,"", exc_info=True)

	return restart




#################################
def beep(hciUse, resetBLE=False):
	"""Reads a queued device list from the beaconloop.beep temp file and, for each MAC, connects via gatttool/pexpect and sends the device's configured ON command repeatedly for the requested beep duration, then the OFF command, optionally resetting the BLE adapter first.

	Inputs:
	    hciUse (str): HCI adapter identifier used in hciconfig/gatttool commands
	    resetBLE (bool): If True, stop the listener and reset the HCI adapter before beeping
	Outputs:
	    int: Restart-state code (0/1/2) indicating whether the BLE listener must be restarted
	"""
	global beepBatteryBusy
	try:	
		restart = 0
		beepBatteryBusy  = min(beepBatteryBusy,1)
		while True: 
			if not os.path.isfile(G.homeDir+"temp/beaconloop.beep"): break
			beepBatteryBusy  = min(beepBatteryBusy,1)

			f = open(G.homeDir+"temp/beaconloop.beep","r")
			deviceList = f.read().strip("\n").split("\n")
			f.close()
			U.removeFile("{}temp/beaconloop.beep".format(G.homeDir))
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
						else:														random = " "
						cmd = "sudo /usr/bin/gatttool -i {} {} -b {} -I".format(hciUse, random, mac) 
						U.logger.log(20,cmd)
						expCommands = pexpect.spawn(cmd)
						ret = expCommands.expect([">","error",pexpect.TIMEOUT], timeout=10)
						if ret == 0:
							U.logger.log(20,"... successful: {}-{}".format(expCommands.before,expCommands.after))
							connected = True
						else:
							if kk < 2:
								if ret == 1:	U.logger.log(20, "... error, giving up: {}-{}".format(expCommands.before,expCommands.after))
								elif ret == 2:	U.logger.log(20, "... timeout, giving up: {}-{}".format(expCommands.before,expCommands.after))
								else:			U.logger.log(20, "... unexpected, giving up: {}-{}".format(expCommands.before,expCommands.after))
							expCommands.kill(0)
							time.sleep(0.1)
							break

						time.sleep(0.1)

						try:
							cmdON		= params.get("cmdON", [])
							cmdOff		= params.get("cmdOff", [])
							beepTime	= float(params.get("beepTime", 0))
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

								except Exception :
									U.logger.log(20,"", exc_info=True)
									if ii < ntriesConnect-1: 
										U.logger.log(20, "... error, try again")
										time.sleep(1)

							if not connected:
								U.logger.log(20, "connect error, giving up")
								tryAgain = 0
					
							else:
								# ---- SwitchBot-style one-shot beep (e.g. WoBtn remote B0:E9:FE:8E:F4:40) ----
								# Some devices beep from a fixed command sequence sent ONCE; there is no
								# repeat and no separate OFF command, so handle them before the generic
								# repeat-until-beepTime logic below. Bytes captured from a BLE sniff of the app.
								# Device entry example (queued into temp/beaconloop.beep):
								#   {"B0:E9:FE:8E:F4:40": {"cmdSeq": ["char-write-req 0x0011 0100",
								#        "char-write-req 0x0013 570000000f2103bb",
								#        "char-write-req 0x0013 57bbd9077db8"]}}
								if "cmdSeq" in params:
									for cc in params["cmdSeq"]:
										U.logger.log(20,"sendline switchbot beep cmd {}".format(cc))
										expCommands.sendline( cc )
										ret = expCommands.expect([mac,"Error","failed",pexpect.TIMEOUT], timeout=5)
										if ret == 0:	U.logger.log(20,"... successful: {}-{}".format(expCommands.before,expCommands.after))
										else:			U.logger.log(20,"... no ack: {}-{}".format(expCommands.before,expCommands.after))
										time.sleep(0.3)
									tryAgain = -1
									restart  = 2
									expCommands.sendline("quit" )
									U.logger.log(20,"sendline quit ")
									ret = expCommands.expect([">","Error",pexpect.TIMEOUT], timeout=5)
									if ret != 0:
										try:	expCommands.kill(0)
										except:	pass
										expCommands = ""
									continue

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

						except Exception :
							U.logger.log(20,"", exc_info=True)
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
	except Exception :
			U.logger.log(20,"", exc_info=True)

	return restart





#################################
def getBeaconParameters(hciUse, resetBLE=True):
	"""Dispatcher for reading beacon battery/parameters; currently always delegates to getBeaconParametersInteractive (the batch variant is commented out).

	Inputs:
	    hciUse (str): HCI adapter identifier passed through to the worker
	    resetBLE (bool): Whether to reset the BLE adapter before querying
	Outputs:
	    None: Delegates to getBeaconParametersInteractive; returns nothing
	"""
	#if G.getBatteryMethod == "batch":	getBeaconParametersBatch(hciUse, resetBLE=resetBLE)
	if True:							getBeaconParametersInteractive(hciUse,resetBLE=resetBLE)
	return 


#################################
def getBeaconParametersBatch(hciUse, resetBLE=True):
	"""Batch implementation of beacon parameter reading: reads queued devices from the beaconloop.getBeaconParameters temp file and for each MAC runs a non-interactive gatttool --char-read by UUID, converts the raw value into a battery-level percentage using the device's bits/shift/norm/offset settings, and posts the results back via sendURL.

	Inputs:
	    hciUse (str): HCI adapter identifier used in gatttool/hciconfig commands
	    resetBLE (bool): If True, kill hci tools and restart the HCI adapter before reading
	Outputs:
	    bool: True after processing (data sent if any), False if no temp file or no devices
	"""

	data ={} 
	try:	
		if not os.path.isfile(G.homeDir+"temp/beaconloop.getBeaconParameters"): return False

		f = open(G.homeDir+"temp/beaconloop.getBeaconParameters","r")
		devices = f.read().strip("\n")
		f.close()

		U.removeFile("{}temp/beaconloop.getBeaconParameters".format(G.homeDir))

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
							except Exception :
								U.logger.log(20,"", exc_info=True)
					U.logger.log(20,"try#:{}/{} ... ret: {}--{}; bits: {}; norm:{}; value-I: {}; B: {}; C: {}; d: {};  F: {} ".format(ii+1, nTries, ret[0], ret[1], bits, norm, valueI, valueB, valueC, valueD, valueF) )
					data["sensors"]["getBeaconParameters"][mac] = {"batteryLevel":valueF}
					if valueF != -2: break
					if ii < nTries-1: time.sleep(0.2)


			except Exception as e:
				if "{}".format(e).find("Timeout") == -1:
					U.logger.log(20,"", exc_info=True)
				else:
					U.logger.log(20,"", exc_info=True)
				time.sleep(1)

			
	except Exception :
			U.logger.log(20,"", exc_info=True)

	if data != {}:
		U.sendURL(data, wait=True, squeeze=False)
		time.sleep(0.5)

	return True



#################################
def getBeaconParametersInteractive(hciUse, resetBLE=True):
	"""Interactive implementation of beacon parameter reading: reads queued devices from the beaconloop.getBeaconParameters temp file and for each MAC opens an interactive gatttool session via pexpect, connects, runs the device's configured GATT commands, parses the returned hex value into a battery-level percentage via bits/shift/norm/offset, and posts results with sendURL.

	Inputs:
	    hciUse (str): HCI adapter identifier used in gatttool/hciconfig commands
	    resetBLE (bool): If True, stop the listener and restart the HCI adapter before reading
	Outputs:
	    bool: False on early exit (no temp file or no devices); otherwise returns None implicitly after processing
	"""
	global beepBatteryBusy

	data = {} 
	try:	
		if not os.path.isfile(G.homeDir+"temp/beaconloop.getBeaconParameters"): return False

		f = open(G.homeDir+"temp/beaconloop.getBeaconParameters","r")
		devices = f.read().strip("\n")
		f.close()

		U.removeFile("{}temp/beaconloop.getBeaconParameters".format(G.homeDir))

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
					else:														random = " "
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
						if kk < nTries-1:
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

						except Exception :
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
								except Exception :
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

		
			except Exception :
					U.logger.log(20,"", exc_info=True)

	except Exception :
			U.logger.log(20,"", exc_info=True)

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
	"""Tests whether a given known-beacon tag pattern matches an advertising hex string, handling wildcard 'X' positions and MAC-substitution placeholders, optional full-match vs. find semantics, and a secondary tag string; on a successful match it also resolves any sub-device type from the tag definition.

	Inputs:
	    hexstring (str): Advertising payload hex string to test against the tag
	    tag (str): Tag name to look up in knownBeaconTags
	    mac (str): Device MAC address (used for tracking/logging)
	    macplain (str): MAC without separators, used to fill MAC placeholders
	    macplainReverse (str): Reversed plain MAC, used to fill RMAC placeholders
	    tagPos (int): Expected position of the tag pattern; defaults from tag definition
	    tagString (str): Hex pattern to match; defaults from the tag's hexCode
	    calledFrom (str): Caller label used only for diagnostic logging
	Outputs:
	    tuple: (posFound int, dPos int, subtypeOfBeacon dict or str) describing match position, offset delta, and resolved subtype
	"""
	try:
		doPrint = mac  in findMAC  and tag == "BLERuuviTag"#.find("D1:AD:6B:3D:AB:2D") >-1 and tag == "SwitchbotCurtain3"
		subtypeOfBeacon = ""
		inputString = copy.copy(hexstring)
		if tag != ""		: tagPos 		= int(knownBeaconTags[tag].get("pos",0))
		if tagString == ""	: tagString 	= knownBeaconTags[tag].get("hexCode","").upper()
		dPos 	 = 0
		posFound = -1

		tagString2							= knownBeaconTags[tag].get("hexCode2","").upper()
		matchString							= knownBeaconTags[tag].get("match",False)

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
			inputString = "".join(inputString)

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

		# alternative patterns (optional "hexCodeAlt" list in the tag definition):
		# a device may advertise TWO frame flavors (e.g. SwitchBot contact:
		# type-16 service data AND FF manufacturer data).  hexCode2 is an
		# AND-condition, not an alternative, so without this the second flavor
		# always ended as "reject".  Tried only when the primary hexCode failed.
		if posFound == -1 and tag != "":
			for altString in knownBeaconTags[tag].get("hexCodeAlt", []):
				if not altString: continue
				altString = altString.upper().replace("RMAC########", macplainReverse.upper()).replace("MAC#########", macplain.upper())
				pAlt = hexstring.upper().find(altString)
				if pAlt > -1:
					posFound = pAlt
					dPos     = pAlt - tagPos
					break

		if lTag2 > 0 and posFound > -1 and dPos == 0:
			if inputString.find(tagString2) == -1: posFound = -1; dPos = 99

		if len(inputString) < lTag + tagPos: posFound =-1; dPos = 100

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("tst-F   ","posFound: {}, dPos: {}, tag: {}, tagString: {}".format(posFound, dPos, tag, tagString), mac)
		if posFound > -1 and doPrint:	U.logger.log(20,"mac:{}, taginKnow:{}, posFound:{}, tag:{}, dPos:{}, tagString:{}, inputString:{}, hexstr:{}".format(mac, tag in knownBeaconTags, posFound, tag, dPos, tagString, inputString, hexstring[12:]))
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
	except Exception :
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20,"Mac#:{}, tag:{}".format(mac, tag, ))
	return -1,100, ""


#################################
def parsePackage(mac, hexstring, logData=False): # hexstring starts after mac#
	"""Parses a BLE advertising hex packet (after the MAC) into its AD structures, decoding section lengths/types, converting name sections (08/09) to ASCII mfg_info, extracting iBeacon and Eddystone TLM service data, and storing the analyzed code/text dictionaries into the global parsedData for the MAC.

	Inputs:
	    mac (str): Device MAC address used as key in parsedData
	    hexstring (str): Advertising payload hex string starting after the MAC
	    logData (bool): If True, write parsed name sections to the track-MAC log
	Outputs:
	    dict: Always an empty dict; results are written into global parsedData[mac]
	"""

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
		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
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
				if sectionCode in ["08","09"]: # names -> text (UTF-8)
					# decode the WHOLE name as UTF-8: multi-byte chars (umlauts etc.) span 2+ bytes,
					# so the old byte-by-byte decode mangled e.g. 'oe' (C3 B6) into '~~' and falsely
					# flagged a "bad string". Strip trailing null padding, then decode in one go.
					xstr = section
					s = section
					while s.endswith("00"): s = s[:-2]
					dd = hex2str(s, logLevel=0) if s else ""
					if dd == "00" and mac in BLEsensorMACs:
						# a SENSOR's 08/09 field is binary payload, not a name (it is decoded from the
						# FF/16 sections by the sensor handler) - no text, no per-byte fallback, no log
						dd = ""
					elif dd == "00":	# non-sensor: whole-string UTF-8 decode failed -> per-byte fallback
						dd = ""
						badChar = False
						for kk in range(int(len(section)/2)):
							x = section[kk*2:kk*2+2]
							if x == "00":  dd += "~"
							else:
								c = hex2str(x, logLevel=0)
								if c == "00":	dd += "~"; badChar = True
								else:			dd += c
						# a non-text name field (some beacons put binary in AD type 08/09) is normal noise -
						# the '~' fallback is the best we can do; log only at debug level (rpi debug switch)
						if badChar:  U.logger.log(10," mac:{:}, bad string: in:{}, out:{}".format(mac, xstr, dd))
						
					if  logData or ((mac == trackMac or trackMac =="*") and logCountTrackMac >0):
						writeTrackMac("parsM   ","Name: section:{}, dd:{}, ll:{}".format( section, dd, int(len(section)/2) ), mac)

					analyzed["text"]["mfg_info"] = dd
					analyzed["text"][sectionName] = dd
					analyzed["code"][sectionCode] = dd

				elif sectionCode ==  "FF": # ManufacturerSpecificData
					if section[0:8] =="4C00":
						try:
							uuidEnd = 8+2*16
							iBeacon = section[8:uuidEnd] +"-"+str(int(section[uuidEnd:uuidEnd+4],16)) +"-"+str(int(section[uuidEnd+4:uuidEnd+4+4],16))
							#analyzed["text"]["iBeacon"] = iBeacon
						except:
							continue

				elif sectionCode == "16": #ServiceData-16-bitUUID
					xxx = getTLMdata(mac, section, verbose=False)
					if xxx != {}:
						analyzed["text"]["TLM"] = xxx


				if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
						writeTrackMac("parsT   "," startOfSection:{:2d}, sectionCode:{},  sectionsData:{}".format( startOfSection, sectionCode, section), mac)

		if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("parsE   "," lenTotal:{}, data:{}, hexstr:{}".format( totalLength, analyzed, hexstring), mac)

		parsedData[mac]["analyzed"] = analyzed
		if doPrint: 
			U.logger.log(20," mac:{:}, parsedData:{}".format(mac, parsedData[mac]))

		return 	{}
	except Exception :
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20," hexstr:{}".format(hexstring))
	return {}



#################################
def getTLMdata(mac, section, verbose = False):
	"""Decodes an Eddystone TLM service-data section by locating the AAFE2000 tag and extracting battery voltage, temperature, advertising count, and time-since-boot from fixed-width hex fields.

	Inputs:
	    mac (str): Device MAC address (used for logging)
	    section (str): Hex section string expected to contain the TLM frame
	    verbose (bool): If True, log the decoded values
	Outputs:
	    dict: TLM values {batteryVoltage, temp, advCount, timeSince}, or empty dict if no TLM tag found
	"""
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

	except Exception :
		U.logger.log(20,"", exc_info=True)
	return retData


#################################
def checkForValueInfo( tag, tagFound, mac, hexstr ):
	"""For a found beacon tag, runs the tag's configured 'msgGet' commands to extract value fields from the advertising hex (or a parsed AD section), applying position/and-mask/length/reverse/norm and a type conversion (int/float/bool/string/bits) to build a dictionary of decoded sensor values.

	Inputs:
	    tag (str): Beacon tag name whose command definitions to apply
	    tagFound (str): Match status; commands only run when equal to 'found'
	    mac (str): Device MAC address (used for tracking/parsedData lookup)
	    hexstr (str): Full advertising hex string to extract values from
	Outputs:
	    dict: Decoded values keyed by command name plus a 'sendImmediatelyIfChanged' flag
	"""
	try:


		if mac == trackMac and logCountTrackMac >0:
			writeTrackMac("Val-0   ","tag:{}; tagFound:{}; tagin:{}; hexstr:{}".format(tag, tagFound, tag in knownBeaconTags, hexstr), mac )
		decodedData = {}
		verbose = False #  mac == "D1:AD:6B:3D:AB:2D"
		if verbose:	U.logger.log(20,"mac:{}, tag:{}, tagFound:{}, hexstr:{}".format(mac, tag, tagFound, hexstr[12:]))
		decodedData["sendImmediatelyIfChanged"] = False
		if tag in knownBeaconTags and tagFound == "found" and "commands" in knownBeaconTags[tag]:
			for cmdName in knownBeaconTags[tag]["commands"]:
				cmdDict = knownBeaconTags[tag]["commands"][cmdName]
				if cmdDict is None: 						continue
				if cmdDict == "": 							continue
				if cmdDict == {}: 							continue
				if type(cmdDict) == type(""): 				continue
				if cmdDict.get("type","") != "msgGet": 		continue
				if "params" not in cmdDict: 				continue
				tagtest =  cmdDict.get("tag","") 
				if tagtest != "" and hexstr.find(tagtest) == -1: continue
				tagtest =  cmdDict.get("tag","") 
				if tagtest != "" and hexstr.find(tagtest) == -1: continue
				decodedData["sendImmediatelyIfChanged"] =  decodedData["sendImmediatelyIfChanged"] or cmdDict.get("sendImmediatelyIfChanged",False) 
				params = cmdDict["params"]
				decodedData[cmdName] = ""
				useAdv = cmdDict.get("useAdv","") 
				try:
					Bstring = ""
					
					if  verbose:
						U.logger.log(20,"mac:{}, tag:{}, tagtest:{}, cmd:{}, params:{}, hexstr:{}".format(mac, tag,tagtest,  cmdName, params, hexstr[12:]))
						pass
					if len(params) > 1: 
						if mac == trackMac and logCountTrackMac >0:
							writeTrackMac("   ","cmd:{}, params:{}".format(cmdName, params), mac )
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

						if  verbose:	U.logger.log(20,"mac:{}, pass 1".format(mac))
						if useAdv == "":
							bHexStr = hexstr[12:]
							Bstring =  bHexStr[pos:pos+length*2]
						else:
							if mac not in parsedData: continue
							if "analyzed" not in parsedData[mac]: continue
							bHexStr = parsedData[mac]["analyzed"]["code"].get(useAdv,"")
							if bHexStr == "": continue
							Bstring = bHexStr[pos:pos+length*2]

						if reverse:
							Bstring = Bstring[2:4]+Bstring[0:2]

						if  verbose:	U.logger.log(20,"mac:{}, pass 2".format(mac))
						if Bstring == "": continue
						if  verbose:	U.logger.log(20,"mac:{}, pass 3".format(mac))
						
						if nType =="float":	decodedData[cmdName] = float(int(Bstring,16)&andWith)/norm
						else:				decodedData[cmdName] = (int(Bstring,16)&andWith)//norm

						if nType == "int": 		decodedData[cmdName] = int(decodedData[cmdName]+0.5)
						if nType == "bool": 	decodedData[cmdName] = decodedData[cmdName] != 0
						if nType == "float": 	decodedData[cmdName] = float(decodedData[cmdName])
						if nType == "string": 	decodedData[cmdName] = resultON if decodedData[cmdName] else resultOFF
						if nType == "bits": 	decodedData[cmdName] = "{:08b}".format(decodedData[cmdName])
						if verbose:  U.logger.log(20,"{}: cmdName:{:15s}, bHexStr:{} pos:{}, hex:{}, norm:{}, length:{}, andWith:{}, reverse:{}, Bstring:{}, andResult:{}, resultON:{}, resultOFF:{}, res:{}".format(mac, cmdName, bHexStr, pos, Bstring, norm, length, andWith, reverse, Bstring, int(Bstring,16)&andWith, resultON, resultOFF, decodedData[cmdName] ) )

				except Exception :
					U.logger.log(20,"", exc_info=True)
					if mac == trackMac and logCountTrackMac >0:
						U.logger.log(20,"", exc_info=True)
					decodedData[cmdName] = ""

	except Exception :
		U.logger.log(20,"", exc_info=True)
	return decodedData


#################################
advShadowStats = {}
batteryFromBLEconnect = {}
watchMACReq = {"active": False, "mode": "single", "macRev": "", "macsRev": {}, "seen": {}, "until": 0., "lastCheck": 0., "raw": ""}	# BLEconnect asks us to watch for connectable advs (one mac or whole battery list)


#################################
def checkWatchMACRequest():
	"""Throttled check for temp/beaconloop.watchMAC (written by BLEconnect before gatt
	jobs): loads the request - we are scanning anyway, so we do the advertisement
	watching for BLEconnect instead of it starting an own scan.
	Two forms: {"mac":..} = single (beep, one-shot: seen -> temp/beaconloop.seenMAC,
	stop) and {"macs":[..]} = battery batch (stays active; every connectable adv of a
	listed mac updates temp/beaconloop.seenMACs {MAC: lastSeenSecs}). A changed file
	content reloads the request - BLEconnect refreshes the list periodically and a beep
	may temporarily replace it with its single-mac request; the accumulated seen times
	survive the switch (pruned to the current list / 30 min on each list load)."""
	tt = time.time()
	if tt - watchMACReq["lastCheck"] < 0.5: return
	watchMACReq["lastCheck"] = tt
	fn = G.homeDir+"temp/beaconloop.watchMAC"
	try:
		if os.path.isfile(fn):
			jj, raw = U.readJson(fn)
			if raw == watchMACReq["raw"]: return		# unchanged request - keep current state (also: no re-trigger after a single-mode hit)
			watchMACReq["raw"] = raw
			macs  = jj.get("macs",[])
			mac   = jj.get("mac","")
			until = float(jj.get("ts", tt)) + float(jj.get("maxWait", 25))
			if macs:
				macsRev = { "".join(reversed(str(m).upper().split(":"))): str(m).upper() for m in macs }
				if set(macsRev) != set(watchMACReq["macsRev"]):
					U.logger.log(20,"watchMAC: watching for connectable advs of {} macs (battery list, until {:.0f})".format(len(macsRev), until))
				watchMACReq["macsRev"] = macsRev
				for m in list(watchMACReq["seen"]):		# prune done/stale macs, keep times across refreshes
					if m not in macsRev.values() or tt - watchMACReq["seen"][m] > 1800.:
						del watchMACReq["seen"][m]
				watchMACReq["mode"]   = "list"
				watchMACReq["until"]  = until
				watchMACReq["active"] = True
				# ack right away (file may be just {}): BLEconnect knows we understood the
				# list - no ack within 30 secs = old beaconloop -> it reads serially instead
				f = open(G.homeDir+"temp/beaconloop.seenMACs","w"); f.write(json.dumps(watchMACReq["seen"])); f.close()
			elif mac != "":
				watchMACReq["mode"]   = "single"
				watchMACReq["macRev"] = "".join(reversed(mac.upper().split(":")))
				watchMACReq["until"]  = until
				watchMACReq["active"] = True
				U.logger.log(20,"watchMAC: watching for connectable adv of {} (until {:.0f})".format(mac, watchMACReq["until"]))
			else:
				watchMACReq["active"] = False
		else:
			watchMACReq["active"] = False
			watchMACReq["raw"]    = ""
	except Exception:
		watchMACReq["active"] = False
		U.logger.log(20,"watchMAC: bad request file", exc_info=True)
#################################
def checkBatteryReadFile():
	"""Picks up battery levels read by BLEconnect (temp/batteryread.json, written by its
	low-priority battery queue) and stores them; checkIfTagged merges each into the NEXT
	message of the specific mac."""
	fn = G.homeDir+"temp/batteryread.json"
	if not os.path.isfile(fn): return
	try:
		bb = json.load(open(fn))
		os.remove(fn)
		for bMac in bb: batteryFromBLEconnect[bMac.upper()] = bb[bMac]
		U.logger.log(20,"battery results from BLEconnect: {}".format(bb))
	except Exception:
		U.logger.log(20,"", exc_info=True)


#################################
def setAdvertising(onOff):
	"""Enables/disables the iBeacon advertising (LE Set Advertise Enable). Socket method:
	sent on the open raw HCI socket (no hcitool needed, errors are logged - a silently
	still-advertising onboard radio makes every gatt connect time out). Other methods,
	or when the socket send fails: hcitool fallback as before.

	Inputs:
	    onOff (bool): True = enable advertising, False = disable
	Outputs:
	    None
	"""
	if rpiDataAcquistionmethod == "socket" and currentBLESocket is not None:
		try:
			bluez.hci_send_cmd(currentBLESocket, 0x08, 0x000A, b"\x01" if onOff else b"\x00")
			return
		except Exception as e:
			U.logger.log(20,"LE Set Advertise Enable={:d} via socket failed ({}) - trying hcitool".format(onOff, type(e).__name__))
	try:	readPopen("sudo hcitool -i {} cmd 0x08 0x000a {:02d} >/dev/null 2>&1".format(useHCIForBeacon, onOff))
	except Exception: pass


#################################
def checkBeaconloopPause():
	"""Single-dongle handshake: BLEconnect creates temp/beaconloop.pause (content = timestamp)
	when it needs the shared adapter for a gatt job (beep/battery/switchbot). We disable
	scanning and wait until the file is gone or its timestamp is older than 55 secs
	(failsafe against a crashed BLEconnect); a stale file is deleted here.
	BLEconnect may extend the pause by rewriting the file with a fresh timestamp.

	Outputs:
	    float: seconds paused (0 = no pause happened)
	"""
	fn = G.homeDir+"temp/beaconloop.pause"
	try:
		if not os.path.isfile(fn): return 0
		t0 = time.time()
		# pause file content: plain timestamp = FULL pause (scan + advertising off), or
		# json {"ts":.., "keepScan": true} = ADV-ONLY pause: the LE scan stays RUNNING and the
		# kernel stops/restarts it itself around its create-connection - connects provably
		# succeed in that environment on the onboard radio where the pre-disabled-scan
		# pause only produced connect timeouts
		keepScan = False
		try:
			raw = open(fn).read().strip()
			if raw.startswith("{"): keepScan = bool(json.loads(raw).get("keepScan", False))
		except Exception: pass
		U.logger.log(20,"pausing {} - BLEconnect needs the adapter (temp/beaconloop.pause)".format("advertising only, LE scan stays ON" if keepScan else "scan"))
		if not keepScan:
			if rpiDataAcquistionmethod == "socket":
				try:
					if currentBLESocket is not None: hci_disable_le_scan(currentBLESocket)
				except Exception: pass
			else:
				U.killOldPgm(-1,"lescan")
		# SINGLE-DONGLE: also stop the iBeacon ADVERTISING while BLEconnect uses the radio. The
		# onboard/combined Pi controller frequently cannot create an LE connection (beep/battery/
		# switchbot) while it is advertising -> the connect just times out. Advertising is restored
		# when the pause ends. (2-dongle mode never pauses, so this only affects the shared adapter.)
		# Socket method: send LE Set Advertise Enable=0 on the OPEN raw socket - no hcitool
		# dependency, and a failure is VISIBLE (the old "sudo hcitool .. >/dev/null" swallowed
		# everything; if the disable silently fails, BLEconnect only ever sees connect timeouts).
		setAdvertising(False)
		while True:
			if not os.path.isfile(fn): break
			# fallback on an unreadable/half-written file is the file's OWN mtime, NOT t0: with t0 a
			# single failed read (empty string while the writer truncates) made a pause that had been
			# refreshed all along look older than 55 secs, so the pause was dropped in the middle of a
			# gatt/qualification run and re-entered 5 secs later - scan flapping. mtime is refreshed by
			# every write, so a live writer can never look stale, and a dead one still times out.
			try:	ts = os.path.getmtime(fn)
			except Exception:	ts = t0
			try:
				raw = open(fn).read().strip()
				if raw != "":
					ts  = float(json.loads(raw).get("ts", ts)) if raw.startswith("{") else float(raw)
			except Exception: pass
			if time.time() - ts > 55.:
				U.logger.log(20,"pause file stale (> 55 secs) - resuming scan, deleting file")
				try:	os.remove(fn)
				except Exception: pass
				break
			time.sleep(0.5)
			U.echoLastAlive(G.program)
		setAdvertising(True)		# restore iBeacon advertising
		dt = time.time() - t0
		U.logger.log(20,"{} pause ended after {:.1f} secs".format("adv-only" if keepScan else "scan", dt))
		return max(dt, 0.1)
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return 0


#################################
def testAdvMatch(mac, tag, macplain, macplainReverse):
	"""Structure-based tag test: checks the advMatch matchers of a known tag against the
	AD sections already parsed into parsedData[mac]["analyzed"] (code per AD type, mfg_info for names).
	All matchers of the tag must succeed. Matcher fields: type (AD section type or NAME),
	startsWith (hex for sections / ascii for NAME; may contain X wildcards and
	MAC#########/RMAC######## placeholders), contains (NAME substring), lenBytes (exact
	section data length). Old key names prefix/lenB are still accepted.

	Inputs:
	    mac (str): device MAC (key into parsedData)
	    tag (str): tag name in knownBeaconTags (must have a non-empty advMatch list)
	    macplain (str): MAC without separators (for MAC######### placeholder)
	    macplainReverse (str): reversed byte-order MAC (for RMAC######## placeholder)
	Outputs:
	    bool: True if every matcher of the tag matches this advertisement
	"""
	try:
		matchers = knownBeaconTags.get(tag,{}).get("advMatch",[])
		if not matchers: return False
		analyzed = parsedData.get(mac,{}).get("analyzed",{})
		code = analyzed.get("code",{})
		name = analyzed.get("text",{}).get("mfg_info","")
		for m in matchers:
			tp = m.get("type","")
			lenB = m.get("lenBytes", m.get("lenB",0))
			if tp == "NAME":
				if name == "": return False
				if lenB and len(name) != lenB: return False
				if "contains" in m:
					if m["contains"] == "" or name.find(m["contains"]) == -1: return False
				else:
					patN = m.get("startsWith", m.get("prefix",""))
					if patN == "" and lenB == 0: return False	# empty/unreadable matcher must NEVER match-all (schema mismatch protection)
					if not name.startswith(patN): return False
			else:
				sec = code.get(tp,"")
				if sec == "": return False
				sec = sec.upper()
				if lenB and len(sec) != lenB*2: return False
				pat = m.get("startsWith", m.get("prefix","")).replace("MAC#########", macplain.upper()).replace("RMAC########", macplainReverse.upper())
				if pat == "" and lenB == 0: return False		# empty/unreadable matcher must NEVER match-all (schema mismatch protection)
				if len(sec) < len(pat): return False
				for ii in range(len(pat)):
					if pat[ii] != "X" and pat[ii] != sec[ii]: return False
		return True
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return False


#################################
def checkIfTagged(mac, macplain, macplainReverse, hexstr, batteryLevel, rssi, txPower):
	"""Core classification routine for a received advertisement: pulls parsed data for the MAC, tries to match the device against its existing tag or any known tag (honoring accept-new-beacon settings and RSSI thresholds), decodes value/battery info, fills the read-cycle structure and history, and decides whether the message is accepted or rejected.

	Inputs:
	    mac (str): Device MAC address being evaluated
	    macplain (str): MAC without separators, passed to tag matching
	    macplainReverse (str): Reversed plain MAC, passed to tag matching
	    hexstr (str): Full advertising hex string for this packet
	    batteryLevel (int or str): Pre-computed battery level, or empty string if unknown
	    rssi (int): Received signal strength, compared against accept thresholds
	    txPower (int): Transmit power stored into the read-cycle data
	Outputs:
	    tuple: (rejectThisMessage str, sendNow bool) giving the accept/reject decision and whether to send immediately
	"""
	doPrint = False
	sendNow = False
	try:
		prio  				= -1
		dPos  				= -100
		tagFound 			= "notTested"
		rejectThisMessage 	= "reject"
		mfg_info			= ""
		#iBeacon				= ""
		mode				= ""
		onOff				= ""
		typeOfBeacon		= "other"
		subtypeOfBeacon		= ""
		existing 			= mac in onlyTheseMAC
		mfgTagged 			= False
		tagOld				= ""

		if mac not in parsedData:  return "reject", sendNow
		if "analyzed" not in parsedData[mac]: return "reject", sendNow
		#iBeacon  = parsedData[mac]["analyzed"]["text"].get("iBeacon","")
		mfg_info = parsedData[mac]["analyzed"]["text"].get("mfg_info","")

		if "TLM" in parsedData[mac]["analyzed"]["text"] and "batteryVoltage" in  parsedData[mac]["analyzed"]["text"]["TLM"]:
			batteryVoltage = parsedData[mac]["analyzed"]["text"]["TLM"]["batteryVoltage"]
			temp = parsedData[mac]["analyzed"]["text"]["TLM"]["temp"]
			TLMenabled = True
		else:
			TLMenabled = ""
			batteryVoltage = 0
			temp = 20.
			
		doPrint = mac in findMAC 
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
			if doPrint: U.logger.log(20,"{} pass2 tagFound:{}, tagOld:{}".format(mac, tagFound, tagOld) )

			if tagOld not in ["", "other"]:
				if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
					writeTrackMac("tag-1   ", "tag:{}, useOnlyIfTagged: {}".format(tagOld, useOnlyIfTagged), mac)

				if  tagOld in knownBeaconTags:
					# structure-based test FIRST (advMatch on parsed AD sections: FF/16/NAME);
					# the raw-hex string method (testComplexTag) is only the fallback for
					# tags without advMatch matchers or when a subType must be resolved.
					if knownBeaconTags[tagOld].get("advMatch") and not knownBeaconTags[tagOld].get("subType"):
						if testAdvMatch(mac, tagOld, macplain, macplainReverse):
							posFound, dPos, subtypeOfBeacon = 0, 0, ""
						else:
							posFound, dPos, subtypeOfBeacon = testComplexTag(hexstr[12:-2], tagOld, mac, macplain, macplainReverse, calledFrom="checkIfTagged-1")
					else:
						posFound, dPos, subtypeOfBeacon = testComplexTag(hexstr[12:-2], tagOld, mac, macplain, macplainReverse, calledFrom="checkIfTagged-1")
					#if tagOld == "iBeacon" and iBeacon != "":
					#	rejectThisMessage = tagOld

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

		if doPrint: U.logger.log(20,"{} pass3 tagFound:{}, tagOld:{}".format(mac, tagFound, tagOld) )

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
			(tagFound != "found") or 
			(existing and tagOld in ["", "other"]) or  # check if we find a better tag than "other"
			( not existing  and  (acceptNewTagiBeacons != "off"  or mfgTagged)   ) # if not existing try to find tag if enabled 
			):

			for testTag in knownBeaconTags:
				#if doPrint:  U.logger.log(20,"{} testing  testTag:{}=={}, ".format(mac, testTag, knownBeaconTags.get(testTag,"")) )
				#if testTag in ["other", tagOld, "iBeacon"]: 		continue
				if testTag in ["other"]:							continue
				if knownBeaconTags[testTag]["pos"] == -1: 			continue
				# structure-based test first (see pass2); string method as fallback
				if knownBeaconTags[testTag].get("advMatch") and not knownBeaconTags[testTag].get("subType"):
					if testAdvMatch(mac, testTag, macplain, macplainReverse):
						posFound, dPos, subtypeOfBeacon = 0, 0, ""
					else:
						posFound, dPos, subtypeOfBeacon = testComplexTag(hexstr[12:-2], testTag, mac, macplain, macplainReverse, calledFrom="checkIfTagged-2")
				else:
					posFound, dPos, subtypeOfBeacon = testComplexTag(hexstr[12:-2], testTag, mac, macplain, macplainReverse, calledFrom="checkIfTagged-2")
				if posFound == -1: 									continue
				if abs(dPos) > knownBeaconTags[testTag]["posDelta"]:continue
				if doPrint:  U.logger.log(20,"{} 2 tagOld:{}, testing  testTag:{}, posFound:{}, check:{}".format(mac, tagOld, testTag, posFound, acceptNewTagiBeacons == "all" or acceptNewTagiBeacons == testTag or tagOld in ["", "other"]) )
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
				if rssi > acceptNewBeaconsMinSIgnal: 
					if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
						writeTrackMac("tag-8   ", "accept rssi > accept new  and !tagfound and not accept mfg name", mac)
					#print " new beacon :", mac, rssi, acceptNewBeaconsMinSIgnal
					rejectThisMessage = "new"

		# (shadow advMatch-vs-string comparison removed 2026-07-29: advMatch is now the
		#  PRIMARY test in pass2 and the search loop; testComplexTag is the fallback)

		decodedDatas = checkForValueInfo( typeOfBeacon, tagFound, mac, hexstr )
		if batteryLevel != "" or "batteryLevel" not in decodedDatas: decodedDatas["batteryLevel"] = batteryLevel

		if batteryFromBLEconnect and mac in batteryFromBLEconnect:	# battery read by BLEconnect -> attach to this message
			decodedDatas["batteryLevel"] = batteryFromBLEconnect.pop(mac).get("batteryLevel","")
			U.logger.log(20,"mac:{} batteryLevel from BLEconnect: {}".format(mac, decodedDatas["batteryLevel"]))

		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-9   ", "batteryLevel>{}<".format(decodedDatas["batteryLevel"]) ,mac)

		if decodedDatas["batteryLevel"] == "" and batteryVoltage != 0: 
			batteryVoltAt100 = 3000.
			batteryVoltAt0   = 2700.
			if mac in  batteryLevelUUID and batteryLevelUUID[mac].find("TLM") == 0: # format is TLM-Vol@0-Volt@100%
				levels = batteryLevelUUID[mac].split("-")
				if len(levels) == 3:
					batteryVoltAt100 = float(levels[1]) 
					batteryVoltAt0   = float(levels[2]) 
			decodedDatas["batteryLevel"] = batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=batteryVoltAt100, batteryVoltAt0=batteryVoltAt0)

		#fillbeaconsThisReadCycle(mac, rssi, txPower, iBeacon, mfg_info, typeOfBeacon, subtypeOfBeacon, TLMenabled, decodedDatas, parsedData[mac]["analyzed"]["text"])
		fillbeaconsThisReadCycle(mac, rssi, txPower, mfg_info, typeOfBeacon, subtypeOfBeacon, TLMenabled, decodedDatas, parsedData[mac]["analyzed"]["text"])

		# Known devices are never rejected by the TAG analysis: identification
		# exists to classify UNKNOWN macs.  A mac configured as a BLE sensor or
		# as an accepted beacon may emit several frame flavors (e.g. SwitchBot
		# contact type-16 service data AND FF mfg data) - all of them count.
		# The min/max signal check below keeps its authority.
		if rejectThisMessage == "reject" and (mac in BLEsensorMACs or existing):
			rejectThisMessage = typeOfBeacon if typeOfBeacon not in ["", "other"] else "all"

		if not checkMinMaxSignalAcceptMessage(mac, rssi): rejectThisMessage = "reject"

		if rejectThisMessage != "reject" and mac in beaconsThisReadCycle: 
			sendNow = fillHistory(mac)

		if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
			writeTrackMac("tag-E   ", "beaconsThisReadCycle ..mfg_info: {}, rejectThisMessage:{},  batteryLevel>{}<".format(mfg_info, rejectThisMessage, batteryLevel) ,mac)
		if doPrint:  U.logger.log(20, "mac:{}  after end of  decodedDatas:{}".format(mac, decodedDatas ))


		if doPrint:  U.logger.log(20,"{} 5 rejectThisMessage:{}, typeOfBeacon:{}, ".format(mac, rejectThisMessage, typeOfBeacon) )
	except Exception :
		U.logger.log(20,"", exc_info=True)
	if rejectThisMessage == mfg_info:
		pass
		#U.logger.log(20,"{} accepted .. rejectThisMessage:{}".format(mac, rejectThisMessage) )
	return rejectThisMessage, sendNow


#################################
def getStdIbeacon(hexstr):
	"""Decodes a standard iBeacon advertisement hex string, extracting the reversed and normalized plain MAC, the colon-formatted MAC, the signed txPower, and the signed RSSI from fixed byte positions.

	Inputs:
	    hexstr (str): Raw advertisement hex string with MAC at the start and tx/rssi at the end
	Outputs:
	    tuple: (rssi int, txPower int, macplainReverse str, macplain str, mac str)
	"""
	try:
		macplainReverse = hexstr[0:12]
		macplain 		= macplainReverse[10:12]+macplainReverse[8:10]+macplainReverse[6:8]+macplainReverse[4:6]+macplainReverse[2:4]+macplainReverse[0:2]
		mac 			= macplain[0:2]+":"+macplain[2:4]+":"+macplain[4:6]+":"+macplain[6:8]+":"+macplain[8:10]+":"+macplain[10:12]
		txPower			= signedIntfrom8(str(signedIntfrom8(hexstr[-4:-2])))
		rssi			= signedIntfrom8(hexstr[-2:])
		msgStart		= 14

		return 	  rssi, txPower, macplainReverse, macplain, mac
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return    rssi, txPower, macplainReverse, macplain, mac




#################################
def fillbeaconsThisReadCycle(mac, rssi, txPower, mfg_info, typeOfBeacon, subtypeOfBeacon, TLMenabled, decodedData, analyzed):
	"""Stores or updates the per-cycle beacon record for a MAC in the global beaconsThisReadCycle dictionary, setting rssi, txPower, timestamp, beacon type/subtype, mfg info, TLM-enabled flag, analyzed AD data, and any non-empty decoded sensor values.

	Inputs:
	    mac (str): Device MAC address key
	    rssi (int): Signal strength to store
	    txPower (int): Transmit power, stored as float
	    mfg_info (str): Manufacturer/name info string
	    typeOfBeacon (str): Beacon type/tag name
	    subtypeOfBeacon (str): Beacon subtype, stored if non-empty
	    TLMenabled (bool or str): TLM-enabled flag (truthy enables it)
	    decodedData (dict): Decoded sensor values to merge in
	    analyzed (dict): Parsed AD code/text structures to store
	Outputs:
	    None: Updates the global beaconsThisReadCycle dictionary
	"""
	try:
		if mac not in beaconsThisReadCycle: setEmptybeaconsThisReadCycle(mac)
					
		if True:
										beaconsThisReadCycle[mac]["rssi"]			= rssi # signal
										beaconsThisReadCycle[mac]["txPower"]		= float(txPower) # transmit power
										beaconsThisReadCycle[mac]["timeSt"]			= time.time() 
										beaconsThisReadCycle[mac]["subtypeOfBeacon"]= "" # 
										beaconsThisReadCycle[mac]["analyzed"]		= analyzed
		if typeOfBeacon != "" and beaconsThisReadCycle[mac].get("typeOfBeacon","other") == "other":
										beaconsThisReadCycle[mac]["typeOfBeacon"]	= typeOfBeacon 
		#if iBeacon != "": 				beaconsThisReadCycle[mac]["iBeacon"]		= iBeacon # 
		if mfg_info != "": 				beaconsThisReadCycle[mac]["mfg_info"]		= mfg_info # 
		if TLMenabled !="":				beaconsThisReadCycle[mac]["TLMenabled"]		= True
		if subtypeOfBeacon !="":		beaconsThisReadCycle[mac]["subtypeOfBeacon"]= subtypeOfBeacon
		if typeOfBeacon != "other": 	beaconsThisReadCycle[mac]["typeOfBeacon"]	= typeOfBeacon # 

		for  ii in decodedData:
			if decodedData[ii] != "":		beaconsThisReadCycle[mac][ii]				= decodedData[ii]
		beaconsThisReadCycle[mac]["analyzed"]				= analyzed
		if mac =="xB0:E9:FE:A4:58:82": 
			U.logger.log(20,"mac:{}, decodedData:{}; beaconsThisReadCycle:{}".format(mac, decodedData, beaconsThisReadCycle[mac]))

	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 

#################################

def checkIfBLEprogramIsRunning(hciUse):
	"""Checks whether the BLE data-acquisition stack is operational on the given HCI adapter, verifying the adapter is up and (unless socket acquisition is used) that hcidump is still running.

	Inputs:
	    hciUse (str): HCI adapter identifier (e.g. 'hci0') to check
	Outputs:
	    bool: True if the adapter is up and the BLE program is running, else False
	"""

	try:
		if not U.checkIfHCiUP(hciUse, verbose=True):
			U.logger.log(20,"{} not up".format(hciUse))
			return False

		if  rpiDataAcquistionmethod.find("socket") == 0: 
			return True

		if not U.pgmStillRunning("hcidump -i", verbose=True): # and U.pgmStillRunning("hcitool -i", verbose=True):
			U.logger.log(20,"hcidump  not up")
			return False

		return True

	except Exception :
		U.logger.log(20,"", exc_info=True)
	return False


#################################
#################################
######## BLE SENSORS END  #######
#################################
#################################




#################################
def startHCIcmdThread():
	"""Creates and starts a background thread named 'loopCheck' that runs loopCheckBeepBattery, recording its state in the global threadCMD dict.

	Inputs:
	    None.
	Outputs:
	    None: Starts a daemon thread and logs; no return value
	"""
	global threadCMD

	U.logger.log(20, "start cmd thread ")
	try:
		threadCMD = {}
		threadCMD["state"]   = "start"
		threadCMD["thread"]  = threading.Thread(name='loopCheck', target=loopCheckBeepBattery)
		threadCMD["thread"].start()
		threadCMD["state"]   = "running"

	except  Exception :
		U.logger.log(20,"", exc_info=True)
	return 



#################################
def loopCheckBeepBattery():
	"""Background loop that repeatedly triggers beep and beacon battery-parameter checks, restarts the plugin when beep/battery changes are detected on the shared HCI, and re-evaluates which HCI to use for beeping until threadCMD is set to 'stop'.

	Inputs:
	    None.
	Outputs:
	    None: Runs continuously; triggers restarts and updates beep/battery globals
	"""
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
			checkExtListenerAlive()

		except  Exception :
			U.logger.log(20,"", exc_info=True)
			time.sleep(20)
	return 

#################################
def checkExtListenerAlive():
	"""Revives the BLE5 extended listener after it exited (radio pulled for longer than its
	~2 min retry window).  execExtListener gives up quickly ON PURPOSE - it must not sit in a
	reset loop on a radio that is gone - so SOMETHING has to start it again once the dongle is
	back.  startExtListener() only ran from the role block inside startBlueTooth, which does
	not re-run when only the BLE5 dongle was unplugged (beaconloop's own scan radio is fine),
	which is why a replug did not recover.  Idempotent: startExtListener returns immediately
	when a listener is already running on that adapter.

	Inputs:
	    None (uses the published hciRoles["extListener"]).
	Outputs:
	    None: restarts the listener thread when its radio is present again.
	"""
	try:
		want = "{}".format(hciRoles.get("extListener", {}).get("hci", ""))
		if want == "":											return		# no BLE5 role on this rpi
		th = extListenerCtl.get("thread")
		if th is not None and th.is_alive():					return		# still running
		# the listener is NOT running: hciInfo_BLE5 has to stop advertising a radio that is not
		# delivering. This is the only place that sees the death (the thread cannot report it
		# about itself - is_alive() is still True while it runs its last lines).
		sendBLE5State()
		wantMac = "{}".format(hciRoles.get("extListener", {}).get("mac", "")).upper()
		nowHCIs = U.whichHCI().get("hci", {})
		for hh in nowHCIs:										# 1st choice: the SAME dongle back (number may have changed)
			if "{}".format(nowHCIs[hh].get("BLEmac", "")).upper() != wantMac:	continue
			if nowHCIs[hh].get("upDown", "") != "UP":							continue
			if hh != want:
				hciRoles["extListener"]["hci"] = hh
				writeBeaconloopHci()							# republish so BLEconnect/beep keep excluding it
			U.logger.log(20, "extListener: radio {} is back as {} - restarting the extended listener".format(wantMac, hh))
			startExtListener(hh)
			return
		# 2nd choice: the dongle was REPLACED by a different one - its mac will never come
		# back, so adopt any free BLE5 radio instead of waiting for hardware that is gone.
		# "free" = not the scan, broadcast or BLEconnect radio (roles published by us).
		taken = []
		for _r in ("scan", "broadcast", "BLEconnect"):
			taken.append("{}".format(hciRoles.get(_r, {}).get("hci", "")))
		for hh in nowHCIs:
			if hh in taken:														continue
			if not nowHCIs[hh].get("extAdv", False):							continue
			if nowHCIs[hh].get("upDown", "") != "UP":							continue
			newMac = "{}".format(nowHCIs[hh].get("BLEmac", "")).upper()
			U.logger.log(20, "extListener: BLE5 radio {} (mac {}) REPLACED by {} (mac {}) - adopting the new one".format(want, wantMac, hh, newMac))
			hciRoles["extListener"]["hci"] = hh
			hciRoles["extListener"]["mac"] = newMac
			hciRoles["extListener"]["bus"] = "{}".format(nowHCIs[hh].get("bus", ""))
			writeBeaconloopHci()
			startExtListener(hh)
			return
	except Exception:
		U.logger.log(20, "", exc_info=True)

#################################
def checkWhichHCIForBeep():
	"""Determines which HCI adapter should be used for beeping, picking an up adapter not already used by the beacon loop or BLE connect, resets it, notifies via URL, and writes the selection to temp/beaconbeep.hci.

	Inputs:
	    None.
	Outputs:
	    None: Updates beep-HCI globals and writes the beaconbeep.hci selection file
	"""
	global hciCheckLastTime, useHCIForBeep
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
		extListenerHCIinUse = "{}".format(hciRoles.get("extListener",{}).get("hci",""))
		# match on the MAC as well: right after a replug the stored hci NUMBER can be stale
		# for a few seconds (live-seen hci2 -> hci3 -> hci2), and excluding only the stale
		# name would let this picker hciconfig-reset the real BLE5 dongle under its new name.
		extListenerMacInUse = "{}".format(hciRoles.get("extListener",{}).get("mac","")).upper()
		for hci in HCIList:
			#U.logger.log(20,"hci:{}".format(hci))
			if hci == useHCIForBeacon: continue
			if hci == hciUsedByBLEconnect.get("usedHCI",""): continue
			# NEVER the BLE5 extended listener: this picker does "hciconfig reset" on the
			# radio it chooses, which wipes that radio's extended scan (live-seen: the ext
			# listener went 98 reports/min -> 0 exactly one 50 s check later and stayed
			# dead). The extended listener is a ROLE like scan/connect - it is taken.
			if extListenerHCIinUse != "" and hci == extListenerHCIinUse: continue
			if extListenerMacInUse != "" and "{}".format(HCIList[hci].get("BLEmac","")).upper() == extListenerMacInUse: continue
			if HCIList[hci]["upDown"] != "UP": continue
			beepBatteryBusy = 0
			if useHCIForBeep != hci:
				#U.logger.log(20,"use for beep:{}".format(hci))
				U.logger.log(20,"useHCIForBeacon:{}, hciUsedByBLEconnect:{}, HCIList:{}".format(useHCIForBeacon, hciUsedByBLEconnect,HCIList))
				useHCIForBeep = hci			# set BEFORE publishing, the state strings read it
				sendHciStates()

			useHCIForBeep = hci
			cmd = "sudo hciconfig "+useHCIForBeep+" reset &"
			readPopen(cmd)
			U.writeFile("temp/beaconbeep.hci", json.dumps({"usedHCI":useHCIForBeep, "myBLEmac": HCIList[hci]["BLEmac"], "usedBus": HCIList[hci]["bus"],"pgm":"beaconbeep"}))
			#U.logger.log(20,"useHCIForBeacon:reset {}".format(useHCIForBeep))
			return 


	except Exception :
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20," HCIs:{}".format(HCIs))

	useHCIForBeep = useHCIForBeacon
	U.writeFile("temp/beaconbeep.hci", json.dumps({"usedHCI":useHCIForBeep, "myBLEmac": HCIList[useHCIForBeacon]["BLEmac"], "usedBus": HCIList[useHCIForBeacon]["bus"]}))
	beepBatteryBusy = 1
	return 




#################################
def doLoopCheck(sensor):
	"""Periodically performs maintenance checks during the beacon loop: track-MAC requests, now-file detection, BLE analysis, time/zone updates (restarting the plugin when needed), and reloading parameters.

	Inputs:
	    sensor (str): Sensor/program name used for now-file checks
	Outputs:
	    None: May restart the plugin and updates reasonMax and check-timer globals
	"""
	global reasonMax
	global sensCheckLastTime, paramCheckLastTime

	try:		
		resetBLE = False

		if tryDeltaTime( sensCheckLastTime) > 0:
			sensCheckLastTime =  time.time() +2		

			checkIFtrackMacIsRequested()

			sendBLE5State()			# BLE5 radio state: sends once the value has settled, see BLE5_SETTLE

			if U.checkNowFile(sensor): reasonMax = max(reasonMax, 7)

			if BLEAnalysisStart(useHCIForBeacon):
				U.restartMyself(param="", reason="BLEanalysis", python3=usePython3)

			if updateTimeAndZone(useHCIForBeacon):
				U.restartMyself(param="", reason="updateTimeAndZone", python3=usePython3)
	

		if  tryDeltaTime(paramCheckLastTime )> 0:
			if readParams(): reasonMax = max(reasonMax, 8) # new params
			paramCheckLastTime = time.time() +10 


		return 

	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 


def dropIgnoredRadios(HCIsIn):
	"""Removes the radios the device dialog pinned to "ignore" from the adapter list.

	Done once, right after whichHCI(), so EVERY role pick downstream (scan / broadcast / connect /
	BLE5 listener) simply never sees them - no per-role filtering to forget somewhere. The last
	remaining radio is never dropped: ignoring it would leave the rpi with no bluetooth at all,
	which is never what the user meant by ticking one radio out.

	Inputs:
	    HCIsIn (dict): the whichHCI() result
	Outputs:
	    dict: the same structure, ignored radios removed
	"""
	try:
		if not hciRolesPinned or not isinstance(HCIsIn, dict) or "hci" not in HCIsIn:	return HCIsIn
		drop = [h for h in HCIsIn["hci"] if "{}".format(hciRolesPinned.get(h,"")) == "ignore"]
		if not drop:	return HCIsIn
		keep = [h for h in HCIsIn["hci"] if h not in drop]
		if not keep:
			U.logger.log(20,"radio role pins: ALL radios are set to 'ignore' - keeping them, an rpi without bluetooth is not a working setup")
			return HCIsIn
		for h in drop:
			U.logger.log(20,"radio {} ({}) IGNORED - set to 'ignore' in the device dialog".format(h, HCIsIn["hci"][h].get("BLEmac","")))
			del HCIsIn["hci"][h]
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return HCIsIn


def pinnedRadio(modes, HCIdict, taken=()):
	"""The hci pinned to one of `modes` by the device dialog - or "" when there is no usable pin.

	A pin only wins if the radio it names is really present and UP: a dongle can be unplugged or come
	back as another hciN, and a pin must never leave a role unfilled (the auto pick then runs as
	before). Radios already holding another role are skipped too, so two contradicting pins cannot
	collapse two roles onto one radio.

	Inputs:
	    modes (tuple): dialog values to look for, e.g. ("scanBLE4","scanBLE45")
	    HCIdict (dict): HCIs["hci"]
	    taken (tuple): hci names already assigned to another role
	Outputs:
	    str: hci name, or ""
	"""
	try:
		for hci in sorted(hciRolesPinned):
			if "{}".format(hciRolesPinned[hci]) not in modes:	continue
			if hci not in HCIdict:
				U.logger.log(20,"radio role pin {}={} ignored - that radio is not present".format(hci, hciRolesPinned[hci]))
				continue
			if "{}".format(HCIdict[hci].get("upDown","")).upper() != "UP":
				U.logger.log(20,"radio role pin {}={} ignored - that radio is DOWN".format(hci, hciRolesPinned[hci]))
				continue
			if hci in taken:
				U.logger.log(20,"radio role pin {}={} ignored - that radio already holds another role".format(hci, hciRolesPinned[hci]))
				continue
			return hci
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return ""


def hciStateStrings():
	"""One state string per radio for the rpi device: hci0 .. hci3.

	Replaces the five old hciInfo* states (hciInfo / _beacons / _beep / _BLEconnect / _BLE5), which
	each named the radio of ONE role - so answering "what is hci1 doing" meant reading all five and
	cross-referencing macs. Now every radio has its own state and carries everything about itself:

	    58:11:22:53:8C:D5/USB/0b05:190e/UP/BLE4+5/scan4+5

	    mac         its BLE mac - FIRST because it is fixed width, so the states of the four
	                radios line up under each other in the device list
	    bus         USB or UART (UART = the onboard radio)
	    usb-id      vendor:product of the dongle, "none" for onboard radios
	    up-down     UP or DOWN
	    capability  what it CAN do: BLE4, BLE5 (extended only), BLE4+5 - measured, not claimed
	    function    what it IS doing, "+"-joined: scan4 / scan4+5 / scan5 / connect / BC (the
	                iBeacon broadcast) / beep, or "-" when it holds no role

	Inputs:
	    None (reads HCIs, hciRoles, scanExtendedMode, useHCIForBeep).
	Outputs:
	    dict: {"hci0": "...", "hci1": "...", ...} - always all four, "" for absent radios
	"""
	out = {"hci0": "", "hci1": "", "hci2": "", "hci3": ""}
	try:
		for hciX in out:
			hh = HCIs.get("hci", {}).get(hciX, {})
			if not hh:	continue
			ext  = hh.get("extAdv", False)
			ble4 = hh.get("ble4", True)
			cap  = "BLE4+5" if (ext and ble4) else ("BLE5" if ext else "BLE4")
			fun  = []
			if hciX == "{}".format(hciRoles.get("scan", {}).get("hci", "")):
				fun.append("scan4+5" if scanExtendedMode else "scan4")
			if hciX == "{}".format(hciRoles.get("extListener", {}).get("hci", "")):	fun.append("scan5")
			if hciX == "{}".format(hciRoles.get("BLEconnect", {}).get("hci", "")):	fun.append("connect")
			if hciX == "{}".format(hciRoles.get("broadcast", {}).get("hci", "")):	fun.append("BC")
			if hciX == "{}".format(useHCIForBeep):									fun.append("beep")
			out[hciX] = "{}/{}/{}/{}/{}/{}".format(
							hh.get("BLEmac", "?"), hh.get("bus", "?"), hh.get("usbId", "") or "none",
							hh.get("upDown", "?"), cap, "+".join(fun) if fun else "-")
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return out


def sendHciStates():
	"""Publishes the per-radio states, but only when something actually changed."""
	global lastHciStates
	try:
		now = hciStateStrings()
		if now == lastHciStates:	return
		lastHciStates = now
		U.sendURL(data={"data": now}, squeeze=False, wait=False)
	except Exception:
		U.logger.log(20,"", exc_info=True)


def probeExtendedScan(sock):
	"""Sets scanExtendedMode: True when the SCAN adapter supports BT5 extended advertising
	(LE Read Local Supported Features, feature bit 12). Then the extended scan commands
	are used and extended advertisements (Ruuvi Air data format E1 etc.) are received
	(converted to the legacy report layout by extAdvToLegacyHex). NOTE: the Pi onboard
	radios (43438/43455) are 5.0-branded but do NOT have this feature - a capable USB
	dongle (e.g. RTL8761B) is needed.

	Inputs:
	    sock (bluetooth socket): open raw HCI socket of the scan adapter (filter must pass events)
	Outputs:
	    None: sets the scanExtendedMode global and logs the decision
	"""
	global scanExtendedMode
	scanExtendedMode = False
	# A DEDICATED BLE5 radio makes combined mode pointless AND harmful. Extended scanning on the
	# scan radio costs BLE4 throughput (live on the ASUS: 202 -> 95 reports per 4 s, ~half) and the
	# BLE5 frames it would pick up are already coming in on the listener - the same E1 advertisement
	# would be processed twice. Combined mode exists for the case where there is NO free BLE5 radio
	# (2-radio rpi), not as an extra on top of one. So: listener present -> the scanner stays BLE4
	# and keeps its full rate.
	# an explicit pin on the SCAN radio decides the mode outright - that is what pinning is for
	_pinMode = "{}".format(hciRolesPinned.get(useHCIForBeacon, ""))
	if _pinMode == "scanBLE4":
		if extScanLastReported[0] != "pinned BLE4":
			extScanLastReported[0] = "pinned BLE4"
			U.logger.log(20,"BLE4-only scanning on {} - pinned to 'scanner BLE4' in the device dialog".format(useHCIForBeacon))
		reportBLE5("no - scan radio pinned to BLE4 only")
		return
	try:
		_lHci = "{}".format(hciRoles.get("extListener", {}).get("hci", ""))
		# "scanner BLE4 + BLE5" pinned here: the user wants ONE radio for both, so do not step aside
		# for a listener - that early return exists to avoid duplicate BLE5 reception when nobody asked
		if _pinMode == "scanBLE45":	_lHci = ""
		if _lHci != "" and _lHci != useHCIForBeacon:
			# log-on-change only: this probe runs every ~30 s and the verdict is stable - the same
			# sentence 2,900x a day is noise (extScanLastReported is the throttle the other verdicts use)
			_msg = "not needed - {} is the dedicated BLE5 listener".format(_lHci)
			if extScanLastReported[0] != _msg:
				extScanLastReported[0] = _msg
				U.logger.log(20,"BT5 extended-advertising scan on the scan radio {}: {} - the scanner keeps its full BLE4 rate".format(useHCIForBeacon, _msg))
			reportBLE5("yes - dedicated BLE5 listener on {}".format(_lHci))
			return
	except Exception:	pass
	if extScanBlockedByAdv[0]:
		U.logger.log(20,"BT5 extended-advertising scan on {} (mac {}): blocked - not enough radios / broadcast shares this adapter (legacy adv cmds lock the command set) -> legacy scanning".format(useHCIForBeacon, myBLEmac))
		return
	if extScanForceLegacy[0]:
		U.logger.log(20,"BT5 extended-advertising scan on {} (mac {}): disabled earlier this session (see first probe result) -> legacy scanning".format(useHCIForBeacon, myBLEmac))
		return
	supported = False
	try:
		sock.settimeout(0.8)

		def cmdComplete(ocf, params):
			"""sends one LE command and waits for its command-complete; returns
			(status, fullEvent) - status -1 on timeout. Unrelated events are skipped."""
			bluez.hci_send_cmd(sock, OGF_LE_CTL, ocf, params)
			opcode = (OGF_LE_CTL << 10) | ocf
			t0 = time.time()
			while time.time() - t0 < 1.2:
				try:	ev = bytearray(sock.recv(255))
				except Exception:	break
				if len(ev) >= 7 and ev[1] == 0x0E and (ev[4] | (ev[5] << 8)) == opcode:
					return ev[6], ev
			return -1, bytearray()

		# 1. feature bit 12 (LE Read Local Supported Features)
		st, ev = cmdComplete(0x0003, b"")
		if st == 0 and len(ev) >= 15:
			supported = bool(ev[8] & 0x10)					# feats byte1 bit4 = LE feature bit 12
		if supported:
			# 2. REALITY CHECK - live testing showed the feature bit alone means nothing:
			#    run A: params+enable status 0 but ZERO reports (the LE EVENT MASK bit 12
			#           "Extended Advertising Report" is OFF in the controller default ->
			#           it scans happily and delivers NOTHING);
			#    run B: set-params 0x0C because a previous scan state was still active.
			# So: clear the scan state, set the LE event mask OURSELVES, then require that
			# actual 0x0D reports ARRIVE before extended mode is accepted.
			cmdComplete(0x0042, struct.pack("<BBHH", 0x00, 0x00, 0x0000, 0x0000))		# clear a stuck EXTENDED scan state
			# ... and the LEGACY one. By the time this probe runs the normal scan loop has already
			# enabled legacy scanning on this very adapter, and the two command families are mutually
			# exclusive WHILE A SCAN IS ACTIVE: set-params then answers 0x00 and enable 0x0C
			# ("Command Disallowed"), which the code below reads as "adapter rejects the commands"
			# and PERSISTS - a BLE5-capable dongle was written off as legacy-only for good.
			cmdComplete(0x000C, struct.pack("<BB", 0x00, 0x00))							# LE Set Scan Enable = 0
			stM, evM = cmdComplete(0x0001, struct.pack("<Q", 0x000FFFFF))				# LE Set Event Mask: bits 0-19 incl. bit12 ext adv report
			stP, evP = cmdComplete(0x0041, struct.pack("<BBBBHH", 0x00, 0x00, 0x01, 0x01, 0x0010, 0x0010))	# ext scan params: 1M PHY, active, 100% duty
			stE, evE = cmdComplete(0x0042, struct.pack("<BBHH", 0x01, 0x00, 0x0000, 0x0000))				# ext scan enable
			if stP == 0 and stE == 0:
				# TRUSTED shortcut: a persisted positive verdict for exactly this hardware
				# (same scan mac + same full adapter mac set) skips the 2.5s proof window -
				# the setup cmds above still ran (reset wipes controller state). Any failure
				# later deletes the file, so the next start re-proves from scratch.
				if loadExtScanVerdict():
					scanExtendedMode = True
					U.logger.log(20,"BT5 extended-advertising scan on {} (mac {}): ACTIVE (trusted verdict from previous run, same adapters - delivery test skipped)".format(useHCIForBeacon, myBLEmac))
					reportBLE5("yes - active, delivery verified")
					return
				# 3. PROOF v3: compare EXTENDED vs LEGACY delivery rate on the same air.
				# The two scan command families are MUTUALLY EXCLUSIVE until an HCI
				# reset (spec: after extended cmds, legacy scan cmds return 0x0C
				# Command Disallowed - proof v2 measured "0 legacy reports" because of
				# exactly this), so each phase gets its own controller reset.
				nExt = 0
				macsExt = set()
				t0 = time.time()
				while time.time() - t0 < 4.0:
					try:	ev = bytearray(sock.recv(512))
					except Exception:	continue					# recv timeout - keep waiting for the full window
					if len(ev) > 4 and ev[1] == 0x3E and ev[3] == 0x0D:
						nExt += 1
						if len(ev) >= 14:	macsExt.add(bytes(ev[8:14]))	# ext report: mac at [8:14]
				# -- reset -> legacy phase (fresh command family) --
				subprocess.call("sudo hciconfig {} reset".format(useHCIForBeacon), shell=True)
				time.sleep(0.4)
				stLP, evLP = cmdComplete(OCF_LE_SET_SCAN_PARAMETERS, struct.pack("<BHHBB", 0x01, 0x0010, 0x0010, 0x00, 0x00))	# legacy params: active, 100% duty
				stLE, evLE = cmdComplete(OCF_LE_SET_SCAN_ENABLE, struct.pack("<BB", 0x01, 0x00))								# legacy scan on
				nLeg = 0
				macsLeg = set()
				t0 = time.time()
				while time.time() - t0 < 4.0:
					try:	ev = bytearray(sock.recv(512))
					except Exception:	continue
					if len(ev) > 4 and ev[1] == 0x3E and ev[3] == 0x02:										# legacy advertising report
						nLeg += 1
						if len(ev) >= 13:	macsLeg.add(bytes(ev[7:13]))	# legacy report: mac at [7:13]
				_uE, _uL  = len(macsExt), len(macsLeg)
				_perMinE  = 60.0 * nExt / 4.0 / max(1, _uE)
				_coverage = 100.0 * _uE / max(1, _uL)
				U.logger.log(20,"BT5 extended advertising on {}: delivery test - BLE5 mode {} report(s) from {} macs, BLE4 mode {} from {} macs (per 4s) -> {:.0f}% of the macs, {:.0f} reports per mac per minute (legacy cmd status params:0x{:02X} enable:0x{:02X})".format(
								useHCIForBeacon, nExt, _uE, nLeg, _uL, _coverage, _perMinE, stLP & 0xFF, stLE & 0xFF))
				# _uL == 0 means the BLE4 phase delivered nothing at all on this radio (BLE5-only
				# firmware): there is nothing to compare against and no alternative either, so
				# extended mode is simply the only way this radio can be used.
				if (nExt >= EXTSCAN_MIN_REPORTS and _perMinE >= EXTSCAN_MIN_PER_MIN
						and (_uL == 0 or _coverage >= EXTSCAN_MIN_COVERAGE)):
					# extended wins -> reset again and restore the full extended setup
					subprocess.call("sudo hciconfig {} reset".format(useHCIForBeacon), shell=True)
					time.sleep(0.4)
					cmdComplete(0x0001, struct.pack("<Q", 0x000FFFFF))										# LE event mask incl. bit12
					cmdComplete(0x0041, struct.pack("<BBBBHH", 0x00, 0x00, 0x01, 0x01, 0x0010, 0x0010))		# ext params
					cmdComplete(0x0042, struct.pack("<BBHH", 0x01, 0x00, 0x0000, 0x0000))					# ext scan on
					nRep = nExt
				else:
					# legacy wins - leave it RUNNING (params+enable already active)
					extScanForceLegacy[0] = True
					saveExtScanVerdict(False)
					U.logger.log(20,"BT5 extended advertising on {}: delivery test FAILED - BLE5 mode reaches {} macs ({:.0f}% of the {} heard in BLE4 mode) at {:.0f} reports per mac per minute (need {:.0f}% and {:.0f}/min) -> BLE4 scanning".format(
									useHCIForBeacon, _uE, _coverage, _uL, _perMinE, EXTSCAN_MIN_COVERAGE, EXTSCAN_MIN_PER_MIN))
					reportBLE5("no - BLE5 mode reaches only {} of {} macs".format(_uE, _uL))
					return
				if nRep > 0:
					# LEAVE the verified extended scan RUNNING - it IS the desired state
					# (mask+params set, provably delivering). The old "off again" here
					# killed scanning right after VERIFIED and nothing re-enabled it ->
					# live log: VERIFIED every cycle, zero messages in between
					scanExtendedMode = True
					U.logger.log(20,"BT5 extended-advertising scan on {} (mac {}): VERIFIED - {} extended report(s) in the probe window (eventMask status:0x{:02X}) - scan stays ON".format(useHCIForBeacon, myBLEmac, nRep, stM & 0xFF))
					reportBLE5("yes - active, delivery verified")
					saveExtScanVerdict(True)		# remember: same adapters -> no proof window next time
				else:
					cmdComplete(0x0042, struct.pack("<BBHH", 0x00, 0x00, 0x0000, 0x0000))	# off - the legacy flow enables its own scan
					extScanForceLegacy[0] = True	# cache the verdict - no 2.5s probe window on every socket setup
					saveExtScanVerdict(False)		# stale trust would mask a now-broken setup
					U.logger.log(20,"BT5 extended advertising on {} (mac {}): scan enabled OK (eventMask status:0x{:02X}) but NO extended reports arrived within 2.5s - the controller does not deliver them -> legacy scanning".format(useHCIForBeacon, myBLEmac, stM & 0xFF))
					reportBLE5("no - adapter claims BLE5 but failed the delivery test")
					return
			else:
				extScanForceLegacy[0] = True		# cache the verdict - controller rejects the commands, retrying every setup is pointless
				saveExtScanVerdict(False)
				U.logger.log(20,"BT5 extended advertising on {} (mac {}): feature bit SET but the extended scan commands are rejected (eventMask status:0x{:02X}, set-params status:0x{:02X}, enable status:0x{:02X}; 0x0C=Command Disallowed) -> legacy scanning".format(useHCIForBeacon, myBLEmac, stM & 0xFF, stP & 0xFF, stE & 0xFF))
				reportBLE5("no - adapter claims BLE5 but rejects the scan commands")
				return
	except Exception:
		U.logger.log(20,"", exc_info=True)
	if not scanExtendedMode: reportBLE5("no - no BLE5 capable adapter")
	# log the scan-mode verdict only when it CHANGES - beaconloop re-runs this on every
	# periodic BLE restart and the unchanging "not supported -> legacy" line was pure spam
	# name the RADIO: "this adapter" was useless with 3 dongles in the rpi - you could not tell
	# which one the verdict was about, nor that it concerns the SCAN radio (the extended listener
	# announces itself separately). The adapter is part of the change gate too, so swapping the
	# scan dongle re-states the verdict for the new hardware instead of staying silent.
	_scanMacNow = "{}".format(hciRoles.get("scan", {}).get("mac", "") or myBLEmac)
	if extScanLastReported[0] != (scanExtendedMode, useHCIForBeacon, _scanMacNow):
		extScanLastReported[0] = (scanExtendedMode, useHCIForBeacon, _scanMacNow)
		U.logger.log(20,"BT5 extended-advertising scan on the SCAN radio {} (mac {}): {}".format(useHCIForBeacon, _scanMacNow,
			"ACTIVE -> using extended scanning (receives Ruuvi Air E1 etc.)" if scanExtendedMode else "not supported by this adapter -> legacy scanning"))


def extAdvToLegacyHex(pkt):
	"""Converts one LE EXTENDED advertising report event (subevent 0x0D, BT5) into a list
	of LEGACY-layout hex frames (043E LL 02 01 evtype addrtype mac datalen data rssi) so
	the ENTIRE downstream pipeline (fillHCIdump, parsers, watchMAC, capture) works
	unchanged. Only COMPLETE reports are forwarded; fragmented payloads (data_status
	incomplete, only for >229-byte advs - Ruuvi Air E1 is 40 bytes) are dropped.

	Inputs:
	    pkt (bytes): raw HCI event packet starting 04 3E .. 0D
	Outputs:
	    list: legacy-layout uppercased hex strings (may be empty)
	"""
	out = []
	try:
		bb  = bytearray(pkt)
		pos = 5
		for ii in range(bb[4]):									# num_reports
			if pos + 24 > len(bb): break
			evt      = bb[pos] | (bb[pos+1] << 8)
			addrType = bb[pos+2]
			macRev   = bb[pos+3:pos+9]
			rssi     = bb[pos+13]
			dataLen  = bb[pos+23]
			data     = bb[pos+24:pos+24+dataLen]
			pos     += 24 + dataLen
			if len(data) != dataLen:		continue
			if (evt >> 5) & 0x03 != 0:		continue			# incomplete/truncated fragment
			if   evt & 0x0008:				evtLegacy = 0x04	# scan response
			elif evt & 0x0001:				evtLegacy = 0x00	# connectable ADV_IND
			else:							evtLegacy = 0x03	# non-connectable
			frame = bytearray([0x04, 0x3E, (12 + dataLen) & 0xFF, 0x02, 0x01, evtLegacy, addrType]) + macRev + bytearray([dataLen]) + data + bytearray([rssi])
			out.append("".join(["{:02X}".format(cc) for cc in frame]))
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return out


#################################
#  EXTENDED-only listener: a reserved BLE5 radio (e.g. the Barrot dongle) receives
#  BT5 extended advertisements (Ruuvi Air E1 ...) that the legacy scan radio cannot
#  hear.  ONLY extended HCI commands are ever sent to it - one legacy command would
#  lock the controller to the legacy command family and kill extended delivery.
#  Frames are converted to the legacy report layout (extAdvToLegacyHex) and merged
#  into the main message stream via extListenerQueue (deque: single producer /
#  single consumer, GIL-atomic append/popleft, no lock needed).
extListenerQueue = collections.deque()
extListenerCtl   = {"run": False, "hci": "", "thread": None, "nRx": 0}

def startExtListener(hci):
	"""(Re)starts the extended-only listener thread on the given adapter; hci=="" stops it.
	IDEMPOTENT: if a listener is already running on the SAME adapter it is left alone -
	beaconloop periodically re-runs startBlueTooth (scan refresh), and tearing the
	listener down + re-resetting the radio each time made it deliver only in the first
	minute then die (92 -> 0 -> 0)."""
	_alive = extListenerCtl["thread"] is not None and extListenerCtl["thread"].is_alive()
	if _alive and extListenerCtl.get("hci","") == hci and hci != "":
		return											# already running on this adapter - do NOT disturb it
	if _alive:											# adapter changed (or now empty) - stop the old thread
		extListenerCtl["run"] = False
		time.sleep(0.3)
	extListenerCtl["hci"] = hci
	if hci == "":
		return
	extListenerCtl["run"]    = True
	extListenerCtl["thread"] = threading.Thread(name="extListener", target=execExtListener, args=(hci,))
	extListenerCtl["thread"].daemon = True
	extListenerCtl["thread"].start()
	U.logger.log(20, "extended-only listener started on {} (BLE5 frames: Ruuvi Air E1 etc.)".format(hci))

def execExtListener(hci):
	"""Reader loop for the extended-only radio: extended scan setup, receive 0x0D
	reports, convert to legacy layout, queue for the main loop.  Silence does NOT
	trigger any self-restart - the dropouts that used to justify one were a radio-role
	collision (BLEconnect on this dongle), fixed by the strict role split; and silence
	is normal when no extended advertiser is in range.  A 60 s heartbeat logs the report
	rate so a dead radio is still visible.  A pulled/replugged dongle is survived: the radio
	is re-resolved BY MAC each pass (it can come back as a different hciN) and the listener
	keeps retrying for ~1 h before deferring to the next bluetooth restart."""
	devId = int(hci.replace("hci", ""))
	extMac = "{}".format(hciRoles.get("extListener", {}).get("mac", "")).upper()
	failInARow = 0
	wasDown    = False			# True once the radio dropped, so the re-open can announce itself
	announced  = False			# the FIRST successful setup says so - see the note at the success block
	while extListenerCtl["run"]:
		sock = None
		try:
			# A USB dongle that was unplugged comes back under a DIFFERENT hci number
			# (live-seen: hci2 -> hci3).  Our role is published with the MAC, so re-resolve
			# the current hciN for that mac on every pass instead of clinging to the old name.
			macIsPresent = False
			if extMac != "":
				try:
					_nowHCIs = U.whichHCI().get("hci", {})
					for _hh in _nowHCIs:
						if "{}".format(_nowHCIs[_hh].get("BLEmac", "")).upper() == extMac:
							macIsPresent = True
							if _hh != hci:
								U.logger.log(20, "extListener: radio {} re-appeared as {} (mac {}) - following it".format(hci, _hh, extMac))
								hci   = _hh
								devId = int(hci.replace("hci", ""))
								extListenerCtl["hci"] = hci
								hciRoles["extListener"]["hci"] = hci
								try:	writeBeaconloopHci()		# BLEconnect reads the FILE - keep it in step
								except Exception:	pass
							break
					# DONGLE SWAPPED WHILE WE WERE RUNNING: our mac is nowhere, but the hciN we hold
					# is UP with a DIFFERENT mac - live-seen when the BLE5 dongle is pulled and the
					# replacement goes into the same port, it comes back as the same hci2 with a new
					# BD address. hci_open_dev(devId) then simply SUCCEEDS, so failInARow stays 0:
					# neither the "mac has not re-appeared" exit below (needs failInARow >= 6) nor
					# checkExtListenerAlive (only runs once this thread DIED) ever notices. The
					# listener then reports "RADIO IS BACK" and keeps going on a radio it never
					# vetted, while beaconloop.hci still publishes the OLD mac - and beep/BLEconnect
					# exclude this radio BY that mac. So identify the swap here, by mac, and say so.
					_macHere = "{}".format(_nowHCIs.get(hci, {}).get("BLEmac", "")).upper()
					if (not macIsPresent) and _macHere not in ("", "0") and _macHere != extMac and _nowHCIs.get(hci, {}).get("upDown", "") == "UP":
						_taken = ["{}".format(hciRoles.get(_r, {}).get("hci", "")) for _r in ("scan", "broadcast", "BLEconnect")]
						if hci in _taken:
							# the roles were re-assigned around us - do not fight over the radio
							U.logger.log(20, "extListener {}: BLE5 radio REPLACED (mac {} -> {}) and {} now holds another role - exiting, checkExtListenerAlive adopts a free BLE5 radio".format(hci, extMac, _macHere, hci))
							return
						if not _nowHCIs.get(hci, {}).get("extAdv", False):
							# a non-BLE5 dongle in that port cannot do extended scanning at all: the
							# ext-scan commands would be accepted and deliver 0 reports/min forever.
							# Keep the role record pointing at the OLD mac on purpose - that is what
							# lets checkExtListenerAlive adopt a proper BLE5 dongle once one is back.
							U.logger.log(20, "extListener {}: BLE5 radio REPLACED (mac {} -> {}) but the new radio has NO BT5 extended advertising - exiting, no extended/E1 reception until a BLE5 dongle is plugged in".format(hci, extMac, _macHere))
							return
						U.logger.log(20, "extListener {}: BLE5 radio REPLACED - mac {} -> {}, new radio is BLE5 capable - adopting it for the extended-listener role".format(hci, extMac, _macHere))
						extMac       = _macHere
						macIsPresent = True
						hciRoles["extListener"]["hci"] = hci
						hciRoles["extListener"]["mac"] = extMac
						hciRoles["extListener"]["bus"] = "{}".format(_nowHCIs.get(hci, {}).get("bus", ""))
						try:	writeBeaconloopHci()			# beep/BLEconnect exclude us BY mac - publish the NEW one
						except Exception:	pass
						sendBLE5State()						# must name the NEW dongle, not the pulled one
				except Exception:	pass
			# HARD reset the adapter FIRST - beaconloop startup only reset the scan
			# radio, so this dongle may carry a stuck/previous scan state that makes
			# the ext-scan commands return 0x0C (Command Disallowed) and deliver ZERO
			# reports.  scanRateTest proved a reset before the ext commands works.
			# >/dev/null: on a vanished adapter hciconfig prints "Can't get device info:
			# No such device" to the console on every retry - the log line below says it once.
			subprocess.call("sudo hciconfig {} reset > /dev/null 2>&1".format(hci), shell=True)
			time.sleep(0.4)
			subprocess.call("sudo hciconfig {} up > /dev/null 2>&1".format(hci), shell=True)
			time.sleep(0.4)
			if not macIsPresent and extMac != "" and failInARow >= 6:
				# ~30 s and our own mac has not shown up once: the dongle was swapped for a
				# different one (new mac) or removed for good. Waiting the full 2 min helps
				# nobody - exit and let checkExtListenerAlive adopt a free BLE5 radio.
				U.logger.log(20, "extListener: radio {} has not re-appeared - exiting so a replacement BLE5 radio can be adopted".format(extMac))
				return
			try:
				sock = bluez.hci_open_dev(devId)
			except Exception:
				# adapter not present (dongle pulled, or still re-enumerating after a replug).
				# NOT a reason to kill the listener for good - keep retrying slowly; the
				# mac-based re-resolve above picks it up again under whatever hciN it returns as.
				failInARow += 1
				if failInARow % 4 == 1:
					U.logger.log(20, "extListener {}: devId{} not present - waiting for the radio to come back (try {})".format(hci, devId, failInARow))
				if failInARow > 24:					# ~2 min at 5 s - then exit; the main loop revives us, see checkExtListenerAlive
					U.logger.log(20, "extListener: radio {} absent for ~2 min - exiting, main loop will retry".format(extMac or hci))
					return
				time.sleep(5)
				continue
		
			flt  = bluez.hci_filter_new()
			bluez.hci_filter_all_events(flt)
			bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
			sock.setsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, padHCIfilter(flt))
			sock.settimeout(2.0)
			# EXTENDED commands only - never legacy on this adapter.
			# order matches the proven probeExtendedScan sequence: event mask FIRST
			# (bit12 ext-adv-report is OFF by default -> scanning delivers nothing),
			# then CLEAR any active scan, then params, then enable.
			# hci_open_dev can SUCCEED on a stale device node while the radio is already
			# gone - the send then fails with OSError [Errno 100] Network is down. That is
			# an absent adapter, not a bug: retry quietly instead of dumping a traceback.
			try:
				bluez.hci_send_cmd(sock, OGF_LE_CTL, 0x0001, struct.pack("<Q", 0x000FFFFF))	# LE event mask incl. bit12 ext adv report
				time.sleep(0.05)
				bluez.hci_send_cmd(sock, OGF_LE_CTL, 0x0042, struct.pack("<BBHH", 0x00, 0x00, 0x0000, 0x0000))				# ext scan DISABLE (clear stuck state)
				time.sleep(0.05)
				bluez.hci_send_cmd(sock, OGF_LE_CTL, 0x0041, struct.pack("<BBBBHH", 0x00, 0x00, 0x01, 0x01, 0x0010, 0x0010))	# ext scan params: 1M PHY, active, 100% duty
				time.sleep(0.05)
				bluez.hci_send_cmd(sock, OGF_LE_CTL, 0x0042, struct.pack("<BBHH", 0x01, 0x00, 0x0000, 0x0000))				# ext scan enable
			except (pySocket.error, OSError, IOError) as e:
				failInARow += 1
				if failInARow % 4 == 1:
					U.logger.log(20, "extListener {}: radio not ready for ext-scan setup ({}) - waiting for it to come back (try {})".format(hci, e, failInARow))
				if failInARow > 24:					# ~2 min at 5 s, same as the open-fail path
					U.logger.log(20, "extListener: radio {} absent ~2 min - exiting, main loop retries".format(extMac or hci))
					return
				time.sleep(5)
				continue
			# FIRST successful setup: announce it. probeExtendedScan logs the SCAN adapter's
			# verdict ("not supported -> legacy scanning") but nothing ever confirmed the other
			# half - the extended LISTENER coming up was completely silent, so a working BLE5
			# setup read exactly like an rpi without any BLE5 radio. The two lines are not
			# contradictory: the scan radio does legacy, this one does extended, by design.
			if not announced:
				announced = True
				U.logger.log(20, "BT5 extended-advertising scan: ACTIVE on the extended-listener radio {} (mac {}) - extended/E1 reports enabled (scan radio {} stays legacy, by design)".format(hci, extMac or "?", useHCIForBeacon))
				sendBLE5State()					# now provably delivering -> publish it as the "scan5" radio
			# setup went through -> the radio is (back) and extended scanning is live.
			# Say so explicitly: without this a recovery is invisible, the log just stops
			# printing "waiting for the radio" and you cannot tell recovered from dead.
			if failInARow > 0 or wasDown:
				# wasDown covers the fast case: the radio was already back by the time we
				# re-resolved it, so there were no failed tries - without this the recovery
				# is silent and only the "following it" line hints that anything happened.
				# the mac is part of the message: after a dongle swap "RADIO IS BACK" alone
				# reads as if the SAME hardware returned - it does not have to be
				if failInARow > 0:
					U.logger.log(20, "extListener {}: RADIO IS BACK (mac {}) - extended scanning re-enabled after {} failed tr{} (~{} s down)".format(hci, extMac or "?", failInARow, "y" if failInARow == 1 else "ies", failInARow*5))
				else:
					U.logger.log(20, "extListener {}: RADIO IS BACK (mac {}) - extended scanning re-enabled (came back immediately)".format(hci, extMac or "?"))
				failInARow = 0
				wasDown    = False
			lastRx        = time.time()
			lastHeartbeat = time.time()
			nRxAtLast     = extListenerCtl["nRx"]
			macsSeen      = set()
			zeroStreak    = 0
			while extListenerCtl["run"]:
				try:
					pkt = sock.recv(512)
				except pySocket.timeout:
					pkt = None			# NORMAL: no extended adv within the read timeout - see the note below
				except (pySocket.error, OSError, IOError) as e:
					# the adapter went away under us - unplugged dongle gives
					# BrokenPipeError [Errno 32], a usb re-enumeration gives ENODEV.
					# Not a code fault: leave the read loop and let the outer loop
					# re-resolve the radio by mac and re-open it.  (py2-safe: never
					# name BrokenPipeError, it does not exist there.)
					U.logger.log(20, "extListener {}: socket closed by the system ({}) - radio removed? re-opening".format(hci, e))
					wasDown = True
					break
				if pkt is None:
					# NO silence watchdog here on purpose. The ~50 s extended-listener dropouts
					# that the old 20 s re-assert / 40 s hciconfig-reset ladder chased were NOT
					# a controller problem: BLEconnect was picking this same BLE5 dongle instead
					# of obeying the master role assignment in beaconloop.hci, and its connect
					# commands knocked the extended scan back to legacy. Fixed 2026-07-29 (roles
					# are strictly separated now - scan+broadcast on the external dongle,
					# BLEconnect on the internal, this radio does extended ONLY).
					# Silence is also the NORMAL state whenever no extended advertiser (Ruuvi
					# Air) is in range, and the ladder could not tell the two apart - it reset
					# the dongle every 40 s forever, which makes a Barrot deliver one burst and
					# die. The 60 s heartbeat below still LOGS a silent radio, so a real failure
					# stays visible without anything restarting itself.
					pkt = None
				if pkt is not None:
					hdr = bytearray(pkt[:4])
					if len(hdr) == 4 and hdr[1] == 0x3E and hdr[3] == 0x0D:
						lastRx = time.time()
						for msg in extAdvToLegacyHex(pkt):
							extListenerQueue.append(msg)
							try:
								# legacy-layout hex: 043E LL 02 01 evt addrtype MAC(12 hex, reversed) ...
								# -> the mac is at hex chars 14:26, byte-reversed
								_rev = msg[14:26]
								macsSeen.add(":".join(_rev[i:i+2] for i in range(10, -2, -2)))
							except Exception:	pass
						extListenerCtl["nRx"] += 1
				# heartbeat every 60 s: prove the BLE5 radio is actually delivering
				if time.time() - lastHeartbeat >= 60:
					got = extListenerCtl["nRx"] - nRxAtLast
					if _debugheartbeat: U.logger.log(20, "extListener {}: {} extended report(s)/min from {} mac(s): {}".format(hci, got, len(macsSeen), ",".join(sorted(macsSeen))))
					if got == 0:
						zeroStreak += 1				# logged only - no self-restart, see the note above
					else:
						zeroStreak = 0
					lastHeartbeat = time.time()
					nRxAtLast     = extListenerCtl["nRx"]
					macsSeen      = set()
			failInARow = 0
		except Exception as e:
			failInARow += 1
			U.logger.log(20, "", exc_info=True)
			if failInARow > 24:					# ~2 min at 5 s, same as the absent-radio paths
				U.logger.log(20, "extListener {}: too many errors - exiting, main loop retries".format(hci))
				return
			time.sleep(5)
		finally:
			try:
				if sock is not None:
					bluez.hci_send_cmd(sock, OGF_LE_CTL, 0x0042, struct.pack("<BBHH", 0x00, 0x00, 0x0000, 0x0000))
					sock.close()
			except Exception:
				pass
	return


def reopenScanSocket(err):
	"""ONE in-place recovery attempt for the scan socket before the (proven, but heavy) full
	restart.  A pulled or hiccuping USB dongle makes sock.recv raise BrokenPipe [Errno 32] /
	ENODEV, and restartMyself then rebuilds the whole program (~5 s, new process, all collected
	beacon state lost).  When the SAME scan radio is back on the SAME hciN only the SOCKET is
	stale - re-open it and keep the loop running.

	Deliberately NOT handled here (they still take the restart route, which is the correct
	recovery): a REPLACED dongle (different mac) and a radio that came back as a different hciN -
	only startBlueTooth can re-pin the radio, re-derive the roles and the rpi identity mac (the
	broadcast radio's mac = piMAC) consistently.

	Inputs:
	    err (Exception): the socket error that triggered this attempt, for the log line
	Outputs:
	    bool: True = socket rebuilt, caller can carry on; False = let the caller restart
	"""
	global currentBLESocket
	try:
		if rpiDataAcquistionmethod != "socket":				return False
		scanMac = "{}".format(hciRoles.get("scan", {}).get("mac", "")).upper()
		if scanMac == "":									return False
		if tryDeltaTime(lastScanSocketReopen[0]) < 20:		# just tried - do not sit in a re-open loop
			U.logger.log(20, "scan socket error again within 20 s ({}) - not retrying, full restart".format(err))
			return False
		# GRACE WINDOW: a replug (or a controller/USB hiccup) needs a few seconds to re-enumerate,
		# so poll instead of deciding after a single look - one check at 1 s declared a dongle dead
		# that was about to come back. A dongle that stays OUT costs the full window before the
		# restart, which is nothing next to the restart itself.
		macHere = ""
		for _try in range(SCAN_REOPEN_WAIT):
			time.sleep(1.0)
			macHere = "{}".format(U.whichHCI().get("hci", {}).get(useHCIForBeacon, {}).get("BLEmac", "")).upper()
			if macHere == scanMac:	break
		if macHere != scanMac:
			U.logger.log(20, "scan socket error ({}) - scan radio {} did NOT come back on {} within {} s (found:{}) - full restart re-selects the radio".format(err, scanMac, useHCIForBeacon, SCAN_REOPEN_WAIT, macHere if macHere not in ("", "0") else "nothing"))
			return False
		lastScanSocketReopen[0] = time.time()
		readPopen("sudo /bin/hciconfig {} up".format(useHCIForBeacon))
		time.sleep(0.3)
		try:
			if currentBLESocket is not None: currentBLESocket.close()
		except Exception:	pass
		currentBLESocket = bluez.hci_open_dev(int("0" + useHCIForBeacon.replace("hci", "")))
		setupSOCKET(currentBLESocket)						# event filter + recv timeout + extended-mode probe
		hci_le_set_scan_parameters(currentBLESocket)		# params BEFORE enable: the radio came up at its defaults (PASSIVE)
		time.sleep(0.05)
		hci_enable_le_scan(currentBLESocket)
		scanSocketRebuilt[0] = True							# main loop swaps the new socket in
		U.logger.log(20, "scan socket error ({}) - radio {} still on {}: socket RE-OPENED in place, scanning resumed without a restart".format(err, scanMac, useHCIForBeacon))
		return True
	except Exception:
		U.logger.log(20, "in-place scan-socket re-open failed - falling back to the full restart", exc_info=True)
		try:
			if currentBLESocket is not None: currentBLESocket.close()
		except Exception:	pass
		currentBLESocket     = None							# never hand a half-built socket to the main loop
		scanSocketRebuilt[0] = False
		return False


def getSocketData(sock):
	"""Receives one BLE HCI packet from the given socket and returns it as a single-element list of uppercased hex strings; on error it tries ONE in-place socket re-open (reopenScanSocket) and only restarts the plugin when that is not the right recovery. Extended advertising reports (BT5) are converted to the legacy layout.

	Inputs:
	    sock (bluetooth socket): Bluez HCI socket to read raw packets from
	Outputs:
	    list: List of uppercased hex-string messages, or empty list on error
	"""
	Msgs = []
	try:
		pkt = sock.recv(512)
		hdr = bytearray(pkt[:4])
		if scanExtendedMode and len(hdr) == 4 and hdr[1] == 0x3E and hdr[3] == 0x0D:
			Msgs = extAdvToLegacyHex(pkt)
		else:
			Msgs = [(stringFromPacket(pkt)).upper()]
	except pySocket.timeout:
		return []					# quiet period, no packet within SOCKET_RECV_TIMEOUT; watchdog in main loop handles recovery
	except Exception as e:
		for ii in range(10):
			if os.path.isfile(G.homeDir+"temp/stopBLE"):
				U.logger.log(20,  "stopBLE is present, waiting for it to disappear")
				time.sleep(5)
			else:
				break
		if os.path.isfile(G.homeDir+"temp/stopBLE"):
			U.removeFile("{}temp/stopBLE".format(G.homeDir))

		# TRY ONCE MORE first: same radio, same hciN -> only the socket is stale, re-open it and
		# keep collecting instead of throwing the whole process away (see reopenScanSocket).
		# The traceback is logged only when we really do restart - an unplugged dongle is not a
		# code fault and its BrokenPipe traceback made every hardware test look like a crash.
		if reopenScanSocket("{}: {}".format(type(e).__name__, e)):
			return []

		# a socket-level error IS the pulled dongle (BrokenPipe/ENODEV/ENETDOWN) and reopenScanSocket
		# has just logged the radio state - the traceback added nothing but made every dongle test
		# look like a crash. Anything else is a real fault and still gets the full trace.
		# (py2-safe: never name BrokenPipeError, it does not exist there - OSError covers it on py3.)
		if isinstance(e, (pySocket.error, OSError, IOError)):
			U.logger.log(20,"scan socket unusable ({}: {}) - restarting beaconloop to re-select the radio".format(type(e).__name__, e))
		else:
			U.logger.log(20,"", exc_info=True)
		time.sleep(1)
		U.restartMyself(param="", reason="sock.recv error", python3=usePython3)
		return []

	# drain everything else the kernel has buffered -> batch like the hcidump method,
	# otherwise the paced main loop reads only ~1 pkt / 0.05-0.15 secs and packets get dropped
	try:
		sock.setblocking(False)
		for ii in range(500):
			try:	pkt = sock.recv(512)
			except:	break
			hdr = bytearray(pkt[:4])
			if scanExtendedMode and len(hdr) == 4 and hdr[1] == 0x3E and hdr[3] == 0x0D:
				Msgs.extend(extAdvToLegacyHex(pkt))
			else:
				Msgs.append((stringFromPacket(pkt)).upper())
	except Exception:
		pass
	finally:
		try:	sock.settimeout(SOCKET_RECV_TIMEOUT)
		except:	pass
	return Msgs

def padHCIfilter(flt):
	"""Pads an HCI socket filter to 16 bytes. sizeof(struct hci_ufilter) is 16 (14 data
	bytes + 2 u32-alignment padding); kernels with the 2024 setsockopt-validation fix
	(>= 6.1.91 / 6.6.30, e.g. updated bookworm) reject shorter buffers with EINVAL -
	pybluez and old getsockopt results are 14 bytes. Old kernels accept 16 identically."""
	bb = bytes(flt)
	if len(bb) < 16: bb += b"\x00" * (16 - len(bb))
	return bb


def setupSOCKET(sock):
	"""Configures a Bluez HCI socket with an all-events filter for HCI event packets and a 12-second timeout, returning the previous filter so it can be restored later.

	Inputs:
	    sock (bluetooth socket): Bluez HCI socket to configure
	Outputs:
	    bytes: The socket's previous HCI_FILTER option value
	"""
	old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

	# perform a device inquiry on bluetooth device #0
	# The inquiry should last 8 * 1.28 = 10.24 seconds
	# before the inquiry is performed, bluez should flush its cache of
	# previously discovered devices
	flt = bluez.hci_filter_new()
	bluez.hci_filter_all_events(flt)
	bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
	sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, padHCIfilter(flt) )
	probeExtendedScan(sock)			# BT5 extended advertising supported? -> extended scan cmds
	sock.settimeout(SOCKET_RECV_TIMEOUT)
	return old_filter


def setBeaconLastMsgTS(mac, setBy=""):
	"""Records the current time as the last-received-message timestamp for the given beacon MAC and logs the event if that MAC is being tracked.

	Inputs:
	    mac (str): Beacon MAC address key
	    setBy (str): Caller/reason label for logging; defaults to empty
	Outputs:
	    None: Updates the beaconLastMessageTS dict and may log
	"""

	beaconLastMessageTS[mac] = time.time()
	if  (mac == trackMac or trackMac =="*") and logCountTrackMac > 0:
		U.logger.log(20, "mac:{} set  beaconLastMessageTS by:{}" .format(mac, setBy))


def setBeaconLastMsgSendTS(mac, setBy=""):
	"""Records the current time as the last-message-sent timestamp for the given beacon MAC and logs the event if that MAC is being tracked.

	Inputs:
	    mac (str): Beacon MAC address key
	    setBy (str): Caller/reason label for logging; defaults to empty
	Outputs:
	    None: Updates the beaconLastMessageSendTS dict and may log
	"""

	beaconLastMessageSendTS[mac] = time.time()
	if  (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
		U.logger.log(20, "mac:{} set  beaconLastMessageSendTS by:{}" .format(mac, setBy))




####### main pgm / loop through package set  ############
def loopThroughMessagesInThisSet(Msgs, timeAtLoopStart, sendAfter, tt):
	"""Iterates over a batch of raw BLE advertisement hex messages, parsing each into MAC/RSSI/TxPower, filtering and accepting/rejecting beacons and sensors per configured rules, handling sensor data and battery levels, and updating tracking timestamps and stats; signals a restart if junk-length data is seen.

	Inputs:
	    Msgs (list): List of raw BLE advertisement hex strings
	    timeAtLoopStart (float): Epoch time when the collection loop started
	    sendAfter (float): Seconds after which to stop collecting and send
	    tt (float): Current epoch time used for the send-timeout comparison
	Outputs:
	    bool: True to request a restart (junk-length message), else False
	"""
	global lastMSGwithDataPlain, nMessagesSend, lastMessageOK, lastMessageRead, lastMSGwithDataPassed, lastTimeMAC

	messageBad  = False
	nJunkFrames = 0
	for hexstr in Msgs:
		try:
			if tt - timeAtLoopStart	 > sendAfter: 
				#U.logger.log(20,  "dt inner :{:.1f} limit:{},  ".format(tt - timeAtLoopStart, sendAfter))
				break # send curl msgs after collecting for xx seconds
			hexstr = fillHCIdump(hexstr)
			nCharThisMessage	= len(hexstr)
			#dtinner[4][1] = max(dtinner[1], tryDeltaTime( startofInnerLoop, oneDigit=True ))
	
			lastMessageRead = hexstr
			# junk-length frames (e.g. a 7-byte command-complete event of our own scan
			# re-enable -> empty string after the preamble strip, or an oversized fragment)
			# are SKIPPED: a single one must not abort the set and fire the restart ladder;
			# only a stream with nothing but junk is really broken
			# legacy: max 31 bytes + preamble; extended advs (main scan OR the dedicated
			# extended listener radio) are longer - use the big limit if EITHER delivers
			# extended frames, else the oversized Ruuvi Air E1 (48-byte, ~126 hex) frames
			# from the listener get dropped here as "junk-length"
			if nCharThisMessage < 16 or nCharThisMessage > (510 if (scanExtendedMode or extListenerCtl.get("hci","")) else 110):
				nJunkFrames += 1
				if nJunkFrames > 20 and nMsgs == 0:	return True
				continue
	
			lastMessageOK = hexstr
	
			#dtinner[4][2] = max(dtinner[2], tryDeltaTime( startofInnerLoop, oneDigit=True ))
			lastMSGwithDataPlain = time.time()


			rssi, txPower, macplainReverse, macplain, mac  = getStdIbeacon(hexstr)

			doPrint =  mac in findMAC

			if False and doPrint : #or mac in findMAC: 
				U.logger.log(20,  "mac:{:}, hexstr:{:}".format(mac,  hexstr[12:]))

			if mac not in parsedData:
				parsedData[mac] = {}
			if  mac in BLEsensorMACs and mac in findMAC:
				U.logger.log(20,  "mac:{:}, BLEsensorMACs:{},".format(mac, BLEsensorMACs[mac]))

			# parse (decode name/mfg/sensor sections) for every ACCEPTED message - sensors and known
			# beacons always, plus any that new-beacon acceptance would take. This EXACTLY mirrors the
			# reject test below (a message is parsed iff it is not rejected), so only unknown beacons
			# with acceptance OFF are skipped - which stops the "bad string" noise the old always-true
			# "acceptNewiBeacons > -200" (true for the 999 = off sentinel) produced.
			if mac in BLEsensorMACs or mac in onlyTheseMAC or rssi > acceptNewBeaconsMinSIgnal or acceptNewBeaconMAC != "" or acceptNewTagiBeacons != "off" or acceptNewMFGNameBeacons not in ["","off"]:
				try:  parsePackage(mac, hexstr[12:], logData=False)
				except: continue


			setBeaconLastMsgTS(mac, "received")

			if mac in findMAC: #== trackMacNumber:# or mac in findMAC:
				U.logger.log(20,  "mac:{:}, DT:{:4.1f}, new data: rssi:{}>{}?, hexstr:{:}\n".format(mac, tryDeltaTime(lastTimeMAC), rssi, ignoreBeaconsIfRssiLessThan, hexstr[12:]))
				lastTimeMAC = time.time()

			if readFrom != "":
				U.logger.log(20, "mac:{}, data:{}".format(mac, hexstr[12:]))

			########  track mac  start / end ############
			trackMacStopIf(hexstr, mac)
			#dtinner[4][2] = max(dtinner[2], tryDeltaTime( startofInnerLoop,oneDigit=True ))

			# check if this is a sensor, will send its own msg to mac, and will return battery level if present 
			sensor = ""
			batteryLevel = ""

			# do sensor macs BEFORE the rssi gate - sensor data (contact open/close,
			# temp, ...) matters regardless of signal strength; the rssi filter below
			# only applies to presence-beacon logic.  (The old order dropped weak
			# sensor packets and made e.g. SwitchBot contacts miss most frames.)
			if mac  in BLEsensorMACs:
				sensor, txPower, batteryLevel = doSensors( mac, macplain, macplainReverse, rssi, txPower, hexstr)

			if rssi < ignoreBeaconsIfRssiLessThan: continue

			if (mac == trackMac or trackMac =="*") and logCountTrackMac >0:
				writeTrackMac("basic   ","  RX :{}, TX: {}".format( rssi, txPower) ,mac)

			if sensor != "": nMessagesSend +=1
			# check if known rejected mac
			if mac in ignoreMAC: 
				if readFrom !="":
					U.logger.log(20, "TestMode: ignored mac:{}".format(mac))
				continue # set to ignore in plugin

			if  not (mac in onlyTheseMAC): 
				# 		accept if rssi				accept spec mac				accept tag							accept mfg tag			if one is tru do not skip	
				if not ( rssi > acceptNewBeaconsMinSIgnal or  acceptNewBeaconMAC != "" or  acceptNewTagiBeacons != "off" or  acceptNewMFGNameBeacons not in ["","off"] ):
				#U.logger.log(20,  "{} {:.1f}  mac:{:}, rejecting {} {} {} {} {} {}".format( datetime.datetime.now().strftime("%H:%M:%S.%f")[:-5], tryDeltaTime( lastTimeMAC), mac,  mac not in onlyTheseMAC, rssi < acceptNewBeaconsMinSIgnal,  acceptNewBeaconMAC == "",  acceptNewTagiBeacons == "off", acceptNewMFGNameBeacons in ["","off"],  mac  not in BLEsensorMACs))
					continue

			rejectMac, sendNow = checkIfTagged(mac, macplain, macplainReverse, hexstr, batteryLevel, rssi, txPower)
	
			if rejectMac == "reject": 
				setBeaconLastMsgTS(mac, "reject")
				continue
	
			if mac in findMAC: #== trackMacNumber:# or mac in findMAC:
				U.logger.log(20,  "mac:{:}, pass reject".format(mac))


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
				if sendNow:
					setBeaconLastMsgTS(mac, "sendNow")
					continue

			if  (mac == trackMac or trackMac =="*") and logCountTrackMac > 0:
				writeTrackMac("Accpt   ", "{}".format(beaconsThisReadCycle[mac]) ,mac)

			setBeaconLastMsgTS(mac, "loop")

		except Exception :
			U.logger.log(20,"", exc_info=True)
			continue

	return  False	



####### main pgm / loop ############

def execbeaconloop(test):
	"""Main entry point for the BLE beacon loop process: initializes all global state and config defaults, sets up BLE service-section maps, kills stale Bluetooth processes, reads parameters and history, restores prior HCI settings, and runs the continuous beacon scan/processing loop.

	Inputs:
	    test (str): 'normal' for live operation, otherwise a test source to read from
	Outputs:
	    None: Runs the long-lived beacon loop; sets globals, manages processes and may restart/reboot
	"""
	global sendAfterSeconds, sendAfterSecsOfLastMsg, deleteHistoryAfterSeconds
	global onlyTheseMAC, enableiBeacons, minSignalOff, minSignalOn
	global acceptNewBeaconsMinSIgnal, acceptNewBeaconMAC, acceptNewTagiBeacons, acceptNewMFGNameBeacons
	global myBLEmac, BLEsensorMACs
	global oldRaw,	lastRead
	global mapReasonToText
	global downCount, beaconsOnline, logCountTrackMac, trackMac, startTimeTrackMac, trackMacText
	global rpiDataAcquistionmethod
	global readBufferSize
	global readbuffer
	global ListenProcessFileHandle
	global lastLESCANrestart
	global beaconsThisReadCycle
	global reasonMax 
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
	global sensCheckLastTime, paramCheckLastTime, hciCheckLastTime, hciAvailableForBeep, useHCIForBeep, useHCIForBeacon
	global beepBatteryBusy, startTimeOfBeaconloop
	global ignoreBeaconsIfRssiLessThan
	global parsedData
	global beaconLastMessageTS
	global beaconLastMessageSendTS
	global outLast
	global dataFromSensors, waitforcheckIfDelaySend
	global lastMSGwithGoodData, lastMSGwithDataPlain, nMessagesSend, nMsgs, lastMessageOK, lastMessageRead, lastMSGwithDataPassed, lastTimeMAC, messageStats, clearmessageStats
	global readFrom
	global initSensor
	
	
	initSensor				= {}
	readFrom				= ""
	clearmessageStats		= [0,0,0,0,0,0,0,0,0,0,0,0]
	messageStats			= {"numberOfMessagesperRead":copy.copy(clearmessageStats),"countTotal":0}
	messageStats["max"]		= len(messageStats["numberOfMessagesperRead"])
	waitforcheckIfDelaySend = False
	dataFromSensors			= {}
	#extraStates 			= ["calibrated","position","light","mode","onOffState", "mfg_info","iBeacon","batteryLevel","subtypeOfBeacon","TLMenabled","inMotion","allowsConnection","analyzed"]
	extraStates 			= ["calibrated","position","light","mode","onOffState", "mfg_info","batteryLevel","subtypeOfBeacon","TLMenabled","inMotion","allowsConnection","analyzed"]
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
	lastLESCANrestart		= 0
	ListenProcessFileHandle =""
	readbuffer				= ""
	readBufferSize			= 4096*8
	rpiDataAcquistionmethod	= ""
	acceptNewTagiBeacons 	= ""
	acceptNewBeaconMAC		= ""
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
	acceptNewBeaconsMinSIgnal		= 999
	enableiBeacons			= "1"
	G.authentication		= "digest"
	# get params
	onlyTheseMAC			= {}
	ignoreMAC				= []
	batteryLevelUUID		= {}
	myBLEmac				= ""
	sensor					= G.program	 



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
		#"10":"SecurityManagerTKValue",
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
	U.logger.log(20,"======= starting beaconloop v:{}".format(VERSION))
	if bluezPresent:	U.logger.log(20,"data acquisition method:{};  socket backend:{}".format(rpiDataAcquistionmethod, getattr(bluez, "__name__", "?")))
	else:				U.logger.log(20,"data acquisition method:{};  NO socket backend available (pybluez/hciRawSocket not importable) -> hcidump".format(rpiDataAcquistionmethod))
	U.killOldPgm(-1,"hcidump")
	U.killOldPgm(-1,"hcitool")
	U.killOldPgm(-1,"lescan")


	U.echoLastAlive(G.program)

	fixOldNames()

	# getIp address 
	if U.getIPNumber() > 0:
		U.logger.log(20, " no ip number ")
		time.sleep(10)
		return

	# get history
	readbeacon_ExistingHistory()

	# try to reuse last settings, if not new bus set in parameters
	hciBeaconloopUsed, raw  = U.readJson("{}beaconloop.hci".format(G.homeDir))
	# role format {"scan":{mac,hci,bus,..},..}; old flat format {"usedHCI","myBLEmac","usedBus"} still read
	if hciBeaconloopUsed != {}:
		sc          = hciBeaconloopUsed.get("scan", {})
		trymyBLEmac = sc.get("mac", hciBeaconloopUsed.get("myBLEmac",""))
		thisHCI     = sc.get("hci", hciBeaconloopUsed.get("usedHCI",""))
		usedBus     = sc.get("bus", hciBeaconloopUsed.get("usedBus",""))
	else:
		trymyBLEmac = ""
		thisHCI = ""
		usedBus = ""
	# nothing invalidates the pinned dongle any more - the bus restriction this used to check
	# (BeaconUseHCINo UART/USB) is gone; roles come from the auto pick / the per-channel pins.


	## start bluetooth
	for ii in range(5):
		sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber, thisHCI=thisHCI, trymyBLEmac=trymyBLEmac)  
		if retCode == 0: break 
		time.sleep(3)
	if retCode != 0: 
		U.logger.log(20,"beaconloop exit, recode from getting BLE stack >0, after 3 tries:")
		return

 

	if rpiDataAcquistionmethod.find("hcidump") == 0:
		retCode = startHCUIDUMPlistnr(useHCIForBeacon)
		if retCode != "":
			U.logger.log(20,"beaconloop exit, === error in starting HCIdump listener, exit beaconloop ===")
			return

	U.logger.log(20,"using >{}< for data read method testMode:>{}< ".format(rpiDataAcquistionmethod, readFrom!=""))
	
	loopCount				= 0
	paramCheckLastTime		= time.time() + 10
	sensCheckLastTime 		= time.time() + 1
	hciCheckLastTime		= time.time() + 0
	checkIPConnection		= time.time()

	U.echoLastAlive(G.program)
	G.tStart				= time.time()
	beaconsThisReadCycle	= {}
	trackMac				= ""
	bleRestartCounter 		= 0
	eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()
	##print "beaconloop", eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled
	nEmptyMessagesInARow 	 = 0
	lastMSGwithDataPlain 	= time.time()
	lastMSGwithDataPassed 	= time.time()
	maxLoopCount			= 6000
	restartCount			= 0
	logCountTrackMac 		= -10 
	nMsgs					= 0
	restartBLE 				= time.time()
	nMsgs					= 0
	zeroInARow 				= 0
	zeroInARowMax			= 6
	lastmsg    				= time.time() + 5
	lastmsgMaxDelta			= 3
	stackrestartcount		= 0
	dtinner = [0,0,0,0,0,0,0,0,0,0]
	lastMSGwithGoodData = time.time()
	startTimeOfBeaconloop = time.time()
	lastTimeMAC = time.time()
	
	startHCIcmdThread()

	lastMessageOK = ""
	lastMessageRead = ""

	trackMacNumber	=  "xxE9:54:00:00:07:2B"
	U.logger.log(20, "starting loop")

	U.echoText(G.restartLogfileName, "starting beaconloop")

	try:
		while True:
			messageBad = False
			loopCount += 1
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
				# how often is the BLE stack being restarted (BLErestart marker is written
				# by BLEconnect - e.g. after an ENOSYS connect wedge)?  Log the interval so
				# the restart rate is measurable.  The extended listener survives these via
				# its own idempotent re-attach + self-heal.
				U.logger.log(20, "BLE stack restart #{} requested (BLEconnect marker); {:.0f}s since last restart".format(
					bleRestartCounter, tryDeltaTime(restartBLE)))
				if bleRestartCounter > 10:
					U.restartMyself(param="", reason="bad BLE restart", python3=usePython3)
					if debugRestarts: U.echoText(G.restartLogfileName,"restart due to bleRestartCounter:{}".format(bleRestartCounter))
					time.sleep(1)
					sys.exit(4)

				sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber, thisHCI=useHCIForBeacon, trymyBLEmac=myBLEmac)
				restartBLE = time.time()
				if rpiDataAcquistionmethod == "hcidump":
					retCode = startHCUIDUMPlistnr(useHCIForBeacon)
				if retCode != 0:
					U.logger.log(20,"stopping {} bad BLE start retCode= {}".format(G.program, retCode) )
					if downCount > 1: sys.exit(5)
					time.sleep(2)
					continue

			if rpiDataAcquistionmethod == "socket":
				if currentBLESocket is not None: sock = currentBLESocket	# pick up a socket rebuilt by restartLESCAN (single-dongle beep reset)
				try:
					old_filter = setupSOCKET(sock)
				except Exception:
					# do NOT crash-loop: log the full reason, fall back to hcidump for this run.
					# make it permanent for this rpi via the acquisition-method override in the
					# rpi device edit (the plugin default stays socket for the other rpis)
					U.logger.log(20,"setupSOCKET failed on {} - socket method not usable on this rpi; falling back to hcidump for this run".format(useHCIForBeacon), exc_info=True)
					rpiDataAcquistionmethod = "hcidump"
					retCode = startHCUIDUMPlistnr(useHCIForBeacon)
					if retCode != 0:
						U.logger.log(20,"stopping {} bad BLE start retCode= {}".format(G.program, retCode))
						time.sleep(2)
						continue

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

					## single-dongle handshake: BLEconnect requests the radio
					pausedSecs = checkBeaconloopPause()
					if pausedSecs > 0:
						lastmsg = time.time(); lastMSGwithGoodData = time.time()
						lastMSGwithDataPlain = time.time(); lastMSGwithDataPassed = time.time()
						zeroInARow = 0
						restartLESCAN(useHCIForBeacon, 20, force=True)	# scan back on (params re-sent)
						break

					if rpiDataAcquistionmethod.find("hcidump") == 0:
						Msgs = readHCUIDUMPlistener()

					else:
						Msgs = getSocketData(sock)
						# getSocketData re-opened the scan socket in place (dongle blip): the local
						# sock is the dead one and is only refreshed OUTSIDE this inner loop, so
						# swap it here or every following recv errors on the stale handle
						if scanSocketRebuilt[0]:
							scanSocketRebuilt[0] = False
							if currentBLESocket is not None: sock = currentBLESocket

					# merge frames captured by the extended-only listener radio (already
					# converted to the legacy report layout - same downstream processing)
					while extListenerQueue:
						try:	Msgs.append(extListenerQueue.popleft())
						except IndexError:	break

					#### check new messages
					#dtinner[4][0] = max(dtinner[0], tryDeltaTime( startofInnerLoop, oneDigit=True))

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
						if scanExtendedMode: extScanZeroMsgRestarts[0] = 0	# extended scanning delivers -> healthy

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
						if rpiDataAcquistionmethod == "socket": restartLESCAN(useHCIForBeacon, 20, force=True)	# re-enable scan after gatttool session



			if rpiDataAcquistionmethod == "socket":
				# restartLESCAN may have REBUILT the socket during this set (single-dongle beep did an
				# hciconfig reset) - use the current one and never crash the whole loop on the restore
				if currentBLESocket is not None: sock = currentBLESocket
				try:
					sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, padHCIfilter(old_filter) )
				except Exception:
					U.logger.log(20, "socket method: filter restore skipped (socket was rebuilt this set)")
		
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
			checkBatteryReadFile()


			dt1 = int(tryDeltaTime( lastMSGwithDataPlain))
			dt2 = int(tryDeltaTime( lastMSGwithDataPassed))

			if  nMessagesSend > 0:
				nEmptyMessagesInARow = 0
				stackrestartcount    = 0	# recovered: the 5-level stack-restart ladder is per INCIDENT - it never reset before, so a long-running beaconloop eventually escalated every hiccup straight to a program restart
			else:
				nEmptyMessagesInARow += 1

				
			if dt1 > 10 or nEmptyMessagesInARow > 9  or messageBad or  (dt1 > 10  and not checkIfBLEprogramIsRunning(useHCIForBeacon)):
					cmd = "rfkill list"
					blocked = readPopen(cmd)[0]
					if blocked.find(" blocked: yes") ==-1:	blocked = ""
					else:									blocked = "\nrfkill list: "+blocked

					out =  "lastmsg {}s:bytes:{},{}; okdata: {}s:,bytes:{},{}; loopCount:{}; restartCount:{}, bleRestartCounter:{}, nEmptyMessagesInARow:{}, {} ".format( dt1, len(lastMessageRead), lastMessageRead,  dt2, len(lastMessageOK), lastMessageOK, loopCount, restartCount, bleRestartCounter, nEmptyMessagesInARow,  blocked)
					U.logger.log(20, "time w/out any message: "+out)
					if debugRestarts: U.echoText(G.restartLogfileName, out)
					if stackrestartcount < 5:
						U.logger.log(20, "restarting stack  due to no messages {}  ".format(dt1) )
						# SELF-HEALING: extended scanning active but NOTHING arrives = the adapter
						# claims BT5 extended advertising but its implementation is broken (several
						# cheap "BT 5.x" dongles do that). After 2 empty restarts fall back to
						# legacy scanning for this session instead of restart-looping forever
						if scanExtendedMode:
							extScanZeroMsgRestarts[0] += 1
							if extScanZeroMsgRestarts[0] >= 2 and not extScanForceLegacy[0]:
								extScanForceLegacy[0] = True
								U.logger.log(20,"extended scanning delivered NO messages {}x - adapter likely misreports its BT5 support; falling back to LEGACY scanning (extended advs / Ruuvi E1 not receivable on this radio)".format(extScanZeroMsgRestarts[0]))
								reportBLE5("no - adapter claims BLE5 but went silent in operation")
								saveExtScanVerdict(False)		# next program start must re-prove delivery
						if rpiDataAcquistionmethod == "socket":
							sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber, thisHCI=useHCIForBeacon, trymyBLEmac=myBLEmac) 
							restartBLE = time.time()
							maxLoopCount = 6000
						else:
							stopHCUIDUMPlistener()
							sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber, thisHCI=useHCIForBeacon, trymyBLEmac=myBLEmac, hardreset=True)
							restartBLE = time.time()
							#restartLESCAN(hciUse, 20, force=True)
							startHCUIDUMPlistnr(useHCIForBeacon)
							if debugRestarts: U.echoText(G.restartLogfileName, "restarted  hcidump restartBLE:{}".format(restartBLE))
						nEmptyMessagesInARow = 0
						stackrestartcount +=1
						if stackrestartcount >= 2: warnBadScanDongle()	# persistent no-message trouble -> blame the dongle only if it is a clone
						# fresh no-data window for the restarted stack - without this the next pass
						# (2 secs later, dt still > 10) escalated straight to a program restart
						lastMSGwithDataPlain = time.time(); lastMSGwithDataPassed = time.time()
					else:
						maxLoopCount = 20
						restartCount += 1
						if restartCount > 0:
							U.logger.log(20, "restarting beaconloop  due to no messages " )
							time.sleep(0.5)
							U.restartMyself(param="", reason="too long a time w/o message", python3=usePython3)
							if debugRestarts: U.echoText(G.restartLogfileName, "restarting beaconloop ")

	except Exception :
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20, "  exiting loop due to error\n restarting "+G.program)
		stopHCUIDUMPlistener()
		time.sleep(20)
		# /usr/bin/python does not exist on bookworm (py3 only) - the crash restart silently died there
		subprocess.call("{} {}{}.py &".format("/usr/bin/python3" if usePython3 else "/usr/bin/python", G.homeDir, G.program), shell=True)
	try: 	G.sendThread["run"] = False; time.sleep(1)
	except: pass


debugRestarts = True

findMAC = [] # debug list, e.g. ["CB:25:B7:8F:BA:BE"]
#["D0:EF:76:6F:18:96","D0:EF:76:6E:FC:5E"]# ["CB:25:B7:8F:BA:BE"] #["E4:88:7D:0D:4D:7A"] # ["E9:DD:2E:0E:3B:54"] # ["DD:53:FB:BF:03:40"] #["00:81:F9:86:3E:A0"] # ["CC:48:72:06:40:52","F0:66:AF:D4:9F:C1"] #["EC:44:51:19:C9:44"] # [,"E9:DD:2E:0E:3B:54","F0:D3:EF:76:A1:74"]
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
U.logger.log(20,"end of beaconloop.py ") 
sys.exit(0)
