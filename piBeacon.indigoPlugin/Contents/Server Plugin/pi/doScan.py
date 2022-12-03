#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# May 1 2020
# version 1.1 
##
import json, sys,subprocess, os, time, datetime
import copy
import pexpect

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "beepBeacon"


def doScan():
	global killMyselfAtEnd
	try:	

		## which HCI? if same as beaconloop, need to signal a restart of hci at the end for  beaconloop
		useHCI = "hci0"
		restartBLE = True
		HCIs = U.whichHCI()
		if HCIs != {} and "hci" in  HCIs and len(HCIs["hci"]) >1: # we have > 1 BLE channel
			useHCIForBeacons,  myBLEmac, devId = U.selectHCI(HCIs["hci"], G.BeaconUseHCINo,"UART")
			restartBLE = False
			if useHCIForBeacons == "hci0":
				useHCI = "hci1"
			else:
				useHCI = "hci0"

		# devices: '{u'24:DA:11:21:2B:20': {u'cmdOff': u'char-write-cmd 0x0011 00', u'cmdON': u'char-write-cmd  0x0011  02', u'beepTime': 2.0}}'
		if restartBLE:
			subprocess.call("echo scan  > {}temp/stopBLE".format(G.homeDir), shell=True)
		ret = subprocess.Popen("sudo /bin/hciconfig {} reset".format(useHCI),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		debugLevel = 40
		U.logger.log(debugLevel,"start scan")
		tryAgain = 3
		done = False
		for kk in range(3):
				tryAgain -= 1
				if tryAgain < 0: break
				if tryAgain != 2:
					try: expCommands.sendline("disconnect")	
					except: pass	
				cmd = "sudo /usr/bin/bluetoothctl" 
				U.logger.log(debugLevel,cmd)
				expCommands = pexpect.spawn(cmd)
				ret = expCommands.expect(["Agent registered","error",pexpect.TIMEOUT], timeout=10)
				if ret == 0:
					U.logger.log(debugLevel,"... successful: {}-{}".format(expCommands.before,expCommands.after))
					connected = True
				elif ret == 1:
					if ii < ntriesConnect-1: 
						U.logger.log(debugLevel, u"... error, giving up: {}-{}".format(expCommands.before,expCommands.after))
						time.sleep(1)
						break
				elif ret == 2:
					if ii < ntriesConnect-1: 
						U.logger.log(debugLevel, u"... timeout, giving up: {}-{}".format(expCommands.before,expCommands.after))
						time.sleep(1)
						break
				else:
					if ii < ntriesConnect-1: 
						U.logger.log(debugLevel,"... unexpected, giving up: {}-{}".format(expCommands.before,expCommands.after))
						time.sleep(1)
						break

				time.sleep(0.1)
				debugLevel = 40
				try:
						success = True
						#cmds= ["menu scan","clear rssi","clear uuids","clear duplicate-data","rssi -60","export","back","scan on","sleep","scan off","quit"]
						cmds= ["scan on","sleep","scan off","quit"]
						for ii in range(50):
								if done: break
								for cc in cmds:
									U.logger.log(debugLevel,"cmd  {}".format(cc))
									if cc.find("sleep") >-1:
										time.sleep(15)
										continue
									expCommands.sendline( cc )
									if cc == "scan on":
										continue
									ret = 0# expCommands.expect(["bluetooth","Error","failed",pexpect.TIMEOUT], timeout=2)
									U.logger.log(debugLevel,"after cmd  {}".format(ret))
									if cc == "scan off":
										U.logger.log(debugLevel,"... outpout of scan output: {}".format(expCommands.before))
										time.sleep(1)
										done = True
										break
									ret = expCommands.expect(["bluetooth","Error","failed",pexpect.TIMEOUT], timeout=2)
									if ret == 0:
										U.logger.log(debugLevel,"... successful: {}-{}".format(expCommands.before,expCommands.after))
										time.sleep(0.1)
										continue
									elif ret in[1,2]:
										if ii < ntriesConnect-1: 
											U.logger.log(debugLevel, u"... error, quit: {}-{}".format(expCommands.before,expCommands.after))
										success = False
										break
									elif ret == 3:
										U.logger.log(debugLevel,"... timeout, quit: {}-{}".format(expCommands.before,expCommands.after))
										success = False
										break
									else:
										U.logger.log(debugLevel,"... unexpected, quit: {}-{}".format(expCommands.before,expCommands.after))
										success = False
										break
								time.sleep(1)
						expCommands.sendline("quit" )
						U.logger.log(debugLevel,"quit ")
						if done: break


				except Exception as e:
					U.logger.log(30,"", exc_info=True)
					time.sleep(1)
				try:	expCommands.sendline("quit\r" )
				except: pass

		expCommands.close()		
	except Exception as e:
			U.logger.log(30,"", exc_info=True)

	if restartBLE:
		subprocess.call("rm "+G.homeDir+"temp/stopBLE", shell=True)

	killMyselfAtEnd = True
	return




def readParams():
	global execcommands, PWM, typeForPWM, killMyselfAtEnd
	killMyselfAtEnd = True
	inp,inpRaw = U.doRead()
	if inp == "": return
	U.getGlobalParams(inp)


### main pgm 		 
global execcommands, PWM, myPID, killMyselfAtEnd, debugLevel
if True: #__name__ == "__main__":
	PWM = 100
	myPID = int(os.getpid())
	U.setLogging()
	readParams()
	debugLevel = 40
	#G.debug  = 1
#### read exec command list for restart values, update if needed and write back
	execcommands={}
	startTime = time.time()
	doScan()
	U.logger.log(debugLevel, u"finished  after {:.1f} secs".format(time.time()-startTime))
	#subprocess.Popen("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
	if killMyselfAtEnd: 
		#U.logger.log(debugLevel, u"exec cmd: killing myself at PID {}".format(myPID))
		subprocess.Popen("sudo kill -9 "+str(myPID), shell=True )
	exit(0)
