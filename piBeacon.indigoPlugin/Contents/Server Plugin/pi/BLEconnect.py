#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# 
##
##	 read BLE sensors and send http to indigo with data
#
##
## ok for py3

import	sys, os, subprocess, copy
import	time
import	json
import  pexpect
import  re
try:
	import bluetooth
	import bluetooth._bluetooth as bt
	bluezPresent = True
except:
	bluezPresent = False
try:
	import hciRawSocket as rawhci		# stdlib raw HCI backend (py3.3+), same API subset as pybluez
	rawhciPresent = True
except:
	if bluezPresent:
		rawhci = bt
		rawhciPresent = True
	else:
		rawhciPresent = False
try:
	import gattAttClient				# stdlib ATT/GATT client (py3.3+) - gatttool replacement
	attClientPresent = True
except:
	attClientPresent = False			# py2 or no AF_BLUETOOTH -> gatttool stays the gatt engine
ATTCLIENT_MINVERSION = 1.4				# checked at startup: partial file sends left STALE gattAttClient.py on rpis 3x already
 
import struct
import array
import fcntl
try: import Queue
except: import queue as Queue
import threading


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "BLEconnect"
VERSION = 12.0
iphoneDebug = False		# True: log every iphone/watch presence poll + the presenceDBG stage lines (page/ACL/Read-RSSI)
ansi_escape =re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')

if sys.version[0] == "3": usePython3 = True
else:					  usePython3 = False




#################################
def escape_ansi(line):
	"""Strips ANSI escape sequences from a line of text using a precompiled regex and encodes the result to ASCII, ignoring non-ASCII characters; returns an empty string on failure.

	Inputs:
	    line (str): text line possibly containing ANSI escape codes
	Outputs:
	    bytes: ASCII-encoded line with ANSI codes removed, or empty string on error
	"""
	try:	ret = ansi_escape.sub('', line).encode('ascii',errors='ignore')
	except: ret = ""
	return ret

####-------------------------------------------------------------------------####
def toStringAndstripRNetc(inX):
	"""Converts a value to a string, strips a leading bytes-literal b' wrapper, replaces escaped and literal carriage-return/newline characters with spaces, and trims surrounding whitespace.

	Inputs:
	    inX (object): value (often bytes) to stringify and clean
	Outputs:
	    str: cleaned single-line string
	"""
	return str(inX).strip("b'").replace("\\r"," ").replace("\\n"," ").replace("\r"," ").replace("\n"," ").strip()

####-------------------------------------------------------------------------####
def toStringAndstripB(inX):
	"""Converts a value to a string and strips the leading bytes-literal b' wrapper characters.

	Inputs:
	    inX (object): value (often bytes) to stringify
	Outputs:
	    str: string with b' characters stripped
	"""
	return str(inX).strip("b'")


####-------------------------------------------------------------------------####
def readPopen(cmd):
		"""Runs a shell command via subprocess.Popen, captures stdout and stderr, and returns them decoded as UTF-8 strings; logs and returns None on exception.

		Inputs:
		    cmd (str): shell command to execute
		Outputs:
		    tuple: (stdout_str, stderr_str) decoded UTF-8, or None on error
		"""
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception :
			U.logger.log(20,"", exc_info=True)



#################################
def signedIntfrom16(string):
	"""Parses a hexadecimal string into an integer and interprets it as a signed 16-bit value (subtracting 65536 when above 32767); returns 0 on error.

	Inputs:
	    string (str): hex string representing a 16-bit value
	Outputs:
	    int: signed 16-bit integer, or 0 on error
	"""
	try:
		intNumber = int(string,16)
		if intNumber > 32767: intNumber -= 65536
	except Exception :
		U.logger.log(20,"", exc_info=True)
		return 0
	return intNumber


#################################
def checkIFQuickRequested():
	"""Checks whether a quick-refresh request file exists for the sensor and, if so, resets per-MAC connection state in macList (last data, timestamps, retry and up flags) for BLE connect and long-connect device types.

	Inputs:
	    None.
	Outputs:
	    None: mutates the macList global and logs on error
	"""
	try:
		if U.checkNowFile(sensor):			  
			for ml in macList :
				if macList[ml]["type"] == "isBLEconnect":
					macList[ml]["lastData"]	   = {"rssi":-999,"txPower":-999}
					macList[ml]["lastTesttt"]  = 0.
					macList[ml]["retryIfUPtemp"] = macList[ml]["retryIfUP"]
					macList[ml]["retryIfUP"] = False
					macList[ml]["up"]		 = False
				if macList[ml]["type"] == "isBLElongConnectDevice":
					macList[ml]["lastTesttt"]  = 0.
					macList[ml]["nextRead"]  = 0.
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 




#################################
def startHCI():
	"""Selects and brings up the appropriate HCI Bluetooth adapter for BLE(long)connect: waits for other BLE functions, reads which HCI beaconloop is using, queries available adapters, ensures enough dongles, picks one (and optionally a second) HCI, persists the choice to temp/BLEconnect.hci, and exits with error notifications if the BLE stack is unavailable.

	Inputs:
	    None.
	Outputs:
	    tuple: (useHCI, myBLEmac, BLEid, bus, useHCI2) on success; exits the process on failure
	"""
	global singleDongleMode
	global useHCI, useHCI2
	## give other ble functions time to finish

	defaultBus = "USB"
	doNotUseHCI = ""
	BusUsedByBeaconloop = ""
	time.sleep(10)

	# always determine which adapter beaconloop uses - also in gatt-service-only
	# mode BLEconnect must not take beaconloop's dongle
	if True:
		for ii in range(4):
			if ii > 0: time.sleep(ii*5)
			hciBeaconloopUsed, raw  = U.readJson("{}temp/beaconloop.hci".format(G.homeDir))
			U.logger.log(20, "BLE(long)connect: beconloop uses: {}".format(hciBeaconloopUsed))
			# role format {"scan":{mac,hci,bus,..},..}; old flat format still read
			sc = hciBeaconloopUsed.get("scan", {})
			doNotUseHCI 		= sc.get("hci", hciBeaconloopUsed.get("usedHCI",""))
			BusUsedByBeaconloop = sc.get("bus", hciBeaconloopUsed.get("usedBus",""))
			# the BLE5 extended-listener radio is OFF LIMITS as well: we hciconfig-reset our
			# own adapter (connect ladder), and doing that to the ext listener kills its
			# extended scan -> Ruuvi Air E1 dropouts. Excluding only beaconloop's SCAN radio
			# was not enough: whenever the master role was momentarily unusable we fell back
			# to a local pick that could land right on the ext-listener dongle.
			doNotUseExtListener = hciBeaconloopUsed.get("extListener", {}).get("hci", "")
			if doNotUseHCI == "" or BusUsedByBeaconloop == "": continue
			break

	#### selct the proper hci bus: if just one take that one, if 2, use bus="USB", if no uart use hci0

	#need to add:
	#	 hciX default 

	HCIs = U.whichHCI()
	"""
	{'hci': {
	'hci0': {'bus': 'USB',  'BLEmac': '5C:F3:70:6D:D9:4A', 'numb': 0, 'upDown': 'UP'}, 
	'hci2': {'bus': 'UART', 'BLEmac': 'DC:A6:32:6E:E6:D0', 'numb': 1, 'upDown': 'UP'}}, 
	'ret': ['hci21:\tType: Primary  Bus: UART\n\tBD Address: DC:A6:32:6E:E6:D0  ACL MTU: 1021:8  SCO MTU: 64:1\n\tUP RUNNING \n\tRX bytes:218659024 acl:5 sco:0 events:6395583 errors:0\n\tTX bytes:5859 acl:4 sco:0 commands:226 errors:0\n\nhci0:\tType: Primary  Bus: USB\n\tBD Address: 5C:F3:70:6D:D9:4A  ACL MTU: 1021:8  SCO MTU: 64:1\n\tUP RUNNING \n\tRX bytes:124594 acl:1716 sco:0 events:9040 errors:0\n\tTX bytes:68257 acl:870 sco:0 commands:5086 errors:0\n\n', u'']}
	"""
	U.logger.log(20, "BLE(long)connect--HCIs read:  {}, hci used by beaconloop:{}, {}".format(HCIs, doNotUseHCI, doNotUseHCI))
	if HCIs["hci"] != {}:
		if len(HCIs["hci"]) < 2:
			# SINGLE DONGLE MODE: share the adapter with beaconloop.
			# - regular BLEconnect sensor polling is DISABLED (needs a 2nd dongle)
			# - on-demand gatt jobs (beep, battery, switchbot) pause beaconloop scanning
			#   via temp/beaconloop.pause (max 55 secs failsafe)
			singleDongleMode = True
			useHCI   = list(HCIs["hci"])[0]
			myBLEmac = HCIs["hci"][useHCI]["BLEmac"]
			BLEid    = HCIs["hci"][useHCI]["numb"]
			bus      = HCIs["hci"][useHCI]["bus"]
			U.logger.log(20, "BLE(long)connect: SINGLE dongle mode on {} - regular sensor polling disabled; beep/battery/switchbot pause beaconloop while using the radio".format(useHCI))
			U.writeFile("temp/BLEconnect.hci", json.dumps({"usedHCI":useHCI, "myBLEmac": myBLEmac, "usedBus":bus,"pgm":"BLEconnect","singleDongle":True}))
			return useHCI,  myBLEmac, BLEid, bus, useHCI

		# beaconloop is the MASTER of radio-role assignment - single source of truth is
		# beaconloop.hci.  OBEY its published "BLEconnect" role instead of computing our own
		# pick: two independent selectHCI runs (master's predicted one vs this one) disagreed
		# and landed BLEconnect on the extended-listener's BLE5 dongle, whose extended scan
		# our connect commands then knocked into legacy mode (~every poll -> Ruuvi E1 dropouts).
		# Fall back to a local pick ONLY until the master has published a usable role (bootstrap).
		# NOTE the scan radio is deliberately NOT excluded here. The master puts connect on its own
		# scan radio whenever that is the only option (1-radio rpi, and 2-radio rpi where the second
		# radio is a BLE5-only dongle doing extended listening) - sharing is what the pause handshake
		# in beaconloop exists for. Refusing it left BLEconnect with nothing at all and it died with
		# "BLE STACK is not UP", killing beep/battery/iphone. The ext-listener radio stays excluded:
		# our connect commands knock its extended scan back into legacy mode.
		masterHCI = hciBeaconloopUsed.get("BLEconnect", {}).get("hci", "")
		if masterHCI and masterHCI != doNotUseExtListener and masterHCI in HCIs["hci"] and HCIs["hci"][masterHCI].get("upDown","") == "UP":
			useHCI   = masterHCI
			myBLEmac = HCIs["hci"][useHCI]["BLEmac"]
			BLEid    = HCIs["hci"][useHCI]["numb"]
			bus      = HCIs["hci"][useHCI]["bus"]
			U.logger.log(20, "BLE(long)connect: using MASTER-assigned connect radio {} (from beaconloop.hci){}".format(
							useHCI, " - SHARED with the scan radio, the pause handshake arbitrates" if useHCI == doNotUseHCI else ""))
		else:
			# AUTO ("-1"): CONNECT role -> best connector (good external > internal > clone external),
			# always avoiding beaconloop's adapter. Explicit USB/UART still honoured.
			useHCI,  myBLEmac, BLEid, bus = U.selectHCI(HCIs["hci"], "-1", defaultBus, doNotUseHCI=doNotUseHCI, doNotUseHCI2=doNotUseExtListener, role="connect")
			U.logger.log(20, "BLE(long)connect: master published no usable BLEconnect role yet -> local pick {}".format(useHCI))
		U.logger.log(20, "BLE(long)connect: useHCI:{}, len(HCIs):{}, BLEid:{}, default:{}, HCIUsedByBeaconloop:{}; BusUsedByBeaconloop:{}".format(useHCI, len(HCIs["hci"]), BLEid, defaultBus, doNotUseHCI, BusUsedByBeaconloop))
		try:
			if "{}".format(bus).upper() == "UART" and G.wifiEnabled:		# onboard BT shares the chip/bus with WiFi
				U.logger.log(20, "BLE(long)connect: using the INTERNAL (onboard) radio for connects AND WiFi is on - beep/battery/iphone/switchbot may be less reliable. An external USB dongle for BLEconnect is recommended.")
		except Exception: pass

		if len(HCIs["hci"]) >= 2:
			if BLEid >= 0:
				if len(HCIs["hci"]) > 2:
					# SECOND adapter (parallel gatt / switchbot work). It must NOT be the BLE5
					# extended listener: gatt on that radio opens ACL connections and knocks its
					# extended scan out (live-seen: hci2 acl:336 while the ext listener went
					# 85 reports/min -> 0 and stayed there). selectHCI only takes two exclusions
					# and both are already used, so drop the ext listener from the pool instead.
					# If nothing is left, BLEid2 stays < 0 and we fall through to using the
					# primary radio for both jobs, which is the correct single-radio behaviour.
					hciPool = dict(HCIs["hci"])
					if doNotUseExtListener in hciPool:	del hciPool[doNotUseExtListener]
					# quiet: "is there a spare 3rd radio?" - finding none is the NORMAL answer here
					# and is handled two lines down, so it must not raise an indigo ERROR
					useHCI2,  myBLEmac2, BLEid2, bus2 = U.selectHCI(hciPool, "", "", doNotUseHCI=doNotUseHCI, doNotUseHCI2=useHCI, quiet=True)
					if BLEid2 >= 0:
						U.writeFile("temp/BLEconnect.hci", json.dumps({"usedHCI":useHCI, "myBLEmac": myBLEmac, "usedBus":bus,"pgm":"BLEconnect"}))
						return useHCI,  myBLEmac, BLEid, bus, useHCI2  

				U.writeFile("temp/BLEconnect.hci", json.dumps({"usedHCI":useHCI, "myBLEmac": myBLEmac, "usedBus":bus,"pgm":"BLEconnect"}))
				U.logger.log(20, "BLE(long)connect: using mac:{};  useHCI: {}; bus: {}; mode: {} searching for MACs:\n{}".format(myBLEmac, useHCI, HCIs["hci"][useHCI]["bus"], BLEconnectMode , macList))
				return 	useHCI,  myBLEmac, BLEid, bus, useHCI


			else:
				text = "BLEconnect: BLE STACK is not UP HCI-info: useHCI:{},  myBLEmac:{}, BLEid:{}, \n{}".format(useHCI,  myBLEmac, BLEid, HCIs)
				U.logger.log(20, text)
				U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
				U.sendURL( data={"data":{"hciInfo":"err-BLE-stack-not-up"}}, squeeze=False, wait=False )
				threadDictReadSwitchbot["state"] = "stop"
				threadDictDoSwitchbot["state"] = "stop"
				threadDictReadSwitchbot["state"] = "stop"
				threadDictDoSwitchbot["state"] = "stop"
				time.sleep(25)
				exit()

	else:
			text = "BLEconnect: BLE STACK HCI is empty HCI:{}".format(HCIs)
			U.logger.log(20, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			U.sendURL( data={"data":{"hciInfo":"err-BLE-stack-empty"}}, squeeze=False, wait=False )
			threadDictReadSwitchbot["state"] = "stop"
			threadDictDoSwitchbot["state"] = "stop"
			time.sleep(25)
			exit()

	threadDictReadSwitchbot["state"] = "stop"
	threadDictDoSwitchbot["state"] = "stop"
	time.sleep(5)
	exit()


#################################
def checkIfHCIup(useHCI):
	"""Queries the available HCI adapters and returns whether the given HCI interface is present and in the UP state.

	Inputs:
	    useHCI (str): HCI interface name to check (e.g. 'hci0')
	Outputs:
	    bool: True if the interface exists and is UP, else False
	"""
	HCIs = U.whichHCI()
	if useHCI in HCIs["hci"]:
		if HCIs["hci"][useHCI]["upDown"] == "UP": return True
	return False

#################################
def batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=3000., batteryVoltAt0=2700.):
	"""Computes a battery charge percentage (0-100) from a measured battery voltage, applying a temperature correction that raises the effective empty-voltage threshold as temperature drops below 10C.

	Inputs:
	    batteryVoltage (float): measured battery voltage in mV
	    temp (float): ambient temperature in Celsius used for correction
	    batteryVoltAt100 (float): voltage corresponding to 100% charge (default 3000.0)
	    batteryVoltAt0 (float): voltage corresponding to 0% charge (default 2700.0)
	Outputs:
	    int: battery level percentage clamped to 0-100, or 0 on error
	"""
	try:
		batteryLowVsTemp			= (1. + 0.7*min(0.,temp-10.)/100.) * batteryVoltAt0 # (changes to 0.9* 2700 @ 0C; to = 0.8*2700 @-10C )
		batteryLevel 				= int(min(100.,max(0.,100.* (batteryVoltage - batteryLowVsTemp)/(batteryVoltAt100-batteryLowVsTemp))))
		return batteryLevel
	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 0



#################################
def checkSwitchBotPrio(thisMAC):
	"""Determines whether a non-SwitchBot BLE operation should yield priority to an active/waiting SwitchBot: returns False if no SwitchBot is present or this MAC already holds priority, otherwise clears nonSwitchBotActive and returns True when a SwitchBot is active or waiting.

	Inputs:
	    thisMAC (str): MAC address of the device requesting/checking priority
	Outputs:
	    bool: True if priority should be ceded to a SwitchBot, else False
	"""
	global nonSwitchBotActive

	verbose = True
	if beaconBeepPending():
		# a beacon beep is queued = highest priority within BLEconnect:
		# abort/yield the sensor operation so the main loop can execute the beep right away
		return True
	if not switchBotPresent: return False
	if currentActiveSwitchbotMAC !="" and currentActiveSwitchbotMAC == thisMAC: return False
	if switchbotActive in ["active", "waiting", "waitingForPrio"]:  
		if verbose: U.logger.log(20,"{} {} cancel prio for switchbot:{} ".format(thisMAC, nonSwitchBotActive, currentActiveSwitchbotMAC ))
		nonSwitchBotActive = ""
		return True
	return False

#################################
def launchGATT(useHCI, thisMAC, timeoutGattool, timeoutConnect, retryConnect=5, random=False, verbose=False, nTries=1, waitbetween=0.5):
	"""Spawns a gatttool interactive session via pexpect for the given BLE MAC address (optionally using random addressing), waiting for the gatttool prompt, then issues a connect command through connectGATT. Retries the whole launch nTries times and yields to higher-priority SwitchBot commands.

	Inputs:
	    useHCI (str): HCI adapter identifier (e.g. hci0) passed to gatttool -i
	    thisMAC (str): BLE device MAC address to connect to
	    timeoutGattool (float): Seconds to wait for the gatttool prompt to appear
	    timeoutConnect (float): Seconds to wait for the connect command to succeed
	    retryConnect (int): Number of connect attempts passed to connectGATT
	    random (bool): If True, use random BLE addressing (-t random)
	    verbose (bool): If True, log detailed progress
	    nTries (int): Number of times to retry the entire launch sequence
	    waitbetween (float): Seconds to wait between connect retries
	Outputs:
	    str: 'ok' on successful connection, otherwise '' (empty string)
	"""
	global nonSwitchBotActive

	if gattEngineIsATT():				# ATT engine: session = LE L2CAP socket, no gatttool process
		sess = attSessions.get(thisMAC)
		if sess is not None and sess.sock is not None: return "ok"
		for kk in range(max(1, int(nTries))):
			if attConnect(thisMAC, random, connectTimeout=10. * max(1, int(retryConnect))):
				return "ok"
		return ""

	if thisMAC not in expCommands: expCommands[thisMAC] = ""	# beacon-tag macs (beep/battery/timeSet) are not pre-registered like sensor devices
	if expCommands[thisMAC] != "": return "ok"

	BF = ""
	AF = ""
	try:
		for kk in range(nTries):
			disconnectGattcmd(thisMAC, 2)
			if checkSwitchBotPrio(thisMAC):
				return ""

			if thisMAC not in lastSwitchbotCMD: nonSwitchBotActive = "connectGATT0-"+thisMAC
			cmd = "sudo /usr/bin/gatttool -i {} -b {} {} -I".format(useHCI,  thisMAC, "-t random " if random else ""  ) 
			if verbose: U.logger.log(20,"{}  {} ;  expecting: '>'".format(thisMAC, cmd))
			expCommands[thisMAC] = pexpect.spawn(cmd)
			ret = expCommands[thisMAC].expect([">","Error","error","Failed","failed",pexpect.TIMEOUT], timeout=timeoutGattool)
			BF = toStringAndstripRNetc(expCommands[thisMAC].before)
			AF = toStringAndstripRNetc(expCommands[thisMAC].after) 
			if ret == 0:
				pass
				#U.logger.log(20,"gatttool started successful: {}-==-:{}".format(expCommands[thisMAC].before,expCommands[thisMAC].after))
			else:
				disconnectGattcmd(thisMAC, 2)
				if kk == nTries -1: 
					U.logger.log(20,"{} gatttool ERROR, giving up: \nBF:{}--\nAF:{}-".format(thisMAC, BF, AF))
					time.sleep(1)
					return ""
				U.logger.log(20,"{} gatttool ERROR:\nBF:{}--\nAF:{}-".format(thisMAC, BF, AF))
				expCommands[thisMAC] = ""
				continue

			# send connect command 
			time.sleep(0.1)
			ret = connectGATT(thisMAC, retryConnect, timeoutConnect=timeoutConnect,  waitbetween=waitbetween, verbose=verbose)
			if ret == "":   return ""
			if ret == "ok": return "ok"


		nonSwitchBotActive = ""
		return ""
	except  Exception :
		U.logger.log(20,"", exc_info=True)
	nonSwitchBotActive = ""
	return ""


