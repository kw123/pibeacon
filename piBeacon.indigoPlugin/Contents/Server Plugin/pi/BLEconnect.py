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
import	time,datetime
import	json
import  pexpect
import  re
try:
	import bluetooth
	import bluetooth._bluetooth as bt
	bluezPresent = True
except:
	bluezPresent = False
 
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
VERSION = 7.1
ansi_escape =re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')

if sys.version[0] == "3": usePython3 = True
else:					  usePython3 = False




#################################
def escape_ansi(line):
	try:	ret = ansi_escape.sub('', line).encode('ascii',errors='ignore')
	except: ret = ""
	return ret

####-------------------------------------------------------------------------####
def toStringAndstripRNetc(inX):
	return str(inX).strip("b'").replace("\\r"," ").replace("\\n"," ").replace("\r"," ").replace("\n"," ").strip()

####-------------------------------------------------------------------------####
def toStringAndstripB(inX):
	return str(inX).strip("b'")


####-------------------------------------------------------------------------####
def readPopen(cmd):
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception as e:
			U.logger.log(20,"", exc_info=True)



#################################
def signedIntfrom16(string):
	try:
		intNumber = int(string,16)
		if intNumber > 32767: intNumber -= 65536
	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
		return 0
	return intNumber


#################################
def checkIFQuickRequested():
	global macList
	global sensor
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
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 




#################################
def startHCI():
	global BLEconnectMode
	global macList
	global oneisBLElongConnectDevice, switchBotPresent
	global useHCI, useHCI2
	## give other ble functions time to finish

	defaultBus = "USB"
	doNotUseHCI = ""
	BusUsedByBeaconloop = ""
	time.sleep(10)

	if oneisBLElongConnectDevice or switchBotPresent:
		for ii in range(4):
			if ii > 0: time.sleep(ii*5)
			hciBeaconloopUsed, raw  = U.readJson("{}temp/beaconloop.hci".format(G.homeDir))
			U.logger.log(20, "BLE(long)connect: beconloop uses: {}".format(hciBeaconloopUsed))
			if "usedHCI" not in hciBeaconloopUsed: continue
			if "usedBus" not in hciBeaconloopUsed: continue
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
	U.logger.log(20, "BLE(long)connect--HCIs read:  {}, hci used by beaconloop:{}, {}".format(HCIs, doNotUseHCI, doNotUseHCI))
	if HCIs["hci"] != {}:
		if len(HCIs["hci"]) < 2 and oneisBLElongConnectDevice:
			text = "BLE(long)connect: only one BLE dongle, need 2 to run, will restart BLE stack (hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -) and try again,, HCI inf:\n{}".format(HCIs)
			U.logger.log(20, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			cmd = "timeout 5 sudo hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -"
			ret = readPopen(cmd)
			U.logger.log(20, "cmd: {} and ret:".format(cmd, ret))

			cmd = "timeout 20 sudo hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -"
			ret = readPopen(cmd)
			U.logger.log(20, "cmd: {} and ret:".format(cmd, ret))
			U.sendURL( data={"data":{"hciInfo":"err-need-2-USB"}}, squeeze=False, wait=False )
			threadDictReadSwitchbot["state"] = "stop"
			threadDictDoSwitchbot["state"] = "stop"
			time.sleep(5)
			exit()

		useHCI,  myBLEmac, BLEid, bus = U.selectHCI(HCIs["hci"], G.BLEconnectUseHCINo, defaultBus, doNotUseHCI=doNotUseHCI)
		U.logger.log(20, "BLE(long)connect: BLEconnectUseHCINo-bus: {}; useHCI:{}, len(HCIs):{}, BLEid:{}, default:{}, HCIUsedByBeaconloop:{}; BusUsedByBeaconloop:{}".format(G.BLEconnectUseHCINo, useHCI, len(HCIs["hci"]), BLEid, defaultBus, doNotUseHCI, BusUsedByBeaconloop))

		if len(HCIs["hci"]) >= 2:
			if BLEid >= 0:
				if len(HCIs["hci"]) > 2:
					useHCI2,  myBLEmac2, BLEid2, bus2 = U.selectHCI(HCIs["hci"], "", "", doNotUseHCI=doNotUseHCI, doNotUseHCI2=useHCI)
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
	HCIs = U.whichHCI()
	if useHCI in HCIs["hci"]:
		if HCIs["hci"][useHCI]["upDown"] == "UP": return True
	return False

#################################
def batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=3000., batteryVoltAt0=2700.):
	try:
		batteryLowVsTemp			= (1. + 0.7*min(0.,temp-10.)/100.) * batteryVoltAt0 # (changes to 0.9* 2700 @ 0C; to = 0.8*2700 @-10C )
		batteryLevel 				= int(min(100.,max(0.,100.* (batteryVoltage - batteryLowVsTemp)/(batteryVoltAt100-batteryLowVsTemp))))
		return batteryLevel
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 0



#################################
def checkSwitchBotPrio(thisMAC):
	global currentActiveSwitchbotMAC, switchbotActive, nonSwitchBotActive
	global switchBotPresent

	verbose = True
	if not switchBotPresent: return False
	if currentActiveSwitchbotMAC !="" and currentActiveSwitchbotMAC == thisMAC: return False
	if switchbotActive in ["active", "waiting", "waitingForPrio"]:  
		if verbose: U.logger.log(20,"{} {} cancel prio for switchbot:{} ".format(thisMAC, nonSwitchBotActive, currentActiveSwitchbotMAC ))
		nonSwitchBotActive = ""
		return True
	return False

