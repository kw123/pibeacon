#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# 
##
##	 read BLE sensors and send http to indigo with data
#
##
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
import traceback
G.program = "BLEconnect"
VERSION = 7.1
ansi_escape =re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')


#################################
def signedIntfrom16(string):
	try:
		intNumber = int(string,16)
		if intNumber > 32767: intNumber -= 65536
	except	Exception as e:
		U.logger.log(20, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
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
		U.logger.log(30,u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 




#################################
def startHCI():
	global BLEconnectMode
	global macList
	global oneisBLElongConnectDevice, switchBotPresent
	global useHCI
	## give other ble functions time to finish

	defaultBus = "USB"
	doNotUseHCI = ""
	BusUsedByBeaconloop = ""
	time.sleep(10)

	if oneisBLElongConnectDevice or switchBotPresent:
		for ii in range(3):
			time.sleep(ii*5)
			hciBeaconloopUsed, raw  = U.readJson("{}temp/beaconloop.hci".format(G.homeDir))
			U.logger.log(30, "BLE(long)connect: beconloop uses: {}".format(hciBeaconloopUsed))
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
			U.logger.log(30, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			cmd = "timeout 5 sudo hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -"
			ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			U.logger.log(30, "cmd: {} and ret:".format(cmd, ret))

			cmd = "timeout 20 sudo hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -"
			ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			U.logger.log(20, "cmd: {} and ret:".format(cmd, ret))
			U.sendURL( data={"data":{"hciInfo":"err-need-2-USB"}}, squeeze=False, wait=False )
			time.sleep(5)
			exit()

		U.logger.log(30, "BLE(long)connect: BLEconnectUseHCINo-bus: {}; default:{}, HCIUsedByBeaconloop:{}; BusUsedByBeaconloop:{}".format(G.BLEconnectUseHCINo, defaultBus, doNotUseHCI, BusUsedByBeaconloop))
		useHCI,  myBLEmac, BLEid, bus = U.selectHCI(HCIs["hci"], G.BLEconnectUseHCINo, defaultBus, doNotUseHCI=doNotUseHCI)
		if BLEid >= 0:
			U.logger.log(30, "BLE(long)connect: using mac:{};  useHCI: {}; bus: {}; mode: {} searching for MACs:\n{}".format(myBLEmac, useHCI, HCIs["hci"][useHCI]["bus"], BLEconnectMode , macList))
			return 	useHCI,  myBLEmac, BLEid, bus 

		else:
			text = "BLEconnect: BLE STACK is not UP HCI-info: useHCI:{},  myBLEmac:{}, BLEid:{}, \n{}".format(useHCI,  myBLEmac, BLEid, HCIs)
			U.logger.log(20, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			U.sendURL( data={"data":{"hciInfo":"err-BLE-stack-not-up"}}, squeeze=False, wait=False )
			time.sleep(25)
			exit()
	else:
			text = "BLEconnect: BLE STACK HCI is empty HCI:{}".format(HCIs)
			U.logger.log(20, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			U.sendURL( data={"data":{"hciInfo":"err-BLE-stack-empty"}}, squeeze=False, wait=False )
			time.sleep(25)
			exit()
	exit()


#################################
def checkIfHCIup(useHCI):
	HCIs = U.whichHCI()
	if useHCI in HCIs["hci"]:
		if HCIs["hci"][useHCI]["upDown"] == "UP": return True
	return False

#################################
def escape_ansi(line):
	try:	ret = ansi_escape.sub('', line).encode('ascii',errors='ignore')
	except: ret = ""
	return ret



#################################
def batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=3000., batteryVoltAt0=2700.):
	try:
		batteryLowVsTemp			= (1. + 0.7*min(0.,temp-10.)/100.) * batteryVoltAt0 # (changes to 0.9* 2700 @ 0C; to = 0.8*2700 @-10C )
		batteryLevel 				= int(min(100.,max(0.,100.* (batteryVoltage - batteryLowVsTemp)/(batteryVoltAt100-batteryLowVsTemp))))
		return batteryLevel
	except	Exception as e:
		U.logger.log(30,u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 0




#################################
def connectGATT(useHCI, thisMAC, timeoutGattool, timeoutConnect, repeat=1, random=False, verbose = False):
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot, switchbotActive
	global nonSwitchBotActive

	try:
		nTries = 1
		for kk in range(nTries):
			if switchBotPresent and switchbotActive in["waiting", "waitingForPrio"]:  
				nonSwitchBotActive = False
				return ""
			nonSwitchBotActive = True
			cmd = "sudo /usr/bin/gatttool -i {} -b {} {} -I".format(useHCI,  thisMAC, "-t random " if random else ""  ) 
			if verbose: U.logger.log(20,"{} ;  expecting: '>'".format(cmd))
			expCommands = pexpect.spawn(cmd)
			ret = expCommands.expect([">","error",pexpect.TIMEOUT], timeout=timeoutGattool)
			if ret == 0:
				pass
				#U.logger.log(20,"gatttool started successful: {}-==-:{}".format(expCommands.before,expCommands.after))
			else:
				if kk == nTries -1: 
					#U.logger.log(20, u"gatttool error, giving up: {}-==-:{}".format(expCommands.before,expCommands.after))
					time.sleep(1)
					return ""
				#U.logger.log(20, u"gatttool error:  {}-==-:{}".format(expCommands.before,expCommands.after))
				expCommands = ""
				continue

			time.sleep(0.1)
			#ret = expCommands.expect(".*", timeout=0.5)s
			#U.logger.log(20,"... .*: {}-==-:{}".format(expCommands.before,expCommands.after))
			for ii in range(repeat):
				try:
					if switchBotPresent and switchbotActive in["waiting", "waitingForPrio"]:  
						nonSwitchBotActive = False
						return ""
					if verbose: U.logger.log(20,"send connect try#:{}  expecting: Connection successful ".format(ii))
					expCommands.sendline("connect")
					ret = expCommands.expect(["Connection successful","Error", pexpect.TIMEOUT], timeout=timeoutConnect)
					if ret == 0:
						if verbose: U.logger.log(20,"connect successful: {}-==-:{}".format(escape_ansi(expCommands.before),escape_ansi(expCommands.after)))
						#ret = expCommands.expect(".*", timeout=0.5)
						#U.logger.log(20,"... .*: {}-==-:{}".format(expCommands.before,expCommands.after))
						nonSwitchBotActive = False
						return expCommands
					else:
						if verbose: U.logger.log(20, u"connect error: waiting 1 sec;  .. {}-==-:{}".format(escape_ansi(expCommands.before),escape_ansi(expCommands.after)))
						time.sleep(1)
				except Exception as e:
					U.logger.log(20, u"Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))


			#U.logger.log(20, u"connect error giving up")

		if expCommands != "": disconnectGattcmd(expCommands, thisMAC, 2)

		nonSwitchBotActive = False
		return ""
	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	nonSwitchBotActive = False
	return ""



#################################
def disconnectGattcmd(expCommands, thisMAC, timeout, verbose=False):	
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot
	try:
		if expCommands == "": return False
		expCommands.sendline("quit" )
		if verbose: U.logger.log(20,"sendline disconnect ")
		ret = expCommands.expect([".*","Error",pexpect.TIMEOUT], timeout=timeout)
		if ret == 0:
			expCommands.kill(0)
			U.killOldPgm(-1,"gatttool",  param1=thisMAC,param2="",verbose=False)
			if verbose: U.logger.log(20,"quit ok")
			return True
		else:
			if verbose: U.logger.log(20,"not disconnected, quit command error: {}".format(escape_ansi(expCommands.after)))
			expCommands.kill(0)
			U.killOldPgm(-1,"gatttool",  param1=thisMAC,param2="",verbose=False)
			return False
	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return False



#################################
def writeGattcmd(expCommands, cc, expectedTag, timeout, verbose=False):	
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot
	try:		
		for ii in range(3):
			if switchBotPresent and switchbotActive in["waiting", "waitingForPrio"]:  return False

			if verbose: U.logger.log(20,"sending cmd:{}, expecting:'{}'".format(cc, expectedTag.encode('ascii', errors='ignore')))
			expCommands.sendline( cc )
			ret = expCommands.expect([expectedTag,"Error","failed",pexpect.TIMEOUT], timeout=5)
			if ret == 0:
				if verbose: U.logger.log(20,"... successful: BF:{}-- AF:{}--".format(escape_ansi(expCommands.before), escape_ansi(expCommands.after)))
				return True
			else: 
				#U.logger.log(20, u"... error, quit: {}-{}".format(expCommands.before, expCommands.after))
				continue
			ret = expCommands.expect("\n")

	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return False



#################################
def writeAndListenGattcmd(expCommands, cc, expectedTag, nBytes, timeout, verbose=False):
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot
	try:
		for kk in range(2):
			if switchBotPresent and switchbotActive in["waiting", "waitingForPrio"]:  return []
			if verbose:  U.logger.log(20,"sendline  cmd:{}, expecting:'{}'".format(cc, expectedTag))
			expCommands.sendline( cc )
			ret = expCommands.expect([expectedTag,"Error","failed",pexpect.TIMEOUT], timeout=timeout)
			if ret == 0:
				if verbose: U.logger.log(20,"... successful:  BF:{}-- AF:{}--".format(escape_ansi(expCommands.before),escape_ansi(expCommands.after)))
				ret = expCommands.expect("\n")
				xx = (expCommands.before.replace("\r","").strip()).split() 
				if len(xx) == nBytes:
					if verbose: U.logger.log(20,"returning:{}".format(xx))
					return xx
				else:
					U.logger.log(20,"... error: len != {} .. {}".format(nBytes, xx))
					continue
			else:
				if verbose: U.logger.log(20,"... error: {}-{}".format(escape_ansi(expCommands.before),escape_ansi(expCommands.after)))
				continue
	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return []



#################################
def readGattcmd(expCommands, cc, expectedTag, nBytes, timeout, verbose=False):
	global switchBotConfig, switchbotActive, switchBotPresent, maxwaitForSwitchBot
	try:
		for kk in range(2):
			if switchBotPresent and switchbotActive in["waiting", "waitingForPrio"]:  return []
			if verbose: U.logger.log(20,"sendline  cmd:{}, expecting:'{}'".format(cc, expectedTag))
			expCommands.sendline( cc )
			ret = expCommands.expect([expectedTag,"Error","failed",pexpect.TIMEOUT], timeout=timeout)
			if ret == 0:
				if verbose: U.logger.log(20,"... successful:  BF:{}-- AF:{}--".format(escape_ansi(expCommands.before),escape_ansi(expCommands.after)))
				ret = expCommands.expect("\n")
				xx = (expCommands.before.replace("\r","").strip()).split() 
				if len(xx) == nBytes or nBytes <0:
					return xx
				else:
					if verbose: U.logger.log(20,"... error: len != {}".format(nBytes))
					continue
			else:
				if verbose: U.logger.log(20,"... error: {}-{}".format(escape_ansi(expCommands.before),escape_ansi(expCommands.after)))
				continue
	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return []



#################################
def batchGattcmd(useHCI, thisMAC, cc, expectedTag, nBytes=0, repeat=3, verbose=False, timeout=6, thisIsASwitchbotCommand = False):
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
		if verbose: U.logger.log(20,"cmd:{} ;  expecting: '{}'; nbytes:{}, repeat:{}, switchBotPresent:{}; switchbotActive:{}; timeout:{}".format(cmd, expectedTag, nBytes, repeat, switchBotPresent, switchbotActive, timeout))
		for kk in range(repeat):
			#if verbose: U.logger.log(20,"try#:{}, switchBotPresent:{}; switchbotActive:{} ".format(kk, switchBotPresent, switchbotActive))
			ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			if ret[0].find(expectedTag) > -1:
				if verbose: U.logger.log(20,"... successful:  0:{}".format( escape_ansi(ret[0]) ))
				if nBytes == 0: 
					currentActiveGattCommandisSwitchBot = False
					return expectedTag
				xx = ret[0].split(expectedTag)[1].replace("\r","").strip()
				xx = xx.split() 
				if len(xx) == nBytes or nBytes < 0:
					currentActiveGattCommandisSwitchBot = False
					return xx
				else:
					if verbose: U.logger.log(20,"... error: len:{} != {}".format(len(xx), nBytes))
					continue
			else:
				if verbose: U.logger.log(20,"... error: {}".format( ret[1].strip() ))
			time.sleep(0.5)

	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	currentActiveGattCommandisSwitchBot = False
	return []



#################################
def tryToConnectSocket(thisMAC,BLEtimeout,devId):
	global BLEsocketErrCount, lastConnect
	global switchBotPresent, switchbotActive

	retdata	 = {"rssi": -999, "txPower": -999,"flag0ok":0,"byte2":0}
	if switchBotPresent and switchbotActive in ["active","waiting", "waitingForPrio"]:  return retdata
	if time.time() - lastConnect < 3: time.sleep( max(0,min(0.5,(3.0- (time.time() - lastConnect) ))) )
	U.logger.log(20, u"starting for {}, using devid:{}".format(thisMAC, devId))

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
			U.logger.log(20, u"in Line {} has error ... sock.recv error, likely time out ".format(sys.exc_traceback.tb_lineno))
			U.restartMyself(reason="sock.recv error", delay = 10)

	except	Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	U.logger.log(10, "{}:  {}".format(thisMAC, retdata))
	BLEsocketErrCount = 0
	return retdata



#################################
def tryToConnectCommandLine(thisMAC, BLEtimeout):
	global BLEsocketErrCount, lastConnect, useHCI
	global switchBotPresent, switchbotActive, nonSwitchBotActive

	try:
		nonSwitchBotActive = True
		retdata	 = {"rssi": -999, "txPower": -999,"flag0ok":0,"byte2":0}
		if switchBotPresent and switchbotActive in ["active","waiting", "waitingForPrio"]:  
			nonSwitchBotActive = False
			return retdata
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
			ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			parts = ret[0].strip("\n").split("\n")
			U.logger.log(20, "cmd:{}; {}  1. try ret: {} --- err>>{}<<".format(cmd, thisMAC, ret[0].strip("\n"), ret[1].strip("\n")))

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
			U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
			retdata = {}
	
	#U.logger.log(20, "{} return data: {}".format(thisMAC, retdata))
	nonSwitchBotActive = False
	return retdata


#################################
def BLEXiaomiMiTempHumSquare(thisMAC, data0):
	global BLEsocketErrCount, macList, maxTrieslongConnect, useHCI
	global switchBotConfig, switchbotActive, switchBotPresent, nonSwitchBotActive

	nonSwitchBotActive = True
	data = copy.deepcopy(data0)
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
		if time.time() - macList[thisMAC]["nextRead"] < 0 or time.time() - macList[thisMAC]["lastTesttt"] < macList[thisMAC]["readSensorEvery"]: return data
		#print "BLEXiaomiMiTempHumSquare ", thisMAC

		minWaitAfterBadRead = max(5,macList[thisMAC]["readSensorEvery"]/3)
		macList[thisMAC]["nextRead"] = time.time() + minWaitAfterBadRead
		for ii in range(1):
			if switchBotPresent and switchbotActive in["waiting", "waitingForPrio"]:  
				nonSwitchBotActive = False
				return ""

			startCMD = time.time()

			expCommands = connectGATT(useHCI, thisMAC, 5, 25, repeat=2, verbose=verbose)
			if expCommands == "":
				macList[thisMAC]["nextRead"] = time.time() + minWaitAfterBadRead
				macList[thisMAC]["triesWOdata"] +=1
				data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
				if macList[thisMAC]["triesWOdata"] > maxTrieslongConnect:
					macList[thisMAC]["triesWOdata"] = 0
					#U.logger.log(20, u"thisMAC{}, not connected, send to indigo, triesWOdata:{}, repeat in {} secs".format(thisMAC, macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
					data["connected"] = False
					data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
				#U.logger.log(20, u"not connected, triesWOdata:{}, repeat in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
				nonSwitchBotActive = False
				return data

			readData = []

			for nn in range(2):
				if switchBotPresent and switchbotActive in["waiting", "waitingForPrio"]:  return ""
				readData = writeAndListenGattcmd(expCommands, "char-write-req 0038 0100", "value:", 5, 15, verbose=verbose)
				if readData != []: break
				time.sleep(1)
			disconnectGattcmd(expCommands, thisMAC, 2)


			#U.logger.log(20, "{}  {}. try ret:{}".format(thisMAC, ii, readData))
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
				nonSwitchBotActive = False
				return data

			macList[thisMAC]["triesWOdata"] += 1

		data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
		if macList[thisMAC]["triesWOdata"] >= maxTrieslongConnect:
			macList[thisMAC]["triesWOdata"] = 0
			#U.logger.log(20, u"error, connected but no data, triesWOdata:{} repeast in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))

	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		data["badSensor"] = True
	
	#U.logger.log(20, "{} return data: {}".format(thisMAC, data))
	
	nonSwitchBotActive = False
	return data



#################################
def BLEXiaomiMiVegTrug(thisMAC, data0):
	global BLEsocketErrCount, macList, maxTrieslongConnect, useHCI
	global switchBotConfig, switchbotActive, switchBotPresent, nonSwitchBotActive

	nonSwitchBotActive = True
	data = copy.deepcopy(data0)
	try:
		if time.time() - macList[thisMAC]["nextRead"] < 0 or time.time() - macList[thisMAC]["lastTesttt"] < macList[thisMAC]["readSensorEvery"]: return data
		verbose = False
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
		#   0-1: temp *10 [�C]
		#     2: ??
		#   3-6: bright [lux]
		#     7: moist [%]
		#   8-9: conduct [�S/cm]
		# 10-15: ?? 
		# eg: 'f4 00 69 00 00 00 00 1d 11 01 02 3c 00 fb 34 9b'
		"""
			
		if verbose: U.logger.log(20, u"{},  tries:{}, DT:{}".format(thisMAC, macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
		expCommands = connectGATT(useHCI, thisMAC, 5,15, verbose=verbose)
		if expCommands == "":
			macList[thisMAC]["triesWOdata"] +=1
			data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
			if macList[thisMAC]["triesWOdata"] > maxTrieslongConnect:
				macList[thisMAC]["triesWOdata"] = 0
				#U.logger.log(20, u"thisMAC:{}, error, not connected, sending not connected to indigo, triesWOdata:{}, retrying in {} secs".format(thisMAC, macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
				U.logger.log(20, u"thisMAC:{}, error, not connected, triesWOdata:{} retrying in {} secs".format(thisMAC, macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
			return data

		result1 = []
		result2 = []

		for nn in range(1):
			if switchBotPresent and switchbotActive in["waiting", "waitingForPrio"]:  return ""
			if not writeGattcmd(expCommands, "char-write-req 33 A01F", "Characteristic value was written successfully", 5, verbose=verbose):
									continue

			result1 = readGattcmd(expCommands, "char-read-hnd 38", "Characteristic value/descriptor:", 7, 5, verbose=verbose)
			if result1 == []:		continue

			result2 = readGattcmd(expCommands, "char-read-hnd 35", "Characteristic value/descriptor:", 16, 5, verbose=verbose)
			if result2 == []:		continue

			break

		disconnectGattcmd(expCommands, thisMAC, 2)

		if verbose: U.logger.log(20, u"connect results:{} - {}".format(result1, result2))

		if result1 == [] or result2 == []:
			data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
			if macList[thisMAC]["triesWOdata"] >= maxTrieslongConnect:
				macList[thisMAC]["triesWOdata"] = 0
				if verbose: U.logger.log(20, u"error connected but do data, send not connetced to indigo, triesWOdata:{}, retrying in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
			nonSwitchBotActive = False
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
			macList[thisMAC]["lastTesttt"] 			= 0.

		if ( abs(data["temp"] 			- macList[thisMAC]["lastData"]["temp"])			> 0.5 	or
			 abs(data["moisture"]  		- macList[thisMAC]["lastData"]["moisture"])		> 2 	or
			 abs(data["Conductivity"]	- macList[thisMAC]["lastData"]["Conductivity"])	> 2 ):
			macList[thisMAC]["lastTesttt"] = time.time()
			macList[thisMAC]["lastData"]  = copy.deepcopy(data)
			data["dataChanged"]			=  True
		if verbose: U.logger.log(20, "{} return data: {}".format(thisMAC, data))
		nonSwitchBotActive = False
		return data


	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		nonSwitchBotActive = False
		data["badSensor"] = True
	
	if verbose: U.logger.log(20, "{} return data: {}".format(thisMAC, data))
	
	nonSwitchBotActive = False
	return data



#################################
def BLEinkBirdPool01B(thisMAC, data0):
	global BLEsocketErrCount, macList, maxTrieslongConnect, useHCI
	global switchBotConfig, switchbotActive, switchBotPresent, nonSwitchBotActive

	data = copy.deepcopy(data0)
	verbose = True
	nonSwitchBotActive = True
	try:
		if (time.time() - macList[thisMAC]["nextRead"] < 0 or time.time() - macList[thisMAC]["lastTesttt"] < macList[thisMAC]["readSensorEvery"]): return data

		minWaitAfterBadRead = min(20.,max(5.,macList[thisMAC]["readSensorEvery"]/3.))
		macList[thisMAC]["nextRead"] = time.time() + minWaitAfterBadRead

		"""
		# simple read: 
		sudo gatttool  --device=49:42:01:00:12:76 --char-read --handle=0x0024
		# temp: first 16bytes  in little endian format 
		"""
		result = batchGattcmd(useHCI, thisMAC, "--char-read --handle=0x{}".format(macList[thisMAC]["bleHandle"]), "descriptor:", nBytes=7, repeat=4, verbose=verbose, timeout=6)

		if verbose: U.logger.log(20, u"connect results:{}".format(result))

		if result == []:
			data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
			if macList[thisMAC]["triesWOdata"] >= maxTrieslongConnect:
				macList[thisMAC]["triesWOdata"] = 0
				if verbose: U.logger.log(20, u"error connected but do data, send not connetced to indigo, triesWOdata:{}, retrying in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
			nonSwitchBotActive = False
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
		nonSwitchBotActive = False
		return data

	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		data["badSensor"] = True
	
	if verbose: U.logger.log(20, "{}  return 99 data: {}".format(thisMAC, data))
	
	nonSwitchBotActive = False
	return data



#################################
def checkSwitchbotForCommand():
	global switchbotActive, switchBotPresent
	global nonSwitchBotActive
	global switchbotQueue
	global threadDict
	global maxwaitForSwitchBot

	maxwaitForSwitchBot = 60
	switchbotActive = ""
	nonSwitchBotActive = False
	U.logger.log(20, u"checkSwitchbotForCommand start")
	while threadDict["state"] != "stop":
		time.sleep(0.5)
		if not switchBotPresent: 
			while not switchbotQueue.empty():
				yy, xx = switchbotQueue.get()
			time.sleep(5)
			continue

		jData = U.checkForNewCommand("switchbot.cmd")
	
		if len(jData) > 0:
			U.logger.log(20, u" ADDING TO QUEUE  switchbotActive:{}, data:{}".format(switchbotActive, jData))
			switchbotQueue.put([0,jData])

		if switchbotActive in["","delayed"] and not switchbotQueue.empty(): 
			doSwitchBot()
			#U.logger.log(20, u" returning from doSwitchBot")

	U.logger.log(20, u"checkSwitchbotForCommand finish")

	return 


#################################
def setSwitchbotParameters(thisMAC, expCommands, verbose):
	#if verbose: U.logger.log(20, "{} entering setparameters, switchBotConfig:{}".format(thisMAC, switchBotConfig[thisMAC]))
	if verbose: U.logger.log(20, "{} entering setparameters".format(thisMAC))
	if  switchBotConfig[thisMAC]["modeOfDevice"] in ["cmdPressNormal","cmdPressInverse","cmdSwitchNormal","cmdSwitchInverse"]: 
		writeHandle 	= switchBotConfig[thisMAC]["blehandle"]
		cmdmodeOfDevice	= switchBotConfig[thisMAC][switchBotConfig[thisMAC]["modeOfDevice"]]
		ok = False
		for ii in range(2):
			if writeGattcmd(expCommands, "char-write-req {} {}".format(writeHandle, cmdmodeOfDevice), "Characteristic value was written successfully", 5, verbose=verbose):
				if verbose: U.logger.log(20, "{} return ok set mode:{}".format(thisMAC, cmdmodeOfDevice))
				ok = True
				break
		if not ok:
			if verbose: U.logger.log(20, "{} return not ok for mode set".format(thisMAC))

	cmdHoldtime = switchBotConfig[thisMAC]["cmdHoldtime"]
	holdSeconds = int(switchBotConfig[thisMAC]["holdSeconds"])
	ok = False
	if holdSeconds >= 0:
		for ii in range(2):
			if writeGattcmd(expCommands, "char-write-req {} {}{:02x}".format(writeHandle, cmdHoldtime, holdSeconds), "Characteristic value was written successfully", 5, verbose=verbose):
				if verbose: U.logger.log(20, "{} return ok cmd:{}{:02x}".format(thisMAC, cmdHoldtime, holdSeconds))
				ok = True
				break
		if not ok:
			if verbose: U.logger.log(20, "{} return not ok for set hold secs".format(thisMAC))
	return True


#################################
def doSwitchBot():
	global useHCI
	global switchBotConfig, switchbotActive, nonSwitchBotActive
	global switchbotQueue
	#### check out for definistions of commands and returns
	#### https://github.com/OpenWonderLabs/SwitchBotAPI-BLE/blob/latest/devicetypes/bot.md

	while nonSwitchBotActive: 
		U.logger.log(20, u" WAITING FOR PRIO")
		switchbotActive = "waitingForPrio"
		time.sleep(0.5)

	switchbotActive	= "active"
	switchbotAction = time.time() 
	verbose = True
	verbose2 = True
	# jData= {"mac":mac#,"onOff":"0/1","statusRequest":True}
	if  switchbotQueue.empty(): 
		U.logger.log(20, u" empty:{}")
		switchbotActive = ""
		return 

	retryCount, jData = switchbotQueue.get()
	switchbotQueue.task_done()
	if verbose2: U.logger.log(20, u" retrycount:{}; jData:{}".format(retryCount, jData))


	if "mac"   not in jData: 
		switchbotActive = ""
		return 

	actualStatus = ""
	checkParams = False
	thisMAC = jData["mac"].upper()

	if thisMAC not in switchBotConfig: 
		switchbotActive = ""
		retryCount = 99
		return 

	retData0 = {"outputs": {"OUTPUTswitchbotRelay": {switchBotConfig[thisMAC]["devId"]: {} }}}
	retData  = retData0["outputs"]["OUTPUTswitchbotRelay"][switchBotConfig[thisMAC]["devId"]]
	retryCount += 1
	if retryCount > 3: 
		retData["error"] = "connection error to switchbot, for command:{}".format(jData)
		U.logger.log(20, u"sending error message, command failed, could not connect")
		U.sendURL(retData0, squeeze=False)
		switchbotActive = ""
		return 

	try:
		readParams()

		if switchBotConfig[thisMAC]["sType"] != "switchbotbot":
			switchbotActive = ""
			return 

		writeHandle = switchBotConfig[thisMAC]["blehandle"]
		readHandle = switchBotConfig[thisMAC]["blehandleStatus"]

		if verbose2: U.logger.log(20, "{} trying to connect".format(thisMAC))
		expCommands = connectGATT(useHCI, thisMAC, 5,15, repeat=2, random=True, verbose=verbose)
		if expCommands == "":
			U.logger.log(20, "{} failed to connect ".format(thisMAC))
			switchbotQueue.put([retryCount, jData])
			switchbotActive	= ""
			return 

		#make keys lowercase
		newData = {}
		for item in jData:
			newData[item.lower()] = jData[item]


		if verbose2: U.logger.log(20, "{} connected ".format(thisMAC))
		if "setparameters" in newData:
			checkParams = setSwitchbotParameters(thisMAC, expCommands, verbose)

		nPulses = 0
		pulseLength = 0
		cmd = ""
		try:
			if    "onoff"  in newData:	cmd = newData["onoff"]
			elif  "onoff"  in newData:	cmd = newData["onoff"]
			elif  "pulses" in newData: 
										cmd = "pulses"
										nPulses = int(newData.get("pulses",1)) 
										pulseLengthOn  = float(newData.get("pulselengthon",0))
										pulseLengthOff = float(newData.get("pulselengthoff",1))
			elif  "statusrequest" in newData: 
										pass
			elif  "setparameters" in newData: 
										pass
			else:
				if verbose2: U.logger.log(20, "{}  command not recognized :{}".format(thisMAC, newData))
				retryCount = 99
				switchbotActive	= ""
				return 
		except  Exception as e:
			U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
			if verbose2: U.logger.log(20, "{}  command not recognized :{}".format(thisMAC, newData))
			retryCount = 99
			switchbotActive	= ""
			return 

		onCmd 				= switchBotConfig[thisMAC]["onCmd"]	
		offCmd 				= switchBotConfig[thisMAC]["offCmd"]	
		onHoldCmd			= switchBotConfig[thisMAC]["onHoldCmd"]
		cmdHoldtime 		= switchBotConfig[thisMAC]["cmdHoldtime"]	
		cmdPressNormal 		= switchBotConfig[thisMAC]["cmdPressNormal"]	
		cmdSwitchNormal 	= switchBotConfig[thisMAC]["cmdSwitchNormal"]	

		if cmd != "":
			if nPulses == 0:
				if str(cmd) == "1":			onOff =  onCmd;  actualStatus = "on"
				else:  						onOff =  offCmd; actualStatus = "off"
				if writeGattcmd(expCommands, "char-write-req {} {}".format(writeHandle, onOff), "Characteristic value was written successfully", 5, verbose=verbose):
					retData ["actualStatus"] =  actualStatus
					#U.sendURL(retData)
					switchBotConfig[thisMAC]["lastFailedTryCount"] = 0 
					switchBotConfig[thisMAC]["lastFailedTryTime"] = 0 
					checkParams = True
					if verbose2: U.logger.log(20, "{} on/off: return ok retData:{}; checkParams:{} ".format(thisMAC, retData, checkParams))
				else:
					switchbotQueue.put([retryCount, newData])
					if verbose2: U.logger.log(20, "{} on/off: ret data not ok, putting command back into queue: ".format(thisMAC))

			elif nPulses >0: 
				# echo '{"mac":"E1:7E:66:F6:A0:E7","pulses":5,"pulseLengthOn":1.8,"pulseLengthOff":4}' > temp/switchbot.cmd
				if verbose2: U.logger.log(20, "doing pulses:{}, setting mode to press normal:{}".format(nPulses, cmdPressNormal))
				if writeGattcmd(expCommands, "char-write-req {} {}".format(writeHandle, cmdPressNormal), "Characteristic value was written successfully", 5, verbose=verbose):
					# set pulse length
					if verbose2: U.logger.log(20, "set pulse length to {}".format(pulseLengthOn))
					if writeGattcmd(expCommands, "char-write-req {} {}{:02x}".format(writeHandle, cmdHoldtime, int(pulseLengthOn)), "Characteristic value was written successfully", 5, verbose=verbose):
						#if ok: send the pulses 
						#time.sleep(1)
						for ii in range(nPulses):
							if ii > 0: 
								effSleep = max(2.7,pulseLengthOff+pulseLengthOn+2.7)
								if verbose2: U.logger.log(20, u"thisMAC:{}, sleep pulse off:{}".format(thisMAC, effSleep))
								time.sleep(effSleep)# need to wait on and off time before sending new pulse 

							if verbose2: U.logger.log(20, u"thisMAC:{}, pulse on:{}, #:{}".format(thisMAC, pulseLengthOn, ii+1))
							result = writeGattcmd(expCommands, "char-write-req {} {}".format(writeHandle, onCmd), "Characteristic value was written successfully", 5, verbose=verbose)
							if verbose2: U.logger.log(20, u"pulse cmd result:{}".format(result))
				checkParams = setSwitchbotParameters(thisMAC, expCommands, verbose)
				retData["actualStatus"] =  "off"


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
				result =  readGattcmd(expCommands, "char-read-hnd {}".format(readHandle),  "Characteristic value/descriptor:", -1, 5, verbose=verbose)
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
					if verbose2: U.logger.log(20, "mac: {} return ok;  result: {}, retData:{}".format(thisMAC, result, retData))
					break
				elif len(result) == 1:
					if verbose2: U.logger.log(20, "mac: {} return not ok, should be 3 or 13 long, got only one byte ;  result: {}, retData:{}".format(thisMAC, result, retData))
					if result[0] in ["08","0b","0a"]:
						retData["warning"] = "device is set to use encrypted communication, use phone app to initialize"
						retData["actualStatus"] = "ConfigureDevOnPhone"
					elif result[0] == "01":
						# this ok 
						pass
						#if verbose2: U.logger.log(20, "mac: {} issue warning".format(thisMAC))
						#retData["warning"] = "device needs to be configured on phone"
						#retData["actualStatus"] = "ConfigureDevOnPhone"
					else:
						retData["error"] = "connection error to switchbot, >> please setup device on phone << "
						retData["actualStatus"] = "unkownError"

					if verbose2: U.logger.log(20, "{} statusRequest: setup device on phone".format(thisMAC, result))
				else :
					if verbose2: U.logger.log(20, "{} statusRequest:  unexpected result {}".format(thisMAC, result))

				# if not status: issue status command, then read again
				result = writeGattcmd(expCommands, "char-write-req {} {}".format(writeHandle, switchBotConfig[thisMAC]["statusCmd"] ), "Characteristic value was written successfully", 5, verbose=verbose)


			if retData !={}:
				if verbose2: U.logger.log(20, "{} sending retData0:{}".format(thisMAC, retData0))
				U.sendURL(retData0, squeeze=False)
				switchBotConfig[thisMAC]["lastFailedTryTime"] = 0 
				switchBotConfig[thisMAC]["lastFailedTryCount"] = 0 
				switchbotActive = ""
				expCommands = disconnectGattcmd(expCommands, thisMAC, 5, verbose=verbose)
				return 
		switchbotActive = ""
		expCommands = disconnectGattcmd(expCommands, thisMAC, 5, verbose=verbose)
		return 

		if sType == "switchbotcurtain":
			if verbose2: U.logger.log(20, "{} switchbotcurtain, jData:{}".format(thisMAC, jData))
			if "pos" in jData: 
			
				if   jData["pos"][0].lower() == "o":  cmd = "{}{}00".format(switchBotConfig[thisMAC]["positionCmd"],switchBotConfig[thisMAC]["modeOfDevice"])
				elif jData["pos"][0].lower() == "c":  cmd = "{}{}ff".format(switchBotConfig[thisMAC]["positionCmd"],switchBotConfig[thisMAC]["modeOfDevice"])
				elif jData["pos"][0].lower() == "p":  cmd = switchBotConfig[thisMAC]["pauseCmd"]
				else: 
					try: 
						cmd = "{}{}{:02x}".format(switchBotConfig[thisMAC]["positionCmd"],switchBotConfig[thisMAC]["modeOfDevice"], int(jData["pos"]))
					except:
						U.logger.log(20, u"{} bad command given:{}".format(thisMAC, jData["pos"]))
						expCommands = disconnectGattcmd(expCommands, thisMAC, 5, verbose=verbose)
						return 

				blecmd = "--char-write-req -t random --handle=0x{} --value={}".format(switchBotConfig[thisMAC]["blehandle"], cmd )	
				if verbose2: U.logger.log(20, "{} sending {}".format(thisMAC, blecmd))
				result = batchGattcmd(useHCI, thisMAC, blecmd, "successfully", nBytes=0, repeat=3, verbose=verbose, timeout=4, thisIsASwitchbotCommand = True)

				if result != []:
					retData = {"outputs":{"OUTPUTswitchbotCurtain":{switchBotConfig[thisMAC]["devId"]:{"position": jData["pos"]}}}}
					if verbose: U.logger.log(20, "{} return ok data: {}, retData0:{}".format(thisMAC, result, retData0))
					U.sendURL(retData0, squeeze=False)
					switchbotActive = ""
					switchBotConfig[thisMAC]["lastFailedTryCount"] = 0 
					switchBotConfig[thisMAC]["lastFailedTryTime"] = 0 
					switchbotActive = ""
					expCommands = disconnectGattcmd(expCommands, thisMAC, 5, verbose=verbose)
					return 
				else:
					switchbotQueue.put([retryCount, jData])
					if verbose2: U.logger.log(20, "{} ret data not ok, putting command back into queue: ".format(thisMAC))
			else:
				if verbose2: U.logger.log(20, "{} direction not in command:{}".format(thisMAC))
				switchbotActive = ""
			expCommands = disconnectGattcmd(expCommands, thisMAC, 5, verbose=verbose)
			return 

		else:
			if verbose2: U.logger.log(20, "{} sType not found:{}".format(thisMAC, sType))
			switchbotActive = ""
		expCommands = disconnectGattcmd(expCommands, thisMAC, 5, verbose=verbose)
		return 
	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	
		if verbose2: U.logger.log(20, "{}  return  data: {}".format(thisMAC, switchBotConfig))
	
	switchbotActive = ""
	expCommands = disconnectGattcmd(expCommands, thisMAC, 5, verbose=verbose)
	return  



##################################
def readParams():
		global debug, ipOfServer,myPiNumber,passwordOfServer, userIdOfServer, authentication,ipOfServer,portOfServer,sensorList,restartBLEifNoConnect
		global macList 
		global oldRaw, lastRead, BLEconnectMode
		global sensor
		global oneisBLElongConnectDevice
		global switchBotConfig, switchbotActive, switchBotPresent

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
					#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"1-ss:{} ".format(ss))
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



			if sensors == {} and "OUTPUTswitchbotRelay" not in inp["output"]:

				U.logger.log(30, u" no {} definitions supplied in sensorList / or switchbot def in outputs{};  stopping (1)".format(sensor, inp["output"]))
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
				U.logger.log(20, "macListNew  {},".format(macListNew) )
			if "isBLElongConnectDevice" in sensors:
				CCC = sensors["isBLElongConnectDevice"]
				for ss in CCC: 	
					#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"CCC:{} ".format(CCC))
					for devId in CCC[ss]:
						#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"devId:{} ".format(devId))
						if "mac" not in CCC[ss][devId]: continue
						thisMAC = CCC[ss][devId]["mac"]
						#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"thisMAC:{} ".format(thisMAC))
						if thisMAC not in macListNew:
							macListNew[thisMAC]={"type":"isBLElongConnectDevice",
												 "updateIndigoTiming":60,
												 "lastSend":0,
												 "readSensorEvery":120,
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


			xxx = False
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
											 "devId": 			devId }
						if "modeOfDevice" in inp["output"][devType][devId]:
							switchBotConfig[thisMAC]["modeOfDevice"] = 	inp["output"][devType][devId]["modeOfDevice"]
							#U.logger.log(30, u"=== modeOfDevice:{}".format(inp["output"][devType][devId]["modeOfDevice"]))
						if "holdSeconds" in inp["output"][devType][devId]:
							switchBotConfig[thisMAC]["holdSeconds"] = 	inp["output"][devType][devId]["holdSeconds"]
							#U.logger.log(30, u"=== holdSeconds:{}".format(inp["output"][devType][devId]["holdSeconds"]))

							#U.logger.log(30, u"=== holdSeconds:{}".format(inp["output"]["OUTPUTswitchbotRelay"][devId]["holdSeconds"]))
						xxx = True
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
											 "openCmd": 				"570f450105ff00",
											 "closeCmd":				"570f450105ff64",
											 "pauseCmd": 				"570f450105ff",
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
			switchBotPresent = xxx

			if len(macList) == 0 and not switchBotPresent:
				U.logger.log(30, u"no BLEconnect - BLElongConnect devices / switchbots supplied in parameters (2)")
				exit()

			#U.logger.log(30, u"BLEconnect - chechink devices (2):{}".format(macList))
			#U.logger.log(30, u"macList:{}".format(macList))
			return True
			
		except	Exception as e:
			U.logger.log(50,u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e) )
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

	try:
		#U.logger.log(20, u"thisMAC:{} BLEid:{}".format(thisMAC, BLEid))

		tt = time.time()
		if macList[thisMAC]["up"]:
			if tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["iPhoneRefreshUpSecs"]*0.90:								return 
		elif tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["iPhoneRefreshDownSecs"] - macList[thisMAC]["quickTest"]:	return 

		#print "tryToConnectToBLEconnect ", thisMAC
		######### here we actually get the data from the phones ###################
		if BLEconnectMode == "socket":
			data0 = tryToConnectSocket(thisMAC, macList[thisMAC]["BLEtimeout"], BLEid)
		else:
			data0 = tryToConnectCommandLine(thisMAC, macList[thisMAC]["BLEtimeout"])

		lastConnect = time.time()

		#print	data0
		macList[thisMAC]["lastTesttt"] = tt

		if	data0 != {}:
			if data0["rssi"] !=-999:
				macList[thisMAC]["up"] = True
				lastSignal	 = time.time()
				restartCount = 0
				if os.path.isfile(G.homeDir + "temp/BLErestart"):
					os.remove(G.homeDir + "temp/BLErestart")

			else:
				macList[thisMAC]["up"] = False

			if data0["rssi"]!=macList[thisMAC]["lastData"] or (tt-macList[thisMAC]["lastMsgtt"]) > (macList[thisMAC]["iPhoneRefreshUpSecs"]-1.): # send htlm message to indigo, if new data, or last msg too long ago
				if macList[thisMAC]["lastData"] != -999 and not macList[thisMAC]["up"] and (tt-macList[thisMAC]["lastMsgtt"]) <	 macList[thisMAC]["iPhoneRefreshUpSecs"]+2.:
					macList[thisMAC]["quickTest"] =macList[thisMAC]["iPhoneRefreshDownSecs"]/2.
					return 
				#print "sending "+thisMAC+" " + datetime.datetime.now().strftime("%M:%S"), macList[thisMAC]["up"] , macList[thisMAC]["quickTest"], data0
				macList[thisMAC]["quickTest"] = 0.
				#print "af -"+datetime.datetime.now().strftime("%M:%S"), macList[thisMAC]["up"], macList[thisMAC]["quickTest"], data0
				macList[thisMAC]["lastMsgtt"]  = tt
				macList[thisMAC]["lastData"] = data0["rssi"]
				data={}
				data["sensors"]					= {"BLEconnect":{macList[thisMAC]["devId"]:{thisMAC:data0}}}
				U.sendURL(data=data)

		else:
			macList[thisMAC]["up"] = False
		return 

	except	Exception as e:
		U.logger.log(30,u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
	return 



#################################
def tryToConnectToSensorDevice(thisMAC):
	global macList
	data = {"connected":False, "dataChanged":False, "dataRead":False, "triesWOdata":macList[thisMAC]["triesWOdata"], "badSensor": False}
	try:
		if macList[thisMAC]["devType"] == "BLEXiaomiMiTempHumSquare":
			#U.logger.log(20, "tryToConnectToSensorDevice BLEXiaomiMiTempHumSquare")
			data = BLEXiaomiMiTempHumSquare(thisMAC, data)

		elif macList[thisMAC]["devType"] == "BLEXiaomiMiVegTrug":
			#U.logger.log(20, "tryToConnectToSensorDevice BLEXiaomiMiVegTrug")
			data = BLEXiaomiMiVegTrug(thisMAC, data)


		elif macList[thisMAC]["devType"] == "BLEinkBirdPool01B":
			#U.logger.log(20, "tryToConnectToSensorDevice BLEinkBirdPool01B")
			data = BLEinkBirdPool01B(thisMAC, data)

		else:
			return 

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
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
		U.logger.log(30, u"thisMAC:{}, data:{}".format(thisMAC, data))
	return 


#################################
def startReadCommandThread():
	global switchbotActive, switchBotPresent
	global nonSwitchBotActive
	global maxwaitForSwitchBot
	global switchbotQueue
	global threadDict
	global currentActiveGattCommandisSwitchBot

	currentActiveGattCommandisSwitchBot = False
	maxwaitForSwitchBot = 60
	switchbotActive = ""
	nonSwitchBotActive = False

	U.logger.log(30, u"start switchbot thread ")
	switchbotQueue = Queue.Queue()
	try:
		threadDict = {}
		threadDict["state"]   		= "start"
		threadDict[u"thread"]  = threading.Thread(name=u'checkSwitchbotForCommand', target=checkSwitchbotForCommand)
		threadDict[u"thread"].start()

	except  Exception as e:
		U.logger.log(30, u"in Line {} has error={}".format(traceback.extract_tb(sys.exc_info()[2])[-1][1], e))
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
	global useHCI
	global lastSignal
	global restartCount
	global nowTest, nowP
	global switchBotConfig, switchbotActive, switchBotPresent, switchbotQueue

	switchbotActive			= ""
	switchBotPresent		= False
	switchBotConfig			= {}
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

	useHCI, myBLEmac, BLEid, bus = startHCI()
	text = "{}-{}-{}".format(useHCI, bus, myBLEmac)
	U.sendURL( data={"data":{"hciInfo":text}}, squeeze=False, wait=False )

	tlastQuick = time.time()

	
	startReadCommandThread()
	U.logger.log(30, "starting v:{} \n                            using HCI:{}; mac#:{}; bus:{}; pid#:{}; eth0IP:{}; wifi0IP:{}; eth0Enabled:{}; wifiEnabled:{}".format(VERSION, useHCI, myBLEmac, bus, myPID, eth0IP, wifi0IP, eth0Enabled, wifiEnabled))
	while True:

			tt = time.time()
			#U.logger.log(20, "loop time after start:{}".format(tt-startSeconds))

			if tt - lastRead > 4 :
				newParameterFile = readParams()
				eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
				lastRead = tt
				if not checkIfHCIup(useHCI):
					U.logger.log(20, "requested a restart of BLE stack due to {} down ".format(useHCI))
					#subprocess.call("echo xx > {}temp/BLErestart".format(G.homeDir), shell=True) # signal that we need to restart BLE
					cmd = "sudo hciconfig {} reset".format(useHCI)
					ret = subprocess.Popen(cmd, shell=True,stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate() # enable bluetooth
					U.logger.log(20,"cmd:{} ".format(cmd)  )
					time.sleep(1)
					restartCount +=1
					if not checkIfHCIup(useHCI): # simple restart did not woek, lets do a master restart 
						cmd = "sudo python master.py &"
						ret = subprocess.Popen(cmd, shell=True,stderr=subprocess.PIPE,stdout=subprocess.PIPE).communicate() # enable bluetooth
						U.logger.log(20,"cmd:{} .. ret:{}".format(cmd, ret)  )
						time.sleep(1)
					else:
						U.logger.log(20,"...restart fixed".format()  )



			if restartBLEifNoConnect and (tt - lastSignal > (2*3600+ 600*restartCount)) :
				U.logger.log(20, "requested a restart of BLE stack due to no signal for {:.0f} seconds".format(tt-lastSignal))
				subprocess.call("echo xx > {}temp/BLErestart".format(G.homeDir), shell=True) # signal that we need to restart BLE
				lastSignal = time.time() +30
				restartCount +=1

			#checkSwitchbotForCommand()

			if time.time() - tlastQuick > 1: 
				#U.logger.log(20, "loop time:{}".format(time.time()) )
				tlastQuick = time.time()

				for thisMAC in macList:
					#U.logger.log(20, "testing mac {}, type:{}".format(thisMAC, macList[thisMAC]["type"]) )

					if macList[thisMAC]["type"] == "isBLEconnect":
						tryToConnectToBLEconnect(thisMAC, BLEid)
						#checkSwitchbotForCommand()

					if macList[thisMAC]["type"] == "isBLElongConnectDevice":
						tryToConnectToSensorDevice(thisMAC)
						#checkSwitchbotForCommand()

			loopCount+=1
			time.sleep(0.1)
			#print "no answer sleep for " + str(iPhoneRefreshDownSecs)
			U.echoLastAlive(G.program)


####### start here #######
execBLEconnect()
		
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
		
sys.exit(0)		   