def connectGATT(thisMAC, retryConnect, timeoutConnect=0.5, waitbetween=0.5, verbose=False):
	"""Sends the gatttool 'connect' command on an already-spawned pexpect session for the given MAC and waits for 'Connection successful', retrying up to retryConnect times. Tracks 'Function not implemented' errors via a global counter and yields to higher-priority SwitchBot commands.

	Inputs:
	    thisMAC (str): BLE device MAC address whose pexpect session to connect
	    retryConnect (int): Maximum number of connect attempts
	    timeoutConnect (float): Seconds to wait for connection success per attempt
	    waitbetween (float): Seconds to sleep between failed attempts
	    verbose (bool): If True, log detailed progress
	Outputs:
	    str: 'ok' if connected, otherwise '' (empty string)
	"""
	global nonSwitchBotActive
	global counterFunctionNotImplemented

	BF = ""
	AF = ""
	try:
		for ii in range(retryConnect):
			if expCommands[thisMAC] == "":
					U.logger.log(20,"{} connect error: expCommands is empty".format(thisMAC))
					break
			try:
				if checkSwitchBotPrio(thisMAC):
					return ""
				if verbose or counterFunctionNotImplemented > 2: U.logger.log(20,"{} send connect try#:{}  expecting: Connection successful".format(thisMAC, ii))
				if thisMAC not in lastSwitchbotCMD: nonSwitchBotActive = "connectGATT1-"+thisMAC
				expCommands[thisMAC].sendline("connect")
				ret = expCommands[thisMAC].expect(["Connection successful","Error","error","Failed","failed", pexpect.TIMEOUT], timeout=timeoutConnect)
				BF = toStringAndstripRNetc(expCommands[thisMAC].before)
				AF = toStringAndstripRNetc(expCommands[thisMAC].after) 
				if ret == 0:
					if verbose or counterFunctionNotImplemented >3: U.logger.log(20,"{} ... SUCCESS  errorCount:{}".format(thisMAC, counterFunctionNotImplemented))
					#ret = expCommands[thisMAC].expect(".*", timeout=0.5)
					#U.logger.log(20,"... .*: {}-==-:{}".format(expCommands[thisMAC].before,expCommands[thisMAC].after))
					counterFunctionNotImplemented = 0
					return "ok"
				else:
					if str(expCommands[thisMAC].before).find("Function not implemented") > -1:
						counterFunctionNotImplemented +=1
					if verbose or counterFunctionNotImplemented > 5: U.logger.log(20, "{} connect ERROR: waiting {:.1f} sec; errorCount:{} retCode:{} .. \nBF:{}--\nAF:{}--".format(thisMAC, waitbetween, counterFunctionNotImplemented, ret, BF, AF))
					time.sleep(waitbetween)
			except Exception as e:
				#U.logger.log(20,"{} error:{}".format(thisMAC, str(e) ) )
				if str(e).find("Bad file descriptor") > -1: 
					U.logger.log(20,"{} bad file descriptor, retry connect".format(thisMAC) )
					time.sleep(1)

				else:
					U.logger.log(20,"", exc_info=True)
					U.logger.log(20,"{} expCommands after error:\n{}".format(thisMAC,  toStringAndstripRNetc(expCommands[thisMAC]) ) )
				break


	except  Exception :
		U.logger.log(20,"", exc_info=True)
	return ""

#################################
def disconnectGattcmd(thisMAC, timeout, verbose=False):	
	"""Sends 'quit' to the gatttool pexpect session for the given MAC, then kills and force-closes the process and removes any lingering gatttool process for that MAC. Clears the stored session and returns whether disconnection completed.

	Inputs:
	    thisMAC (str): BLE device MAC address whose gatttool session to close
	    timeout (float): Seconds to wait for the quit command response
	    verbose (bool): If True, log detailed progress
	Outputs:
	    bool: True if disconnected/cleaned up (or no session existed), False on exception
	"""
	if thisMAC in attSessions:		# ATT engine: closing the socket IS the disconnect
		attClose(thisMAC)
		return True
	doPrint = verbose
	BF = ""
	AF = ""
	try:
		if thisMAC not in expCommands: return True
		if expCommands[thisMAC] == "": return True
		expCommands[thisMAC].sendline("quit" )
		if doPrint: U.logger.log(20,"{} sendline disconnect ".format(thisMAC))
		ret = expCommands[thisMAC].expect([".*", "Error",pexpect.TIMEOUT], timeout=timeout)
		if ret == 0:
			expCommands[thisMAC].kill(0)
			expCommands[thisMAC].close(force=True)
			U.killOldPgm(-1,"gatttool", param1=thisMAC, param2="",verbose=False)
			if verbose: U.logger.log(20,"{} disconnect: quit ok".format(thisMAC))
			expCommands[thisMAC] = ""
			return True
		else:
			BF = toStringAndstripRNetc(expCommands[thisMAC].before)
			AF = toStringAndstripRNetc(expCommands[thisMAC].after) 
			if doPrint: U.logger.log(20,"{} Error: NOT disconnected, quit command error: \nBF:{}--\nAF:{}--".format(thisMAC, BF, AF))
			expCommands[thisMAC].kill(0)
			expCommands[thisMAC].close(force=True)
			U.killOldPgm(-1,"gatttool",  param1=thisMAC,param2="",verbose=False)
			expCommands[thisMAC] = ""
			return True
	except  Exception :
		U.logger.log(20,"", exc_info=True)
	expCommands[thisMAC] = ""
	return False



#################################
def writeGattcmd(thisMAC, cc,  expectedTag, timeout, verbose=False, retryCMD=3):	
	"""Sends a gatttool command line on the MAC's pexpect session and waits for the expectedTag response, retrying up to retryCMD times. On a dropped connection it attempts a reconnect via connectGATT before retrying.

	Inputs:
	    thisMAC (str): BLE device MAC address whose session to write to
	    cc (str): gatttool command string to send
	    expectedTag (str): Expected substring/pattern in the success response
	    timeout (float): Timeout value for the command (note: expect uses a hardcoded 5s)
	    verbose (bool): If True, log detailed progress
	    retryCMD (int): Maximum number of command attempts
	Outputs:
	    bool: True if the expected response was received, otherwise False
	"""
	global counterFunctionNotImplemented
	if thisMAC in attSessions:			# ATT engine session
		ok, values = attExecGattCmd(thisMAC, cc, timeout)
		return ok
	retryConnect = 5
	BF = ""
	AF = ""
	try:
		retryCMD = int(retryCMD)
		for ii in range(retryCMD):
			if checkSwitchBotPrio(thisMAC):  return False
			if checkIfSwitchbotStopAND(thisMAC): return False

			if verbose: U.logger.log(20,"{} sending cmd:{}, expecting:'{}'".format(thisMAC, cc, expectedTag))
			expCommands[thisMAC].sendline( cc )
			ret = expCommands[thisMAC].expect([expectedTag,"Error","failed","Failed",pexpect.TIMEOUT], timeout=5)
			if ret == 0:
				if verbose or counterFunctionNotImplemented >0: U.logger.log(20,"{} ... SUCCESS".format(thisMAC))
				counterFunctionNotImplemented = 0
				return True
			else: 
				BF = toStringAndstripRNetc(expCommands[thisMAC].before)
				AF = toStringAndstripRNetc(expCommands[thisMAC].after) 
				if  str(expCommands[thisMAC].before).find("Function not implemented") > -1:
					counterFunctionNotImplemented +=1
				if counterFunctionNotImplemented > 5: U.logger.log(20, "{} ... ERROR, errorCount:{}, try reconnect\nBF:{}--\nAF:{}".format(thisMAC, counterFunctionNotImplemented, BF, AF))

				if ii < (retryCMD-1):
					try:
						if BF.find("Disconnected") >-1 or BF.find("WARNING") >-1 or BF.find("Invalid") >-1 :
							U.logger.log(20,"{} sending connect after connection lost ".format(thisMAC))
							ret = connectGATT(thisMAC, retryConnect, verbose=verbose)
							if ret != "ok": 
								return False
							U.logger.log(20,"{}  re-connected !!, now retry cmd".format(thisMAC))
						else:
							U.logger.log(20,"{} failed, cmd:{}, expectedTag:{}, \nBF:{}--\nAF:{}--".format(thisMAC, cc, expectedTag, BF, AF))

					except  Exception :
						U.logger.log(20,"", exc_info=True)

				continue
			ret = expCommands[thisMAC].expect("\n")

	except  Exception :
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20,"{} cc:{}, expectedTag:{}, ii:{}, retryCMD:{}, ".format(thisMAC, cc, expectedTag, ii, retryCMD))
	return False



#################################
def writeAndListenGattcmd(thisMAC, cc, expectedTag, nBytes, timeout, verbose=False):
	"""Sends a gatttool command and listens for the expectedTag response, then parses the following line into whitespace-separated byte tokens, requiring exactly nBytes tokens (or any count if nBytes is negative). Retries up to twice and yields to SwitchBot priority.

	Inputs:
	    thisMAC (str): MAC address of the BLE device (key into expCommands)
	    cc (str): gatttool command string to send
	    expectedTag (str): Expected substring/pattern marking a valid response
	    nBytes (int): Expected number of returned byte tokens; negative accepts any length
	    timeout (float): Seconds to wait for the response
	    verbose (bool): If True, log detailed progress
	Outputs:
	    list: List of byte token strings on success, otherwise empty list
	"""
	if thisMAC in attSessions:			# ATT engine: a write (e.g. notify-enable) delivers its data as a NOTIFICATION
		ok, zz = attExecGattCmd(thisMAC, cc, timeout)
		if not ok: return []
		if not zz:
			nn = attSessions[thisMAC].waitNotify(timeout=timeout)
			if nn is None:
				U.logger.log(20,"{} ATT: no notification within {}s after {}".format(thisMAC, timeout, cc))
				return []
			zz = ["{:02x}".format(bb) for bb in bytearray(nn[1])]
		if len(zz) == nBytes or nBytes < 0:	return zz
		if verbose: U.logger.log(20,"{} ATT ... ERROR: len:{} != {}, data:{}".format(thisMAC, len(zz), nBytes, zz))
		return []
	BF = ""
	AF = ""
	try:
		for kk in range(2):
			if checkIfSwitchbotStopAND(thisMAC): return []
			if checkSwitchBotPrio(thisMAC):  return []
			if verbose:  U.logger.log(20,"{} sendline  cmd:{}, expecting:'{}'".format(thisMAC, cc, expectedTag))
			expCommands[thisMAC].sendline( cc )
			ret = expCommands[thisMAC].expect([expectedTag,"Error","failed",pexpect.TIMEOUT], timeout=timeout)
			if ret == 0:
				if verbose: U.logger.log(20,"{} ... SUCCESS!!".format(thisMAC))
				ret = expCommands[thisMAC].expect("\n")
				xx = toStringAndstripRNetc(expCommands[thisMAC].before)
				zz = xx.split() 
				if len(zz) == nBytes or nBytes < 0:
					if verbose: U.logger.log(20,"{} returning:{}".format(thisMAC, zz))
					return zz
				else:
					U.logger.log(20,"{} ... ERROR: len != {} .. {}".format(thisMAC, nBytes, xx))
					continue
			else:
				BF = toStringAndstripRNetc(expCommands[thisMAC].before)
				AF = toStringAndstripRNetc(expCommands[thisMAC].after) 
				if verbose: U.logger.log(20,"{} ... ERROR, cmd:{}, expectedTag:{}, \nBF:{}--\nAF:{}--".format(thisMAC, cc, expectedTag, BF, AF))
				continue
	except  Exception :
		U.logger.log(20,"", exc_info=True)
	return []




#################################
def readGattcmd(thisMAC, cc, expectedTag, nBytes, timeout, verbose=False):
	"""Sends a gatttool read command on the MAC's session, waits for expectedTag, and parses the following line into whitespace-separated byte tokens, requiring exactly nBytes tokens (or any count if nBytes is negative). Retries up to twice and yields to SwitchBot priority.

	Inputs:
	    thisMAC (str): BLE device MAC address whose session to read from
	    cc (str): gatttool read command string to send
	    expectedTag (str): Expected substring/pattern marking a valid response
	    nBytes (int): Expected number of returned byte tokens; negative accepts any length
	    timeout (float): Seconds to wait for the response
	    verbose (bool): If True, log detailed progress
	Outputs:
	    list: List of byte token strings on success, otherwise empty list
	"""
	if thisMAC in attSessions:			# ATT engine session
		ok, zz = attExecGattCmd(thisMAC, cc, timeout)
		if ok and (len(zz) == nBytes or nBytes < 0):	return zz
		if ok and verbose: U.logger.log(20,"{} ATT ... ERROR: len:{} != {}, data:{}".format(thisMAC, len(zz), nBytes, zz))
		return []
	BF = ""
	AF = ""
	try:
		for kk in range(2):
			if checkIfSwitchbotStopAND(thisMAC): return []
			if checkSwitchBotPrio(thisMAC):  return []
			if verbose: U.logger.log(20,"{} sendline  cmd:{}, expecting:'{}'".format(thisMAC, cc, expectedTag))
			expCommands[thisMAC].sendline( cc )
			ret = expCommands[thisMAC].expect([expectedTag,"Error","failed",pexpect.TIMEOUT], timeout=timeout)
			if ret == 0:
				if verbose: U.logger.log(20,"{} ... SUCCESS!!".format(thisMAC))
				ret = expCommands[thisMAC].expect("\n")
				xx = toStringAndstripRNetc(expCommands[thisMAC].before)
				zz = xx.split() 
				if len(zz) == nBytes or nBytes < 0:
					return zz
				else:
					if verbose: U.logger.log(20,"{} ... ERROR: len:{} != {}, retCode:{}".format(thisMAC, len(zz), nBytes, xx))
					continue
			else:
				BF = toStringAndstripRNetc(expCommands[thisMAC].before)
				AF = toStringAndstripRNetc(expCommands[thisMAC].after) 
				if verbose: U.logger.log(20,"{} .. ERROR, cmd:{}, expectedTag:{} \nBF:{}--\nAF:{}--".format(thisMAC, cc, expectedTag, BF, AF))
				continue
	except  Exception :
		U.logger.log(20,"", exc_info=True)
	return []



#################################
def batchGattcmd(useHCI, thisMAC, cc, expectedTag, nBytes=0, retryCMD=3, verbose=False, timeout=6, thisIsASwitchbotCommand = False):
	"""Runs a one-shot gatttool command via a timeout-wrapped subprocess (readPopen) instead of an interactive session, retrying up to retryCMD times until the output contains expectedTag. Coordinates with a global flag so SwitchBot and non-SwitchBot commands do not run concurrently, and parses the output into nBytes byte tokens.

	Inputs:
	    useHCI (str): HCI adapter identifier passed to gatttool -i
	    thisMAC (str): BLE device MAC address to query
	    cc (str): gatttool command arguments string
	    expectedTag (str): Expected substring in the command output
	    nBytes (int): Expected number of byte tokens; 0 returns the tag, negative accepts any length
	    retryCMD (int): Maximum number of command attempts
	    verbose (bool): If True, log detailed progress
	    timeout (float): Seconds passed to the timeout wrapper around gatttool
	    thisIsASwitchbotCommand (bool): Marks the command as a SwitchBot command for concurrency arbitration
	Outputs:
	    str or list: expectedTag when nBytes==0, a list of byte tokens on success, or empty list on failure
	"""
	global currentActiveGattCommandisSwitchBot

	if gattEngineIsATT():				# ATT engine: one-shot = connect - execute - disconnect, no gatttool process
		if currentActiveGattCommandisSwitchBot and not thisIsASwitchbotCommand: return []
		for ii in range(100):
			if not currentActiveGattCommandisSwitchBot: break
			time.sleep(0.2)
		currentActiveGattCommandisSwitchBot = thisIsASwitchbotCommand
		zz  = []
		okC = False
		try:
			ownSession = thisMAC not in attSessions
			if (not ownSession) or attConnect(thisMAC, "-t random" in cc, connectTimeout=float(timeout) + 6.):
				for kk in range(max(1, int(retryCMD))):
					if checkIfSwitchbotStopAND(thisMAC): break
					okC, zz = attExecGattCmd(thisMAC, cc, timeout)
					if okC and (nBytes == 0 or len(zz) == nBytes or nBytes < 0): break
					okC = False
					time.sleep(0.5)
				if ownSession: attClose(thisMAC)
		except Exception:
			U.logger.log(20,"", exc_info=True)
			attClose(thisMAC)
		currentActiveGattCommandisSwitchBot = False
		if okC:	return expectedTag if nBytes == 0 else zz
		return []

	try:
		if currentActiveGattCommandisSwitchBot and not thisIsASwitchbotCommand : return []
		for ii in range(100):
			if not currentActiveGattCommandisSwitchBot: break
			#if verbose: U.logger.log(20," wait loop currentActiveGattCommandisSwitchBot:{} ".format(currentActiveGattCommandisSwitchBot))
			time.sleep(0.2)

		currentActiveGattCommandisSwitchBot = thisIsASwitchbotCommand
		cmd = "/usr/bin/timeout -s SIGKILL {} /usr/bin/gatttool -i {} -b {} {}".format(timeout, useHCI,  thisMAC, cc)
		if verbose: U.logger.log(20,"{} cmd:{} ;  expecting: '{}'; nbytes:{}, retryCMD:{}, switchBotPresent:{}; switchbotActive:{}; timeout:{}".format(thisMAC, cmd, expectedTag, nBytes, retryCMD, switchBotPresent, switchbotActive, timeout))
		for kk in range(retryCMD):
			if checkIfSwitchbotStopAND(thisMAC): return []
			#if verbose: U.logger.log(20,"try#:{}, switchBotPresent:{}; switchbotActive:{} ".format(kk, switchBotPresent, switchbotActive))
			ret = readPopen(cmd)
			if ret[0].find(expectedTag) > -1:
				if verbose: U.logger.log(20,"{} ... SUCCESS:  0:{}".format(thisMAC,  escape_ansi(ret[0]) ))
				if nBytes == 0: 
					currentActiveGattCommandisSwitchBot = False
					return expectedTag
				# this should work with py2 and py3
				xx = toStringAndstripRNetc(ret[0])
				xx = xx.split() 
				if len(xx) == nBytes or nBytes < 0:
					currentActiveGattCommandisSwitchBot = False
					return xx
				else:
					if verbose: U.logger.log(20,"{} ... ERROR: len:{} != {}, data:{}".format(thisMAC, len(xx), nBytes, xx))
					continue
			else:
				if verbose: U.logger.log(20,"{} ... ERROR: {}".format(thisMAC,  ret[1].strip() ))
			time.sleep(0.5)

	except  Exception :
		U.logger.log(20,"", exc_info=True)
	currentActiveGattCommandisSwitchBot = False
	return []



#################################
beaconBatteryQueue = {}		# pending battery reads for beacon tags: mac -> device entry (battCmd..)
beaconBatteryQueueSince = 0.	# when the low-prio queue first became non-empty (starvation cap)
beaconBatteryQueuedAt = {}		# mac -> when it entered the queue (per-mac serial-fallback patience)
beaconBatteryWatchLastWrite = 0.	# last refresh of beaconloop's battery watch list
beaconBatteryWatchFirstWrite = 0.	# when this batch's list was FIRST given to beaconloop (ack timeout)
beaconBatteryWatchOK = None		# None=waiting for beaconloop's ack (seenMACs file), True=acked, False=no list support -> serial
beaconBatteryWaitLogLast = 0.	# throttle for the "waiting for tags to wake up" log line
BATTWATCH_FRESH    = 15.	# adv (any type) younger than this = tag is online/in range, connect NOW
BATTWATCH_ACK      = 30.	# no seenMACs file (even empty) within this after the first list write -> beaconloop < v10.1, read serially
BATTWATCH_PATIENCE = 900.	# mac not heard for this long after queueing -> old serial listen+connect
singleDongleMode   = False	# True = only one BLE adapter: share it with beaconloop via temp/beaconloop.pause


#################################
lastPauseKeepScan = [False]	# mode of the current pause (list: refreshBeaconloopPause reuses it, no global decl)


