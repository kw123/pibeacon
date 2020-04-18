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

		U.logger.log(20,"get beacon parameters devices:{}".format(devices))
 		timeoutSecs = 15
		for mac in devices:
			if len(mac) < 10: continue
			if mac not in beaconsOnline:
				U.logger.log(20,"mac: {}; skipping, not online or not in range".format(mac) )
				continue
			try:
				params		= devices[mac]

				#U.logger.log(30,"params:{}".format(params))
				state	= []
				uuid	= []
				random	= []
				dType	= []

				for xx in params:
					yy = xx.split("-")
					if len(yy) < 4: continue
					uuid.append(yy[0])
					if yy[1] == "randomON": random.append(" -t random ")
					else:				    random.append(" ")
					state.append(yy[2])
					dType.append(yy[3])
					bits = 127
					norm = 100
					if len(yy) == 6:
						bits = int(yy[4].split("=")[1])
						norm = int(yy[5].split("=")[1])
#					"2A19-randomON-batteryLevel-int-bits127-max64"  > read battery level UUID=2A19 random ON  for eg XY beacons
#					<"2A19-randomOff-batteryLevel-int-bits63-max36" > read battery level UUID=2A19 random off for ed noda/aiko/iHere 

				#U.logger.log(20,"{}:  state: {}; uuid:{}; random:{}; dType:{} ".format(mac, state, uuid, random, dType ) )
				if len(state) ==0: continue
				for ll in range(len(state)):
					cmd = "/usr/bin/timeout -s SIGKILL {}   /usr/bin/gatttool -b {} {} --char-read --uuid={}".format(timeoutSecs, mac,random[ll], uuid[ll])
					##					                                                 /usr/bin/gatttool -b 24:da:11:26:3b:4d --char-read --uuid=2A19 -t public    
					U.logger.log(20,"cmd: {}".format(cmd) )
					ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
					check = (ret[0]+" -- "+ret[1]).lower().strip("\n").replace("\n"," -- ").strip()
					if check.find("connect error") >-1:	value = check
					elif check.find("killed") >-1:		value = "timeout"
					elif check.find("error") >-1: 		value = check
					else: 
						value = -2
						ret2 = ret[0].split("value: ")
						if len(ret2) == 2:  
							try:
								if dType[ll] == "int": 
									value = int(((int(ret2[1].strip(),16) & bits ) *100)/norm)
								if dType[ll] == "str": value = str(ret2[1])
							except:pass
					U.logger.log(20,"... ret: {}; bits: {}; norm:{}; value: {} ".format(check, bits, norm, value) )
					#U.logger.log(10,"{}:  return: {} {} {} ".format(mac, state[ll], ret[0], value) )
					if "sensors" not in data: data["sensors"] = {}
					if "getBeaconParameters" not in data["sensors"]: data["sensors"]["getBeaconParameters"] ={}
					if mac not in data["sensors"]["getBeaconParameters"]: data["sensors"]["getBeaconParameters"][mac] ={}
					data["sensors"]["getBeaconParameters"][mac] = {state[ll]:value}
			except Exception, e:
					if unicode(e).find("Timeout") == -1:
						U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					else:
						U.logger.log(20, u"Line {} has timeout".format(sys.exc_traceback.tb_lineno))
					time.sleep(1)

			
	except Exception, e:
			U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	if data !={}:
		U.sendURL(data, wait=False, squeeze=False)

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
	time.sleep(0.5)
	subprocess.Popen("/usr/bin/python "+G.homeDir+"master.py &" , shell=True)
	if killMyselfAtEnd: 
		#U.logger.log(20, u"exec cmd: killing myself at PID {}".format(myPID))
		time.sleep(5)
		subprocess.Popen("sudo kill -9 "+str(myPID), shell=True )
	exit(0)
