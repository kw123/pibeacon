#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 1.1
##
##	  --- utils 
#
#	 
import	sys, os, subprocess, math, copy
import	time, datetime, json
sys.path.append(os.getcwd())
import piBeaconGlobals as G
import socket
import urllib
import RPi.GPIO as GPIO

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
def setLogging():
	global logging, logger
	import logging
	import logging.handlers
	global streamhandler, permLogHandler

	# regular logfile 
	logging.basicConfig(level=logging.DEBUG, filename= G.logDir+"pibeacon.log",format='%(asctime)s %(module)-15s %(funcName)-20s L:%(lineno)d Lv:%(levelno)s %(message)s', datefmt='%y%m%d-%H:%M:%S')
	logger = logging.getLogger(__name__)

	 # permanent logfile in pibeacon directory only for serious restarts, in case log dir is ramdisk 
	permLogHandler = logging.handlers.WatchedFileHandler(G.homeDir+"permanentLog.log")
	permFormat = logging.Formatter('%(asctime)s %(module)-15s %(funcName)-20s L:%(lineno)d Lv:%(levelno)s %(message)s',datefmt='%Y%m%d-%H:%M:%S')
	permLogHandler.setFormatter(permFormat)
	permLogHandler.setLevel(logging.CRITICAL)
	logger.addHandler(permLogHandler)

	# console output 
	streamhandler = logging.StreamHandler()
	streamhandler.setLevel(logging.WARNING)
	streamformatter = logging.Formatter('%(asctime)s %(module)-15s %(funcName)-20s L:%(lineno)d Lv:%(levelno)s %(message)s',datefmt='%H:%M:%S')
	streamhandler.setFormatter(streamformatter)
	logger.addHandler(streamhandler)

	setLogLevel()

	G.loggerSet = True

#################################
def setLogLevel():
	global streamhandler, permLogHandler, logger 
	if G.debug !=0:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)

	permLogHandler.setLevel(logging.CRITICAL)
	streamhandler.setLevel(logging.WARNING)
	