def pauseBeaconloopForGatt(keepScan=True):
	"""Single-dongle mode: creates temp/beaconloop.pause so a gatt connect can use the
	shared adapter (max 55 secs failsafe). No-op with 2 dongles.
	keepScan=True (DEFAULT - proven live 3/3): beaconloop only stops the iBeacon
	ADVERTISING and leaves its LE scan RUNNING - the kernel stops/restarts the scan itself
	around its create-connection; connects succeed in 3-7s in that environment, while a
	pre-disabled scan (keepScan=False, the old full pause) made every create-connection
	on the onboard radio time out (15s AND 25s pending, tag connectable at rssi -6x)."""
	if not singleDongleMode: return
	try:
		lastPauseKeepScan[0] = keepScan
		f = open(G.homeDir+"temp/beaconloop.pause","w")
		f.write(json.dumps({"ts": time.time(), "keepScan": True}) if keepScan else "{}".format(time.time()))
		f.close()
		# adv-only stop lands ~0.1s after beaconloop sees the file - 0.4s is plenty;
		# only the old full pause (scan teardown) needed the long settle
		time.sleep(0.4 if keepScan else 1.2)
	except Exception:
		U.logger.log(20,"", exc_info=True)


#################################
def resumeBeaconloop():
	"""Single-dongle mode: removes temp/beaconloop.pause -> beaconloop resumes scanning."""
	if not singleDongleMode: return
	try:
		if os.path.isfile(G.homeDir+"temp/beaconloop.pause"): os.remove(G.homeDir+"temp/beaconloop.pause")
	except Exception:
		U.logger.log(20,"", exc_info=True)
lastBeepPendingCheck = [0., False]	# [last file check time, result] - throttled beep-pending flag


#################################
def beaconBeepPending():
	"""True if a beacon beep job is queued (temp/BLEconnect.beep). File check throttled to
	every 0.5 secs so it is cheap enough for the sensor retry loops."""
	tt = time.time()
	if tt - lastBeepPendingCheck[0] > 0.5:
		lastBeepPendingCheck[0] = tt
		try:	lastBeepPendingCheck[1] = os.path.isfile(G.homeDir+"temp/BLEconnect.beep")
		except:	lastBeepPendingCheck[1] = False
	return lastBeepPendingCheck[1]


#################################
attSessions = {}		# mac -> gattAttClient.GattSession (ATT gatt engine, replaces the gatttool pexpect session)
myBLEmac    = ""		# our dongle's own BLE mac (set by execBLEconnect/startHCI; used to pin the ATT socket)
ENOSYS_RETRIES = 5		# ATT connect: retry an intermittent ENOSYS (adapter refuses create-connection) this many times, 1s apart
knownBeaconTags = {}	# switchbot device-type definitions from temp/knownBeaconTags - MUST exist even when the file is missing (NameError killed readParams before)
lastLoggedGattEngine = [""]	# log the engine decision once per change (list: no global decl needed)


#################################
def gattEngineIsATT():
	"""True when the rpi is configured (BLEconnectMode == attSocket) AND the stdlib ATT
	client imported (py3.3+/Linux). Everything else keeps the gatttool engine."""
	return attClientPresent and BLEconnectMode == "attSocket"


#################################
def attConnect(mac, useRandom, connectTimeout=12.):
	"""Opens an ATT session to a beacon tag (LE L2CAP socket - the kernel creates the
	connection, no gatttool process). Bound to our own dongle (myBLEmac). True/False.
	The kernel keeps the create-connection pending for the WHOLE timeout - a long
	timeout is what catches sparse advertisers (tag only connectable for a moment
	every few secs). ENOSYS (= "Function not implemented", the connect adapter refusing
	create-connection - often the onboard Pi BT, busy/out of slots) is INTERMITTENT, so
	we retry it up to ENOSYS_RETRIES times with a 0.4s wait; it also feeds the wedge
	counter -> main loop restarts the BLE stack at >20. Non-ENOSYS failures (timeout,
	ETIMEDOUT) already consumed their window and are not immediately retried here."""
	global counterFunctionNotImplemented
	attClose(mac)
	try:
		for attempt in range(ENOSYS_RETRIES):
			t0   = time.time()
			sess = gattAttClient.GattSession(mac, randomAddr=useRandom, adapterMac=myBLEmac, connectTimeout=connectTimeout)
			if sess.connect():
				attSessions[mac] = sess
				counterFunctionNotImplemented = 0
				U.logger.log(20,"{} ATT session connected after {:.1f}s (no gatttool){}".format(
								mac, time.time()-t0, "" if attempt == 0 else " on ENOSYS-retry #{}".format(attempt)))
				return True
			isENOSYS = "ENOSYS" in sess.lastError
			if isENOSYS: counterFunctionNotImplemented += 1
			# SO_ERROR:ENOSYS/EIO right after a heard adv = the connect ADAPTER refused create-connection
			# (busy/out-of-slots/weak controller - often the onboard Pi BT); "connect timeout" = never found;
			# fast ETIMEDOUT = HCI 0x3E "Connection Failed to be Established" (tag found, link not held)
			U.logger.log(20,"{} ATT connect failed after {:.1f}s of {:.0f}s on {} (mac {}): {} (wedgeCount:{}, attempt {}/{})".format(
							mac, time.time()-t0, connectTimeout, useHCI, myBLEmac, sess.lastError, counterFunctionNotImplemented, attempt+1, ENOSYS_RETRIES))
			if isENOSYS and attempt == 0:
				# ENOSYS = the controller REFUSED create-connection, and the error alone never says
				# why. The usual reason is the single LE initiator slot still being held by a
				# pending or stale link - invisible unless we ask. Log the link state once per job
				# (not per attempt): a slow beep then tells whether something squats the slot,
				# which is the one thing the blind 0.4s retry ladder cannot distinguish.
				try:
					con = readPopen("sudo hcitool -i {} con".format(useHCI))
					U.logger.log(20,"{} ENOSYS diag - {} links: {}".format(mac, useHCI, "{}".format(con[0]).replace("\n","; ").strip()))
				except Exception:	pass
			if not isENOSYS:
				break						# timeout / ETIMEDOUT etc. won't benefit from an immediate retry
			time.sleep(0.4)					# brief breather; live logs show the slot frees within well under a second
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return False


#################################
def attClose(mac):
	"""Closes and forgets the ATT session of this mac (never raises)."""
	sess = attSessions.pop(mac, None)
	if sess is not None:
		try:	sess.close()
		except Exception:	pass


#################################
def gattEngineConnect(mac, useRandom, retryConnect, nTries, gattTimeout=6, bleTimeout=15):
	"""Connects with the configured gatt engine: ATT session (attSocket mode) or the
	gatttool pexpect session. True when a session is established. The ATT timeout
	mirrors gatttool's persistence (retryConnect sends of "connect" a ~15s wait each):
	sparse advertisers need the long pending create-connection to catch a window."""
	if gattEngineIsATT():
		for ii in range(max(1, int(nTries))):
			if attConnect(mac, useRandom, connectTimeout=float(bleTimeout)):	# bleTimeout = how long the kernel keeps create-connection pending
				return True
		return False
	return launchGATT(useHCI, mac, gattTimeout, bleTimeout, retryConnect=retryConnect, random=useRandom, nTries=nTries, verbose=True) == "ok"


#################################
def attExecGattCmd(mac, cc, timeout=5):
	"""Executes ONE gatttool-SYNTAX command string on the open ATT session of this mac -
	the tag database (knownBeaconTags.json battCmd/beep) keeps its gatttool command
	strings unchanged. Supported: char-write-req / char-write-cmd / char-read-hnd /
	char-read-uuid. Returns (ok, values); values = list of 2-char hex byte strings
	(the same format the gatttool output parsers deliver), [] for writes."""
	sess = attSessions.get(mac)
	if sess is None:
		return False, []
	try:
		cc = "{}".format(cc).strip()
		m = re.match(r"char-write-(req|cmd)\s+(?:0x)?([0-9a-fA-F]+)\s+([0-9a-fA-F]+)$", cc)
		if m:
			handle = int(m.group(2), 16)
			data   = bytes(bytearray.fromhex(m.group(3)))
			if m.group(1) == "req":
				ok = sess.writeReq(handle, data, timeout)
			else:
				ok = sess.writeCmd(handle, data)
			if not ok: U.logger.log(20,"{} ATT write failed: {} ({})".format(mac, cc, sess.lastError))
			return ok, []
		m = re.match(r"char-read-hnd\s+(?:0x)?([0-9a-fA-F]+)$", cc)
		if m:
			val = sess.readHnd(int(m.group(1), 16), timeout)
			if val is None:
				U.logger.log(20,"{} ATT read failed: {} ({})".format(mac, cc, sess.lastError))
				return False, []
			return True, ["{:02x}".format(bb) for bb in bytearray(val)]
		m = re.match(r"char-read-uuid\s+(?:0x)?([0-9a-fA-F]{4})$", cc)
		if m:
			res = sess.readUUID(int(m.group(1), 16), timeout)
			if res is None:
				U.logger.log(20,"{} ATT read-uuid failed: {} ({})".format(mac, cc, sess.lastError))
				return False, []
			return True, ["{:02x}".format(bb) for bb in bytearray(res[1])]
		if cc.startswith("--char-write-req") or cc.startswith("--char-read"):	# batchGattcmd one-shot syntax
			mH = re.search(r"--handle=(?:0x)?([0-9a-fA-F]+)", cc)
			mV = re.search(r"--value=([0-9a-fA-F]+)", cc)
			if mH is not None and cc.startswith("--char-write-req") and mV is not None:
				ok = sess.writeReq(int(mH.group(1), 16), bytes(bytearray.fromhex(mV.group(1))), timeout)
				if not ok: U.logger.log(20,"{} ATT write failed: {} ({})".format(mac, cc, sess.lastError))
				return ok, []
			if mH is not None and cc.startswith("--char-read"):
				val = sess.readHnd(int(mH.group(1), 16), timeout)
				if val is None:
					U.logger.log(20,"{} ATT read failed: {} ({})".format(mac, cc, sess.lastError))
					return False, []
				return True, ["{:02x}".format(bb) for bb in bytearray(val)]
		U.logger.log(20,"{} ATT engine: unsupported gatt cmd syntax: {}".format(mac, cc))
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return False, []


#################################
def sendBeaconGattCmd(mac, cc, timeout=5):
	"""Sends one gatttool command on the open session of a beacon tag and waits for the prompt
	(same expect pattern beaconloop's beep uses). Returns True on prompt, False otherwise.
	With the ATT engine the command string is executed on the ATT session instead."""
	if mac in attSessions:
		ok, values = attExecGattCmd(mac, cc, timeout)
		return ok
	try:
		expCommands[mac].sendline(cc)
		ret = expCommands[mac].expect([mac, "Error", "failed", pexpect.TIMEOUT], timeout=timeout)
		return ret == 0
	except Exception as e:
		U.logger.log(20,"{} gatt session error ({}) for cmd:{}".format(mac, type(e).__name__, cc))
	return False


#################################
def waitForAdvBeaconloop(mac, maxWait=20):
	"""Asks beaconloop - which is scanning anyway - to watch for a CONNECTABLE
	advertisement of this mac (temp/beaconloop.watchMAC -> temp/beaconloop.seenMAC).
	No own scan process needed, and on single-dongle rpis the beacon tracking keeps
	running during the whole wait. Returns True (seen) / False (timeout) /
	None (beaconloop not alive -> caller falls back to the own scan)."""
	try:
		fnAlive = G.homeDir+"temp/alive.beaconloop"
		if not (os.path.isfile(fnAlive) and time.time() - os.path.getmtime(fnAlive) < 90.): return None
		req  = G.homeDir+"temp/beaconloop.watchMAC"
		seen = G.homeDir+"temp/beaconloop.seenMAC"
		try:	os.remove(seen)
		except Exception: pass
		f = open(req,"w"); f.write(json.dumps({"mac": mac, "ts": time.time(), "maxWait": maxWait})); f.close()
		t0 = time.time()
		while time.time() - t0 < maxWait:
			if os.path.isfile(seen):
				# beaconloop >= v12.7 reports {"ts":.., "rssi":..} - log the rssi: a connect timeout
				# despite strong rssi = adapter problem, weak rssi = tag likely cannot hear us back
				rssiTxt = ""
				try:
					dd = json.load(open(seen))
					if isinstance(dd, dict) and "rssi" in dd: rssiTxt = " (rssi {})".format(dd["rssi"])
				except Exception: pass
				U.logger.log(20,"{} CONNECTABLE adv reported by beaconloop after {:.1f}s{} - connecting NOW".format(mac, time.time()-t0, rssiTxt))
				try:	os.remove(seen)
				except Exception: pass
				try:	os.remove(req)
				except Exception: pass
				return True
			time.sleep(0.05)
		U.logger.log(20,"{} no connectable adv reported by beaconloop within {}s".format(mac, maxWait))
		try:	os.remove(req)
		except Exception: pass
		return False
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return None


#################################
def waitForBeaconAdv(mac, maxWait=15):
	"""Watches our own adapter for an advertisement of this mac (raw HCI socket, active
	scan) and returns as soon as one is seen - connecting immediately after an
	advertisement has a far higher success rate on tags with long/intermittent
	advertising intervals (iTrack etc.) than blindly retrying into timeouts.
	Returns True if seen, False on timeout or no raw backend (caller connects anyway)."""
	if not rawhciPresent: return False
	sock = None
	try:
		macRev = bytes(bytearray(int(x,16) for x in reversed(mac.split(":"))))
		devId  = int("0"+useHCI.replace("hci",""))
		sock = rawhci.hci_open_dev(devId)
		flt = rawhci.hci_filter_new()
		rawhci.hci_filter_all_events(flt)
		rawhci.hci_filter_set_ptype(flt, rawhci.HCI_EVENT_PKT)
		# kernels >= 6.1.91/6.6.30 reject filters shorter than sizeof(struct hci_ufilter)=16
		# with EINVAL (pybluez delivers 14 bytes) - pad; old kernels accept 16 identically
		flt = bytes(flt);	flt += b"\x00" * max(0, 16 - len(flt))
		sock.setsockopt(rawhci.SOL_HCI, rawhci.HCI_FILTER, flt)
		sock.settimeout(1.0)
		try:	rawhci.hci_send_cmd(sock, 0x08, 0x000C, struct.pack("<BB", 0x00, 0x00))	# scan off (params need it)
		except Exception: pass
		time.sleep(0.05)
		rawhci.hci_send_cmd(sock, 0x08, 0x000B, struct.pack("<BHHBB", 0x01, 0x0010, 0x0010, 0x00, 0x00))	# active scan params
		rawhci.hci_send_cmd(sock, 0x08, 0x000C, struct.pack("<BB", 0x01, 0x00))			# scan on, all packets
		t0 = time.time()
		nSeen = 0
		while time.time() - t0 < maxWait:
			try:	pkt = sock.recv(255)
			except Exception:	continue
			# LE meta event, legacy (0x02) or extended (0x0D) advertising report; mac reversed on the wire.
			# only CONNECTABLE frames count - these tags mostly broadcast non-connectable frames,
			# and connecting after one of those still times out (the radio is not listening)
			if len(pkt) > 13 and pkt[0] == 0x04 and pkt[1] == 0x3E:
				if pkt[3] == 0x02:								# legacy report
					if pkt[7:13] == macRev:
						nSeen += 1
						if pkt[5] in (0x00, 0x01):				# ADV_IND / ADV_DIRECT_IND = connectable
							U.logger.log(20,"{} CONNECTABLE advertisement seen after {:.1f}s - connecting NOW".format(mac, time.time()-t0))
							return True
				elif pkt[3] == 0x0D and len(pkt) >= 14:			# extended report (BT5)
					if pkt[8:14] == macRev:
						nSeen += 1
						if (pkt[5] | (pkt[6] << 8)) & 0x01:		# connectable bit
							U.logger.log(20,"{} CONNECTABLE advertisement seen after {:.1f}s - connecting NOW".format(mac, time.time()-t0))
							return True
		U.logger.log(20,"{} no CONNECTABLE advertisement within {}s ({} non-connectable frames seen) - trying to connect anyway".format(mac, maxWait, nSeen))
	except Exception as e:
		U.logger.log(20,"waitForBeaconAdv unavailable ({}) - connecting blindly".format(e))
	finally:
		try:
			if sock is not None:
				rawhci.hci_send_cmd(sock, 0x08, 0x000C, struct.pack("<BB", 0x00, 0x00))	# scan off
				sock.close()
		except Exception: pass
	return False


#################################
def refreshBeaconloopPause():
	"""Single-dongle: renews the pause-file timestamp so a longer listen+connect sequence
	does not run into beaconloop's 55 sec pause failsafe. Keeps the mode of the current pause."""
	if not singleDongleMode: return
	try:
		f = open(G.homeDir+"temp/beaconloop.pause","w")
		f.write(json.dumps({"ts": time.time(), "keepScan": True}) if lastPauseKeepScan[0] else "{}".format(time.time()))
		f.close()
	except Exception:
		pass


#################################
def beaconGattConnect(mac, useRandom, advJustSeen=False):
	"""Connect to a beacon tag - LISTEN-FAST, CONNECT-PATIENT (vendor-app behaviour):
	a SHORT listen gives a fast path (connect at once when beaconloop already knows the
	tag is connectable), but we then attempt a PATIENT connect whether or not an adv was
	heard. The controller's own LE create-connection catches the tag's brief connectable
	window directly - so our SCANNER missing a connectable frame does NOT mean the tag is
	unconnectable. This is why the vendor app (which never pre-observes an adv, sometimes
	taking a few secs) succeeds ~always where the old listen-GATE gave up on iTrack-style
	sparse advertisers. Two rounds with an adapter reset between (a connect failing right
	after a heard adv points at a wedged adapter). advJustSeen=True -> fast path.
	NOTE: patient connects work best with the ATT engine (attSocket mode), which keeps the
	kernel create-connection pending the whole window exactly like the app; gatttool is
	markedly less reliable at holding a pending connect."""
	if rawhciPresent:
		for round2 in (False, True):
			if advJustSeen and not round2:
				seen = True									# tag provably awake seconds ago - no listen window needed
			elif gattEngineIsATT():
				# ATT engine: NO pre-listen. The kernel's pending create-connection IS the
				# listener - it catches the tag's next connectable adv itself (1-3s typical).
				# Waiting for beaconloop to hear one first only added 1-7s latency per beep
				seen = True
			else:
				seen = waitForAdvBeaconloop(mac, 8)	# SHORT: only the fast path, we connect patiently regardless
				if seen is None:
					seen = waitForBeaconAdv(mac, 8)				# beaconloop not alive: own scan (adapter is free then)
			# single-dongle: adv-only pause for the gatt session (LE scan stays ON - the kernel
			# handles the scan-stop around create-connection itself; live 3/3: full pause = 15s
			# timeout every time, adv-only pause = connected in 3-7s every time)
			pauseBeaconloopForGatt(keepScan=True)
			# connect with TWO SHORTER pending windows instead of one long one: the tag sends
			# connectable frames every 2-4s, so a pending create-connection that has not caught
			# one within ~8s is sitting in an unlucky/half-wedged initiator state (live log:
			# 13.5s single attempt vs 3-5s typical) - cancel + re-issue re-rolls the initiator
			# and is the silent-sibling fix of the ENOSYS retry. Round 2 gets wider windows
			if gattEngineConnect(mac, useRandom, retryConnect=1, nTries=2, gattTimeout=6, bleTimeout=(8 if (seen and not round2) else 12)):
				return True								# caller resumes beaconloop after its commands + disconnect
			U.logger.log(20,"{} connect failed{}{}".format(mac, "" if seen else " (patient connect, no adv heard)", " - giving up" if round2 else " - resetting "+useHCI+" and retrying"))
			try:	disconnectGattcmd(mac, 2)
			except Exception: pass
			expCommands[mac] = ""
			resumeBeaconloop()								# scan again before the 2nd round
			if not round2:
				readPopen("sudo /bin/hciconfig {} reset".format(useHCI))
				time.sleep(1.5)
		# LAST RESORT: both patient ATT rounds timed out although the tag was heard with good
		# rssi - on some radios (single-dongle onboard) the kernel L2CAP connect path starves
		# while gatttool connects fine. Try gatttool ONCE; the diag line shows leftover LE
		# links (a stale pending connection blocks the single initiator slot), and the WARNING
		# on success is the proof that the kernel path - not RF/tag - is at fault.
		if gattEngineIsATT() and os.path.isfile("/usr/bin/gatttool"):
			try:
				con = readPopen("sudo hcitool con")
				U.logger.log(20,"{} diag before gatttool fallback - current links: {}".format(mac, "{}".format(con[0]).replace("\n","; ").strip()))
			except Exception: pass
			pauseBeaconloopForGatt(keepScan=True)	# gatttool's proven environment: scan running, adv off
			if launchGATT(useHCI, mac, 6, 20, retryConnect=2, random=useRandom, nTries=1, verbose=True) == "ok":
				U.logger.log(20,"{} ATT engine could not connect but gatttool fallback DID - kernel L2CAP connect path failing on this radio".format(mac))
				return True
			resumeBeaconloop()
		U.logger.log(20,"{} giving up after 2 patient rounds".format(mac))
		return False

	# no raw backend available: blind ladder as before
	if gattEngineConnect(mac, useRandom, retryConnect=3, nTries=2, gattTimeout=6, bleTimeout=20):
		return True
	U.logger.log(20,"{} connect failed - resetting {} and retrying once".format(mac, useHCI))
	try:
		expCommands[mac] = ""
		attClose(mac)
		readPopen("sudo /bin/hciconfig {} reset".format(useHCI))
		time.sleep(1.5)
	except Exception:
		U.logger.log(20,"", exc_info=True)
	if gattEngineConnect(mac, useRandom, retryConnect=3, nTries=2, gattTimeout=6, bleTimeout=20):
		return True
	try:	disconnectGattcmd(mac, 2)	# never leave a half-open session behind
	except Exception: pass
	expCommands[mac] = ""
	return False


