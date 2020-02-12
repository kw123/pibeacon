#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	 read sensors and GPIO INPUT and send http to indigo with data
#

##
import	sys, os, subprocess, copy
import	time,datetime
import	json
import	RPi.GPIO as GPIO  
import bluetooth
import bluetooth._bluetooth as bt
import struct
import array
import fcntl


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "BLEconnect"

				
def readParams():
		global debug, ipOfServer,myPiNumber,passwordOfServer, userIdOfServer, authentication,ipOfServer,portOfServer,sensorList,restartBLEifNoConnect
		global macList 
		global oldRaw, lastRead

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return False
		if lastRead2 == lastRead: return False
		lastRead  = lastRead2
		if inpRaw == oldRaw: return False
		oldRaw	   = inpRaw

		oldSensor		  = sensorList

		try:

			U.getGlobalParams(inp)
			if "restartBLEifNoConnect"	in inp:	 restartBLEifNoConnect=		  (inp["restartBLEifNoConnect"])
			if "sensorList"				in inp:	 sensorList=				  (inp["sensorList"])

			if "BLEconnect" not in sensorList:
				U.logger.log(30, u" no iphoneBLE definitions supplied (1) stopping")
				exit()
			if "sensors"				in inp:	 sensors=					  (inp["sensors"]["BLEconnect"])
			macListNew={}

			for devId in sensors :
					thisMAC = sensors[devId]["macAddress"]
					macListNew[thisMAC]={"iPhoneRefreshDownSecs":float(sensors[devId]["iPhoneRefreshDownSecs"]),
										 "iPhoneRefreshUpSecs":float(sensors[devId]["iPhoneRefreshUpSecs"]),
										 "BLEtimeout":float(sensors[devId]["BLEtimeout"]),
										 "up":False,
										 "lastTesttt":time.time()-1000.,
										 "lastMsgtt":time.time()-1000. ,
										 "lastData":"xx" ,
										 "quickTest": 0. ,
										 "devId": devId	 }
			for thisMAC in macListNew:
				if thisMAC not in macList:
					macList[thisMAC]=copy.copy(macListNew[thisMAC])
				else:
					macList[thisMAC]["iPhoneRefreshDownSecs"] = macListNew[thisMAC]["iPhoneRefreshDownSecs"]
					macList[thisMAC]["iPhoneRefreshUpSecs"]	  = macListNew[thisMAC]["iPhoneRefreshUpSecs"]
					macList[thisMAC]["BLEtimeout"]	 		  = macListNew[thisMAC]["BLEtimeout"]

			delMac={}
			for thisMAC in macList:
				if thisMAC not in macListNew:
					delMac[thisMAC]=1
			for	 thisMAC in delMac:
				del macList[thisMAC]

			if len(macList)	   == 0:
				U.logger.log(30, u" no BLEconnect definitions supplied stopping")
				exit()

			return True
			
		except	Exception, e:
			U.logger.log(50,u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
		return False

def tryToConnect(MAC,BLEtimeout,devId):
	global errCount

	ret	 = {"signal": -999, "txPower": -999,"flag0ok":0,"byte2":0}
	try:
		for ii in range(5):	 # wait until (wifi) sending is finsihed
			if os.path.isfile(G.homeDir + "temp/sending"):
				#print "delaying hci"
				time.sleep(0.5)
			else:
				 break

		hci_sock = bt.hci_open_dev(devId)
		hci_fd	 = hci_sock.fileno()

		# Connect to device (to whatever you like)
		bt_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
		bt_sock.settimeout(BLEtimeout)

		try:
			result	= bt_sock.connect_ex((MAC, 1))	# PSM 1 - Service Discovery
			reqstr = struct.pack("6sB17s", bt.str2ba(MAC), bt.ACL_LINK, "\0" * 17)
			request = array.array("c", reqstr)
			handle = fcntl.ioctl(hci_fd, bt.HCIGETCONNINFO, request, 1)
			handle = struct.unpack("8xH14x", request.tostring())[0]
			cmd_pkt=struct.pack('H', handle)
			# Send command to request RSSI
			rssi = bt.hci_send_req(hci_sock, bt.OGF_STATUS_PARAM, bt.OCF_READ_RSSI, bt.EVT_CMD_COMPLETE, 4, cmd_pkt)
			bt_sock.close()
			hci_sock.close()
			flag0ok	  = struct.unpack('b', rssi[0])[0]
			txPower	  = struct.unpack('b', rssi[1])[0]
			byte2	  = struct.unpack('b', rssi[2])[0]
			signal	  = struct.unpack('b', rssi[3])[0]
			#print MAC, test0, txPower, test2, signal
			ret["flag0ok"]	= flag0ok
			ret["byte2"]	= byte2
			if flag0ok == 0 and not (txPower == signal and signal == 0 ):
				ret["signal"]	= signal
				ret["txPower"]	= txPower
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
			os.system("rm {}temp/stopBLE > /dev/null 2>&1".format(G.homeDir))
			U.logger.log(20, u"in Line {} has error ... sock.recv error, likely time out ".format(sys.exc_traceback.tb_lineno))
			U.restartMyself(reason="sock.recv error",delay = 10)

	except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	U.logger.log(10, "{}:  {}".format(MAC, ret))
	errCount = 0
	return ret




#################################

####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
####################################################################################################################################
def execBLEconnect():
	global sensorList,restartBLEifNoConnect
	global macList,oldParams
	global oldRaw,	lastRead
	global errCount
	oldRaw					= ""
	lastRead				= 0
	errCount				= 0
	###################### constants #################

	####################  input gios   ...allrpi	  only rpi2 and rpi0--
	oldParams		  = ""
	#####################  init parameters that are read from file 
	sensorList			= "0"
	G.authentication	= "digest"
	restartBLEifNoConnect = True
	sensor				= G.program
	macList				={}
	waitMin				=2.
	oldRaw				= ""
	try:
		onlyThisMAC	  = sys.argv[1]
	except:
		onlyThisMAC = ""


	myPID			= str(os.getpid())
	U.setLogging()
	if onlyThisMAC =="":
		U.killOldPgm(myPID,G.program+".py")# kill  old instances of myself if they are still running
	else:
		U.killOldPgm(myPID, G.program+".py ",param1=onlyThisMAC)  # kill  old instances of myself if they are still running

	loopCount		  = 0
	sensorRefreshSecs = 90
	U.logger.log(30, "starting BLEconnect program ")
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


	## give other ble functions time to finish
	time.sleep(1)



	#### selct the proper hci bus: if just one take that one, if 2, use bus="uart", if no uart use hci0
	HCIs = U.whichHCI()
	useHCI,  myBLEmac, BLEid = U.selectHCI(HCIs, G.BLEconnectUseHCINo,"UART")
	if BLEid <0:
		U.logger.log(0, "BLEconnect: NO BLE STACK UP ")
		sys.exit(1)



	U.logger.log(30, "BLEconnect: using mac:{};  useHCI: {}; bus: {}; serching for MACs:\n{}".format(myBLEmac, useHCI, HCIs[useHCI]["bus"] , macList))

	while True:

			tt= time.time()
			if tt - nowTest > 15:
				nowP	= False
				nowTest = 0
			if tt - lastRead > 4 :
				newParameterFile = readParams()
				eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
				lastRead=tt

			if restartBLEifNoConnect and (tt - lastSignal > (2*3600+ 600*restartCount)) :
				U.logger.log(30, "requested a restart of BLE stack due to no signal for {:.0f} seconds".format(tt-lastSignal))
				os.system("echo xx > {}temp/BLErestart".format(G.homeDir)) # signal that we need to restart BLE
				lastSignal = time.time() +30
				restartCount +=1

			nextTest = 300

			for thisMAC in macList:
				if onlyThisMAC !="" and onlyThisMAC != thisMAC: continue
				if macList[thisMAC]["up"]:
					nextTest = min(nextTest, macList[thisMAC]["lastTesttt"] + (macList[thisMAC]["iPhoneRefreshUpSecs"]*0.90)   -tt )
				else:
					nextTest = min(nextTest, macList[thisMAC]["lastTesttt"] + macList[thisMAC]["iPhoneRefreshDownSecs"] -tt - macList[thisMAC]["quickTest"] )

				if True:
					nT= max(int(nextTest),1)
					fTest = nextTest / nT
					#print "fTest",thisMAC, fTest
					for ii in range(nT):
						tt=time.time()
						if fTest > 0:
							time.sleep(fTest)  # print "time to sleep "+datetime.datetime.now().strftime("%M:%S"), macList[thisMAC]["up"], macList[thisMAC]["quickTest"], nextTest
						#if thisMAC == "54:9F:13:3F:95:26":
							#print thisMAC, onlyThisMAC, nowP, tt, nowTest, tt-nowTest
						if not nowP and tt-nowTest > 20.:
							quick = U.checkNowFile(sensor)				  
							if quick:
								for ml in macList :
									if onlyThisMAC != "" and onlyThisMAC != ml: continue
									macList[ml]["lastData"]	   = {"signal":-999,"txPower":-999}
									macList[ml]["lastTesttt"]  = 0.
									#macList[ml]["lastMsgtt"]  = 0.
									macList[ml]["retryIfUPtemp"] = macList[ml]["retryIfUP"]
									macList[ml]["retryIfUP"] = False
									macList[ml]["up"]		 = False
								nowTest = tt
								nowP	= True
								#print " received BLEconnect now,", thisMAC,onlyThisMAC, "setting nowTest",	 nowTest
								break

						if nowP and tt - nowTest > 5 and tt - nowTest < 10.:
							for ml in macList:
								if onlyThisMAC != "" and onlyThisMAC != ml: continue
								nowTest = 0.
								nowP	= False
								#print "resetting  ", ml, onlyThisMAC, nowTest
			for thisMAC in macList:
				if onlyThisMAC !="" and onlyThisMAC != thisMAC: continue
				tt = time.time()
				#if nowP: print "nowP:	testing: "+thisMAC,macList[ml]["retryIfUP"], tt - macList[thisMAC]["lastTesttt"]
				if macList[thisMAC]["up"]:
					if tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["iPhoneRefreshUpSecs"]*0.90:	  continue
				elif tt - macList[thisMAC]["lastTesttt"] <= macList[thisMAC]["iPhoneRefreshDownSecs"] - macList[thisMAC]["quickTest"]:	 continue


				data0 = tryToConnect(thisMAC,macList[thisMAC]["BLEtimeout"],BLEid)
				#if nowP: print "nowP:	testing: "+thisMAC+"  "+ unicode(data0)

				#print	data0
				macList[thisMAC]["lastTesttt"] =tt

				if	data0 != {}:
					if data0["signal"] !=-999:
						macList[thisMAC]["up"] =True
						lastSignal	 = time.time()
						restartCount = 0
						if os.path.isfile(G.homeDir + "temp/BLErestart"):
							os.remove(G.homeDir + "temp/BLErestart")

					else:
						macList[thisMAC]["up"] =False

					if data0["signal"]!=macList[thisMAC]["lastData"] or (tt-macList[thisMAC]["lastMsgtt"]) > (macList[thisMAC]["iPhoneRefreshUpSecs"]-1.): # send htlm message to indigo, if new data, or last msg too long ago
						if macList[thisMAC]["lastData"] != -999 and not macList[thisMAC]["up"] and (tt-macList[thisMAC]["lastMsgtt"]) <	 macList[thisMAC]["iPhoneRefreshUpSecs"]+2.:
							macList[thisMAC]["quickTest"] =macList[thisMAC]["iPhoneRefreshDownSecs"]/2.
							continue
						#print "sending "+thisMAC+" " + datetime.datetime.now().strftime("%M:%S"), macList[thisMAC]["up"] , macList[thisMAC]["quickTest"], data0
						macList[thisMAC]["quickTest"] = 0.
						#print "af -"+datetime.datetime.now().strftime("%M:%S"), macList[thisMAC]["up"], macList[thisMAC]["quickTest"], data0
						macList[thisMAC]["lastMsgtt"]  = tt
						macList[thisMAC]["lastData"] = data0["signal"]
						data={}
						data["sensors"]					= {"BLEconnect":{macList[thisMAC]["devId"]:{thisMAC:data0}}}
						U.sendURL(data)

				else:
					macList[thisMAC]["up"] = False

			loopCount+=1
			#print "no answer sleep for " + str(iPhoneRefreshDownSecs)
			U.echoLastAlive(G.program)

execBLEconnect()
		
try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
		
sys.exit(0)		   
