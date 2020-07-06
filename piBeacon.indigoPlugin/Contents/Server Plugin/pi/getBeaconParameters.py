#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7 
##
import SocketServer
import RPi.GPIO as GPIO
import smbus
import re
import json, sys,subprocess, os, time, datetime
import copy

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "getBeaconParameters"



def execGetParams(devices, beaconsOnline):
	global killMyselfAtEnd
	data ={} 
	try:	
		devices = json.loads(devices)
		if len(devices) ==0: return
		subprocess.call("echo getbeaconparameters  > {}temp/stopBLE".format(G.homeDir), shell=True)
		cmd = "sudo /bin/hciconfig hci0 down;sudo /bin/hciconfig hci0 up"
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		U.logger.log(20,"get beacon getbeaconparameters devices:{}".format(devices))
 		timeoutSecs = 15
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
				uuid  = params["uuid"]
				bits  = params["bits"]
				norm  = params["norm"]
#					devices:{u'24:DA:11:21:2B:20': {u'battCmd': {u'random': u'public', u'bits': 63, u'uuid': u'2A19', u'norm': 36}}}

				cmd = "/usr/bin/timeout -s SIGKILL {}   /usr/bin/gatttool -b {} {} --char-read --uuid={}".format(timeoutSecs, mac,random, uuid)
				##					                   /usr/bin/gatttool -b 24:da:11:27:E4:23 --char-read --uuid=2A19 -t public / random   
				U.logger.log(20,"cmd: {}".format(cmd) )
				ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
				check = (ret[0]+" -- "+ret[1]).lower().strip("\n").replace("\n"," -- ").strip()
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
							valueF = int( ( valueB *100. )/norm )
						except:pass
				U.logger.log(20,"... ret: {}; bits: {}; norm:{}; value-I: {}; -B: {};  -F: {} ".format(check, bits, norm, valueI, valueB, valueF) )
				if "sensors" not in data: data["sensors"] = {}
				if "getBeaconParameters" not in data["sensors"]: data["sensors"]["getBeaconParameters"] ={}
				if mac not in data["sensors"]["getBeaconParameters"]: data["sensors"]["getBeaconParameters"][mac] ={}
				data["sensors"]["getBeaconParameters"][mac] = {"batteryLevel":valueF}
			except Exception, e:
				if unicode(e).find("Timeout") == -1:
					U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				else:
					U.logger.log(20, u"Line {} has timeout".format(sys.exc_traceback.tb_lineno))
				time.sleep(1)

			
	except Exception, e:
			U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	if data !={}:
		U.sendURL(data, wait=True, squeeze=False)

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
	execGetParams(sys.argv[1],beaconsOnline)
	U.logger.log(20, u"finished  after {:.1f} secs".format(time.time()-startTime))
	time.sleep(3.)
	subprocess.Popen("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
	if killMyselfAtEnd: 
		#U.logger.log(20, u"exec cmd: killing myself at PID {}".format(myPID))
		time.sleep(5)
		subprocess.Popen("sudo kill -9 "+str(myPID), shell=True )
	exit(0)
