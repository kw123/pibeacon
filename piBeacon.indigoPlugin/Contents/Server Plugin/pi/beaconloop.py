#!/usr/bin/env python
# -*- coding: utf-8 -*-
# test BLE Scanning software
# jcs 6/8/2014
#  adopted by Karl Wachs Nov27	2015
# version 1.1  Dec 24
# v 2	 feb 5 2016


import sys, os, subprocess
import time,datetime
import struct
import bluetooth._bluetooth as bluez
import json

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


def returnnumberpacket(pkt):
	myInteger = 0
	multiple = 256
	for c in pkt:
		myInteger +=  struct.unpack("B",c)[0] * multiple
		multiple = 1
	return myInteger 

def returnstringpacket(pkt):
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
	global myBLEmac
	useHCI	 = ""
	myBLEmac = ""
	devId	 = 0
	## good explanation: http://gaiger-G.programming.blogspot.com/2015/01/bluetooth-low-energy.html
	U.toLog(-1,"(re)starting bluetooth")
	try:
		ret = subprocess.Popen("hciconfig hci0 down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # disenable bluetooth
		ret = subprocess.Popen("hciconfig hci1 down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # disenable bluetooth
		time.sleep(0.1)
		ret = subprocess.Popen("hciconfig hci0 down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # disenable bluetooth
		ret = subprocess.Popen("hciconfig hci1 down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # disenable bluetooth
		time.sleep(0.1)
		ret = subprocess.Popen("hciconfig hci0 up ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()	 # enable bluetooth
		ret = subprocess.Popen("hciconfig hci1 up ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()	 # enable bluetooth

		#### selct the proper hci bus: if just one take that one, if 2, use bus="uart", if no uart use hci0
		HCIs = U.whichHCI()
		useHCI,  myBLEmac, devId = U.selectHCI(HCIs, G.BeaconUseHCINo,"UART")
		if myBLEmac ==  -1:
			return 0,  0, -1
		U.toLog(-1,"Beacon Use HCINo " +unicode(G.BeaconUseHCINo)+";  useHCI:" +unicode(useHCI)+ ";  myBLEmac:"+unicode(myBLEmac)+"; devId:" +unicode(devId), doPrint = True )
			

		#ret = subprocess.Popen("hciconfig hci0 leadv 3",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate() # enable ibeacon signals, next is the ibeacon message
		OGF					= " 0x08"
		OCF					= " 0x0008"
		iBeaconPrefix		= " 1E 02 01 1A 1A FF 4C 00 02 15"
		uuid				= " 2f 23 44 54 cf 6d 4a 0f ad f2 f4 91 1b a9 ff a6"
		MAJ					= " 00 09"
		MIN					= " 00 "+"0%x"%(int(pi))
		txP					= " C5 00"
		cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + OCF + iBeaconPrefix + uuid + MAJ + MIN + txP
		U.toLog(-1,cmd, doPrint =True) 
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		####################################set adv params		minInt	 maxInt		  nonconectable	 +??  <== THIS rpi to send beacons every 10 secs only 
		#											   00 40=	0x4000* 0.625 msec = 16*4*256 = 10 secs	 bytes are reverse !! 
		#											   00 10=	0x1000* 0.625 msec = 16*1*256 = 2.5 secs
		#											   00 04=	0x0400* 0.625 msec =	4*256 = 0.625 secs
		cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + " 0x0006"	  + " 00 10"+ " 00 20" +  " 03"			   +   " 00 00 00 00 00 00 00 00 07 00"
		## maxInt= A0 00 ==	 100ms;	 40 06 == 1000ms; =0 19 = 4 =seconds  (0x30x00	==> 64*256*0.625 ms = 10.024secs  use little endian )
		U.toLog(-1,cmd, doPrint =True) 
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		####################################LE Set Advertise Enable
		cmd	 = "hcitool -i "+useHCI+" cmd" + OGF + " 0x000a" + " 01"
		U.toLog(-1,cmd, doPrint =True) 
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		ret = subprocess.Popen("hciconfig ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if ret[1] != "": U.toLog(-1,"BLE start returned:\n{}error:>>{}<<".format(ret[0],ret[1]), doPrint=True )
		else:			 U.toLog(-1,"BLE start returned:\n{}".format(ret[0]), doPrint=True )
	except Exception, e: 
		U.toLog(-1,u"exit at restart BLE stack error  in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e), permanentLog=True, doPrint =True)
		time.sleep(10)
		f = open(G.homeDir+"temp/restartNeeded","w")
		f.write("bluetooth_startup.ERROR:"+unicode(e))
		f.close()
		subprocess.Popen("hciconfig "+useHCI+" down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # enable bluetooth
		subprocess.Popen("service bluetooth restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("service dbus restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		return 0, "", -5

	U.toLog(-1,"my BLE mac# is : "+ unicode(myBLEmac))
	if myBLEmac !="":
		f=open(G.homeDir+"myBLEmac","w")
		f.write(myBLEmac)
		f.close()

	try:
		sock = bluez.hci_open_dev(devId)
		U.toLog(-1, "ble thread started")
	except	Exception, e:
		U.toLog(-1,"error accessing bluetooth device..."+unicode(e),permanentLog=True)
		f = open(G.homeDir+"temp/rebootNeeded","w")
		f.write("bluetooth_startup.ERROR:"+unicode(e))
		f.close()
		subprocess.Popen("hciconfig "+useHCI+" down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # enable bluetooth
		subprocess.Popen("service bluetooth restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("service dbus restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		return 0,  "", -1
		
	try:
		hci_le_set_scan_parameters(sock)
		hci_enable_le_scan(sock)
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),permanentLog=True)
		if unicode(e).find("Bad file descriptor") >-1:
			f = open(G.homeDir+"temp/rebootNeeded","w")
			f.write("bluetooth_startup.ERROR:Bad_file_descriptor...SSD.damaged?")
			f.close()
		if unicode(e).find("Network is down") >-1:
			f = open(G.homeDir+"temp/rebootNeeded","w")
			f.write("bluetooth_startup.ERROR:Network_is_down...need_to_reboot")
			f.close()
		subprocess.Popen("hciconfig "+useHCI+" down ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  # enable bluetooth
		subprocess.Popen("service bluetooth restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("service dbus restart ",shell=True ,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		return 0, "", -1 
	return sock, myBLEmac, 0




	
#################################
def toReject(text):
	try:
		f=open(G.homeDir+"temp/rejects","a")
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
		fg=open(G.homeDir+"beacon_ExistingHistory","r")
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
		fg=open(G.homeDir+"beacon_ExistingHistory","w")
		fg.write(json.dumps(beacon_ExistingHistory))
		fg.close()
	except	Exception, e:
		if unicode(e).find("Read-only file system:") >-1:
			os.system("sudo reboot")
#################################
def fixOldNames():

	if os.path.isfile(G.homeDir+"beaconsExistingHistory"):
		os.system("sudo mv "+G.homeDir+"beaconsExistingHistory " + G.homeDir+"beacon_ExistingHistory")


#################################
def handleHistory():
	global	beacon_ExistingHistory, deleteHistoryAfterSeconds

	delHist=[]		  
	for beaconMAC in beacon_ExistingHistory:
		if beacon_ExistingHistory[beaconMAC]["lCount"] < 0: beacon_ExistingHistory[beaconMAC]["lCount"] =10
		beacon_ExistingHistory[beaconMAC]["lCount"] -=1
		beacon_ExistingHistory[beaconMAC]["reason"] =0
		if time.time() - beacon_ExistingHistory[beaconMAC]["timeSt"] > deleteHistoryAfterSeconds : # delete history if older than 2 days with no message
			delHist.append(beaconMAC)
				
	# delete old data if older than 2 days		  
	for beaconMAC in delHist:
		del beacon_ExistingHistory[beaconMAC]

	# save history to file
	writebeacon_ExistingHistory() 



def readParams(init):
	global	 collectMsgs, sendAfterSeconds, loopMaxCallBLE,	 ignoreUUID,UUIDtoIphoneReverse,  beacon_ExistingHistory, deleteHistoryAfterSeconds,ignoreMAC,signalDelta,UUIDtoIphone,offsetUUID,fastDown,maxParseSec,batteryLevelPosition,doNotIgnore
	global acceptNewiBeacons,onlyTheseMAC,enableiBeacons, sendFullUUID,BLEsensorMACs, minSignalCutoff, acceptJunkBeacons
	global oldRaw,	lastRead
	if init:
		G.debug			  = 2
		collectMsgs		= 10  # in parse loop collect how many messages max	  ========	all max are an "OR" : if one hits it stops
		sendAfterSeconds= 60  # collect for xx seconds then send msg
		loopMaxCallBLE	= 900 # max loop count	in main pgm to collect msgs
		maxParseSec		= 2	  # stop aprse loop after xx seconds 
		portOfServer	="8176"
		G.ipOfServer	  =""
		G.passwordOfServer=""
		G.userIdOfServer  =""
		G.myPiNumber	  ="0"
		deleteHistoryAfterSeconds  =72000

	inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
	if inp == "":				return False
	if lastRead2 == lastRead:	return False
	lastRead   = lastRead2
	if inpRaw == oldRaw:		return False
	oldRaw	   = inpRaw

	try:
		if "enableiBeacons"		in inp:	 enableiBeacons=	   (inp["enableiBeacons"])
		if enableiBeacons == "0":
			U.toLog(-1," termination ibeacon scanning due to parameter file",permanentLog=True)
			time.sleep(0.5)
			sys.exit(3)
		U.getGlobalParams(inp)

		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPIBEACON"])
		if "rebootSeconds"		in inp:	 rebootSeconds=		  int(inp["rebootSeconds"])
		if "enableRebootCheck"	in inp:	 enableRebootCheck=		 (inp["enableRebootCheck"])
		if "sendAfterSeconds"	in inp:	 sendAfterSeconds=	  int(inp["sendAfterSeconds"])
		if "acceptNewiBeacons"	in inp:	 acceptNewiBeacons=	  int(inp["acceptNewiBeacons"])
		if "sendFullUUID"		in inp:	 sendFullUUID=			 (inp["sendFullUUID"]=="1" )
		if "acceptJunkBeacons"	in inp:	 acceptJunkBeacons=		 (inp["acceptJunkBeacons"]=="1" )


		if "deleteHistoryAfterSeconds"	in inp:
								  deleteHistoryAfterSeconds=  int(inp["deleteHistoryAfterSeconds"])
		BLEsensorMACs = {}
		sensor		  = "BLEsensor"
		if "sensors"			 in inp: 
			sensors =				 (inp["sensors"])
			if sensor in sensors:
				for devId in sensors[sensor]:
					sensD	= sensors[sensor][devId]
					mac		= sensD["mac"]
					BLEsensorMACs[mac]={}
					BLEsensorMACs[mac]["type"]				   = sensD["type"]
					BLEsensorMACs[mac]["devId"]				   = devId
					try:	BLEsensorMACs[mac]["offsetTemp"]   = float(sensD["offsetTemp"])
					except: BLEsensorMACs[mac]["offsetTemp"]	= 0.
					try:	BLEsensorMACs[mac]["multiplyTemp"] = float(sensD["multiplyTemp"])
					except: BLEsensorMACs[mac]["multiplyTemp"] = 1.
					try:	BLEsensorMACs[mac]["updateIndigoTiming"] = float(sensD["updateIndigoTiming"])
					except: BLEsensorMACs[mac]["updateIndigoTiming"] = 0.
					BLEsensorMACs[mac]["lastUpdate"]				 = -1
					##print BLEsensorMACs

	except	Exception, e:
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



	try:
		f=open(G.homeDir+"temp/beacon_parameters","r")
		InParams=json.loads(f.read().strip("\n"))
		f.close()
	except:
		InParams={}

	try:		 onlyTheseMAC=InParams["onlyTheseMAC"]
	except:		 onlyTheseMAC=[]

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


		
	U.toLog(1,"fastDown:			" +unicode(fastDown))
	U.toLog(1,"signalDelta:			" +unicode(signalDelta))
	U.toLog(1,"ignoreUUID:			" +unicode(ignoreUUID))
	U.toLog(1,"ignoreMAC:			" +unicode(ignoreMAC))
	U.toLog(1,"UUIDtoIphone:		" +unicode(UUIDtoIphone))
	U.toLog(1,"UUIDtoIphoneReverse: " +unicode(UUIDtoIphoneReverse))
	return	True


def composeMSGSensor(data):

		U.sendURL({"sensors":data})
		
		
	
#################################
def composeMSG(beaconsNew,timeAtLoopStart,reason):
	global	 collectMsgs, sendAfterSeconds, loopMaxCallBLE,	 ignoreUUID,  beacon_ExistingHistory, deleteHistoryAfterSeconds
	global myBLEmac, sendFullUUID
	try:
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
					data.append([str(beaconMAC),beacon_ExistingHistory[beaconMAC]["reason"],uuid,aveSignal,avePower,beaconsNew[beaconMAC]["count"],beaconsNew[beaconMAC]["bLevel"],beaconsNew[beaconMAC]["pkLen"]])
					beacon_ExistingHistory[beaconMAC]["rssi"]=beaconsNew[beaconMAC]["rssi"]/max(beaconsNew[beaconMAC]["count"],1.) # average last rssi
			except	Exception, e:
				U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				U.toLog(-1, " error composing msg \n"+unicode(beaconsNew[beaconMAC]))

		secsCollected=int(time.time()-timeAtLoopStart)
##		  if unicode(data).find("0C:F3:EE:00:66:15") > -1:	 print data

		data ={"msgs":data,"pi":str(G.myPiNumber),"mac":myBLEmac,"secsCol":secsCollected,"reason":reason}
		U.sendURL(data)
	except	Exception, e:
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))





#################################
def checkIfNewOrDeltaSignalOrWasMissing(reason,beaconMAC,beaconMSG,msgCount):
	global	 collectMsgs, sendAfterSeconds, loopMaxCallBLE, ignoreUUID,	 beacon_ExistingHistory, deleteHistoryAfterSeconds,signalDelta,fastDown, minSignalCutoff
 
	t=time.time()
	try:
		if beaconMAC not in beacon_ExistingHistory: # is it new?
			if beaconMAC in minSignalCutoff:
				if	float(beaconMSG[2]) < minSignalCutoff[beaconMAC]:
					#print "rejecting: ", beaconMAC, minSignalCutoff[beaconMAC] ,  float(beaconMSG[2])
					return reason
				else:
					#print "accepting: ", beaconMAC, minSignalCutoff[beaconMAC] ,  float(beaconMSG[2])
					pass
					
			reason=2 
			beacon_ExistingHistory[beaconMAC]={"uuid":beaconMSG[1],"lCount":1,"txPower":float(beaconMSG[3]),"rssi":float(beaconMSG[2]),"reason":reason,"timeSt":t}
			
		elif beaconMAC in minSignalCutoff and float(beaconMSG[2]) < minSignalCutoff[beaconMAC]:# 
			if float(beaconMSG[2]) < minSignalCutoff[beaconMAC]: 
				#print "rejecting: existing", beaconMAC, minSignalCutoff[beaconMAC] ,  float(beaconMSG[2])
				return reason
	 
		elif beacon_ExistingHistory[beaconMAC]["rssi"] ==-999: # in fast down mode, was down for some time
			reason=4 
			#print " rssi=-999 "+ beaconMAC +"; dT: "+unicode(t-beacon_ExistingHistory[beaconMAC]["timeSt"])+"sec; rssi= "+beaconMSG[2] +"; ex history: "+unicode(beacon_ExistingHistory[beaconMAC])+"; fd: "+ unicode(fastDown)+"; t:"+unicode(t) 
			beacon_ExistingHistory[beaconMAC]={"uuid":beaconMSG[1],"lCount":1,"txPower":float(beaconMSG[3]),"rssi":float(beaconMSG[2]),"reason":reason,"timeSt":t}
	 

 
		elif (t - beacon_ExistingHistory[beaconMAC]["timeSt"])	> 1.3*sendAfterSeconds: # not new but have not heard for > 1+1/3 periods
			reason=5
			beacon_ExistingHistory[beaconMAC]["reason"]=reason
			#print	"curl: first msg after	collect time "+ beaconMAC +" "+unicode(beacon_ExistingHistory[beaconMAC])

		elif beaconMAC in signalDelta: 
			if beacon_ExistingHistory[beaconMAC]["rssi"] !=-999. and float(beaconMSG[2]) !=0:
				if abs(beacon_ExistingHistory[beaconMAC]["rssi"]-float(beaconMSG[2])) >	 signalDelta[beaconMAC] :	# delta signal > xxdBm (set param)
					#print beaconMAC, "signalDelta",beacon_ExistingHistory[beaconMAC]["rssi"], float(beaconMSG[2]), signalDelta[beaconMAC] 
					reason=6
					beacon_ExistingHistory[beaconMAC]["reason"]=reason
					U.toLog(1, "curl: signalDelta "+ beaconMAC +" "+unicode(beacon_ExistingHistory[beaconMAC]) )

		beacon_ExistingHistory[beaconMAC]["reason"]= max(1,beacon_ExistingHistory[beaconMAC]["reason"])
		beacon_ExistingHistory[beaconMAC]["timeSt"]= t
	except	Exception, e:
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return ""
		
#################################
def setUUIDcompare(uuid, constantUUIDmajMIN,lenOfUUID):
	try:
		UUIDx = uuid.split("-")
		UUid  = uuid
		if len(UUIDx)	 !=3:			return False, uuid
		if len(UUIDx[0]) != lenOfUUID:	return False, uuid
		if	 constantUUIDmajMIN	 == "uuid--min":	UUid = UUIDx[0] + "--"+ UUIDx[2]
		elif constantUUIDmajMIN	 == "uuid-maj-":	UUid = UUIDx[0] + "-" + UUIDx[1] + "-"
		elif constantUUIDmajMIN	 == "uuid--":		UUid = UUIDx[0]
		return True, UUid
	except	Exception, e:
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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

				 
			reason=3
			beacon_ExistingHistory[beacon]["timeSt"]= tt
			beacon_ExistingHistory[beacon]["rssi"]= -999
			beacon_ExistingHistory[beacon]["reason"]= reason
			if "pkLen" not in beacon_ExistingHistory: 
				beacon_ExistingHistory[beacon]["pkLen"]=0
			beaconsNew[beacon]={
				"uuid":beacon_ExistingHistory[beacon]["uuid"],
				"txPower":beacon_ExistingHistory[beacon]["txPower"],
				"rssi":-999,
				"timeSt":tt,
				"bLevel":"",
				"pkLen":beacon_ExistingHistory[beacon]["pkLen"],
				"count":1}# [uid-major-minor,txPower,signal strength, # of measuremnts
	except	Exception, e:
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

				
	return reason, beaconsNew

#################################, check if signal strength is acceptable for fastdown 
def checkIfFastDownMinSignal(beaconMAC,rssi,fastDown):
	try:
		if	beaconMAC in fastDown:
			if "fastDownMinSignal" in fastDown[beaconMAC]:
				if fastDown[beaconMAC]["fastDownMinSignal"] > rssi: return True
	except	Exception, e:
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		U.toLog(-1," restart of BLE stack requested") 
		return True
	return False



#################################
def doSensors(pkt, UUID, Maj, Min, mac, rx, tx):
	global BLEsensorMACs
	try:
		if time.time() - BLEsensorMACs[mac]["lastUpdate"]  < BLEsensorMACs[mac]["updateIndigoTiming"]: 
			#print "rejecting ", time.time() - BLEsensorMACs[mac]["lastUpdate"] ,  BLEsensorMACs[mac]["updateIndigoTiming"]
			return 
		#print "accepting ", time.time() - BLEsensorMACs[mac]["lastUpdate"],  BLEsensorMACs[mac]["updateIndigoTiming"]
		BLEsensorMACs[mac]["lastUpdate"] = time.time()
		
		RawData = list(struct.unpack("BBB", pkt[31:34])) # get bytes # 31,32,33	 (starts at # 0 , #33 has sign, if !=0 subtract 2**15
		if RawData[2] != 0: tSign = 0x10000 # == 65536 == 2<<15
		else:				tSign = 0
		r8			= RawData[1] << 8 
		sensorData	= ( r8 + RawData[0] - tSign ) /100.
		UUID		= UUID[0:12]+"-"+Maj+"-"+Min
		sensor		= "BLEsensor"
		devId		= BLEsensorMACs[mac]["devId"]
		try:	temp  = (sensorData + BLEsensorMACs[mac]["offsetTemp"]) * BLEsensorMACs[mac]["multiplyTemp"]
		except: temp  = sensorData
		# print "raw, tSign, t1<<8, sensorData, sensorData*9./5 +32.", RawData, tSign, r8, temp, sensorData, sensorData*9./5 +32.
		data   = {sensor:{devId:{}}}
		data[sensor][devId] = {"temp":temp, "type":BLEsensorMACs[mac]["type"],"mac":mac,"rssi":float(rx),"txPower":float(tx),"UUID":UUID}
		composeMSGSensor(data)
	except	Exception, e:
		U.toLog(-1,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
	return


####### main pgm / loop ############


#################################



####### main pgm / loop ############


global	 collectMsgs, sendAfterSeconds, loopMaxCallBLE,	 ignoreUUID,  beacon_ExistingHistory, deleteHistoryAfterSeconds,lastWriteHistory,maxParseSec,batteryLevelPosition
global acceptNewiBeacons, onlyTheseMAC,enableiBeacons,offsetUUID,alreadyIgnored, sendFullUUID, minSignalCutoff, acceptJunkBeacons
global myBLEmac, BLEsensorMACs
global oldRaw,	lastRead
global UUIDtoIphone, UUIDtoIphoneReverse
BLEsensorMACs = {}

acceptJunkBeacons	= False
oldRaw					= ""
lastRead				= 0
minSignalCutoff		= {}
G.debug				= 2
acceptNewiBeacons	= -999
enableiBeacons		= "1"
G.authentication	= "digest"
# get params
onlyTheseMAC		=[]
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
U.killOldPgm(myPID,G.program+".py")

readParams(True)
fixOldNames()


# getIp address 
if U.getIPNumber() > 0:
	U.toLog(-1, " no ip number ", doPrint=True)
	time.sleep(10)
	exit(2)


# get history
readbeacon_ExistingHistory()


## start bluetooth
sock, myBLEmac, retCode= startBlueTooth(G.myPiNumber)  
if retCode !=0: 
	U.toLog(-1,"stopping "+G.program+" bad BLE start retCode= "+str(retCode),doPrint=True )
	time.sleep(30)
	sys.exit(1)

	
loopCount	 = 0
tt			 = time.time()
logfileCheck = tt
paramCheck	 = tt

os.system("echo "+str(tt)+" > "+ G.homeDir+"temp/alive.beaconloop  &" )
lastAlive=tt
lastIgnoreReset =tt
U.toLog(-1, "starting loop", doPrint=True )
G.tStart= time.time()
beaconsNew={}

bleRestartCounter = 0
eth0IP, wifi0IP, G.eth0Enabled,G.wifiEnabled = U.getIPCONFIG()
##print "beaconloop", eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled


lastMSGwithData1 = time.time()
lastMSGwithData2 = time.time()
maxLoopCount	 = 6000
restartCount	 = 0
try:
	while True:
		loopCount +=1
		tt = time.time()
		if tt - lastIgnoreReset > 600: # check once per 10 minutes
			alreadyIgnored ={}
			lastIgnoreReset =tt
			eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
					
			
		beaconsNew = {}
		
		U.toLog(3,"beacons info: "+unicode(beacon_ExistingHistory))
		timeAtLoopStart = tt

		U.echoLastAlive(G.program)

		reason = 1

		if checkIfBLErestart():
			bleRestartCounter +=1
			if bleRestartCounter > 10: 
				U.restartMyself(param="", reason="bad BLE restart",doPrint=True)
				time.sleep(1)
				sys.exit(4)

			sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber)
			U.toLog(-1,"stopping "+G.program+" bad BLE start retCode= "+str(retCode),doPrint=True )
			if retCode != 0 : sys.exit(5)

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
			tt=time.time()
			quick = U.checkNowFile(sensor)				  
			if tt - paramCheck > 2:
				newParametersFile = readParams(False)
				paramCheck=time.time()
				if newParametersFile: 
					quick = True
				
				
			if reason > 1 and tt -G.tStart > 30: break	# only after ~30 seconds after start....  to avoid lots of short messages in the beginning = collect all ibeacons before sending

			if tt - timeAtLoopStart	 > sendAfter: 
				break # send curl msgs after collecting for xx seconds

			## get new data
#			 allBeaconMSGs = parse_events(sock, collectMsgs,offsetUUID,batteryLevelPosition,maxParseSec ) # get the data:  get up to #collectMsgs at one time
			allBeaconMSGs=[]
			try: pkt = sock.recv(255)
			except: 
				U.toLog(-1, " timeout exception", doPrint = True)
				pkt=""
			doP = False
			U.toLog(5, "loopCount:"+unicode(loopCount)+ "  #:"+unicode(iiWhile)+"  len:"+unicode(len(pkt))) 
			pkLen = len(pkt)
			if pkLen > 20: 
				num_reports = struct.unpack("B", pkt[4])[0]
				num_reports = 1
				try:
					offS = 7
					for i in range(0, num_reports):
						if pkLen < offS + 6: 
							U.toLog(-1, "bad data" +unicode(i)+ " "+unicode(num_reports)+ " "+unicode(offS + 6)+ " " +unicode(pkLen)+ "xx", doPrint = True)
							break
						# build the return string: mac#, uuid-major-minor,txpower??,rssi
						mac	 = (packed_bdaddr_to_string(pkt[offS :offS + 6])).upper()
						lastMSGwithData1 = int(time.time())
						
						if mac in badMacs: continue
						if mac in batteryLevelPosition: blOffset= batteryLevelPosition[mac] 
						else:							blOffset= 0
						if mac in offsetUUID:
							offsetU = int(offsetUUID[mac])
						else: 
							offsetU = 0	  
						nBytesThisMSG		= ord(pkt[offS+6])
						if not acceptJunkBeacons:
							if nBytesThisMSG < 5: 
								#print "reject nBytesThisMSG" 
								continue # this is not supported ..
						
						msgStart			= offS + 7
						AD1Len				= ord(pkt[msgStart])
						AD1Start			= msgStart + 1
						if nBytesThisMSG > 17:
							if AD1Start+AD1Len >= pkLen: continue
							AD2Len			= ord(pkt[AD1Start+AD1Len])
							AD2Start		= AD1Start+AD1Len + 1
						else:
							AD2Len			= AD1Len
							AD2Start		= AD1Start

						
						uuidStart		= AD2Start ##  (-Maj-Min-batteryLength-TX-RSSI)
						uuidLen			= msgStart+nBytesThisMSG-uuidStart-2-2-1-offsetU
						if uuidStart > pkLen - 2 or  uuidStart < 12:
							uuidLen			 = min(nBytesThisMSG - 5, 16)
							uuidStart		 = AD1Start + 2

						if uuidStart >= pkLen or uuidStart+uuidLen > pkLen : continue
						UUID = returnstringpacket(pkt[uuidStart : uuidStart+uuidLen])
						

						if not acceptJunkBeacons:
							if UUID =="" or UUID.find("0000000000") > -1: 
								#print "reject UUID" 
								continue # this is not supported ..


						if len(UUID) > 32:
							UUID=UUID[len(UUID) -32:]  # drop AD2 stuff only use the real UUID 
						Maj	 = "%i" % returnnumberpacket(pkt[uuidStart+uuidLen	  : uuidStart+uuidLen + 2])
						Min	 = "%i" % returnnumberpacket(pkt[uuidStart+uuidLen + 2: uuidStart+uuidLen + 4])
						 
						tx	 = "%i" % struct.unpack("b", pkt[ -2 ])
						rx	 = "%i" % struct.unpack("b", pkt[ -1 ])
						if not acceptJunkBeacons:
							if tx == 0 and rx == 0: 
								#print "reject rxtx" 
								continue # this is not supported ..
								
						if mac in batteryLevelPosition:
							try:	
								bl	 =	"%i" % ord( pkt[ batteryLevelPosition[mac] ])
							except: 
								bl	 = "-"
						else:
							bl	 =""	
							
						sensorData=0
						
						lastMSGwithData2 = int(time.time())
						
						if mac in BLEsensorMACs: 
							doSensors(pkt,UUID,Maj,Min,mac,rx,tx)
							continue

						beaconMSG = [mac, UUID+"-"+Maj+"-"+Min,rx,tx,bl,nBytesThisMSG]

						if False and   mac == "EC:FE:7E:10:9C:E7xx" : #False and ( G.debug>3  or mac[0:5]=="E0:48" or pkLen < 20 ):
								doP=True
								print beaconMSG, " len: "+str(pkLen)+" nBytesThisMSG: "+str(nBytesThisMSG)+	 " AD1Start: "+str(AD1Start)+  " AD1Len: "+str(AD1Len)+	 " AD2Start: "+str(AD2Start)+  " AD2Len: "+str(AD2Len)+	 " uuidStart: "+str(uuidStart)+	 " uuidLen: "+str(uuidLen)
								print	  ( " " .join( str(n).rjust(4) for n in range( offS )  )  )	 + " | "							+ ( " " .join( str(n).rjust(4) for n in range(offS, offS + 6 )	)  )  + " | " +	 ( " " .join( str(n).rjust(4) for n in range( offS + 6,pkLen )	)  )
								print "	 "+ "  ".join(str((returnstringpacket(pkt[n:n+1]))).ljust(3) for n in range(  offS )	) + "|	 "+ "  ".join(str((returnstringpacket(pkt[n:n+1]))).ljust(3) for n in range(offS,  offS + 6 )	 ) + "|	  "+ "	".join(str((returnstringpacket(pkt[n:n+1]))).ljust(3) for n in range( offS + 6,pkLen )	  )
								print " ".join(str(ord(pkt[n])).rjust(4) for n in range(   offS	 )	)+ " | "								+" ".join(str(ord(pkt[n])).rjust(4) for n in range( offS,  offS + 6	 )	)+ " | "+ " ".join(str(ord(pkt[n])).rjust(4) for n in range(  offS + 6,pkLen  )	 )
								print " ".join(str("%i" % struct.unpack("b", pkt[n ])).rjust(4) for n in range( offS ) )+ " | "			   + " ".join(str("%i" % struct.unpack("b", pkt[n ])).rjust(4) for n in range(offS, offS + 6) )+ " | "+ " ".join(str("%i" % struct.unpack("b", pkt[n ])).rjust(4) for n in range(offS + 6,pkLen) )
								#print "temp ", tempString , tempString/ 100., (tempString/ 100. )*1.8 + 32
							
							
						beaconMSG = [mac, UUID+"-"+Maj+"-"+Min,rx,tx,bl,nBytesThisMSG]
						

						offS+=nBytesThisMSG
						U.toLog(2, "allBeaconMSGs: "+unicode( beaconMSG) )


						try: 
							beaconMAC	= mac
							uuid		= UUID+"-"+Maj+"-"+Min
							rssi		= float(rx)
							txPower		= float(tx)
							bLevel		= bl
							pkLen		= nBytesThisMSG
						except	Exception, e:
							U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),permanentLog=True)
							U.toLog(-1, "bad data >> "+unicode(beaconMSG)+"  <<beaconMSG", doPrint=True)
							continue# skip if bad data
 
						### if in fast down lost and signal < xx ignore this signal= count as not there 
						if beaconMAC in fastDown : sendAfter = min(45., sendAfterSeconds)
						if checkIfFastDownMinSignal(beaconMAC,rssi,fastDown): continue

						iphoneUUID, beaconMAC = checkIfIphone(uuid,beaconMAC)
						if not iphoneUUID:
							if checkIfIgnore(uuid,beaconMAC): continue

						if not (beaconMAC in onlyTheseMAC or beaconMAC	in doNotIgnore):  # this is a new one
							if rssi < acceptNewiBeacons: continue						  # if new it must have signal > threshold

						if beaconMAC not in beaconsNew: # add fresh one if not in new list
							beaconsNew[beaconMAC]={"uuid":uuid,"txPower":txPower,"rssi":rssi,"count":1,"timeSt":tt,"bLevel":bl,"pkLen":pkLen}# [uid-major-minor,txPower,signal strength, # of measuremnts
							#reason = 3
							
						else:  # increment averages and counters
							if beaconsNew[beaconMAC]["rssi"] == -999:
								beaconsNew[beaconMAC]["rssi"]	 = rssi # signal
								beaconsNew[beaconMAC]["count"]	 = 1  # count for calculating averages
								beaconsNew[beaconMAC]["txPower"] = txPower # transmit power
								#print "rssi =-999 set first entry ",beaconMAC, rssi,"-- rssi"
							else:	 
								beaconsNew[beaconMAC]["rssi"]	 += rssi # signal
								beaconsNew[beaconMAC]["count"]	 += 1  # count for calculating averages
								beaconsNew[beaconMAC]["txPower"] += txPower # transmit power
							beaconsNew[beaconMAC]["timeSt"]		 = tt  # count for calculating averages
							beaconsNew[beaconMAC]["bLevel"]		 = bLevel # battery level or temp of sensor 
						reason= checkIfNewOrDeltaSignalOrWasMissing(reason,beaconMAC,beaconMSG,beaconsNew[beaconMAC]["count"])
						####if beaconMAC =="0C:F3:EE:00:66:15": print  beaconsNew

				except	Exception, e:
					U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)+ "  bad data, skipping",permanentLog=True, doPrint=True)
					try:
						print "	 MAC:  ", mac
						print "	 UUID: ", UUID
					except: pass
					continue# skip if bad data


			#print time.time()-timeAtLoopStart, len(beaconsNew)
			reason, beaconsNew = checkIfFastDown(beaconsNew,reason) # send -999 if gone 
			#if beaconMAC =="0C:F3:EE:00:66:15": print	beaconsNew
			#sys.stdout.write( str(reason)+" ")
			if quick: break

			


		sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
		#print "reason",datetime.datetime.now(), reason
		composeMSG(beaconsNew,timeAtLoopStart,reason)
		handleHistory() 
		U.echoLastAlive(G.program)

		dt1 = int(time.time() - lastMSGwithData1)
		dt2 = int(time.time() - lastMSGwithData2)
		if dt1 > 90 or dt2 > 90:
			G.debug = 10
			maxLoopCount = 20
			restartCount +=1
			U.toLog(-1, u" time w/out any message .. anydata: %6d[secs];  okdata: %6d[secs];   loopCount:%d;  restartCount:%d"%(dt1,dt2,loopCount,restartCount),doPrint=True)
			if dt2 > 400 :
				time.sleep(20)
				U.restartMyself(param="", reason="bad BLE (2),restart",doPrint=True)
			if restartCount > 1:
				U.toLog(-1, " restarting BLE stack due to no messages "+G.program)
				G.debug = 0
				sock, myBLEmac, retCode = startBlueTooth(G.myPiNumber)
				maxLoopCount = 6000
		else:
			restartCount = 0

except	Exception, e:
	U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),permanentLog=True)
	U.toLog(-1, "  exiting loop due to error\n restarting "+G.program)
	time.sleep(20)
	os.system("/usr/bin/python "+G.homeDir+G.program+".py &")

U.toLog(-1,"end of beaconloop.py ", doPrint=True ) 
sys.exit(0)		   