#################################
def doBeaconGattBeep(mac, params):
	"""Executes a beep job for a beacon tag: connect (random/public per tag definition), then
	cmdSeq once (SwitchBot-remote style) OR cmdON repeatedly for beepTime secs followed by
	cmdOff; disconnects afterwards."""
	U.logger.log(20,"BLEconnect beep {}  on {} (singleDongle:{})  params:{}".format(mac, useHCI, singleDongleMode, str(params)[:140]))
	useRandom = (params.get("random","") == "randomON")
	beepTime  = float(params.get("beepTime", 1))
	U.killOldPgm(-1,"gatttool", param1=mac, param2="",verbose=False)	# no leftover gatttool for this mac
	if not beaconGattConnect(mac, useRandom):
		U.logger.log(20,"BLEconnect beep: could not connect to {}".format(mac))
		resumeBeaconloop()
		return
	try:
		cmdONs  = params.get("cmdON",[])
		cmdOffs = params.get("cmdOff",[])
		if isinstance(cmdONs,  str): cmdONs  = [cmdONs]
		if isinstance(cmdOffs, str): cmdOffs = [cmdOffs]
		if params.get("cmdSeq"):
			for cc in params["cmdSeq"]:
				if not sendBeaconGattCmd(mac, cc): break
		elif beepTime <= 0:
			for cc in cmdOffs:
				if not sendBeaconGattCmd(mac, cc): break
		else:
			tEnd  = time.time() + beepTime
			fails = 0
			while time.time() < tEnd:
				for cc in cmdONs:
					if sendBeaconGattCmd(mac, cc):	fails = 0
					else:							fails += 1
				if fails >= 2:
					U.logger.log(20,"BLEconnect beep {}: session dead - aborting".format(mac))
					break
				time.sleep(0.3)
			if fails < 2:
				for cc in cmdOffs:
					if not sendBeaconGattCmd(mac, cc): break
	except Exception:
		U.logger.log(20,"", exc_info=True)
	disconnectGattcmd(mac, 3)
	resumeBeaconloop()


#################################
def processBeepQueueBLEconnect():
	"""HIGHEST priority: executes all queued beacon beeps (temp/BLEconnect.beep, written by
	receiveCommands.py) immediately. Returns True if any beep was processed."""
	fn = G.homeDir+"temp/BLEconnect.beep"
	if not os.path.isfile(fn): return False
	if switchbotActive == "active":
		return False	# let the running switchbot command finish (secs); beep executes next pass
	try:
		f = open(fn,"r"); lines = f.read().strip("\n").split("\n"); f.close()
		os.remove(fn)
		lastBeepPendingCheck[0] = time.time(); lastBeepPendingCheck[1] = False
	except Exception:
		U.logger.log(20,"", exc_info=True)
		return False
	did = False
	for line in lines:
		if line == "": continue
		try:	devices = json.loads(line)
		except Exception: continue
		for mac in devices:
			try:
				doBeaconGattBeep(mac, devices[mac])
				did = True
			except Exception:
				U.logger.log(20,"", exc_info=True)
	return did


#################################
def readBeaconBattery(mac, params, advJustSeen=False):
	"""Connects to a beacon tag and reads its battery level via the tag's battCmd gatt
	command(s); decodes the first returned byte with bits/shift/norm/offset. Returns
	the level (int) or "" on failure. advJustSeen: beaconloop's battery watch list
	just reported a connectable adv of this mac -> connect without a listen window."""
	useRandom = (params.get("random","") == "randomON")
	level = ""
	U.killOldPgm(-1,"gatttool", param1=mac, param2="",verbose=False)
	if not beaconGattConnect(mac, useRandom, advJustSeen=advJustSeen):
		U.logger.log(20,"BLEconnect battery: could not connect to {}".format(mac))
		resumeBeaconloop()
		return level
	try:
		batCMDs = params.get("gattcmd",[])
		if isinstance(batCMDs, str): batCMDs = [batCMDs]
		for cc in batCMDs:
			if isinstance(cc, (int, float)):		# plugin's beep-before-battery inserts a sleep as a number
				time.sleep(float(cc))
				continue
			cc = "{}".format(cc)
			if not cc.startswith("char-read"):		# write commands (e.g. the beep sequence): just send
				sendBeaconGattCmd(mac, cc)
				continue
			if mac in attSessions:
				okATT, zz = attExecGattCmd(mac, cc, 8)
			else:
				zz = writeAndListenGattcmd(mac, cc, "value:", -1, 8)
			if zz:
				try:
					val    = int(zz[0],16)
					bits   = int(params.get("bits",127))
					shift  = int(params.get("shift",0))
					norm   = float(params.get("norm",100))
					offset = float(params.get("offset",0))
					val    = (val >> shift) & bits
					if norm > 0:	level = int(round(val * 100. / norm + offset, 0))
					else:			level = val
					break
				except Exception:
					U.logger.log(20,"", exc_info=True)
	except Exception:
		U.logger.log(20,"", exc_info=True)
	disconnectGattcmd(mac, 3)
	resumeBeaconloop()
	return level


