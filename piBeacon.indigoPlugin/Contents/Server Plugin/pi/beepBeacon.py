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


def beep(devices, beaconsOnline):
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
		devices = json.loads(devices)
		if len(devices) ==0: return
		if restartBLE:
			subprocess.call("echo beepBeacon  > {}temp/stopBLE".format(G.homeDir), shell=True)
		ret = subprocess.Popen("sudo /bin/hciconfig {} reset".format(useHCI),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		U.logger.log(debugLevel,"beepBeacon devices:{}".format(devices))
		for mac in devices:
			if len(mac) < 10: continue
			params		= devices[mac]

			tryAgain = 3
			for kk in range(3):
				tryAgain -= 1
				if tryAgain < 0: break
				if tryAgain != 2:
					try: expCommands.sendline("disconnect")	
					except: pass	

				if "random" in params and params["random"] == "randomON":	random = " -t random"
				else:					 									random = " "
				cmd = "sudo /usr/bin/gatttool -i {} {} -b {} -I".format(useHCI, random, mac) 
				U.logger.log(debugLevel,cmd)
				expCommands = pexpect.spawn(cmd)
				ret = expCommands.expect([">","error",pexpect.TIMEOUT], timeout=10)
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

				if "mustBeUp" in params and params["mustBeUp"]: force = False
				else:											force = True
				if  not force and mac not in beaconsOnline:
					U.logger.log(debugLevel,"mac: {}; skipping, not online or not in range".format(mac) )
					continue
				try:
					cmdON		= params["cmdON"]
					cmdOff		= params["cmdOff"]
					beepTime	= float(params["beepTime"])
					U.logger.log(debugLevel,"{}:   cmdON:{};  cmdOff:{};  beepTime:{} ".format(mac, cmdON, cmdOff, beepTime) )

					connected = False
					ntriesConnect = 6
					for ii in range(ntriesConnect):
						try:
							U.logger.log(debugLevel,"expect connect ")
							expCommands.sendline("connect ")
							ret = expCommands.expect(["Connection successful","Error", pexpect.TIMEOUT], timeout=15)
							if ret == 0:
								U.logger.log(debugLevel,"... successful: {}".format(expCommands.after))
								connected = True
								break
							elif ret == 1:
								if ii < ntriesConnect-1: 
									U.logger.log(debugLevel, u"... error, try again: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(1)
							elif ret == 2:
								if ii < ntriesConnect-1: 
									U.logger.log(debugLevel, u"... timeout, try again: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(1)
							else:
								if ii < ntriesConnect-1: 
									U.logger.log(debugLevel,"... unexpected, try again: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(1)

						except Exception, e:
							U.logger.log(debugLevel, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							if ii < ntriesConnect-1: 
								U.logger.log(debugLevel, u"... error, try again")
								time.sleep(1)

					if not connected:
						U.logger.log(debugLevel, u"connect error, giving up")
						tryAgain = True
					
					else:
						startbeep = time.time()
						lastBeep = 0
						success = True
						for ii in range(50):
							if time.time() - lastBeep > 10:
								for cc in cmdON:
									U.logger.log(debugLevel,"sendline  cmd{}".format( cc))
									expCommands.sendline( cc )
									ret = expCommands.expect([mac,"Error","failed",pexpect.TIMEOUT], timeout=5)
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
								lastBeep = time.time()
							if time.time() - startbeep > beepTime: break
							time.sleep(1)

						if success:
							for cc in cmdOff:
								U.logger.log(debugLevel,"sendline  cmd{}".format( cc))
								expCommands.sendline( cc )
								ret = expCommands.expect([mac,"Error","failed",pexpect.TIMEOUT], timeout=5)
								if ret == 0:
									U.logger.log(debugLevel,"... successful: {}-{}".format(expCommands.before,expCommands.after))
									time.sleep(0.1)
								elif ret in[1,2]:
									U.logger.log(debugLevel,"... error: {}-{}".format(expCommands.before,expCommands.after))
								elif ret == 3:
									U.logger.log(debugLevel,"... timeout: {}-{}".format(expCommands.before,expCommands.after))
								else:
									U.logger.log(debugLevel,"... unknown: {}-{}".format(expCommands.before,expCommands.after))
								tryAgain = -1

						expCommands.sendline("disconnect" )
						U.logger.log(debugLevel,"sendline disconnect ")
						ret = expCommands.expect([">","Error",pexpect.TIMEOUT], timeout=5)
						if ret == 0:
							U.logger.log(debugLevel,"... successful: {}".format(expCommands.after))
						elif ret == 1:
							U.logger.log(debugLevel,"... error: {}".format(expCommands.after))
						elif ret == 2:
							U.logger.log(debugLevel,"... timeout: {}".format(expCommands.after))
						else: 
							U.logger.log(debugLevel,"... unknown: {}".format(expCommands.after))


				except Exception, e:
					U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					time.sleep(1)
				try:	expCommands.sendline("quit\r" )
				except: pass

		expCommands.close()		
	except Exception, e:
			U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
	debugLevel = 20
	#G.debug  = 1
#### read exec command list for restart values, update if needed and write back
	execcommands={}
	startTime = time.time()
	U.logger.log(10, u"exec cmd: {}".format(sys.argv[1]))
	beaconsOnline, raw = U.readJson("{}temp/beaconsOnline".format(G.homeDir))	
	beep(sys.argv[1],beaconsOnline)
	U.logger.log(debugLevel, u"finished  after {:.1f} secs".format(time.time()-startTime))
	#subprocess.Popen("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
	if killMyselfAtEnd: 
		#U.logger.log(debugLevel, u"exec cmd: killing myself at PID {}".format(myPID))
		subprocess.Popen("sudo kill -9 "+str(myPID), shell=True )
	exit(0)
