#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	  --- utils 
#
#	 
import	sys, os, subprocess, math, copy
import	time, datetime, json
sys.path.append(os.getcwd())
import piBeaconGlobals as G
import socket

##
#  do 
# sys.path.append(os.getcwd())
# import  piBeaconUtils	  as U
# then get the modules as xxx()
#
#################################
def test():
	print "U.test G.ipOfServer ", G.ipOfServer 

#################################
def killOldPgm(myPID,pgmToKill,param1="",param2=""):
	try:
		cmd= "ps -ef | grep '"+pgmToKill+"' | grep -v grep"
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		lines=ret.split("\n")
		for line in lines:
			if len(line) < 10: continue
			items=line.split()
			pid=int(items[1])
			if pid == int(myPID): continue
			
			if param1 != "":
				linef = line.find(param1)
				if linef == -1: continue
				if param2 != "":
					if line[linef:].find(param2) == -1: continue
					
			toLog(-1, "killing "+pgmToKill+"  "+param1 +" "+param2)
			os.system("kill -9 "+str(pid))
	except Exception, e:
		toLog(-1, u"killOldPgm	in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

#################################
def restartMyself(param="", reason="",doPrint=True):
	toLog(-1, u"  ---- restarting ---	"+param+"  "+ reason,doPrint=doPrint)
	time.sleep(2)
	os.system("/usr/bin/python "+G.homeDir+G.program+".py "+ param+" &")

#################################
def setStopCondition(on=True):
	if on:
		os.system("sudo chmod 666 /dev/i2c-*")
		os.system("sudo chmod 666 /sys/module/i2c_bcm2708/parameters/combined")
		os.system("sudo echo -n 1 > /sys/module/i2c_bcm2708/parameters/combined")
	else:
		os.system("sudo chmod 666 /dev/i2c-*")
		os.system("sudo chmod 666 /sys/module/i2c_bcm2708/parameters/combined")
		os.system("sudo echo -n N > /sys/module/i2c_bcm2708/parameters/combined")
	
#################################
def toLog(lvl,msg,permanentLog=False,doPrint=False):
	if lvl < G.debug:
		try:
			if G.program =="":
				print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+ " toLog	 G.program not defined msg= "+ msg 
				return 
			if	not os.path.isdir(G.logDir):
				print " logfile not ready"
				os.system("sudo mkdir "+G.logDir+" &")
				os.system("sudo chown -R  pi:pi	 "+G.logDir)
			if	not os.path.isdir(G.logDir):
				return

			f=open(G.logDir+G.program+".log","a")
			f.write((datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" "+msg+"\n").encode("utf8"))
			f.close()
			if permanentLog:
				f=open(G.homeDir+"permanentLog.log","a")
				f.write((datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+"	"+G.program+" "+msg+"\n").encode("utf8"))
				f.close()

				
		except	Exception, e:
			print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),"toLog",G.program, " in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)
			if unicode(e).find("No space left on device") >-1:
				fixoutofdiskspace()
			if unicode(e).find("Read-only file system:") >-1:
				os.system("sudo reboot")

	if doPrint:
			try:
				print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+ "  "+G.program+" "+msg
			except	Exception, e:
				print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),G.program, " in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)
	return 



def checkrclocalFile():
	
	replace = False
	if not os.path.isfile("/etc/rc.local"):	 # does not exist
		replace = True
	else:
		f = open("/etc/rc.local","r")
		if "python" not in f.read():
			replace=True
		f.close()

	if replace:
		os.system("sudo cp "+G.homeDir+"rc.local.default /etc/rc.local ")
		os.system("sudo chmod a+x /etc/rc.local")
		toLog(-1, u"replacing rc.local file" )


	return 



def fixoutofdiskspace():
	print " trying to fix oput of disk space" 
	
	try:	os.system("rm "+G.logDir+"*")
	except: pass
	try:	os.system("logrotate -f /etc/logrotate.d/rsyslog; sleep 1; logrotate -f /etc/logrotate.d/rsyslog")
	except: pass

