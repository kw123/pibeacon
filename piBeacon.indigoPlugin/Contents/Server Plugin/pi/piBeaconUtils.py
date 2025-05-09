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
try:
	import RPi.GPIO as GPIO
except: pass
import threading
try: import Queue
except: import queue as Queue
import zlib
try: 	unicode
except: unicode = str

import traceback



import urllib


global failedURLimport

try:
	from urllib.request import Request, urlopen
	failedURLimport = False
except:
	failedURLimport = True
		

#except: 
#	from urllib.request import request 
#	Request = request
#	from urllib.request import urlopen



import re

global OSVersion
OSVersion = -1

##
#  do
# sys.path.append(os.getcwd())
# import  piBeaconUtils	  as U
# then get the modules as xxx()
#
#################################
def test():
	return 

#################################
def setLogging():
	global logging, logger
	import logging
	import logging.handlers
	global streamhandler, permLogHandler
	global failedURLimport

	# regular logfile
	logging.basicConfig(level=logging.INFO, filename= "{}pibeacon".format(G.logDir),format='%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d Lv:%(levelno)s %(message)s', datefmt='%d-%H:%M:%S')
	logger = logging.getLogger(__name__)

	# permanent logfile in pibeacon directory only for serious restarts, in case log dir is ramdisk
	permLogHandler = logging.handlers.WatchedFileHandler("{}permanent.log".format(G.homeDir))
	permFormat = logging.Formatter('%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d Lv:%(levelno)s %(message)s',datefmt='%Y-%m-%d-%H:%M:%S')
	permLogHandler.setFormatter(permFormat)
	permLogHandler.setLevel(logging.CRITICAL)
	logger.addHandler(permLogHandler)

	# console output
	streamhandler = logging.StreamHandler()
	streamhandler.setLevel(logging.WARNING)
	streamformatter = logging.Formatter('%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d Lv:%(levelno)s %(message)s',datefmt='%Y-%d-%H:%M:%S')
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
	logger.log(10, "cBY:{:<20} setting debuglevel to {}".format(G.program, "on" if  G.debug == 1 else "off"))

	permLogHandler.setLevel(logging.CRITICAL)
	streamhandler.setLevel(logging.WARNING)


#################################
def killOldPgm(myPID,pgmToKill, delList=[], param1="", param2="", verbose=False,wait=False):
	global failedURLimport, logger

	#print ("cBY:{:<20} sys info:{}".format(G.program, sys.version_info))
	#print ("cBY:{:<20} urllib:{}".format(G.program, urllib))
	#print ("cBY:{:<20} failedURLimport:{}".format(G.program, failedURLimport))

	ps = "{}".format(subprocess.Popen("ps -ef | grep .py", shell=True,stdout=subprocess.PIPE).communicate())
	count = 0
	try:		
		if int(myPID) > 10 and len(delList) == 0:
			cmd= ["/usr/bin/sudo","/usr/bin/python","{}killOldPgm.py".format(G.homeDir), str(myPID), pgmToKill, param1, param2]
			if verbose: logger.log(20, "cBY:{:<20} kill pgm using external, myPID:{}, cmd:{}".format(G.program, myPID, cmd) )
			ret = subprocess.Popen(cmd)
			return 1
	except Exception as e:
		logger.log(30,"", exc_info=True)
		
	count = 0
	try:
		#print "killOldPgm ",pgmToKill,str(myPID)
		cmd = "ps -ef | grep '{}' | grep -v grep".format(pgmToKill)
		if param1 !="":
			cmd = "{} | grep {}".format(cmd,param1)
		if param2 !="":
			cmd = "{} | grep ".format(cmd,param2)
		if verbose: logger.log(20, "cBY:{:<20} kill mypid:{}, command {}, {}, \nps:{}".format(G.program, myPID, cmd, delList, ps) )

		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
		lines=ret.split("\n")
		del ret
		xlist = ""
		for line in lines:
			if len(line) < 10: continue
			items=line.split()
			pid=int(items[1])
			if pid == int(myPID): continue
			if delList != []:
				found = False
				for dd in delList:
					if line.find(dd+".py") > -1:
						found = True
						break 
			else:
				found = True
			if not found: continue

			if verbose: logger.log(20, "cBY:{:<20}  killing {}  {}  {}, pid={}, line:{}".format(G.program, pgmToKill, param1, param2, pid, (" ").join(items[8:])) )
			xlist += str(pid)+ " "
			count += 1
		if verbose: 
			logger.log(20, "cBY:{:<20} /usr/bin/sudo kill -9 {} ".format(G.program, xlist) )
		if len(xlist) > 2:
			cmd = "/usr/bin/sudo kill -9 {}".format(xlist)
			if not wait: cmd += " &"
			subprocess.call(cmd, shell=True)
	except Exception as e:
		logger.log(30,"", exc_info=True)
		if str(e).find("Too many open files") >-1:
			doReboot(tt=3, text=str(e), force=True)
	return count

#################################
def restartMyself(param="", reason="", delay=1, doPrint=True, python3=False, doRestartCount=True):
	py3 = python3 or checkIfmustUsePy3()
	try:
		if doPrint: logger.log(20, "cBY:{:<20} --- restarting --- {}  due to: {}, py3:{}, delay:{}".format(G.program, param, reason, py3, delay) )
	except Exception as e:
		logger.log(30,"", exc_info=True)

	time.sleep(delay)

	if doRestartCount:
		lastRestartCount	= 0
		lastRestart 		= 0
		if os.path.isfile("{}temp/restartLast.{}".format(G.homeDir, G.program)):
			lastRestart = os.path.getmtime("{}temp/restartLast.{}".format(G.homeDir, G.program))
			f = open("{}temp/restartLast.{}".format(G.homeDir, G.program ))
			lastRestartCount = int(f.read())
			f.close()
		if time.time() - lastRestart  < 300 and lastRestartCount > 30:
			if G.enableRebootCheck.find("reboot") >-1:
				doReboot(tt=10, text="restarted {} too often".format(G.program), force=True)
		elif time.time() - lastRestart > 600:
			lastCount  = 0

		cmd= "echo  {} > {}temp/restartLast.{}".format(lastRestartCount+1,G.homeDir, G.program )
		if doPrint: logger.log(30, cmd )
		subprocess.call(cmd, shell=True)

	if sys.version_info[0] == 3 or py3:
		cmd = "/usr/bin/sudo /usr/bin/python3 {}{}.py {} &".format(G.homeDir,G.program, param)
	else:
		cmd = "/usr/bin/sudo /usr/bin/python {}{}.py {} &".format(G.homeDir,G.program, param)

	if doPrint: logger.log(30, cmd )
	subprocess.call(cmd, shell=True)
	exit()
	time.sleep(5)



	cmd = "/usr/bin/sudo /usr/bin/python {}{}.py {} &".format(G.homeDir,G.program, param)

	if doPrint: logger.log(30, cmd )
	subprocess.call(cmd, shell=True)


#################################
def setStopCondition(on=True):
	if on:
		subprocess.call("/usr/bin/sudo chmod 666 /dev/i2c-*", shell=True)
		subprocess.call("/usr/bin/sudo chmod 666 /sys/module/i2c_bcm2708/parameters/combined", shell=True)
		subprocess.call("/usr/bin/sudo echo -n 1 > /sys/module/i2c_bcm2708/parameters/combined", shell=True)
	else:
		subprocess.call("/usr/bin/sudo chmod 666 /dev/i2c-*", shell=True)
		subprocess.call("/usr/bin/sudo chmod 666 /sys/module/i2c_bcm2708/parameters/combined", shell=True)
		subprocess.call("/usr/bin/sudo echo -n N > /sys/module/i2c_bcm2708/parameters/combined", shell=True)


#################################################################
def doReadSimpleFile(fname):

		if os.path.isfile(fname):
			f = open(fname,"r")
			ddd =  f.read()
			f.close()
			return ddd
		return ""

#################################################################
def doWriteSimpleFile(fname, data):

		f = open(fname,"w")
		ddd =  f.write("{}".format(data))
		f.close()
		return


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
		subprocess.call("/usr/bin/sudo cp {}rc.local.default /etc/rc.local ".format(G.homeDir), shell=True)
		subprocess.call("/usr/bin/sudo chmod a+x /etc/rc.local", shell=True)
		logger.log(30, u"{:<20}replacing rc.local file".format(G.program) )


	return



#################################
def fixoutofdiskspace():
	try:	subprocess.call("rm {} *".format(G.logDir), shell=True)
	except: pass
	try:	subprocess.call("logrotate -f /etc/logrotate.d/rsyslog; sleep 1; logrotate -f /etc/logrotate.d/rsyslog", shell=True)
	except: pass

