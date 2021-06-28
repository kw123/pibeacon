#!/usr/bin/env python
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


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "BLEconnect"
version = 6.3
ansi_escape =re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')


#################################
def signedIntfrom16(string):
	try:
		intNumber = int(string,16)
		if intNumber > 32767: intNumber -= 65536
	except	Exception, e:
		U.logger.log(20, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 




#################################
def startHCI():
	global BLEconnectMode
	global macList
	global oneisBLElongConnectDevice
	global useHCI
	## give other ble functions time to finish

	doNotUseHCI = ""
	BusUsedByBeaconloop = ""
	if oneisBLElongConnectDevice:
		for ii in range(3):
			time.sleep(ii)
			hciBeaconloopUsed, raw  = U.readJson("{}temp/beaconloop.hci".format(G.homeDir))
			if raw != "": 
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
	#U.logger.log(20, "BLE(long)connect--HCIs:  {}".format(HCIs))
	if HCIs["hci"] != {}:
		if len(HCIs["hci"]) < 2 and oneisBLElongConnectDevice:
			text = "BLE(long)connect: only one BLE dongle, need 2 to run, will restart BLE stack (hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -) and try again,, HCI inf:\n{}".format(HCIs)
			U.logger.log(20, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			cmd = "timeout 5 sudo hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -"
			ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			U.logger.log(20, "cmd: {} and ret:".format(cmd, ret))

			cmd = "timeout 20 sudo hciattach /dev/ttyAMA0 bcm43xx 921600 noflow -"
			ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			U.logger.log(20, "cmd: {} and ret:".format(cmd, ret))
			time.sleep(5)
			exit()

		U.logger.log(20, "BLE(long)connect: BLEconnectUseHCINo-bus: {}; default:{}, HCIUsedByBeaconloop:{}; BusUsedByBeaconloop:{}".format(G.BLEconnectUseHCINo, "USB", doNotUseHCI, BusUsedByBeaconloop))
		useHCI,  myBLEmac, BLEid, bus = U.selectHCI(HCIs["hci"], G.BLEconnectUseHCINo, "USB", doNotUseHCI=doNotUseHCI)
		if BLEid >= 0:
			U.logger.log(20, "BLE(long)connect: using mac:{};  useHCI: {}; bus: {}; mode: {} searching for MACs:\n{}".format(myBLEmac, useHCI, HCIs["hci"][useHCI]["bus"], BLEconnectMode , macList))
			return 	useHCI,  myBLEmac, BLEid, bus 

		else:
			text = "BLEconnect: BLE STACK is not UP HCI-info:\n{}".format(HCIs)
			U.logger.log(20, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			time.sleep(25)
			exit()
	else:
			text = "BLEconnect: BLE STACK HCI is empty HCI:{}".format(HCIs)
			U.logger.log(20, text)
			U.sendURL( data={"data":{"error":text}}, squeeze=False, wait=True )
			time.sleep(25)
			exit()
	exit()



#################################
def escape_ansi(line):
	return ansi_escape.sub('', line).encode('ascii',errors='ignore')



#################################
def batLevelTempCorrection(batteryVoltage, temp, batteryVoltAt100=3000., batteryVoltAt0=2700.):
	try:
		batteryLowVsTemp			= (1. + 0.7*min(0.,temp-10.)/100.) * batteryVoltAt0 # (changes to 0.9* 2700 @ 0C; to = 0.8*2700 @-10C )
		batteryLevel 				= int(min(100.,max(0.,100.* (batteryVoltage - batteryLowVsTemp)/(batteryVoltAt100-batteryLowVsTemp))))
		return batteryLevel
	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 0




#################################
def connectGATT(useHCI, thisMAC, timeoutGattool, timeoutConnect, repeat=1, verbose = False):
	global switchBotConfig, switchbugActive, switchBotPresent

	try:
		nTries = 1
		for kk in range(nTries):
			if switchBotPresent and switchbugActive == "delayed" and checkSwitchbot(): return ""
			cmd = "sudo /usr/bin/gatttool -i {} -b {} -I".format(useHCI,  thisMAC) 
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
					if switchBotPresent and switchbugActive == "delayed" and checkSwitchbot(): return ""
					if verbose: U.logger.log(20,"send connect try#:{}  expecting: Connection successful ".format(ii))
					expCommands.sendline("connect")
					ret = expCommands.expect(["Connection successful","Error", pexpect.TIMEOUT], timeout=timeoutConnect)
					if ret == 0:
						if verbose: U.logger.log(20,"connect successful: {}-==-:{}".format(escape_ansi(expCommands.before),escape_ansi(expCommands.after)))
						#ret = expCommands.expect(".*", timeout=0.5)
						#U.logger.log(20,"... .*: {}-==-:{}".format(expCommands.before,expCommands.after))
						return expCommands
					else:
						if verbose: U.logger.log(20, u"connect error: waiting 1 sec;  .. {}-==-:{}".format(escape_ansi(expCommands.before),escape_ansi(expCommands.after)))
						time.sleep(1)
				except Exception, e:
					U.logger.log(20, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


			#U.logger.log(20, u"connect error giving up")

		if expCommands != "": disconnectGattcmd(expCommands, thisMAC, 2)

		return ""
	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return ""



#################################
def disconnectGattcmd(expCommands, thisMAC, timeout, verbose=False):	
	global switchBotConfig, switchbugActive, switchBotPresent
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
	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return False



#################################
def writeGattcmd(expCommands, cc, expectedTag, timeout, verbose=False):	
	global switchBotConfig, switchbugActive, switchBotPresent
	try:		
		for ii in range(3):
			if switchBotPresent and switchbugActive  == "delayed":  return False
			if switchBotPresent and checkSwitchbot(): return False

			if verbose: U.logger.log(20,"sending cmd:{}, expecting:'{}'".format(cc, expectedTag.encode('ascii',errors='ignore')))
			expCommands.sendline( cc )
			ret = expCommands.expect([expectedTag,"Error","failed",pexpect.TIMEOUT], timeout=5)
			if ret == 0:
				if verbose: U.logger.log(20,"... successful: BF:{}-- AF:{}--".format(escape_ansi(expCommands.before), escape_ansi(expCommands.after)))
				return True
			else: 
				#U.logger.log(20, u"... error, quit: {}-{}".format(expCommands.before, expCommands.after))
				continue
			ret = expCommands.expect("\n")

	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return False



#################################
def writeAndListenGattcmd(expCommands, cc, expectedTag, nBytes, timeout, verbose=False):
	global switchBotPresent, switchbugActive
	try:
		for kk in range(2):
			if switchBotPresent and checkSwitchbot(): return []
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
	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return []



#################################
def readGattcmd(expCommands, cc, expectedTag, nBytes, timeout, verbose=False):
	global switchBotConfig, switchbugActive, switchBotPresent
	try:
		for kk in range(2):
			if switchBotPresent and switchbugActive == "delayed": return []
			if switchBotPresent and checkSwitchbot(): return []
			if verbose: U.logger.log(20,"sendline  cmd:{}, expecting:'{}'".format(cc, expectedTag))
			expCommands.sendline( cc )
			ret = expCommands.expect([expectedTag,"Error","failed",pexpect.TIMEOUT], timeout=timeout)
			if ret == 0:
				if verbose: U.logger.log(20,"... successful:  BF:{}-- AF:{}--".format(escape_ansi(expCommands.before),escape_ansi(expCommands.after)))
				ret = expCommands.expect("\n")
				xx = (expCommands.before.replace("\r","").strip()).split() 
				if len(xx) == nBytes:
					return xx
				else:
					if verbose: U.logger.log(20,"... error: len != {}".format(nBytes))
					continue
			else:
				if verbose: U.logger.log(20,"... error: {}-{}".format(escape_ansi(expCommands.before),escape_ansi(expCommands.after)))
				continue
	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return []



#################################
def batchGattcmd(useHCI, thisMAC, cc, expectedTag, nBytes=0, repeat=3, verbose=False, timeout=6):
	global switchBotConfig, switchbugActive, switchBotPresent
	try:
		cmd = "/usr/bin/timeout -s SIGKILL {} /usr/bin/gatttool -i {} -b {} {}".format(timeout, useHCI,  thisMAC, cc) 
		if verbose: U.logger.log(20,"cmd:{} ;  expecting: '{}'; nbytes:{}, repeat:{}, switchBotPresent:{}; switchbugActive:{}; timeout:{}".format(cmd, expectedTag, nBytes, repeat, switchBotPresent, switchbugActive, timeout))
		for kk in range(repeat):
			if verbose: U.logger.log(20,"try#:{}, switchBotPresent:{}; switchbugActive:{} ".format(kk, switchBotPresent, switchbugActive))
			if switchBotPresent and switchbugActive == "delayed": return []
			ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			if ret[0].find(expectedTag) > -1:
				if verbose: U.logger.log(20,"... successful:  0:{}".format( escape_ansi(ret[0]) ))
				xx = ret[0].replace("\r","").strip()
				if nBytes == 0: return xx
				xx = ret[0].split(expectedTag)[1].replace("\r","").strip().split() 
				if len(xx) == nBytes or nBytes < 0:
					return xx
				else:
					if verbose: U.logger.log(20,"... error: len:{} != {}".format(len(xx), nBytes))
					continue
			else:
				if verbose: U.logger.log(20,"... error: {}".format( ret[1].strip() ))
			time.sleep(0.5)

	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return []



#################################
def tryToConnectSocket(thisMAC,BLEtimeout,devId):
	global errCount, lastConnect

	if time.time() - lastConnect < 3: time.sleep( max(0,min(0.5,(3.0- (time.time() - lastConnect) ))) )

	retdata	 = {"rssi": -999, "txPower": -999,"flag0ok":0,"byte2":0}
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
			errCount += 1
			if errCount  < 10: return {}
			subprocess.call("rm {}temp/stopBLE > /dev/null 2>&1".format(G.homeDir), shell=True)
			U.logger.log(20, u"in Line {} has error ... sock.recv error, likely time out ".format(sys.exc_traceback.tb_lineno))
			U.restartMyself(reason="sock.recv error", delay = 10)

	except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	U.logger.log(10, "{}:  {}".format(thisMAC, retdata))
	errCount = 0
	return retdata



#################################
def tryToConnectCommandLine(thisMAC, BLEtimeout):
	global errCount, lastConnect, useHCI

	try:
		if time.time() - lastConnect < 3: 
			time.sleep( max(0,min(0.5,(3.0- (time.time() - lastConnect) ))) )

		retdata	 = {"rssi": -999, "txPower": -999,"flag0ok":0,"byte2":0}
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
			#U.logger.log(20, "{}  1. try ret: {} --- err>>{}<<".format(thisMAC, ret[0].strip("\n"), ret[1].strip("\n")))

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

	except  Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return {}
	
	#U.logger.log(20, "{} return data: {}".format(thisMAC, retdata))
	return retdata



#################################
def BLEXiaomiMiTempHumSquare(thisMAC, data0):
	global errCount, macList, maxTrieslongConnect, useHCI
	global switchBotConfig, switchbugActive, switchBotPresent

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
				return data

			readData = []

			for nn in range(2):
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
				return data

			macList[thisMAC]["triesWOdata"] += 1

		data["triesWOdata"] = macList[thisMAC]["triesWOdata"]
		if macList[thisMAC]["triesWOdata"] >= maxTrieslongConnect:
			macList[thisMAC]["triesWOdata"] = 0
			#U.logger.log(20, u"error, connected but no data, triesWOdata:{} repeast in {} secs".format(macList[thisMAC]["triesWOdata"], minWaitAfterBadRead))
			return data

	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		data["badSensor"] = True
		return data
	
	#U.logger.log(20, "{} return data: {}".format(thisMAC, data))
	
	return data



#################################
def BLEXiaomiMiVegTrug(thisMAC, data0):
	global errCount, macList, maxTrieslongConnect, useHCI
	global switchBotConfig, switchbugActive, switchBotPresent

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
		#   0-1: temp *10 [°C]
		#     2: ??
		#   3-6: bright [lux]
		#     7: moist [%]
		#   8-9: conduct [µS/cm]
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
		return data


	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		data["badSensor"] = True
	
	if verbose: U.logger.log(20, "{} return data: {}".format(thisMAC, data))
	
	return data



#################################
def BLEinkBirdPool01B(thisMAC, data0):
	global errCount, macList, maxTrieslongConnect, useHCI
	global switchBotConfig, switchbugActive, switchBotPresent

	data = copy.deepcopy(data0)
	verbose = False
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
		return data

	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		data["badSensor"] = True
	
	if verbose: U.logger.log(20, "{}  return 99 data: {}".format(thisMAC, data))
	
	return data




def checkSwitchbot():
	global switchbugActive, switchBotPresent, oldSwitchbotCommand

	switchbugActive = ""
	if not switchBotPresent: return False

	jData = U.checkForNewCommand("switchbot.cmd")
	
	if len(jData) == 0 and len(oldSwitchbotCommand) == 0: return False

	# we have something
	if len(jData) == 0: jData = copy.copy(oldSwitchbotCommand)
	else:				oldSwitchbotCommand = copy.copy(jData)
	return getSwitchBot(jData)


#################################
def getSwitchBot(jData):
	global useHCI
	global switchBotConfig, switchbugActive, oldSwitchbotCommand

	switchbugActive = "started"
	verbose = False
	# jData= {"mac":mac#,"onOff":"0/1","statusRequest":True}
	#U.logger.log(20, u"jData:{}".format(jData))
	try:
		"""
		# read: 
		gatttool -b F9:A6:49:9A:DF:85 -t random --char-write-req  --handle=0x0016 --value=570102 / 1
		"""
		if "mac"   not in jData: 
			switchbugActive = ""
			return False

		thisMAC = jData["mac"]
		if switchBotConfig[thisMAC]["lastFailedTryCount"] > 1 and time.time() - switchBotConfig[thisMAC]["lastFailedTryTime"] < 30:
			#if verbose: U.logger.log(20, "skip next test dt:{}".format(time.time() - switchBotConfig[thisMAC]["lastFailedTryTime"]))
			switchbugActive = "waiting"
			return False
		#if verbose: U.logger.log(20, "not skiped next test dt:{}".format(time.time() - switchBotConfig[thisMAC]["lastFailedTryTime"]))

		if time.time() - switchBotConfig[thisMAC]["lastFailedTryTime"] > 35:
			switchBotConfig[thisMAC]["lastFailedTryTime"] = time.time()
			switchBotConfig[thisMAC]["lastFailedTryCount"] = 0
		switchBotConfig[thisMAC]["lastFailedTryCount"] += 1

		if "onOff" in jData: 
			if str(jData["onOff"]) == "1":  onOff =  switchBotConfig[thisMAC]["onCmd"];  actualStatus = "on"
			else:  							onOff =  switchBotConfig[thisMAC]["offCmd"]; actualStatus = "off"

			result = batchGattcmd(useHCI, thisMAC, "--char-write-req -t random --handle=0x{} --value={}".format(switchBotConfig[thisMAC]["blehandle"], onOff ), "successfully", nBytes=0, repeat=3, verbose=verbose, timeout=2)


			if result != []:
				retData = {"outputs":{"OUTPUTswitchbotRelay":{switchBotConfig[thisMAC]["devId"]:{"actualStatus": actualStatus}}}}
				if verbose: U.logger.log(20, "{} return ok data: {}, retData:{}".format(thisMAC, result, retData))
				U.sendURL(retData)
				oldSwitchbotCommand = {}
				switchbugActive = "finished"
				switchBotConfig[thisMAC]["lastFailedTryCount"] = 0 
				switchBotConfig[thisMAC]["lastFailedTryTime"] = 0 
				return True

			##jData["statusRequest"] = True

		if "statusRequest" in jData: 
			result = batchGattcmd(useHCI, thisMAC, "--char-read -t random --handle=0x{}".format(switchBotConfig[thisMAC]["blehandle"] ), "descriptor:", nBytes=0, repeat=3, verbose=verbose, timeout=2)
			if result != []:
				cmdOn  = switchBotConfig[thisMAC]["onCmd"].replace(" ","")[-4:]
				cmdOff = switchBotConfig[thisMAC]["offCmd"].replace(" ","")[-4:]
				result = result.split("descriptor: ")[1].strip().replace(" ","")[-4:]
				if   result == cmdOn:	actualStatus = "on"
				elif result == cmdOff:	actualStatus = "off"
				else: 					actualStatus = "unknown"

				retData = {"outputs":{"OUTPUTswitchbotRelay":{switchBotConfig[thisMAC]["devId"]:{"actualStatus": actualStatus}}}}
				#if verbose: U.logger.log(20, "{} return ok;  result: {}, retData:{}, cmdOn:{}; cmdOff:{}".format(thisMAC, result, retData, cmdOn, cmdOff))
				U.sendURL(retData)
				oldSwitchbotCommand = {}
				switchbugActive = "finished"
				switchBotConfig[thisMAC]["lastFailedTryTime"] = 0 
				switchBotConfig[thisMAC]["lastFailedTryCount"] = 0 
				return True

	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	
		if verbose: U.logger.log(20, "{}  return  data: {}".format(thisMAC, switchBotConfig))
	
	switchbugActive = "delayed"
	return False 



##################################
def readParams():
		global debug, ipOfServer,myPiNumber,passwordOfServer, userIdOfServer, authentication,ipOfServer,portOfServer,sensorList,restartBLEifNoConnect
		global macList 
		global oldRaw, lastRead, BLEconnectMode
		global sensor
		global oneisBLElongConnectDevice
		global switchBotConfig, switchbugActive, switchBotPresent

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return False
		if lastRead2 == lastRead: return False
		lastRead  = lastRead2
		if inpRaw == oldRaw: return False
		oldRaw	   = inpRaw

		oldSensor		  = sensorList

		try:

			U.getGlobalParams(inp)
			sensors = {}
			output = {}
			switchbugActive = ""
			switchBotPresent = False

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



			if "output" in inp:	
				if "OUTPUTswitchbotRelay" in inp["output"]: 
					output["switchbot"] = copy.deepcopy(inp["output"]["OUTPUTswitchbotRelay"])


			if sensors == {} and  output == {} :
				U.logger.log(30, u" no {} definitions supplied in sensorList / oputputs;  stopping (1)".format(sensor))
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
			if "isBLElongConnectDevice" in sensors:
				CCC = sensors["isBLElongConnectDevice"]
				for ss in CCC: 	
					#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"CCC:{} ".format(CCC))
					for devId in CCC[ss]:
						#if ss == "BLEdirectMiTempHumSquare":	U.logger.log(30, u"devId:{} ".format(devId))
						if "mac" in CCC[ss][devId]:
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
					if ss =="BLEdirectMiTempHumSquare":	U.logger.log(30, u"macListNew:{} ".format(macListNew))




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


			if output != {}:
				for devId in output["switchbot"]:
					thisMAC = output["switchbot"][devId]["mac"]
					switchBotConfig[thisMAC] = {
										"type":			"switchbot",
										 "blehandle":	output["switchbot"][devId]["blehandle"],
										 "onCmd": 		output["switchbot"][devId]["onCmd"],
										 "offCmd":		output["switchbot"][devId]["offCmd"],
										 "lastFailedTryTime":0,
										 "lastFailedTryCount":0,
										 "devId": 		devId }
					switchBotPresent = True



			if len(macList) == 0:
				U.logger.log(30, u"no BLEconnect - BLElongConnect devices supplied in parameters (2)")
				exit()

			#U.logger.log(30, u"BLEconnect - chechink devices (2):{}".format(macList))
			return True
			
		except	Exception, e:
			U.logger.log(50,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
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

	except	Exception, e:
		U.logger.log(30,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
			
	except  Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30, u"thisMAC:{}, data:{}".format(thisMAC, data))
	return 



####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
def execBLEconnect():
	global sensorList,restartBLEifNoConnect
	global macList,oldParams
	global oldRaw,	lastRead
	global errCount, lastConnect
	global BLEconnectMode
	global sensor
	global oneisBLElongConnectDevice
	global maxTrieslongConnect
	global useHCI
	global lastSignal
	global restartCount
	global nowTest, nowP
	global switchBotConfig, switchbugActive, switchBotPresent, oldSwitchbotCommand

	oldSwitchbotCommand		= {}
	switchbugActive			= ""
	switchBotPresent		= False
	switchBotConfig			= {}
	lastConnect 			= time.time()
	maxTrieslongConnect 	= 4
	oneisBLElongConnectDevice = False
	BLEconnectMode			= "commandLine" # socket or commandLine
	oldRaw					= ""
	lastRead				= 0
	errCount				= 0
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

	myPID			= str(os.getpid())
	U.setLogging()
	U.killOldPgm(myPID,G.program+".py")# kill  old instances of myself if they are still running

	loopCount		  = 0
	sensorRefreshSecs = 90
	U.logger.log(30, "======== starting BLEconnect program v:{} ".format(version))
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
	lastMsg				={}
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

	tlastQuick = time.time()

	while True:

			tt = time.time()
			if tt - lastRead > 4 :
				newParameterFile = readParams()
				eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
				lastRead=tt

			if restartBLEifNoConnect and (tt - lastSignal > (2*3600+ 600*restartCount)) :
				U.logger.log(30, "requested a restart of BLE stack due to no signal for {:.0f} seconds".format(tt-lastSignal))
				subprocess.call("echo xx > {}temp/BLErestart".format(G.homeDir), shell=True) # signal that we need to restart BLE
				lastSignal = time.time() +30
				restartCount +=1

			checkSwitchbot()

			if time.time() - tlastQuick > 1: 
				tlastQuick = time.time()
				checkIFQuickRequested()

				for thisMAC in macList:
					checkSwitchbot()
					#U.logger.log(20, "testing mac {}, type:{}".format(thisMAC, macList[thisMAC]["type"]) )

					if macList[thisMAC]["type"] == "isBLEconnect":
						tryToConnectToBLEconnect(thisMAC, BLEid)

					if macList[thisMAC]["type"] == "isBLElongConnectDevice":
						tryToConnectToSensorDevice(thisMAC)

			loopCount+=1
			time.sleep(0.1)
			#print "no answer sleep for " + str(iPhoneRefreshDownSecs)
			U.echoLastAlive(G.program)


####### start here #######
execBLEconnect()
		
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
		
sys.exit(0)		   