#################################
def pgmStillRunning(pgmToTest) :
	try :
		cmd = "ps -ef | grep '" + pgmToTest + "' | grep -v grep"
		#print cmd
		ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
		lines = ret.split("\n")
		for line in lines :
			#print " testing  if pgm is still running	>>"+pgmToTest+"<<  >>"+	 line+"<<"
			#toLog(-1,	" testing  if pgm is still running	 "+pgmToTest+"	"+	line)
			if len(line) < 10 : continue
			#print "kill found"
			return True
	except	Exception, e :
		toLog(-1, u"pgmStillRunning in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
	#print "ps	failed for "+pgmToTest
	#os.system("ps -ef | grep python")
	return False


#################################
def checkParametersFile(defaultParameters, force=False):
		inp,inpRaw,lastRead2 = doRead(lastTimeStamp=1)
		#print "checking parameters file"
		if len(inpRaw) < 100 or force:
			# restore old parameters"
			os.system("cp " +G.homeDir+defaultParameters+"	" +G.homeDir+"parameters")
			os.system("touch " +G.homeDir+"temp\touchFile")
			restartMyself(reason="bad parameter...	file.. restored" , doPrint=True)

#################################
def doRead(inFile=G.homeDir+"temp/parameters",lastTimeStamp=""):
	t=0
	try:
		if not os.path.isfile(inFile):
			if lastTimeStamp != "": 
				return "","error",t
			return "","error"
				
		t = os.path.getmtime(inFile)
		if lastTimeStamp != "": 
			if lastTimeStamp == t: return "","",t
		
		f=open(inFile,"r")
		inRaw =f.read().strip('"')
		inp =json.loads(inRaw)
	except	Exception, e :
			toLog(1, u"doRead in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			try:
				if not os.path.isfile(inFile):
					if lastTimeStamp != "": 
						if lastTimeStamp == t: return "","error",t
					return "","error"
				time.sleep(0.1)
				f=open(inFile,"r")
				inRaw =f.read()
				inp =json.loads(inRaw).strip('"')
			except	Exception, e :
				if inFile == G.homeDir+"temp/parameters":
					toLog(1, u"doRead in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
				try:	f.close()
				except: 
					pass
				if lastTimeStamp != "":
					return "","error", t
				return "","error"

	try:	f.close()
	except: pass
	if lastTimeStamp != "":
		return inp, inRaw, t
	return inp, inRaw

#################################
def setNetwork(mode):
	f=open(G.homeDir+"temp/networkMODE","w")
	f.write(mode) 
	f.close()
#################################
def clearNetwork():
	if os.path.isfile(G.homeDir+"temp/networkMODE"):
		os.system("rm "+G.homeDir+"temp/networkMODE") 
#################################
def getNetwork():
	try:
		if os.path.isfile(G.homeDir+"temp/networkMODE"):
			f=open(G.homeDir+"temp/networkMODE","r")
			rr = f.read()
			f.close() 
			if rr =="off": 
				return "off"
			if rr =="on": 
				return "on"
			if rr =="clock": 
				return "clock"
			return "on"
	except:
		pass
	return "on"


#################################
def getGlobalParams(inp):

		sensors ={}
		if "debugRPI"				in inp:	 G.debug=					 int(inp["debugRPI"]["debugRPISENSOR"])
		if "ipOfServer"				in inp:	 G.ipOfServer=					(inp["ipOfServer"])
		if "myPiNumber"				in inp:	 G.myPiNumber=					(inp["myPiNumber"])
		if "authentication"			in inp:	 G.authentication=				(inp["authentication"])
		if "sendToIndigoSecs"		in inp:	 G.sendToIndigoSecs=	   float(inp["sendToIndigoSecs"])
		if "passwordOfServer"		in inp:	 G.passwordOfServer=			(inp["passwordOfServer"])
		if "userIdOfServer"			in inp:	 G.userIdOfServer=				(inp["userIdOfServer"])
		if "portOfServer"			in inp:	 G.portOfServer=				(inp["portOfServer"])
		if "indigoInputPORT"		in inp:	 G.indigoInputPORT=			 int(inp["indigoInputPORT"])
		if "IndigoOrSocket"			in inp:	 G.IndigoOrSocket=				(inp["IndigoOrSocket"])


		if u"rebootCommand"			in inp:	 G.rebootCommand=				(inp["rebootCommand"])
		if u"wifiOFF"				in inp:	 G.wifiOFF=						(inp["wifiOFF"])
		if G.networkType !="clockMANUAL" and  G.networkType!="":
			if u"networkType"			in inp:	 G.networkType=					(inp["networkType"])
		try:
			if u"deltaChangedSensor" in inp:  G.deltaChangedSensor=	   float(inp["deltaChangedSensor"])
		except: pass
		if u"shutDownPinOutput"		 in inp:  
			try:							  G.shutDownPinOutput=		 int(inp["shutDownPinOutput"])
			except:							  G.shutDownPinOutput=		-1

		if u"enableMuxI2C"		in inp:	 
			try:							  G.enableMuxI2C=			   int(inp["enableMuxI2C"])
			except:							  G.enableMuxI2C=			   -1
		else:
											  G.enableMuxI2C=			   -1
			 
		if G.wifiType != "normal": # is ad-hoc
			G.networkType = "clock"
		return 

#################################
def cleanUpSensorlist(sens, theSENSORlist):
		deldevID={}		   
		for devId in theSENSORlist:
			if devId not in sens:
				deldevID[devId]=1
		for dd in  deldevID:
			del theSENSORlist[dd]
		if len(theSENSORlist) ==0: 
			####exit()
			pass
		return theSENSORlist

#################################
def doReboot(tt,text,cmd=""):
	if cmd =="":
		doCmd= G.rebootCommand
	else: 
		doCmd = cmd

	toLog(-1," rebooting / shutdown "+doCmd+"  "+ text,permanentLog=True,doPrint=True)


	time.sleep(0.1)
	os.system("sudo sync") 
	time.sleep(tt)

	if cmd =="":
		os.system(doCmd)
		time.sleep(20)
		os.system("sudo sudo reboot -f") 
		os.system("sudo sync;sudo halt") 
	else:
		os.system(doCmd)
		time.sleep(20)
		os.system("sudo sync;sudo halt") 

	doRebootThroughRUNpinReset()

#################################
def doRebootThroughRUNpinReset():
	if G.shutDownPinOutput >0:
		GPIO.setup(G.shutDownPinOutput, GPIO.OUT) 
		GPIO.output(G.shutDownPinOutput, True)
		GPIO.output(G.shutDownPinOutput, False)


#################################
def sendRebootHTML(reason,reboot=True):
	sendURL(sendAlive="reboot",text=reason)
	if reboot:
	   doReboot(1.," reboot at " +str(datetime.datetime.now())+"  "	 +reason)
	else:
	   doReboot(1.," shut down at " +str(datetime.datetime.now())+"	 " +reason,cmd="shutdown -h now ")
	
	return



#################################
def setUpRTC(useRTCnew):
	global initRTC
	try:
		if initRTC:
			initRTC=False
	except:
			initRTC=True
		

	if useRTCnew not in ["ds3231","ds1307"]: useRTCnew ="0"

	if	G.useRTC == useRTCnew and not initRTC: # return if not first and no change
		return
	
	if useRTCnew == "ds3231":
		if findString("dtoverlay=i2c-rtc,ds3231",	"/boot/config.txt") == 2: # already there ?
			G.useRTC = useRTCnew
			return 
		
		uncommentOrAdd("/sbin/hwclock -s|| echo \"hwclock not working\"","/etc/rc.local",	 before="(sleep ")
		removefromFile("dtoverlay=i2c-rtc,ds1307", "/boot/config.txt")
		uncommentOrAdd("dtoverlay=i2c-rtc,ds3231", "/boot/config.txt", before="")
		removefromFile("if [ -e /run/systemd/system ]", "/lib/udev/hwclock-set",nLines=3)
		os.system("apt-get -y remove fake-hwclock")
		doReboot(30,"installing HW clock" ,cmd="")

	elif useRTCnew == "ds1307":
		if findString("dtoverlay=i2c-rtc,ds1307",	"/boot/config.txt") == 2: # already done ?
			G.useRTC = useRTCnew
			return 
		uncommentOrAdd("/sbin/hwclock -s|| echo \"hwclock not working\"","/etc/rc.local",	 before="(sleep ")
		removefromFile("dtoverlay=i2c-rtc,ds3231", "/boot/config.txt")
		uncommentOrAdd("dtoverlay=i2c-rtc,ds1307", "/boot/config.txt", before="")

		# in /lib/udev/hwclock-set ADD # infront of 
		#if [ -e /run/systemd/system ] ; then
		# exit 0
		#fi
		removefromFile("if [ -e /run/systemd/system ]", "/lib/udev/hwclock-set",nLines=3)
		os.system("sudo chmod a+x  /lib/udev/hwclock-set")
		os.system("apt-get -y remove fake-hwclock")
		doReboot(30,"installing HW clock" ,cmd="")

	else:
		if (findString("dtoverlay=i2c-rtc,ds1307",	 "/boot/config.txt") != 2 and 
			findString("dtoverlay=i2c-rtc,ds3231",	 "/boot/config.txt") != 2 ) : # already done ?
			G.useRTC = useRTCnew
			return 

		removefromFile("dtoverlay=i2c-rtc,ds3231",	"/boot/config.txt")
		removefromFile("dtoverlay=i2c-rtc,ds1307",	"/boot/config.txt")
		removefromFile('/sbin/hwclock -s|| echo "hwclock not working"',			 "/etc/rc.local" )
		# in /lib/udev/hwclock-set REMOVE # infront of 
		#if [ -e /run/systemd/system ] ; then
		# exit 0
		#fi
		os.system("cp "+G.homeDir+"hwclock.set.nohwclock /lib/udev/hwclock-set") 
		os.system("sudo chmod a+x  /lib/udev/hwclock-set")
		os.system("apt-get -y install fake-hwclock") 

		doReboot(30," .. reason de installing HW clock" ,cmd="")

#################################
def getIPNumber():
	G.ipAddress=""
	ipAddressRead=""
	if G.networkType  not in G.useNetwork or G.wifiType !="normal": return 0
	try:
		f=open(G.homeDir+"ipAddress","r")
		ipAddressRead = f.read().strip(" ").strip("\n").strip(" ")
		f.close()
		if len(ipAddressRead) > 7:
			G.ipAddress = ipAddressRead
			toLog(1, "found IP number "+G.ipAddress)
			#print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" "+G.program +"	 found IP number "+G.ipAddress
			return 0
	except	Exception, e :
		toLog(-1, u"getIPNumber in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
	toLog(-1,u"getIPNumber getIPnumber : no ip number defined")
	print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" "+G.program +"	did not find IP number "+G.ipAddress
			
	return 1

################################
def gethostnameIP():
	ret = subprocess.Popen("hostname -I " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip()
	return	ret.strip().split(" ")

################################
def getIPCONFIG():
	wifi0IP = ""
	eth0IP = ""
	G.wifiEnabled = False
	G.eth0Enabled = False
	try:
		retIfconfig = subprocess.Popen("/sbin/ifconfig " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip()
		if retIfconfig.find("wlan0   ") > -1 : G.wifiEnabled= True
		if retIfconfig.find("eth0   ") > -1 : G.eth0Enabled= True

		if retIfconfig.find("wlan0:") > -1 : G.wifiEnabled= True
		if retIfconfig.find("eth0:") > -1 :	 G.eth0Enabled= True


		ifConfigSections = retIfconfig.split("\n\n")
		for ii in range(len(ifConfigSections)):
			if ifConfigSections[ii].find("eth0  ") > -1 or ifConfigSections[ii].find("eth0:") > -1:
				if ifConfigSections[ii].find("inet addr:") >-1:
					eth0IP= ifConfigSections[ii].split("inet addr:")
					if len(eth0IP) > 1:
						eth0IP = eth0IP[1].split(" ")[0]

				elif ifConfigSections[ii].find("inet ") >-1:
					eth0IP= ifConfigSections[ii].split("inet ")
					if len(eth0IP) > 1:
						eth0IP = eth0IP[1].split(" ")[0]


			if ifConfigSections[ii].find("wlan0  ") > -1 or ifConfigSections[ii].find("wlan0:") > -1:
				if	ifConfigSections[ii].find("inet addr:") >-1:
					wifiIP= ifConfigSections[ii].split("inet addr:")
					if len(wifiIP) > 1:
						wifi0IP = wifiIP[1].split(" ")[0]
				elif ifConfigSections[ii].find("inet ") >-1:
					wifi0IP= ifConfigSections[ii].split("inet ")
					if len(wifi0IP) > 1:
						wifi0IP = wifi0IP[1].split(" ")[0]
					
	except	Exception, e:
		toLog(-1,u"error in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
	return eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled

################################
def whichWifi():
	ret = subprocess.Popen("/sbin/ifconfig" ,shell=True,stdout=subprocess.PIPE).communicate()[0]
	if	ret.find(":192.168.5.5 ") >-1:
		G.wifiType="adhoc"
		return "adhoc"
	G.wifiType="normal"
	return "normal"

#################################
def prepAdhocWifi():
	killOldPgm(-1,"neopixel.py",param1="",param2="")
	print "prepAdhoc Wifi: starting wifi servers as clock  no password "
	os.system('cp /etc/network/interfaces  '+G.homeDir+'interfaces-old')
	os.system('cp '+G.homeDir+'interfaces-WIFI-clock /etc/network/interfaces')
	time.sleep(0.2)
	os.system('sudo reboot now')
	return

#################################
def resetWifi():
	print " resetting wifi to default for next re-boot"
	os.system('cp '+G.homeDir+'interfaces-DEFAULT-clock /etc/network/interfaces')
	return	



################################
def getIPNumberMaster(quiet=False):
	G.ipAddress								  = ""
	ipAddressRead							  = ""
	retcode									  = 0
	ipHostname								  = gethostnameIP()		   
	eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = getIPCONFIG()
	changed = False
	if G.wifiOFF.upper() !="ON": 
		wifi0IP,eth0IP,changed = setWLANoffIFeth0ON(wifi0IP,eth0IP)

	try:
		try:
			f=open(G.homeDir+"ipAddress","r")
			ipAddressRead = f.read().strip(" ").strip("\n").strip(" ")
			f.close()
		except:
			ipAddressRead = ""

		if not quiet: toLog(-1," IP find::::	wifiIP >>"+ wifi0IP+ "<<;	eth0IP: >>"+eth0IP+ "<<;   hostnameIP >>"+ unicode(ipHostname)+ "<<;   ipAddressRead >>"+ ipAddressRead+"<<",doPrint=True)

		if testDNS() >0:
			   retcode=1

# simple cases:
		if len(ipAddressRead) > 7  and ipAddressRead in [wifi0IP,eth0IP] and  testPing(ipIn=ipAddressRead) ==0:
				G.ipAddress = ipAddressRead
				return retcode , changed
				

		if len(ipHostname) ==1	and ipHostname[0] in [wifi0IP,eth0IP] and  testPing(ipIn=ipHostname[0]) ==0:
				if ipHostname[0] != ipAddressRead:
					writeIPtoFile(ipHostname[0],reason="hostname gives differnt that stored IP#")
				G.ipAddress = ipHostname[0]
				return retcode , changed
			
		if len(ipHostname) >1 and len(ipHostname[1])> 6:
			for ii in range(len(ipHostname)):
				if ipHostname[ii] in [wifi0IP,eth0IP]:
					if testPing(ipIn=ipHostname[ii]) ==0:
						if ipAddressRead != ipHostname[ii]:
							writeIPtoFile(ipHostname[ii],reason="2 host names")
						G.ipAddress = ipHostname[0]
						return retcode , changed

	except	Exception, e:
		toLog(-1,u"U.getIPNumberMaster error in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)

	toLog(-1,u"U.getIPNumberMaster bad IP number ...  ipHostname >>"+unicode(ipHostname)+"<<  old from file ipAddressRead>>"+ ipAddressRead+"<< not in sync with ifconfig output: wifi0IP>>"+ wifi0IP+"<<;	eth0IP>>"+eth0IP,doPrint=True  )
	return 2, changed

def setWLANoffIFeth0ON(wifi0IP,eth0IP):
	if wifi0IP == "": return wifi0IP,eth0IP,False
	if eth0IP  == "": return wifi0IP,eth0IP,False

	testIP = G.ipOfServer.split(".")
	if len(testIP) !=4: return wifi0IP,eth0IP,False
	testIP = testIP[0]+"."+testIP[1]+"."

	if eth0IP.find(testIP) > -1:
		if wifi0IP.find(testIP) > -1:
			toLog(-1,u"switching wifi off as ethernet is connected",doPrint=True)
			cmd="ifconfig wlan0 down "
			os.system(cmd) 
			cmd="iwconfig wlan0 txpower off"
			os.system(cmd) 
			return "",eth0IP, True
	return wifi0IP,eth0IP, False
		

def writeIPtoFile(ip,reason=""):
	G.ipAddress = ip
	f=open(G.homeDir+"ipAddress","w")
	f.write(G.ipAddress.strip(" ").strip("\n").strip(" "))
	f.close()
	toLog(-1," writing ip number to file >>" +G.ipAddress+"<<  reason:"+reason,doPrint=True)
	return	



#################################
def testPing(ipIn=""):
	if (G.networkType  not in G.useNetwork and ipIn =="")  or G.wifiType !="normal": return 0
	try:
		if pgmStillRunning("installLibs.py"): 
			G.ipConnection = time.time()
			return -1

		if ipIn =="": ipToPing = G.ipOfServer
		else:		  ipToPing = ipIn
		
		# IPnumber setup?
		ipi =  (ipToPing.strip()).split(".")
		if len(ipi) !=4: 
			toLog(-1, "testPing bad ip number to ping >>"+ str(ipToPing)+"<<" )
			return 1
		for ii in ipi:
			try: int(ii)
			except: 
				toLog(-1, "testPing bad ip number for ping >>"+ str(ipToPing)+"<<" )
				return 1
		

		for ii in range(4):
			cmd= "/bin/ping	 -c 1 -W 1 " + ipToPing+" >/dev/null 2>&1"
			ret = os.system(cmd)  # send max 4 packets, wait 1 secs between each and stop if one gets back
			#print cmd, "ret=", ret,"=="
			if int(ret) == 0:
				G.ipConnection = time.time()
				return 0
		if ipIn !="":
			return 1

		toLog(1,"testPing can not connect to server: "+ ipToPing+"	ping code: "+unicode(ret) )
			
		return 2

	except	Exception, e :
		toLog(-1, u"testPing in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
	return 2



#################################
def getSerialDEV():	   
	version = subprocess.Popen("cat /proc/device-tree/model" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	# return eg 
	# Raspberry Pi 2 Model B Rev 1.1
	#return "/dev/ttyAMA0"
	serials = subprocess.Popen("ls -l /dev/ | grep serial" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	# should return something like:
	#lrwxrwxrwx 1 root root			  5 Apr 20 11:17 serial0 -> ttyS0
	#lrwxrwxrwx 1 root root			  7 Apr 20 11:17 serial1 -> ttyAMA0


	if version[0].find("Raspberry") ==-1:
		toLog(-1,"cat /proc/device-tree/model something is wrong... "+unicode(version) )
		print "cat /proc/device-tree/model something is wrong... "+unicode(version) 
		time.sleep(10)
		exit(1)
		
	if version[0].find("Pi 3") == -1 and version[0].find("Pi Zero") == -1:	# not RPI3
		sP = "/dev/ttyAMA0"

		### disable and remove tty usage for console
		subprocess.Popen("systemctl stop serial-getty@ttyAMA0.service" ,	shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("systemctl disable serial-getty@ttyAMA0.service" , shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		if serials[0].find("serial0 -> ttyAMA0") ==-1 :
			toLog(-1, "pi2 .. wrong serial port setup  can not run missing in 'ls -l /dev/' : serial0 -> ttyAMA0")
			print		"pi2 .. wrong serial port setup	 can not run missing in 'ls -l /dev/' : serial0 -> ttyAMA0"
			time.sleep(10)
			exit(1)

	else:# RPI3
		sP = "/dev/ttyS0"

		### disable and remove tty usage for console
		subprocess.Popen("systemctl stop serial-getty@ttyS0.service" ,	  shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("systemctl disable serial-getty@ttyS0.service" , shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		if serials[0].find("serial0 -> ttyS0")==-1:
			U.toLog(-1, "pi3 .. wrong serial port setup	 can not run missing in 'ls -l /dev/' : serial0 -> ttyS0")
			print		"pi3 .. wrong serial port setup	 can not run missing in 'ls -l /dev/' : serial0 -> ttyS0"
			time.sleep(10)
			exit(1)
	return sP


#################################
def geti2c():
	try:
		i2cChannels=[]
		ret= subprocess.Popen("i2cdetect -y 1",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if ret[1] is not  None and ret[1].find("No such file or directory") > 0:
			i2cChannels=["i2c.ERROR:.no.such.file....redo..SSD?"]
		else:
			lines = ret[0].split("\n")
			i2cChannels=[]
			ii=-1
			for line in	 lines:
				if line.find(":") ==-1: continue  # skip first line
				ii+=1
				line = line[3:]
				line = line.replace("--","    ")
				val = [line[jj:jj+3] for jj in range(0,3*16,3)]
				kk = -1
				if len(val)>0:
					for v in val:
						kk+=1
						if v !="   ":
							v16=ii*16 + kk
							if v.find("UU")>-1: v16 =-v16
							i2cChannels.append(v16) # converted
		return i2cChannels
	except	Exception, e :
		toLog(-1, u"geti2c in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
	return []

#################################
def whichHCI():
	ret	   = subprocess.Popen("hciconfig ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()#################################	 BLE iBeaconScanner	 ----> end
	# try again, sometimes does not return anything
	if len(ret[0]) < 5:
		time.sleep(0.5)
		ret	  = subprocess.Popen("hciconfig ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()#################################	BLE iBeaconScanner	----> end
		print "U.whichHCI, hciconfig 2. try: ",ret
		
	lines = ret[0].split("\n")
	hci={}
	for ll in range(len(lines)):
		if lines[ll].find("hci")>-1:
			bus = lines[ll].split("Bus: ")[1]
			hciNo = lines[ll].split(":")[0]
			hci[hciNo] = {"bus":bus, "numb":int(hciNo[3:])}
			if lines[ll+1].find("BD Address:")>-1:
				mm=lines[ll+1].strip().split(" ")
				if len(mm)>2:
					hci[hciNo]["BLEmac"]=  mm[2]
		#hci1:	Type: Primary  Bus: UART
		#	BD Address: B8:27:EB:D4:E3:35  ACL MTU: 1021:8	SCO MTU: 64:1
		#	UP RUNNING 
		#	RX bytes:2850 acl:21 sco:0 events:141 errors:0
		#	TX bytes:5581 acl:20 sco:0 commands:115 errors:0
		#
		#hci0:	Type: Primary  Bus: USB
		#	BD Address: 5C:F3:70:69:69:FB  ACL MTU: 1021:8	SCO MTU: 64:1
		#	UP RUNNING 
		#	RX bytes:11143 acl:0 sco:0 events:379 errors:0
		#	TX bytes:4570 acl:0 sco:0 commands:125 errors:0
	if hci =={}: print lines
	return	hci				  




#################################
def sendURL(data={},sendAlive="",text="", wait=True,squeeze=True):
	try:
			if (G.networkType  not in G.useNetwork or G.wifiType !="normal") or	 (getNetwork() =="off" or getNetwork() =="clock") : 
				G.lastAliveSend	 = time.time()
				G.lastAliveSend2 = time.time()
				return

			os.system("echo x > "+ G.homeDir+"temp/sending")

			data["program"]	  = G.program
			data["pi"]		  = str(G.myPiNumber)
			data["ipAddress"] = G.ipAddress.strip(" ").strip("\n").strip(" ")
			if len(text) >0: 
				data["text"] = text

			if (time.time() - G.tStart > 40):#dont send time if we have just started .. wait for ntp etc to get time 
				tz = time.tzname[1]
				if len(tz) < 2:	 tz = time.tzname[0]
				data["ts"]			= {"time":round(time.time(),2),"tz":tz}
			
			if	sendAlive == "reboot":
				name = "pi_IN_Alive"
				data["reboot"] =True
				G.lastAliveSend2 = time.time()
				
			elif  sendAlive == "alive":
				name = "pi_IN_Alive"
				G.lastAliveSend2 = time.time()
				
			else:
				name = "pi_IN_"+str(G.myPiNumber)
 

			if G.IndigoOrSocket =="indigo":
						var = "/variables/"+name
						data0 = json.dumps(data)
						if squeeze: 
							data0 = data0.replace(" ","")
						cmd=[]
						cmd.append("/usr/bin/curl")
						if G.userIdOfServer =="" or G.authentication =="none":
								pass  # no id password ...
						else:
							if G.authentication == "basic":	   
								cmd.append("--user")
								cmd.append(G.userIdOfServer+":"+G.passwordOfServer)
							else:
								cmd.append("-u")
								cmd.append(G.userIdOfServer+":"+G.passwordOfServer)
								cmd.append("--digest")
						cmd.append("-X")
						cmd.append("PUT")
						cmd.append("-d")
						cmd.append("value="+data0)
						cmd.append("http://"+G.ipOfServer+":"+G.portOfServer+var)  ##+" > /dev/null 2>&1 &"
						#print cmd
						toLog(0,"msg: " + unicode(cmd)+"\n" )
						if wait:
							ret = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
							if ret[0].find("This resource can be found at")==-1:
								toLog(-1,"curl err:"+ ret[0])
								toLog(-1,"curl err:"+ ret[1])
							else:
								os.system("echo '"+G.program+":	 "+data0+"' > "+ G.homeDir+"temp/messageSend")
						else:
							cmd.append(" &")
							subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
							os.system("echo '"+G.program+":	 "+data0+"' > "+ G.homeDir+"temp/messageSend")

			else:
						
						sendMSG = False
						for ii in range(3): # try max 3 times.
							data0 = json.dumps(data)
							if squeeze: 
								data0 = data0.replace(" ","")
							sendData= str(len(data0))+"x-6-a"+name+"x-6-a"+data0
							try:
								soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
								soc.settimeout(5.)
								soc.connect((G.ipOfServer, G.indigoInputPORT))
								len_sent = soc.send(sendData)
								time.sleep(0.1)
								response = soc.recv(512)

								if response.find("ok") >-1:
									os.system("echo '"+G.program+":	 "+data0+"' > "+ G.homeDir+"temp/messageSend")
									sendMSG =True
									break
								else:# try again
									toLog(0, "Sending  again: send bytes: " + str(len(data0)) + " ret MSG>>"+  response+"<<")
									try:	soc.close()
									except: pass
									time.sleep(3.)

							except	Exception, e:
								toLog(-1, u"sendURL in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
								try:	soc.shutdown(socket.SHUT_RDWR)
								except: pass
								try:	soc.close()
								except: pass
								time.sleep(3.)

							# redo time stamp, at it is delayed .. 
							tz = time.tzname[1]
							if len(tz) < 2:	 tz = time.tzname[0]
							data["ts"]			= {"time":round(time.time(),2),"tz":tz}

						if sendMSG:
									toLog(0,"msg: " + unicode(sendData)+"\n" )
						else:
									toLog(0,"msg not send "+sendData)
						try:	soc.shutdown(socket.SHUT_RDWR)
						except: pass
						try:	soc.close()
						except: pass
			#print " send time ",time.time()- tStart



				
	except	Exception, e:
		toLog(-1, u"sendURL in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

	os.system("rm  "+ G.homeDir+"temp/sending > /dev/null 2>&1 ")
	G.lastAliveSend = time.time()

	return 
		
######## setup and use	multiplexer if requested
def muxTCA9548A(sens,i2c=""):

	if i2c == "":
		if "i2cAddress" in sens:
			i2c = int(sens["i2cAddress"])
		else:
			i2c = 0
	else:
		pass
	
	if G.enableMuxI2C == -1:		 
						return	i2c
	if u"useMuxChannel" not in sens: 
						return	i2c
	try:				channel = int(sens[u"useMuxChannel"])
	except:				return	i2c
	if channel == -1:	return	i2c
	channelBit	= (1 << channel )
	
	if G.enableMuxBus == "":
		import smbus
		#print "muxTCA9548A",channel,  G.enableMuxI2C
		G.enableMuxBus = smbus.SMBus(1)
		#print "enableMuxBus read byte:", G.enableMuxBus.read_byte(G.enableMuxI2C)

	G.enableMuxBus.write_byte(G.enableMuxI2C,channelBit)
	#print "enableMuxBus read byte:", G.enableMuxBus.read_byte(G.enableMuxI2C)
	time.sleep(0.01)
	
	return i2c# G.enableMuxI2C+channel
def muxTCA9548Areset():
	if G.enableMuxBus !="":
		G.enableMuxBus.write_byte(G.enableMuxI2C,0x0)
	
#################################
def removeOutPutFromFutureCommands(pin, devType):
	try:
		if os.path.isfile(G.homeDir+"execcommands.current"):
			f=open(G.homeDir+"execcommands.current","r")
			input = f.read()
			if len(input) < 3: return
			execcommands=json.loads(input)
			f.close()
			rmEXEC={}
			for channel in execcommands:
				toLog(2,"removing  testing channel "+str(channel) +"  "+ str(execcommands[channel]) )
				if channel != str(pin): continue
				if "device" in execcommands[channel] and devType == execcommands[channel]["device"]:
					toLog(2,"removing testing channel device found" )
					if "startAtDateTime" in execcommands[channel] and time.time() - float(execcommands[channel]["startAtDateTime"]) > 2: 
						if execcommands[channel]["command"]	 not in ["analogWrite","up","down"]:
							toLog(2,"removing testing channel time expired" )
							rmEXEC[channel]=1
							toLog(2,"removing removing channel "+str(channel)) 
			for channel in rmEXEC:
				del execcommands[channel]
			f=open(G.homeDir+"execcommands.current","w")
			f.write(json.dumps(execcommands))
			f.close()
	except	Exception, e:
		toLog(-1, u"removeOutPutFromFutureCommands in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			os.system("sudo reboot")

			
#################################
def echoLastAlive(sensor):
	try: 
		tt=time.time()
		if time.time() - G.lastAliveEcho > 60.: 
			G.lastAliveEcho = tt
			os.system("echo	 "+str(tt)+" > "+G.homeDir+"temp/alive."+sensor)
	except:
			G.lastAliveEcho = tt
			os.system("echo	 "+str(tt)+" > "+G.homeDir+"temp/alive."+sensor)
	return 

			
#################################
def calcStartTime(data,timeStamp):
	if timeStamp in data:
		try:
			startAtDateTime =  float(data[timeStamp]) 
			if startAtDateTime < 100000000.:
				return time.time()+ startAtDateTime
			return startAtDateTime
		except:
			pass
	return time.time()

#################################
def checkNowFile(xxx):
	return doFileCheck(xxx, "now")
#################################
def checkResetFile(xxx):
	return doFileCheck(xxx, "reset")

#################################
def checkNewCalibration(xxx):
	return doFileCheck(xxx, "startCalibration")

#################################
def doFileCheck(xxx,extension):
	try:
		if os.path.isfile(G.homeDir +"temp/"+ xxx+"."+extension):
			try:
				os.remove(G.homeDir +"temp/"+ xxx+"."+extension)
			except:
				pass
			return	True
		return False
	except	Exception, e:
		toLog(-1, u"doFileCheck in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

#################################
def makeDATfile(sensor, data):
	try:
		if G.debug > 1	or G.networkType  not in G.useNetwork :
			f=open(G.homeDir+"temp/"+sensor+".dat","w")
			f.write(json.dumps(data))
			f.close()
	except	Exception, e:
		toLog(-1, u"makeDATfile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			os.system("sudo reboot")

#################################
def checkresetCount(IPCin):
	IPC = copy.copy(IPCin)
	try:
		if not os.path.isfile(G.homeDir + G.program+".reset"): 
			#print "checkresetCount no file"
			return IPC
		try:
			f = open(G.homeDir + G.program+".reset", "r")
			inp = f.read()
			f.close()
			os.remove(G.homeDir + G.program+".reset")
		except	Exception, e:
			try: os.remove(G.homeDir + G.program+".reset")
			except: pass
			inp=""
		try:
			if len(inp) < 3: 
				return IPC
			inp = json.loads(inp)
		except	Exception, e:
			toLog(-1, u"checkresetCount in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
			return IPC
		#print "checkresetCount doing reset", inp
		for p in inp:
			pin = int(p)
			if pin > 99:  continue
			if pin < 0:	  continue
			IPC[pin] = 0
			#print "checkresetCount pin=", pin
		writeINPUTcount(IPC)
	except	Exception, e:
		toLog(-1, u"checkresetCount in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
	#print "checkresetCount pin=", IPC[15:25]
	return IPC
	
######################################
def readINPUTcount():
		IPC = [0 for i in range(100)]
		try:
			f=open(G.homeDir+G.program+".count","r")
			IPC =json.loads(f.read())
			f.close()
		except:
			pass
		for p in range(100):
			try:
				int(IPC[p])
			except:
				IPC[p] =0
				
		if len(IPC) < 10:
			IPC = [0 for i in range(100)]
		writeINPUTcount(IPC)
		return IPC


######################################
def writeINPUTcount(IPC):
	try:
		f=open(G.homeDir+G.program+".count","w")
		f.write(json.dumps(IPC))
		f.close()
	except	Exception, e:
		if unicode(e).find("Read-only file system:") >-1:
			os.system("sudo reboot")
			
######################################
def readRainStatus():
		try:
			f=open(G.homeDir+G.program+".status","r")
			status =json.loads(f.read())
			f.close()
			return status
		except:
			pass
		return {}

######################################
def writeRainStatus(status):
	try:
		f=open(G.homeDir+G.program+".status","w")
		f.write(json.dumps(status))
		f.close()
	except	Exception, e:
		if unicode(e).find("Read-only file system:") >-1:
			os.system("sudo reboot")

######################################
def doActions(data0,lastGPIO, sensors, sensor,sensorType="INPUT_",gpio="",theAction=""): # theAction can be 1 2 3 4 5
	try:			   
		if sensor not in sensors: return
		for devId in sensors[sensor]:
			sens = sensors[sensor][devId]
			if (("actionUP"				in sens and	 sens["actionUP"]	!="") or 
				("actionDOWN"			in sens and	 sens["actionDOWN"] !="") or
				("action1"				in sens and	 sens["action1"]	!="") or
				("action2"				in sens and	 sens["action2"]	!="") or
				("action3"				in sens and	 sens["action3"]	!="") or
				("action4"				in sens and	 sens["action4"]	!="") or
				("action5"				in sens and	 sens["action5"]	!="") or
				("actionDoubleClick"	in sens and	 sens["actionDoubleClick"] !="") or
				("actionLongClick"		in sens and	 sens["actionLongClick"] !="")		): 
				action= ""
				try:
					#print data0
					if devId in data0[sensor]:
						if theAction!="": # sensorType must be key for value to test 
									action = theAction
						else:
							for inputN in data0[sensor][devId]:
								if inputN.find(sensorType)>-1:
									new = data0[sensor][devId][inputN]
									nn = int(inputN.split("_")[1])
									if lastGPIO[nn] !="" and  lastGPIO[nn] !=new: 
										if new !="0":
											action = "UP"
										else:
											action = "DOWN"
									lastGPIO[nn] = new
									break

							
						
				except	Exception, e:
					 toLog(-1 , u"doActions in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint =True)
				
				if	action !="": 
					if "action"+action in sens and sens["action"+action] !="":
						if	action =="UP" or action =="DOWN" or action =="1" or action =="2" or action =="3" or action =="4" or action =="5":

							toLog(1, u"action"+action+": " +sens["action"+action])
							checkIfrebootAction(sens["action"+action])
							os.system(sens["action"+action])

					if "actionDoubleClick" in sens and sens["actionDoubleClick"] !="":
						manageActions(sens["actionDoubleClick"],waitTime=3,click=action,aType="actionDoubleClick", devId=devId)

					if "actionLongClick" in sens and sens["actionLongClick"] !="":
						manageActions(sens["actionLongClick"],waitTime=3,click=action,aType="actionLongClick", devId=devId)

		############ local action  end #######
	except	Exception, e:
		toLog(-1, u"doActions in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), doPrint =True)
	return lastGPIO



#################################
def manageActions(action,waitTime=3,click="UP", aType="actionDoubleClick",devId=""):
	try:
		tt = time.time()
		if action == "-loop-":
			if	G.actionDict=={}: 
				return
			#print " manage actions:" ,action,waitTime,click, aType,devId
			for aa in G.actionDict:
				removeDevs={}
				for dd in G.actionDict[aa]:
					if	  G.actionDict[aa][dd]["aType"] =="actionDoubleClick" and tt - G.actionDict[aa][dd]["timerStart"] >= G.actionDict[aa][dd]["waitTime"]:
						removeDevs[dd] =1
				for dd in removeDevs:
					del G.actionDict[aa][dd]
					
			removeActions={}
			for aa in G.actionDict:
				if len(G.actionDict[aa]) ==0:
					removeActions[aa] =1
			for aa in removeActions:
				del G.actionDict[aa]
			return

		if action not in G.actionDict:
			G.actionDict[action] ={devId:{"timerStart":tt,"waitTime":waitTime,"click":click, "aType":aType}}
			return
		if devId not in G.actionDict[action]:
			G.actionDict[action][devId]={"timerStart":tt,"waitTime":waitTime,"click":click, "aType":aType}
			return


		if aType=="actionDoubleClick"  and aType == G.actionDict[action][devId]["aType"]:
			if click == G.actionDict[action][devId]["click"]:
				if tt - G.actionDict[action][devId]["timerStart"] < 0.2 :
						del G.actionDict[action]
				if tt - G.actionDict[action][devId]["timerStart"] < G.actionDict[action][devId]["waitTime"]:
					toLog(1," executing action: "+unicode(action)) 
					checkIfrebootAction(action)
					os.system(action)
			return

		elif aType=="actionLongClick" and aType == G.actionDict[action][devId]["aType"]:
			if click != G.actionDict[action][devId]["click"] :
				if tt - G.actionDict[action][devId]["timerStart"] > G.actionDict[action][devId]["waitTime"]	 :
					checkIfrebootAction(action)
					toLog(1," executing action: "+unicode(action)) 
					os.system(action)
				else  :
					del G.actionDict[action][devId]
			else:
				del G.actionDict[action][devId]
			return
		
	except	Exception, e:
		toLog(-1, u"manageActions in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
	return

#################################
def checkIfrebootAction(action):
	# display.py might stop shutdown from going through, need to kill first
	try:
		if action.find("shutdown") >-1 or  action.find("reboot") >-1 :	
			toLog(-1," executing action: "+unicode(action),doPrint=True) 
			killOldPgm(-1,"display.py")
			time.sleep(0.2)
	except	Exception, e:
		toLog(-1, u"checkIfrebootAction in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
	return


################################


def sendi2cToPlugin():
	try:
		i2c= geti2c()
		ret = subprocess.Popen("/opt/vc/bin/vcgencmd measure_temp" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		try:	temp = ret.split("=")[1].split("'")[0]
		except: temp = 0
		sendURL(data={"i2c":i2c,"temp":temp},sendAlive="alive")
	except	Exception, e :
		toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
	return 

#################################
def testBad(newX, lastX, inXXX):

	xxx = inXXX
	try:
		if newX.find("bad") ==-1:
			if lastX.find("bad") ==-1:
				xxx = max(xxx, abs( float(lastX) - float(newX) )/ max(0.1, abs(float(lastX) + float(newX)) )   )
			else:
				xxx = 99999.
		else:
			if lastX.find("bad") >-1:
				xxx = 0
			else:
				xxx = 99999.
	except : xxx = 99999.
	return xxx



#################################
def checkIfAliveNeedsToBeSend():
	try:
		tt = time.time()
		lastSend = 0
		if os.path.isfile(G.homeDir+"temp/messageSend"):
			try:
				lastSend = os.path.getmtime(G.homeDir+"temp/messageSend")
			except:
				pass
		if time.time() - lastSend> 330:	 # do we have to send alive signal to plugin?
			sendURL(sendAlive=True )
	except	Exception, e:
		U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),permanentLog=True)
	return



#################################
def doWeNeedToStartSensor(sensors, sensorsOld, selectedSensor="",sensorType=""):
	if selectedSensor =="":
		sensorUp ={}
		for sensor in sensors:
			if sensor.find("INPUTgpio") >-1:					   continue
			if sensorType !=""	and sensor.find(sensorType) ==-1:  continue
			if sensor not  in sensorsOld:							sensorUp[sensor] = 1; continue
			for devId in sensors[sensor] :
					if devId not in sensorsOld[sensor] :			sensorUp[sensor] = 1; continue
					for prop in sensors[sensor][devId] :
						if prop not in sensorsOld[sensor][devId] :	sensorUp[sensor] = 1; break
						if sensors[sensor][devId][prop] != sensorsOld[sensor][devId][prop]:
																	sensorUp[sensor] = 1; break
		for sensor in  sensorsOld:
			if sensor.find("INPUTgpio") >-1:					   continue
			if sensorType !=""	and sensor.find(sensorType) ==-1:  continue
			if sensor not  in sensors:								sensorUp[sensor] = 1; continue
			for devId in sensorsOld[sensor] :
					if devId not in sensors[sensor] :				sensorUp[sensor] = 1; continue
					for prop in sensorsOld[sensor][devId] :
						if prop not in sensors[sensor][devId] :		sensorUp[sensor] = 1; break

		return sensorUp
	
	else:

		if selectedSensor not in sensors:	 return -1
		if selectedSensor not in sensorsOld: return 1

		for devId in sensors[selectedSensor] :
				if devId not in sensorsOld[selectedSensor] :			return 1
				for prop in sensors[selectedSensor][devId] :
					if prop not in sensorsOld[selectedSensor][devId] :	return 1
					if sensors[selectedSensor][devId][prop] != sensorsOld[selectedSensor][devId][prop]:
						return 1
   
		for devId in sensorsOld[selectedSensor]:
				if devId not in sensors[selectedSensor] :				return 1
				for prop in sensorsOld[selectedSensor][devId] :
					if prop not in sensors[selectedSensor][devId] :		return 1

		return 0
#################################
def doWeNeedToStartGPIO(sensors, sensorsOld):
	oneFound = False
	for sensor in sensors:
		if sensor.find("INPUTgpio") ==1: continue
		oneFound= True
		if sensor not  in sensorsOld:							return True
		for devId in sensors[sensor] :
				if devId not in sensorsOld[sensor] :			return True
				for prop in sensors[sensor][devId] :
					if prop not in sensorsOld[sensor][devId] :	return True
					if prop =="gpio":
						for pp in prop:
							if pp not in sensorsOld[sensor][devId][prop]: return True
							if sensors[sensor][devId][prop][pp] != sensorsOld[sensor][devId][prop][pp]: return True
					elif sensors[sensor][devId][prop] != sensorsOld[sensor][devId][prop]: return True

	for sensor in  sensorsOld:
		if sensor.find("INPUTgpio") ==-1: continue
		if sensor not  in sensors:								return True
		for devId in sensorsOld[sensor] :
				if devId not in sensors[sensor] :				return True
				for prop in sensorsOld[sensor][devId] :
					if prop not in sensors[sensor][devId] :		return True
					if prop =="gpio":
						for pp in prop:
							if pp not in sensors[sensor][devId][prop]: return True
							if sensors[sensor][devId][prop][pp] != sensorsOld[sensor][devId][prop][pp]: return True
					elif sensors[sensor][devId][prop] != sensorsOld[sensor][devId][prop]: return True
	if oneFound: return False
	return True
 
 
 
#################################
###for mag sensors calibration ##
#################################
		
def magCalibrate(theClass, force = False, calibTime=10):
		'''We need to calibrate the sensor
		otherwise we'll be going round in circles.

		basically we need to go round in circles and average out
		the min and max values, that is then the offset (?)
		https://github.com/kriswiner/MPU-6050/wiki/Simple-and-Effective-Magnetometer-Calibration

		Keep rotating the sensor in all direction until the output stops updating
		'''
	   
		calib = theClass.calibrations
		if force or sum([abs(calib[x]) for x in calib]) ==0 :
			reading = theClass.getRawMagData()
			if max([abs(reading[x]) for x in range(3)]) < 4000:	 # no overflow
				calib['maxX'] = reading[0]
				calib['minX'] = reading[0]
				calib['maxY'] = reading[1]
				calib['minY'] = reading[1]
				calib['maxZ'] = reading[2]
				calib['minZ'] = reading[2]

		toLog(1,'magCalibrate -2 ')
		toLog(0,'Starting Debug, please rotate the magnetometer about all axis')
		theList={"maxX":0,"minX":0,"maxY":0,"minY":0,"maxZ":0,"minZ":0}
		calibruns= int(calibTime/0.1)
		for ii in range(calibruns):
			try:
				change = False
				reading = theClass.getRawMagData()
				if max([abs(reading[x]) for x in range(3)]) < 4000: #  no overflow
					# X calibration
					for mm in theList:
						ll = theList[mm]
						if mm.find("max")>-1:
							if reading[ll] > calib[mm]:
								calib[mm] = reading[ll]
								change = True
						else:
							if reading[ll] < calib[mm]:
								calib[mm] = reading[ll]
								change = True
					if change:
						toLog(1,'magCalibrate Update: '+unicode(calib))
				time.sleep(0.1)
			except:
				break
		saveCalibration(theClass.calibrationFile, calib)
		theClass.magOffset = setOffsetFromCalibration(theClass.calibrations)
		return True

#################################
def saveCalibration(theClass, calibrationFile, calib):
		toLog(1,'saveCalibration:  enableCalibration = '+unicode(calib))
		try:
			f=open(theClass.calibrationFile, 'w')
			calib = json.dumps(calib, sort_keys=True)
			f.write(calib)
			f.close()
		except Exception, e:
			toLog(-1,'saveCalibration unable to save calibration: {0}'.format(e))
			if unicode(e).find("Read-only file system:") >-1:
				os.system("sudo reboot")

#################################
def setOffsetFromCalibration(calib):
		try:
			offset=[]
			offset[0] = (calib['minX'] + calib['maxX'])/2
			offset[1] = (calib['minY'] + calib['maxY'])/2
			offset[2] = (calib['minZ'] + calib['maxZ'])/2
			toLog(1,'theClass.magOffset '+unicode(offset))
			return offset
		except	Exception, e:
			toLog(-1, u"setOffsetFromCalibration in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		return [0,0,0]

#################################
def loadCalibration(calibrationFile):
		try:
			f=open(calibrationFile, 'r')
			calib = f.read()
			calibrations = json.loads(calib)
			f.close()
		except Exception, e:
			toLog(-1,'Unable to open  calibration file : {0}'.format(e))
			return {}
		return calibrations

#################################
def magDataCorrected(theClass,data):
		out=[0 for ii in range(len(data))]
		for ii in range(len(data)):
			out[ii] = (data[ii]	 - theClass.magOffset[ii] ) / max(0.01,theClass.magDivider )
		return out

#################################
def setMAGParams(theClass, magOffset="",magDivider="", enableCalibration="", declination="", offsetTemp=""):
		try:
			if magOffset !="":
				theClass.magOffset = copy.copy(magOffset)
		except: pass
		try:
			if magDivider !="":
				theClass.magDivider = copy.copy(magDivider)
		except: pass
		try:
			if declination !="":
				theClass.declination = copy.copy(declination)
		except: pass
		try:
			if enableCalibration !="":
				theClass.enableCalibration = copy.copy(enableCalibration)
		except: pass
		try:
			if offsetTemp !="":
				theClass.offsetTemp = copy.copy(offsetTemp)
		except: pass


#################################
def getEULER(v,theClass=""):
		'''Experimentally put roll and pitch back in to
		get some tilt compenstation
		https://gist.github.com/timtrueman/322555
		roll	== x-z
		pitch	== y-z
		v =[x,y,z]
		'''
		if v == "" :
			if theClass == "": return [0,0,0] 
			v = theClass.getRawMagData()
			v = theClass.magDataCorrected(v)
		
		if theClass == "":
			decl =	0
		else: 
			decl =	theClass.declination
		
		roll		= math.atan2(v[0],v[2])
		pitch		= math.atan2(v[1],v[2])
		heading		= math.atan2(v[1],v[0])
		if heading < 0:
			heading += 2 * math.pi
		heading = math.degrees(heading) + decl
		
		return [heading, roll, pitch]
		#### this more complex 
		#compX	 = x * math.cos(pitch) + y * math.sin(roll) * math.sin(pitch) + z * math.cos(roll) * math.sin(pitch)
		#compY	 = y * math.cos(roll)  - z * math.sin(roll)
		#heading = math.atan2(-compY, compX)

#################################
def getMAGReadParameters( sens,devId):
		changed = ""
		try:
			G.i2cAddress = ""	 
			if "i2cAddress" in sens: 
				G.i2cAddress = int(sens["i2cAddress"])
		except:
			G.i2cAddress = ""	 

		try:
			magOffsetX = 0
			if "magOffsetX" in sens: 
				G.magOffsetX= float(sens["magOffsetX"])
		except:
			magOffsetX = 0
		try:
			magOffsetY = 0
			if "magOffsetY" in sens: 
				magOffsetY= float(sens["magOffsetY"])
		except:
			magOffsetY = 0
		try:
			magOffsetZ = 0
			if "magOffsetZ" in sens: 
				magOffsetZ= float(sens["magOffsetZ"])
		except:
			magOffsetZ = 0
		G.magOffset[devId] =[magOffsetX,magOffsetY,magOffsetZ]
		
		try:
			G.magDivider[devId] = 1
			if "magDivider" in sens: 
				G.magDivider[devId]= float(sens["magDivider"])
		except:
			G.magDivider[devId] = 1

		try:
			G.magResolution[devId] = 1
			if "magResolution" in sens: 
				G.magResolution[devId]= int(sens["magResolution"])
		except:
			G.magResolution[devId] = 1

		try:
			G.declination[devId] = 0
			if "declination" in sens: 
				G.declination[devId]= float(sens["declination"])
		except:
			G.declination[devId] = 0
			
		try:
			G.deltaX[devId] = 5
			if "deltaX" in sens: 
				G.deltaX[devId]= float(sens["deltaX"])/100.
		except:
			G.deltaX[devId] = 5

		try:
			G.sensorRefreshSecs = 100	 
			xx = sens["sensorRefreshSecs"].split("#")
			G.sensorRefreshSecs = float(xx[0]) 
		except:
			G.sensorRefreshSecs = 100  
			  
		try:
			G.enableCalibration[devId]=False	
			G.enableCalibration[devId] = sens["enableCalibration"]=="1"
		except:
			G.enableCalibration[devId] = False	  

		try:
			G.displayEnable = sens["displayEnable"]
			if "displayEnable" in sens: 
				G.displayEnable = sens["displayEnable"]
		except:
			G.displayEnable = False	   

		try:
			G.sensorLoopWait = 2
			if "sensorLoopWait" in sens: 
				G.sensorLoopWait= float(sens["sensorLoopWait"])
		except:
			G.sensorLoopWait = 2

		try:
			G.minSendDelta = 5.
			if "minSendDelta" in sens: 
				G.minSendDelta= float(sens["minSendDelta"])/100.
		except:
			G.minSendDelta = 5.

		try:
			G.offsetTemp[devId]= 0
			if "offsetTemp" in sens: 
				G.offsetTemp[devId]= float(sens["offsetTemp"])
		except:
			G.offsetTemp[devId] = 0

		try:
			if "accelerationGain" in sens: 
				if G.accelerationGain !="" and	float(G.accelerationGain) != float(sens["accelerationGain"]):
					changed +="accelerationGain",
				G.accelerationGain= float(sens["accelerationGain"])
		except:
			pass
		try:
			if "magGain" in sens: 
				if G.magGain !="" and  float(G.magGain) != float(sens["magGain"]):
					changed +="magGain",
				G.magGain= float(sens["magGain"])
		except:
			pass
	
		return changed

#################################
def checkMGACCGYRdata(new,oldIN,dims,coords,testForBad,devId,sensor,quick,
		sumTest={"dim":"","limits":[1000000,-100000]},singleTest={"dim":"","coord":"","limits":[1000000,-100000]}):
		old=copy.copy(oldIN)
		try:
			data={"sensors":{sensor:{devId:{}}}}
			retCode="ok"
			if new =="": return old
			if unicode(new).find("bad") >-1:
				G.badCount1+=1
				G.sensorWasBad = True
				if G.badCount1 < 5: 
					toLog(0," bad sensor")
					data["sensors"][sensor][devId][testForBad]="badSensor"
					sendURL(data)
				for mm in dims:
					for x in coords:
						old[devId][mm][x]=-50000
				if G.badCount1 > 10: 
						restartMyself(reason=" empty sensor reading, need to restart to get sensors reset",doPrint=False)
				return old
			G.badCount1 =0
			if testForBad not in new: 
				#print "reject 2"
				return old
			if new[testForBad] =="":  
				G.badCount5 +=1
				if G.badCount5 < 5: 
					toLog(0," bad sensor")
				if G.badCount5 > 15: 
					data["sensors"][sensor][testForBad]="badSensor"
					sendURL(data)
					restartMyself(reason=" empty sensor reading, need to restart to get sensors reset",doPrint=False)
				return old
			G.badCount5 =0
			if singleTest["dim"]!="":
					if ( abs(new[singleTest["dim"]][singleTest["coord"]]) >	 singleTest["limits"][1] or 
						 abs(new[singleTest["dim"]][singleTest["coord"]]) <= singleTest["limits"][0]): 
						toLog(0, singleTest["dim"]+"-"+singleTest["coord"]+" out of bounds, ignoring: " +unicode(new))
						G.badCount4+=1
						if G.badCount4 > 10: 
							restartMyself(reason=unicode(singleTest)+"- wrong, need to restart to get sensors reset",doPrint=False)
						#print "reject 3"
						return old
			G.badCount4 =0
			if sumTest["dim"]!="":
				dd= sumTest["dim"]
				SUM = sum(	[abs(new[dd][x]) for x in new[dd] ]	 ) 
				if SUM <=sumTest["limits"][0] or SUM > sumTest["limits"][1]:
					toLog(0, unicode(sumTest)+" sum of values bad " + unicode(SUM))
					G.badCount3 +=1
					if G.badCount3 > 10: 
						restartMyself(reason=unicode(sumTest)+"	 bad, need to restart to get sensors reset",doPrint=False)
					#print "reject 4"
					return old
			G.badCount3 =0
			
			totalABS	 =0
			totalDelta	 =0
			nTotal		 =0
			for mm in dims:
				for xx in coords:
					#print bb, xx ,values[bb][xx]
					try: v = float(new[mm][xx])
					except: continue
					totalABS += abs(v)
					if abs(v) < G.threshold[devId]: continue # no noise stuff
					totalDelta	+= abs(old[devId][mm][xx]-v)/(max(0.01,abs(v)+abs(old[devId][mm][xx])))
					nTotal +=1

			#toLog(-1,unicode(totalDelta)+"	 "+unicode(totalABS)+"	"+ unicode(nTotal)+"  "+unicode(deltaX))
			if nTotal > 1 and totalDelta/nTotal > max(0.01,G.deltaX[devId]): 
				#print " sendNow", total/nTotal , deltaX[devId]
				retCode = "sendNow" 
			if nTotal > 1 and totalABS ==0: 
				G.badCount2+=1
				if G.badCount2 > 5: 
					restartMyself(reason=unicode(dims)+" values identival 5 times need to restart to get sensors reset",doPrint=False)
				#print "reject 5"
				return old
				
			else:
				G.badCount2 =0
			if G.sensorWasBad:
				restartMyself(reason=unicode(dims)+" back from bad sensor, restart",doPrint=False)
			data["sensors"][sensor][devId] = new
			#print	 time.time() - G.lastAliveSend , abs(G.sensorRefreshSecs) , quick , retCode=="sendNow" , time.time() - G.lastAliveSend , G.minSendDelta
			if (  (time.time() - G.lastAliveSend > abs(G.sensorRefreshSecs) or quick or retCode=="sendNow" )  and (time.time() - G.lastAliveSend > G.minSendDelta) ):
					#print	"sending", unicode(data)
					sendURL(data)
					old[devId]	= copy.copy(new)
   
		except	Exception, e: 
			toLog(-1, u"checkMGACCGYRdata in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
			retCode="exception"
		if retCode =="ok":
			makeDATfile(G.program, data)

		return old





#################################
def applyOffsetNorm(vector, params, offset, norm):
	out =copy.copy(vector)
	for ii in range(len(vector)):
		if offset[ii] in params:
			try:	out[ii] -= params[offset[ii]]
			except: pass
		if norm	 in params and params[norm]!="":
			try:	out[ii] /= float(params[norm])
			except: pass
	return out

#################################
import io
import fcntl

class simpleI2cReadWrite:
	I2C_SLAVE=0x0703

	def __init__(self, i2cAddress, bus):
		self.fr = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
		self.fw = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)
		fcntl.ioctl(self.fr, self.I2C_SLAVE, i2cAddress)
		fcntl.ioctl(self.fw, self.I2C_SLAVE, i2cAddress)

	def write(self, bytes):
		self.fw.write(bytes)

	def read(self, bytes):
		return self.fr.read(bytes)

	def close(self):
		self.fw.close()
		self.fr.close()
		
#################################
def findString(string,file):
	if string =="": return 0

	try:
		f=open(file,"r")
		text0=f.read()
		text =text0.split("\n")
		f.close()
		for line in text:
			if line.find(string) ==0:
				return 2
			if line.find("#"+string) ==0: 
				return 1
		return 0
	except	Exception, e:
		toLog(-1, u"findString in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			os.system("sudo reboot")
	return 3


#################################
def checkIfInFile(stringItems,file):
	if stringItems =="" or stringItems ==[]: return 0
	if stringItems[0] == "": return 0
	nItems		= len(stringItems)
	try:
		f=open(file,"r")
		text0=f.read()
		text =text0.split("\n")
		f.close()
		for line in text:
			lineItems =line.split(" ")
			nFound	= 0
			for item in stringItems:
				if item =="": nFound+=1
				else:
					for item2 in lineItems:
						if item == item2:
							nFound +=1
							break
			if nFound == nItems: return 0
		return 1
	except	Exception, e:
		toLog(-1, u"findString in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			os.system("sudo reboot")



#################################
def uncommentOrAdd(string,file,before="",nLines=1):
	if string =="": return 0

	try:
		f=open(file,"r")
		text0=f.read()
		text =text0.split("\n")
		f.close()
		found = 0
		for line in text:
			if line.find(string) ==0:
				found =2
				return 0
			if line.find("#"+string) ==0: 
				found =1
				break
		if found ==0:
			if before !="" and text0.find(before) >-1:
				done=False
				f=open(file,"w")
				for line in text:
					if line.find(before) ==0 and not done:
						f.write(string+"\n")
						done = True
					if len(line)> 0: f.write(line+"\n") # remove empty lines
				f.close()
				return 1

			text0+="\n"+string+"\n"
			f=open(file,"w")
			f.write(text0.replace("\n\n","\n"))
			f.close()
			return 1
			
		if found ==1:
			iLines =0
			f=open(file,"w")
			for line in text:
				if line.find(string)>-1:
					f.write(line[1:]+"\n")
					iLines +=1
					continue
				if iLines < nLines and iLines >0:
					iLines+=1
					if line.find("#")==0:
						line = line[1:]
				if len(line)> 0: 
					f.write(line+"\n") # remove empty lines
			f.close()
			return 1
	except	Exception, e:
		toLog(-1, u"uncommentOrAdd in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			os.system("sudo reboot")


#################################
def removefromFile(string,file,nLines =1):
	if string =="": return 0
	stringItems =string.split()
	nItems		= len(stringItems)
	iLines=0
	try:
		f	  = open(file,"r")
		text0 = f.read()
		text  = text0.split("\n")
		f.close()
		out=""
		for line in text:
			lineItems = line.split()
			nFound	= 0
			for item in stringItems:
				if item =="": nFound+=1
				else:
					for item2 in lineItems:
						if item == item2:
							nFound +=1
							break
			if nFound == nItems: 
				continue
			out+=line+"\n"
		out = out.replace("\n\n","\n")
		if out != text0: 
			f=open(file,"w")
			f.write(out)
			f.close()
		return 0
	except	Exception, e:
		toLog(-1, u"removefromFile in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			os.system("sudo reboot")
	return 1	

#################################
def startNTP(mode=""):
	if mode == "simple": os.system("sudo /etc/init.d/ntp start ")
	else: os.system("sudo /etc/init.d/ntp stop ; sudo ntpd -q -g ; sudo /etc/init.d/ntp start ")
	
	testNTP()
	return

#  ntpStatus		   = "not started" #   / "started, working" / "started not working" / "temp disabled" / "stopped after not working"



#################################
def checkNTP(mode=""):
	if G.ntpStatus == "temp disabled": 
		return

	if G.networkStatus.find("local") >-1: 
		G.ntpStatus = "stopped after not working"
		return

	testNTP(mode="test")
	if G.ntpStatus == "started, not working": 
		stopNTP("final")
		return

	if G.ntpStatus == "stopped, after not working":
		startNTP()
		if G.ntpStatus == "started, not working": 
			stopNTP("final")

	return

#################################
def testNTP(mode=""):
	if not pgmStillRunning("/usr/sbin/ntpd "):
		if mode == "temp":
			G.ntpStatus = "temp disabled"
		elif mode == "test":
			G.ntpStatus = "started not working"
		elif mode == "finalTest":
			G.ntpStatus = "stopped after not working"
		else:
			G.ntpStatus = "not started"
		#print "in testNTP",mode, G.ntpStatus
		return
	
	st = 0
	G.ntpStatus = "not started"
	ret = subprocess.Popen("/usr/bin/ntpq -p",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
	ret = ret.strip("\n")
	lines = ret.split("\n")
	if len(lines) < 1: 
		st = 1
	else:
		if lines[0].find("Connection refused") >-1:
			st	= 2
		else:		 
			if len(lines) < 3: 
				st = 3
			else:
				if lines[0].find("remote") >-1 and lines[0].find("refid") >-1:
					if lines[1].find("============")==-1:
						st = 5
					else:
						for line in lines[2:]:
							items = line.split()
							if len(items) > 5:
								st = 6
								break
				else:
					st = 4
								
	if st == 6:
		G.ntpStatus = "started, working"
	else:
		if mode == "temp":
			G.ntpStatus = "temp disabled"
		elif mode == "test":
			G.ntpStatus = "started, not working"
		elif mode == "finalTest":
			G.ntpStatus = "stopped, after not working"
		else:
			G.ntpStatus = "not started"
	#print "in testNTP",mode, G.ntpStatus, lines
	return

		

#################################
def stopNTP(mode=""):
	#print " stopping NTP, mode=", mode
	os.system("sudo /etc/init.d/ntp stop &")
	if mode =="":
		G.ntpStatus = "not started"
	elif mode == "temp":
		G.ntpStatus = "temp disabled"
	elif mode.find("final") >-1:
		G.ntpStatus = "stopped, after not working"
	return

################################
def testDNS():
	try:
		ret = subprocess.Popen("cat /etc/resolv.conf | grep nameserver" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip()
		if len(ret)< 5:	  return 1
		ret = ret.split("\n")
		if len(ret) ==0:  return 1
		for line in ret:
			ip = line.split("nameserver ")
			if len(ip) == 2 : 
				ret =testPing(ipIn=ip[1]) 
				if	ret ==0:
					#print	" DNS server reachable at:"+ip[1]
					toLog(1," DNS server reachable at:"+ip[1])
					return 0
				if ret ==-2:
					toLog(-1," still waiting for installLibs to finish",doPrint=True)
					time.sleep(30)
					return 1
	except	Exception, e:
		toLog(-1,u"testDNS error in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
	return 1

#################################
##networkStatus		  = "no"   # "no" = no network what so ever / "local" =only local cant find anything else/ "inet" = internet yes, indigo no / "indigoLocal" = indigo not internet / "indigoInet" = indigo with inetrnet
def testNetwork(force=False):
	global lasttestNetwork, rememberLineSystemLOG
	try: 
		ii = lasttestNetwork
	except: 
		lasttestNetwork=0
	
	tt = int(time.time())
	if (tt - lasttestNetwork < 180 ) and not force:
		return 
	lasttestNetwork = tt

	try:
		if len(G.ipOfServer) > 6:
			testIndigo = testPing(ipIn=G.ipOfServer)
		else:
			testIndigo =1
		testD	   = testDNS()

		if testIndigo == 0 and testD == 0:
			G.networkStatus = "indigoInet"
			#print "in testNetwork",testIndigo, testDNS, G.networkStatus
			return

		if testIndigo == 0 and testD != 0:
			G.networkStatus = "indigoLocal"
			#print "in testNetwork",testIndigo, testDNS, G.networkStatus
			return 
			
		if testIndigo != 0 and testD == 0:
			G.networkStatus = "Inet"
			#print "in testNetwork",testIndigo, testDNS, G.networkStatus
			return


		if testIndigo != 0 and testD != 0:
			G.networkStatus = "local"
			#print "in testNetwork",testIndigo, testDNS, G.networkStatus
			return 
	   

	
	except	Exception, e :
		toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
	G.networkStatus = "local"
	return 