#################################
def killOldPgm(myPID,pgmToKill,param1="",param2=""):
	try:
		#print "killOldPgm ",pgmToKill,str(myPID)
		cmd= "ps -ef | grep '"+pgmToKill+"' | grep -v grep"
		if param1 !="":
			cmd+= " | grep " +param1
		if param2 !="":
			cmd+= " | grep " +param2
		logger.log(10, "trying to kill " + cmd )

		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		lines=ret.split("\n")
		for line in lines:
			if len(line) < 10: continue
			items=line.split()
			pid=int(items[1])
			if pid == int(myPID): continue

			logger.log(10, "killing "+pgmToKill+" "+param1 +" "+param2)
			os.system("kill -9 "+str(pid))
	except Exception, e:
		logger.log(30, u"killOldPgm	in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

#################################
def restartMyself(param="", reason="", delay=1, doPrint= True):
	if doPrint: 
		logger.log(50, u"--- restarting --- "+param+"  "+ reason)
	else:
		logger.log(30, u"--- restarting --- "+param+"  "+ reason)

	time.sleep(delay)
	os.system("/usr/bin/python "+G.homeDir+G.program+".py "+ param+" &")
	time.sleep(10)

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
def toLog(lvl, msg, doPrint = False, permanentLog=False):
	if not G.loggerSet:
		setLogging()

	if lvl < G.debug:
		try:
			if G.program =="":
				G.Program = "unknown"
			if	not os.path.isdir(G.logDir):
				return

			f=open(G.logDir+"pibeacon.log","a")
			f.write( (  "{} {} L:{:2d}= {} \n".format(datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"), G.program.ljust(15), lvl, msg) ).encode("utf8") )
			f.close()
			if permanentLog:
				f=open(G.homeDir+"permanentLog.log","a")
				f.write( (  "{} {} L:{:2d}= {} \n".format(datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"), G.program.ljust(15), lvl, msg) ).encode("utf8") )
				f.close()

				
		except	Exception, e:
			f.write( (  "{} {} L:{:2d}= {} \n".format(datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"), G.program.ljust(15), lvl, msg) ).encode("utf8") )
			print ( ( "{} {} L:{:2d}= in Line {} has error={}".format(datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),G.program, lvl, sys.exc_traceback.tb_lineno, e ) ).encode("utf8") )
			if unicode(e).find("No space left on device") >-1:
				fixoutofdiskspace()
			if unicode(e).find("Read-only file system:") >-1:
				doReboot(0,"")

	if doPrint:
			try:
				print ( (  "{} {} L:{:2d}= {}".format(datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"), G.program.ljust(15), lvl, msg) ).encode("utf8") )
			except	Exception, e:
				print ( ( "{} {} L:{:2d}= in Line {} has error={}".format(datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),G.program, lvl, sys.exc_traceback.tb_lineno, e ) ).encode("utf8") )
	return 


#################################
def doRebootNow():
	doReboot(0,"",cmd="")




#################################
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
		logger.log(30, u"replacing rc.local file" )


	return 



#################################
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
			#logger.log(30,	"testing  if pgm is still running	 "+pgmToTest+"	"+	line)
			if len(line) < 10 : continue
			#print "kill found"
			return True
	except	Exception, e :
		logger.log(30, u"pgmStillRunning in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	#print "ps	failed for "+pgmToTest
	#os.system("ps -ef | grep python")
	return False


#################################
def checkParametersFile(defaultParameters, force=False):
		inp,inpRaw,lastRead2 = doRead(lastTimeStamp=1)
		#print "checking parameters file"
		if len(inpRaw) < 100 or force:
			# restore old parameters"
			os.system("cp "+G.homeDir+"parameters " +G.homeDir+"temp\parameters")
			os.system("touch " +G.homeDir+"temp\touchFile")
			print "lastRead2 >>", lastRead2, "<<"
			print "inpRaw >>", inpRaw, "<<"
			print "inp >>", inp, "<<"
			restartMyself(reason="bad parameter... file.. restored" , doPrint= True)

#################################
def doRead(inFile=G.homeDir+"temp/parameters", lastTimeStamp="", testTimeOnly=False, deleteAfterRead = False):
	if not G.loggerSet:
		setLogging()
	t=0
	if not os.path.isfile(inFile):
		if lastTimeStamp != "": 
			return "","error",t
		return "","error"

	if testTimeOnly:  return t
			
	t = os.path.getmtime(inFile)
	if lastTimeStamp != "": 
		if lastTimeStamp == t: 
			if testTimeOnly: return t
			else: 			 return "","",t
	if testTimeOnly:  return t
	
	inp, inRaw = readJson(inFile)
	if deleteAfterRead: os.remove(inFile)

	if inp =={}:
		if not os.path.isfile(inFile):
			if lastTimeStamp != "": 
				if lastTimeStamp == t: return "","error",t
			return "","error"
		time.sleep(0.1)
		inp, inRaw = readJson(inFile)
		if inp =={}:
			if inFile == G.homeDir+"temp/parameters":
				logger.log(20, u"doRead error empty file")
		if deleteAfterRead: os.remove(inFile)
		if lastTimeStamp != "":
			return "","error", t
		return "","error"

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
		try:
			if "debugRPI"				in inp:	 G.debug=				 int(inp["debugRPI"]["debugRPISENSOR"])
		except: pass
		if "ipOfServer"				in inp:	 G.ipOfServer=					(inp["ipOfServer"])
		if "myPiNumber"				in inp:	 G.myPiNumber=					(inp["myPiNumber"])
		if "authentication"			in inp:	 G.authentication=				(inp["authentication"])
		try:
			if "sendToIndigoSecs"		in inp:	 G.sendToIndigoSecs=	float(inp["sendToIndigoSecs"])
		except: pass
		if "passwordOfServer"		in inp:	 G.passwordOfServer=			(inp["passwordOfServer"])
		if "userIdOfServer"			in inp:	 G.userIdOfServer=				(inp["userIdOfServer"])
		if "portOfServer"			in inp:	 G.portOfServer=				(inp["portOfServer"])
		try:
			if "indigoInputPORT"		in inp:	 G.indigoInputPORT=		 int(inp["indigoInputPORT"])
		except: pass
		if "IndigoOrSocket"			in inp:	 G.IndigoOrSocket=				(inp["IndigoOrSocket"])
		if "BeaconUseHCINo"			in inp:	 G.BeaconUseHCINo=				(inp["BeaconUseHCINo"])
		if "BLEconnectUseHCINo"		in inp:	 G.BLEconnectUseHCINo=			(inp["BLEconnectUseHCINo"])
		try:
			if "rebootIfNoMessages"		in inp:	 G.rebootIfNoMessages=	 int(inp["rebootIfNoMessages"])
		except: pass

		if u"rebootCommand"			in inp:	 G.rebootCommand=				(inp["rebootCommand"])


		if u"wifiEth"				in inp:	 
			xxx = inp["wifiEth"]
			if len(xxx) == 2 and "eth0" in xxx and "wlan0" in xxx: 
				if xxx != G.wifiEthOld:
					G.wifiEth = xxx
					G.wifiEthOld = G.wifiEth 

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
		setLogLevel()
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

	logger.log(50," rebooting / shutdown "+doCmd+"  "+ text)
	os.system("echo 'rebooting / shutdown' > "+G.homeDir+"temp/rebooting.now")


	time.sleep(0.1)
	os.system("sudo sync") 
	time.sleep(tt)


	if doCmd.find("halt") >-1 or doCmd.find("shut") >-1:
		try: os.system("sudo killall pigpiod &")
		except: pass
		try: GPIO.cleanup() 
		except: pass
		time.sleep(0.1)

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
def checkifRebooting():
	if os.path.isfile(G.homeDir+"temp/rebooting.now"): return True
	return False

#################################
def resetRebootingNow():
	if os.path.isfile(G.homeDir+"temp/rebooting.now"):
		os.system( "sudo rm "+G.homeDir+"temp/rebooting.now")


#################################
def doRebootThroughRUNpinReset():
	if G.shutDownPinOutput >1:
		os.system("echo 'rebooting / shutdown' > "+G.homeDir+"temp/rebooting.now")
		time.sleep(5) 
		GPIO.setup(G.shutDownPinOutput, GPIO.OUT) 
		GPIO.output(G.shutDownPinOutput, True)
		GPIO.output(G.shutDownPinOutput, False)


#################################
def sendRebootHTML(reason,reboot=True):
	sendURL(sendAlive="reboot",text=reason)
	if reboot:
	   doReboot(3," reboot at " +str(datetime.datetime.now())+"  "    +reason)
	else:
	   doReboot(3.," shut down at " +str(datetime.datetime.now())+"   " +reason,cmd="sudo killall python; wait 1; shutdown -h now ")
	
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
		if findString("dtoverlay=i2c-rtc,ds3231", "/boot/config.txt") == 2: # already there ?
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
		uncommentOrAdd("/sbin/hwclock -s|| echo \"hwclock not working\"","/etc/rc.local", before="(sleep ")
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
		if (findString("dtoverlay=i2c-rtc,ds1307", "/boot/config.txt") != 2 and 
			findString("dtoverlay=i2c-rtc,ds3231", "/boot/config.txt") != 2 ) : # already done ?
			G.useRTC = useRTCnew
			return 

		removefromFile("dtoverlay=i2c-rtc,ds3231","/boot/config.txt")
		removefromFile("dtoverlay=i2c-rtc,ds1307","/boot/config.txt")
		removefromFile('/sbin/hwclock -s|| echo "hwclock not working"', "/etc/rc.local" )
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
	###  if G.networkType  not in G.useNetwork or G.wifiType !="normal": return 0
	try:
		f=open(G.homeDir+"ipAddress","r")
		ipAddressRead = f.read().strip(" ").strip("\n").strip(" ")
		f.close()
		if isValidIP(ipAddressRead):
			G.ipAddress = ipAddressRead
			logger.log(20, "found IP number "+G.ipAddress)
			#print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" "+G.program +"	 found IP number "+G.ipAddress
			return 0
	except	Exception, e :
		logger.log(30, u"getIPNumber in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	logger.log(30,u"getIPNumber getIPnumber : no ip number defined")
			
	return 1


def isValidIP(ip0):
	ipx = ip0.split(u".")
	if len(ipx) != 4:
		return False
	else:
		for ip in ipx:
			try:
				if int(ip) < 0 or  int(ip) > 255: return False
			except:
				return False
	return True


################################
def gethostnameIP():
	ret = subprocess.Popen("hostname -I " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip()
	return	ret.strip().split(" ")

################################
def getIPCONFIG():
	wlan0IP 			= ""
	eth0IP 				= ""
	G.packetsTimeOld	= G.packetsTime
	G.eth0PacketsOld 	= G.eth0Packets
	G.eth0Packets 		= ""
	G.wlan0PacketsOld 	= G.wlan0Packets
	G.wlan0Packets 		= ""
	G.wifiEnabled 		= False
	G.eth0Enabled 		= False
	try:
		retIfconfig = subprocess.Popen("/sbin/ifconfig " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip()
		#eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
		#        inet 192.168.1.21  netmask 255.255.255.0  broadcast 192.168.1.255
		#        inet6 fe80::5b33:6d88:a2c6:34b  prefixlen 64  scopeid 0x20<link>
		#        ether b8:27:eb:00:30:7f  txqueuelen 1000  (Ethernet)
		#        RX packets 1010518  bytes 147369407 (140.5 MiB)
		#        RX errors 0  dropped 70  overruns 0  frame 0
		#        TX packets 81052  bytes 9516989 (9.0 MiB)
		#        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

		#lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
		#        inet 127.0.0.1  netmask 255.0.0.0
		#        inet6 ::1  prefixlen 128  scopeid 0x10<host>
		#        loop  txqueuelen 1000  (Local Loopback)
		#        RX packets 28688  bytes 6781920 (6.4 MiB)
		#        RX errors 0  dropped 0  overruns 0  frame 0
		#        TX packets 28688  bytes 6781920 (6.4 MiB)
		#        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0
		retwifiID = subprocess.Popen("/sbin/iwgetid " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip()

		if retIfconfig.find("lo") > -1: 
			packets 	= retIfconfig
			networks 	= retIfconfig 
			ifconfig 	= True
		else:
			packets = subprocess.Popen("cat /proc/net/dev " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip()
			#Inter-|   Receive                                                |  Transmit
			# face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
			#    lo: 6758900   28590    0    0    0     0          0         0  6758900   28590    0    0    0     0       0          0
			#  eth0: 147198293 1008371    0   69    0     0          0         0  9488704   80818    0    0    0     0       0          0
			networks = subprocess.Popen("ip -4 a show ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip()
			#1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
			#    inet 127.0.0.1/8 scope host lo
			#       valid_lft forever preferred_lft forever
			#2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
			#    inet 192.168.1.21/24 brd 192.168.1.255 scope global eth0
			#      valid_lft forever preferred_lft forever
			ifconfig = False
			
		if networks.find("wlan0   ") > -1: G.wifiEnabled= True
		if networks.find("wlan1   ") > -1: G.wifiEnabled= True
		if networks.find("eth0   ")  > -1: G.eth0Enabled= True

		if networks.find("wlan0:") > -1: G.wifiEnabled= True
		if networks.find("wlan1:") > -1: G.wifiEnabled= True
		if networks.find("eth0:")  > -1: G.eth0Enabled= True



		ifConfigSections = retIfconfig.split("\n\n")
		for ii in range(len(ifConfigSections)):
			if G.eth0Enabled:
				if ifConfigSections[ii].find("eth0  ") > -1 or ifConfigSections[ii].find("eth0:") > -1:
					if ifConfigSections[ii].find("inet addr:") >-1:
						eth0IP= ifConfigSections[ii].split("inet addr:")
						if len(eth0IP) > 1:
							eth0IP = eth0IP[1].split(" ")[0]

					elif ifConfigSections[ii].find("inet ") >-1:
						eth0IP= ifConfigSections[ii].split("inet ")
						if len(eth0IP) > 1:
							eth0IP = eth0IP[1].split(" ")[0]
					if  eth0IP.find("169.254.")>-1:
						G.eth0Enabled =False
						##os.system("sudo ifconfig eth0 down")

					if ifConfigSections[ii].find("RX packets ") >-1:
						eth0Packets = ifConfigSections[ii].split("RX packets ")
						if len(eth0Packets) ==2:
							G.eth0Packets = eth0Packets[1].split(" ")[0]
					# this happens when not connected 
							


			if G.wifiEnabled:
				if ifConfigSections[ii].find("wlan0  ") > -1 or ifConfigSections[ii].find("wlan0:") > -1 or \
				   ifConfigSections[ii].find("wlan1  ") > -1 or ifConfigSections[ii].find("wlan1:") > -1:
					if	ifConfigSections[ii].find("inet addr:") >-1:
						wlan0IP= ifConfigSections[ii].split("inet addr:")
						if len(wlan0IP) > 1:
							wlan0IP = wlan0IP[1].split(" ")[0]
					elif ifConfigSections[ii].find("inet ") >-1:
						wlan0IP= ifConfigSections[ii].split("inet ")
						if len(wlan0IP) > 1:
							wlan0IP = wlan0IP[1].split(" ")[0]

					if ifConfigSections[ii].find("RX packets ") >-1:
						wlan0Packets = ifConfigSections[ii].split("RX packets ")
						if len(wlan0Packets) ==2:
							G.wlan0Packets = wlan0Packets[1].split(" ")[0]
			if retwifiID.find(":") >-1:
				G.wifiID = retwifiID.split(":")[1]

	except	Exception, e:
		logger.log(30,u"error in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	G.packetsTime = time.time()
	return eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled

################################
def whichWifi():
	ret = subprocess.Popen("/sbin/ifconfig" ,shell=True,stdout=subprocess.PIPE).communicate()[0]
	#print "whichWifi", ret 
	if	ret.find("192.168.5.5 ") >-1:
		G.wifiType="adhoc"
		return "adhoc"
	G.wifiType="normal"
	return "normal"


################################
def checkWhenAdhocWifistarted():
	if not os.path.isfile(G.homeDir+"adhocWifistarted.time"): return -1
	xxx, ddd = readJson(G.homeDir+"adhocWifistarted.time")
	if  xxx =={}: return -1
	if "startTime" in xxx:
		return xxx["startTime"]
	return -1

#################################
def startAdhocWifi():
	try:
		logger.log(30, "prepAdhoc Wifi: starting wifi servers as clock  no password ")
		#os.system("sudo ifconfig wlan0 up")
		#os.system("sudo iwconfig wlan0 mode ad-hoc")
		#os.system('sudo iwconfig wlan0 essid "clock"')
		#os.system("sudo ifconfig wlan0 192.168.5.5 netmask 255.255.255.0")
		os.system("sudo cp /etc/network/interfaces "+G.homeDir+"interfaces-old")
		os.system("sudo cp "+G.homeDir+"interfaces-adhoc /etc/network/interfaces")
		writeJson(G.homeDir+"adhocWifistarted.time", {"startTime":time.time()})
		time.sleep(2)
		doReboot(0,"")
	except	Exception, e :
		logger.log(30, u"startAdhocWifi in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

#################################
def stopAdhocWifi():
	if  os.path.isfile(G.homeDir+"adhocWifistarted.time"): 
		os.system("sudo rm "+ G.homeDir+"adhocWifistarted.time")
	if os.path.isfile(G.homeDir+"temp/adhocWifi.stop"):
		os.system("sudo rm "+G.homeDir+"temp/adhocWifi.stop")
	if os.path.isfile(G.homeDir+"temp/adhocWifi.start"):
		os.system("sudo rm "+G.homeDir+"temp/adhocWifi.start")

	logger.log(30, "stopAdhocwebserver Wifi: stopping wifi, restoring old interface file and reboot")
	os.system('sudo cp '+G.homeDir+'interfaces-DEFAULT /etc/network/interfaces')
	os.system('sudo cp '+G.homeDir+'interfaces-DEFAULT '+G.homeDir+'interfaces')
	time.sleep(2)
	doReboot(0,"")
	return


#################################
def startWiFi():
	if G.wifiEth["wlan0"]["on"] == "dontChange": return 
	os.system("sudo rfkill unblock all")
	os.system("sudo wpa_cli -i wlan0 reconfigure ") 
	os.system("sudo wpa_cli -i wlan1 reconfigure ") 


	# new tool to be converted..  --> use ip instead if ifconfig 
	# ip link set dev wlan1 up
	time.sleep(0.5)
	os.system("sudo ifconfig wlan0 up ") 
	os.system("sudo ifconfig wlan1 up ") 
	os.system("sudo wpa_supplicant -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf & sudo dhcpcd wlan0")
	os.system("sudo wpa_supplicant -i wlan1 -c /etc/wpa_supplicant/wpa_supplicant.conf & sudo dhcpcd wlan1")
	os.system("sudo wpa_cli -i wlan0 reconfigure ") 
	os.system("sudo wpa_cli -i wlan1 reconfigure ") 
	time.sleep(0.5)
	os.system("sudo wpa_cli -i wlan0 reassociate ") 
	os.system("sudo wpa_cli -i wlan1 reassociate ") 
	G.wifiEnabled = True

	return
#################################
def startEth():
	if G.wifiEth["eth0"]["on"] == "dontChange": return 
	os.system("sudo rfkill unblock all")
	os.system("sudo ifconfig eth0 up ") 
	G.eth0Enabled = True
	return

#################################
def stopWiFi():
	if G.wifiEth["wlan0"]["on"] == "dontChange": return 
	os.system("sudo rfkill unblock all")
	os.system("sudo ifconfig wlan0 down ") 
	os.system("sudo ifconfig wlan1 down ") 
	# ip link set dev wlan1 down
	G.wifiEnabled = False
	return
#################################
def stopEth():
	if G.wifiEth["eth0"]["on"] == "dontChange": return 
	os.system("sudo rfkill unblock all")
	os.system("sudo ifconfig eth0 down ") 
	G.eth0Enabled = False
	return

#################################
def startwebserverINPUT(port, useIP="", force=False):
	if checkIfStartwebserverINPUT() and not force: return 
	outFile	= G.homeDir+"temp/webparameters.Input"
	ip = G.ipAddress
	if useIP !="":
		ip = useIP
	cmd = "sudo /usr/bin/python {}webserverINPUT.py  {} {} {} {}  > /dev/null 2>&1  &".format(G.homeDir, ip, port, outFile, G.sunDialActive)
	logger.log(30, "starting web server:{}".format(cmd) )
	if os.path.isfile(outFile):
		os.system('rm '+outFile)
	os.system(cmd)
	return

#################################
def stopwebserverINPUT():
	killOldPgm(-1,"/webserverINPUT.py")
	return

#################################
def startwebserverSTATUS(port,useIP="", force=False):
	if checkIfStartwebserverSTATUS() and not force: return 
	outFile	= G.homeDir+"temp/showOnwebserver"
	ip = G.ipAddress
	if useIP !="":
		ip = useIP
	cmd = "sudo /usr/bin/python {}webserverSTATUS.py  {} {} {}  > /dev/null 2>&1  &".format(G.homeDir, ip, port, outFile)
	logger.log(30, "starting web server:{}".format(cmd) )
	if os.path.isfile(outFile):
		os.system('rm '+outFile)
	os.system(cmd)
	return

#################################
def stopwebserverSTATUS():
	logger.log(30, "webserverSTATUS stop" )
	killOldPgm(-1,"/webserverSTATUS.py")
	return


#################################
def setStartwebserverINPUT():
	setFileTo(G.homeDir+"temp/webserverINPUT.start", "start")
	return
#################################
def setStopwebserverINPUT():
	setFileTo(G.homeDir+"temp/webserverINPUT.stop", "stop")
	return
#################################
def setStartwebserverSTATUS():
	setFileTo(G.homeDir+"temp/webserverSTATUS.start", "start")
	return
#################################
def setStopwebserverSTATUS():
	setFileTo(G.homeDir+"temp/webserverSTATUS.stop", "stop")
	return
#################################
def setStartAdhocWiFi():
	setFileTo(G.homeDir+"temp/adhocWifi.start", "start")
	return
#################################
def setStopAdhocWiFi():
	setFileTo(G.homeDir+"temp/adhocWifi.stop", "stop")
	return 
#################################
def setFileTo(file, value):
	os.system('echo  '+value+' > '+file)
	return 


#################################
def checkIfStartAdhocWiFi():
	return testForFile(G.homeDir+"temp/adhocWifi.start")

#################################
def checkIfStopAdhocWiFi():
	return testForFile(G.homeDir+"temp/adhocWifi.stop")

#################################
def checkIfStartwebserverINPUT():
	return testForFile(G.homeDir+"temp/webserverINPUT.start")

#################################
def checkIfwebserverINPUTrunning():
	if pgmStillRunning("/webserverSTATUS.py"): return True
	return False

#################################
def checkIfStopwebserverINPUT():
	return testForFile(G.homeDir+"temp/webserverINPUT.stop")

#################################
def checkIfStartwebserverSTATUS():
	return testForFile(G.homeDir+"temp/webserverSTATUS.start")

#################################
def checkIfStopwebserverSTATUS():
	return testForFile(G.homeDir+"temp/webserverSTATUS.stop")


#################################
def checkIfwebserverSTATUSrunning():
	if pgmStillRunning("/webserverSTATUS.py"): return True
	return False


#################################
def checkIfwebserverINPUTrunning():
	if pgmStillRunning("/webserverINPUT.py"): return True
	return False


#################################
def updateWebStatus(data):
	logger.log(10,"updating web status "+unicode(data))
	f=open(G.homeDir+"temp/showOnwebserver","w")
	f.write(data)
	f.close()
	return

#################################
def testForFile(fname):
	if os.path.isfile(fname):
		os.system('sudo rm '+fname)
		return True
	return False


#################################
def checkwebserverINPUT():
	try:
		newFile = False
		fName	= G.homeDir+"temp/webparameters.Input"
		if not  os.path.isfile(fName): return newFile
		data = {}
		ddd  = ""
		try:	
			data, ddd = readJson(fName)
		except: 
			pass
		os.system('rm '+fName)

		if len(ddd) > 3 and data !={}: 
			if "timezone" in data and len(data["timezone"]) >0:
				try:
					iTZ = int(data["timezone"])
					if iTZ !=99:
						writeTZ(iTZ=iTZ )
						newFile = True
				except	Exception, e :
					logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			if makeNewSupplicantFile(data):
				newFile = True
			return newFile

	except	Exception, e :
		logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return newFile



###############################
def writeTZ( iTZ = 99, cTZ="" ):
	try: 

		if cTZ =="": 
			try:
				iTZ = int(iTZ)
				if iTZ == 99: return 
				newTZ = G.timeZones[iTZ+12]
			except	Exception, e :
				logger.log(30, u"writeTZ in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				return 

		else: newTZ = cTZ
		oldTZ = subprocess.Popen('date +"%Z"' ,shell=True,stdout=subprocess.PIPE).communicate()[0].strip("\n").strip("\r")
		logger.log(30,"changing timezone from: {}  to: {}".format(oldTZ, newTZ) )
		if oldTZ != newTZ:
			logger.log(30,"changing timezone executing")
			if os.path.isfile("/usr/share/zoneinfo/"+newTZ):
				#  old
				#os.system('sudo rm /etc/localtime; sudo  cp /usr/share/zoneinfo/'+newTZ+' /etc/localtime')
				#  not needed...   ; sudo echo "TZ='+newTZ+'" >> /etc/timezone  ; sudo dpkg-reconfigure -f noninteractive tzdata' )
				# better just unlink and relink 
				os.system("sudo rm /etc/localtime")
				os.system("sudo ln -sf /usr/share/zoneinfo/{} /etc/localtime".format(newTZ) )
			else:
				logger.log(30,"error bad timezone:{}".foormat(newTZ) )
	except	Exception, e :
		logger.log(30, u"writeTZ in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return




#################################
def resetWifi(defaultFile= "interfaces-DEFAULT-clock"):
	logger.log(30,"resetting wifi to default for next re-boot")
	if os.path.isfile(G.homeDir+defaultFile): 
		os.system("cp "+G.homeDir+defaultFile+" /etc/network/interfaces")
	stopWiFi()
	time.sleep(0.2)
	startWiFi()
	return	

#################################
def restartWifi():
	logger.log(30,"restartWifi  w new config and wps files")
	stopWiFi()
	time.sleep(0.2)
	startWiFi()
	return	

#################################
def makeNewSupplicantFile(data):
	try:
		if "SSID"      not in data: 			return False
		if "passCode"  not in data: 			return False
		if len(data["SSID"]) < 1:				return False
		if len(data["passCode"]) < 1:			return False
		if data["SSID"] 	== "do not change": return False
		if data["SSID"] 	== "do+not+change": return False
		if data["passCode"] == "do not change": return False
		if data["passCode"] == "do+not+change": return False

		old = ""

		logger.log(30,"making new supplicant file with: " + unicode(data))
		if os.path.isfile("/etc/wpa_supplicant/wpa_supplicant.conf"): 
			os.system("cp  /etc/wpa_supplicant/wpa_supplicant.conf " +G.homeDir+"wpa_supplicant.conf-temp ")
			f = open(G.homeDir+"wpa_supplicant.conf-temp","r")
			old = f.read()
			f.close()
			if old.find('"'+data["SSID"]+'"') >-1 and  old.find('"'+data["passCode"]+'"') >-1: 
				logger.log(30,"ssid and passcode already in config file.. no update")
				return False

		if old.find("network={") ==-1: 
			os.system("cp "+G.homeDir+"wpa_supplicant.conf-DEFAULT " +G.homeDir+"wpa_supplicant.conf-temp")

		f = open(G.homeDir+"wpa_supplicant.conf-temp","a")
		f.write('network={\n      ssid="'+data["SSID"]+'"\n      psk="'+data["passCode"]+'"\n}\n')
		f.close()
		os.system("cp "+G.homeDir+"wpa_supplicant.conf-temp /etc/wpa_supplicant/wpa_supplicant.conf")
		if whichWifi().find("adhoc") > -1:
			setStopAdhocWiFi()
			time.sleep(3) 
			stopAdhocWifi()
		else:
			## need to reboot to get the new configs loaded 
			time.sleep(2)
			doReboot(0,"")
	except	Exception, e :
		logger.log(30, u"makeNewSupplicantFile in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return	True

#

################################
def getIPNumberMaster(quiet=False):
	G.ipAddress								  = ""
	ipAddressRead							  = ""
	retcode									  = 0
	ipHostname								  = gethostnameIP()		   
	eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled = getIPCONFIG()

	wlan0IP,eth0IP,changed = setWlanEthONoff(wlan0IP, eth0IP)
	if changed: 
		time.sleep(2)
		eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled= getIPCONFIG()

	try:
		try:
			f=open(G.homeDir+"ipAddress","r")
			ipAddressRead = f.read().strip(" ").strip("\n").strip(" ")
			f.close()
		except:
			ipAddressRead = ""

		if not quiet: 
			logger.log(30,"IP find:: IPs#: Indigo>{}<; wlan0>{}<; eth0>{}<; hostname>{}<; AddressFile>{}<; PKTS(eth0>{},{}<; wlan0>{},{}<, dTime:{:.1f})".format( G.ipOfServer, wlan0IP, eth0IP, ipHostname, ipAddressRead, G.eth0Packets, G.eth0PacketsOld, G.wlan0Packets,G .wlan0PacketsOld, min(99.9,G.packetsTime-G.packetsTimeOld)))
			logger.log(30,"          Requested Config:{}".format(G.wifiEth))


		if testDNS() >0:
			retcode = 1
		if testPing() >0:
			retcode = 2
			if not G.wifiEnabled and not G.switchedToWifi:
				G.wifiEthOld		= copy.copy(G.wifiEth)
				G.wifiEth["wlan0"]["on"]	= "on"
				G.wifiEth["wlan0"]["useIP"]	= "use"
				G.wifiEth["eth0"]["useIP"]  = "useIf"
				eth0IP = ""
				if not G.wifiEnabled:
					startWiFi()
					time.sleep(10)
				eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled = getIPCONFIG()
				

# simple cases:
		if len(ipAddressRead) > 7  and ipAddressRead in [wlan0IP,eth0IP] and  testPing(ipIn=ipAddressRead) ==0:
				G.ipAddress = ipAddressRead
				return retcode , changed
				

		if len(ipHostname) ==1	and ipHostname[0] in [wlan0IP,eth0IP] and  testPing(ipIn=ipHostname[0]) ==0:
				if ipHostname[0] != ipAddressRead:
					writeIPtoFile(ipHostname[0],reason="hostname gives differnt than stored IP#")
				G.ipAddress = ipHostname[0]
				return retcode , changed
			
		if len(ipHostname) > 1 and len(ipHostname[1]) > 6:
			for ii in range(len(ipHostname)):
				if ipHostname[ii] in [wlan0IP,eth0IP]:
					if testPing(ipIn=ipHostname[ii]) == 0:
						if ipAddressRead != ipHostname[ii]:
							writeIPtoFile(ipHostname[ii],reason="2 host names")
						G.ipAddress = ipHostname[0]
						return retcode , changed

	except	Exception, e:
		logger.log(30,u"U.getIPNumberMaster error in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	logger.log(30,u"U.getIPNumberMaster bad IP number ...  ipHostname >>{}<<  old from file ipAddressRead>>{}<< not in sync with ifconfig output: wlan0IP>>{}<<;	eth0IP>>{}<<".format(unicode(ipHostname), ipAddressRead, wlan0IP,eth0IP)  )
	return 2, changed

#################################
def setWlanEthONoff(wlan0IP, eth0IP):

# G.wifiEth["eth0"]  ={"on":{"on"/"onIf"/"off"/"dontChange"}, "useIP":"use"/"useIf"/"off"}}
# G.wifiEth["wlan0"] ={"on":{"on"/"onIf"/"off"/"dontChange"}, "useIP":"use"/"useIf"/"off"}}

	changed	= False
	if wlan0IP == "": 
		if G.wifiEth["eth0"]["on"] in ["on","onIf","dontChange"] and eth0IP == "" and not G.eth0Enabled:
			startEth()
			time.sleep(10)
			changed	= True
			logger.log(30,u"setWlanEthONoff  ip changed: eth0[on]: {}, eth0IP:/, eth0Enabled:F, wlan0IP:{}, eth0Packets:{}, wlan0Packets:{} .. starting eth0".format(G.wifiEth["eth0"]["on"], G.eth0Packets, G.wlan0Packets) ) 
		
	if G.switchedToWifi != 0 and time.time() - G.switchedToWifi < 100:
		G.switchedToWifi =time.time() + 100.
		# reset eth packet counters
		if G.eth0Enabled:
			##sudo rfkill unblock all ;sudo ifconfig eth0 down ;sudo modprobe -r e1000 ;sudo modprobe e1000 ;sudo ifconfig eth0 up
			stopEth()
			startEth()
		if wlan0IP == "": 
			if not G.wifiEnabled:
				startWiFi()
				time.sleep(10)
			changed	= True
			logger.log(30,u"etWlanEthONoff  ip changed: switchedToWifi:T , wlan0IP:/, wifiEnabled:F starting WiFi".format(wlan0IP, G.eth0Packets, G.wlan0Packets) ) 

	# check if ethernet is back after 5 minutes
	if G.switchedToWifi != 0 and time.time() - G.switchedToWifi > 300:
		if eth0IP != "" and G.eth0Enabled:
			if G.eth0Packets != G.eth0PaketsOld and (G.packetsTime- G.packetsTimeOld > 2.):
				if testPing() != 0:
					G.wifiEth	= copy.copy(G.wifiEthOld)
					G.switchedToWifi = 0
					if G.wifiEth["wlan0"]["on"]  in ["onIf","off"]:
						stopWiFi()
						time.sleep(2)
					changed	= True
					logger.log(30,u"setWlanEthONoff  ip changed: resetting switchedToWifi, eth0 seems to be back(packet count);  wlan0[on]:{}, eth0IP:{}, G.eth0Enabled:T, stopWiFi".format(G.wifiEth["wlan0"]["on"],eth0IP) ) 

	if changed: 
		time.sleep(2)
		eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled = getIPCONFIG()
		logger.log(30,u"setWlanEthONoff  return: eth0IP:{}, wlan0IP:{}, eth0Enabled:{}, wifiEnabled:{}, eth0Packets:{},eth0PacketsOld:{}, wlan0Packets:{},  wlan0PacketsOld:{}".format(eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled, G.eth0Packets, G.wlan0Packets  ) ) 
		return wlan0IP, eth0IP, True


	if G.wifiEth["wlan0"]["on"] not in ["on","dontChange"] and wlan0IP != "" and G.wifiEnabled: 
		if eth0IP !="":
			logger.log(30,u"switching WiFi off")
			stopWiFi()
			changed = True
			logger.log(30,u"setWlanEthONoff  ip changed: G.wifiEth[wlan0][on] not in [on,dontChange] and wlan0IP:{}  and G.wifiEnabled, eth0IP:{}, eth0Packets:{}, wlan0Packets:{}".format(wlan0IP, eth0IP, G.eth0Packets, G.wlan0Packets ) ) 
		else:
			logger.log(30,u"switching WiFi off not possible as eth0 not on ")


	if G.wifiEth["eth0"]["on"] == "off" and eth0IP != "": 
			logger.log(30,u"switching eth0 off")
			logger.log(30,u"setWlanEthONoff  ip changed: G.wifiEth[eth0][on] ==off and  eth0IP:{}, eth0Packets:{}, wlan0Packets:{}".format(eth0IP, G.eth0Packets, G.wlan0Packets) ) 
			stopEth()
			changed = True

	if  G.wifiEth["eth0"]["useIP"] == "off" and eth0IP !="":
		logger.log(30,u"setting eth0 /")
		logger.log(30,u"setWlanEthONoff  ip changed: G.wifiEth[eth0][useIP] ==off and  eth0IP:{}, eth0Packets:{}, wlan0Packets:{}".format(eth0IP, G.eth0Packets, G.wlan0Packets) ) 
		changed = True

	if  G.wifiEth["wlan0"]["useIP"] == "off" and wlan0IP !="":
		changed = True
		logger.log(30,u"setWlanEthONoff  ip changed: G.wifiEth[wlan0][useIP] ==off and  wlan0IP:{}, eth0Packets:{}, wlan0Packets:{}".format(wlan0IP, G.eth0Packets, G.wlan0Packets) ) 



	return wlan0IP,eth0IP, changed
		

		

#################################
def writeIPtoFile(ip,reason=""):
	G.ipAddress = ip
	f=open(G.homeDir+"ipAddress","w")
	f.write(G.ipAddress.strip(" ").strip("\n").strip(" "))
	f.close()
	logger.log(30," writing ip number to file >>{}<<  reason:{}".format(G.ipAddress, reason))
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
		logger.log(10, "testPing input>>{}<< indigoIP>>{}<<".format(ipIn,G.ipOfServer) )
		
		# IPnumber setup?
		ipi =  (ipToPing.strip()).split(".")
		if len(ipi) !=4: 
			logger.log(10, "testPing bad ip number to ping >>{}<<".format(str(ipToPing)) )
			return 1
		for ii in ipi:
			try: int(ii)
			except: 
				logger.log(30, "testPing bad ip number for ping >>{}<<".format(str(ipToPing)) )
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

		logger.log(30,"testPing can not connect to server: {}	ping code:{}".format(ipToPing,unicode(ret)) )
			
		return 2

	except	Exception, e :
		logger.log(30, u"testPing in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
	#or just:
	#lrwxrwxrwx 1 root root           7 Jul  7 13:30 serial1 -> ttyAMA0



	if version[0].find("Raspberry") ==-1:
		logger.log(30,"cat /proc/device-tree/model something is wrong... "+unicode(version)  )
		time.sleep(10)
		return ""
		
	if version[0].find("Pi 3") == -1 and version[0].find("Pi Zero") == -1:	# not RPI3
		sP = "/dev/ttyAMA0"

		### disable and remove tty usage for console
		subprocess.Popen("systemctl stop serial-getty@ttyAMA0.service" ,	shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("systemctl disable serial-getty@ttyAMA0.service" , shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		if serials[0].find("serial0 -> ttyAMA0") ==-1 :
			logger.log(30, "pi2 .. wrong serial port setup .. enable serial port in raspi-config ..  can not run missing in 'ls -l /dev/' : serial0 -> ttyAMA0" )
			time.sleep(10)
			return ""

	elif version[0].find("Pi Zero") >-1:	# not RPI3
		sP = "/dev/ttyS0"

		### disable and remove tty usage for console
		subprocess.Popen("systemctl stop serial-getty@ttyS0.service" ,	  shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("systemctl disable serial-getty@ttyS0.service" , shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		if serials[0].find("serial0 -> ttyS0")==-1:
			logger.log(30, "pi3 .. wrong serial port setup  .. enable serial port in raspi-config .. can not run missing in 'ls -l /dev/' : serial0 -> ttyS0" )
			time.sleep(10)
			return ""

	else:# RPI3
		sP = "/dev/ttyS0"

		### disable and remove tty usage for console
		subprocess.Popen("systemctl stop serial-getty@ttyS0.service" ,	  shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		subprocess.Popen("systemctl disable serial-getty@ttyS0.service" , shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		if serials[0].find("serial0 -> ttyS0")==-1:
			logger.log(30, "pi3 .. wrong serial port setup .. enable serial port in raspi-config ..  can not run missing in 'ls -l /dev/' : serial0 -> ttyS0" )
			time.sleep(10)
			return ""
	return sP


#################################
def geti2c():
	try:
		i2cChannels=[]
		temp =[]
		ret= subprocess.Popen("i2cdetect -y 1",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if ret[1] is not  None and ret[1].find("No such file or directory") > 0:
			i2cChannels=["i2c.ERROR:.no.such.file....redo..SSD?"]
		else:
			lines = ret[0].split("\n")
			temp=[]
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
							temp.append(v16) # converted
			for channel in temp:
				i2cChannels.append("{}={}".format(channel,hex(channel)))
		return i2cChannels
	except	Exception, e :
		logger.log(30, u"geti2c in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return ["i2c detect error"]




#### selct the proper hci bus: if just one take that one, if 2, use bus="uart", if no uart use hci0
def selectHCI(HCIs, useDev, default):
	if len(HCIs) ==1:
		useHCI = list(HCIs)[0]
		myBLEmac= HCIs[useHCI]["BLEmac"]
		devId = 0
		return useHCI,  myBLEmac, devId

	elif len(HCIs) == 2:
		if useDev =="USB":
			for hh in ["hci0","hci1"]:
				if HCIs[hh]["bus"] =="USB":
					useHCI	= hh
					myBLEmac= HCIs[hh]["BLEmac"]
					devId	= HCIs[hh]["numb"]
					return useHCI,  myBLEmac, devId

		elif useDev =="UART":
			for hh in ["hci0","hci1"]:
				if HCIs[hh]["bus"] =="UART":
					useHCI	= hh
					myBLEmac= HCIs[hh]["BLEmac"]
					devId	= HCIs[hh]["numb"]
					return useHCI,  myBLEmac, devId

		else:
			for hh in ["hci0","hci1"]:
				if HCIs[hh]["bus"] == default:
					useHCI	= hh
					myBLEmac= HCIs[hh]["BLEmac"]
					devId	= HCIs[hh]["numb"]
					return useHCI,  myBLEmac, devId

		useHCI	= "hci0"
		myBLEmac= HCIs[useHCI]["BLEmac"]
		devId	= HCIs[useHCI]["numb"]
		return useHCI,  myBLEmac, devId
		
	logger.log(20, "BLEconnect: NO BLE STACK UP ")
	return 0, -1, -1

#################################
def whichHCI():

	#hci={"hci0":{"bus":"UART", "numb":0 ,"BLEmac":"xx:xx:xx:xx:xx:xx"}}
	hci ={}
		
	ret	   = subprocess.Popen("hciconfig ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()#################################	 BLE iBeaconScanner	 ----> end
	# try again, sometimes does not return anything
	if len(ret[0]) < 5:
		time.sleep(0.5)
		ret	  = subprocess.Popen("hciconfig ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()#################################	BLE iBeaconScanner	----> end
		logger.log(30,"whichHCI, hciconfig...  2. try: "+unicode(ret))
		
	lines = ret[0].split("\n")
	for ll in range(len(lines)):
		if lines[ll].find("hci")>-1:
			bus = lines[ll].split("Bus: ")[1]
			hciNo = lines[ll].split(":")[0]
			hci[hciNo] = {"bus":bus, "numb":int(hciNo[3:])}
			if lines[ll+1].find("BD Address:")>-1:
				mm=lines[ll+1].strip().split("BD Address: ")[1]
				mm=mm.split(" ")
				if len(mm)>2:
					hci[hciNo]["BLEmac"] = mm[0]

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
	if hci =={}: logger.log(30, unicode(lines))
	return	hci				  




#################################
def sendURL(data={},sendAlive="",text="", wait=True, squeeze=True, escape=False):
		
	try:
			netwM = getNetwork() 
			if (G.networkType  not in G.useNetwork or G.wifiType !="normal") or	 (netwM=="off" or netwM =="clock") : 
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

			if G.IndigoOrSocket == "indigo":  # use indigo http restful 
						var = "/variables/"+name
						data0 = json.dumps(data, separators=(',',':'))
						if squeeze: data0 = data0.replace(" ","")
						if escape:  data0 = urllib.quote(data0)
						###print data0
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
						logger.log(10,"msg: " + unicode(cmd)+"\n" )
						if wait:
							ret = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
							if ret[0].find("This resource can be found at")==-1:
								logger.log(30,"curl err:"+ ret[0])
								logger.log(30,"curl err:"+ ret[1])
								os.system("echo '"+G.program+": NOT successfully send -- "+data0+"' > "+ G.homeDir+"temp/messageSend")
							else:
								os.system("echo '"+G.program+": send --  "+data0+"' > "+ G.homeDir+"temp/messageSend")
						else:
							cmd.append(" &")
							subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
							os.system("echo '"+G.program+": sending  "+data0+"' > "+ G.homeDir+"temp/messageSend")

			else:  ## do socket comm 
						
						sendMSG = False
						for ii in range(3): # try max 3 times.
							data0 = json.dumps(data, separators=(',',':'))
							if squeeze: data0 = data0.replace(" ","")
							sendData= str(len(data0))+"x-6-a"+name+"x-6-a"+data0
							try:
								soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
								soc.settimeout(5.)
								soc.connect((G.ipOfServer, G.indigoInputPORT))
								len_sent = soc.send(sendData)
								time.sleep(0.1)
								response = soc.recv(512)
								if response.find("ok") >-1:
									sendMSG =True
									break
								else:# try again
									logger.log(10, "Sending  again: send bytes: " + str(len(data0)) + " ret MSG>>"+  response+"<<")
									try:	soc.close()
									except: pass
									time.sleep(3.)

							except	Exception, e:
								logger.log(30, u"sendURL in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
									logger.log(10,"msg: " + unicode(sendData)+"\n" )
									os.system("echo '"+G.program+":  send -- "+data0+"' > "+ G.homeDir+"temp/messageSend")
						else:
									logger.log(10,"msg not send "+sendData)
									os.system("echo '"+G.program+": NOT successfully send -- "+data0+"' > "+ G.homeDir+"temp/messageSend")
						try:	soc.shutdown(socket.SHUT_RDWR)
						except: pass
						try:	soc.close()
						except: pass
			#print " send time ",time.time()- tStart



				
	except	Exception, e:
		logger.log(30, u"sendURL in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

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
			execcommands, input = readJson(G.homeDir+"execcommands.current")
			if len(input) < 3: return
			rmEXEC={}
			for channel in execcommands:
				logger.log(10,"removing  testing channel "+str(channel) +"  "+ str(execcommands[channel]) )
				if channel != str(pin): continue
				if "device" in execcommands[channel] and devType == execcommands[channel]["device"]:
					logger.log(10,"removing testing channel device found" )
					if "startAtDateTime" in execcommands[channel] and time.time() - float(execcommands[channel]["startAtDateTime"]) > 2: 
						if execcommands[channel]["command"]	 not in ["analogWrite","up","down"]:
							logger.log(10,"removing testing channel time expired" )
							rmEXEC[channel]=1
							logger.log(10,"removing removing channel "+str(channel)) 
			for channel in rmEXEC:
				del execcommands[channel]
			writeJson(G.homeDir+"execcommands.current",execcommands)
	except	Exception, e:
		logger.log(30, u"removeOutPutFromFutureCommands in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			doReboot(0,"")

			
#################################
def echoLastAlive(sensor):
	try: 
		tt=time.time()
		if time.time() - G.lastAliveEcho > 30.: 
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
		logger.log(30, u"doFileCheck in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

#################################
def makeDATfile(sensor, data):
	if "sensors" in data:
		for sens in data["sensors"]:
			#print sensor, "makeDATfile", sens, data["sensors"][sens]
			writeJson(G.homeDir+"temp/"+sens+".dat", data["sensors"][sens], indent=2)
	else:
			writeJson(G.homeDir+"temp/"+sensor+".dat",data, indent=2)


#################################
def writeJson(fName, data, sort_keys=False, indent=0):
	try:
		f=open(fName,"w")
		if indent != 0:
			out = json.dumps(data,sort_keys=sort_keys, indent=indent)
		else:	
			out = json.dumps(data,sort_keys=sort_keys)
	##print "writing json to "+fName, out
		f.write(out)
		f.close()
	except	Exception, e:
		logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			doReboot(0,"")
	return 


#################################
def readJson(fName):
	data ={}
	ddd = ""
	try:
		f=open(fName,"r")
		ddd = f.read()
		data = json.loads(ddd)
		f.close()
	except: return {},""
	return data, ddd


#################################
def checkresetCount(IPCin):
	IPC = copy.copy(IPCin)
	try:
		if not os.path.isfile(G.homeDir + G.program+".reset"): 
			#print "checkresetCount no file"
			return IPC
		inpJ, inp = readJson(G.homeDir + G.program+".reset")
		os.remove(G.homeDir + G.program+".reset")
		if len(inp) < 3: 
			return IPC
		#print "checkresetCount doing reset", inp
		for p in inpJ:
			pin = int(p)
			if pin > 99:  continue
			if pin < 0:	  continue
			IPC[pin] = 0
			#print "checkresetCount pin=", pin
		writeINPUTcount(IPC)
	except	Exception, e:
		logger.log(30, u"checkresetCount in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	#print "checkresetCount pin=", IPC[15:25]
	return IPC
	
######################################
def readINPUTcount():
		IPC = [0 for i in range(100)]
		try:
			IPC, ddd = readJson(G.homeDir+G.program+".count")
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
	writeJson(G.homeDir+G.program+".count",IPC)
			
######################################
def readRainStatus():
	status, ddd = readJson(G.homeDir+G.program+".status")
	return status

######################################
def writeRainStatus(status):
	writeJson(G.homeDir+G.program+".status",status)
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
					 logger.log(30, u"doActions in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				
				if	action !="": 
					if "action"+action in sens and sens["action"+action] !="":
						if	action =="UP" or action =="DOWN" or action =="1" or action =="2" or action =="3" or action =="4" or action =="5":

							logger.log(20, u"action"+action+": " +sens["action"+action])
							checkIfrebootAction(sens["action"+action])
							os.system(sens["action"+action])

					if "actionDoubleClick" in sens and sens["actionDoubleClick"] !="":
						manageActions(sens["actionDoubleClick"],waitTime=3,click=action,aType="actionDoubleClick", devId=devId)

					if "actionLongClick" in sens and sens["actionLongClick"] !="":
						manageActions(sens["actionLongClick"],waitTime=3,click=action,aType="actionLongClick", devId=devId)

		############ local action  end #######
	except	Exception, e:
		logger.log(30, u"doActions in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
					logger.log(20," executing action: "+unicode(action)) 
					checkIfrebootAction(action)
					os.system(action)
			return

		elif aType=="actionLongClick" and aType == G.actionDict[action][devId]["aType"]:
			if click != G.actionDict[action][devId]["click"] :
				if tt - G.actionDict[action][devId]["timerStart"] > G.actionDict[action][devId]["waitTime"]	 :
					checkIfrebootAction(action)
					logger.log(20," executing action: "+unicode(action)) 
					os.system(action)
				else  :
					del G.actionDict[action][devId]
			else:
				del G.actionDict[action][devId]
			return
		
	except	Exception, e:
		logger.log(30, u"manageActions in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

#################################
def checkIfrebootAction(action):
	# display.py might stop shutdown from going through, need to kill first
	try:
		if action.find("shutdown") >-1 or  action.find("reboot") >-1 :	
			logger.log(30," executing action: "+unicode(action)) 
			killOldPgm(-1,"display.py")
			time.sleep(0.2)
	except	Exception, e:
		logger.log(30, u"checkIfrebootAction in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return


################################


def sendi2cToPlugin(sensDict):
	i2c			= ""
	lastBoot	= ""
	os			= ""
	temp		= ""
	rpiType		= ""
	try:
		i2c		 = geti2c()
		sensList = ""		
		for sens in sensDict:
			if sens.find("i2c") == 0: # strip i2c from the beginning of name.
				ss = sens[3:]
			else:
				ss = sens
			ll = len(sensDict[sens])
			if ll > 1:
				sensList += str(ll)+" "+ss+"; "
			else:
				sensList += ss+"; "

		if len(sensList) > 0: sensList = sensList.strip(" ").strip(";")
		#																	remove trailing null chars;  \\ for escape  of \
		rpiType	 = subprocess.Popen("cat /sys/firmware/devicetree/base/model | tr -d '\\000' " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		###print "rpiType1>>"+rpiType+"<<"
		rpiType	 = ''.join(i for i in rpiType if ord(i)>1).split("Raspberry ")
		if len(rpiType) ==2: rpiType = rpiType[1]
		else:				 rpiType = rpiType[0]
		##print "rpiType2>>"+rpiType+"<<"
		serN	 = subprocess.Popen("cat /sys/firmware/devicetree/base/serial-number | tr -d '\\000' " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		serN	 = (''.join(i for i in serN if ord(i)>1)).lstrip("0")
		###print "serN>>"+serN+"<<"
		rpiType +="; ser#"+serN
		#  --> Raspberry Pi 3 Model B Plus Rev 1.3/ ser#00000000dcfb216c

		osInfo	 = subprocess.Popen("cat /etc/os-release" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").split("\n")
		for line in osInfo:
			if line .find("VERSION=") == 0:
				os = line.split("=")[1].strip('"').strip(' ')
		os += "; "+ subprocess.Popen("uname -r" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip(' ')
		os += "; "+ subprocess.Popen("uname -v" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip(' ')

		tempInfo = subprocess.Popen("/opt/vc/bin/vcgencmd measure_temp" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		try:	temp = tempInfo.split("=")[1].split("'")[0]
		except: temp = "0"

		lastBoot = subprocess.Popen("uptime -s" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n")
		lastBoot = subprocess.Popen("uptime -s" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n")

		data ={"sensors_active":sensList, "i2c_active":json.dumps(i2c).replace(" ","").replace("[","").replace("]","").replace('"','').replace('0x','x'),"temp":temp, "rpi_type":rpiType, "op_sys":os, "last_boot":lastBoot,"last_masterStart":G.last_masterStart}
		##print data
		sendURL(data=data, sendAlive="alive", squeeze=False, escape=True)

	except Exception, e :
		logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 

#################################
def testBad(newX, lastX, inXXX):

	xxx = inXXX
	try:
		if newX.find("bad") == -1:
			if lastX.find("bad") == -1:
				xxx = max(xxx, abs( float(lastX) - float(newX) )/ max(0.1, abs(float(lastX) + float(newX)) ) )
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
		logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e),permanentLog=True)
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

		logger.log(20,'magCalibrate -2 ')
		logger.log(10,'Starting Debug, please rotate the magnetometer about all axis')
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
						logger.log(20,'magCalibrate Update: '+unicode(calib))
				time.sleep(0.1)
			except:
				break
		saveCalibration(theClass.calibrationFile, calib)
		theClass.magOffset = setOffsetFromCalibration(theClass.calibrations)
		return True

#################################
def saveCalibration(theClass, calibrationFile, calib):
	logger.log(20,'saveCalibration:  enableCalibration = '+unicode(calib))
	writeJson(theClass.calibrationFile,calib, sort_keys=True)

#################################
def setOffsetFromCalibration(calib):
		try:
			offset=[]
			offset[0] = (calib['minX'] + calib['maxX'])/2
			offset[1] = (calib['minY'] + calib['maxY'])/2
			offset[2] = (calib['minZ'] + calib['maxZ'])/2
			logger.log(20,'theClass.magOffset '+unicode(offset))
			return offset
		except	Exception, e:
			logger.log(30, u"setOffsetFromCalibration in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return [0,0,0]

#################################
def loadCalibration(calibrationFile):
		calibrations, calib = readJson(G.homeDir+G.program+".status")
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
					logger.log(10," bad sensor")
					data["sensors"][sensor][devId][testForBad]="badSensor"
					sendURL(data)
				for mm in dims:
					for x in coords:
						old[devId][mm][x]=-50000
				if G.badCount1 > 10: 
						restartMyself(reason=" empty sensor reading, need to restart to get sensors reset",doPrint= False)
				return old
			G.badCount1 =0
			if testForBad not in new: 
				#print "reject 2"
				return old
			if new[testForBad] =="":  
				G.badCount5 +=1
				if G.badCount5 < 5: 
					logger.log(10," bad sensor")
				if G.badCount5 > 15: 
					data["sensors"][sensor][testForBad]="badSensor"
					sendURL(data)
					restartMyself(reason=" empty sensor reading, need to restart to get sensors reset",doPrint= False)
				return old
			G.badCount5 =0
			if singleTest["dim"]!="":
					if ( abs(new[singleTest["dim"]][singleTest["coord"]]) >	 singleTest["limits"][1] or 
						 abs(new[singleTest["dim"]][singleTest["coord"]]) <= singleTest["limits"][0]): 
						logger.log(10, singleTest["dim"]+"-"+singleTest["coord"]+" out of bounds, ignoring: " +unicode(new))
						G.badCount4+=1
						if G.badCount4 > 10: 
							restartMyself(reason=unicode(singleTest)+"- wrong, need to restart to get sensors reset",doPrint= False)
						#print "reject 3"
						return old
			G.badCount4 =0
			if sumTest["dim"]!="":
				dd= sumTest["dim"]
				SUM = sum(	[abs(new[dd][x]) for x in new[dd] ]	 ) 
				if SUM <=sumTest["limits"][0] or SUM > sumTest["limits"][1]:
					logger.log(10, unicode(sumTest)+" sum of values bad " + unicode(SUM))
					G.badCount3 +=1
					if G.badCount3 > 10: 
						restartMyself(reason=unicode(sumTest)+"	 bad, need to restart to get sensors reset",doPrint= False)
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

			#logger.log(30,unicode(totalDelta)+"	 "+unicode(totalABS)+"	"+ unicode(nTotal)+"  "+unicode(deltaX))
			if nTotal > 1 and totalDelta/nTotal > max(0.01,G.deltaX[devId]): 
				#print " sendNow", total/nTotal , deltaX[devId]
				retCode = "sendNow" 
			if nTotal > 1 and totalABS ==0: 
				G.badCount2+=1
				if G.badCount2 > 5: 
					restartMyself(reason=unicode(dims)+" values identival 5 times need to restart to get sensors reset",doPrint= False)
				#print "reject 5"
				return old
				
			else:
				G.badCount2 =0
			if G.sensorWasBad:
				restartMyself(reason=unicode(dims)+" back from bad sensor, restart",doPrint= False)
			data["sensors"][sensor][devId] = new
			#print	 time.time() - G.lastAliveSend , abs(G.sensorRefreshSecs) , quick , retCode=="sendNow" , time.time() - G.lastAliveSend , G.minSendDelta
			if (  (time.time() - G.lastAliveSend > abs(G.sensorRefreshSecs) or quick or retCode=="sendNow" )  and (time.time() - G.lastAliveSend > G.minSendDelta) ):
					#print	"sending", unicode(data)
					sendURL(data)
					old[devId]	= copy.copy(new)
   
		except	Exception, e: 
			logger.log(30, u"checkMGACCGYRdata in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		logger.log(30, u"findString in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			doReboot(0,"")
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
		logger.log(30, u"findString in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
		logger.log(30, u"uncommentOrAdd in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			doReboot(0,"")


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
		logger.log(30, u"removefromFile in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		if unicode(e).find("Read-only file system:") >-1:
			doReboot(0,"")
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
		if ret.find("nameserver") == -1:
			logger.log(30," resolv.conf has no nameserverlisted")
			return 1
		ret = ret.split("\n")
		if len(ret) ==0:
			logger.log(30," resolv.conf has no nameserverlisted")
			return 1

		for line in ret:
			ip = line.split("nameserver ")
			if len(ip) == 2 : 
				ret =testPing(ipIn=ip[1]) 
				if	ret ==0:
					#print	" DNS server reachable at:"+ip[1]
					logger.log(10," DNS server reachable at:"+ip[1])
					return 0
				if ret ==-2:
					logger.log(30,"still waiting for installLibs to finish")
					time.sleep(30)
					return 1
	except	Exception, e:
		logger.log(30,u"testDNS error in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return 1

#################################
##networkStatus		  = "no"   # "no" = no network what so ever / "local" =only local cant find anything else/ "inet" = internet yes, indigo no / "indigoLocal" = indigo not internet / "indigoInet" = indigo with inetrnet
def testNetwork(force=False):
	global lasttestNetwork
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
		toLog (-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	G.networkStatus = "local"
	return 



