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



def beepBatch(devices, beaconsOnline):  # not used anymore 
	global killMyselfAtEnd
	try:	
		devices = json.loads(devices)
		if len(devices) == 0: return
		subprocess.call("echo beepBeacon  > {}temp/stopBLE".format(G.homeDir), shell=True)
		cmd = "sudo /bin/hciconfig hci0 down;sudo /bin/hciconfig hci0 up"
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20,"beepBeacon devices:{}".format(devices))
 		timeoutSecs = 10
		for mac in devices:
			U.logger.log(30,"mac: {}".format(mac) )
			if len(mac) < 10: continue
			if False and mac not in beaconsOnline:
				U.logger.log(20,"mac: {}; skipping, not online or not in range".format(mac) )
				continue
			try:
				#'{"24:DA:11:21:2B:20":"char-write-cmd=0x0011+02=0x0011+02=2"}'
				params		= devices[mac]
				cmdON		= devices[mac]["cmdON"]
				cmdOff		= devices[mac]["cmdOff"]
				beepTime	= devices[mac]["beepTime"]
				U.logger.log(20,"{}:  cmdON:{};  cmdOff:{};  beepTime:{} ".format(mac, cmdON, cmdOff, beepTime) )
				cmd = "sudo gatttool -b "+mac+"  "+ cmdON
				U.logger.log(20,"cmd:{};  ".format(cmd) )
				ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				time.sleep(beepTime)
				cmd = "sudo gatttool -b "+mac+"  "+ cmdOff
				U.logger.log(20,"cmd:{};  ".format(cmd) )
				ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			except Exception, e:
				U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				time.sleep(1)
	except Exception, e:
			U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	subprocess.call("rm "+G.homeDir+"temp/stopBLE", shell=True)
	killMyselfAtEnd = True
	return

def beep(devices, beaconsOnline):
	global killMyselfAtEnd
	try:	
		# devices: '{u'24:DA:11:21:2B:20': {u'cmdOff': u'char-write-cmd 0x0011 00', u'cmdON': u'char-write-cmd  0x0011  02', u'beepTime': 2.0}}'
		devices = json.loads(devices)
		if len(devices) ==0: return
		subprocess.call("echo beepBeacon  > {}temp/stopBLE".format(G.homeDir), shell=True)
		cmd = "sudo /bin/hciconfig hci0 down;sudo /bin/hciconfig hci0 up"
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(20,"beepBeacon devices:{}".format(devices))
		expCommands = pexpect.spawn("gatttool -I")
		ret = expCommands.expect(">", timeout=5)
		U.logger.log(10,"spawn gatttool -I ret:{}".format(ret))
 		timeoutSecs = 10
		for mac in devices:
			U.logger.log(30,"mac: {}".format(mac) )
			if len(mac) < 10: continue
			if  mac not in beaconsOnline:
				U.logger.log(20,"mac: {}; skipping, not online or not in range".format(mac) )
				continue
			try:
				params		= devices[mac]
				onCMD		= params["cmdON"]
				offCMD		= params["cmdOff"]
				beepTime	= float(params["beepTime"])
				U.logger.log(20,"{}:   onCMD:{};  offCMD:{};  beepTime:{} ".format(mac, onCMD, offCMD, beepTime) )
				for ii in range(3):
					try:
						ret = expCommands.sendline("connect {}".format(mac))
						U.logger.log(10,"expect connect {} ret:{}".format(mac, ret))
						ret = expCommands.expect("Connection successful", timeout=5)
						U.logger.log(10,"expect Connection successful >  ret:{}".format(ret))
						break
					except Exception, e:
						U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						U.logger.log(30, u" try again")
						time.sleep(2)


				startbeep = time.time()
				lastBeep = 0
				for ii in range(50):
					if time.time() - lastBeep > 10:
						ret = expCommands.sendline( onCMD )
						U.logger.log(10,"sendline  cmd{}  ret:{}".format( onCMD, ret))
						lastBeep = time.time()
						ret = expCommands.expect(">", timeout=5)
						U.logger.log(10,"expect >  ret:{}".format(ret))
					if time.time() - startbeep > beepTime: break
					time.sleep(1)
				ret = expCommands.sendline(offCMD )
				U.logger.log(10,"sendline  cmd{}  ret:{}".format( offCMD, ret))
				ret = expCommands.expect(">", timeout=5)
				U.logger.log(10,"expect >  ret:{}".format(ret))
				ret = expCommands.sendline("disconnect" )
				U.logger.log(10,"sendline disconnect  ret:{}".format(ret))
				ret = expCommands.expect(">", timeout=5)
				U.logger.log(10,"expect >  ret:{}".format(ret))
			except Exception, e:
				U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				time.sleep(1)

		ret = expCommands.sendline("quit\r" )
		expCommands.close()		
	except Exception, e:
			U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
global execcommands, PWM, myPID, killMyselfAtEnd
if True: #__name__ == "__main__":
	PWM = 100
	myPID = int(os.getpid())
	U.setLogging()
	readParams()
	#G.debug  = 1
#### read exec command list for restart values, update if needed and write back
	execcommands={}
	startTime = time.time()
	U.logger.log(10, u"exec cmd: {}".format(sys.argv[1]))
	beaconsOnline, raw = U.readJson("{}temp/beaconsOnline".format(G.homeDir))	
	beep(sys.argv[1],beaconsOnline)
	U.logger.log(20, u"finished  after {:.1f} secs".format(time.time()-startTime))
	#subprocess.Popen("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
	if killMyselfAtEnd: 
		#U.logger.log(20, u"exec cmd: killing myself at PID {}".format(myPID))
		subprocess.Popen("sudo kill -9 "+str(myPID), shell=True )
	exit(0)