#################################
def launchGATT(useHCI, thisMAC, timeoutGattool, timeoutConnect, retryConnect=5, random=False, verbose=False, nTries=1, waitbetween=0.5):
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot, switchbotActive, lastSwitchbotCMD
	global nonSwitchBotActive
	global expCommands
	global counterFunctionNotImplemented

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
					U.logger.log(20, u"{} gatttool ERROR, giving up: \nBF:{}--\nAF:{}-".format(thisMAC, BF, AF))
					time.sleep(1)
					return ""
				U.logger.log(20, u"{} gatttool ERROR:\nBF:{}--\nAF:{}-".format(thisMAC, BF, AF))
				expCommands[thisMAC] = ""
				continue

			# send connect command 
			time.sleep(0.1)
			ret = connectGATT(thisMAC, retryConnect, timeoutConnect=timeoutConnect,  waitbetween=waitbetween, verbose=verbose)
			if ret == "":   return ""
			if ret == "ok": return "ok"


		nonSwitchBotActive = ""
		return ""
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	nonSwitchBotActive = ""
	return ""


def connectGATT(thisMAC, retryConnect, timeoutConnect=0.5, waitbetween=0.5, verbose=False):
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot, switchbotActive, lastSwitchbotCMD
	global nonSwitchBotActive
	global expCommands
	global counterFunctionNotImplemented

	BF = ""
	AF = ""
	try:
		for ii in range(retryConnect):
			if expCommands[thisMAC] == "":
					U.logger.log(20, u"{} connect error: expCommands is empty".format(thisMAC))
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


	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	return ""

#################################
def disconnectGattcmd(thisMAC, timeout, verbose=False):	
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot
	global expCommands
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
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	expCommands[thisMAC] = ""
	return False



#################################
def writeGattcmd(thisMAC, cc,  expectedTag, timeout, verbose=False, retryCMD=3):	
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot
	global expCommands
	global counterFunctionNotImplemented
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

					except  Exception as e:
						U.logger.log(30,"", exc_info=True)

				continue
			ret = expCommands[thisMAC].expect("\n")

	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30,"{} cc:{}, expectedTag:{}, ii:{}, retryCMD:{}, ".format(thisMAC, cc, expectedTag, ii, retryCMD))
	return False



#################################
def writeAndListenGattcmd(cc, expectedTag, nBytes, timeout, verbose=False):
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot
	global expCommands
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
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	return []




#################################
def readGattcmd(thisMAC, cc, expectedTag, nBytes, timeout, verbose=False):
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot
	global expCommands
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
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	return []



#################################
def batchGattcmd(useHCI, thisMAC, cc, expectedTag, nBytes=0, retryCMD=3, verbose=False, timeout=6, thisIsASwitchbotCommand = False):
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot
	global currentActiveGattCommandisSwitchBot

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
			if checkIfSwitchbotStopAND(thisMAC): return 
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

	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	currentActiveGattCommandisSwitchBot = False
	return []



#################################
def tryToConnectSocket(thisMAC,BLEtimeout,devId):
	global BLEsocketErrCount, lastConnect

	retdata	 = {"rssi": -999, "txPower": -999,"flag0ok":0,"byte2":0}
	if checkSwitchBotPrio(thisMAC):  return retdata
	if time.time() - lastConnect < 3: time.sleep( max(0,min(0.5,(3.0- (time.time() - lastConnect) ))) )
	U.logger.log(20, u"{} starting, using devid:{}".format(thisMAC, devId))

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
			U.logger.log(20, u"send command via socket ")
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
			subprocess.call("rm {}temp/stopBLE > /dev/null 2>&1".format(G.homeDir), shell=True)
			U.logger.log(20,"", exc_info=True)
			U.restartMyself(reason="sock.recv error", delay = 10)

	except	Exception as e:
			U.logger.log(30,"", exc_info=True)
	U.logger.log(10, "{} retdata:{}".format(thisMAC, retdata))
	BLEsocketErrCount = 0
	return retdata



#################################
def tryToConnectCommandLine(thisMAC, BLEtimeout):
	global BLEsocketErrCount, lastConnect, useHCI
	global switchBotPresent, switchbotActive, nonSwitchBotActive

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

	except  Exception as e:
			U.logger.log(30,"", exc_info=True)
			retdata = {}
	
	#U.logger.log(20, "{} return data: {}".format(thisMAC, retdata))
	nonSwitchBotActive = ""
	return retdata