#################################
def doXiaomiTimeSet(mac):
	"""Sets time + timezone on a Xiaomi LYWSD02-style clock: writes the current epoch
	(little-endian, +1 sec for write delay) plus the timezone offset byte (two's
	complement - fixes the old encoding that broke for negative timezones) to
	characteristic handle 0x3e. Uses the pause handshake on single-dongle rpis."""
	U.killOldPgm(-1,"gatttool", param1=mac, param2="",verbose=False)
	ok = False
	if not beaconGattConnect(mac, False):
		U.logger.log(20,"BLEconnect timeSet: could not connect to {}".format(mac))
		resumeBeaconloop()
		return False
	try:
		correctTz = int(-time.timezone // 3600 + time.localtime().tm_isdst)
		correctTT = int(time.time()) + 1				# +1 for write delay
		tsh = ""
		xx  = correctTT
		for div in [256*256*256, 256*256, 256, 1]:
			tsh = "{:02x}".format(xx // div) + tsh		# prepend -> little endian
			xx  = xx % div
		writeback = tsh + "{:02x}".format(correctTz & 0xFF)
		cc = "char-write-req 3e {}".format(writeback)
		U.logger.log(20,"BLEconnect timeSet {}:  cmd:{}  timestamp:{} tz:{}".format(mac, cc, correctTT, correctTz))
		for ii in range(3):
			if sendBeaconGattCmd(mac, cc):
				ok = True
				break
			time.sleep(1)
	except Exception:
		U.logger.log(20,"", exc_info=True)
	disconnectGattcmd(mac, 3)
	resumeBeaconloop()
	U.logger.log(20,"BLEconnect timeSet {} {}".format(mac, "successful" if ok else "FAILED"))
	return ok


#################################
def processTimeSetQueueBLEconnect():
	"""LOW priority (like battery): processes queued Xiaomi clock time-set jobs
	(temp/BLEconnect.updateTimeAndZone, one mac per call). Returns True if one was done."""
	fn = G.homeDir+"temp/BLEconnect.updateTimeAndZone"
	if not os.path.isfile(fn): return False
	try:
		f = open(fn,"r"); lines = f.read().strip("\n").split("\n"); f.close()
		os.remove(fn)
	except Exception:
		U.logger.log(20,"", exc_info=True)
		return False
	did = False
	for line in lines:
		if line == "": continue
		try:	devices = json.loads(line)
		except Exception: continue
		for mac in devices:
			if len(mac) < 10: continue
			try:
				doXiaomiTimeSet(mac)
				did = True
			except Exception:
				U.logger.log(20,"", exc_info=True)
	return did


#################################
def refreshBatteryWatchList():
	"""Battery batch: gives beaconloop the WHOLE pending mac list to watch for connectable
	advs while it is scanning anyway (temp/beaconloop.watchMAC {"macs":[..]}; beaconloop
	accumulates {MAC: lastSeenSecs} in temp/beaconloop.seenMACs). Rewritten every ~20
	secs while the queue is non-empty - that keeps the watch alive (maxWait 60) and
	re-establishes the list after a beep job temporarily replaced the file with its
	single-mac request. Returns True if beaconloop is alive AND speaks the list
	protocol (>= v10.1; no ack -> False, the queue is read serially)."""
	global beaconBatteryWatchLastWrite, beaconBatteryWatchFirstWrite
	try:
		if beaconBatteryWatchOK is False: return False		# beaconloop w/o list support (no ack) - serial mode
		fnAlive = G.homeDir+"temp/alive.beaconloop"
		if not (os.path.isfile(fnAlive) and time.time() - os.path.getmtime(fnAlive) < 90.): return False
		tt = time.time()
		if tt - beaconBatteryWatchLastWrite < 20.: return True
		beaconBatteryWatchLastWrite = tt
		if beaconBatteryWatchFirstWrite == 0:
			beaconBatteryWatchFirstWrite = tt
			try:	os.remove(G.homeDir+"temp/beaconloop.seenMACs")	# a stale answer from a previous batch must not fake the ack
			except Exception: pass
		f = open(G.homeDir+"temp/beaconloop.watchMAC","w")
		f.write(json.dumps({"macs": list(beaconBatteryQueue), "ts": tt, "maxWait": 60.}))
		f.close()
		if beaconBatteryWatchFirstWrite == tt:		# first handover of this batch
			U.logger.log(20,"BLEconnect battery: watch list -> beaconloop: {}".format(list(beaconBatteryQueue)))
	except Exception:
		U.logger.log(20,"", exc_info=True)
		return False
	return True


#################################
def pickBatteryMacToRead(watchAlive):
	"""Selects the next battery-queue mac: the one with the FRESHEST connectable adv
	(beaconloop's temp/beaconloop.seenMACs) within BATTWATCH_FRESH wins -> (mac, True):
	connect immediately, no listen window. Nothing fresh -> ("", False): just wait,
	beaconloop keeps watching and the queue costs nothing. Exceptions: macs queued
	longer than BATTWATCH_PATIENCE without an adv (oldest first), or beaconloop not
	alive at all -> (mac, False): old serial listen+connect path so tags this rpi never
	hears in the scan stream still get their chance and the queue always drains.
	The ack: beaconloop >= v10.1 writes seenMACs (may be {}) as soon as it loads the
	list; no file within BATTWATCH_ACK secs = old beaconloop -> serial for the batch."""
	global beaconBatteryWatchOK, beaconBatteryWaitLogLast
	tt   = time.time()
	seen = {}
	if watchAlive:
		fnSeen = G.homeDir+"temp/beaconloop.seenMACs"
		if os.path.isfile(fnSeen):
			if beaconBatteryWatchOK is not True:
				beaconBatteryWatchOK = True
				U.logger.log(20,"BLEconnect battery: beaconloop acknowledged the watch list")
			try:	seen = json.load(open(fnSeen))
			except Exception: seen = {}
		elif beaconBatteryWatchOK is None and beaconBatteryWatchFirstWrite > 0 and tt - beaconBatteryWatchFirstWrite > BATTWATCH_ACK:
			beaconBatteryWatchOK = False
			U.logger.log(20,"BLEconnect battery: beaconloop did NOT acknowledge the watch list within {:.0f} secs (beaconloop < v10.1?) - reading the queue serially, old listen+connect per mac".format(BATTWATCH_ACK))
			watchAlive = False
	best, bestTs = "", 0.
	for mac in beaconBatteryQueue:
		ts = float(seen.get(mac.upper(), 0.))
		if tt - ts <= BATTWATCH_FRESH and ts > bestTs:
			best, bestTs = mac, ts
	if best != "": return best, True
	if watchAlive:
		waiting = [ m for m in beaconBatteryQueue if tt - beaconBatteryQueuedAt.get(m, tt) > BATTWATCH_PATIENCE ]
		if not waiting:
			if tt - beaconBatteryWaitLogLast > 60.:
				beaconBatteryWaitLogLast = tt
				nHeard = len([ m for m in beaconBatteryQueue if seen.get(m.upper(), 0.) > 0. ])
				U.logger.log(20,"BLEconnect battery: waiting for a queued tag to send a connectable adv ({} queued, {} heard so far)".format(len(beaconBatteryQueue), nHeard))
			return "", False
		waiting.sort(key=lambda m: beaconBatteryQueuedAt.get(m, tt))
		return waiting[0], False
	return list(beaconBatteryQueue)[0], False


#################################
def cleanupBatteryWatch():
	"""Battery queue drained: removes the watch-list request and beaconloop's seenMACs
	answer file (a beep's own single-mac request never exists here - it is written and
	removed synchronously inside waitForAdvBeaconloop)."""
	global beaconBatteryQueuedAt, beaconBatteryWatchLastWrite, beaconBatteryWatchFirstWrite, beaconBatteryWatchOK, beaconBatteryWaitLogLast
	beaconBatteryQueuedAt        = {}
	beaconBatteryWatchLastWrite  = 0.
	beaconBatteryWatchFirstWrite = 0.
	beaconBatteryWatchOK         = None
	beaconBatteryWaitLogLast     = 0.
	for fn in ["temp/beaconloop.watchMAC", "temp/beaconloop.seenMACs"]:
		try:	os.remove(G.homeDir+fn)
		except Exception: pass


#################################
def processBatteryQueueBLEconnect():
	"""LOW priority: loads new battery-read requests (temp/BLEconnect.getBeaconParameters)
	into the pending queue. The WHOLE pending list is handed to beaconloop to watch for
	connectable advs (refreshBatteryWatchList); macs are then read in the order the tags
	actually WAKE UP - a fresh adv means the connect works first try - instead of blindly
	listening up to 40 secs per mac in queue order. At most one read per call; the result
	is merged into temp/batteryread.json which beaconloop picks up and adds to the next
	message of that mac. Returns True if a read was done."""
	global beaconBatteryQueueSince, beaconBatteryWatchLastWrite
	fn = G.homeDir+"temp/BLEconnect.getBeaconParameters"
	if os.path.isfile(fn):
		try:
			f = open(fn,"r"); devices = json.loads(f.read().strip("\n")); f.close()
			os.remove(fn)
			tt = time.time()
			newMacs = []
			for mac in devices:
				if mac in beaconBatteryQueue:
					U.logger.log(20,"BLEconnect battery: {} already queued - request ignored".format(mac))
					continue
				beaconBatteryQueue[mac]    = devices[mac]
				beaconBatteryQueuedAt[mac] = tt
				newMacs.append(mac)
			if newMacs:
				if beaconBatteryQueueSince == 0: beaconBatteryQueueSince = time.time()
				beaconBatteryWatchLastWrite = 0.		# push the new list to beaconloop right away
				U.logger.log(20,"BLEconnect battery queue += {}".format(newMacs))
		except Exception:
			U.logger.log(20,"", exc_info=True)
	if not beaconBatteryQueue:
		beaconBatteryQueueSince = 0.
		return False
	watchAlive = refreshBatteryWatchList()
	mac, advJustSeen = pickBatteryMacToRead(watchAlive)
	if mac == "": return False		# nobody awake yet - beaconloop keeps watching, we keep waiting for free
	entry  = beaconBatteryQueue.pop(mac)
	beaconBatteryQueuedAt.pop(mac, None)
	beaconBatteryWatchLastWrite = 0.	# list shrank - rewrite on the next pass
	if not beaconBatteryQueue:
		cleanupBatteryWatch()
	level  = readBeaconBattery(mac, entry.get("battCmd",{}), advJustSeen=advJustSeen)
	if level == "":
		U.logger.log(20,"BLEconnect battery {}: no result - NOT reported (keeps the last good value in indigo)".format(mac))
		return True
	fnOut  = G.homeDir+"temp/batteryread.json"
	try:
		out = {}
		if os.path.isfile(fnOut):
			try:	out = json.load(open(fnOut))
			except Exception: out = {}
		out[mac] = {"batteryLevel": level, "time": time.time()}
		json.dump(out, open(fnOut,"w"))
		U.logger.log(20,"BLEconnect battery result {} = {} -> batteryread.json".format(mac, level))
	except Exception:
		U.logger.log(20,"", exc_info=True)
	return True


#################################
def checkBeaconGattQueues():
	"""Beacon-tag GATT jobs routed to BLEconnect by receiveCommands.py:
	beep first (highest priority, all pending at once), then at most one low-priority
	battery read per main-loop pass."""
	try:
		if processBeepQueueBLEconnect(): return
		# battery is LOWEST priority: only read one when no regular sensor read
		# (humidity/temp etc. from macList) is currently due
		try:
			tt = time.time()
			for mm in macList:
				if macList[mm].get("type","") != "isBLElongConnectDevice": continue	# only real sensor devices gate the low-prio jobs
				nr  = macList[mm].get("nextRead", None)
				lt  = macList[mm].get("lastTesttt", None)
				rse = macList[mm].get("readSensorEvery", None)
				if nr is None or lt is None or rse is None: continue		# uninitialized entries must not starve the queues
				if tt - nr >= 0 and tt - lt >= float(rse):
					if beaconBatteryQueueSince == 0 or tt - beaconBatteryQueueSince < 120.:
						return		# a sensor read is due -> low-prio jobs wait (starvation cap 120s)
		except Exception:
			pass
		if processTimeSetQueueBLEconnect(): return
		processBatteryQueueBLEconnect()
	except Exception:
		U.logger.log(20,"", exc_info=True)


#################################
def tryToConnectSocket(thisMAC,BLEtimeout,devId):
	"""Opens a raw Bluetooth L2CAP socket and HCI device to connect to the MAC, then issues an HCI Read RSSI request to obtain RSSI and transmit power. Returns a dict of signal data; on repeated IOErrors it eventually restarts the plugin.

	Inputs:
	    thisMAC (str): BLE device MAC address to connect to
	    BLEtimeout (float): Socket timeout in seconds
	    devId (int): HCI device index to open
	Outputs:
	    dict: Dict with rssi/txPower/flag0ok/byte2 keys, or empty dict on connection failure
	"""
	global BLEsocketErrCount

	retdata	 = {"rssi": -999, "txPower": -999,"flag0ok":0,"byte2":0}
	if checkSwitchBotPrio(thisMAC):  return retdata
	if time.time() - lastConnect < 3: time.sleep( max(0,min(0.5,(3.0- (time.time() - lastConnect) ))) )
	U.logger.log(20,"{} starting, using devid:{}".format(thisMAC, devId))

	try:
		for ii in range(5):	 # wait until (wifi) sending is finsihed
			if os.path.isfile(G.homeDir + "temp/sending"):
				time.sleep(0.5)
			else:
				break

		hci_sock = bt.hci_open_dev(devId)
		hci_fd	 = hci_sock.fileno()

		# Connect to device (to whatever you like)
		bt_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
		bt_sock.settimeout(BLEtimeout)

		try:
			result	= bt_sock.connect_ex((thisMAC, 1))	# PSM 1 - Service Discovery
			reqstr = struct.pack("6sB17s", bt.str2ba(thisMAC), bt.ACL_LINK, "\0" * 17)
			request = array.array("c", reqstr)
			handle = fcntl.ioctl(hci_fd, bt.HCIGETCONNINFO, request, 1)
			handle = struct.unpack("8xH14x", request.tostring())[0]
			cmd_pkt=struct.pack('H', handle)
			# Send command to request RSSI
			U.logger.log(20,"send command via socket ")
			socdata = bt.hci_send_req(hci_sock, bt.OGF_STATUS_PARAM, bt.OCF_READ_RSSI, bt.EVT_CMD_COMPLETE, 4, cmd_pkt)
			bt_sock.close()
			hci_sock.close()
			flag0ok	  = struct.unpack('b', socdata[0])[0]
			txPower	  = struct.unpack('b', socdata[1])[0]
			byte2	  = struct.unpack('b', socdata[2])[0]
			rssi	  = struct.unpack('b', socdata[3])[0]
			#print thisMAC, test0, txPower, test2, signal
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
			BLEsocketErrCount += 1
			if BLEsocketErrCount  < 10: return {}
			U.removeFile("{}temp/stopBLE".format(G.homeDir))
			U.logger.log(20,"", exc_info=True)
			U.restartMyself(reason="sock.recv error", delay = 10)

	except Exception :
			U.logger.log(20,"", exc_info=True)
	U.logger.log(10, "{} retdata:{}".format(thisMAC, retdata))
	BLEsocketErrCount = 0
	return retdata



#################################
def tryToConnectSocketStdlib(thisMAC, BLEtimeout, devId):
	"""Phone/watch presence check with the python STDLIB only (gattAttClient.
	classicPresenceRSSI): no pybluez (gone on bookworm) and no hcitool (deprecated).
	Classic L2CAP page to PSM 1 + HCI Read-RSSI - byte-for-byte the same return dict
	and error behavior as the old pybluez tryToConnectSocket (which was py2-only)."""
	global BLEsocketErrCount

	retdata	 = {"rssi": -999, "txPower": -999,"flag0ok":0,"byte2":0}
	if checkSwitchBotPrio(thisMAC):  return retdata
	if time.time() - lastConnect < 3: time.sleep( max(0,min(0.5,(3.0- (time.time() - lastConnect) ))) )
	try:
		for ii in range(5):	 # wait until (wifi) sending is finished
			if os.path.isfile(G.homeDir + "temp/sending"):	time.sleep(0.5)
			else:											break
		try:
			kw = {}
			try:		# older gattAttClient.py on the rpi (partial file send) may lack newer parameters
				varnames = gattAttClient.classicPresenceRSSI.__code__.co_varnames
				if "log" in varnames and iphoneDebug:
					kw["log"] = lambda msg: U.logger.log(20, "{} presenceDBG: {}".format(thisMAC, msg))	# stage diagnostics (page/ACL/Read-RSSI)
				if "adapterMac" in varnames:
					kw["adapterMac"] = myBLEmac		# pin the page to OUR dongle - multi-adapter rpis route via the default adapter otherwise
				if "log" not in varnames or "adapterMac" not in varnames:
					U.logger.log(20, "gattAttClient.py on this rpi is OLDER than BLEconnect.py (partial file send?) - send ALL pgm files")
			except Exception:	pass
			socdata = gattAttClient.classicPresenceRSSI(thisMAC, devId=devId, connectTimeout=BLEtimeout, **kw)
			if socdata is None:
				# phone/watch did not answer the page = normal AWAY - NOT an error:
				# the old 10-strikes error counter restarted BLEconnect after ~40 secs
				# of an absent phone; the counter is now only for real adapter errors
				if iphoneDebug: U.logger.log(20, "{} presence: not reachable (away)".format(thisMAC))
				BLEsocketErrCount = 0
				return retdata
			if len(socdata) == 0:
				# page answered but no reading (reset/refused/link dropped): the phone IS
				# there - keep the previous device state (natural debounce, like the old
				# pybluez path's {} return) instead of flapping to away for one poll
				if iphoneDebug: U.logger.log(20, "{} presence: answered but no reading - keeping previous state".format(thisMAC))
				BLEsocketErrCount = 0
				return {}
			flag0ok	= struct.unpack("b", socdata[0:1])[0]
			txPower	= struct.unpack("b", socdata[1:2])[0]	# legacy field name - actually the handle low byte, kept for compatibility
			byte2	= struct.unpack("b", socdata[2:3])[0]
			rssi	= struct.unpack("b", socdata[3:4])[0]
			retdata["flag0ok"]	= flag0ok
			retdata["byte2"]	= byte2
			if flag0ok == 0 and not (txPower == rssi and rssi == 0):
				retdata["rssi"]		= rssi
				retdata["txPower"]	= txPower
		except (IOError, OSError):
			# real adapter-level error (away is handled via socdata None above)
			for ii in range(30):
				if os.path.isfile(G.homeDir+"temp/stopBLE"):	time.sleep(5)
				else:											break
			BLEsocketErrCount += 1
			if BLEsocketErrCount  < 10: return {}
			U.removeFile("{}temp/stopBLE".format(G.homeDir))
			U.logger.log(20,"", exc_info=True)
			U.restartMyself(reason="sock.recv error", delay = 10)
	except Exception:
			U.logger.log(20,"", exc_info=True)
	if iphoneDebug: U.logger.log(20, "{} presence: rssi:{} txPower:{} flag0ok:{}".format(thisMAC, retdata["rssi"], retdata["txPower"], retdata["flag0ok"]))
	BLEsocketErrCount = 0
	return retdata


#################################
def tryToConnectCommandLine(thisMAC, BLEtimeout):
	"""Connects to a BLE device using command-line hcitool (cc/rssi/tpl) wrapped in a timeout, parsing the textual output to extract RSSI and transmit power. Retries up to twice and waits for any in-progress WiFi sending to finish first.

	Inputs:
	    thisMAC (str): BLE device MAC address to query
	    BLEtimeout (float): Seconds passed to the hcitool timeout wrapper
	Outputs:
	    dict: Dict with rssi/txPower/flag0ok/byte2 keys, or empty dict on error
	"""
	global nonSwitchBotActive

	try:
		nonSwitchBotActive = "tryToConnectCommandLine-"+thisMAC
		retdata	 = {"rssi": -999, "txPower": -999,"flag0ok":0,"byte2":0}
		if checkSwitchBotPrio(thisMAC):  return retdata
		if time.time() - lastConnect < 3: 
			time.sleep( max(0,min(0.5,(3.0- (time.time() - lastConnect) ))) )

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
			cmd = "sudo timeout -s SIGINT {:.1f}s hcitool -i {}  cc {};sleep 0.2; hcitool -i {} rssi {} ;sleep 0.2;hcitool -i {} tpl {}".format(BLEtimeout, useHCI, thisMAC, useHCI,  thisMAC, useHCI, thisMAC)
			#U.logger.log(20, cmd)
			ret = readPopen(cmd)
			parts = ret[0].strip("\n").split("\n")
			#U.logger.log(20, "cmd:{}; {}  1. try ret: {} --- err>>{}<<".format(cmd, thisMAC, ret[0].strip("\n"), ret[1].strip("\n")))

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

	except  Exception :
			U.logger.log(20,"", exc_info=True)
			retdata = {}
	
	#U.logger.log(20, "{} return data: {}".format(thisMAC, retdata))
	nonSwitchBotActive = ""
	return retdata


#################################
def BLEXiaomiMiTempHumSquare(thisMAC, data0):
	"""Reads a Xiaomi Mi square temperature/humidity BLE sensor by launching gatttool, enabling notifications (char-write-req 0038 0100), and parsing the notification value into temperature, humidity, battery voltage and computed battery level. Applies configured offsets, flags changed data, and updates the per-MAC state in macList.

	Inputs:
	    thisMAC (str): BLE device MAC address of the sensor
	    data0 (dict): Base data dict deep-copied and populated with the reading
	Outputs:
	    dict or str: Data dict with sensor values/flags, or '' if it yielded to a SwitchBot command
	"""
	global nonSwitchBotActive

	nonSwitchBotActive = "BLEXiaomiMiTempHumSquare-"+thisMAC
	data = copy.deepcopy(data0)
	data["mac"] = thisMAC
	if thisMAC not in expCommands:
		expCommands[thisMAC] = ""
	try:
		verbose = False
		"""
		will take ~ 8-12 secs to connect then send data every 5 secs or so, 
			when issuing command immediate afterwards, will likely retuurn data, when waiting for more than 10 secs it will need a pause of > 1 minute 
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
		if verbose: U.logger.log(20,"{} trying hci:{}".format(thisMAC, useHCI))
		if time.time() - macList[thisMAC]["nextRead"] < 0 or time.time() - macList[thisMAC]["lastTesttt"] < macList[thisMAC]["readSensorEvery"]: return data

		minWaitAfterBadRead = max(5,macList[thisMAC]["readSensorEvery"]/3)
		macList[thisMAC]["nextRead"] = time.time() + minWaitAfterBadRead
		for ii in range(1):
			if checkSwitchBotPrio(thisMAC): return ""

			startCMD = time.time()

			if launchGATT(useHCI, thisMAC, 4, 25, retryConnect=2, verbose=verbose) != "ok": continue
			if expCommands[thisMAC] == "":
				macList[thisMAC]["nextRead"] = time.time() + minWaitAfterBadRead
				macList[thisMAC]["triesWOdata"] +=1
				data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
				if macList[thisMAC]["triesWOdata"] > maxTrieslongConnect:
					macList[thisMAC]["triesWOdata"] = 0
					#U.logger.log(20,"{} not connected, send to indigo, triesWOdata:{}, retryCMD in {} secs".format(thisMAC, macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
					data["connected"] = False
					data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
				if verbose: U.logger.log(20,"not connected, triesWOdata:{}, retryCMD in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
				disconnectGattcmd(thisMAC, 2)
				nonSwitchBotActive = ""
				return data

			readData = []

			for nn in range(2):
				if checkSwitchBotPrio(thisMAC):
					disconnectGattcmd(thisMAC, 2)
					nonSwitchBotActive = ""
					return ""

				readData = writeAndListenGattcmd( thisMAC, "char-write-req 0038 0100", "value:", 5, 15, verbose=verbose)
				if readData != []: break
				time.sleep(1)
			disconnectGattcmd(thisMAC, 2)


			if verbose:U.logger.log(20, "{}  {}. try ret:{}".format(thisMAC, ii, readData))
			if len(readData) == 5:
				data["temp"] 			= round( signedIntfrom16(readData[1]+readData[0])/100. + macList[thisMAC]["offsetTemp"],1) 
				data["hum"]  			= int( int(readData[2],16) + macList[thisMAC]["offsetHum"] )
				data["batteryVoltage"]	= int(readData[4]+readData[3],16)
				data["batteryLevel"]	= batLevelTempCorrection(data["batteryVoltage"], data["temp"], batteryVoltAt100 = 3000, batteryVoltAt0=2700. )
				data["connected"]   	= True
				data["dataRead"]		= True
				macList[thisMAC]["triesWOdata"] = 0
				#U.logger.log(20, "{} return data: {}".format(thisMAC, data))

				if macList[thisMAC]["lastData"] == {}:
					macList[thisMAC]["lastData"] 			= copy.deepcopy(data)
					macList[thisMAC]["lastData"]["temp"]	= -10000.
					macList[thisMAC]["lastTesttt"] 			= 0.

				if ( abs(data["temp"] - macList[thisMAC]["lastData"]["temp"])      > 0.5	or
					 abs(data["hum"]  - macList[thisMAC]["lastData"]["hum"])       > 2):
						data["dataChanged"]	= True
				macList[thisMAC]["lastTesttt"] = time.time()
				macList[thisMAC]["lastData"]  = copy.deepcopy(data)
				nonSwitchBotActive = ""
				return data

			macList[thisMAC]["triesWOdata"] += 1

		data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
		if macList[thisMAC]["triesWOdata"] >= maxTrieslongConnect:
			macList[thisMAC]["triesWOdata"] = 0
			#U.logger.log(20,"error, connected but no data, triesWOdata:{} repeast in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))

	except  Exception :
		U.logger.log(20,"", exc_info=True)
		data["badSensor"] = True
	
	#U.logger.log(20, "{} return data: {}".format(thisMAC, data))
	
	nonSwitchBotActive = ""
	return data



#################################
def BLEXiaomiMiVegTrug(thisMAC, data0):
	"""Reads a Xiaomi Mi / VegTrug plant sensor over gatttool: triggers a read (char-write-req 33 A01F), then reads handle 38 (battery/firmware version) and handle 35 (temp, illuminance, moisture, conductivity), parsing the little-endian byte data. Flags changed data and updates per-MAC state in macList.

	Inputs:
	    thisMAC (str): BLE device MAC address of the sensor
	    data0 (dict): Base data dict deep-copied and populated with the reading
	Outputs:
	    dict or None: Data dict with sensor values/flags, or None on connection failure or SwitchBot yield
	"""
	global nonSwitchBotActive

	nonSwitchBotActive = "BLEXiaomiMiVegTrug0-"+thisMAC
	data = copy.deepcopy(data0)
	if thisMAC not in expCommands:
		expCommands[thisMAC] = ""
	try:
		verbose = False
		verbose0 = False
		if verbose0: U.logger.log(20,"{}  tries:{}, test1:{}, test2:{}".format(thisMAC, macList[thisMAC]["triesWOdata"], time.time() - macList[thisMAC]["nextRead"] < 0 , time.time() - macList[thisMAC]["lastTesttt"] < macList[thisMAC]["readSensorEvery"]))
		if time.time() - macList[thisMAC]["nextRead"] < 0 or time.time() - macList[thisMAC]["lastTesttt"] < macList[thisMAC]["readSensorEvery"]: return data
		#print "BLEXiaomiMiVegTrug ", thisMAC

		minWaitAfterBadRead = min(20,max(5,macList[thisMAC]["readSensorEvery"]/3))
		macList[thisMAC]["nextRead"] = time.time() + minWaitAfterBadRead

		"""
		# start reading:  char-write-req 33 A01F

		get fist set: char-read-hnd 38
		# 7b in l endian
		#    0: batteryLevel
		#    1: ??
		#  2-6: fw eg: '56 2d 33 2e 32 2e 34', 

		get second set: char-read-hnd 35
		# 16b in l endian
		#   0-1: temp *10 [C]
		#     2: ??
		#   3-6: bright [lux]
		#     7: moist [%]
		#   8-9: conduct [S/cm]
		# 10-15: ?? 
		# eg: 'f4 00 69 00 00 00 00 1d 11 01 02 3c 00 fb 34 9b'
		"""
			
		if launchGATT(useHCI, thisMAC, 4,5, verbose=verbose, waitbetween=0.5) != "ok": 
			return None

		time.sleep(.2)
		if checkSwitchBotPrio(thisMAC): 
			disconnectGattcmd(thisMAC, 2)
			return None
		nonSwitchBotActive = "BLEXiaomiMiVegTrug1-"+thisMAC
		if expCommands[thisMAC] == "":
			macList[thisMAC]["triesWOdata"] +=1
			data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
			if macList[thisMAC]["triesWOdata"] > maxTrieslongConnect:
				macList[thisMAC]["triesWOdata"] = 0
				#U.logger.log(20,"{} error, not connected, sending not connected to indigo, triesWOdata:{}, retrying in {} secs".format(thisMAC, macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
				U.logger.log(20,"{}  error, not connected, triesWOdata:{} retrying in {} secs".format(thisMAC, macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
			macList[thisMAC]["lastTesttt"] = time.time() - 90
			disconnectGattcmd(thisMAC, 2)
			return data

		result1 = []
		result2 = []

		for nn in range(1):
			if checkSwitchBotPrio(thisMAC): return None
			time.sleep(.1)
			if not writeGattcmd(thisMAC,  "char-write-req 33 A01F", "Characteristic value was written successfully", 5, verbose=verbose):
				nonSwitchBotActive = ""
				disconnectGattcmd(thisMAC, 2)
				return None

			time.sleep(0.1)
			result1 = readGattcmd(thisMAC,  "char-read-hnd 38", "Characteristic value/descriptor:", 7, 5, verbose=verbose)
			if checkSwitchBotPrio(thisMAC): 
				disconnectGattcmd(thisMAC, 2)
				return None
			if result1 == []:		continue

			time.sleep(0.1)
			result2 = readGattcmd(thisMAC,  "char-read-hnd 35", "Characteristic value/descriptor:", 16, 5, verbose=verbose)
			if checkSwitchBotPrio(thisMAC): 
				disconnectGattcmd(thisMAC, 2)
				return None
			if result2 == []:		continue

			break

		nonSwitchBotActive = "BLEXiaomiMiVegTrug2-"+thisMAC
		disconnectGattcmd(thisMAC, 2)
		nonSwitchBotActive = ""

		if verbose0: U.logger.log(20,"connect results:{} - {}".format(result1, result2))

		if result1 == [] or result2 == []:
			data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
			if macList[thisMAC]["triesWOdata"] >= maxTrieslongConnect:
				macList[thisMAC]["triesWOdata"] = 0
				if verbose0: U.logger.log(20,"error connected but do data, send not connetced to indigo, triesWOdata:{}, retrying in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
			macList[thisMAC]["lastTesttt"] = time.time() - 90
			nonSwitchBotActive = ""
			return data

		data["batteryLevel"]		= int(result1[0],16)
		try:	data["Version"]		= "".join(result1[2:]).decode("hex")
		except: data["Version"]		= "unknown"
		data["temp"]  				= round( signedIntfrom16(result2[1]+result2[0])/10., 1)
		data["Illuminance"]			= int(result2[6]+result2[5]+result2[4]+result2[3],16)
		data["Moisture"] 			= int(result2[7],16)
		data["Conductivity"]		= int(result2[9]+result2[8],16)
		data["dataRead"]			= True
		data["connected"]			= True
		macList[thisMAC]["triesWOdata"] = 0

		if macList[thisMAC]["lastData"] == {}:
			macList[thisMAC]["lastData"] 			= copy.deepcopy(data)
			macList[thisMAC]["lastData"]["temp"]	= -10000.
			macList[thisMAC]["lastTesttt"] 			= time.time() - 90

		if ( abs(data["temp"] 			- macList[thisMAC]["lastData"].get("temp",-100))			> 0.5 	or
			 abs(data["Moisture"]  		- macList[thisMAC]["lastData"].get("Moisture",-100))		> 2 	or
			 abs(data["Conductivity"]	- macList[thisMAC]["lastData"].get("Conductivity",-100))	> 2 ):
			macList[thisMAC]["lastTesttt"] = time.time()
			macList[thisMAC]["lastData"]  = copy.deepcopy(data)
			data["dataChanged"]			=  True
		if verbose0: U.logger.log(20, "{} return data: {}".format(thisMAC, data))
		nonSwitchBotActive = ""
		return data


	except  Exception :
		U.logger.log(20,"", exc_info=True)
		nonSwitchBotActive = ""
		data["badSensor"] = True
	
	if verbose0: U.logger.log(20, "{} return data: {}".format(thisMAC, data))
	
	nonSwitchBotActive = ""
	return data



#################################
def BLEinkBirdPool01B(thisMAC, data0):
	"""Reads an InkBird pool thermometer over a one-shot gatttool read (batchGattcmd on the configured handle), decoding the first two little-endian bytes into temperature with the configured offset. Flags changed data and updates per-MAC state in macList.

	Inputs:
	    thisMAC (str): BLE device MAC address of the sensor
	    data0 (dict): Base data dict deep-copied and populated with the reading
	Outputs:
	    dict: Data dict with temperature and connection flags, or with badSensor set on error
	"""
	global nonSwitchBotActive

	data = copy.deepcopy(data0)
	verbose = False
	nonSwitchBotActive = "BLEinkBirdPool01B-"+thisMAC
	try:
		if (time.time() - macList[thisMAC]["nextRead"] < 0 or time.time() - macList[thisMAC]["lastTesttt"] < macList[thisMAC]["readSensorEvery"]): return data

		minWaitAfterBadRead = min(20.,max(5.,macList[thisMAC]["readSensorEvery"]/3.))
		macList[thisMAC]["nextRead"] = time.time() + minWaitAfterBadRead

		"""
		# simple read: 
		sudo gatttool  --device=49:42:01:00:12:76 --char-read --handle=0x0024
		# temp: first 16bytes  in little endian format 
		"""
		result = batchGattcmd(useHCI, thisMAC, "--char-read --handle=0x{}".format(macList[thisMAC]["bleHandle"]), "descriptor:", nBytes=7, retryCMD=4, verbose=verbose, timeout=6)

		if verbose: U.logger.log(20,"connect results:{}".format(result))

		if result == []:
			data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
			if macList[thisMAC]["triesWOdata"] >= maxTrieslongConnect:
				macList[thisMAC]["triesWOdata"] = 0
				if verbose: U.logger.log(20,"error connected but do data, send not connetced to indigo, triesWOdata:{}, retrying in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
			nonSwitchBotActive = ""
			return data

		data["temp"]  				= round( signedIntfrom16(result[1]+result[0]) /100. + macList[thisMAC]["offsetTemp"], 1)
		data["dataRead"]			= True
		data["connected"]			= True
		macList[thisMAC]["triesWOdata"] = 0
		data["triesWOdata"] = macList[thisMAC]["triesWOdata"]

		if macList[thisMAC]["lastData"] == {}:
			macList[thisMAC]["lastData"]			= copy.deepcopy(data)
			macList[thisMAC]["lastData"]["temp"]	= -10000.
			macList[thisMAC]["lastTesttt"]			= 0.

		if abs(data["temp"] - macList[thisMAC]["lastData"]["temp"]) > 0.5:
			data["dataChanged"] = True

		macList[thisMAC]["lastTesttt"] = time.time()
		macList[thisMAC]["lastData"]  = copy.deepcopy(data)
		if verbose: U.logger.log(20, "{} return ok data: {}".format(thisMAC, data))
		nonSwitchBotActive = ""
		return data

	except  Exception :
		U.logger.log(20,"", exc_info=True)
		data["badSensor"] = True
	
	if verbose: U.logger.log(20, "{}  return 99 data: {}".format(thisMAC, data))
	
	nonSwitchBotActive = ""
	return data



#################################
def checkSwitchbotForCmd():
	"""Worker-thread loop that polls the 'switchbot.cmd' command file for new SwitchBot commands and feeds them onto the switchbotQueue. It handles stop requests (recording per-MAC stop windows and purging that MAC's queued commands), suppresses duplicate commands issued too soon after the previous one, and runs until its thread state is set to 'stop'.

	Inputs:
	    None.
	Outputs:
	    None: runs until thread stop; reads command files, enqueues commands, mutates global switchbot state dicts, logs
	"""
	global switchbotActive
	global maxwaitForSwitchBot
	global expCommands
	global switchbotStop
	global lastSwitchbotCMD

	U.logger.log(20,"checkSwitchbotForCmd start")
	expCommands 		= {}
	switchbotStop 		= {}
	maxwaitForSwitchBot	= 60
	switchbotActive		= ""
	lastSwitchbotCMD	= {}

	while threadDictReadSwitchbot["state"] != "stop":
		try:
			time.sleep(0.25)
			if not switchBotPresent: 
				while not switchbotQueue.empty():
					yy, xx = switchbotQueue.get()
				time.sleep(5)
				continue

			jData = U.checkForNewCommand("switchbot.cmd")
			if len(jData) == 0: continue

			U.logger.log(20, " read new data: {}".format(jData))
			if "mac" not in jData: 
				U.logger.log(20," read new data, bad data")
				jData = {}
				continue

			thisMAC = jData["mac"]

			if thisMAC not in switchbotStop: 
				switchbotStop[thisMAC] = [0.,0.]

			if thisMAC not in expCommands:
				expCommands[thisMAC] = ""

			if thisMAC not in lastSwitchbotCMD:
				lastSwitchbotCMD[thisMAC] = 0

			if "stop" in jData:
				stopActionsForSeconds = jData.get("stopActionsForSeconds",0)
				U.logger.log(20,"{} received stop cmd switchbot action for now and {} seconds".format(thisMAC, stopActionsForSeconds))

				#						 now			stop for 
				switchbotStop[thisMAC] = [time.time(), stopActionsForSeconds]

				tempList = []
				while not switchbotQueue.empty():
					yy, xx = switchbotQueue.get()
					if "mac" in xx and xx["mac"] == thisMAC: continue
					tempList.append((xx,yy))
				if len(tempList) > 0:
					for yy, xx in tempList:
						switchbotQueue.put([yy,xx])
				continue

			if time.time() - lastSwitchbotCMD.get(thisMAC,-100) < switchBotConfig[thisMAC].get("suppressQuickSecond", -2.): 
				U.logger.log(20,"{} suppress second command quickly after last, dSecs:{:.1f} < {} secs".format(thisMAC, time.time() - lastSwitchbotCMD.get(thisMAC,-100), switchBotConfig[thisMAC].get("suppressQuickSecond", -2.)))
				continue 
	
			if len(jData) > 0:
				U.logger.log(20,"{} ADDING TO QUEUE  switchbotActive:{},switchbotActive>{}<".format(thisMAC, switchbotActive, switchbotActive))
				switchbotQueue.put([0,jData])
				#U.logger.log(20," returning from doSwitchBot")
		except  Exception :
			U.logger.log(20,"", exc_info=True)

	U.logger.log(20,"checkSwitchbotForCmd finish")

	return 


#################################
def doSwitchBotThread():
	"""Worker-thread loop that dispatches queued SwitchBot commands by calling doSwitchBot() whenever the queue is non-empty and no command is currently active, pacing executions at least 3.5 seconds apart. After each command it clears active-MAC state, resets expired per-MAC stop windows, and disconnects/clears any open GATT connections.

	Inputs:
	    None.
	Outputs:
	    None: runs until thread stop; invokes doSwitchBot, disconnects GATT, mutates global switchbot state, logs
	"""
	global currentActiveSwitchbotMAC, switchbotActive


	lastCommand = 0
	U.logger.log(20, "doSwitchBotThread start")
	while threadDictDoSwitchbot["state"] != "stop":
		try:
			time.sleep(0.1)
			if switchbotActive in ["","delayed"] and not switchbotQueue.empty(): 
				if time.time() - lastCommand < 3.5: continue  # give the last command time to finish
				pauseBeaconloopForGatt()	# single-dongle: beaconloop pauses while switchbot uses the radio
				doSwitchBot()
				currentActiveSwitchbotMAC = ""; switchbotActive = ""
				lastCommand = time.time()
				for thisMAC in switchbotStop:# reset?
					if switchbotStop[thisMAC] != [0.,0.]: # reset?
						if switchbotStop[thisMAC][1] == 0: # yes
							switchbotStop[thisMAC] = [0.,0.]

						elif switchbotStop[thisMAC] != [0.,0.] and ( time.time() - switchbotStop[thisMAC][0] > switchbotStop[thisMAC][1]): # yes
							switchbotStop[thisMAC] = [0.,0.]
				# just in case other process is changing expCommands at the same time, this will take precedence, and will not change dict structure
				cc =  list(expCommands.keys())
				for mac in cc:
					disconnectGattcmd(mac, 2)
					expCommands[mac] = ""
				time.sleep(0.1)
				resumeBeaconloop()

		except  Exception :
			U.logger.log(20,"", exc_info=True)
	U.logger.log(20,"doSwitchBotThread finish")


#################################
def setSwitchbotParameters(thisMAC, retryCount, jData, verbose):
	"""Configures a SwitchBot device by connecting over GATT (if needed) and writing its mode-of-device characteristic (press/switch normal or inverse) and its hold-time characteristic. On connection or write failure it re-queues the command for a retry.

	Inputs:
	    thisMAC (str): BLE MAC address of the target SwitchBot device
	    retryCount (int): current retry attempt count, re-queued on failure
	    jData (dict): command/parameter data, re-queued on failure
	    verbose (bool): whether to emit detailed log messages
	Outputs:
	    None: writes GATT characteristics over BLE; may re-queue command; logs
	"""

	#if verbose: U.logger.log(20, "{} entering setparameters, switchBotConfig:{}".format(thisMAC, switchBotConfig[thisMAC]))
	if verbose: U.logger.log(20, "{} entering setparameters".format(thisMAC))

	if  switchBotConfig[thisMAC]["modeOfDevice"] in ["cmdPressNormal","cmdPressInverse","cmdSwitchNormal","cmdSwitchInverse"]: 
		writeHandle 	= switchBotConfig[thisMAC]["blehandle"]
		cmdmodeOfDevice	= switchBotConfig[thisMAC][switchBotConfig[thisMAC]["modeOfDevice"]]
		if verbose: U.logger.log(20, "{} trying to connect".format(thisMAC))
		if expCommands[thisMAC] == "":
			if launchGATT(useHCI2, thisMAC, 4, 15, retryConnect=1, random=True, verbose=verbose, nTries=3) != "ok": expCommands[thisMAC] = ""
		if expCommands[thisMAC] == "":
			switchbotQueue.put([retryCount, jData])
			return 

		ok = False
		for ii in range(2):
			if writeGattcmd(thisMAC, "char-write-req {} {}".format(writeHandle, cmdmodeOfDevice), "Characteristic value was written successfully", 5, verbose=verbose):
				if verbose: U.logger.log(20, "{} return ok set mode:{}".format(thisMAC, cmdmodeOfDevice))
				ok = True
				break
		if not ok:
			if verbose: U.logger.log(20, "{} return not ok for mode set".format(thisMAC))
			switchbotQueue.put([retryCount, jData])

	cmdHoldtime = switchBotConfig[thisMAC]["cmdHoldtime"]
	holdSeconds = int(switchBotConfig[thisMAC]["holdSeconds"])
	ok = False
	if holdSeconds >= 0:
		for ii in range(2):
			if writeGattcmd(thisMAC, "char-write-req {} {}{:02x}".format(writeHandle, cmdHoldtime, holdSeconds), "Characteristic value was written successfully", 5, verbose=verbose):
				if verbose: U.logger.log(20, "{} return ok cmd:{}{:02x}".format(thisMAC, cmdHoldtime, holdSeconds))
				ok = True
				break
		if not ok:
			if verbose: U.logger.log(20, "{} return not ok for set hold secs".format(thisMAC))
			switchbotQueue.put([retryCount, jData])
	return 

#################################
def checkIfSwitchbotStop(thisMAC):
	"""Returns True if the given MAC currently has an active stop request, meaning either an indefinite stop (duration 0) or a timed stop whose elapsed time is still within its configured stop-for-seconds window; otherwise returns False.

	Inputs:
	    thisMAC (str): BLE MAC address to check for an active stop request
	Outputs:
	    bool: True if commands for this MAC are currently stopped
	"""
	if thisMAC not in switchbotStop: return False
	if switchbotStop[thisMAC] != [0.,0.] and (switchbotStop[thisMAC][1] == 0 or (time.time() - switchbotStop[thisMAC][0] < switchbotStop[thisMAC][1])): 
		U.logger.log(20, "{} switchbot stop True".format(thisMAC))
		return True
	return False

#################################
def checkIfSwitchbotStopAND(thisMAC):
	"""Returns True if the given MAC has a recorded stop timestamp greater than zero and the current time is past that timestamp; otherwise returns False. A variant stop check used in AND-style conditions.

	Inputs:
	    thisMAC (str): BLE MAC address to check against its recorded stop timestamp
	Outputs:
	    bool: True if the stop timestamp exists and has passed
	"""
	if thisMAC not in switchbotStop: return False
	if thisMAC in switchbotStop and (switchbotStop[thisMAC][0] >0. and time.time() > switchbotStop[thisMAC][0]): return True
	return False

#################################
def doSwitchBot():
	"""Pulls the next SwitchBot command off the queue and executes it. It validates the MAC against switchBotConfig, honors stop and quick-suppress windows, enforces a retry limit, and then performs the requested action (onoff, pulses, statusrequest, setparameters) in either 'batch' mode (command-line GATT write) or 'interactive' mode (persistent GATT connection), re-queuing the command on failure and reporting errors back via sendURL.

	Inputs:
	    None.
	Outputs:
	    None: executes BLE GATT commands, re-queues on failure, sends status/error via sendURL, mutates global switchbot state, logs
	"""
	global currentActiveSwitchbotMAC, switchbotActive, nonSwitchBotActive

	#### check out for definistions of commands and returns
	#### https://github.com/OpenWonderLabs/SwitchBotAPI-BLE/blob/latest/devicetypes/bot.md

	switchbotActive	= "waitingForPrio"
	currentActiveSwitchbotMAC = ""

	if useHCI == useHCI2:
		for ii in range (10):
			if nonSwitchBotActive == "": break
			U.logger.log(20," WAITING FOR PRIO, waiting for:{}".format(nonSwitchBotActive))
			time.sleep(0.5)
	nonSwitchBotActive = ""


	switchbotAction = time.time() 
	verbose = True
	# jData= {"mac":mac#,"onOff":"0/1","statusRequest":True}
	if  switchbotQueue.empty(): 
		switchbotActive	= ""
		U.logger.log(20,"switchbot queue is empty, nothing to do")
		return 

	retryCount, jData = switchbotQueue.get()
	switchbotQueue.task_done()
	if False and verbose: U.logger.log(20," retrycount:{}; jData:{}, switchbotStop:{}".format(retryCount, jData, switchbotStop))


	if "mac"  not in jData: 
		switchbotActive	= ""
		U.logger.log(20,"mac not in data")
		return 

	actualStatus = ""
	checkParams = False
	thisMAC = jData["mac"].upper()

	if thisMAC not in switchBotConfig: 
		switchbotActive	= ""
		U.logger.log(20,"{} not switchBotConfig".format(thisMAC))
		retryCount = 99
		return 
	verbose2 = False# thisMAC == "D1:AD:6B:3D:AB:2D"
	verbose3 = False
	
	expCommands[thisMAC] = ""

	if checkIfSwitchbotStop(thisMAC):
		switchbotActive	= ""
		return 

	if retryCount == 0  and time.time() - lastSwitchbotCMD.get(thisMAC,-100) < switchBotConfig[thisMAC].get("suppressQuickSecond", -2.): 
		U.logger.log(20,"{} suppress second command quickly after last, dSecs:{:.1f} < {} secs".format(thisMAC, time.time() - lastSwitchbotCMD.get(thisMAC,-100), switchBotConfig[thisMAC].get("suppressQuickSecond", -2.)))
		switchbotActive	= ""
		return  

	lastSwitchbotCMD[thisMAC] = time.time()

	retData0 = {"outputs": {"OUTPUTswitchbotRelay": {switchBotConfig[thisMAC]["devId"]: {} }}}
	retData  = retData0["outputs"]["OUTPUTswitchbotRelay"][switchBotConfig[thisMAC]["devId"]]
	retData["mac"] = thisMAC
	retryCount += 1
	if retryCount > 2: 
		retData["error"] = "connection error to switchbot, for command:{}".format(jData)
		U.logger.log(20,"sending error message, command failed, could not connect")
		U.sendURL(retData0, squeeze=False)
		return 


	currentActiveSwitchbotMAC	= thisMAC
	switchbotActive = "active"
	try:
		readParams()
		# make keys lower case
		newData = {}
		for item in jData:
			newData[item.lower()] = jData[item]
		if verbose2: U.logger.log(20, "{} data-in:{}".format(thisMAC, newData))
		cmd  			= newData.get("cmd","onOff").lower()
		mode 			= newData.get("mode","batch").lower()

		if switchBotConfig[thisMAC]["sType"] == "OUTPUTswitchbotRelay":
			retData0 = {"outputs": {"OUTPUTswitchbotRelay": {switchBotConfig[thisMAC]["devId"]: {} }}}
			retData  = retData0["outputs"]["OUTPUTswitchbotRelay"][switchBotConfig[thisMAC]["devId"]]
			retData["mac"] = thisMAC

			try:	onOff 			= int(newData.get("onoff",1))
			except:	onOff			= 1
			try:	pulses 			= int(newData.get("pulses",1))
			except:	pulses			= 1
			try:	pulseLengthOn 	= float(newData.get("pulselengthon",0.))
			except:	pulseLengthOn	= 0.
			try:	pulseLengthOff	= float(newData.get("pulselengthoff",1.))
			except:	pulseLengthOff	= 1.
			try:	pulseDelay		= float(newData.get("pulsedelay",0.))
			except:	pulseDelay		= 0.
			try:	repeat			= int(newData.get("repeat",0)) +1
			except:	repeat			= 1
			try:	repeatDelay		= float(newData.get("repeatdelay",0.)) + 3.
			except:	repeatDelay		= 3.

			if verbose or verbose3: U.logger.log(20, "{} received cmd:{}, onOff:{}, pulses:{}, pulseLengthOn:{}, pulseLengthOff:{}, pulseDelay{}, repeat:{}, repeatDelay:{}, mode:{}".format(thisMAC, cmd, onOff, pulses, pulseLengthOn, pulseLengthOff, pulseDelay, repeat, repeatDelay, mode))

			if  cmd not in ["onoff","pulses","statusrequest","setparameters"]:
				if verbose2: U.logger.log(20, "{}  command not recognized :{}".format(thisMAC, newData))
				retryCount = 99

				return 

			if cmd == "setparameters":
				setSwitchbotParameters(thisMAC, retryCount, jData, verbose)

				return 

			onCmd 				= switchBotConfig[thisMAC]["onCmd"]	
			offCmd 				= switchBotConfig[thisMAC]["offCmd"]	
			onHoldCmd			= switchBotConfig[thisMAC]["onHoldCmd"]
			cmdHoldtime 		= switchBotConfig[thisMAC]["cmdHoldtime"]	
			cmdPressNormal 		= switchBotConfig[thisMAC]["cmdPressNormal"]	
			cmdSwitchNormal 	= switchBotConfig[thisMAC]["cmdSwitchNormal"]	

			writeHandle = switchBotConfig[thisMAC]["blehandle"]
			readHandle = switchBotConfig[thisMAC]["blehandleStatus"]



			#Examples:
			# 3  pulses, on = 1.8 secs, delay between = 4 +2.7 secs
			# echo '{"mac":"E1:7E:66:F6:A0:E7", "cmd":"pulses","pulses":3,"pulseLengthOn":1.8,"pulseLengthOff":4,"mode":"interactive"}' > temp/switchbot.cmd

			# 5 SIMPLE press, delay between = 4 +2.7 secs
			# echo '{"mac":"E1:7E:66:F6:A0:E7", "cmd":"pulses","pulses":5,"pulseLengthOn":0,"pulseLengthOff":0,"pulseDelay":4,"mode":"interactive"}' > temp/switchbot.cmd

			# simple press in interctive mode
			# echo '{"mac": "F9:A6:49:9A:DF:85", "cmd":"onoff", "onoff": "1","mode":"interactive"}' > temp/switchbot.cmd

			# simple press in batch mode
			# echo '{"mac": "F9:A6:49:9A:DF:85", "cmd":"onoff", "onoff": "1","mode":"batch"}' > temp/switchbot.cmd

			# simple on
			# echo '{"mac": "F9:A6:49:9A:DF:85"}' > temp/switchbot.cmd

			if mode == "batch":
						if cmd == "onoff":
							if onOff == 1: 	xxx = onCmd
							else:			xxx = offCmd

							for kk in range(repeat):
								if checkIfSwitchbotStop(thisMAC): return 
								if kk >0: time.sleep(repeatDelay)
								blecmd = "--char-write-req -t random --handle=0x{} --value={}".format(switchBotConfig[thisMAC]["blehandle"], xxx )	
								if verbose2: U.logger.log(20, "{} #{}/{}  sending {}".format(thisMAC, kk, repeat, blecmd))
								if checkIfSwitchbotStop(thisMAC): return
								result = batchGattcmd(useHCI2, thisMAC, blecmd, "successfully", nBytes=0, retryCMD=4, verbose=verbose, timeout=4, thisIsASwitchbotCommand = True)
								if verbose2: U.logger.log(20, "{} result>{}<".format(thisMAC, result))
							if result != "successfully":
								if checkIfSwitchbotStop(thisMAC): 
									if verbose: U.logger.log(20,"pulse cmd stopped du to request")
									return
								switchbotQueue.put([retryCount, jData])
						else:
							if verbose: U.logger.log(20, "{} cmd {} not supported in batch mode".format(thisMAC, cmd))
						lastSwitchbotCMD[thisMAC] = time.time()
		
						return 

			# interactive ####################################################  start
			else:
						if verbose2 or verbose3: U.logger.log(20, "{} trying to connect interactive cmd:{}".format(thisMAC, cmd))
						if launchGATT(useHCI2, thisMAC, 4,15, retryConnect=10, random=True, verbose=verbose, nTries = 2) != "ok": 
							U.logger.log(20, "{} failed to connect ".format(thisMAC))
							switchbotQueue.put([retryCount, jData])
							return 
				
						if expCommands[thisMAC] == "":
							U.logger.log(20, "{} failed to connect ".format(thisMAC))
							switchbotQueue.put([retryCount, jData])
							return 


						#echo '{"mac": "F9:A6:49:9A:DF:85", "cmd": "onoff", "onoff": "1","mode":"interactive"}' > temp/switchbot.cmd
						if cmd == "onoff":
							if onOff == 1:		of =  onCmd;  actualStatus = "on"
							else:  				of =  offCmd; actualStatus = "off"
							for kk in range(repeat):
								if checkIfSwitchbotStop(thisMAC): 
					
									return 
								if kk >0: time.sleep(repeatDelay)
								if checkIfSwitchbotStop(thisMAC): 
					
									return 
								if writeGattcmd(thisMAC, "char-write-req {} {}".format(writeHandle, of), "Characteristic value was written successfully", 5, verbose=verbose):
									retData ["actualStatus"] =  actualStatus
									#U.sendURL(retData)
									switchBotConfig[thisMAC]["lastFailedTryCount"] = 0 
									switchBotConfig[thisMAC]["lastFailedTryTime"] = 0 
									checkParams = True
									if verbose2: U.logger.log(20, "{} on/off: return ok retData:{}; checkParams:{} ".format(thisMAC, retData, checkParams))
								else:
									if checkIfSwitchbotStop(thisMAC): 
										if verbose: U.logger.log(20,"pulse cmd stopped du to request")
										return

									switchbotQueue.put([retryCount, newData])
									if verbose2: U.logger.log(20, "{} on/off: ret data not ok, putting command back into queue: ".format(thisMAC))
							if verbose: U.logger.log(20,"return")
							lastSwitchbotCMD[thisMAC] = time.time()
			
							return 

						elif cmd == "pulses":
							# echo '{"mac": "F9:A6:49:9A:DF:85", "cmd": "pulses", "pulses": "2","pulseLengthOn":"0","pulseLengthOff":"0","pulseDelay":"3","mode":"interactive"}' > temp/switchbot.cmd
							##### simple clock  ##########
							if pulseLengthOn == 0: # switchbot should be in press mode 
								for kk in range(repeat):
									if kk > 0: time.sleep(repeatDelay)
									for ii in range(pulses):
										if checkIfSwitchbotStop(thisMAC): return 
										pulseOK = False
										if ii >0: # wait after 1.,2... pulse
											effSleep = max(2.7, pulseDelay+pulseLengthOff)
											if verbose: U.logger.log(20,"{} sleep pulse off:{}".format(thisMAC, effSleep))
											time.sleep(effSleep)# need to wait on and off time before sending new pulse 
											if checkIfSwitchbotStop(thisMAC): return 

										if verbose: U.logger.log(20,"{} pulse on:{}, #:{}, cmd:char-write-req {} {}".format(thisMAC, pulseLengthOn, kk+1, writeHandle, onCmd ))
										if writeGattcmd(thisMAC, "char-write-req {} {}".format(writeHandle, onCmd), "Characteristic value was written successfully", 5, verbose=verbose):
											if verbose: U.logger.log(20,"{} pulse cmd ok, try#:{}".format(thisMAC, kk+1))
											pulseOK = True
											continue
										else:
											if checkIfSwitchbotStop(thisMAC): 
												if verbose: U.logger.log(20,"{} pulse cmd stopped du to request, try#:{}".format(thisMAC, kk+1))
												return
											if verbose: U.logger.log(20,"{} pulse cmd not ok, try#:{}".format(thisMAC, kk+1))
											pulseOK = False
											break

									if pulseOK:
										break 

								if not pulseOK:
									switchbotQueue.put([retryCount, jData])
									return 

								if verbose: U.logger.log(20,"{} return".format(thisMAC))
								lastSwitchbotCMD[thisMAC] = time.time()
				
								return 

							##### OFF ##########
							else:
								if verbose2: U.logger.log(20, "{} doing pulses:{}, setting mode to press normal:{}".format(thisMAC, pulses, cmdPressNormal))
								if not writeGattcmd(thisMAC, "char-write-req {} {}".format(writeHandle, cmdPressNormal), "Characteristic value was written successfully", 5, verbose=verbose):
									switchbotQueue.put([retryCount, jData])
									return 
									# set pulse length
								if verbose2: U.logger.log(20, "{} set pulse length to {}".format(thisMAC, pulseLengthOn))
								if not writeGattcmd(thisMAC, "char-write-req {} {}{:02x}".format(writeHandle, cmdHoldtime, int(pulseLengthOn)), "Characteristic value was written successfully", 5, verbose=verbose):
									if checkIfSwitchbotStop(thisMAC): 
										if verbose: U.logger.log(20,"{} pulse cmd stopped du to request".format(thisMAC))
										return
									switchbotQueue.put([retryCount, jData])
									return 
								retData["actualStatus"] = "off"


								for mm in range(repeat):
									if mm >0: time.sleep(repeatDelay)
									if pulses > 0: 
										for kk in range(repeat):
											if checkIfSwitchbotStop(thisMAC): 
												return 
											if kk >0: time.sleep(repeatDelay)
											# echo '{"mac":"E1:7E:66:F6:A0:E7","pulses":5,"pulseLengthOn":1.8,"pulseLengthOff":4}' > temp/switchbot.cmd
													#if ok: send the pulses 
													#time.sleep(1)
											for ii in range(pulses):
												if ii > 0: # sleep after first pulse
													if checkIfSwitchbotStop(thisMAC): return 

													effSleep = max(2.7, pulseDelay+pulseLengthOff+pulseLengthOn+2.7)
													if verbose2: U.logger.log(20,"{} sleep pulse off:{}".format(thisMAC, effSleep))
													time.sleep(effSleep)# need to wait on and off time before sending new pulse 

												if verbose2: U.logger.log(20, "{} pulse on:{}, #:{}".format(thisMAC, pulseLengthOn, ii+1))
												if checkIfSwitchbotStop(thisMAC): return 

												if not writeGattcmd(thisMAC, "char-write-req {} {}".format(writeHandle, onCmd), "Characteristic value was written successfully", 5, verbose=verbose):
													if checkIfSwitchbotStop(thisMAC): 
														if verbose: U.logger.log(20, "{} pulse cmd stopped due to request".format(thisMAC))
														return
													switchbotQueue.put([retryCount, jData])
													if verbose2: U.logger.log(20,"{} pulse cmd not ok".format(thisMAC))
													return 

												if verbose2: U.logger.log(20, "{} pulse cmd ok".format(thisMAC))

									setSwitchbotParameters(thisMAC, retryCount, jData, verbose)
									retData["actualStatus"] =  "off"

			# interactive ####################################################  end


			if "statusrequest" in newData or checkParams:
				if verbose2 or verbose3: U.logger.log(20, "{}  entering statusRequest".format(thisMAC))

				# in switch mode 
				#down    570101: 01 48 90   
				#up      570102: 01 48 d0 

				#pres&h  570103: 01 ff d0 

				# in press mode 
				#down    570101: 05 ff 00 
				#up      570102: 05 ff 00 

				#pres&h  570103: 01 ff 00 

				#press:  5701: 01 48 d0 / 01 48 90
				#status  5702: 01 60 31 64 00 00 00 be 00 10 02 00 00 

				for ii in range(3):
					# just read status, later check what status received
					result =  readGattcmd(thisMAC, "char-read-hnd {}".format(readHandle),  "Characteristic value/descriptor:", -1, 5, verbose=verbose)
					if len(result) == 3:
						if verbose2 or verbose3: U.logger.log(20, "{} statusRequest: return ok;  result: {}, retData:{}, actualStatus:{}".format(thisMAC, result, retData, actualStatus))

						# handle 0x13  should give  status  w/o previous 5702, after press or switch:
						# switch mode
						if result   == ["01","48","90"]: 	actualStatus = "on"
						elif result == ["01","48","d0"]: 	actualStatus = "off"

						# press
						elif result == ["05","ff","31"]: 	actualStatus = "on"
						elif result == ["05","ff","00"]: 	actualStatus = "off"
						elif result == ["03","ff","00"]: 	actualStatus = "off"

						# press and hold
						elif result == ["01","ff","00"]: 	actualStatus = "on"
						elif result == ["01","ff","d0"]: 	actualStatus = "on"

						else: 						  		actualStatus = "status_request"
						retData["actualStatus"] = actualStatus

					elif len(result) == 13:
						#01 61 31 64 00 00 00 bd 00 10 02 00 00 
						#01 5e 31 64 00 00 00 bf 00 00 01 00 00 
						# st 
						#   bat   #1
						#      firmware  #2
						#         The strength to push button #3
						#            ADC--  #4-5
						#                  motCV- #6-7
						#                        timer #8
						#                           mode #9
						#                           inverse #9
						#                              hold time #10
						#                                 ??
						#                                    ??
						retData["batteryLevel"]		= int(result[1],16) & 0b01111111
						retData["version"] 			= str(int(result[2],16)/10.)
						retData["inverseDirection"]	= "inverse" if int(result[9],16) & 1 != 0 else "normal"          #(=x1)
						retData["mode"]				= "pressMode" if int(result[9],16) & 16 == 0 else "onOffMode" #(=1x)
						retData["holdSeconds"]		= int(result[10],16)
						retData["actualStatus"]     = "status_request"
						if verbose2 or verbose3: U.logger.log(20, "{} return ok;  result: {}, retData:{}".format(thisMAC, result, retData))
						break
					elif len(result) == 1:
						if verbose2 or verbose3: U.logger.log(20, "{} return not ok, should be 3 or 13 long, got only one byte ;  result: {}, retData:{}".format(thisMAC, result, retData))
						if result[0] in ["08","0b","0a"]:
							retData["warning"] = "device is set to use encrypted communication, use phone app to initialize"
							retData["actualStatus"] = "ConfigureDevOnPhone"
						elif result[0] == "01":
							# this ok 
							pass
							#if verbose2: U.logger.log(20, "mac: {} issue warning".format(thisMAC))
							#retData["warning"] = "device needs to be configured on phone"
							#retData["actualStatus"] = "ConfigureDevOnPhone"
						elif result[0] == "ff":
							pass

						else:
							retData["error"] = "connection error to switchbot, >> please setup device on phone << {}".format(result)
							retData["actualStatus"] = "unkownError"

						if verbose2: U.logger.log(20, "{} statusRequest: setup device on phone".format(thisMAC))
					else :
						if verbose2 or verbose3: U.logger.log(20, "{} statusRequest:  unexpected result {}".format(thisMAC, result))

					# if not status: issue status command, then read again
					result = writeGattcmd(thisMAC, "char-write-req {} {}".format(writeHandle, switchBotConfig[thisMAC]["statusCmd"] ), "Characteristic value was written successfully", 5, verbose=verbose)


				if retData !={}:
					if verbose2 or verbose3: U.logger.log(20, "{} sending retData0:{}".format(thisMAC, retData0))
					U.sendURL(retData0, squeeze=False)
					switchBotConfig[thisMAC]["lastFailedTryTime"] = 0 
					switchBotConfig[thisMAC]["lastFailedTryCount"] = 0 

			lastSwitchbotCMD[thisMAC] = time.time()
			return 


		##############  switchbotcurtain  ############## 
		if switchBotConfig[thisMAC]["sType"] in ["OUTPUTswitchbotCurtain","OUTPUTswitchbotCurtain3"]:
			retData0 = {"outputs": {switchBotConfig[thisMAC]["sType"]: {switchBotConfig[thisMAC]["devId"]: {} }}}
			retData  = retData0["outputs"][switchBotConfig[thisMAC]["sType"]][switchBotConfig[thisMAC]["devId"]]
			retData["mac"] = thisMAC

			if verbose2: U.logger.log(20, "{} switchbotcurtain, jData:{}".format(thisMAC, newData))

			moveTo 			= newData.get("moveto","open").lower()
			mode 			= newData.get("mode","interacive").lower()
			speed 			= newData.get("speed","").lower()
			position		= newData.get("position",50)
			cmdStop = ""
			useMode = switchBotConfig[thisMAC]["modeOfDevice"] 
			if speed != "": useMode = speed
			if moveTo in ["open","close","stop","position"]:
				if   moveTo == "position":	position = position;	cmd = "{}{}{:02x}".format(switchBotConfig[thisMAC]["positionCmd"], useMode, int(position))
				elif moveTo == "open":		position = "0";			cmd = "{}{}00".format(switchBotConfig[thisMAC]["openCmd"], useMode )
				elif moveTo == "close":		position = "100";		cmd = "{}{}64".format(switchBotConfig[thisMAC]["closeCmd"], useMode )
				elif moveTo == "stop":		position = "" ;			cmd = switchBotConfig[thisMAC]["pauseCmd"]
				else: 												cmd = "error"; return


				if verbose2: U.logger.log(20, "{} trying to connect".format(thisMAC))
				if launchGATT(useHCI2, thisMAC, 4,15, retryConnect=15, random=True, verbose=verbose, nTries = 2) !="ok":
					U.logger.log(20, "{} failed to connect ".format(thisMAC))
					switchbotQueue.put([retryCount, jData])
					return 

				startT = time.time()
				blecmd = "--char-write-req -t random --handle=0x{} --value={}".format(switchBotConfig[thisMAC]["blehandle"], cmd )	
				if verbose2: U.logger.log(20, "{} sending {}".format(thisMAC, blecmd))
				if not writeGattcmd(thisMAC, "char-write-req {} {}".format(switchBotConfig[thisMAC]["blehandle"], cmd), "Characteristic value was written successfully", 5, verbose=verbose, retryCMD=5):
					switchbotQueue.put([retryCount, jData])
					if verbose2: U.logger.log(20, "{} ret data not ok, putting command back into queue, not executed".format(thisMAC))
					return 

				retData["position"] = position
				if verbose: U.logger.log(20, "{} return ok data, retData:{}".format(thisMAC, retData0))
				U.sendURL(retData0, squeeze=False)
				switchBotConfig[thisMAC]["lastFailedTryCount"] = 0 
				switchBotConfig[thisMAC]["lastFailedTryTime"] = 0 
				return 

			else:
				if verbose2: U.logger.log(20, "{} direction not in command".format(thisMAC))
			return 

		else:
			if verbose2: U.logger.log(20, "{} Type not found".format(thisMAC))
		return 
	except  Exception :
		U.logger.log(20,"", exc_info=True)
		if verbose2: U.logger.log(20, "{}  return  data: {}".format(thisMAC, switchBotConfig))
	
	return  



##################################
def readParams():
		"""Reads the plugin's beacon parameter/sensor configuration files and rebuilds the in-memory device tables. It loads beacon_parameters and knownBeaconTags, refreshes globals via doRead, builds macList entries for BLEconnect and long-connect BLE sensor devices, and populates switchBotConfig for SwitchBot relay and curtain outputs. If no relevant sensors or SwitchBot outputs are defined it stops the worker threads and exits.

		Inputs:
		    None.
		Outputs:
		    bool: False if no new/changed input data; otherwise rebuilds global config tables (or exits if nothing configured)
		"""
		global sensorList, restartBLEifNoConnect
		global BLEconnectLastUp
		global oldRaw, lastRead, BLEconnectMode
		global oneisBLElongConnectDevice
		global switchBotPresent, knownBeaconTags




		try:
			f = open("{}temp/beacon_parameters".format(G.homeDir),"r")
			InParams = json.loads(f.read().strip("\n"))
			f.close()
			BLEconnectLastUp	 = InParams.get("BLEconnectLastUp", {})
		except: 
			BLEconnectLastUp = {}
			

		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return False
		if lastRead2 == lastRead: return False
		lastRead  = lastRead2
		if U.stripConfigured(inpRaw) == U.stripConfigured(oldRaw):	oldRaw = inpRaw; return False	# ignore cosmetic timestamp-only resends
		oldRaw	   = inpRaw
		oldSensor		  = sensorList

		try:
			f = open("{}temp/knownBeaconTags".format(G.homeDir),"r")
			xx = json.loads(f.read().strip("\n"))
			knownBeaconTags = xx["output"]
			f.close()
		except:
			if knownBeaconTags == {}:
				U.logger.log(20,"temp/knownBeaconTags missing/unreadable - switchbot devices cannot be configured until the plugin sends it (send config to rpi)")


		try:
			sensors = {}
			
			U.getGlobalParams(inp)

			oneisBLElongConnectDevice = False
			if "sensors" in inp:	
				if "BLEconnect" in inp["sensors"]: 
					sensors["BLEconnect"] = copy.deepcopy(inp["sensors"]["BLEconnect"])
				for ss in inp["sensors"]:
					#U.logger.log(20,"1-ss:{}, sens:{} ".format(ss, inp["sensors"][ss]))
					#if ss == "BLEdirectMiTempHumSquare":	
					oneActive = False
					for devId in inp["sensors"][ss]:
						#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(20,"1-devId:{} ".format(devId))
						if "isBLElongConnectDevice" in inp["sensors"][ss][devId] and inp["sensors"][ss][devId]["isBLElongConnectDevice"]:
							#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(20,"1-sensors[ss]:{} ".format(inp["sensors"][ss]))
							oneActive = True
							oneisBLElongConnectDevice = True
							if "isBLElongConnectDevice" not in sensors:
								sensors["isBLElongConnectDevice"] = {}
					if oneActive:
						sensors["isBLElongConnectDevice"][ss] = copy.deepcopy(inp["sensors"][ss])



			if sensors == {} and "OUTPUTswitchbotRelay" not in inp["output"] and "OUTPUTswitchbotCurtain" not in inp["output"]:
				U.logger.log(20," no BLEconnect devices / switchbots in parameters - continuing as gatt service only (beep/battery for beacon tags, routed by receiveCommands)")



			if "restartBLEifNoConnect"	in inp:	 restartBLEifNoConnect=		  (inp["restartBLEifNoConnect"])
			if "sensorList"				in inp:	 sensorList=				  (inp["sensorList"])

			if "BLEconnectMode"			in inp:	 BLEconnectMode=			  (inp["BLEconnectMode"])
			if BLEconnectMode not in ("commandLine", "socket", "attSocket"):		BLEconnectMode = "attSocket"	# e.g. stale "useDefault" in an old params file -> new default
			if BLEconnectMode == "socket" and not (bluezPresent or attClientPresent):	BLEconnectMode = "commandLine"	# socket presence needs pybluez (py2) OR the py3 stdlib backend
			xx = "ATT-socket" if gattEngineIsATT() else "gatttool"
			if BLEconnectMode == "attSocket" and not attClientPresent:
				xx += " (attSocket configured but gattAttClient.py not available - file missing on rpi or python < 3.3?)"
			if xx != lastLoggedGattEngine[0]:
				lastLoggedGattEngine[0] = xx
				U.logger.log(20,"gatt engine: {}  (BLEconnectMode:{})".format(xx, BLEconnectMode))

			macListNew={}

			if "BLEconnect" in sensors:
				for devId in sensors["BLEconnect"]:
					if "macAddress" not in sensors["BLEconnect"][devId]: continue
					thisMAC = sensors["BLEconnect"][devId]["macAddress"]
					macListNew[thisMAC]={"type":"isBLEconnect",
										 "iPhoneRefreshDownSecs":float(sensors["BLEconnect"][devId]["iPhoneRefreshDownSecs"]),
										 "iPhoneRefreshUpSecs":float(sensors["BLEconnect"][devId]["iPhoneRefreshUpSecs"]),
										 "BLEtimeout":max(1.,float(sensors["BLEconnect"][devId]["BLEtimeout"])),
										 "up":False,
										 "lastTesttt":time.time()-1000.,
										 "lastMsgtt":time.time()-1000. ,
										 "lastData":{},
										 "triesWOdata": 0,
										 "quickTest": 0.,
										 "devId": devId }
					oneisBLElongConnectDevice = True


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
				U.logger.log(10, "macListNew  {},".format(macListNew) )
			if "isBLElongConnectDevice" in sensors:
				CCC = sensors["isBLElongConnectDevice"]
				for ss in CCC: 	
					#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(20,"CCC:{} ".format(CCC))
					for devId in CCC[ss]:
						#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(20,"devId:{} ".format(devId))
						if "mac" not in CCC[ss][devId]: continue
						thisMAC = CCC[ss][devId]["mac"]
						#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(20,"{} ".format(thisMAC))
						if thisMAC not in macListNew:
							macListNew[thisMAC]={"type":"isBLElongConnectDevice",
												 "updateIndigoTiming":60,
												 "lastSend":0,
												 "readSensorEvery":180,
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
												 "nextRead": 0,
												 "bleHandle": "",
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
						if "bleHandle" in CCC[ss][devId]:
							macListNew[thisMAC]["bleHandle"] = CCC[ss][devId]["bleHandle"]
					#if ss =="BLEdirectMiTempHumSquare":	U.logger.log(20,"macListNew:{} ".format(macListNew))




			#U.logger.log(20,"BLEconnect - chechink devices (1):{}".format(macList))
			for thisMAC in macListNew:
				if thisMAC not in macList:
					macList[thisMAC] = copy.deepcopy(macListNew[thisMAC])
				else:
					if macList[thisMAC]["type"] == "BLEconnect": 
						macList[thisMAC]["iPhoneRefreshDownSecs"] = macListNew[thisMAC]["iPhoneRefreshDownSecs"]
						macList[thisMAC]["iPhoneRefreshUpSecs"]	  = macListNew[thisMAC]["iPhoneRefreshUpSecs"]
						macList[thisMAC]["BLEtimeout"]			  = macListNew[thisMAC]["BLEtimeout"]
					elif macList[thisMAC]["type"] == "isBLElongConnectDevice": 
						macList[thisMAC]["updateIndigoTiming"]	  = macListNew[thisMAC]["updateIndigoTiming"]

			delMac={}
			for thisMAC in macList:
				if thisMAC not in macListNew:
					delMac[thisMAC] = 1
			for	 thisMAC in delMac:
				del macList[thisMAC]


			switchBotPresent = False
			for devType in ["OUTPUTswitchbotRelay"]:
				if devType in inp["output"]:
					for devId in inp["output"][devType]:
						if "mac" not in inp["output"][devType][devId]: continue
						if devType not in knownBeaconTags:
							U.logger.log(20,"switchbot {}: type {} not in knownBeaconTags (file not sent yet?) - device skipped this round".format(inp["output"][devType][devId]["mac"], devType))
							continue
						thisMAC = inp["output"][devType][devId]["mac"]
						switchBotConfig[thisMAC] = copy.copy(knownBeaconTags[devType])
						switchBotConfig[thisMAC]["sType"] = devType
						switchBotConfig[thisMAC]["devId"] = devId

						if "modeOfDevice" in inp["output"][devType][devId]:
							switchBotConfig[thisMAC]["modeOfDevice"] = 	inp["output"][devType][devId]["modeOfDevice"]
						switchBotConfig[thisMAC]["suppressQuickSecond"] = float(inp["output"][devType][devId].get("suppressQuickSecond",-10.))
							#U.logger.log(20,"=== modeOfDevice:{}".format(inp["output"][devType][devId]["modeOfDevice"]))
						if "holdSeconds" in inp["output"][devType][devId]:
							switchBotConfig[thisMAC]["holdSeconds"] = 	inp["output"][devType][devId]["holdSeconds"]
							#U.logger.log(20,"=== holdSeconds:{}".format(inp["output"][devType][devId]["holdSeconds"]))

							#U.logger.log(20,"=== holdSeconds:{}".format(inp["output"]["OUTPUTswitchbotRelay"][devId]["holdSeconds"]))
						switchBotPresent = True
			for devType in ["OUTPUTswitchbotCurtain", "OUTPUTswitchbotCurtain3"]:
				if devType in inp["output"]:
					for devId in inp["output"][devType]:
						if "mac" not in inp["output"][devType][devId]: continue
						if devType not in knownBeaconTags:
							U.logger.log(20,"switchbot {}: type {} not in knownBeaconTags (file not sent yet?) - device skipped this round".format(inp["output"][devType][devId]["mac"], devType))
							continue
						thisMAC = inp["output"][devType][devId]["mac"]
						switchBotConfig[thisMAC] = copy.copy(knownBeaconTags[devType])
						switchBotConfig[thisMAC]["sType"] = devType
						switchBotConfig[thisMAC]["devId"] = devId
						if "modeOfDevice" in inp["output"][devType][devId] and inp["output"][devType][devId]["modeOfDevice"] in ["00","01","ff"]:
							switchBotConfig[thisMAC]["modeOfDevice"] = 	inp["output"][devType][devId]["modeOfDevice"]
						switchBotConfig[thisMAC]["devType"] = 	devType

							#U.logger.log(20,"=== holdSeconds:{}".format(inp["output"]["OUTPUTswitchbotRelay"][devId]["holdSeconds"]))
						switchBotPresent = True
			#U.logger.log(20," switchBotConfig:{}".format(switchBotConfig))
			#U.logger.log(20," BLEconnect - switchBotConfig {}".format(switchBotConfig))

			if len(macList) == 0 and not switchBotPresent:
				U.logger.log(20,"no BLEconnect devices / switchbots in parameters (2) - continuing as gatt service only")

			#U.logger.log(20,"BLEconnect - chechink devices (2):{}".format(macList))
			#U.logger.log(20,"macList:{}".format(macList))
			return True
			
		except Exception :
			U.logger.log(20,"", exc_info=True)
		return False



################################
def tryToConnectToBLEconnect(thisMAC, BLEid):
	"""Attempts to read RSSI/presence data from a BLEconnect (iPhone) device, throttling attempts according to per-device up/down refresh intervals. On a valid reading it marks the device up, clears any BLE-restart flag, and sends new data to Indigo via sendURL when the value changed or the last message is stale; otherwise it marks the device down.

	Inputs:
	    thisMAC (str): BLE MAC address of the device to poll
	    BLEid (str): BLE identifier passed to the socket/command-line connect routine
	Outputs:
	    None: connects over BLE, updates macList presence state, sends data via sendURL, logs
	"""
	global lastSignal
	global lastConnect
	global restartCount

	try:
		#U.logger.log(20,"{} BLEid:{}".format(thisMAC, BLEid))

		tt = time.time()
		if macList[thisMAC]["up"]:
			if tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["iPhoneRefreshUpSecs"] * 0.99:							return 
		elif tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["iPhoneRefreshDownSecs"] - macList[thisMAC]["quickTest"]:	return 

		if thisMAC in BLEconnectLastUp:
			#U.logger.log(20, "{}  testing lastup delta :{}, refresh secs:{}".format(thisMAC,  tt - BLEconnectLastUp[thisMAC]["lastUp"], macList[thisMAC]["iPhoneRefreshUpSecs"] ))
			if tt - BLEconnectLastUp[thisMAC]["lastUp"] <= macList[thisMAC]["iPhoneRefreshUpSecs"] * 0.99:
				#U.logger.log(20,"{}  testing lastup delta2 :{}".format(thisMAC,  BLEconnectLastUp[thisMAC]["lastUp"] -  macList[thisMAC]["lastMsgtt"]))
				if BLEconnectLastUp[thisMAC]["lastUp"] -  macList[thisMAC]["lastMsgtt"]  < 60.:									
											#U.logger.log(20, "{}  reject".format(thisMAC))
											return
		#U.logger.log(20,"{}  testing connect ".format(thisMAC))


		#print "tryToConnectToBLEconnect ", thisMAC
		######### here we actually get the data from the phones ###################
		if BLEconnectMode in ("socket", "attSocket") and attClientPresent:		# py3 stdlib presence - no pybluez, no hcitool needed
			data0 = tryToConnectSocketStdlib(thisMAC, macList[thisMAC]["BLEtimeout"], BLEid)
		elif BLEconnectMode == "socket" and bluezPresent and not usePython3:	# legacy py2 pybluez path (broken on py3: array.array("c"))
			data0 = tryToConnectSocket(thisMAC, macList[thisMAC]["BLEtimeout"], BLEid)
		else:
			data0 = tryToConnectCommandLine(thisMAC, macList[thisMAC]["BLEtimeout"])

		lastConnect = time.time()
		macList[thisMAC]["lastTesttt"] = tt		# pace the polls: the iPhoneRefreshUp/DownSecs gates above compare
												# against this - it was NEVER set in the presence path, so phones
												# were paged every main-loop pass (~1 sec) regardless of the config

		#print	data0

		#U.logger.log(20, "{} rssi {}, txPower:{},".format(thisMAC, data0.get("rssi",-999), data0.get("txPower",-999) ))


		macList[thisMAC]["lastMsgtt"]  = tt


		if	data0 != {}:
			if data0["rssi"] != -999:
				macList[thisMAC]["up"] = True
				lastSignal	 = time.time()
				restartCount = 0
				if os.path.isfile(G.homeDir + "temp/BLErestart"):
					os.remove(G.homeDir + "temp/BLErestart")

			else:
				macList[thisMAC]["up"] = False

			#U.logger.log(20,"{} up>{},".format(thisMAC, macList[thisMAC]["up"]) ))

			if data0["rssi"] != macList[thisMAC]["lastData"] or (tt-macList[thisMAC]["lastMsgtt"]) > (macList[thisMAC]["iPhoneRefreshUpSecs"]-1.): # send htlm message to indigo, if new data, or last msg too long ago
				if macList[thisMAC]["lastData"] != -999 and not macList[thisMAC]["up"] and (tt-macList[thisMAC]["lastMsgtt"]) <	 macList[thisMAC]["iPhoneRefreshUpSecs"]+2.:
					macList[thisMAC]["quickTest"] =macList[thisMAC]["iPhoneRefreshDownSecs"]/2.
					return 
				#print "sending "+thisMAC+" " + datetime.datetime.now().strftime("%M:%S"), macList[thisMAC]["up"] , macList[thisMAC]["quickTest"], data0
				macList[thisMAC]["quickTest"] = 0.
				#print "af -"+datetime.datetime.now().strftime("%M:%S"), macList[thisMAC]["up"], macList[thisMAC]["quickTest"], data0
				macList[thisMAC]["lastMsgtt"]  = tt
				macList[thisMAC]["lastData"] = data0["rssi"]
				data={}
				data["sensors"]				= {"BLEconnect":{macList[thisMAC]["devId"]:{thisMAC:data0}}}
				U.sendURL(data=data)

		else:
			macList[thisMAC]["up"] = False
		return 

	except Exception :
		U.logger.log(20,"", exc_info=True)
	return 

def tryDeltaTime(tt):
	"""Stub method that ignores its argument and always returns 0.

	Inputs:
	    tt (float): unused timestamp argument
	Outputs:
	    int: always 0
	"""
	return 0
	
def hardresetHCI(hci):
	
	"""Hard-resets a Bluetooth HCI adapter by shelling out to bring the interface down, restart the bluetooth service, and bring the interface back up, logging each command and its result.

	Inputs:
	    hci (str): HCI adapter name (e.g. 'hci0') to reset
	Outputs:
	    None: runs hciconfig/service shell commands to reset the adapter; logs
	"""
	try:
		cmd = "sudo hciconfig {} down".format(hci)
		ret = readPopen(cmd) # enable bluetooth
		U.logger.log(20,"cmd:{} .. ret:{}".format(cmd, ret)  )
		cmd = "sudo invoke-rc.d bluetooth restart"
		ret = readPopen(cmd) # enable bluetooth
		U.logger.log(20,"cmd:{} .. ret:{}".format(cmd, ret)  )
		cmd = "sudo hciconfig {} up".format(hci)
		ret = readPopen(cmd) # enable bluetooth
		U.logger.log(20,"cmd:{} .. ret:{}".format(cmd, ret) )
	except Exception : 
		U.logger.log(20,"", exc_info=True)
	return 


#################################
def tryToConnectToSensorDevice(thisMAC):
	"""Reads sensor data from a long-connect BLE sensor device by dispatching to the appropriate driver based on its devType (Xiaomi Mi temp/hum square, Mi VegTrug, or InkBird pool). It tracks bad-sensor counts, sends readings to Indigo via sendURL when changed or due, and requests a BLE stack restart if the device produces no data for too many tries.

	Inputs:
	    thisMAC (str): BLE MAC address of the sensor device to read
	Outputs:
	    None: reads BLE sensor, updates macList state, sends data via sendURL, may flag BLE restart, logs
	"""
	data = {"connected":False, "mac":thisMAC, "dataChanged":False, "dataRead":False, "triesWOdata":macList[thisMAC]["triesWOdata"], "badSensor": False}
	try:
		if macList[thisMAC]["devType"] == "BLEXiaomiMiTempHumSquare":
			#U.logger.log(20, "{} BLEXiaomiMiTempHumSquare".format(thisMAC))
			data = BLEXiaomiMiTempHumSquare(thisMAC, data)

		elif macList[thisMAC]["devType"] == "BLEXiaomiMiVegTrug":
			#U.logger.log(20, "{} BLEXiaomiMiVegTrug".format(thisMAC))
			data = BLEXiaomiMiVegTrug(thisMAC, data)


		elif macList[thisMAC]["devType"] == "BLEinkBirdPool01B":
			#U.logger.log(20, " BLEinkBirdPool01B")
			data = BLEinkBirdPool01B(thisMAC, data)

		else:
			return 

		if data is None or len(data) == 0: return 
		dataSend = {}
		#U.logger.log(20, "BLEconnect: data:{}".format(data))
		if data["badSensor"]:
			macList[thisMAC]["up"] = False
			macList[thisMAC]["badSensor"] +=1
			if macList[thisMAC]["badSensor"] > 3:
				dataSend["sensors"] = {macList[thisMAC]["devType"]:{macList[thisMAC]["devId"]:"badSensor"}}
				U.sendURL(data=dataSend)
				macList[thisMAC]["badSensor"] = 0
			macList[thisMAC]["up"] = False
			return 
		
		if (time.time() - macList[thisMAC]["lastSend"] <= macList[thisMAC]["updateIndigoTiming"] and not data["dataChanged"] ): return 

		del data["badSensor"]

		macList[thisMAC]["badSensor"]	= 0
		macList[thisMAC]["up"] 			= True
		dataSend["sensors"]				= {macList[thisMAC]["devType"]:{macList[thisMAC]["devId"]:data}}
		U.sendURL(data=dataSend)
		macList[thisMAC]["lastSend"] = time.time()
		if macList[thisMAC]["triesWOdata"] >  2* maxTrieslongConnect:
			U.logger.log(20, "requested a restart of BLE stack due to no sensor signal  for {} tries".format( macList[thisMAC]["triesWOdata"]))
			time.sleep(5)
			U.doWriteSimpleFile("{}temp/BLErestart".format(G.homeDir), "xx") # signal that we need to restart BLE
			
	except  Exception :
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20,"{} data:{}".format(thisMAC, data))
	return 


#################################
def startReadCmdThread():
	"""Initializes SwitchBot worker globals and the command queue, then starts the two background threads: checkSwitchbotForCmd (reads commands) and doSwitchBotThread (executes commands), recording their state and thread objects in the thread-tracking dicts.

	Inputs:
	    None.
	Outputs:
	    None: creates the queue and starts the reader/executor threads, sets global thread state, logs
	"""
	global switchbotActive
	global nonSwitchBotActive
	global maxwaitForSwitchBot
	global switchbotQueue
	global threadDictReadSwitchbot, threadDictDoSwitchbot
	global currentActiveGattCommandisSwitchBot

	currentActiveGattCommandisSwitchBot = False
	maxwaitForSwitchBot = 60
	switchbotActive = ""
	nonSwitchBotActive = ""

	U.logger.log(20,"start switchbot thread ")
	switchbotQueue = Queue.Queue()
	try:
		threadDictReadSwitchbot = {}
		threadDictReadSwitchbot["state"]   		= "start"
		threadDictReadSwitchbot["thread"]  = threading.Thread(name='checkSwitchbotForCmd', target=checkSwitchbotForCmd)
		threadDictReadSwitchbot["thread"].start()

		threadDictDoSwitchbot = {}
		threadDictDoSwitchbot["state"]   		= "start"
		threadDictDoSwitchbot["thread"]  = threading.Thread(name='doSwitchBotThread', target=doSwitchBotThread)
		threadDictDoSwitchbot["thread"].start()

	except  Exception :
		U.logger.log(20,"", exc_info=True)
	return 


####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
def execBLEconnect():
	"""Main entry point and infinite loop for the BLEconnect helper process: initializes all global state, reads parameters, starts the HCI/Bluetooth stack and the read-command thread, then continuously monitors HCI health (restarting the BLE stack when it goes down or no signal is seen) and polls each tracked MAC to connect to BLEconnect and long-connect sensor devices.

	Inputs:
	    None.
	Outputs:
	    None: Runs forever; manages BLE connections, restarts HCI, sends URL updates, and writes logs/files
	"""
	global sensorList,restartBLEifNoConnect
	global macList,oldParams
	global oldRaw,	lastRead
	global BLEsocketErrCount, lastConnect
	global BLEconnectMode
	global sensor
	global oneisBLElongConnectDevice
	global maxTrieslongConnect
	global useHCI, useHCI2, myBLEmac
	global lastSignal
	global restartCount
	global nowTest, nowP
	global switchBotConfig, switchbotActive, switchBotPresent, nonSwitchBotActive, expCommands
	global threadDictReadSwitchbot, threadDictDoSwitchbot, switchbotStop
	global counterFunctionNotImplemented
	global currentActiveSwitchbotMAC



	currentActiveSwitchbotMAC = ""
	counterFunctionNotImplemented = 0
	threadDictReadSwitchbot = {}
	threadDictDoSwitchbot	= {}
	expCommands				= {}
	nonSwitchBotActive		= ""
	switchbotActive			= ""
	switchBotPresent		= False
	switchBotConfig			= {}
	switchbotStop			= {}
	lastConnect 			= time.time()
	maxTrieslongConnect 	= 4
	oneisBLElongConnectDevice = False
	BLEconnectMode			= "attSocket" # attSocket (default) / socket / commandLine; auto-fallback to gatttool when the ATT client is unavailable
	oldRaw					= ""
	lastRead				= 0
	BLEsocketErrCount				= 0
	###################### constants #################

	####################  input gios   ...allrpi	  only rpi2 and rpi0--
	oldParams				= ""
	#####################  init parameters that are read from file 
	sensorList				= "0"
	G.authentication		= "digest"
	restartBLEifNoConnect 	= True
	sensor					= G.program
	macList					= {}
	oldRaw					= ""

	myPID				= str(os.getpid())
	U.setLogging()
	U.logger.log(20,"======= starting BLEconnect v:{}".format(VERSION))
	U.killOldPgm(myPID,G.program+".py")# kill  old instances of myself if they are still running

	loopCount		  	= 0
	lastPauseLog	  	= 0.		# throttle for the "paused" log line below
	pauseStart		  	= 0.		# when the CURRENT pause began (0 = not paused) - see the log there
	readParams()

	time.sleep(1)  # give HCITOOL time to start

	lastData			= {}
	lastRead			= -1

	if U.getIPNumber() > 0:
		U.logger.log(20," no ip number ")
		time.sleep(10)
		exit()

	G.tStart			= time.time() 
	#print iPhoneRefreshDownSecs
	#print iPhoneRefreshUpSecs
	startSeconds		= time.time()
	lastSignal			= time.time()
	restartCount		= 0
	nowTest				= 0
	nowP				= False
	eth0IP, wifi0IP, eth0Enabled, wifiEnabled = U.getIPCONFIG()
	##print eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled

	useHCI, myBLEmac, BLEid, bus, useHCI2 = startHCI()
	text = "{}-{}-{}".format(useHCI, bus, myBLEmac)
	U.sendURL( data={"data":{"hciInfo_BLEconnect":text}}, squeeze=False, wait=False )

	tlastQuick = time.time()

	
	startReadCmdThread()
	U.logger.log(20, "starting v:{} \n                            using HCI:{}/{}; mac#:{}; bus:{}; pid#:{}; eth0IP:{}; wifi0IP:{}; eth0Enabled:{}; wifiEnabled:{}".format(VERSION, useHCI, useHCI2, myBLEmac, bus, myPID, eth0IP, wifi0IP, eth0Enabled, wifiEnabled))
	if attClientPresent and getattr(gattAttClient, "VERSION", 0.) < ATTCLIENT_MINVERSION:
		U.logger.log(20, "gattAttClient.py on this rpi is v{} but BLEconnect v{} needs v{} - STALE FILE (partial send?): send ALL pgm files to this rpi!".format(getattr(gattAttClient, "VERSION", 0.), VERSION, ATTCLIENT_MINVERSION))
	while True:

			tt = time.time()
			checkBeaconGattQueues()		# beacon-tag beeps (highest prio) + one battery read (low prio) per pass
			#U.logger.log(20, "loop time after start:{}".format(tt-startSeconds))

			if tt - lastRead > 8 :
				readParams()
				eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
				lastRead = tt
				if not checkIfHCIup(useHCI):
					U.logger.log(20, "requested a restart of BLE stack due to {} down ".format(useHCI))
					#U.doWriteSimpleFile("{}temp/BLErestart".format(G.homeDir), "xx") # signal that we need to restart BLE
					cmd = "sudo hciconfig {} down;sudo hciconfig {} up;".format(useHCI, useHCI)
					readPopen(cmd) # enable bluetooth
					U.logger.log(20,"cmd:{} ".format(cmd)  )
					time.sleep(1)
					restartCount += 1
					if not checkIfHCIup(useHCI): # simple restart did not woek, lets do a master restart 
						hardresetHCI(useHCI)
						
						if checkIfHCIup(useHCI):
							restartCount = 0
							
						if restartCount > 5:
							U.writeFile("temp/restartNeeded", "bleconnect request")
					else:
						restartCount = 0
						U.logger.log(20,"...restart fixed".format()  )


			if restartBLEifNoConnect and (tt - lastSignal > (2*3600+ 600*restartCount)) or counterFunctionNotImplemented > 20 :
				U.logger.log(20, "requested a restart of BLE stack due to no signal for {:.0f} seconds".format(tt-lastSignal))
				U.doWriteSimpleFile("{}temp/BLErestart".format(G.homeDir), "xx") # signal that we need to restart BLE
				lastSignal = time.time() +30
				restartCount +=1

			#checkSwitchbotForCmd()

			# PAUSE: temp/BLEconnect.pause (timestamp content) means someone else needs the radios -
			# today that is the dongle qualification started from the plugin menu. We stay alive and
			# keep writing our alive file, we just do not touch a radio. 120 s failsafe against a
			# writer that died, same idea as beaconloop.pause.
			try:
				_pf = G.homeDir+"temp/BLEconnect.pause"
				if os.path.isfile(_pf):
					# fallback is the file's own mtime, NEVER time.time(): with "now" an unparseable or
					# half-written file looked freshly refreshed on every single pass, so the 120 s
					# failsafe below could not fire at all and BLEconnect stayed "radios handed over"
					# for good. mtime keeps a live writer alive and lets a dead one expire.
					try:	_ts = os.path.getmtime(_pf)
					except Exception:	_ts = 0.
					try:
						_raw = U.doReadSimpleFile(_pf).strip()
						if _raw != "":	_ts = float(_raw)
					except Exception:	pass
					if time.time() - _ts < 120.:
						if pauseStart == 0.:	pauseStart = time.time()
						if time.time() - lastPauseLog > 10:
							lastPauseLog = time.time()
							# TWO different numbers, and the old line showed the wrong one: how long we
							# have been paused (what you want to know) is NOT the age of the pause file.
							# The file is refreshed every 5 s for as long as the pause lasts, so its age
							# is always ~0-5 s - "paused (0s so far)" was printed 8 times during an 85 s
							# pause. The file age still matters (at 120 s the pause expires), so show both.
							U.logger.log(20, "BLEconnect paused for {:.0f}s - radios handed over (pause file refreshed {:.0f}s ago, expires at 120s)".format(
											time.time() - pauseStart, time.time() - _ts))
						U.echoLastAlive(G.program)
						time.sleep(1)
						continue
					else:
						U.logger.log(20, "BLEconnect.pause is stale ({:.0f}s with no refresh) - resuming after {:.0f}s".format(
										time.time() - _ts, time.time() - pauseStart if pauseStart > 0. else 0.))
						pauseStart = 0.
						try:	os.remove(_pf)
						except Exception:	pass
				elif pauseStart > 0.:
					U.logger.log(20, "BLEconnect resumed after {:.0f}s - radios back".format(time.time() - pauseStart))
					pauseStart = 0.
			except Exception:	pass

			if time.time() - tlastQuick > 1 and not singleDongleMode:	# regular sensor polling needs a 2nd dongle 
				#U.logger.log(20, "loop time:{}".format(time.time()) )
				tlastQuick = time.time()

				for thisMAC in macList:
					#U.logger.log(20, "{} testing type:{}".format(thisMAC, macList[thisMAC]["type"]) )

					if macList[thisMAC]["type"] == "isBLEconnect":
						tryToConnectToBLEconnect(thisMAC, BLEid)
						#checkSwitchbotForCmd()

					if macList[thisMAC]["type"] == "isBLElongConnectDevice":
						tryToConnectToSensorDevice(thisMAC)
						#checkSwitchbotForCmd()

			loopCount+=1
			time.sleep(0.1)
			#print "no answer sleep for " + str(iPhoneRefreshDownSecs)
			U.echoLastAlive(G.program)


####### start here #######
execBLEconnect()
		
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
		
sys.exit(0)		   