#################################
def pgmStillRunning(pgmToTest, notPresent ="", verbose=False) :
	try :
		pgmToTest = pgmToTest.strip()
		if verbose: logger.log(20, "testing  for '{}'".format(pgmToTest))
		cmd = "ps -ef | grep '{}' | grep -v grep".format(pgmToTest)
		if notPresent != "": cmd += " | grep -v " + notPresent
		if verbose: logger.log(20, "command:{}".format( cmd))
		ret = (subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))
		lines = ret.split("\n")
		if False and verbose: logger.log(20, "test returns {} ".format(ret))
		for line in lines :
			if len(line) < 10: continue
			if verbose: logger.log(20, "testing  line >>{}<< ".format(line) )
			return True
	except Exception as e:
		logger.log(20, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return False

################################# 2020-12-12 12:12:12
def getTimetimeFromDateString( dateString, fmrt="%Y-%m-%d %H:%M:%S"):
	if len(dateString) >9:
		try:
			return  time.mktime( datetime.datetime.strptime(dateString, fmrt).timetuple()  )
		except:
			return 0
	else:
		return 0

#################################
def checkParametersFile(force=False):
		inp, inpRaw, lastRead2 = doRead(lastTimeStamp=1)
		#print "checking parameters file"
		if len(inpRaw) < 100 or force:
			# restore old parameters"
			subprocess.call("cp {}parameters {}temp\parameters".format(G.homeDir,G.homeDir), shell=True)
			subprocess.call("touch {}temp\touchFile".format(G.homeDir), shell=True)
			restartMyself(reason="bad parameter... file.. restored" , doPrint= True)



#################################
#################################
#################################
######### distance actions ###### START -----------------------------------------------------------------
def readDistanceSensor(devId, sensors, sensor):
	global actionDistance, actionShortDistanceLimit,actionVeryShortDistanceLimit, actionLongDistanceLimit, actionVeryLongDistanceLimit, actionStopMinSpeed, actionStopWait, debugDistance
	global actionSpeedLast, actionShortDistanceLimit, distanceActiveCommand, distanceActiveLimit, oldStop, oldRegion, actionEnable, oldSpeed, lastCommandExecuted

	debugDistance 						= False

	try: 	actionSpeedLast
	except:  # init first time called
		actionSpeedLast 				= {}
		oldStop 						= {} 
		oldRegion 						= {} 
		oldSpeed						= {} 
		lastCommandExecuted				= {} 
		oldRegion						= {} 
		actionDistance 					= {} 
		actionEnable					= {}
		distanceActiveLimit 			= {}
		distanceActiveCommand 			= {}
		actionVeryShortDistanceLimit 	= {}
		actionShortDistanceLimit 		= {}
		actionLongDistanceLimit 		= {}
		actionVeryLongDistanceLimit		= {}
		actionStopWait 					= {}
		actionStopMinSpeed 				= {}

	actionDistance[devId]				= {"VeryShort":"","Short":"","Medium":"","Long":"","VeryLong":"","Stop":""}
	actionEnable[devId]					= False
	distanceActiveLimit[devId]			= False
	distanceActiveCommand[devId]		= False
	actionVeryShortDistanceLimit[devId]	= -1
	actionShortDistanceLimit[devId]		= -1
	actionLongDistanceLimit[devId] 		= 99999
	actionVeryLongDistanceLimit[devId] 	= 99999
	actionStopWait[devId] 				= -1
	actionStopMinSpeed [devId]			= -1
	actionSpeedLast[devId] 				= time.time()
	oldStop[devId] 						= "Stop"
	oldRegion[devId] 					= "VeryLong"
	oldSpeed[devId]						= 0
	lastCommandExecuted[devId]			= ""
	oldRegion[devId]					= ""
	if sensor not in sensors: 			return 
	if devId  not in sensors[sensor]: 	return 



	ssd = sensors[sensor][devId]
	actionEnable[devId]								= ssd.get("actionEnable","0") == "1"
	if not actionEnable[devId]	: return 
	try:
		for region in actionDistance[devId]:
			actionDistance[devId][region]			= ssd.get("action{}Distance".format(region),"")
			if len(actionDistance[devId][region]) < 3: actionDistance[devId][region] = ""

		try: 	actionVeryShortDistanceLimit[devId] = float(ssd.get("actionVeryShortDistanceLimit",-1))
		except:	actionVeryShortDistanceLimit[devId] = -1.

		try: 	actionVeryLongDistanceLimit[devId] 	= float(ssd.get("actionVeryLongDistanceLimit",99999))
		except:	actionVeryLongDistanceLimit[devId] 	= 99999

		try: 	actionShortDistanceLimit[devId] 	= float(ssd.get("actionShortDistanceLimit",-1))
		except:	actionShortDistanceLimit[devId] 	= -1.

		try: 	actionLongDistanceLimit[devId] 		= float(ssd.get("actionLongDistanceLimit",99999))
		except:	actionLongDistanceLimit[devId] 		= 99999

		try: 	actionStopWait[devId] 				= float(ssd.get("actionStopWait",-1))
		except:	actionStopWait[devId] 				= -1.

		try: 	actionStopMinSpeed[devId] 			= float(ssd.get("actionStopMinSpeed",-1))
		except:	actionStopMinSpeed[devId] 			= -1.

		for region in actionDistance[devId]:
			if actionDistance[devId][region] != "":
				distanceActiveCommand[devId] = True
				break

		if actionVeryShortDistanceLimit[devId] > 0: 	distanceActiveLimit[devId] = True
		if actionShortDistanceLimit[devId] > 0: 		distanceActiveLimit[devId] = True
		if actionLongDistanceLimit[devId] < 9999: 		distanceActiveLimit[devId] = True
		if actionVeryLongDistanceLimit[devId] < 9999: 	distanceActiveLimit[devId] = True
		if actionStopWait[devId] >0: 					distanceActiveLimit[devId] = True
		if actionStopMinSpeed[devId] >0: 				distanceActiveLimit[devId] = True

	except  Exception as e:
			logger.log(30,"", exc_info=True)

	if debugDistance:logger.log(20," limits: devId:{}\nVeryShort:{}\nShort:{}\n Long:{}\nVeryLong:{}\n actionStopWait:{}\n actionStopMinSpeed:{}\nactionDistance:{}".format( 
					devId, actionVeryShortDistanceLimit[devId], actionShortDistanceLimit[devId], actionLongDistanceLimit[devId], actionVeryLongDistanceLimit[devId], actionStopWait[devId], actionStopMinSpeed[devId], actionDistance[devId]))
	return  

#################################
def doActionDistance(distance, speed, devId):
	global actionDistance, actionShortDistanceLimit,actionVeryShortDistanceLimit, actionLongDistanceLimit, actionVeryLongDistanceLimit, actionStopMinSpeed, actionStopWait, debugDistance
	global actionSpeedLast, distanceActiveCommand, distanceActiveLimit, oldStop, oldRegion, actionEnable, oldSpeed

	try:
		if devId not in actionEnable:		return "","",False
		if not actionEnable[devId]:			return "","",False
		if not distanceActiveLimit[devId]:	return "","",False
		if distance == "":					return "","",False
		if speed == "": 					return "","",False

		if debugDistance: logger.log(20, "in  dist:{:6.1f}, speed:{:8.1f}, oldRegion:{:}, oldStop:{:}".format(
				distance, speed, oldRegion[devId], oldStop[devId]) )	
		previousRegion	= oldRegion[devId] 
		previousStop	= oldStop[devId] 

		if distanceActiveLimit[devId]:
			if		distance > actionVeryLongDistanceLimit[devId]:	region = "VeryLong"
			elif	distance > actionLongDistanceLimit[devId]:		region = "Long"
			elif 	distance < actionVeryShortDistanceLimit[devId]:	region = "VeryShort"
			elif 	distance < actionShortDistanceLimit[devId]:		region = "Short"
			else:													region = "Medium"


		if actionStopMinSpeed[devId] >0 and actionStopWait[devId] >0:
			if  (abs(speed) <= actionStopMinSpeed[devId] and time.time() - actionSpeedLast[devId] > actionStopWait[devId]):
				oldStop[devId], actionSpeedLast[devId] = execDistanceCommand("Stop", distance, speed, oldStop[devId], devId)
				#logger.log(20, "in stop active dist:{:6.1f}, speed:{:8.1f}, oldR:{:10s},newR:{:6s}, oldSTOP:{:1}, newSTOP:{:1}, tt-actionSpeedLast:{:.1f}, Wait:{}, MinSpeed:{}".format(distance, speed, oldRegion, region, previousStop, oldStop, time.time() - actionSpeedLast, actionStopWait, actionStopMinSpeed) )	
				oldStop[devId] = "Stop"
			elif abs(speed) > actionStopMinSpeed[devId]:
				oldStop[devId] = "dSpeed:{:.1f}".format(speed-oldSpeed[devId])
				#logger.log(20, "in stop reset  dist:{:6.1f}, speed:{:8.1f}, oldR:{:10s},newR:{:6s}, oldSTOP:{:1}, newSTOP:{:1}, tt-actionSpeedLast:{:.1f}, Wait:{}, MinSpeed:{}".format(distance, speed, oldRegion, region, previousStop, oldStop, time.time() - actionSpeedLast, actionStopWait, actionStopMinSpeed) )	

		if abs(speed) > actionStopMinSpeed[devId] and actionStopMinSpeed[devId] >0:
				oldRegion[devId], actionSpeedLast[devId] = execDistanceCommand(region, distance, speed, oldRegion[devId], devId)
		else:
				oldRegion[devId] = region

		if previousRegion != region:
			oldStop[devId] = "" 

		oldSpeed[devId] = speed
		if debugDistance: logger.log(20, "in  dist:{:6.1f}, speed:{:8.1f}, oldRegion:{:}, oldStop:{:}, previousRegion:{:}".format(
				distance, speed, oldRegion[devId], oldStop[devId], previousRegion) )	
		returns = [previousRegion, previousStop=="Stop", False]

		if oldStop[devId]	!= previousStop: 	returns[1] = oldStop == "Stop"; 	returns[2] = True
		if oldRegion[devId] != previousRegion: 	returns[0] = oldRegion[devId];		returns[2] = True
		if debugDistance: logger.log(20, "in  dist:{:6.1f}, speed:{:8.1f}, oldR:{:10s},newR:{:6s}, previousRegion:{:}, previousStop:{:1}, oldStop:{:1}, returns:{:}; tt-actionSpeedLast:{:.1f}, Wait:{}, MinSpeed:{}".format(
											distance,     speed,   oldRegion[devId],    region,  previousRegion,    previousStop, oldStop[devId], returns,    time.time() - actionSpeedLast[devId], actionStopWait[devId], actionStopMinSpeed[devId]) )	
		return returns

	except  Exception as e:
			logger.log(30,"", exc_info=True)
	return "","",False

#################################
def execDistanceCommand(region, distance, speed, oldAction, devId):
	global debugDistance, actionDistance, lastCommandExecuted,  actionSpeedLast
	try:
		if region == oldAction: return oldAction, actionSpeedLast[devId]

		if actionDistance[devId][region] != "":
			if len(actionDistance[devId][region]) > 3:
				# check if last command was the same if neopixel command, if yes do not execute again, otherwise yes.
				if debugDistance: logger.log(20, "neopix:{}  newcmd:{}".format("{}".format(actionDistance[devId][region]).find("neopixel") > -1, actionDistance[devId][region] == lastCommandExecuted[devId]))
				if not( "{}".format(actionDistance[devId][region]).find("neopixel") > -1 and actionDistance[devId][region] == lastCommandExecuted[devId]):
					if debugDistance: logger.log(20, "dist:{:6.1f}, speed:{:8.1f}, Action: old:{:10}, new:{:6}, lastAction:{}; action:{}".format(
												distance, speed, oldAction, region, lastCommandExecuted[devId], actionDistance[devId][region]) )	
					sendToNeopixel = actionDistance[devId][region]
					if "{}".format(sendToNeopixel).find("neopixel") > -1 and '"status":"' in sendToNeopixel:
						sendToNeopixel = sendToNeopixel.replace('"status":"','"fromDev":"{}","status":"'.format(devId))
					subprocess.call(sendToNeopixel, shell=True)
					lastCommandExecuted[devId] = actionDistance[devId][region]
		return region, time.time()   

	except  Exception as e:
			logger.log(30,"", exc_info=True)
	return oldAction, actionSpeedLast[devId]
######### distance actions ###### END ------------------------------------------------------------------
#################################
#################################
#################################



#################################
def readFloat(filename, default=0.):
	try:
		f = open(filename)
		v = float(f.read())
		f.close()
	except:
		try: f.close()
		except: pass
		v = default
	return v

#################################
def readInt(filename, default=0):
	try:
		f = open(filename)
		v = int(f.read())
		f.close()
	except:
		try: f.close()
		except: pass
		v = default
	return v


#################################
def getOsVersion():
	global OSVersion
	if OSVersion !=-1: return  OSVersion

	OSVersion = 8
	ret = (subprocess.Popen("/bin/cat /etc/os-release", shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").split("\n")
	for line in ret:
		try:
			if line.find("VERSION_ID=") == 0:
				items = line.split("=")
				OSVersion = int( items[1].strip('"') )
				#logger.log(10, "cBY:{:<20} os version:{}".format(G.program,osVersion) )
				break
		except Exception as e:
			logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return OSVersion


#################################
def doRead(inFile="{}temp/parameters".format(G.homeDir), lastTimeStamp="", testTimeOnly=False, deleteAfterRead=False):

	try:
		if not G.loggerSet:
			setLogging()

		t = 0
		if not os.path.isfile(inFile):
			if lastTimeStamp != "":
				return "","error",t
			return "","error"

		if testTimeOnly:  return "","", t

		t = os.path.getmtime(inFile)
		if lastTimeStamp != "":
			if lastTimeStamp == t:
				if testTimeOnly: return "","",t
				else: 			 return "","",t
		if testTimeOnly:  return "","",t 

		inp, inRaw = readJson(inFile)
		if deleteAfterRead: os.remove(inFile)

		if inp == {}:
			if not os.path.isfile(inFile):
				if lastTimeStamp != "":
					if lastTimeStamp == t: return "","error",t
				return "","error", 0
			time.sleep(0.1)
			inp, inRaw = readJson(inFile)
			if inp =={}:
				if inFile == "{}temp/parameters".format(G.homeDir):
					logger.log(20, "cBY:{:<20} doRead error empty file".format(G.program))
			if deleteAfterRead: os.remove(inFile)
			if lastTimeStamp != "":
				return "","error", t
			return "","error", 0

		if lastTimeStamp != "":
			return inp, inRaw, t
		return inp, inRaw, 0
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		if str(e).find("Too many open files") > -1:
			doReboot(tt=3, text=str(e), force=True)
	return "", "", 0

#################################
def setNetwork(mode):
	writeFile("temp/networkMODE", mode)
#################################
def clearNetwork():
	if os.path.isfile("{}temp/networkMODE".format(G.homeDir)):
		subprocess.call("rm {}temp/networkMODE".format(G.homeDir), shell=True)
#################################
def getNetwork():
	try:
		if os.path.isfile("{}temp/networkMODE".format(G.homeDir)):
			f=open("{}temp/networkMODE".format(G.homeDir),"r")
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
	try:
		sensors = {}
		oldDebug = G.debug

		G.ipOfServer =				inp.get("ipOfServer",G.ipOfServer)
		G.myPiNumber =				inp.get("myPiNumber",G.myPiNumber)
		G.portOfServer =			inp.get("portOfServer",G.portOfServer )
		G.IndigoOrSocket =			G.IndigoOrSocket
		G.BeaconUseHCINo =			inp.get("BeaconUseHCINo",G.BeaconUseHCINo)
		G.BLEconnectUseHCINo =		inp.get("BLEconnectUseHCINo",G.BLEconnectUseHCINo)
		G.enableRebootCheck =		inp.get("enableRebootCheck",G.enableRebootCheck)
		G.rpiIPNumber =				inp.get("rpiIPNumber",G.rpiIPNumber)
		G.networkType =				inp.get("networkType",G.networkType)
		G.getBatteryMethod =		inp.get("getBatteryMethod",G.getBatteryMethod)
		G.debug =					inp.get("debug",G.debug)
		G.ipNumberRpiStatic =		inp.get("ipNumberRpiStatic", G.ipNumberRpiStatic) == "1"

		try:	
			if "sendToIndigoSecs"	in inp:	 G.sendToIndigoSecs=	float(inp["sendToIndigoSecs"])
		except: pass
		try:	
			if "indigoInputPORT"	in inp:	 G.indigoInputPORT=		 int(inp["indigoInputPORT"])
		except: pass
		try:	
			if "rebootIfNoMessages"	in inp:	 G.rebootIfNoMessages=	 int(inp["rebootIfNoMessages"])
		except: pass
		try:	
			if u"deltaChangedSensor" in inp:  G.deltaChangedSensor=	float(inp["deltaChangedSensor"])
		except: pass


		if u"compressRPItoPlugin"	in inp:	 
			try:	G.compressRPItoPlugin =	int(inp["compressRPItoPlugin"])
			except: G.compressRPItoPlugin = 20000

		if u"wifiEth"				in inp:
			xxx = inp["wifiEth"]
			if len(xxx) == 2 and "eth0" in xxx and "wlan0" in xxx:
				if xxx != G.wifiEthOld:
					G.wifiEth = xxx
					G.wifiEthOld = G.wifiEth

		if u"shutDownPinOutput"		 in inp:
			try:							 	G.shutDownPinOutput=		int(inp["shutDownPinOutput"])
			except:							 	G.shutDownPinOutput=		-1

		if u"enableMuxI2C"			in inp:
			try:							 	G.enableMuxI2C=			int(inp["enableMuxI2C"])
			except:							 	G.enableMuxI2C=			-1
		else:
												G.enableMuxI2C=			-1
		if oldDebug != G.debug: setLogLevel()

		if "timeZone"	 in inp:
			if len(inp["timeZone"]) > 5 and G.timeZone !=	(inp["timeZone"]):
				G.timeZone 	= (inp["timeZone"])
				tznew  		= int(G.timeZone.split(" ")[0])
				writeTZ(iTZ=tznew)

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))

	return

#################################
def cleanUpSensorlist(sens, theSENSORlist):
	try:
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
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return {}
	
	
#################################
#######  reboot utils ##########
#################################
def doReboot(tt=10., text="", cmd="", force=False):
	try:
		setRebootedToday()
		setRebootingNow(text=text)
		time.sleep(tt)
		if cmd == "":
			subprocess.call("sh /home/pi/pibeacon/forceReboot.sh &",shell=True)
		else:
			subprocess.call(cmd,shell=True)

		doRebootThroughRUNpinReset()
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return 

#################################
def checkifRebootedToday():
	if not os.path.isfile("{}rebootedToday".format(G.homeDir)): return False
	if time.localtime(os.path.getmtime("rebootedToday")).tm_mday == datetime.datetime.now().day: return True
	return False

#################################
def resetRebootedToday():
	if os.path.isfile("{}rebootedToday".format(G.homeDir)):
		os.remove("{}rebootedToday".format(G.homeDir))
	return 
#################################

def resetRebootRequest():
	if os.path.isfile("{}temp/rebootNeeded".format(G.homeDir)):
		os.remove("{}temp/rebootNeeded".format(G.homeDir))
	return 

#################################
def setRebootedToday(text=""):
	doWriteSimpleFile("{}rebootedToday".format(G.homeDir), text)
	return 

#################################
def setRebootRequest(reason):
	doWriteSimpleFile("{}temp/rebootNeeded".format(G.homeDir), reason)
	return 

#################################
def resetRebootingNow():
	if os.path.isfile("{}temp/rebooting.now".format(G.homeDir)):
		os.remove("{}temp/rebooting.now".format(G.homeDir))
	return 

#################################
def setRebootingNow(text=""):
	doWriteSimpleFile("{}temp/rebooting.now".format(G.homeDir), "rebooting / shutdown {}".format(text) )
	return 
	
#################################
def checkifRebooting():
	if os.path.isfile("{}temp/rebooting.now".format(G.homeDir)): return True
	return False
	
#################################
def checkifRebootRequested():
	if not os.path.isfile("{}temp/rebootNeeded".format(G.homeDir)): return ""
	f = open(G.homeDir+"temp/rebootNeeded") 
	try: reason = f.read()
	except: reason = "other"
	f.close()
	if reason == "": return "other"
	return reason

#################################
def doRebootThroughRUNpinReset(tt =20):
	if G.shutDownPinOutput > 1:
		setRebootingNow()
		time.sleep(tt)
		GPIO.setup(G.shutDownPinOutput, GPIO.OUT)
		GPIO.output(G.shutDownPinOutput, True)
		GPIO.output(G.shutDownPinOutput, False)
	return 

#################################
def sendRebootHTML(reason, reboot=True, force=False, wait=10.):
	sendURL(sendAlive="reboot", text=reason)
	setRebootingNow()
	if reboot:
		doReboot(tt=wait, text=reason,force=force)
	else:
		doReboot(tt=wait, text=reason, cmd="/usr/bin/sudo /usr/bin/killall -9 python3; sleep 1; shutdown -r now ")

	return

#################################
#######  restart utils ##########
#################################
def checkifRestartedToday():
	if not os.path.isfile("{}restartedoday".format(G.homeDir)): return False
	if time.localtime(os.path.getmtime("restartedoday")).tm_mday == datetime.datetime.now().day: return True
	return False

#################################
def resetRestartedToday():
	if os.path.isfile("{}restartedToday".format(G.homeDir)):
		os.remove("{}restartedToday".format(G.homeDir))
	return 

#################################
def setRestartedToday(text=""):
	doWriteSimpleFile("{}restartedToday".format(G.homeDir), text)
	return 

#################################
def setRestartRequest(reason):
	doWriteSimpleFile("{}temp/restartNeeded".format(G.homeDir), reason)
	return 

#################################
def resetRestartRequest():
	if os.path.isfile("{}restartNeeded".format(G.homeDir)):
		os.remove("{}restartNeeded".format(G.homeDir))
	return 

#################################
def resetRestartingNow():
	if os.path.isfile("{}temp/restarting".format(G.homeDir)):
		os.remove("{}temp/restarting.now".format(G.homeDir))
	return 

#################################
def setRestaringNow(text=""):
	doWriteSimpleFile("{}temp/restarting.now".format(G.homeDir), "rebooting / shutdown {}".format(text) )
	return 
	
#################################
def checkifRestarting():
	if os.path.isfile("{}temp/restarting.now".format(G.homeDir)): return True
	return False
	
#################################
def checkifRestartRequested():
	if not os.path.isfile("{}temp/restartNeeded".format(G.homeDir)): return ""
	f = open(G.homeDir+"temp/restartNeeded") 
	reason = f.read()
	f.close()
	return reason




#################################
def manualStartOfRTC():
	try:
		global checkIfmanualStartOfRTC
		try:
			y=checkIfmanualStartOfRTC
			logger.log(20, "cBY:{:<20} RTC clock not needed, network connection present".format(G.program))
			return 
		except:
			checkIfmanualStartOfRTC = 1
	
		ret = (subprocess.Popen("/usr/bin/timedatectl status " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip()
		if ret.find("NTP service: activex") > -1:
			logger.log(20, "cBY:{:<20} RTC clock not needed, network connection present".format(G.program))
			return

		logger.log(20, "cBY:{:<20} starting RTC clock manually".format(G.program))
		subprocess.call("/usr/bin/sudo bash -c 'echo ds1307 0x68 > /sys/class/i2c-adapter/i2c-1/new_device'", shell=True)
		subprocess.call("sudo hwclock -s", shell=True)
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return
		



#################################
def setUpRTC(useRTCnew):
	try:
		global initRTC
		try:
			if initRTC:
				initRTC=False
		except:
				initRTC=True


		if useRTCnew == "manual":
			return

		if useRTCnew not in ["ds3231","ds1307"]: useRTCnew ="0"

		if	G.useRTC == useRTCnew and not initRTC: # return if not first and no change
			return

		bootFile = getBootFileName()



		if useRTCnew == "ds3231":
			if findString("dtoverlay=i2c-rtc,ds3231", bootFile) == 2: # already there ?
				G.useRTC = useRTCnew
				return

			uncommentOrAdd("/sbin/hwclock -s|| echo \"hwclock not working\"","/etc/rc.local",	 before="(sleep ")
			removefromFile("dtoverlay=i2c-rtc,ds1307", bootFile)
			uncommentOrAdd("dtoverlay=i2c-rtc,ds3231", bootFile, before="")
			removefromFile("if [ -e /run/systemd/system ]", "/lib/udev/hwclock-set",nLines=3)
			subprocess.call("apt-get -y remove fake-hwclock", shell=True)
			doReboot(tt=30, text="installing HW clock" )

		elif useRTCnew == "ds1307":
			if findString("dtoverlay=i2c-rtc,ds1307",	bootFile) == 2: # already done ?
				G.useRTC = useRTCnew
				return
			uncommentOrAdd("/sbin/hwclock -s|| echo \"hwclock not working\"","/etc/rc.local", before="(sleep ")
			removefromFile("dtoverlay=i2c-rtc,ds3231", bootFile)
			uncommentOrAdd("dtoverlay=i2c-rtc,ds1307", bootFile, before="")

			# in /lib/udev/hwclock-set ADD # infront of
			#if [ -e /run/systemd/system ] ; then
			# exit 0
			#fi
			removefromFile("if [ -e /run/systemd/system ]", "/lib/udev/hwclock-set",nLines=3)
			subprocess.call("/usr/bin/sudo chmod a+x  /lib/udev/hwclock-set", shell=True)
			subprocess.call("apt-get -y remove fake-hwclock", shell=True)
			doReboot(tt=30, text="installing HW clock")

		else:
			if (findString("dtoverlay=i2c-rtc,ds1307", bootFile) != 2 and
				findString("dtoverlay=i2c-rtc,ds3231", bootFile) != 2 ) : # already done ?
				G.useRTC = useRTCnew
				return

			removefromFile("dtoverlay=i2c-rtc,ds3231",bootFile)
			removefromFile("dtoverlay=i2c-rtc,ds1307",bootFile)
			removefromFile('/sbin/hwclock -s|| echo "hwclock not working"', "/etc/rc.local" )
			# in /lib/udev/hwclock-set REMOVE # infront of
			#if [ -e /run/systemd/system ] ; then
			# exit 0
			#fi
			subprocess.call("cp {}hwclock.set.nohwclock /lib/udev/hwclock-set".format(G.homeDir), shell=True)
			subprocess.call("/usr/bin/sudo chmod a+x  /lib/udev/hwclock-set", shell=True)
			subprocess.call("apt-get -y install fake-hwclock", shell=True)

		doReboot(tt=30, text=" .. reason de installing HW clock" ,cmd="")
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def getIPNumber(doPrint=True):
	ipAddressRead = ""
	###  if G.networkType  not in G.useNetwork or G.wifiType !="normal": return 0
	try:
		f = open("{}ipAddress".format(G.homeDir),"r")
		ipAddressRead = f.read().strip(" ").strip("\n").strip(" ")
		f.close()
		if isValidIP(ipAddressRead):
			if G.ipAddress != ipAddressRead:
				if doPrint: logger.log(20, "cBY:{:<20} found new IP number:{}, old:{}".format(G.program, ipAddressRead, G.ipAddress))
			G.ipAddress = ipAddressRead
			return 0
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	logger.log(30, "cBY:{:<20} no ip number defined".format(G.program))

	return 1


def isValidIP(ip0):
	ipx = ip0.split(".")
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
	ret = (subprocess.Popen("hostname -I " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip()
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
	G.eth0Active		= False
	G.wifiActive		= False

	try:

		osVersion = getOsVersion()
		if osVersion > 7:
			retIp = (subprocess.Popen("/sbin/ip addr show " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip().split("\n")

			#	1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
			#	    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
			#	    inet 127.0.0.1/8 scope host lo
			#	       valid_lft forever preferred_lft forever
			#	    inet6 ::1/128 scope host
			#	2: eth0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc pfifo_fast state DOWN group default qlen 1000
			#	    link/ether b8:27:eb:37:90:c9 brd ff:ff:ff:ff:ff:ff
			#	    inet 192.168.1.121/24 brd 192.168.1.255 scope global eth0
			#	       valid_lft forever preferred_lft forever
			#	3: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
			#	    link/ether b8:27:eb:62:c5:9c brd ff:ff:ff:ff:ff:ff
			#	    inet 192.168.1.104/24 brd 192.168.1.255 scope global wlan0
			#	       valid_lft forever preferred_lft forever
			#	    inet6 fe80::ba27:ebff:fe62:c59c/64 scope link
			#	       valid_lft forever preferred_lft forever

			ind 		= -1
			section 	= 0
			oldSection	= -1
			dev			= ["","","","","","","",""]
			state		= ["","","","","","","",""]
			mac			= ["","","","","","","",""]
			ip			= ["","","","","","","",""]
			rxBytes		= [0,0,0,0,0,0,0,0]
			txBytes		= [0,0,0,0,0,0,0,0]
			rxPackets	= [0,0,0,0,0,0,0,0]
			rxBytes		= [0,0,0,0,0,0,0,0]
			txPackets	= [0,0,0,0,0,0,0,0]
			for line in retIp:
				lineItems = line.split()
				if line[1] == ":":
					section =int(line[0])
				if oldSection != section:
					ind += 1
					oldSection = section
					dev[ind] = lineItems[1].strip(":")
					state[ind] = line.split(" state ")[1].split(" ")[0]
				if lineItems[0] == "inet":
					ip[ind] = lineItems[1].split("/")[0]
				if lineItems[0] == "link/ether":
					mac[ind] = lineItems[1]
			ind +=1

			retBytes = (subprocess.Popen("/bin/cat /proc/net/dev" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip().split("\n")
			#	Inter-|   Receive                                                |  Transmit
			#	 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
			#	  eth0:   48686     595    0    0    0     0          0         0     6488      38    0    0    0     0       0          0
			#		lo: 3137748  487135    0    0    0     0          0         0 43137748  487135    0    0    0     0       0          0
			#	 wlan0: 3220685   14907    0    0    0     0          0      6469  1530314    5879    0    0    0     0       0          0
			for line in retBytes:
				lineItems = line.split()
				if len(lineItems) < 11: continue
				dd = lineItems[0].strip(":").strip()

				for ii in range(ind):
					ddd = dev[ii]
					if ddd == dd:
						rxBytes[ii]   = lineItems[1]
						rxPackets[ii] = lineItems[2]
						txBytes[ii]   = lineItems[9]
						txPackets[ii] = lineItems[10]

			for line in retBytes:
				lineItems = line.split()
				if len(lineItems) < 11: continue
				dd = lineItems[0].strip(":").strip()

				for ii in range(ind):
					ddd = dev[ii]
					if ddd == dd:
						rxBytes[ii]   = lineItems[1]
						rxPackets[ii] = lineItems[2]
						txBytes[ii]   = lineItems[9]
						txPackets[ii] = lineItems[10]

			G.ipOfRouter = getIPofRouter()

			retwifiID = (subprocess.Popen("/sbin/iwgetid " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip()
			if retwifiID.find(":") >-1:
				G.wifiID = retwifiID.split(":")[1]
			for ii in range(ind):
				ddd = dev[ii]
				if ddd == "eth0":
					if  ip[ii].find("169.254.") == -1: # this is a dummy address
						eth0IP 	  = ip[ii]
						G.eth0Packets = rxPackets[ii]
						G.eth0Packets = rxPackets[ii]
						G.eth0Enabled = True
						G.eth0Active  = state[ii] == "UP"
				if ddd == "wlan0" or ddd == "wlan1" :
					if  ip[ii].find("169.254.") == -1:
						G.wlan0Packets = rxPackets[ii]
						wlan0IP 	   = ip[ii]
						G.wifiActive  = state[ii] == "UP"
						G.wifiEnabled = True
						if G.wifiID == "": G.wifiActive = False
						if not G.wifiActive: 
							G.wifiEnabled = False


			#logger.log(20, "cBY:{:<20} network info: \ndevs:     {}\nstate:    {}\nmac:      {}\nip:       {}\nrxBytes: {}\nrxPackets:{}\ntxBytes:   {}\ntxPackets:{}".format(G.program, dev, state,  mac, ip, rxBytes, rxPackets ,txBytes, txPackets))
			#logger.log(20, "cBY:{:<20} network info: G.wifiID:{}, G.wifiActive:{},  G.wifiEnabled:{}".format(G.program, G.wifiID , G.wifiActive,  G.wifiEnabled))


		else:  # pre os v 8
			retIfconfig = (subprocess.Popen("/sbin/ifconfig " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip()
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
			retwifiID = (subprocess.Popen("/sbin/iwgetid " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip()

			if retIfconfig.find("lo") > -1:
				packets 	= retIfconfig
				networks 	= retIfconfig
				ifconfig 	= True
			else:
				packets = (subprocess.Popen("cat /proc/net/dev " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip()
				#Inter-|   Receive                                                |  Transmit
				# face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
				#    lo: 6758900   28590    0    0    0     0          0         0  6758900   28590    0    0    0     0       0          0
				#  eth0: 147198293 1008371    0   69    0     0          0         0  9488704   80818    0    0    0     0       0          0
				networks = (subprocess.Popen("ip -4 a show ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip()
				#1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
				#    inet 127.0.0.1/8 scope host lo
				#       valid_lft forever preferred_lft forever
				#2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
				#    inet 192.168.1.21/24 brd 192.168.1.255 scope global eth0
				#      valid_lft forever preferred_lft forever
				ifconfig = False


			retRoute= (subprocess.Popen("/sbin/route " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip()
				#/sbinstr(/route
				#Kernel IP routing table
				#Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
				#default         GatewayUSG4     0.0.0.0         UG    303    0        0 wlan0 <== gateway
				#192.168.1.0     0.0.0.0         255.255.255.0   U     303    0        0 wlan0
				#  or
				##Kernel IP routing table
				#Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
				#192.168.1.0     0.0.0.0         255.255.255.0   U     0      0        0 eth0
				#192.168.1.0     0.0.0.0         255.255.255.0   U     0      0        0 wlan0

			if  retRoute.find(" eth0") > -1:   G.eth0Active  = True
			if  retRoute.find(" wlan0") > -1:  G.wifiActive  = True
			if  retRoute.find(" wlan1") > -1:  G.wifiActive  = True

			if networks.find("wlan0   ") > -1: G.wifiEnabled = True
			if networks.find("wlan1   ") > -1: G.wifiEnabled = True
			if networks.find("eth0   ")  > -1: G.eth0Enabled = True

			if networks.find("wlan0:") > -1:   G.wifiEnabled = True
			if networks.find("wlan1:") > -1:   G.wifiEnabled = True
			if networks.find("eth0:")  > -1:   G.eth0Enabled = True



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
							##subprocess.call("/usr/bin/sudo ifconfig eth0 down", shell=True)

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

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))

	G.packetsTime = time.time()
	return eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled


################################
def getIPofRouter():
	try:
		retRoute = (subprocess.Popen("/sbin/ip route" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip().split("\n")
		#default via 192.168.1.1 dev eth0 proto dhcp src 192.168.1.22 metric 202
		#192.168.1.0/24 dev eth0 proto dhcp scope link src 192.168.1.22 metric 202
		for line in retRoute:
			lineItems = line.split()
			#logger.log(20, "cBY:{:<20} lineItems:{}".format(G.program, lineItems))
			if len(lineItems) > 1 and lineItems[0] == "default" and isValidIP(lineItems[2]):
				return  lineItems[2]
				break
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return ""

################################
def whichWifi():
	try:
		lines = ""
		if os.path.isfile("/etc/network/interfaces"):
			f = open("/etc/network/interfaces","r")
			lines = f.read()
			f.close()
		if	lines.find(" ad-hoc") > -1 and lines.find("wireless-mode") > -1 and lines.find("clock") > -1:
			G.wifiType = "adhoc"
		else:
			G.wifiType = "normal"
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return G.wifiType

################################
def checkWhenAdhocWifistarted():
	try:
		if not os.path.isfile("{}adhocWifistarted.time".format(G.homeDir)): return -1
		xxx, ddd = readJson("{}adhocWifistarted.time".format(G.homeDir))
		if  xxx =={}: return -1
		if "startTime" in xxx:
			return xxx["startTime"]
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return -1

#################################
def startAdhocWifi():
	try:
		logger.log(30, "cBY:{:<20}  prepAdhoc Wifi: starting wifi servers as clock  no password ".format(G.program))
		#subprocess.call("/usr/bin/sudo ifconfig wlan0 up", shell=True)
		#subprocess.call("/usr/bin/sudo iwconfig wlan0 mode ad-hoc", shell=True)
		#subprocess.call('/usr/bin/sudo iwconfig wlan0 essid "clock"', shell=True)
		#subprocess.call("/usr/bin/sudo ifconfig wlan0 192.168.5.5 netmask 255.255.255.0", shell=True)
		subprocess.call("/usr/bin/sudo cp /etc/network/interfaces {}interfaces-fromBeforeAdhoc".format(G.homeDir), shell=True)
		subprocess.call("/usr/bin/sudo cp /etc/wpa_supplicant/wpa_supplicant.conf {}wpa_supplicant.conf-fromBeforeAdhoc".format(G.homeDir), shell=True)
		subprocess.call("/usr/bin/sudo cp {}interfaces-adhoc /etc/network/interfaces".format(G.homeDir), shell=True)
		subprocess.call("/usr/bin/sudo rm /etc/wpa_supplicant/wpa_supplicant.conf", shell=True)
		writeJson("{}adhocWifistarted.time".format(G.homeDir), {"startTime":time.time()})
		time.sleep(2)
		doReboot(tt=0)
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def prepNextNormalRestartFromAdhocWifi():
	try:
		if  os.path.isfile("{}interfaces-fromBeforeAdhoc".format(G.homeDir)):
			logger.log(20, "cBY:{:<20}  restoring wifi /etc/network/interface file from before wifi adhoc start ".format(G.program))
			subprocess.call('/usr/bin/sudo cp {}interfaces-fromBeforeAdhoc /etc/network/interfaces'.format(G.homeDir), shell=True)
			subprocess.call('/usr/bin/sudo cp {}wpa_supplicant.conf-fromBeforeAdhoc /etc/wpa_supplicant/wpa_supplicant.conf'.format(G.homeDir), shell=True)
			subprocess.call("/usr/bin/sudo rm {}interfaces-fromBeforeAdhoc".format(G.homeDir), shell=True)
			time.sleep(0.1)
		else:
			logger.log(20, "cBY:{:<20}  restoring wifi /etc/network/interface not needed, adhoc file not present ".format(G.program))
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return
#################################
def stopAdhocWifi():
	try:
		prepNextNormalRestartFromAdhocWifi()
		clearAdhocWifi()
		logger.log(50, "cBY:{:<20}  stopping wifi, restoring wifi active (dhcp) interface file and reboot".format(G.program))
		#subprocess.call('/usr/bin/sudo cp {}dhclient.conf-fast /etc/dhcp/dhclient.conf'.format(G.homeDir), shell=True)
		time.sleep(2)
		doReboot(tt=0)
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def clearAdhocWifi():
	try:
		logger.log(20, "cBY:{:<20}  clearing adhoc files".format(G.program))

		if  os.path.isfile("{}adhocWifistarted.time".format(G.homeDir)):
			subprocess.call("/usr/bin/sudo rm {}adhocWifistarted.time".format(G.homeDir), shell=True)

		if os.path.isfile("{}temp/adhocWifi.stop".format(G.homeDir)):
			subprocess.call("/usr/bin/sudo rm {}temp/adhocWifi.stop".format(G.homeDir), shell=True)
			subprocess.call("/usr/bin/sudo rm {}temp/adhocWifi.start".format(G.homeDir), shell=True)

		if  os.path.isfile("{}adhocWifistarted.time".format(G.homeDir)):
			subprocess.call("/usr/bin/sudo rm {}adhocWifistarted.time".format(G.homeDir), shell=True)
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return


#################################
def startWiFi():
	try:

		if G.wifiEth["wlan0"]["on"] == "dontChange": return
		logger.log(20, "cBY:{:<20} starting WiFi".format(G.program) )
		subprocess.call("/usr/bin/sudo rfkill unblock all", shell=True)

		osVersion = getOsVersion()
		# new tool to be converted..  --> use ip instead if ifconfig
		# ip link set dev wlan1 up
		# /usr/bin/sudo ip addr flush dev eth0
		time.sleep(0.5)
		ret = []
		ret.append((subprocess.Popen("/usr/bin/sudo rfkill unblock all" 				,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())

		ret.append((subprocess.Popen("/usr/bin/sudo wpa_cli -i wlan0 reconfigure " 	,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		if osVersion < 8:
			ret.append((subprocess.Popen("/usr/bin/sudo ifconfig wlan0 up " 			,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		else:
			ret.append((subprocess.Popen("/usr/bin/sudo /sbin/ip link set wlan0 up " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		ret.append((subprocess.Popen("/usr/bin/sudo wpa_supplicant -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf & /usr/bin/sudo dhcpcd wlan0&" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		time.sleep(0.5)
		ret.append((subprocess.Popen("/usr/bin/sudo wpa_cli -i wlan0 reconfigure " 	,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		ret.append((subprocess.Popen("/usr/bin/sudo wpa_cli -i wlan0 reassociate " 	,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		ret.append((subprocess.Popen("/usr/bin/sudo /etc/init.d/networking restart&" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		#subprocess.call('/usr/bin/sudo cp {}dhclient.conf-fast /etc/dhcp/dhclient.conf'.format(G.homeDir), shell=True)
		logger.log(30, "cBY:{:<20} starting Wifi: {}".format(G.program, ret))
		G.wifiEnabled = True
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))

	return
#################################
def startEth():
	try:
		ret = []
		if G.wifiEth["eth0"]["on"] == "dontChange": return
		osVersion = getOsVersion()
		ret.append((subprocess.Popen("/usr/bin/sudo rfkill unblock all" 				,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		if osVersion < 8:
			ret.append((subprocess.Popen("/usr/bin/sudo ifconfig eth0 up " 			,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		else:
			ret.append((subprocess.Popen("/usr/bin/sudo /sbin/ip link set  eth0 up " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		ret.append((subprocess.Popen("/usr/bin/sudo dhcpcd eth0&" 					,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		ret.append((subprocess.Popen("/usr/bin/sudo /etc/init.d/networking restart&" 	,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		#subprocess.call('/usr/bin/sudo cp {}dhclient.conf-fast /etc/dhcp/dhclient.conf'.format(G.homeDir), shell=True)
		logger.log(30,  "cBY:{:<20} starting ETH: {}".format(G.program, ret))
		G.eth0Enabled = True
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def stopWiFi(calledFrom=""):
	try:
		ret = []
		osVersion = getOsVersion()
		if G.wifiEth["wlan0"]["on"] == "dontChange": return
		logger.log(30, "cBY:{:<20} stopping WiFi: called from:{}".format(G.program, calledFrom))
		ret.append((subprocess.Popen("/usr/bin/sudo rfkill unblock all"    	,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		if osVersion < 8:
			ret.append((subprocess.Popen("/usr/bin/sudo ifconfig wlan0 down " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		else:
			ret.append((subprocess.Popen("/usr/bin/sudo /sbin/ip link set wlan0 down " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())

		logger.log(30, "cBY:{:<20} stopping WiFi: {}; called from:{}".format(G.program, ret, calledFrom))
		G.wifiEnabled = False
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return
#################################
def stopEth():
	try:
		if G.wifiEth["eth0"]["on"] == "dontChange": return
		osVersion = getOsVersion()
		ret = []
		ret.append((subprocess.Popen("/usr/bin/sudo rfkill unblock all"   ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		if osVersion < 8:
			ret.append((subprocess.Popen("/usr/bin/sudo ifconfig eth0 down " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())
		else:
			ret.append((subprocess.Popen("/usr/bin/sudo /sbin/ip link set  eth0 down " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip())

		logger.log(30, "cBY:{:<20} stopping ETH: {}".format(G.program, ret))
		G.eth0Enabled = False
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def stopDisplay():
	subprocess.call("echo stop > {}temp/display.inp".format(G.homeDir), shell=True)
	return



#################################
def startwebserverINPUT(port, useIP="", force=False):
	global startwebserverINPUTTries
	try: 
		startwebserverINPUTTries +=1
	except:
		startwebserverINPUTTries = 0

	try:
		if startwebserverINPUTTries > 5: return
		if checkIfStartwebserverINPUT() and not force: return
		outFile	="{}temp/webparameters.input".format(G.homeDir)
		ip = G.ipAddress
		if useIP !="":
			ip = useIP
		if len(ip) > 8:
			cmd = "/usr/bin/sudo /usr/bin/python3 {}webserverINPUT.py  {} {} {}  > /dev/null 2>&1  &".format(G.homeDir, ip, port, outFile ) #, G.sundialActive)
			logger.log(20, "cBY:{:<20} starting web server:{}".format( G.program, cmd) )
			if os.path.isfile(outFile):
				subprocess.call('rm {}'.format(outFile), shell=True)
			subprocess.call(cmd, shell=True)
		else:
			logger.log(20, "cBY:{:<20} starting web server INPUT.. error no ip number".format(G.program) )

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def stopwebserverINPUT():
	killOldPgm(-1,"/webserverINPUT.py")
	return

#################################
def startwebserverSTATUS(port, useIP="", force=False):
	global startwebserverSTATUSTries
	try: 
		startwebserverSTATUSTries +=1
	except:
		startwebserverSTATUSTries = 0
	try:
		if startwebserverSTATUSTries > 5: return
		if checkIfStartwebserverSTATUS() and not force and startwebserverSTATUSTries >3: return
		outFile	= "{}temp/webserverSTATUS.show".format(G.homeDir)
		ip = G.ipAddress
		if useIP !="":
			ip = useIP
		if len(ip) > 8:
			cmd = "/usr/bin/sudo /usr/bin/python3 {}webserverSTATUS.py  {} {} {}  > /dev/null 2>&1  &".format(G.homeDir, ip, port, outFile)
			logger.log(20, "cBY:{:<20} starting web server:{}".format(G.program, cmd) )
			if os.path.isfile(outFile):
				subprocess.call('rm {}'.format(outFile), shell=True)
			subprocess.call(cmd, shell=True)
		else:
			logger.log(20, "cBY:{:<20}  starting web server STATUS.. error no ip number".format(G.program) )


	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))

	return

#################################
def stopwebserverSTATUS():
	logger.log(30, "cBY:{:<20} webserverSTATUS stop".format(G.program) )
	killOldPgm(-1,"/webserverSTATUS.py")
	return


#################################
def setStartwebserverINPUT():
	setFileTo("{}temp/webserverINPUT.start".format(G.homeDir), "start")
	return
#################################
def setStopwebserverINPUT():
	setFileTo("{}temp/webserverINPUT.stop".format(G.homeDir), "stop")
	return
#################################
def setStartwebserverSTATUS():
	setFileTo("{}temp/webserverSTATUS.start".format(G.homeDir), "start")
	return
#################################
def setStopwebserverSTATUS():
	setFileTo("{}temp/webserverSTATUS.stop".format(G.homeDir), "stop")
	return
#################################
def setStartAdhocWiFi():
	setFileTo("{}temp/adhocWifi.start".format(G.homeDir), "start")
	return
#################################
def setStopAdhocWiFi():
	setFileTo("{}temp/adhocWifi.stop".format(G.homeDir), "stop")
	return
#################################
def setFileTo(file, value):
	subprocess.call('echo  '+value+' > '+file, shell=True)
	return


#################################
def checkIfStartAdhocWiFi():
	return testForFile("{}temp/adhocWifi.start".format(G.homeDir))

#################################
def checkIfStopAdhocWiFi():
	return testForFile("{}temp/adhocWifi.stop".format(G.homeDir))

#################################
def checkIfStartwebserverINPUT():
	return testForFile("{}temp/webserverINPUT.start".format(G.homeDir))

#################################
def checkIfwebserverINPUTrunning():
	if pgmStillRunning("/webserverSTATUS.py"): return True
	return False

#################################
def checkIfStopwebserverINPUT():
	return testForFile("{}temp/webserverINPUT.stop".format(G.homeDir))

#################################
def checkIfStartwebserverSTATUS():
	return testForFile("{}temp/webserverSTATUS.start".format(G.homeDir))

#################################
def checkIfStopwebserverSTATUS():
	return testForFile("{}temp/webserverSTATUS.stop".format(G.homeDir))


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
	logger.log(10, "cBY:{:<20} updating web status {}".format(G.program, data))
	writeFile("temp/webserverSTATUS.show", data)
	return


#################################
def updateWebINPUT(data):
	logger.log(10, "cBY:{:<20} updating web INPUT {}".format(G.program, data))
	writeFile("temp/webserverINPUT.show", data)
	return

#################################
def testForFile(fname):
	if os.path.isfile(fname):
		subprocess.call('/usr/bin/sudo rm '+fname, shell=True)
		return True
	return False


#################################
def checkwebserverINPUT():
	try:
		newFile = False
		fName	= "{}temp/webparameters.input".format(G.homeDir)
		if not  os.path.isfile(fName): return newFile
		data = {}
		ddd  = ""
		try:
			data, ddd = readJson(fName)
		except:
			pass
		subprocess.call('rm '+fName, shell=True)

		if len(ddd) > 3 and data !={}:
			if "timezone" in data and len(data["timezone"]) >0:
				try:
					iTZ = int(data["timezone"])
					if iTZ != 99:
						try:
							xxx=G.timeZones[iTZ+12]
							subprocess.call("rm {}timezone.set".format(G.homeDir), shell=True)
							writeTZ(iTZ=iTZ, force=True )
							newFile = True
							writeJson("{}timezone.set".format(G.homeDir), {"timezone":data["timezone"]}, sort_keys=False, indent=0)
						except: pass
				except Exception as e:
					logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
			if makeNewSupplicantFile(data):
				newFile = True
			return newFile

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return newFile



###############################
def getTZ():

#timedatectl
#      Local time: Sat 2019-08-17 13:04:28 CDT
#  Universal time: Sat 2019-08-17 18:04:28 UTC
#        RTC time: Sat 2019-08-17 18:04:28
#       Time zone: US/Central (CDT, -0500)
# Network time on: yes
#NTP synchronized: yes
# RTC in local TZ: no

	try:
		ret  = (subprocess.Popen("timedatectl" ,shell=True,stdout=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip("\r").split("\n")
	except:
		return ""
	try:
		for line in ret:
			if line.lower().find("time zone:") > -1:
				return line.split(":")[1]
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return ""
###############################
def getTZNumber():

# returns time relative to GMZ
	tznumber = ""
	try:
		#JulDelta = int(subprocess.Popen("date -d '1 Jul' +%z " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100
		JanDelta = int(subprocess.Popen("date -d '1 Jan' +%z " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100
		#NowDelta = int(subprocess.Popen("date  +%z "		   ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip())/100
		tznumber = JanDelta
	except: pass	
	return tznumber
###############################
def writeTZ( iTZ = 99, cTZ="",force=False ):
	try:

		if iTZ == 99: return
		try:
			newTZ = G.timeZones[iTZ+12]
		except:
			logger.log(30, "cBY:{:<20}  bad tz given: iTZ:{}".format(G.program, iTZ))
			return

		"""
		date +"%Z %z"  			-->		CDT -0500
		date -d '1 Jan' +%z		-->		-0600
		date -d '1 Jul' +%z  	-->		-0500
		date +%z 				--> 	-0500
		"""
		summerHH = int((subprocess.Popen("date -d '1 Jul' +%z" ,shell=True,stdout=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip("\r"))/100
		winterHH = int((subprocess.Popen("date -d '1 Jan' +%z" ,shell=True,stdout=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip("\r"))/100
		currTZHH  = int((subprocess.Popen("date  +'%z'" ,shell=True,stdout=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip("\r"))/100
		storediTZr, raw = readJson("{}timezone.set".format(G.homeDir))

		deltaSW 		=  int(winterHH - summerHH)
		if currTZHH == winterHH: deltaSW = 0
		iTZC 			= iTZ
		currTZC 		=  int(currTZHH + deltaSW)
		setNewStored 	= 99
		setNewStoredC	= 99
		storediTZ		= 99
		if "timezone" in storediTZr:
			storediTZ = int(storediTZr["timezone"])
		if storediTZ != 99:
			try:
				setNewStored  =  int(storediTZ)
				setNewStoredC =  int(setNewStored + deltaSW)
			except:
				subprocess.call("rm {}timezone.set".format(G.homeDir), shell=True)

		logger.log(10, "cBY:{:<20}  iTZ:{},  iTZC:{}, newTZ:{},  summerHH:{},  winterHH:{},  currTZHH:{}, currTZC:{}, deltaSW:{}, storediTZ:{}, storediTZr:{}, setNewStored:{},  setNewStoredC:{}, force:{}".format(G.program, iTZ, iTZC, newTZ, summerHH, winterHH, currTZHH, currTZC, deltaSW, storediTZ, storediTZr, setNewStored, setNewStoredC, force))

		setNew =  int(iTZ)
		if setNewStored < 30: setNew =  int(setNewStored)

		G.timeZone = "{}  {}".format(setNew, G.timeZones[setNew+12])

		if force  or  (setNewStoredC != 99 and setNewStoredC != currTZC)  or  int(iTZC) != int(currTZC):


			if  setNew < 30 and (setNew != currTZC or force):
				logger.log(20, "cBY:{:<20} changing timezone from: {}:{} to: {}:{}".format(G.program, currTZC,G.timeZones[currTZC+12], setNew, G.timeZones[setNew+12]) )
				if currTZC != iTZ:
					logger.log(30, "cBY:{:<20} changing timezone executing".format(G.program))
					if os.path.isfile("/usr/share/zoneinfo/{}".format(G.timeZones[setNew+12])):
						subprocess.call("/usr/bin/sudo timedatectl set-timezone {}".format(G.timeZones[setNew+12]) , shell=True)
						logger.log(20, "cBY:{:<20} changing timezone done".format(G.program))
						inp, raw, x = doRead()
						if raw != "error" and raw != "":
							if "timeZone" in inp:
								inp["timeZone"] = u"{} {}".format(setNew, G.timeZones[setNew+12])
								writeJson(u"{}parameters".format(G.homeDir), inp, sort_keys=True)
								subprocess.call("touch {}temp\touchFile".format(G.homeDir), shell=True)
					# must restart master to get clean restart w new time 
						if sys.version_info[0] == 3:
							cmd = "/usr/bin/sudo /usr/bin/python3 master.py &".format(G.homeDir)
						else:
							cmd = "/usr/bin/sudo /usr/bin/python master.py &".format(G.homeDir)
						subprocess.call(cmd, shell=True)
					else:
						logger.log(20, "cBY:{:<20} error bad timezone:{}".format(G.program, G.timeZones[setNew+12]) )




	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return




#################################... not used !!
def resetWifi(defaultFile= "interfaces-DEFAULT-clock"):
	try:
		logger.log(30, "cBY:{:<20} resetting wifi to default for next re-boot".format(G.program))
		if os.path.isfile("{}{}".format(G.homeDir, defaultFile)):
			subprocess.call("cp {}{} /etc/network/interfaces".format(G.homeDir, defaultFile), shell=True)
		stopWiFi(calledFrom="resetWifi")
		time.sleep(0.2)
		startWiFi()
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def restartWifi():
	try:
		logger.log(30, "cBY:{:<20} restartWifi  w new config and wps files".format(G.program))
		stopWiFi(calledFrom="restartWifi")
		time.sleep(0.2)
		startWiFi()
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return



#################################
def copySupplicantFileFromBoot():
	try:
		logger.log(20, "cBY:{:<20} checking if interfaces or wpa_supplicant.conf files in /boot/".format(G.program))
		retCode = False
		if os.path.isfile("/boot/wpa_supplicant.conf"):
			subprocess.call("/usr/bin/sudo cp  /boot/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf", shell=True)
			subprocess.call("/usr/bin/sudo rm  /boot/wpa_supplicant.conf", shell=True)
			retCode = True
			logger.log(20, "cBY:{:<20} copying new wpa_supplicant.conf file from boot".format(G.program))
		if os.path.isfile("/boot/interfaces"):
			subprocess.call("/usr/bin/sudo cp  /boot/interfaces  /etc/network/interfaces", shell=True)
			subprocess.call("/usr/bin/sudo rm  /boot/interfaces", shell=True)
			retCode = True
			logger.log(20, "cBY:{:<20} copying new interfaces file from boot".format(G.program))
		return retCode
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return False

#################################
def checkifWifiJsonFileInBootDir():
	if os.path.isfile("/boot/wifiInfo.json"):
		wifiInfo, raw = readJson("/boot/wifiInfo.json")
		logger.log(20, 'reading wifi info file:{}'.format(raw) )
		subprocess.call("/usr/bin/sudo rm /boot/wifiInfo.json", shell=True)
		if wifiInfo !={} and "SSID" in wifiInfo and  "passCode" in wifiInfo:
			makeNewSupplicantFile(wifiInfo)
			return True
		else:
			logger.log(40, 'bad newWifi.json:{}; \n should be json format: {{"SSID":"xxx", "passCode":"xxx"}}'.format(raw) )
	return False

#################################
def makeNewSupplicantFile(data):
	try:
		logger.log(50, "cBY:{:<20} enter with {}".format(G.program, data))

		if "SSID"      not in data: 			return False
		if "passCode"  not in data: 			return False
		if len(data["SSID"]) < 1:				return False
		if len(data["passCode"]) < 1:			return False
		if data["SSID"] 	== "do not change": return False
		if data["SSID"] 	== "do+not+change": return False
		if data["passCode"] == "do not change": return False
		if data["passCode"] == "do+not+change": return False

		tryFileAdhoc = "{}wpa_supplicant.conf-fromBeforeAdhoc".format(G.homeDir)
		tryFileActive = "/etc/wpa_supplicant/wpa_supplicant.conf"

		minFile = "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\ncountry=US\mnetwork={}\n"

		useFile = "{}wpa_supplicant.conf-temp".format(G.homeDir)

		if os.path.isfile(tryFileActive): # does supplicant file exist, if yes use it 
			subprocess.call("/usr/bin/sudo cp  {} {}".format(tryFileActive, useFile), shell=True)
		elif os.path.isfile(tryFileAdhoc):# does supplicant adhoc file exist, if yes use it 
			subprocess.call("/usr/bin/sudo cp  {} {}".format(tryFileAdhoc, useFile), shell=True)
		else:
			writeFile(useFile, minFile, useHomeDir=False) # nothing exists: start from scratch 

		# from now on only work with wpa_supplicant.conf-temp	

		logger.log(50, "cBY:{:<20} making new supplicant file with: {}".format(G.program, data))

		f = open(useFile,"r")
		old = f.read()
		f.close()


		if old.find("network={") == -1:
			old = minFile

		if old.find('"'+data["SSID"]+'"') >-1 and  old.find('"'+data["passCode"]+'"') >-1:
			logger.log(50, "cBY:{:<20} ssid and passcode already in wpa_supplicant.conf file.. no update".format(G.program))
			return False

		oldSidFound = old.find('"'+data["SSID"]+'"')

		maxprio = 0
		for j in range(20):
			prio = old.find("priority={}".format(20-j))
			if prio > -1:
				maxprio = 20-j
				break
		maxprio +=1

		newF = ""

		if oldSidFound > -1: # replace only password
			part1 = old[:oldSidFound] + '"' +data["SSID"]+'"\n'  # up to and including ssid
			n1  = old[oldSidFound:].find("\n") # next line end
			part2 = old[oldSidFound+n1:].lstrip("\n") #the rest
			n1  = part2.find("\n")  # replace next line w new passcode
			part2 = '  psk="'+data["passCode"]+ '"'+part2[n1:]
			newF = part1+part2
			writeFile(useFile, newF, useHomeDir=False)
			logger.log(20, "cBY:{:<20} added to network = SSID..,  changed passcode in file {}".format(G.homeDir, tryFileActive))

		else: # add network={ssid="xxx" psk="yyy"}
			newF = old +'\nnetwork={\n  ssid="'+data["SSID"]+'"\n  psk="'+data["passCode"]+'"\n }\n' # priority='+str(maxprio)+'\n
			writeFile(useFile, newF, useHomeDir=False)
			logger.log(50, "cBY:{:<20} added network = ... SSID and passcode in file: {}".format(G.homeDir,tryFileActive))

		logger.log(50, "cBY:{:<20} copying files back in place file:{} and :{}, contents:{}".format(G.homeDir,useFile, tryFileAdhoc, newF))

		subprocess.call("/usr/bin/sudo cp {} {}".format(useFile, tryFileActive), shell=True)
		subprocess.call("/usr/bin/sudo cp {} {}".format(useFile, tryFileAdhoc), shell=True)

		## need to reboot to get the new configs loaded
		if whichWifi().find("adhoc") > -1:
			setStopAdhocWiFi()
			stopAdhocWifi()

		doReboot(tt=2)
		return True
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return False

#

################################
def getIPNumberMaster(quiet=True, noRestart=False):
	ipAddressRead		= ""
	retcode				= 0
	connected			= False
	indigoServer		= False
	changed				= ""

	try:
		try:
			f = open("{}ipAddress".format(G.homeDir),"r")
			ipAddressRead = f.read().strip(" ").strip("\n").strip(" ")
			if not quiet: logger.log(20, "cBY:{:<20} found IP number:{}".format(G.program, ipAddressRead))
			f.close()
		except:
			ipAddressRead = ""
			if not quiet: logger.log(20, "cBY:{:<20}  no ipAddress file".format(G.program))


		eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled = getIPCONFIG()

		wlan0IP,eth0IP,changed = setWlanEthONoff(wlan0IP, eth0IP, ipAddressRead, noRestart=noRestart)


		if testROUTER() == 0: 			connected	 = True
		if testPing(G.ipOfServer) == 0:	indigoServer = True

		if changed != "" or not isValidIP(ipAddressRead):
			time.sleep(2)
			eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled= getIPCONFIG()

			if testROUTER() == 0: 		connected	 = True
			if testIndigoServer()== 0:	indigoServer = True
			

		if not quiet: logger.log(20,"cBY:{:<20} IP info:  xxx  wlan0>{}<; eth0>{}<;  changed:{}<<; connected:{}<<; indigoServer:{}-{}<<, G.ipAddress:{}<;  ipAddressRead:{}<; G.wifiEth:{}<; G.wifiActive:{}".format( G.program, wlan0IP,eth0IP,changed, connected, indigoServer, G.ipOfServer, G.ipAddress, ipAddressRead, G.wifiEth, G.wifiActive) )

		if not connected:
			if not G.wifiEnabled and not G.switchedToWifi:
				G.wifiEthOld		= copy.copy(G.wifiEth)
				G.wifiEth["wlan0"]["on"]	= "on"
				G.wifiEth["wlan0"]["useIP"]	= "use"
				G.wifiEth["eth0"]["useIP"]  = "useIf"
				eth0IP = ""
				if not G.wifiEnabled:
					startWiFi()
					time.sleep(20)
				eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled = getIPCONFIG()
				if testROUTER() == 0: 		connected	 = True
				if testIndigoServer() == 0:	indigoServer = True

		## added "connected or" in case router is not reachable, only indigo server
		if connected or indigoServer:
			if G.ipNumberRpiStatic:
				G.ipAddress = G.ipNumberPi

			else:
				if  eth0IP !="" and G.eth0Active and (
					 G.wifiEth["eth0"]["useIP"] in ["use","dontChange"] or
					(G.wifiEth["eth0"]["useIP"] in ["useIf"] and  wlan0IP == "")
					) :
					G.ipAddress = eth0IP

				elif  wlan0IP !="" and G.wifiActive and (
					 G.wifiEth["wlan0"]["useIP"] in ["use","dontChange"] or
					 (G.wifiEth["wlan0"]["useIP"] in ["useIf"] and  eth0IP == "")
					):
					G.ipAddress = wlan0IP
					if not quiet: logger.log(20,"cBY:{:<20} doing wlanIP :{}< G.ipAddress :{}<".format(G.program, wlan0IP, G.ipAddress) )

				if not quiet: logger.log(20,"cBY:{:<20} IP info:  yyy  wlan0>{}<; eth0>{}<;  G.ipAddress:{}<;  G.wifiEth:{}<; G.wifiActive:{}; ipAddressRead:{}<".format( G.program, wlan0IP,eth0IP, G.ipAddress, G.wifiEth, G.wifiActive, ipAddressRead) )

			if G.ipAddress != ipAddressRead:
				if not quiet: logger.log(20,"cBY:{:<20} IP info:  writing  wlan0>{}<; eth0>{}<;  G.ipAddress:{}<;  G.wifiEth:{}<; G.wifiActive:{}; ipAddressRead:{}<".format( G.program, wlan0IP,eth0IP, G.ipAddress, G.wifiEth, G.wifiActive, ipAddressRead) )
				writeIPtoFile(G.ipAddress, reason=changed)
				logger.log(20,"cBY:{:<20} IP info: IPs#: changed:>{}<; connected:{}; IndigoServer>{}<; Router>{}<; wlan0>{}<; eth0>{}<; G.wlanActive:{}; G.eth0Active:{};  AddressFile>{}<; PKTS(eth0>{},{}<; wlan0>{},{}<, dTime:{:.1f})".format( 
									G.program, 			  changed, 	   connected,    G.ipOfServer, 	  G.ipOfRouter, wlan0IP,  eth0IP,   G.wifiActive,    G.eth0Active,     ipAddressRead,   G.eth0Packets, G.eth0PacketsOld, G.wlan0Packets,G .wlan0PacketsOld, min(99.9,G.packetsTime-G.packetsTimeOld)))
				logger.log(20,"cBY:{:<20} ... Requested Config:{}".format(G.program, G.wifiEth))
				return indigoServer, True, connected


			else:
				if not quiet: logger.log(20,"cBY:{:<20} IP info: IPs#: changed:>{}<; connected:{}; IndigoServer>{}<; Router>{}<; wlan0>{}<; eth0>{}<; G.wlanActive:{}; G.eth0Active:{}; AddressFile>{}<; PKTS(eth0>{},{}<; wlan0>{},{}<, dTime:{:.1f})".format( 
											G.program, 				   changed, 	 connected, 	G.ipOfServer,  G.ipOfRouter, wlan0IP,   eth0IP,   G.wifiActive,    G.eth0Active,    ipAddressRead,  G.eth0Packets, G.eth0PacketsOld, G.wlan0Packets,G .wlan0PacketsOld, min(99.9,G.packetsTime-G.packetsTimeOld)))
				if not quiet: logger.log(20,"cBY:{:<20} ... Requested Config:{}".format(G.program,G.wifiEth))
				return indigoServer, False, connected

		else:
			if not quiet: logger.log(20,"cBY:{:<20} not connected to either router:{} or indigo server:{}".format(G.program, connected, indigoServer))

	except Exception as e:
		logger.log(30,"", exc_info=True)

	if changed !="":
		logger.log(20, "cBY:{:<20} bad IP number ...  old from file ipAddressRead>>{}<< not in sync with ip output: wlan0IP>>{}<<;	eth0IP>>{}<<".format( G.program, ipAddressRead, wlan0IP,eth0IP)  )
	return indigoServer, changed !="", connected

#################################
def setWlanEthONoff(wlan0IP, eth0IP,oldIP, noRestart=False):

# G.wifiEth["eth0"]  ={"on":{"on"/"onIf"/"off"/"dontChange"}, "useIP":"use"/"useIf"/"off"}}
# G.wifiEth["wlan0"] ={"on":{"on"/"onIf"/"off"/"dontChange"}, "useIP":"use"/"useIf"/"off"}}
#  /usr/bin/sudo /etc/init.d/networking restart
	changed	= ""

	
	try:
		if G.ipNumberRpiStatic:
			return wlan0IP, eth0IP, ""
		if wlan0IP == "":
			if G.wifiEth["eth0"]["on"] in ["on","onIf","dontChange"] and eth0IP == "" and not G.eth0Enabled:
				if not noRestart: startEth()
				time.sleep(10)
				changed	= "ETHon"
				logger.log(30, "cBY:{:<20} setWlanEthONoff  ip changed: eth0[on]: {}, eth0IP:/, eth0Enabled:F, wlan0IP=="", eth0Packets:{}, wlan0Packets:{} .. starting eth0".format(G.program, G.wifiEth["eth0"]["on"],  G.eth0Packets, G.wlan0Packets) )

		if G.switchedToWifi != 0 and time.time() - G.switchedToWifi < 100:
			G.switchedToWifi =time.time() + 100.
			# reset eth packet counters
			if G.eth0Enabled and not noRestart:
				stopEth()
				startEth()
			if wlan0IP == "":
				if not G.wifiEnabled and not noRestart:
					startWiFi()
					time.sleep(10)
				changed	= "WIFIon"
				logger.log(30, "cBY:{:<20} etWlanEthONoff  ip changed: switchedToWifi:T , wlan0IP:/, wifiEnabled:F starting WiFi".format(G.program, wlan0IP, G.eth0Packets, G.wlan0Packets) )

		# check if ethernet is back after 5 minutes
		if G.switchedToWifi != 0 and time.time() - G.switchedToWifi > 300:
			if eth0IP != "" and G.eth0Enabled and G.eth0Active:
				if G.eth0Packets != G.eth0PaketsOld and (G.packetsTime- G.packetsTimeOld > 2.):
					if testROUTER() != 0:
						G.wifiEth	= copy.copy(G.wifiEthOld)
						G.switchedToWifi = 0
						if G.wifiEth["wlan0"]["on"]  in ["onIf","off"]:
							stopWiFi(calledFrom="setWlanEthONoff - 1")
							time.sleep(2)
						changed	= "WIFIoff"
						logger.log(30, "cBY:{:<20} setWlanEthONoff  ip changed: resetting switchedToWifi, eth0 seems to be back(packet count);  wlan0[on]:{}, eth0IP:{}, G.eth0Enabled:T, G.eth0Active:T, stopWiFi".format(G.program,G.wifiEth["wlan0"]["on"],eth0IP) )

		if changed != "":
			time.sleep(2)
			eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled = getIPCONFIG()
			if oldIP in [eth0IP, wlan0IP]:
				changed = ""
				return wlan0IP, eth0IP, changed
			logger.log(30, "cBY:{:<20} setWlanEthONoff  return: eth0IP:{}, wlan0IP:{}, eth0Enabled:{}, wifiEnabled:{}, eth0Active:{}, wifiActive:{}, eth0Packets:{}, eth0PacketsOld:{}, wlan0Packets:{}".format( G.program, eth0IP, wlan0IP, G.eth0Enabled, G.wifiEnabled, G.eth0Active, G.wifiActive, G.eth0Packets, G.wlan0Packets, G.wlan0Packets ) )
			return wlan0IP, eth0IP, changed


		if G.wifiEth["wlan0"]["on"] not in ["on","dontChange"] and wlan0IP != "" and G.wifiEnabled:
			if eth0IP !="" and G.eth0Active:
				logger.log(30, "cBY:{:<20} switching WiFi off".format(G.program))
				if not noRestart: stopWiFi(calledFrom="setWlanEthONoff - 2")
				changed = "ETHon"
				logger.log(30, "cBY:{:<20} setWlanEthONoff  ip changed: G.wifiEth[wlan0][on] not in [on,dontChange] and wlan0IP:{}  and G.wifiEnabled, eth0IP:{}, eth0Packets:{}, wlan0Packets:{}".format(G.program,wlan0IP, eth0IP, G.eth0Packets, G.wlan0Packets ) )


		if G.wifiEth["eth0"]["on"] == "off" and eth0IP != "" and G.eth0Active:
				logger.log(30, "cBY:{:<20} switching eth0 off".format(G.program))
				logger.log(30, "cBY:{:<20} setWlanEthONoff  ip changed: G.wifiEth[eth0][on] ==off and  eth0IP:{}, eth0Packets:{}, wlan0Packets:{}".format(G.program,eth0IP, G.eth0Packets, G.wlan0Packets) )
				if not noRestart: pass
				changed = "ETHoff"

		if  G.wifiEth["eth0"]["useIP"] == "off" and eth0IP !="":
			logger.log(30, "cBY:{:<20} setWlanEthONoff  ip changed: G.wifiEth[eth0][useIP] ==off and  eth0IP:{}, eth0Packets:{}, wlan0Packets:{}".format(G.program,eth0IP, G.eth0Packets, G.wlan0Packets) )
			if not noRestart: stopEth()
			changed = "ETHoff"

		if  G.wifiEth["wlan0"]["useIP"] == "off" and wlan0IP !="":
			changed = "WIFIoff"
			logger.log(30, "cBY:{:<20} setWlanEthONoff  ip changed: G.wifiEth[wlan0][useIP] ==off and  wlan0IP:{}, eth0Packets:{}, wlan0Packets:{}".format(G.program,wlan0IP, G.eth0Packets, G.wlan0Packets) )
			if not noRestart: stopWiFi()

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))


	return wlan0IP,eth0IP, changed

#################################
def writeIPtoFile(ip,reason=""):
	try:
		G.ipAddress = ip
		writeFile("ipAddress", G.ipAddress.strip(" ").strip("\n").strip(" "))
		logger.log(30,"cBY:{:<20} writing ip number to file >>{}<<  reason:{}".format( G.program, G.ipAddress, reason))
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return


#################################
def findActiveUSB():
	activUsbList=[]
	try:
		cmd = "/bin/ls -l /dev | grep USB"
		# returns: crw-rw----  1 root dialout 188,   0 Nov 22 09:51 ttyUSB0
		ret = (subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))

		#logger.log(10,"cBY:{:<20} found ls /dev usb:  {}".format( G.program,ret) )
		for line in ret.split("\n"):
				if line.find("dialout") == -1: continue
				line = line.split()[-1]
				if line.find("tty") == -1: continue
				line = line.split("tty")[-1]
				#logger.log(10,"cBY:{:<20} return  {}".format( G.program,line) )
				activUsbList.append(line)
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return activUsbList


#################################
def checkIfusbSerialActive(usb):
	try:
		cmd = "/bin/ls -l /dev | grep {}".format(usb)
		ret = (subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))
		if  ret.find(usb) > -1 and ret.find("dialout")> -1: 
			return True
		else:
			return False
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return False



#################################
def getBootFileName():
	try:
		bootFile = "/boot/config.txt"
		if not os.path.isfile(bootFile):
			bootFile = "/boot/firmware/config.txt"
		else:
			if doReadSimpleFile(bootFile).find("/boot/firmware/config.txt") > -1:
				bootFile = "/boot/firmware/config.txt"
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return bootFile



#################################
def getSerialDEV():
	try:
		version = subprocess.Popen("cat /proc/device-tree/model" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
		# return eg
		# Raspberry Pi 2 Model B Rev 1.1
		#return "/dev/ttyAMA0"
		serials = subprocess.Popen("ls -l /dev/ | grep serial" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
		# should return something like:
		#lrwxrwxrwx 1 root root			  5 Apr 20 11:17 serial0 -> ttyS0
		#lrwxrwxrwx 1 root root			  7 Apr 20 11:17 serial1 -> ttyAMA0
		#or just:
		#lrwxrwxrwx 1 root root           7 Jul  7 13:30 serial1 -> ttyAMA0



		if (version).find("Raspberry") == -1:
			logger.log(30, "cBY:{:<20} cat /proc/device-tree/model something is wrong... {}".format(G.program,version)  )
			time.sleep(10)
			return ""

		if (version).find("Pi 3") == -1 and (version[0]).find("Pi 4") == -1 and (version[0]).find("Pi Zero") == -1:	# pi2?
			sP = "/dev/ttyAMA0"

			### disable and remove tty usage for console
			subprocess.Popen("systemctl stop serial-getty@ttyAMA0.service" ,	shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			subprocess.Popen("systemctl disable serial-getty@ttyAMA0.service" , shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

			if serials.find("serial0 -> ttyAMA0") == -1 :
				logger.log(30, "cBY:{:<20} pi2 .. wrong serial port setup .. enable serial port in raspi-config ..  can not run missing in 'ls -l /dev/' : serial0 -> ttyAMA0".format(G.program) )
				time.sleep(10)
				return ""
			return sP

		elif version.find("Pi Zero") > -1:	# not RPI3
			sP = "/dev/ttyS0"

			### disable and remove tty usage for console
			subprocess.Popen("systemctl stop serial-getty@ttyS0.service" ,	  shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			subprocess.Popen("systemctl disable serial-getty@ttyS0.service" , shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

			if serials.find("serial0 -> ttyS0")== -1:
				logger.log(30, "cBY:{:<20} pi3 4 .. wrong serial port setup  .. enable serial port in raspi-config .. can not run missing in 'ls -l /dev/' : serial0 -> ttyS0".format(G.program)  )
				time.sleep(10)
				return ""
			return sP

		else:# RPI3, 4
			sP = "/dev/ttyS0"

			### disable and remove tty usage for console
			subprocess.Popen("systemctl stop serial-getty@ttyS0.service" ,	  shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			subprocess.Popen("systemctl disable serial-getty@ttyS0.service" , shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

			if serials.find("serial0 -> ttyS0") == -1:
				logger.log(30, "cBY:{:<20} pi3 .. wrong serial port setup .. enable serial port in raspi-config ..  can not run missing in 'ls -l /dev/' : serial0 -> ttyS0".format(G.program) )
				time.sleep(10)
				return ""
		logger.log(20, "cBY:{:<20} serial port name:{}".format(G.program, sP) )

		return sP
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return ""



#### selct the proper hci bus: if just one take that one, if 2, use bus="uart", if no uart use hci0
def selectHCI(HCIs, useDev, defaultBus, doNotUseHCI="", tryBLEmac="", doNotUseHCI2=""): 
	# default is UART or USB, used if no other choice selected
	# useDev  is UART or USB, used if available
	# doNotUseHCI is ""/hci0/hci1/..2/..3/..4
	#logger.log(20, "cBY:{:<20} HCIs:{}, useDev:{}, defaultBus:{}, doNotUseHCI:{}".format(G.program,HCIs, useDev, defaultBus, doNotUseHCI ))
	try:
		if len(HCIs) == 1:
			useHCI = list(HCIs)[0]
			return useHCI, HCIs[useHCI]["BLEmac"], 0, HCIs[useHCI]["bus"]

		elif len(HCIs) > 1:
			hciChannels = []
			for xx in HCIs:
				hciChannels.append(xx)
			if doNotUseHCI in hciChannels:
				hciChannels.remove(doNotUseHCI)
			if doNotUseHCI2 in hciChannels:
				hciChannels.remove(doNotUseHCI2)

			if tryBLEmac != "":
				for hh in hciChannels:
					if tryBLEmac == HCIs[hh]["BLEmac"]:
						#logger.log(20, "cBY:{:<20} ret USB".format(G.program ))
						return hh,  HCIs[hh]["BLEmac"], HCIs[hh]["numb"], HCIs[hh]["bus"]

			#logger.log(20, "cBY:{:<20} 1- , hciChannels:{}".format(G.program, hciChannels ))
			if useDev == "USB":
				for hh in hciChannels:
					if HCIs[hh]["bus"] == "USB":
						#logger.log(20, "cBY:{:<20} ret USB".format(G.program ))
						return hh,  HCIs[hh]["BLEmac"], HCIs[hh]["numb"], HCIs[hh]["bus"]

			elif useDev == "UART":
				for hh in hciChannels:
					if HCIs[hh]["bus"] == "UART":
						#logger.log(20, "cBY:{:<20} ret UART".format(G.program ))
						return hh,  HCIs[hh]["BLEmac"], HCIs[hh]["numb"], HCIs[hh]["bus"]

			elif defaultBus != "":
				for hh in hciChannels:
					if HCIs[hh]["bus"] == defaultBus:
						#logger.log(20, "cBY:{:<20} ret default".format(G.program ))
						return hh,  HCIs[hh]["BLEmac"], HCIs[hh]["numb"], HCIs[hh]["bus"]
				for hh in hciChannels:
					if HCIs[hh]["bus"] != doNotUseHCI:
						#logger.log(20, "cBY:{:<20} ret default".format(G.program ))
						return hh,  HCIs[hh]["BLEmac"], HCIs[hh]["numb"], HCIs[hh]["bus"]

			elif defaultBus == "":
				for hh in hciChannels:
						return hh,  HCIs[hh]["BLEmac"], HCIs[hh]["numb"], HCIs[hh]["bus"]
				
			else:
				hh = hciChannel[0]
				return hh,  HCIs[hh]["BLEmac"], HCIs[hh]["numb"], HCIs[hh]["bus"]

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		logger.log(30, "cBY:{:<20} HCIs={}".format(G.program, HCIs))

	sendURL( data={"ERROR":"can_not_setup_BLE,_HCIs:{},useDev:{}, defaultBus:{}, doNotUseHCI:{}, tryBLEmac:{}".format(HCIs, useDev, defaultBus, doNotUseHCI, tryBLEmac )} )

	logger.log(20, "cBY:{:<20} BLEconnect: NO BLE STACK UP ".format(G.program))
	logger.log(20, "cBY:{:<20} HCIs:{}, useDev:{}, defaultBus:{}, doNotUseHCI:{}, tryBLEmac:{}".format(G.program,HCIs, useDev, defaultBus, doNotUseHCI, tryBLEmac ))
	return 0, -1, -1, -1

#################################
def whichHCI():
	try:

		#hci={"hci0":{"bus":"UART", "numb":0 ,"BLEmac":"xx:xx:xx:xx:xx:xx","upDown":"UP/Down"},"ret":ret[0,1]}
		hci ={"hci":{}}

		aa	= subprocess.Popen("hciconfig ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		ret	= [aa[0].decode('utf-8'),aa[1].decode('utf-8')]
		# try again, sometimes does not return anything
		if len(ret[0]) < 5:
			time.sleep(0.5)
			aa	= subprocess.Popen("hciconfig ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			ret	= [aa[0].decode('utf-8'),aa[1].decode('utf-8')]
			logger.log(30, "cBY:{:<20} whichHCI, hciconfig...  2. try: {}".format(G.program,ret))

		lines = (ret[0]).split("\n")
		for ll in range(len(lines)):
			if lines[ll].find("hci") == 0: # finds :  #hci1:	Type: Primary  Bus: UART
				bus = lines[ll].split("Bus: ")[1]
				hciNo = lines[ll].split(":")[0]
				hci["hci"][hciNo] = {"bus":bus, "numb":int(hciNo[-1]),"upDown":"DOWN","BLEmac":"0"}
				if lines[ll+1].find("BD Address:") >- 1: # finds: BD Address: B8:27:EB:D4:E3:35  ACL MTU: 1021:8	SCO MTU: 64:1
					mm=lines[ll+1].strip().split("BD Address: ")[1]
					mm=mm.split(" ")
					if len(mm)>2:
						hci["hci"][hciNo]["BLEmac"] = mm[0]
					if "UP" in lines[ll+2].strip():	hci["hci"][hciNo]["upDown"] = "UP"
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
		if hci["hci"] == {}: logger.log(30, " empty return from which HCI :{}".format(lines))
		hci["ret"] = ret
		return hci
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return {}
#################################
def checkIfHCiUP(useHCI,verbose=False):
	"""
checking for hci is up , find "up runnning" for proper hci channel hci0/hci1..
hci0:	Type: Primary  Bus: USB
	BD Address: 5C:F3:70:6D:D9:4A  ACL MTU: 1021:8  SCO MTU: 64:1
	UP RUNNING  <----- looking for this
	RX bytes:65822 acl:0 sco:0 events:1922 errors:0
	TX bytes:3460 acl:0 sco:0 commands:92 errors:0

hci1:	Type: Primary  Bus: UART
	BD Address: B8:27:EB:12:5A:C1  ACL MTU: 1021:8  SCO MTU: 64:1
	UP RUNNING 
	RX bytes:795280348 acl:21 sco:0 events:22341732 errors:0

	"""
	try:
		aa	= subprocess.Popen("hciconfig ",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		ret	= [aa[0].decode('utf-8'),aa[1].decode('utf-8')]
		if verbose: logger.log(20, "cBY:{:<20} {}".format(G.program, ret[0]))
		hciFound = False
		for line in ret[0].split("\n"):
			if line.find(str(useHCI)) == 0: 
				hciFound = True
				continue
			if hciFound:
				#if verbose: logger.log(20, "cBY:{:<20} hciFound, line:{}".format(G.program, line))
				if line.find("Bus: ") > 15:			return False # found next section , no up running
				if len(line) < 5: 					return False # next section ...
				if line.find("UP RUNNING") > -1:	return True  # ok, return True
		return False			

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return False
#################################
def checkIfHciBlocked(verbose=False):
	"""
checking for hci is up , find "up runnning" for proper hci channel hci0/hci1..
sudo rfkill --output-all
ID TYPE      DEVICE TYPE-DESC         SOFT      HARD
 0 bluetooth hci0   Bluetooth    unblocked unblocked
 1 bluetooth hci1   Bluetooth    unblocked unblocked
 3 wlan      phy0   Wireless LAN unblocked unblocked
 4 bluetooth hci3   Bluetooth    unblocked unblocked
34 bluetooth hci2   Bluetooth    unblocked unblocked
returns {"hciX":{"softBlock": True/false, "hardBlock":true/false}}

	"""
	hciBlocked = {}
	blocked = False
	try:
		cmd = "/usr/bin/sudo /usr/sbin/rfkill --output-all"
		aa	= subprocess.Popen("/usr/bin/sudo /usr/sbin/rfkill --output-all",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		ret	= [aa[0].decode('utf-8'),aa[1].decode('utf-8')]
		if verbose: logger.log(20, "cBY:{:<20} {}\n{}".format(G.program, cmd, ret[0]))
		for line in ret[0].split("\n"):
			if line.find("bluetooth") > 0: 
				items = line.split("bluetooth")[1].split()
				if len(items) == 4:
					hci = items[0]
					if hci.find("hci") ==0:
						softBlock = items[2] == "blocked"
						hardBlock = items[3] == "blocked"
						hciBlocked[hci] = {"softBlock": softBlock, "hardBlock":hardBlock}
						if softBlock or hardBlock: blocked = True
		return blocked, hciBlocked			

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return blocked, hciBlocked

#################################
def hciUnblock():
	"""
	tries to unblock bluetooth 
	"""
	subprocess.Popen("/usr/bin/sudo /usr/sbin/rfkill unblock bluetooth",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	return

#################################
def sendURL(data={}, sendAlive="", text="", wait=True, verbose=False, squeeze=True, escape=False, forceCompress=False):

	try:
			netwM = getNetwork()
			if (G.networkType  not in G.useNetwork or G.wifiType !="normal") or (netwM=="off" or netwM =="clock") :
				G.lastAliveSend	 = time.time()
				G.lastAliveSend2 = time.time()
				return

			if G.sendThread == {}:
				G.sendThread = { "run":True, "queue": Queue.Queue(), "thread": threading.Thread(name=u'execSend', target=execSend, args=())}
				G.sendThread["thread"].start()

			G.sendThread["queue"].put({"data":data, "sendAlive":sendAlive, "text":text, "wait":wait, "verbose":verbose, "squeeze":squeeze, "escape":escape, "forceCompress":forceCompress})
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return


#################################
def execSend():
	global varNanmes


	try:
		while G.sendThread["run"]:
			time.sleep(1)
			while not G.sendThread["queue"].empty():
				try:
					nextData 		= G.sendThread["queue"].get()
					
					verbose = nextData.get("verbose",False)

					if verbose:	logger.log(20, "cBY:{:<20} send queue data {}".format(G.program, "{}".format(nextData)[0:100]) )
					data 			= nextData["data"]
					sendAlive 		= nextData["sendAlive"]
					text 			= nextData["text"]
					wait 			= nextData["wait"]
					squeeze 		= nextData["squeeze"]
					escape 			= nextData["escape"]
					forceCompress 	= nextData["forceCompress"]

					subprocess.call("touch {}temp/sending".format(G.homeDir), shell=True)

					data["program"]	  = G.program
					data["pi"]		  = str(G.myPiNumber)
					data["ipAddress"] = G.ipAddress.strip(" ").strip("\n").strip(" ")
					if len(text) > 0:
						data["text"] = text

					if (time.time() - G.tStart > 40):#dont send time if we have just started .. wait for ntp etc to get time
						tz = time.tzname[1]
						if len(tz) < 2:	 tz = time.tzname[0]
						data["ts"]			= {"time":round(time.time(),2),"tz":tz}


					if	False and sendAlive != "":
						logger.log(20, "cBY:{:<20}  data:{} ".format(G.program, data)) 


					if	sendAlive == "reboot":
						name = "pi_IN_Alive"
						data["msgType"] = sendAlive
						data["reboot"] = True
						G.lastAliveSend2 = time.time()

					elif  sendAlive == "alive":
						name = "pi_IN_Alive"
						data["msgType"] = sendAlive
						G.lastAliveSend2 = time.time()

					elif  sendAlive == "raspi-config":
						name = "pi_IN_Alive"
						data["msgType"] = sendAlive
						G.lastAliveSend2 = time.time()

					elif  sendAlive == "config.txt":
						name = "pi_IN_Alive"
						data["msgType"] = sendAlive
						G.lastAliveSend2 = time.time()

					else:
						name = "pi_IN_{}".format(G.myPiNumber)
						data["msgType"] = "regular"

					if True:  ## do socket comm
								MSGwasSend = False
								ii = 5
								while ii > 0: 
									ii -= 1
									dataC = json.dumps(data, separators=(',',':'))
									if dataC.find("NaN") > 0: dataC = dataC.replace("NaN","-9999")
									lenStart = len(dataC)
									if squeeze: dataC = dataC.replace(" ","")
									if  len(dataC) > G.compressRPItoPlugin or forceCompress: 
										if sys.version_info[0] == 3: data0 = zlib.compress(bytes(dataC,'utf-8'))
										else:						 data0 = zlib.compress(dataC)
										compressedTag = "+comp"
									else: 
										data0 = dataC
										compressedTag = "+NOTC"
									lld = len(data0)
									if verbose: logger.log(20, "cBY:{:<20}  socket send data lengths  in:{} --> :sq:{} --> cmp:{} ".format(G.program, lenStart, len(dataC), lld))
									sendData = "{}x-6-a{}x-6-a{}".format(lld, name,compressedTag)
									sendData = "{:<30}".format(sendData)
									if sys.version_info[0] == 3 and type(data0) == type(bytes("xx","utf-8")): 
										if verbose: logger.log(20, "cBY:{:<20}  sendData type{}, data0 type:{} ".format(G.program, type(sendData), type(data0) ))
										sendData = bytes(sendData,"utf8")
										sendData = sendData+data0
									else:
										sendData = sendData+data0
										if sys.version_info[0] == 3:
											sendData = bytes(sendData,"utf8")

									try:
										soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
										soc.settimeout(6.)
										soc.connect((G.ipOfServer, G.indigoInputPORT))
										len_sent = soc.send(sendData)
										time.sleep(0.2+ min(10,lld/20000))
										soc.settimeout(3.+ min(10,lld/10000))
										response = soc.recv(512).decode('utf-8')
										#logger.log(20, "cBY:{:<20}  socket send  response{} ".format(G.program, response))
										if (response).find("ok") == 0:
											MSGwasSend = True
											if verbose: logger.log(20, "cBY:{:<20}  socket send  finished ".format(G.program))
											break
										else:# try again
											if verbose: logger.log(20, "cBY:{:<20} Sending  again: send bytes: {} ret MSG from plugin: >>{}<<".format(G.program, len(data0), response))
											try:	soc.close()
											except: pass
											time.sleep(1.)

									except Exception as e:
										logger.log(20, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
										logger.log(20, "cBY:{:<20} trying to send  bytes: {} --{};  starting w:{}".format(G.program, len(dataC), len(data0), dataC[:100]))
										try:	soc.shutdown(socket.SHUT_RDWR)
										except: pass
										try:	soc.close()
										except: pass
										time.sleep(3.)

									# redo time stamp, at it is delayed ..
									tz = time.tzname[1]
									if len(tz) < 2:	 tz = time.tzname[0]
									data["ts"]			= {"time":round(time.time(),2),"tz":tz}

								if MSGwasSend:
									echoToMessageSend(dataC, "msg send, {} ---".format(compressedTag))
									if ii !=4:
										logger.log(20, "cBY:{:<20} +++ message was send sucessfully after initial error at {}. try +++".format(G.program, 5-ii))
								else:
									echoToMessageSend(dataC, "=== msg not send after 5 tries ===")
									logger.log(20, "cBY:{:<20} === message not send after 5 tries due to network error ===".format(G.program))
								try:	soc.shutdown(socket.SHUT_RDWR)
								except: pass
								try:	soc.close()
								except: pass

				except Exception as e:
					logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))

				subprocess.call("rm  {}temp/sending > /dev/null 2>&1 ".format(G.homeDir), shell=True)
				G.lastAliveSend = time.time()

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))

	return

######## un decode i2c ether from in or from hex
def echoToMessageSend(data, wasSend):
	try:
		if len(data) > 6000: data = data[0:5000]+"    ...    "+data[-990:]
		logger.log(10, "cBY:{:<20}  {} {}\n".format(G.program, wasSend, data) )
		writeFile("temp/messageSend", "{} {} {}: {}\n".format(datetime.datetime.now().strftime("%d-%H:%M:%S"), wasSend, G.program , data) )
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))


######## un decode i2c ether from in or from hex
def getI2cAddress(item,default =0):
	try:
		if "i2cAddress" in item:
			if item["i2cAddress"].find("x") >-1:
				i2cAddress = int(item["i2cAddress"],16)

			elif item["i2cAddress"].find("USB") >-1:
				return item["i2cAddress"]

			else:
				i2cAddress = int(item["i2cAddress"])

		else:
			i2cAddress =default
		return  i2cAddress
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		return default

######## setup and use	multiplexer if requested
def muxTCA9548A(sens,i2c=""):

	if i2c == "":
		i2c = getI2cAddress(sens, default=0)

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

################################
def muxTCA9548Areset():
	if G.enableMuxBus !="":
		G.enableMuxBus.write_byte(G.enableMuxI2C,0x0)

#################################
def removeOutPutFromFutureCommands(pin, devType):
	try:
		if os.path.isfile("{}execcommands.current".format(G.homeDir)):
			execcommands, input = readJson("{}execcommands.current".format(G.homeDir))
			if len(input) < 3: return
			rmEXEC={}
			for channel in execcommands:
				logger.log(10, "cBY:{:<20} removing  testing channel {}  {}".format(G.program,channel, execcommands[channel]) )
				if channel != str(pin): continue
				if "device" in execcommands[channel] and devType == execcommands[channel]["device"]:
					logger.log(10, "cBY:{:<20} removing testing channel device found".format(G.program) )
					if "startAtDateTime" in execcommands[channel] and time.time() - float(execcommands[channel]["startAtDateTime"]) > 2:
						if execcommands[channel]["command"]	 not in ["analogWrite","up","down"]:
							logger.log(10, "cBY:{:<20} removing testing channel time expired".format(G.program) )
							rmEXEC[channel] = 1
							logger.log(10, "cBY:{:<20} removing removing channel".format(G.program,channel))
			for channel in rmEXEC:
				del execcommands[channel]
			writeJson("{}execcommands.current".format(G.homeDir),execcommands)
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		if str(e).find("Read-only file system:") > -1:
			doReboot(tt=0)


#################################
def echoLastAlive(sensor):
	try:
		tt = time.time()
		if time.time() - G.lastAliveEcho > 30.:
			G.lastAliveEcho = tt
			subprocess.call("echo  {} > {}temp/alive.{}".format(tt,G.homeDir,sensor), shell=True)
	except:
			G.lastAliveEcho = tt
			subprocess.call("echo  {} > {}temp/alive.{}".format(tt,G.homeDir,sensor), shell=True)
	return


#################################
def echoText(fileName, text, start=False):
	try:
		#logger.log(20, " echoText to file:{}, text:{}".format(fileName, text))
		if start:
			f = open(fileName,"w")
		else:
			f = open(fileName,"a")
		f.write("{} {}\n".format(datetime.datetime.now().strftime("%d-%H:%M:%S"),text))
		f.close()
	except Exception as e:
		logger.log(20, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return


#################################
def calcStartTime(data,timeStamp):
	if timeStamp in data:
		try:
			startAtDateTime =  float(data[timeStamp])
			if startAtDateTime < 1000000.:
				return time.time() + startAtDateTime
			return startAtDateTime
		except:
			pass
	elif timeStamp.lower() in data:
		try:
			startAtDateTime =  float(data[timeStamp.lower()])
			if startAtDateTime < 1000000.:
				return time.time() + startAtDateTime
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
		thefile = "{}temp/{}.{}".format(G.homeDir, xxx, extension)
		if os.path.isfile(thefile):
			try:
				if len(thefile) > 0:
					f = open(thefile,"r")
					raw = f.read()
					f.close()
					#logger.log(20, "cBY:{:<20}  removing calibration file:{}".format(G.program, thefile))
					os.remove(thefile)
					try:
						data = json.loads(raw)
						return data
					except Exception as e:
						pass
				#logger.log(20, "cBY:{:<20}  removing calibration file:{}".format(G.program, thefile))
				os.remove(thefile)
			except:
				pass
			return True
		return False
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))

#################################
def checkForNewCommand(fname):
	try:
		if os.path.isfile("{}temp/{}".format(G.homeDir, fname)):
			try:
				jData, xx = readJson("{}temp/{}".format(G.homeDir, fname))
				os.remove("{}temp/{}".format(G.homeDir, fname))
				return jData
			except:
				pass
			return ""
		return ""
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return ""

#################################
def writeFile(outFile, text, writeOrAppend="w", useHomeDir=True):
	try:
		if useHomeDir:
			f = open("{}{}".format(G.homeDir, outFile), writeOrAppend)
		else:
			f = open(outFile, writeOrAppend)

		f.write(text)
		f.close()
		#logger.log(20, u"===== writing to {}{} text:{}".format(G.homeDir, outFile, text))
	except Exception as e:
		logger.log(30,"", exc_info=True)
		if "{}".format(e).find("Read-only file system:") >-1:
			doReboot(tt=0)
	return


#################################
def makeDATfile(sensor, data):
	if "sensors" in data:
		for sens in data["sensors"]:
			#print sensor, "makeDATfile", sens, data["sensors"][sens]
			writeJson("{}temp/{}.dat".format(G.homeDir,sens),   data["sensors"][sens], indent=2)
	else:
		if data != {}:
			writeJson("{}temp/{}.dat".format(G.homeDir,sensor), data, indent=2)


#################################
def writeJson(fName, data, sort_keys=False, indent=0):
	try:
		if indent != 0:
			out = json.dumps(data,sort_keys=sort_keys, indent=indent)
		else:
			out = json.dumps(data,sort_keys=sort_keys)
		#logger.log(10, u" writeJson-in:{}\nout: {}".format(data, out) )
	##print "writing json to "+fName, out
		f=open(fName,"w")
		f.write(out)
		f.close()
	except Exception as e:
		logger.log(30,"cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		if str(e).find("Read-only file system:") >-1:
			doReboot(tt=0)
	return


#################################
def readPopen(cmd):
	try:
		ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		return ret.decode('utf_8'), err.decode('utf_8')
	except Exception as e:
		logger.log(20,"", exc_info=True)

#################################
def checkIfmustUsePy3():
	if getOsVersion() >= 11:
		return True
	return False

#################################
def getOsVersion():
	osInfo	 = readPopen("cat /etc/os-release")[0].strip("\n").split("\n")
	for line in osInfo:
		if line .find("VERSION_ID=") == 0:
			return int( line.strip('"').split('="')[1] )
	return 0 

#################################
def readJson(fName):
	data = {}
	raw  = ""
	if not os.path.isfile(fName):
		logger.log(10,"cBY:{:<20}  fname does not exist:{}, return empty".format(G.program, fName))
		return {}, ""

	for ii in range(2):
		try:
			f = open(fName,"r")
			raw = f.read()
			f.close()
			data = json.loads(raw)
			if ii == 1: logger.log(20, "cBY:{:<20} read error fixed".format(G.program) )
			return data, raw
		except Exception as e:
			logger.log(20,"cBY:{:<20} Line {} has error={}, fname:{}, data:>>{}..{}<<".format(G.program, sys.exc_info()[-1].tb_lineno, e, fName, raw[0:50],raw[-50:] ))
			if ii > 0:
				return {}, ""
			time.sleep(1)

	return data, raw


#################################
def compareDict(oldDict, newDict, levels=3, mustHaveKey="", mustHaveSensor=""):

	sens = ""
	try:
		for sens in newDict:
			if mustHaveSensor != "" and mustHaveSensor != sens :	continue  
			if type(newDict[sens]) != type({}): 					continue
			if sens not in  oldDict: 														return True
			if type(newDict[sens]) != type(oldDict[sens]): 									return True

			if levels >= 2:
				for sensId in newDict[sens]:
					if type(newDict[sens][sensId]) != type({}): 	continue
					if mustHaveKey != "" and mustHaveKey not in newDict[sens][sensId]: break 
					if sensId not in  oldDict[sens]: 										return True

					if levels >=3:
						for xx in newDict[sens][sensId]:
							if xx not in  oldDict[sens][sensId]: 							return True
							if oldDict[sens][sensId][xx] !=  newDict[sens][sensId][xx]: 	return True


		for sens in oldDict:
			if mustHaveSensor != "" and mustHaveSensor != sens :	continue  
			if sens not in  newDict: 														return True
			if type(oldDict[sens]) != type({}): 					continue
			if type(newDict[sens]) != type(oldDict[sens]): 									return True

			if levels >= 2:
				for sensId in oldDict[sens]:
					if type(oldDict[sens][sensId]) != type({}): 	continue
					if mustHaveKey != "" and mustHaveKey not in oldDict[sens][sensId]: break 
					if sensId not in  newDict[sens]: 										return True

		return False

	except Exception as e:
		logger.log(30,"sensor:{}, newDict:{}, oldDict:{}".format(sens, newDict.get(sens,"---"), oldDict.get(sens,"---")), exc_info=True)

	return True



#################################
def checkresetCount(IPCin):
	IPC = copy.copy(IPCin)
	try:
		resetfile = "{}temp/{}.reset".format(G.homeDir, G.program)
		if not os.path.isfile(resetfile):
			#logger.log(20,  "checkresetCount no file for {}resetfile".format(resetfile))
			return IPC
		inpJ, inp = readJson(resetfile)
		os.remove(resetfile)
		logger.log(20,"{} checkresetCount doing reset for {:<20}".format(G.program, inp ) )
		if len(inp) < 2:
			return IPC
		for p in inpJ:
			IPC[str(p)] = 0
			#print "checkresetCount pin=", pin
		writeINPUTcount(IPC)
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	#print "checkresetCount pin=", IPC[15:25]
	return IPC

######################################
def readINPUTcount():
		IPC={}
		for ii in range(1,30):
			IPC[str(ii)] = 0
		try:
			IPC, ddd = readJson("{}{}.count".format(G.homeDir, G.program))
			logger.log(10, u" readINPUTcount-0:{}\nddd: {}".format(IPC, ddd) )
		except:
			pass
		## check if change from list to dict
		fix = False
		for p in IPC:
			try:
				int(IPC[str(p)])
			except:
				try: IPC[str(p)] =0
				except: fix = True
		if fix: IPC ={}
		if len(IPC) < 10:
			IPC = {}
			for ii in range(1,30):
				IPC[str(ii)] = 0
		out = {}
		for p in IPC:
			out[str(p)] = IPC[p]
		writeINPUTcount(out)
		return out


######################################
def writeINPUTcount(IPC):
	writeJson("{}{}.count".format(G.homeDir, G.program), IPC)

######################################
def readRainStatus():
	status, ddd = readJson("{}{}.status".format(G.homeDir, G.program))
	return status

######################################
def writeRainStatus(status):
	writeJson("{}{}.status".format(G.homeDir, G.program),status)
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



				except Exception as e:
					logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))

				if	action !="":
					if "action{}".format(action) in sens and sens["action{}".format(action)] !="":
						if	action =="UP" or action =="DOWN" or action =="1" or action =="2" or action =="3" or action =="4" or action =="5":

							logger.log(20, "cBY:{:<20} action:{}  {}".format(G.program, action, sens["action".format(action)]) )
							checkIfrebootAction(sens["action{}".format(action)])
							subprocess.call(sens["action{}".format(action)], shell=True)

					if "actionDoubleClick" in sens and sens["actionDoubleClick"] !="":
						manageActions(sens["actionDoubleClick"],waitTime=3,click=action,aType="actionDoubleClick", devId=devId)

					if "actionLongClick" in sens and sens["actionLongClick"] !="":
						manageActions(sens["actionLongClick"],waitTime=3,click=action,aType="actionLongClick", devId=devId)

		############ local action  end #######
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
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
					logger.log(20, "cBY:{:<20}  executing action: {}".format(G.program, action))
					checkIfrebootAction(action)
					subprocess.call(action, shell=True)
			return

		elif aType=="actionLongClick" and aType == G.actionDict[action][devId]["aType"]:
			if click != G.actionDict[action][devId]["click"] :
				if tt - G.actionDict[action][devId]["timerStart"] > G.actionDict[action][devId]["waitTime"]	 :
					checkIfrebootAction(action)
					logger.log(20, "cBY:{:<20}  executing action: {}".format(G.program,action))
					subprocess.call(action, shell=True)
				else  :
					del G.actionDict[action][devId]
			else:
				del G.actionDict[action][devId]
			return

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def checkIfrebootAction(action):
	# display.py might stop shutdown from going through, need to kill first
	try:
		if action.find("shutdown") >-1 or  action.find("reboot") >-1 :
			logger.log(30, "cBY:{:<20}  executing action: {}".format(G.program, action))
			killOldPgm(-1,"display.py")
			time.sleep(0.2)
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return


################################
################################


#################################
def getSensorInfo(sensDict, i2cList):
	i2cError	= ""
	try:
		#logger.log(30, "cBY:{:<20}  into sendi2cToPlugin".format(G.program) )
		sensList = ""
		for sens in sensDict:
			if sens.find("i2c") == 0: # strip i2c from the beginning of name.
				ss = sens[3:]
			else:
				ss = sens
			ll = len(sensDict[sens])
			if ll > 1:
				sensList = "{}{} {},".format(sensList, ss, ll)
			else:
				sensList = "{}{}, ".format(sensList, ss)
			for devId in sensDict[sens]:
				if sensDict[sens][devId].get("i2cOrUart","") == "uart": continue
				if "i2cAddress" in sensDict[sens][devId]:
					logger.log(10, "cBY:{:<20}   i2c:{} in sensor:{}".format(G.program, sensDict[sens][devId]["i2cAddress"], sens) )
					try:
						i2cI = int(sensDict[sens][devId]["i2cAddress"])
						if i2cI < 1: continue
					except: continue
				else: continue

				matchFound = False
				for i2cH in i2cList:
					i2cActive = i2cH.split("=")[0]
					if int(i2cActive) != i2cI: continue
					matchFound =True
					logger.log(10, "cBY:{:<20}  match found for i2c:{}".format(G.program,i2cI) )
					break
				if not matchFound:
					logger.log(10, "cBY:{:<20}  no match found for i2c:{}".format(G.program,i2cI) )
					i2cError = "{}sensor:{} - devId:{} i2c:{}/{}; ".format(i2cError, sens, devId, i2cI,hex(i2cI))

		i2cError = i2cError.strip("; ")
		if len(sensList) > 0: sensList = sensList.strip(" ").strip(",")
		return i2cError, sensList
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return "","",""

#

#################################
def getRPiType():
	try:
		#logger.log(30, "cBY:{:<20}  into sendi2cToPlugin".format(G.program) )
		#																	remove trailing null chars;  \\ for escape  of \
		rpiType	 = (subprocess.Popen("cat /sys/firmware/devicetree/base/model | tr -d '\\000' " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))
		rpiType	 = ''.join(i for i in rpiType if ord(i)>1).split("Raspberry ")
		if len(rpiType) ==2: rpiType = rpiType[1]
		else:				 rpiType = rpiType[0]
		serN	 = (subprocess.Popen("cat /sys/firmware/devicetree/base/serial-number | tr -d '\\000' " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))
		serN	 = (''.join(i for i in serN if ord(i)>1)).lstrip("0")
		rpiType  = "{}, ser#{}".format(rpiType, serN)
		#  --> Raspberry Pi 3 Model B Plus Rev 1.3/ ser#00000000dcfb216c
		return rpiType
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return ""


#################################
def getOSinfo():
	try:
		os = ""
		osInfo	 = (subprocess.Popen("cat /etc/os-release" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").split("\n")
		for line in osInfo:
			if line .find("VERSION=") == 0:
				os = line.split("=")[1].strip('"').strip(" ")
		os1 = (subprocess.Popen("uname -r" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip()
		os2 = (subprocess.Popen("uname -v" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n").strip()
		ret = "{}, {}, {}".format(os, os1, os2)
		return str(ret)
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return ""


#################################
def getTemperatureOfRPI():
	try:
		tempInfo = (subprocess.Popen("/opt/vc/bin/vcgencmd measure_temp" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))
		if tempInfo.find("No such file") >-1 or tempInfo == "":
			tempInfo = (subprocess.Popen("/usr/bin/vcgencmd measure_temp" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))

		try:	temp = str(tempInfo.split("=")[1].split("'")[0])
		except: temp = "0"
		return  temp
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return ""


#################################
def checkIfThrottled():
	try:
		MESSAGES = {
			0:  'E#0_Under-volt',
			1:  'E#1_ARM_freq_capped',
			2:  'E#2_Curr_throttled',
			3:  'E#3_Soft_temp_limit_active',
			16: 'E#16_Under-volt_occd_since_reb.',
			17: 'E#17_Throttled_occd_since_reb.',
			18: 'E#18_ARM_freq_capped_occd_since_reb.',
			19: 'E#19_Soft_temp_limit_occd'
		}
		#0x50005 =  327685 =
		#' 1010000000000000101
		#  8 6 4 2 1 8 6 4 2 0
		#111100000000000001010
		#||||             ||||_ under-voltage
		#||||             |||_ currently throttled
		#||||             ||_ arm frequency capped
		#||||             |_ soft temperature reached
		#||||_ under-voltage has occurred since last reboot
		#|||_ throttling has occurred since last reboot
		#||_ arm frequency capped has occurred since last reboot
		#|_ soft temperature reached since last reboot		


		tempInfo = (subprocess.Popen("/opt/vc/bin/vcgencmd get_throttled" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))
		#logger.log(20, "cBY:{:<20} tempInfo old: {}".format(G.program, tempInfo))
		if tempInfo.find("No such file") > -1 or tempInfo =="":
			tempInfo = (subprocess.Popen("/usr/bin/vcgencmd get_throttled" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))
		#logger.log(20, "cBY:{:<20} tempInfo new: {}".format(G.program, tempInfo))

		try:	code = tempInfo.split("=")[1][:-1]
		except: return "err_in_proc_check_power"
		try:	temp = bin(int(code,0))
		except: return "err_in_proc_check_power"
		msg = ""
		for position in MESSAGES:
			message = MESSAGES[position]
			#Check for the binary digits to be "on" for each warning message
			if len(temp) > position and temp[0 - position - 1] == '1':
				msg += message+";"
		if msg == "": return "no_problem_detected"
		retCode = "code:{}={}".format(code, msg).strip(";")
		G.lastVcode = retCode
		if retCode != G.lastVcode:
			logger.log(20, "retCode: {}".format(retCode))
		return  retCode
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return ""


#################################
def getLastBoot():
	try:
		lastBoot = (subprocess.Popen("uptime -s" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')).strip("\n")
		return lastBoot
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return ""

#################################
def resetI2cBus():
	try:
		cmd = "sudo su; echo '3f804000.i2c' > /sys/bus/platform/drivers/i2c-bcm2835/unbind;echo '3f804000.i2c' > /sys/bus/platform/drivers/i2c-bcm2835/bind &"
		subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return 


#################################
def checki2cdetect():
	try:
		i2cfile = "{}temp/i2cdetect".format(G.homeDir)
		if os.path.isfile(i2cfile):
			os.remove(i2cfile)

		cmd = "/usr/sbin/i2cdetect -y 1 > {} &".format(i2cfile)
		subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		time.sleep(2)

		if os.path.isfile(i2cfile):
			f = open(i2cfile)
			i2cout = f.read()
			f.close()

			if i2cout.find("   0  1  2  3  4  5  6  ") > -1 and i2cout.find("70: ") > 10 : 
				#logger.log(20, "cBY:{:<20} cmd:{} ret ok .. is:\n{}".format(G.program, cmd, i2cout))
				return "ok"

			logger.log(20, "cBY:{:<20} cmd:{}  ret bad.. is:\n{}".format(G.program, cmd, i2cout))

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return "bad"

#################################
def geti2c():
	try:
		i2cChannelsINTHex=[]
		i2cChannelsHEX=[]
		temp =[]
		retx = subprocess.Popen("i2cdetect -y 1",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		ret   = retx[0].decode('utf-8')
		reterr = retx[1].decode('utf-8')

		if reterr is not  None and reterr.find("No such file or directory") > 0:
			i2cChannels=["i2c.ERROR:.no.such.file....redo..SSD?"]
		else:
			lines = ret.split("\n")
			temp=[]
			ii=-1
			for line in	 lines:
				if line.find(":") ==-1: continue  # skip non data lines
				ii+=1
				line = line[3:]
				line = line.replace("-"," ")
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
				i2cChannelsINTHex.append("{}={}".format(channel,hex(channel)))
				i2cChannelsHEX.append("{}".format(hex(channel)))
		return i2cChannelsINTHex, i2cChannelsHEX
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return ["i2c detect error"]


#################################
def geti2cIntChannels():
	retInt = []
	try:
		i2cChannelsINTHex,i2cChannelsHEX = geti2c()
		for ret in i2cChannelsINTHex:
			retInt.append(int(ret.split("=")[0]))
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		return  []
	return retInt


#################################
def sendSensorAndRPiInfoToPlugin(sensDict, fanOnTimePercent="", ):
	try:

		i2cok 						= checki2cdetect()
		i2cListIntHex,i2cListHex	= geti2c()
		i2cError, sensList			= getSensorInfo(sensDict,i2cListIntHex)
		rpiType						= getRPiType()
		os							= getOSinfo()
		temp						= getTemperatureOfRPI()
		RPI_throttled 				= checkIfThrottled()
		lastBoot					= getLastBoot()
		data = {"i2c_ok":i2cok, "sensors_active":sensList, "i2c_active":json.dumps(i2cListHex).replace(" ","").replace("[","").replace("]","").replace('"','').replace('0x','x'),"temp":temp,
			 "rpi_type":rpiType, "op_sys":os, "last_boot":lastBoot,"last_masterStart":G.last_masterStart,"RPI_throttled":"{}".format(RPI_throttled)}
		if fanOnTimePercent != "": data["fan_OnTime_Percent"] = int(fanOnTimePercent*100)
		if i2cError != "": data["i2cError"]   = i2cError
		##print data
		sendURL(data=data, sendAlive="alive", squeeze=False, escape=True)
		if G.i2cMustBeOn and ( not i2cok or i2cError != ""):
			startI2C(text="reason: {}, {}".format(i2cok, i2cError))
			logger.log(20, "cBY:{:<20} enabled i2c reason: {}, {}".format(G.program, i2cok, i2cError))

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return

#################################
def startI2C(text=""):
	try:
		cmd = "sudo raspi-config nonint do_i2c 0 "
		subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		logger.log(20, "cBY:{:<20} enabled i2c with cmd:{}".format(G.program, cmd))
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))


#################################
def testBad(newX, lastX, inXXX, deltaAbs=99999999.):

	xxx = inXXX
	try:
		if lastX is not None and newX is not None:
			if str(newX).find("bad") == -1:
				if str(lastX).find("bad") == -1:
					dAbs = abs( float(lastX) - float(newX) )
					if dAbs > deltaAbs: xxx = 999.
					xxx = max(xxx, abs( dAbs ) / max(0.1, abs(float(lastX) + float(newX)) ) )
				else:
					xxx = 9991.
			else:
				if lastX.find("bad") > -1:
					xxx = 0
				else:
					xxx = 9992.
		else:
			xxx = 0
	except Exception as e:
		logger.log(20, "cBY:{:<20} newX:{}, lastX:{}, inXXX:{}".format(G.program,newX, lastX, inXXX))
		logger.log(20, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		xxx = 9993.
	return xxx



#################################
def checkIfAliveNeedsToBeSend():
	try:
		lastSend = 0
		if os.path.isfile("{}temp/messageSend".format(G.homeDir)):
			try:  	lastSend = float(os.path.getmtime("{}temp/messageSend".format(G.homeDir)))
			except:	lastSend = 0
		#logger.log(20, "cBY:{:<20} last messageSend was {:.1f} sec ago".format(G.program, time.time() - lastSend ))
		if time.time() - lastSend > 100:	 # do we have to send alive signal to plugin?
			sendURL(sendAlive=True )
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return


#################################
def checkIfPauseSensor(sensor):
	try:
		tt = time.time()
		lastSend = 0
		if os.path.isfile("{}temp/pauseSensor".format(G.homeDir)):
			f = open("{}temp/pauseSensor".format(G.homeDir),"r")
			rr = f.read()
			f.close()
			if rr.find(sensor) >-1:
				try:	
					xx = json.loads(rr)
					sleepFor = xx[sensor]
					sleepFor = float(sleepFor)
					logger.log(20, "cBY:{:<20} sleep for {}".format(G.program,sleepFor))
					startSleep = time.time()
					for ii in range(1000):
						echoLastAlive(sensor)
						time.sleep(5)
						if time.time() - startSleep >= sleepFor: break
					logger.log(20, "cBY:{:<20} sleep ended".format(G.program))
				except:	pass
				subprocess.call("/usr/bin/sudo rm {}temp/pauseSensor".format(G.homeDir), shell=True)
				return 
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
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
		"""We need to calibrate the sensor
		otherwise we'll be going round in circles.

		basically we need to go round in circles and average out
		the min and max values, that is then the offset (?)
		https://github.com/kriswiner/MPU-6050/wiki/Simple-and-Effective-Magnetometer-Calibration

		Keep rotating the sensor in all direction until the output stops updating
		"""

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
						logger.log(20,'magCalibrate Update: '+str(calib))
				time.sleep(0.1)
			except:
				break
		saveCalibration(theClass, calib)
		theClass.magOffset = setOffsetFromCalibration(theClass.calibrations)
		return True

#################################
def saveCalibration(theClass, calib):
	logger.log(20,'saveCalibration:  enableCalibration = {}'.format(calib))
	writeJson(theClass.calibrationFile, calib, sort_keys=True)

#################################
def setOffsetFromCalibration(calib):
		try:
			offset=[]
			offset[0] = (calib['minX'] + calib['maxX'])/2
			offset[1] = (calib['minY'] + calib['maxY'])/2
			offset[2] = (calib['minZ'] + calib['maxZ'])/2
			logger.log(20,'theClass.magOffset {}'.format(offset))
			return offset
		except Exception as e:
			logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		return [0,0,0]

#################################
def loadCalibration(calibrationFile):
		calibrations, calib = readJson("{}{}.status".format(G.program, G.program))
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
		"""Experimentally put roll and pitch back in to
		get some tilt compenstation
		https://gist.github.com/timtrueman/322555
		roll	== x-z
		pitch	== y-z
		v =[x,y,z]
		"""
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
		#global magOffsetX, magOffsetY, magOffsetZ, magDivider, magResolution, declination, deltaX, sensorRefreshSecs, enableCalibration, displayEnable, sensorLoopWait, minSendDelta, offsetTemp, magFregRate, accelerationGain, 
		changed = ""

		G.i2cAddress = getI2cAddress(sens,default="")

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
			if "magFregRate" in sens:
				if G.magFregRate !="" and	G.magFregRate != sens["magFregRate"]:
					changed ="{}magFregRate".format(changed)
				G.magFregRate= sens["magFregRate"]
		except:
			G.magFregRate = "3.0"
			pass

		try:
			if "accelerationGain" in sens:
				if G.accelerationGain !="" and	G.accelerationGain != sens["accelerationGain"]:
					changed ="{}accelerationGain".format(changed)
				G.accelerationGain= sens["accelerationGain"]
		except:
			G.accelerationGain = "1"
			pass

		try:
			if "magGain" in sens:
				if G.magGain != "" and  G.magGain != sens["magGain"]:
					changed ="{}magGain".format(changed)
				G.magGain= sens["magGain"]
		except:
			G.magGain = "4.7"
			pass

		return changed

#################################
def checkMGACCGYRdata(new, oldIN, dims, coords, testForBad, devId, sensor, quick, sumTest = {"dim":"","limits":[1000000,-100000]}, singleTest={"dim":"","coord":"","limits":[1000000,-100000]}):
		old = copy.copy(oldIN)
		try:
			data = {"sensors":{sensor:{devId:{}}}}
			retCode = "ok"
			if new =="": return old
			if str(new).find("bad") >-1:
				G.badCount1+=1
				G.sensorWasBad = True
				if G.badCount1 < 5:
					logger.log(10, "cBY:{:<20}  bad sensor".format(G.program))
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
				#print( "reject 2")
				return old
			if new[testForBad] =="":
				G.badCount5 +=1
				if G.badCount5 < 5:
					logger.log(10, "cBY:{:<20}  bad sensor".format(G.program))
				if G.badCount5 > 15:
					data["sensors"][sensor][testForBad]="badSensor"
					sendURL(data)
					restartMyself(reason=" empty sensor reading, need to restart to get sensors reset",doPrint= False)
				return old

			G.badCount5 =0
			if singleTest["dim"]!="":
					if ( abs(new[singleTest["dim"]][singleTest["coord"]]) >	 singleTest["limits"][1] or
						 abs(new[singleTest["dim"]][singleTest["coord"]]) <= singleTest["limits"][0]):
						logger.log(10, "{}-{} out of bounds, ignoring: {}".format(singleTest["dim"], singleTest["coord"], new))
						G.badCount4+=1
						if G.badCount4 > 10:
							restartMyself(reason="{}- wrong, need to restart to get sensors reset".format(singleTest),doPrint= False)
						#print( "reject 3")
						return old

			G.badCount4 =0
			if sumTest["dim"]!="":
				dd= sumTest["dim"]
				SUM = sum(	[abs(new[dd][x]) for x in new[dd] ]	 )
				if SUM <=sumTest["limits"][0] or SUM > sumTest["limits"][1]:
					logger.log(10, "{} sum of values bad ".format(sumTest, SUM))
					G.badCount3 +=1
					if G.badCount3 > 10:
						restartMyself(reason="{}- wrong, need to restart to get sensors reset".format(sumTest),doPrint= False)
					#print( "reject 4")
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

			if nTotal > 1 and totalDelta/nTotal > max(0.01,G.deltaX[devId]):
				#logger.log(20," sendNow: delta={}  > {}".format(totalDelta/nTotal , G.deltaX[devId]))
				retCode = "sendNow"

			if nTotal > 1 and totalABS ==0:
				G.badCount2+=1
				if G.badCount2 > 5:
					restartMyself(reason="{} values identival 5 times need to restart to get sensors reset".format(dims),doPrint= False)
				#print( "reject 5")
				return old

			else:
				G.badCount2 = 0

			if G.sensorWasBad:
				restartMyself(reason="{} back from bad sensor, restart".format(dims),doPrint= False)

			data["sensors"][sensor][devId] = new
			#print(  time.time() - G.lastAliveSend , abs(G.sensorRefreshSecs) , quick , retCode=="sendNow" , time.time() - G.lastAliveSend , G.minSendDelta )
			if (  (time.time() - G.lastAliveSend > 60 or quick or retCode=="sendNow" )  and (time.time() - G.lastAliveSend > G.minSendDelta) ):
					#logger.log(20,"sending {}".format(data))
					sendURL(data)
					old[devId]	= copy.copy(new)
					G.lastAliveSend  = time.time()

		except Exception as e:
			logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
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
		self.fr = io.open("/dev/i2c-{}".format(bus), "rb", buffering=0)
		self.fw = io.open("/dev/i2c-{}".format(bus), "wb", buffering=0)
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
def findString(string, filename):
	if string == "": return 0

	try:
		text = doReadSimpleFile(filename).split("\n")
		for line in text:
			if line.find(string) ==0:
				return 2
			if line.find("#{}".format(string) ) ==0:
				return 1
		return 0
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		logger.log(30, "string:{}, fname:{}".format(G.program, string, filename))
		if str(e).find("Read-only file system:") >-1:
			doReboot(tt=0)
	return 3


#################################
def checkIfInFile(stringItems, file):
	if stringItems =="" or stringItems ==[]: return "error"
	if stringItems[0] == "": return "error"
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
			if nFound == nItems: return "found"
		return "not found" # == not found
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		if str(e).find("Read-only file system:") >-1:
			subprocess.call("/usr/bin/sudo reboot", shell=True)
	return "error"


#################################
def uncommentOrAdd(string, file, before="", nLines=1):
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
			if line.find("#{}".format(string)) ==0:
				found =1
				break
		if found ==0:
			if before !="" and text0.find(before) >-1:
				done=False
				f=open(file,"w")
				for line in text:
					if line.find(before) ==0 and not done:
						f.write("{}\n".format(line))
						done = True
					if len(line)> 0: f.write("{}\n".format(line)) # remove empty lines
				f.close()
				return 1

			text0 ="{}\n{}\n".format(text0,string)
			f=open(file,"w")
			f.write(text0.replace("\n\n","\n"))
			f.close()
			return 1

		if found ==1:
			iLines =0
			f=open(file,"w")
			for line in text:
				if line.find(string)>-1:
					f.write("{}\n".format(line[1:]))
					iLines +=1
					continue
				if iLines < nLines and iLines >0:
					iLines+=1
					if line.find("#")==0:
						line = line[1:]
				if len(line)> 0:
					f.write("{}\n".format(line)) # remove empty lines
			f.close()
			return 1
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		if str(e).find("Read-only file system:") >-1:
			doReboot(tt=0)


#################################
def removefromFile(string, file, nLines=1):
	if string =="": return 0
	stringItems = string.split()
	nItems		= len(stringItems)
	iLines=0
	try:
		f	  = open(file,"r")
		text0 = f.read()
		text  = text0.split("\n")
		f.close()
		out=""
		skip = 0
		for line in text:
			skip -=1
			if skip > 0: continue
			lineItems = line.split()
			nFound	= 0
			for item in stringItems:
				for item2 in lineItems:
					if item == item2:
						nFound +=1
						break
			if nFound == nItems:
				skip = nLines
				continue
			out = "{}{}\n".format(out, line)
		out = out.replace("\n\n","\n")
		if out != text0:
			f=open(file,"w")
			f.write(out)
			f.close()
		return 0
	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
		if str(e).find("Read-only file system:") >-1:
			doReboot(tt=0)
	return 1

#################################
def startNTP(mode=""):
	if mode == "simple": subprocess.call("/usr/bin/sudo /etc/init.d/ntp start ", shell=True)
	else: subprocess.call("/usr/bin/sudo /etc/init.d/ntp stop ; /usr/bin/sudo ntpd -q -g ; /usr/bin/sudo /etc/init.d/ntp start ", shell=True)

	testNTP()
	return

#  ntpStatus		   = "not started" #   / "started, working" / "started not working" / "temp disabled" / "stopped after not working"

#################################
def installNTP():
	if os.path.isfile("/etc/init.d/ntp"): return 
	logger.log(30, "cBY:{:<20} started NTP install w >>/usr/bin/sudo apt-get -y install ntp &<<;  will be installed next time around")
	subprocess.call("/usr/bin/sudo apt-get -y install ntp & ", shell=True)
	time.sleep(30)
	return



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
	ret = (subprocess.Popen("/usr/bin/ntpq -p",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))
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
	subprocess.call("/usr/bin/sudo /etc/init.d/ntp stop &", shell=True)
	if mode =="":
		G.ntpStatus = "not started"
	elif mode == "temp":
		G.ntpStatus = "temp disabled"
	elif mode.find("final") >-1:
		G.ntpStatus = "stopped, after not working"
	return


####-------------------------------------------------------------------------####
def isValidMAC(mac0):
		macx = mac0.split(u":")
		if len(macx) != 6 : # len(mac.split(u"D0:D2:B0:88:7B:76")):
			return False

		for xx in macx:
			if len(xx) !=2:
				return False

			try: 	int(xx,16)
			except: return False

		return True

#################################
def testPing(ipToPing):
	if (G.networkType  not in G.useNetwork and ipToPing =="")  or G.wifiType !="normal": return 0
	try:
		if pgmStillRunning("installLibs.py"):
			G.ipConnection = time.time()
			return -1


		# IPnumber setup?
		if not isValidIP(ipToPing):
			logger.log(10, "cBY:{:<20}  testPing bad ip number to ping >>{}<<".format(G.program,ipToPing) )
			return 1


		for ii in range(4):
			cmd= "/bin/ping	 -c 1 -W 1 {} >/dev/null 2>&1".format(ipToPing)
			ret = subprocess.call(cmd,shell=True)
			# send max 4 packets, wait 1 secs between each and stop if one gets back
			#print cmd, "ret=", ret,"=="
			if int(ret) == 0:
				G.ipConnection = time.time()
				return 0
		if ipToPing !="":
			return 1

		logger.log(10,"cBY:{:<20} testPing can not connect to : {}	ping code:{}".format( G.program, ipToPing,ret) )

		return 2

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return 2




################################
def testROUTER():
	try:
		G.ipOfRouter = getIPofRouter()
		if isValidIP(G.ipOfRouter):
			logger.log(10, "cBY:{:<20} router info ip:>{}<".format(G.program,G.ipOfRouter))
			ret = testPing(G.ipOfRouter)
			if	ret == 0:
				logger.log(10, "cBY:{:<20} ROUTER server reachable at:{}".format(G.program,G.ipOfRouter))
				return 0
			if ret == -1:
				logger.log(30, "cBY:{:<20} still waiting for installLibs to finish".format(G.program))
				time.sleep(30)
				return 1
			time.sleep(1)
			newIP = getIPofRouter()
			if newIP != G.ipOfRouter and isValidIP(newIP):
				G.ipOfRouter = newIP
				if	testPing(G.ipOfRouter)  ==0:
					logger.log(30, "cBY:{:<20}  ROUTER server reachable at:{}".format(G.program,G.ipOfRouter))
					return 0
			logger.log(20, "cBY:{:<20}  ROUTER server NOT reachable at:{}".format(G.program,G.ipOfRouter))
			return 1
		else:
			logger.log(20, "cBY:{:<20} ipOfRouter not valid:".format(G.ipOfRouter))
			return 1

	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	return 1
################################
def testIndigoServer():
	try:
		if not isValidIP(G.ipOfServer):
			return 1

		ret =testPing(G.ipOfServer)
		if	ret ==0:
			logger.log(10, "cBY:{:<20}  ROUTER server reachable at:{}".format(G.program,G.ipOfRouter))
			return 0
		if ret ==-1:
			logger.log(30, "cBY:{:<20} still waiting for installLibs to finish".format(G.program))
			time.sleep(30)
			return 1
		return 1


	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
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
		if isValidIP(G.ipOfServer):
			testIndigo = testPing(G.ipOfServer)
		else:
			testIndigo = 1
		testD	   = testROUTER()

		if testIndigo == 0 and testD == 0:
			G.networkStatus = "indigoInet"
			return

		if testIndigo == 0 and testD != 0:
			G.networkStatus = "indigoLocal"
			return

		if testIndigo != 0 and testD == 0:
			G.networkStatus = "Inet"
			return


		if testIndigo != 0 and testD != 0:
			G.networkStatus = "local"
			return



	except Exception as e:
		logger.log(30, "cBY:{:<20} Line {} has error={}".format(G.program, sys.exc_info()[-1].tb_lineno, e))
	G.networkStatus = "local"
	return