#################################
def BLEXiaomiMiTempHumSquare(thisMAC, data0):
	global BLEsocketErrCount, macList, maxTrieslongConnect, useHCI
	global switchBotConfig, switchbotActive, switchBotPresent, nonSwitchBotActive

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
		if verbose: U.logger.log(20, u"{} trying hci:{}".format(thisMAC, useHCI))
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
					#U.logger.log(20, u"{} not connected, send to indigo, triesWOdata:{}, retryCMD in {} secs".format(thisMAC, macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
					data["connected"] = False
					data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
				if verbose: U.logger.log(20, u"not connected, triesWOdata:{}, retryCMD in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
				disconnectGattcmd(thisMAC, 2)
				nonSwitchBotActive = ""
				return data

			readData = []

			for nn in range(2):
				if checkSwitchBotPrio(thisMAC):
					disconnectGattcmd(thisMAC, 2)
					nonSwitchBotActive = ""
					return ""

				readData = writeAndListenGattcmd( "char-write-req 0038 0100", "value:", 5, 15, verbose=verbose)
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
			#U.logger.log(20, u"error, connected but no data, triesWOdata:{} repeast in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))

	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		data["badSensor"] = True
	
	#U.logger.log(20, "{} return data: {}".format(thisMAC, data))
	
	nonSwitchBotActive = ""
	return data



#################################
def BLEXiaomiMiVegTrug(thisMAC, data0):
	global BLEsocketErrCount, macList, maxTrieslongConnect, useHCI
	global switchBotConfig, switchbotActive, switchBotPresent, nonSwitchBotActive

	nonSwitchBotActive = "BLEXiaomiMiVegTrug0-"+thisMAC
	data = copy.deepcopy(data0)
	if thisMAC not in expCommands:
		expCommands[thisMAC] = ""
	try:
		verbose = False
		verbose0 = False
		if verbose0: U.logger.log(20, u"{}  tries:{}, test1:{}, test2:{}".format(thisMAC, macList[thisMAC]["triesWOdata"], time.time() - macList[thisMAC]["nextRead"] < 0 , time.time() - macList[thisMAC]["lastTesttt"] < macList[thisMAC]["readSensorEvery"]))
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
				#U.logger.log(20, u"{} error, not connected, sending not connected to indigo, triesWOdata:{}, retrying in {} secs".format(thisMAC, macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
				U.logger.log(20, u"{}  error, not connected, triesWOdata:{} retrying in {} secs".format(thisMAC, macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
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

		if verbose0: U.logger.log(20, u"connect results:{} - {}".format(result1, result2))

		if result1 == [] or result2 == []:
			data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
			if macList[thisMAC]["triesWOdata"] >= maxTrieslongConnect:
				macList[thisMAC]["triesWOdata"] = 0
				if verbose0: U.logger.log(20, u"error connected but do data, send not connetced to indigo, triesWOdata:{}, retrying in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
			macList[thisMAC]["lastTesttt"] = time.time() - 90
			nonSwitchBotActive = ""
			return data

		data["batteryLevel"]		= int(result1[0],16)
		try:	data["Version"]		= "".join(result1[2:]).decode("hex")
		except: data["Version"]		= "unknown"
		data["temp"]  				= round( signedIntfrom16(result2[1]+result2[0])/10., 1)
		data["illuminance"]			= int(result2[6]+result2[5]+result2[4]+result2[3],16)
		data["moisture"] 			= int(result2[7],16)
		data["Conductivity"]		= int(result2[9]+result2[8],16)
		data["dataRead"]			= True
		data["connected"]			= True
		macList[thisMAC]["triesWOdata"] = 0

		if macList[thisMAC]["lastData"] == {}:
			macList[thisMAC]["lastData"] 			= copy.deepcopy(data)
			macList[thisMAC]["lastData"]["temp"]	= -10000.
			macList[thisMAC]["lastTesttt"] 			= time.time() - 90

		if ( abs(data["temp"] 			- macList[thisMAC]["lastData"]["temp"])			> 0.5 	or
			 abs(data["moisture"]  		- macList[thisMAC]["lastData"]["moisture"])		> 2 	or
			 abs(data["Conductivity"]	- macList[thisMAC]["lastData"]["Conductivity"])	> 2 ):
			macList[thisMAC]["lastTesttt"] = time.time()
			macList[thisMAC]["lastData"]  = copy.deepcopy(data)
			data["dataChanged"]			=  True
		if verbose0: U.logger.log(20, "{} return data: {}".format(thisMAC, data))
		nonSwitchBotActive = ""
		return data


	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		nonSwitchBotActive = ""
		data["badSensor"] = True
	
	if verbose0: U.logger.log(20, "{} return data: {}".format(thisMAC, data))
	
	nonSwitchBotActive = ""
	return data



#################################
def BLEinkBirdPool01B(thisMAC, data0):
	global BLEsocketErrCount, macList, maxTrieslongConnect, useHCI
	global switchBotConfig, switchbotActive, switchBotPresent, nonSwitchBotActive

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

		if verbose: U.logger.log(20, u"connect results:{}".format(result))

		if result == []:
			data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
			if macList[thisMAC]["triesWOdata"] >= maxTrieslongConnect:
				macList[thisMAC]["triesWOdata"] = 0
				if verbose: U.logger.log(20, u"error connected but do data, send not connetced to indigo, triesWOdata:{}, retrying in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
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

	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		data["badSensor"] = True
	
	if verbose: U.logger.log(20, "{}  return 99 data: {}".format(thisMAC, data))
	
	nonSwitchBotActive = ""
	return data



#################################
def checkSwitchbotForCmd():
	global switchbotActive, switchBotPresent
	global nonSwitchBotActive
	global switchbotQueue
	global threadDictReadSwitchbot, threadDictDoSwitchbot
	global maxwaitForSwitchBot
	global expCommands
	global switchbotStop
	global lastSwitchbotCMD

	U.logger.log(20, u"checkSwitchbotForCmd start")
	expCommands 		= {}
	switchbotStop 		= {}
	maxwaitForSwitchBot	= 60
	switchbotActive		= ""
	nonswitchbotActive	= ""; currentActiveSwitchbotMAC = ""
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

			U.logger.log(20, u" read new data: {}".format(jData))
			if "mac" not in jData: 
				U.logger.log(20, u" read new data, bad data".format(jData))
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
				U.logger.log(20, u"{} received stop cmd switchbot action for now and {} seconds".format(thisMAC, stopActionsForSeconds))

				#						 now			stop for 
				switchbotStop[thisMAC] = [time.time(), stopActionsForSeconds]

				tempList = []
				while not switchbotQueue.empty():
					yy, xx = switchbotQueue.get()
					if "mac" in xx and xx["mac"] == thisMAC: continue
					tempList.append(xx,yy)
				if len(tempList) > 0:
					for yy, xx in tempList:
						switchbotQueue.put([yy,xx])
				continue

			if time.time() - lastSwitchbotCMD.get(thisMAC,-100) < switchBotConfig[thisMAC].get("suppressQuickSecond", -2.): 
				U.logger.log(20, u"{} suppress second command quickly after last, dSecs:{:.1f} < {} secs".format(thisMAC, time.time() - lastSwitchbotCMD.get(thisMAC,-100), switchBotConfig[thisMAC].get("suppressQuickSecond", -2.)))
				continue 
	
			if len(jData) > 0:
				U.logger.log(20, u"{} ADDING TO QUEUE  switchbotActive:{},switchbotActive>{}<".format(thisMAC, switchbotActive, switchbotActive))
				switchbotQueue.put([0,jData])
				#U.logger.log(20, u" returning from doSwitchBot")
		except  Exception as e:
			U.logger.log(30,"", exc_info=True)

	U.logger.log(20, u"checkSwitchbotForCmd finish")

	return 


#################################
def doSwitchBotThread():
	global switchbotActive, switchBotPresent
	global nonSwitchBotActive
	global switchbotQueue
	global threadDictReadSwitchbot, threadDictDoSwitchbot
	global expCommands
	global switchbotStop
	global lastSwitchbotCMD
	global currentActiveSwitchbotMAC, switchbotActive, nonSwitchBotActive


	lastCommand = 0
	U.logger.log(20, u"doSwitchBotThread start")
	while threadDictDoSwitchbot["state"] != "stop":
		try:
			time.sleep(0.1)
			if switchbotActive in ["","delayed"] and not switchbotQueue.empty(): 
				if time.time() - lastCommand < 3.5: continue  # give the last command time to finish
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

		except  Exception as e:
			U.logger.log(30,"", exc_info=True)
	U.logger.log(20, u"doSwitchBotThread finish")


#################################
def setSwitchbotParameters(thisMAC, retryCount, jData, verbose):
	global expCommands
	global switchBotConfig
	global useHCI, useHCI2
	global switchbotStop
	global lastSwitchbotCMD

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
	global switchbotStop
	if thisMAC not in switchbotStop: return False
	if switchbotStop[thisMAC] != [0.,0.] and (switchbotStop[thisMAC][1] == 0 or (time.time() - switchbotStop[thisMAC][0] < switchbotStop[thisMAC][1])): 
		U.logger.log(20, "{} switchbot stop True".format(thisMAC))
		return True
	return False

#################################
def checkIfSwitchbotStopAND(thisMAC):
	global switchbotStop
	if thisMAC not in switchbotStop: return False
	if thisMAC in switchbotStop and (switchbotStop[thisMAC][0] >0. and time.time() > switchbotStop[thisMAC][0]): return True
	return False

#################################
def doSwitchBot():
	global useHCI, useHCI2
	global switchBotConfig
	global switchbotQueue, expCommands
	global switchbotStop
	global lastSwitchbotCMD
	global currentActiveSwitchbotMAC, switchbotActive, nonSwitchBotActive

	#### check out for definistions of commands and returns
	#### https://github.com/OpenWonderLabs/SwitchBotAPI-BLE/blob/latest/devicetypes/bot.md

	switchbotActive	= "waitingForPrio"
	currentActiveSwitchbotMAC = ""

	if useHCI == useHCI2:
		for ii in range (10):
			if nonSwitchBotActive == "": break
			U.logger.log(20, u" WAITING FOR PRIO, waiting for:{}".format(nonSwitchBotActive))
			time.sleep(0.5)
	nonSwitchBotActive = ""


	switchbotAction = time.time() 
	verbose = True
	verbose2 = False
	# jData= {"mac":mac#,"onOff":"0/1","statusRequest":True}
	if  switchbotQueue.empty(): 
		switchbotActive	= ""
		U.logger.log(20, u" empty:{}")
		return 

	retryCount, jData = switchbotQueue.get()
	switchbotQueue.task_done()
	if verbose2: U.logger.log(20, u" retrycount:{}; jData:{}, switchbotStop:{}".format(retryCount, jData, switchbotStop))


	if "mac"  not in jData: 
		switchbotActive	= ""
		U.logger.log(20, u"mac not in data")
		return 

	actualStatus = ""
	checkParams = False
	thisMAC = jData["mac"].upper()

	if thisMAC not in switchBotConfig: 
		switchbotActive	= ""
		U.logger.log(20, u"{} not switchBotConfig".format(thisMAC))
		retryCount = 99
		return 

	expCommands[thisMAC] = ""

	if checkIfSwitchbotStop(thisMAC):
		switchbotActive	= ""
		return 

	if retryCount == 0  and time.time() - lastSwitchbotCMD.get(thisMAC,-100) < switchBotConfig[thisMAC].get("suppressQuickSecond", -2.): 
		U.logger.log(20, u"{} suppress second command quickly after last, dSecs:{:.1f} < {} secs".format(thisMAC, time.time() - lastSwitchbotCMD.get(thisMAC,-100), switchBotConfig[thisMAC].get("suppressQuickSecond", -2.)))
		switchbotActive	= ""
		return  

	lastSwitchbotCMD[thisMAC] = time.time()

	retData0 = {"outputs": {"OUTPUTswitchbotRelay": {switchBotConfig[thisMAC]["devId"]: {} }}}
	retData  = retData0["outputs"]["OUTPUTswitchbotRelay"][switchBotConfig[thisMAC]["devId"]]
	retData["mac"] = thisMAC
	retryCount += 1
	if retryCount > 2: 
		retData["error"] = "connection error to switchbot, for command:{}".format(jData)
		U.logger.log(20, u"sending error message, command failed, could not connect")
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

		if switchBotConfig[thisMAC]["sType"] == "switchbotbot":

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

			if verbose: U.logger.log(20, "{} received onOff:{}, pulses:{}, pulseLengthOn:{}, pulseLengthOff:{}, pulseDelay{}, repeat:{}, repeatDelay:{}, mode:{}".format(thisMAC, onOff, pulses, pulseLengthOn, pulseLengthOff, pulseDelay, repeat, repeatDelay, mode))

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
									if verbose: U.logger.log(20, u"pulse cmd stopped du to request")
									return
								switchbotQueue.put([retryCount, jData])
						else:
							if verbose: U.logger.log(20, "{} cmd {} not supported in batch mode".format(thisMAC, cmd))
						lastSwitchbotCMD[thisMAC] = time.time()
		
						return 

			# interactive ####################################################  start
			else:
						if verbose2: U.logger.log(20, "{} trying to connect".format(thisMAC))
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
										if verbose: U.logger.log(20, u"pulse cmd stopped du to request")
										return

									switchbotQueue.put([retryCount, newData])
									if verbose2: U.logger.log(20, "{} on/off: ret data not ok, putting command back into queue: ".format(thisMAC))
							if verbose: U.logger.log(20, u"return")
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
											if verbose: U.logger.log(20, u"{} sleep pulse off:{}".format(thisMAC, effSleep))
											time.sleep(effSleep)# need to wait on and off time before sending new pulse 
											if checkIfSwitchbotStop(thisMAC): return 

										if verbose: U.logger.log(20, u"{} pulse on:{}, #:{}, cmd:char-write-req {} {}".format(thisMAC, pulseLengthOn, kk+1, writeHandle, onCmd ))
										if writeGattcmd(thisMAC, "char-write-req {} {}".format(writeHandle, onCmd), "Characteristic value was written successfully", 5, verbose=verbose):
											if verbose: U.logger.log(20, u"{} pulse cmd ok, try#:{}".format(thisMAC, kk+1))
											pulseOK = True
											continue
										else:
											if checkIfSwitchbotStop(thisMAC): 
												if verbose: U.logger.log(20, u"{} pulse cmd stopped du to request, try#:{}".format(thisMAC, kk+1))
												return
											if verbose: U.logger.log(20, u"{} pulse cmd not ok, try#:{}".format(thisMAC, kk+1))
											pulseOK = False
											break

									if pulseOK:
										break 

								if not pulseOK:
									switchbotQueue.put([retryCount, jData])
									return 

								if verbose: U.logger.log(20, u"{} return".format(thisMAC))
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
										if verbose: U.logger.log(20, u"{} pulse cmd stopped du to request".format(thisMAC))
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
													if verbose2: U.logger.log(20, u"{} sleep pulse off:{}".format(thisMAC, effSleep))
													time.sleep(effSleep)# need to wait on and off time before sending new pulse 

												if verbose2: U.logger.log(20, "{} pulse on:{}, #:{}".format(thisMAC, pulseLengthOn, ii+1))
												if checkIfSwitchbotStop(thisMAC): return 

												if not writeGattcmd(thisMAC, "char-write-req {} {}".format(writeHandle, onCmd), "Characteristic value was written successfully", 5, verbose=verbose):
													if checkIfSwitchbotStop(thisMAC): 
														if verbose: U.logger.log(20, "{} pulse cmd stopped due to request".format(thisMAC))
														return
													switchbotQueue.put([retryCount, jData])
													if verbose2: U.logger.log(20, u"{} pulse cmd not ok".format(thisMAC))
													return 

												if verbose2: U.logger.log(20, "{} pulse cmd ok".format(thisMAC))

									setSwitchbotParameters(thisMAC, retryCount, jData, verbose)
									retData["actualStatus"] =  "off"

			# interactive ####################################################  end


			if "statusrequest" in newData or checkParams:
				if verbose2: U.logger.log(20, "{}  entering statusRequest".format(thisMAC))

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

				for ii in range(2):
					# just read ststus, later check what status received
					result =  readGattcmd(thisMAC, "char-read-hnd {}".format(readHandle),  "Characteristic value/descriptor:", -1, 5, verbose=verbose)
					if len(result) == 3:
						if verbose2: U.logger.log(20, "{} statusRequest: return ok;  result: {}, retData:{}, actualStatus:{}".format(thisMAC, result, retData, actualStatus))

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

						else: 						  		actualStatus = ""
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
						if verbose2: U.logger.log(20, "{} return ok;  result: {}, retData:{}".format(thisMAC, result, retData))
						break
					elif len(result) == 1:
						if verbose2: U.logger.log(20, "{} return not ok, should be 3 or 13 long, got only one byte ;  result: {}, retData:{}".format(thisMAC, result, retData))
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

						if verbose2: U.logger.log(20, "{} statusRequest: setup device on phone".format(thisMAC, result))
					else :
						if verbose2: U.logger.log(20, "{} statusRequest:  unexpected result {}".format(thisMAC, result))

					# if not status: issue status command, then read again
					result = writeGattcmd(thisMAC, "char-write-req {} {}".format(writeHandle, switchBotConfig[thisMAC]["statusCmd"] ), "Characteristic value was written successfully", 5, verbose=verbose)


				if retData !={}:
					if verbose2: U.logger.log(20, "{} sending retData0:{}".format(thisMAC, retData0))
					U.sendURL(retData0, squeeze=False)
					switchBotConfig[thisMAC]["lastFailedTryTime"] = 0 
					switchBotConfig[thisMAC]["lastFailedTryCount"] = 0 

			lastSwitchbotCMD[thisMAC] = time.time()
			return 


		##############  switchbotcurtain  ############## 
		if switchBotConfig[thisMAC]["sType"] == "switchbotcurtain":

			if verbose2: U.logger.log(20, "{} switchbotcurtain, jData:{}".format(thisMAC, newData))

			moveTo 			= newData.get("moveto","open").lower()
			position		= int(newData.get("position",50))
			cmdStop = ""

			if moveTo in ["open","close","stop","position"]:
				if   moveTo == "position":	position = position;	cmd = "{}{}{:02x}".format(switchBotConfig[thisMAC]["positionCmd"], switchBotConfig[thisMAC]["modeOfDevice"], position)
				elif moveTo == "open":		position = "0";			cmd = "{}{}00".format(switchBotConfig[thisMAC]["openCmd"], switchBotConfig[thisMAC]["modeOfDevice"] )
				elif moveTo == "close":		position = "100";		cmd = "{}{}64".format(switchBotConfig[thisMAC]["closeCmd"], switchBotConfig[thisMAC]["modeOfDevice"] )
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
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		if verbose2: U.logger.log(20, "{}  return  data: {}".format(thisMAC, switchBotConfig))
	
	return  



##################################
def readParams():
		global debug, ipOfServer,myPiNumber,passwordOfServer, userIdOfServer, authentication,ipOfServer,portOfServer,sensorList,restartBLEifNoConnect
		global macList, BLEconnectLastUp
		global oldRaw, lastRead, BLEconnectMode
		global sensor
		global oneisBLElongConnectDevice
		global switchBotConfig, switchbotActive, switchBotPresent




		try:
			f = open("{}temp/beacon_parameters".format(G.homeDir),"r")
			InParams = json.loads(f.read().strip("\n"))
			f.close()
			BLEconnectLastUp	 = InParams.get("BLEconnectLastUp", {})
		except: pass


		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return False
		if lastRead2 == lastRead: return False
		lastRead  = lastRead2
		if inpRaw == oldRaw: return False
		oldRaw	   = inpRaw
		oldSensor		  = sensorList

		try:

			sensors = {}
			
			U.getGlobalParams(inp)

			oneisBLElongConnectDevice = False
			if "sensors" in inp:	
				if "BLEconnect" in inp["sensors"]: 
					sensors["BLEconnect"] = copy.deepcopy(inp["sensors"]["BLEconnect"])
				for ss in inp["sensors"]:
					#U.logger.log(30, u"1-ss:{}, sens:{} ".format(ss, inp["sensors"][ss]))
					#if ss == "BLEdirectMiTempHumSquare":	
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
						sensors["isBLElongConnectDevice"][ss] = copy.deepcopy(inp["sensors"][ss])



			if sensors == {} and "OUTPUTswitchbotRelay" not in inp["output"] and "OUTPUTswitchbotCurtain" not in inp["output"]:

				U.logger.log(30, u" no {} definitions supplied in sensorList / or switchbot/switchbotCurtain in outputs{};  stopping (1)".format(sensor, inp["output"]))
				time.sleep(5)
				threadDictReadSwitchbot["state"] = "stop"
				threadDictDoSwitchbot["state"] = "stop"
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
					#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"CCC:{} ".format(CCC))
					for devId in CCC[ss]:
						#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"devId:{} ".format(devId))
						if "mac" not in CCC[ss][devId]: continue
						thisMAC = CCC[ss][devId]["mac"]
						#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"{} ".format(thisMAC))
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
					#if ss =="BLEdirectMiTempHumSquare":	U.logger.log(30, u"macListNew:{} ".format(macListNew))




			#U.logger.log(30, u"BLEconnect - chechink devices (1):{}".format(macList))
			for thisMAC in macListNew:
				if thisMAC not in macList:
					macList[thisMAC] = copy.deepcopy(macListNew[thisMAC])
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


			switchBotPresent = False
			for devType in ["OUTPUTswitchbotRelay"]:
				if devType in inp["output"]:
					for devId in inp["output"][devType]:
						if "mac" not in inp["output"][devType][devId]: continue
						thisMAC = inp["output"][devType][devId]["mac"]
						switchBotConfig[thisMAC] = {"sType":"switchbotbot",
											 "devType":					devType,
											 "blehandle":				"16",
											 "blehandleStatus":			"13",
											 "statusCmd":				"5702",   # the use blehandleStatus to get basic settings
											 "moveToNextPosCmd": 		"570100", # press/off/press/off ...
											 "onCmd": 					"570101", # on
											 "offCmd":					"570102", # off
											 "onHoldCmd": 				"570103", # on and hold 
											 "modeOfDevice":			"donotchange",
											 "holdSeconds":	 			-1,
											 "cmdPressNormal":			"57036400",
											 "cmdPressInverse":			"57036401",
											 "cmdSwitchNormal":			"57036410",
											 "cmdSwitchInverse": 		"57036411",
											 "cmdHoldtime": 			"570F08", # + secs to hold 
											 "lastFailedTryTime":		0,
											 "lastFailedTryCount":		0,
											 "suppressQuickSecond":		-10,
											 "devId": 			devId }
						if "modeOfDevice" in inp["output"][devType][devId]:
							switchBotConfig[thisMAC]["modeOfDevice"] = 	inp["output"][devType][devId]["modeOfDevice"]
						switchBotConfig[thisMAC]["suppressQuickSecond"] = float(inp["output"][devType][devId].get("suppressQuickSecond",-10.))
							#U.logger.log(30, u"=== modeOfDevice:{}".format(inp["output"][devType][devId]["modeOfDevice"]))
						if "holdSeconds" in inp["output"][devType][devId]:
							switchBotConfig[thisMAC]["holdSeconds"] = 	inp["output"][devType][devId]["holdSeconds"]
							#U.logger.log(30, u"=== holdSeconds:{}".format(inp["output"][devType][devId]["holdSeconds"]))

							#U.logger.log(30, u"=== holdSeconds:{}".format(inp["output"]["OUTPUTswitchbotRelay"][devId]["holdSeconds"]))
						switchBotPresent = True
			for devType in ["OUTPUTswitchbotCurtain"]:
				if devType in inp["output"]:
					for devId in inp["output"][devType]:
						if "mac" not in inp["output"][devType][devId]: continue
						thisMAC = inp["output"][devType][devId]["mac"]
						switchBotConfig[thisMAC] = {"sType":"switchbotcurtain",
											 "devType":					devType,
											 "blehandle":				"0d",
											 "blehandleStatus":			"0f",
											 "statusCmd":				"5702",
											 "openCmd": 				"570f450105",
											 "closeCmd":				"570f450105",
											 "pauseCmd": 				"570f450105",
											 "positionCmd": 			"570f450105", 
											 "modeOfDevice": 			"ff", 
											 "lastFailedTryTime":		0,
											 "lastFailedTryCount":		0,
											 "devId": 			devId }
						if "modeOfDevice" in inp["output"][devType][devId] and inp["output"][devType][devId]["modeOfDevice"] in ["00","ff"]:
							switchBotConfig[thisMAC]["modeOfDevice"] = 	inp["output"][devType][devId]["modeOfDevice"]
						switchBotConfig[thisMAC]["devType"] = 	devType

							#U.logger.log(30, u"=== holdSeconds:{}".format(inp["output"]["OUTPUTswitchbotRelay"][devId]["holdSeconds"]))
						switchBotPresent = True
			#U.logger.log(20, u" switchBotConfig:{}".format(switchBotConfig))
			#U.logger.log(20, u" BLEconnect - switchBotConfig {}".format(switchBotConfig))

			if len(macList) == 0 and not switchBotPresent:
				U.logger.log(30, u"no BLEconnect - BLElongConnect devices / switchbots supplied in parameters (2)")
				threadDictReadSwitchbot["state"] = "stop"
				threadDictDoSwitchbot["state"] = "stop"
				time.sleep(5)
				exit()

			#U.logger.log(30, u"BLEconnect - chechink devices (2):{}".format(macList))
			#U.logger.log(30, u"macList:{}".format(macList))
			return True
			
		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
		return False



################################
def tryToConnectToBLEconnect(thisMAC, BLEid):
	global BLEconnectMode
	global macList
	global oneisBLElongConnectDevice
	global useHCI
	global lastSignal
	global lastConnect
	global restartCount
	global BLEconnectLastUp

	try:
		#U.logger.log(20, u"{} BLEid:{}".format(thisMAC, BLEid))

		tt = time.time()
		if macList[thisMAC]["up"]:
			if tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["iPhoneRefreshUpSecs"] * 0.99:							return 
		elif tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["iPhoneRefreshDownSecs"] - macList[thisMAC]["quickTest"]:	return 

		if thisMAC in BLEconnectLastUp:
			#U.logger.log(20, "{}  testing lastup delta :{}, refresh secs:{}".format(thisMAC,  tt - BLEconnectLastUp[thisMAC]["lastUp"], macList[thisMAC]["iPhoneRefreshUpSecs"] ))
			if tt - BLEconnectLastUp[thisMAC]["lastUp"] <= macList[thisMAC]["iPhoneRefreshUpSecs"] * 0.99:
				#U.logger.log(20, u"{}  testing lastup delta2 :{}".format(thisMAC,  BLEconnectLastUp[thisMAC]["lastUp"] -  macList[thisMAC]["lastMsgtt"]))
				if BLEconnectLastUp[thisMAC]["lastUp"] -  macList[thisMAC]["lastMsgtt"]  < 60.:									
											#U.logger.log(20, "{}  reject".format(thisMAC))
											return
		#U.logger.log(20, u"{}  testing connect ".format(thisMAC))


		#print "tryToConnectToBLEconnect ", thisMAC
		######### here we actually get the data from the phones ###################
		if BLEconnectMode == "socket":
			data0 = tryToConnectSocket(thisMAC, macList[thisMAC]["BLEtimeout"], BLEid)
		else:
			data0 = tryToConnectCommandLine(thisMAC, macList[thisMAC]["BLEtimeout"])

		lastConnect = time.time()

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

			#U.logger.log(20, u"{} up>{},".format(thisMAC, macList[thisMAC]["up"]) ))

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

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 



#################################
def tryToConnectToSensorDevice(thisMAC):
	global macList
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
			subprocess.call("echo xx > {}temp/BLErestart".format(G.homeDir), shell=True) # signal that we need to restart BLE
			
	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30, u"{} data:{}".format(thisMAC, data))
	return 


#################################
def startReadCmdThread():
	global switchbotActive, switchBotPresent
	global nonSwitchBotActive
	global maxwaitForSwitchBot
	global switchbotQueue
	global threadDictReadSwitchbot, threadDictDoSwitchbot
	global currentActiveGattCommandisSwitchBot

	currentActiveGattCommandisSwitchBot = False
	maxwaitForSwitchBot = 60
	switchbotActive = ""
	nonSwitchBotActive = ""

	U.logger.log(20, u"start switchbot thread ")
	switchbotQueue = Queue.Queue()
	try:
		threadDictReadSwitchbot = {}
		threadDictReadSwitchbot["state"]   		= "start"
		threadDictReadSwitchbot[u"thread"]  = threading.Thread(name=u'checkSwitchbotForCmd', target=checkSwitchbotForCmd)
		threadDictReadSwitchbot[u"thread"].start()

		threadDictDoSwitchbot = {}
		threadDictDoSwitchbot["state"]   		= "start"
		threadDictDoSwitchbot[u"thread"]  = threading.Thread(name=u'doSwitchBotThread', target=doSwitchBotThread)
		threadDictDoSwitchbot[u"thread"].start()

	except  Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 


####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
def execBLEconnect():
	global sensorList,restartBLEifNoConnect
	global macList,oldParams
	global oldRaw,	lastRead
	global BLEsocketErrCount, lastConnect
	global BLEconnectMode
	global sensor
	global oneisBLElongConnectDevice
	global maxTrieslongConnect
	global useHCI, useHCI2
	global lastSignal
	global restartCount
	global nowTest, nowP
	global switchBotConfig, switchbotActive, switchBotPresent, switchbotQueue, nonSwitchBotActive, expCommands
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
	BLEconnectMode			= "commandLine" # socket or commandLine
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
	waitMin					= 2.
	oldRaw					= ""

	myPID				= str(os.getpid())
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")# kill  old instances of myself if they are still running

	loopCount		  	= 0
	sensorRefreshSecs 	= 90
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
	lastMsg				= {}
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

	useHCI, myBLEmac, BLEid, bus, useHCI2 = startHCI()
	text = "{}-{}-{}".format(useHCI, bus, myBLEmac)
	U.sendURL( data={"data":{"hciInfo_BLEconnect":text}}, squeeze=False, wait=False )

	tlastQuick = time.time()

	
	startReadCmdThread()
	U.logger.log(30, "starting v:{} \n                            using HCI:{}/{}; mac#:{}; bus:{}; pid#:{}; eth0IP:{}; wifi0IP:{}; eth0Enabled:{}; wifiEnabled:{}".format(VERSION, useHCI, useHCI2, myBLEmac, bus, myPID, eth0IP, wifi0IP, eth0Enabled, wifiEnabled))
	while True:

			tt = time.time()
			#U.logger.log(20, "loop time after start:{}".format(tt-startSeconds))

			if tt - lastRead > 8 :
				newParameterFile = readParams()
				eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
				lastRead = tt
				if not checkIfHCIup(useHCI):
					U.logger.log(20, "requested a restart of BLE stack due to {} down ".format(useHCI))
					#subprocess.call("echo xx > {}temp/BLErestart".format(G.homeDir), shell=True) # signal that we need to restart BLE
					cmd = "sudo hciconfig {} reset".format(useHCI)
					ret = readPopen(cmd) # enable bluetooth
					U.logger.log(20,"cmd:{} ".format(cmd)  )
					time.sleep(1)
					restartCount +=1
					if not checkIfHCIup(useHCI): # simple restart did not woek, lets do a master restart 
						U.writeFile("temp/restartNeeded", "bleconnect request")
					else:
						U.logger.log(20,"...restart fixed".format()  )


			if restartBLEifNoConnect and (tt - lastSignal > (2*3600+ 600*restartCount)) or counterFunctionNotImplemented > 20 :
				U.logger.log(20, "requested a restart of BLE stack due to no signal for {:.0f} seconds".format(tt-lastSignal))
				subprocess.call("echo xx > {}temp/BLErestart".format(G.homeDir), shell=True) # signal that we need to restart BLE
				lastSignal = time.time() +30
				restartCount +=1

			#checkSwitchbotForCmd()

			if time.time() - tlastQuick > 1: 
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
