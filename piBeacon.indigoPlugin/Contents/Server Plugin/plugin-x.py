#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# pibeacon Plugin
# Developed by Karl Wachs
# karlwachs@me.com

import os
import sys
import subprocess
import pwd
import datetime
import time
import json
import copy
import math
import socket
import threading
import SocketServer
import Queue
import cProfile
import pstats
import logging

#import pydevd_pycharm
#pydevd_pycharm.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)

try:
	# noinspection PyUnresolvedReferences
	import indigo
except ImportError:
	pass
################################################################################
##########  Static parameters, not changed in pgm
################################################################################
_sqlLoggerDevTypes  = ["isRelayDevice","isSensorDevice"]
_sqlLoggerIgnoreStates = {"isRelayDevice":		"status,sensorvalue_ui,updateReason,lastStatusChange"
				         ,"isRPISensorDevice":	"displayStatus,status,sensorvalue_ui,lastStatusChange"}
_debugAreas = ["Logic","HTTPlistener","Polling","SetupShelly","Actions","SQLlogger","SQLSuppresslog","Special"]



_defaultDateStampFormat				= u"%Y-%m-%d %H:%M:%S"

################################################################################
################################################################################
################################################################################

# 
# noinspection PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PySimplifyBooleanCheck,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyAttributeOutsideInit,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class Plugin(indigo.PluginBase):
####-------------------------------------------------------------------------####
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

		self.pluginShortName 			= "shelly"

		self.quitNow					= ""
		self.getInstallFolderPath		= indigo.server.getInstallFolderPath()+"/"
		self.indigoPath					= indigo.server.getInstallFolderPath()+"/"
		self.indigoRootPath 			= indigo.server.getInstallFolderPath().split("Indigo")[0]
		self.pathToPlugin 				= self.completePath(os.getcwd())

		major, minor, release 			= map(int, indigo.server.version.split("."))
		self.indigoVersion 				= float(major)+float(minor)/10.
		self.indigoRelease 				= release
	

		self.pluginVersion				= pluginVersion
		self.pluginId					= pluginId
		self.pluginName					= pluginId.split(".")[-1]
		self.myPID						= os.getpid()
		self.pluginState				= "init"

		self.myPID 						= os.getpid()
		self.MACuserName				= pwd.getpwuid(os.getuid())[0]

		self.MAChome					= os.path.expanduser(u"~")
		self.userIndigoDir				= self.MAChome + "/indigo/"
		self.indigoPreferencesPluginDir = self.getInstallFolderPath+"Preferences/Plugins/"+self.pluginId+"/"
		self.indigoPluginDirOld			= self.userIndigoDir + self.pluginShortName+"/"
		self.PluginLogFile				= indigo.server.getLogsFolderPath(pluginId=self.pluginId) +"/plugin.log"


		formats=	{   logging.THREADDEBUG: "%(asctime)s %(msg)s",
						logging.DEBUG:       "%(asctime)s %(msg)s",
						logging.INFO:        "%(asctime)s %(msg)s",
						logging.WARNING:     "%(asctime)s %(msg)s",
						logging.ERROR:       "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s",
						logging.CRITICAL:    "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s" }

		date_Format = { logging.THREADDEBUG: "%Y-%m-%d %H:%M:%S",
						logging.DEBUG:       "%Y-%m-%d %H:%M:%S",
						logging.INFO:        "%Y-%m-%d %H:%M:%S",
						logging.WARNING:     "%Y-%m-%d %H:%M:%S",
						logging.ERROR:       "%Y-%m-%d %H:%M:%S",
						logging.CRITICAL:    "%Y-%m-%d %H:%M:%S" }
		formatter = LevelFormatter(fmt="%(msg)s", datefmt="%Y-%m-%d %H:%M:%S", level_fmts=formats, level_date=date_Format)

		self.plugin_file_handler.setFormatter(formatter)
		self.indiLOG = logging.getLogger("Plugin")  
		self.indiLOG.setLevel(logging.THREADDEBUG)

		self.indigo_log_handler.setLevel(logging.WARNING)
		indigo.server.log("initializing	 ... ")

		indigo.server.log(  u"path To files:          =================")
		indigo.server.log(  u"indigo                  {}".format(self.indigoRootPath))
		indigo.server.log(  u"installFolder           {}".format(self.indigoPath))
		indigo.server.log(  u"plugin.py               {}".format(self.pathToPlugin))
		indigo.server.log(  u"Plugin params           {}".format(self.indigoPreferencesPluginDir))

		self.indiLOG.log( 0, "!!!!INFO ONLY!!!!  logger  enabled for   0             !!!!INFO ONLY!!!!")
		self.indiLOG.log( 5, "!!!!INFO ONLY!!!!  logger  enabled for   THREADDEBUG   !!!!INFO ONLY!!!!")
		self.indiLOG.log(10, "!!!!INFO ONLY!!!!  logger  enabled for   DEBUG         !!!!INFO ONLY!!!!")
		self.indiLOG.log(20, "!!!!INFO ONLY!!!!  logger  enabled for   INFO          !!!!INFO ONLY!!!!")
		self.indiLOG.log(30, "!!!!INFO ONLY!!!!  logger  enabled for   WARNING       !!!!INFO ONLY!!!!")
		self.indiLOG.log(40, "!!!!INFO ONLY!!!!  logger  enabled for   ERROR         !!!!INFO ONLY!!!!")
		self.indiLOG.log(50, "!!!!INFO ONLY!!!!  logger  enabled for   CRITICAL      !!!!INFO ONLY!!!!")

		indigo.server.log(  u"check                   {}  <<<<    for detailed logging".format(self.PluginLogFile))
		indigo.server.log(  u"Plugin short Name       {}".format(self.pluginShortName))
		indigo.server.log(  u"my PID                  {}".format(self.myPID))	 
		indigo.server.log(  u"set params for indigo V {}".format(self.indigoVersion))	 

####-------------------------------------------------------------------------####
	def __del__(self):
		indigo.PluginBase.__del__(self)

	###########################		INIT	## START ########################

####-------------------------------------------------------------------------####
	def startup(self):
		try:
			if self.pathToPlugin.find("/"+self.pluginName+".indigoPlugin/")==-1:
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"The pluginname is not correct, please reinstall or rename")
				self.errorLog(u"It should be   /Libray/....../Plugins/"+self.pluginName+".indigPlugin")
				p=max(0,self.pathToPlugin.find("/Contents/Server"))
				self.errorLog(u"It is: "+self.pathToPlugin[:p])
				self.errorLog(u"please check your download folder, delete old *.indigoPlugin files or this will happen again during next update")
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.errorLog(u"---------------------------------------------------------------------------------------------------------------" )
				self.sleep(100000)
				self.quitNOW="wromg plugin name"
				return

			if not self.checkPluginPath(self.pluginName,  self.pathToPlugin):
				exit()


			self.startTime = time.time()

			self.getDebugLevels()

			self.setVariables()

			#### basic check if we can do get path for files			 
			self.initFileDir()

			self.checkcProfile()

			self.myLog( text = " --V {}   initializing  -- ".format(self.pluginVersion), destination="standard")

			self.setupBasicFiles()

			self.startupFIXES0()

			self.readConfig()

			self.resetMinMaxSensors(init=True)

			self.setSqlLoggerIgnoreStatesAndVariables()
	  
 			self.indiLOG.log(10, "startup(self): setting variables, debug ..   finished ")

		except Exception, e:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(50,u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)
		return


	####-----------------	 ---------
	def setSqlLoggerIgnoreStatesAndVariables(self):
		try:
			if self.indigoVersion <  7.4:                             return 
			if self.indigoVersion == 7.4 and self.indigoRelease == 0: return 

			outOND  = ""
			outOffD = ""
			outONV  = ""
			outOffV = ""
			if self.decideMyLog(u"SQLSuppresslog"): self.indiLOG.log(20,"setSqlLoggerIgnoreStatesAndVariables settings:{} ".format( self.SQLLoggingEnable) )
			if not self.SQLLoggingEnable["devices"]: # switch sql logging off
				for ff in _sqlLoggerDevTypes:

					statesToInclude = _sqlLoggerIgnoreStates[ff].split(",")[0]
					for dev in indigo.devices.iter("props."+ff):	
						props = dev.pluginProps
						skip = False
						if ff == "isSensorDevice":
							for kk in _sqlLoggerDevTypesNotSensor:
								if kk in props:
									skip=True
									break
						if skip: continue
						sp = dev.sharedProps
						#if self.decideMyLog(u"SQLSuppresslog"): self.indiLOG.log(20,"\n1 dev: {} current sharedProps: testing for off \n{}".format(dev.name.encode("utf8"), unicode(sp).replace("\n","")) )
						if "sqlLoggerIgnoreStates" not in sp or statesToInclude not in sp["sqlLoggerIgnoreStates"]: 
							sp["sqlLoggerIgnoreStates"] = copy.copy(_sqlLoggerIgnoreStates[ff])
							dev.replaceSharedPropsOnServer(sp)
							outOffD += dev.name+"; "
							dev2 = indigo.devices[dev.id]
							sp2 = dev2.sharedProps

			else:  # switch sql logging (back) on
				for ff in _sqlLoggerDevTypes:
					for dev in indigo.devices.iter("props."+ff):	
						props = dev.pluginProps
						skip = False
						### alsways set completely
						if ff == "isSensorDevice":
							for kk in _sqlLoggerDevTypesNotSensor:
								if kk in props:
									skip=True
									break
						if skip: continue
						sp = dev.sharedProps
						if "sqlLoggerIgnoreStates" in sp and len(sp["sqlLoggerIgnoreStates"]) > 0: 
							outOffD += dev.name+"; "
							sp["sqlLoggerIgnoreStates"] = ""
							dev.replaceSharedPropsOnServer(sp)



			if not self.SQLLoggingEnable["variables"]:

				for v in self.varExcludeSQLList:
					var = indigo.variables[v]
					sp = var.sharedProps
					if "sqlLoggerIgnoreChanges" in sp and sp["sqlLoggerIgnoreChanges"] == "true": 
						continue
					outOffV += var.name+"; "
					sp["sqlLoggerIgnoreChanges"] = "true"
					var.replaceSharedPropsOnServer(sp)

			else:
				for v in self.varExcludeSQLList:
					var = indigo.variables[v]
					sp = var.sharedProps
					if "sqlLoggerIgnoreChanges" not in sp  or sp["sqlLoggerIgnoreChanges"] != "true": 
						continue
					outONV += var.name+"; "
					sp["sqlLoggerIgnoreChanges"] = ""
					var.replaceSharedPropsOnServer(sp)

			if self.decideMyLog(u"SQLSuppresslog"): 
				self.indiLOG.log(20," \n\n")
				if outOffD !="":
					self.indiLOG.log(20," switching off SQL logging for special devtypes/states:\n{}\n for devices:\n>>>{}<<<".format(json.dumps(_sqlLoggerIgnoreStates, sort_keys=True, indent=2), outOffD.encode("utf8")) )

				if outOND !="":
					self.indiLOG.log(20," switching ON SQL logging for special states for devices: {}".format(outOND.encode("utf8")) )

				if outOffV !="":
					self.indiLOG.log(20," switching off SQL logging for variables :{}".format(outOffV.encode("utf8")) )

				if outONV !="":
					self.indiLOG.log(20," switching ON SQL logging for variables :{}".format(outONV.encode("utf8")) )
				self.indiLOG.log(20,"setSqlLoggerIgnoreStatesAndVariables settings end\n")



		except Exception, e:
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 


####-------------------------------------------------------------------------####
	def initFileDir(self):

		try:
			return 
			if not os.path.exists(self.indigoPreferencesPluginDir):
				os.mkdir(self.indigoPreferencesPluginDir)

		except Exception, e:
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 

	
	####-------------------------------------------------------------------------####
	def startupFIXES0(self): # change old names used
		try:
			return 
		except Exception, e:
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 




####-------------------------------------------------------------------------####
	def setupBasicFiles(self):
		try:
			return 
		except Exception, e:
			self.indiLOG.log(40,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 



####-------------------------------------------------------------------------####
	def getDebugLevels(self):
		try:
			self.debugLevel			= []
			for d in _debugAreas:
				if self.pluginPrefs.get(u"debug"+d, False): self.debugLevel.append(d)


			try: self.debugRPI			 = int(self.pluginPrefs.get(u"debugRPI", -1))
			except: self.debugRPI=-1
		except Exception, e:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
			self.indiLOG.log(50,u"Error in startup of plugin, plugin prefs are wrong ")
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
		return




####-------------------------------------------------------------------------####
	def setVariables(self):
		try:
			self.deviceStopCommIgnore 		= 0

			self.setLogfile(self.pluginPrefs.get("logFileActive2", "standard"))

			try:
				xx = (self.pluginPrefs.get("SQLLoggingEnable", "on-on")).split("-")
				self.SQLLoggingEnable ={"devices":xx[0]=="on", "variables":xx[1]=="on"}
			except:
				self.SQLLoggingEnable ={"devices":False, "variables":False}

			try:
				self.tempUnits				= self.pluginPrefs.get(u"tempUnits", u"Celsius")
			except:
				self.tempUnits				= u"Celsius"

			try:
				self.tempDigits				 = int(self.pluginPrefs.get(u"tempDigits", 1))
			except:
				self.tempDigits				 = 1

			try:
				self.rainUnits				= self.pluginPrefs.get(u"rainUnits", u"mm")
			except:
				self.rainUnits				= u"mm"

			try:
				self.rainDigits				 = int(self.pluginPrefs.get(u"rainDigits", 0))
			except:
				self.rainDigits				 = 0

			try:
				self.pressureUnits			= self.pluginPrefs.get(u"pressureUnits", u"hPascal")
			except:
				self.pressureUnits			= u"hPascal"
			if 	self.pressureUnits			== u"mbar": self.pressureUnits = u"mBar"

			try:
				self.distanceUnits			= float(self.pluginPrefs.get(u"distanceUnits", 1.))
			except:
				self.distanceUnits			= 1.0
			try:
				self.speedUnits				= float(self.pluginPrefs.get(u"speedUnits", 1.))
			except:
				self.speedUnits				= 1.0

			self.portOfIndigoServer			= int(self.pluginPrefs.get(u"portOfIndigoServer", 7987))

			self.portOfServer				= self.pluginPrefs.get(u"portOfServer", u"8176")
			self.userIDOfShellyDevices		= self.pluginPrefs.get(u"userIDOfShellyDevices", u"")
			self.passwordOfShellyDevices	= self.pluginPrefs.get(u"passwordOfShellyDevices", u"")
			self.IndigoServerIPNumber		= self.pluginPrefs.get(u"IndigoServerIPNumber", u"192.168.1.x")

			self.useCurlOrPymethod				= self.pluginPrefs.get(u"useCurlOrPymethod", "/usr/bin/curl")
			if self.useCurlOrPymethod == "curl" or len(self.useCurlOrPymethod) < 4:
				self.useCurlOrPymethod = "/usr/bin/curl"
				self.pluginPrefs["useCurlOrPymethod"] = self.useCurlOrPymethod

	
			self.pythonPath					= u"/usr/bin/python2.6"
			if os.path.isfile(u"/usr/bin/python2.7"):
				self.pythonPath				= u"/usr/bin/python2.7"
			elif os.path.isfile(u"/usr/bin/python2.6"):
				self.pythonPath				= u"/usr/bin/python2.6"

		except Exception, e:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(50,u"Error in startup of plugin, waiting for 2000 secs then restarting plugin")
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.sleep(2000)
			exit(1)

		self.lastSaveConfig = 0

		return


######################################################################################
	# Indigo Trigger Start/Stop
######################################################################################

####-------------------------------------------------------------------------####
	def triggerStartProcessing(self, trigger):
		self.triggerList.append(trigger.id)

####-------------------------------------------------------------------------####
	def triggerStopProcessing(self, trigger):
		if trigger.id in self.triggerList:
			self.triggerList.remove(trigger.id)

	#def triggerUpdated(self, origDev, newDev):
	#	self.triggerStopProcessing(origDev)
	#	self.triggerStartProcessing(newDev)


######################################################################################
	# Indigo Trigger Firing
######################################################################################

####-------------------------------------------------------------------------####
	def triggerEvent(self, eventId):
		if	time.time() < self.currentlyBooting: # no triggering in the first 100+ secs after boot 
			#self.indiLOG.log(10, u"triggerEvent: %s suppressed due to reboot" % eventId)
			return
		for trigId in self.triggerList:
			trigger = indigo.triggers[trigId]
			if trigger.pluginTypeId == eventId:
				indigo.trigger.execute(trigger)
		return


####------================------- sprinkler ------================-----------END


####-------------------------------------------------------------------------####
	def readConfig(self):  ## only once at startup
		try:

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 
#

####-------------------------------------------------------------------------####
	def writeJson(self,data, fName="", fmtOn=False ):
		try:

			if format:
				out = json.dumps(data, sort_keys=True, indent=2)
			else:
				out = json.dumps(data)

			if fName !="":
				f=open(fName,u"w")
				f.write(out)
				f.close()
			return out

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return ""



####-------------------------------------------------------------------------####
	def deviceStartComm(self, dev):
		try:
			#self.indiLOG.log(20,"deviceStartComm called for dev={}, stopcom ignore:{}".format(dev.name, self.deviceStopCommIgnore) )

			if self.pluginState == "init":

				dev.stateListOrDisplayStateIdChanged()	# update  from device.xml info if changed

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####-------------------------------------------------------------------------####
	def deviceDeleted(self, dev):  ### indigo calls this 
		self.deviceStopComm(dev)
		return

####-------------------------------------------------------------------------####
	def deviceStopComm(self, dev):
		#self.indiLOG.log(20,"deviceStopComm called for dev={}, stopcom ignore:{}".format(dev.name, self.deviceStopCommIgnore) )
		try:
			pass
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	#def didDeviceCommPropertyChange(self, origDev, newDev):
	#	 #if origDev.pluginProps['xxx'] != newDev.pluginProps['address']:
	#	 #	  return True
	#	 return False
	###########################		INIT	## END	 ########################




	###########################		DEVICE	#################################
####-------------------------------------------------------------------------####
	def getDeviceConfigUiValues(self, pluginProps, typeId="", devId=0):
	
		return super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)



####-------------------------------------------------------------------------####
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):

		error =""
		errorDict = indigo.Dict()
		valuesDict[u"MSG"] = "OK"
		try:
		pass

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			return ( False, valuesDict, errorDict )

		return ( True, valuesDict )





####-------------------------------------------------------------------------####


# noinspection SpellCheckingInspection
	def actionControlDimmerRelay(self, action, dev0):
		try:
			props0 = dev0.pluginProps
			if dev0.deviceTypeId == "neopixel-dimmer":
				valuesDict={}
			 
				try:
						devNEO		= indigo.devices[int(props0[u"neopixelDevice"])]
						typeId		= devNEO.deviceTypeId
						devId		= devNEO.id
						propsNEO	= devNEO.pluginProps
						devTypeNEO	= propsNEO[u"devType"]
						try: 
							xxx= propsNEO[u"devType"].split(u"x")
							ymax = int(xxx[0])
							xmax = int(xxx[1])
						except Exception, e:
							self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							return
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					return

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "{}".format(action) )
	 
				if not action.configured:
					self.indiLOG.log(20, "actionControlDimmerRelay neopixel-dimmer not enabled:{}".format(unicode(dev0.name)) )
					return
				###action = dev.deviceAction
				if u"pixelMenulist" in props0 and props0[u"pixelMenulist"] != "":
					position = props0[u"pixelMenulist"]
					if position.find(u"*") >-1:
						position='["*","*"]'
				else:
					try:
						position = u"["
						for ii in range(100):
							mmm = "pixelMenu{}".format(ii)
							if	mmm not in props0 or props0[mmm] ==u"":		continue
							if len(props0[mmm].split(u",")) !=2:			continue
							position += u"[{}],".format(props0[mmm])
						position  = position.strip(u",") +u"]"
						position = json.loads(position)
					except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(40,"position data: ".format(position))
						position=[]
				chList =[]


				RGB = [0,0,0,-1]

				channelKeys={u"redLevel":0,"greenLevel":1,"blueLevel":2,"whiteLevel":3}
				if action.deviceAction == indigo.kDeviceAction.TurnOn:
					chList.append({'key':"onOffState", 'value':True})
					RGB=[255,255,255,-1]
				elif action.deviceAction == indigo.kDeviceAction.TurnOff:
					chList.append({'key':"onOffState", 'value':False})
					RGB=[0,0,0,-1]
				elif action.deviceAction == indigo.kDeviceAction.SetBrightness:
					brightness	   = float(action.actionValue)
					brightnessByte = int(round(2.55 * brightness ))	 ### 0..255
					RGB[3]	= brightnessByte
				elif action.deviceAction == indigo.kDeviceAction.SetColorLevels:
					actionColorVals = action.actionValue
					for channel in actionColorVals:
						if channel in channelKeys:
							brightness	   = float(actionColorVals[channel])  ## 0...100
							brightnessByte = int(round(2.55 * brightness ))	 ### 0..255
							if channel in channelKeys:
								RGB[channelKeys[channel]] = brightnessByte


				if RGB[3] !=-1:
					white = int((RGB[3])/(2.55))
					for col in	channelKeys:
						ii = channelKeys[col]
						RGB[ii]=RGB[3]
						chList.append({'key':col, 'value':white})
				else:
					RGB[3] = int(  round( (RGB[0]+RGB[1]+RGB[2])/3. )  )  ## 0..3*2.55=7.65

				for channel in channelKeys:
					if channel in dev0.states:
						chList.append(	{  'key':channel, 'value':int(round(RGB[channelKeys[channel]]/2.55))  }	 )

				if max(RGB) > 55: chList.append({'key':"onOffState", 'value':True})	   ## scale is 0-255
				else:			  chList.append({'key':"onOffState", 'value':False})

				#if "whiteLevel" in chList: del chList[u"whiteLevel"]
				self.execUpdateStatesList(dev0,chList)

				ppp =[]
				if unicode(position).find(u"*") > -1:
					ppp=[u"*","*",RGB[0],RGB[1],RGB[2]]
				else:
					for p in position:
						p[0] = min(	 max((ymax-1),0),int(p[0])	)
						p[1] = min(	 max((xmax-1),0),int(p[1])	)
						ppp.append([p[0],p[1],RGB[0],RGB[1],RGB[2]])
				if u"speedOfChange" in props0 and props0[u"speedOfChange"] !="":
					try:
						valuesDict[u"speedOfChange0"]		  = int(props0[u"speedOfChange"])
					except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "props0 {}".format(props0) )

				valuesDict[u"outputDev"]		 = devId
				valuesDict[u"type0"]			 = "points"
				valuesDict[u"position0"]		 = json.dumps(ppp)
				valuesDict[u"display0"]			 = "immediate"
				valuesDict[u"reset0"]			 = ""
				valuesDict[u"restoreAfterBoot"]	 = True

				if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "valuesDict {}".format(valuesDict) )

				self.setneopixelCALLBACKmenu(valuesDict)

				return


			#####  GPIO		 
			else:
				dev= dev0
			props = dev.pluginProps

			if self.decideMyLog(u"OutputDevice"): self.indiLOG.log(10, "deviceAction \n{}\n props {}".format(action, props))
			valuesDict={}
			valuesDict[u"outputDev"]=dev.id
			valuesDict[u"piServerNumber"] = props[u"piServerNumber"]
			valuesDict[u"deviceDefs"]	  = props[u"deviceDefs"]
			if dev.deviceTypeId ==u"OUTPUTgpio-1-ONoff":
				valuesDict[u"typeId"]	  = "OUTPUTgpio-1-ONoff"
				typeId					  = "OUTPUTgpio-1-ONoff"
			else: 
				valuesDict[u"typeId"]	  = "OUTPUTgpio-1"
				typeId					 = "OUTPUTgpio-1"
			if u"deviceDefs" in props:
				dd = json.loads(props[u"deviceDefs"])
				if len(dd) >0 and "gpio" in dd[0]:
					valuesDict[u"GPIOpin"]	  = dd[0][u"gpio"]
				elif "gpio" in props:
					valuesDict[u"GPIOpin"] = props[u"gpio"]
				else:
					self.indiLOG.log(20, "deviceAction error, gpio not defined action={}\n props {}".format(action.replace(u"\n",""), props) )
			elif "gpio" in props:
				valuesDict[u"GPIOpin"] = props[u"gpio"]
			else:
				self.indiLOG.log(20, "deviceAction error, gpio not defined action={}\n props {}".format(action.replace(u"\n",""), props) )
			   


			###### TURN ON ######
			if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
				valuesDict[u"cmd"] = "up"

			###### TURN OFF ######
			elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
				valuesDict[u"cmd"] = "down"

			###### TOGGLE ######
			elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
				newOnState = not dev.onState
				if newOnState: valuesDict[u"cmd"] = "up"
				else:		   valuesDict[u"cmd"] = "down"

			###### SET BRIGHTNESS ######
			elif action.deviceAction == indigo.kDimmerRelayAction.SetBrightness:
				newBrightness = action.actionValue
				valuesDict[u"cmd"] = "analogWrite"
				valuesDict[u"analogValue"] = unicode(float(newBrightness))


			###### BRIGHTEN BY ######
			elif action.deviceAction == indigo.kDimmerRelayAction.BrightenBy:
				newBrightness = dev.brightness + action.actionValue
				if newBrightness > 100:
					newBrightness = 100
				valuesDict[u"cmd"] = "analogWrite"
				valuesDict[u"analogValue"] = unicode(float(newBrightness))

			###### DIM BY ######
			elif action.deviceAction == indigo.kDimmerRelayAction.DimBy:
				newBrightness = dev.brightness - action.actionValue
				if newBrightness < 0:
					newBrightness = 0
				valuesDict[u"cmd"] = "analogWrite"
				valuesDict[u"analogValue"] = unicode(float(newBrightness))

			else:
				return

			self.setPinCALLBACKmenu(valuesDict, typeId)
			return
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
	def actionControlGeneral(self, action, dev):
		###### STATUS REQUEST ######
		if action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			self.indiLOG.log(20,u"sent \"{}\"  status request".format(dev.name.encode("utf8")) )


####-------------------------------------------------------------------------####

# noinspection SpellCheckingInspection
	def validatePrefsConfigUi(self, valuesDict):


		self.debugLevel			= []
		for d in _debugAreas:
			if valuesDict[u"debug"+d]: self.debugLevel.append(d)
		try:			   
			if self.debugRPI	   != int(valuesDict[u"debugRPI"]):	   self.setALLrPiV(u"ipNumberpToDate", [u"updateParamsFTP"])
			self.debugRPI			= int(valuesDict[u"debugRPI"])
		except: pass

		self.setLogfile(valuesDict[u"logFileActive2"])
	 
		self.enableBroadCastEvents					= valuesDict[u"enableBroadCastEvents"]

		try: 
			xx = valuesDict["SQLLoggingEnable"].split("-")
			yy = {"devices":xx[0]=="on", "variables":xx[1]=="on"}
			if yy != self.SQLLoggingEnable:
				self.SQLLoggingEnable = yy
				self.actionList["setSqlLoggerIgnoreStatesAndVariables"] = True
		except Exception, e:
			self.indiLOG.log(30,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.SQLLoggingEnable = {"devices":True, "variables":True}


		try: self.speedUnits			= int(valuesDict[u"speedUnits"])
		except: self.speedUnits			= 1.
		try: self.distanceUnits			= int(valuesDict[u"distanceUnits"])
		except: self.distanceUnits		= 1.

		self.pressureUnits				= valuesDict[u"pressureUnits"]	# 1 for Pascal
		self.tempUnits					= int(valuesDict[u"tempUnits"])	# Celsius, Fahrenheit, Kelvin
		self.tempDigits					= int(valuesDict[u"tempDigits"])  # 0/1/2

		self.IndigoServerIPNumber 		= valuesDict[u"IndigoServerIPNumber"]
		self.portOfIndigoServer 		= valuesDict[u"portOfServer"]
		self.userIDOfShellyDevices 		= valuesDict[u"userIDOfShellyDevices"]
		self.passwordOfShellyDevices 	= valuesDict[u"passwordOfShellyDevices"]
		self.userIDOfShellyDevices 		= valuesDict[u"userIDOfShellyDevices"]

		return True, valuesDict

	###########################	   MAIN LOOP  ############################
####-------------------------------------------------------------------------####
	def initConcurrentThread(self):

		now = datetime.datetime.now()
		self.messagesQueue	  = Queue.Queue()
		self.queueActive	  = False
		self.quitNow		  = u""

		self.startTime		  = time.time()
		self.stackReady		  = False
		self.socketServer	  = None


		for ii in range(2):
			if self.pluginPrefs.get(u"IndigoServerIPNumber","") == "none": break
			if self.userIdOfServer !="" and self.passwordOfServer !="": break
			self.indiLOG.log(30, u"indigo server userid or password not configured in config and security level is set to digest or basic")
			self.sleep(10)



		self.writeJson(self.pluginVersion, fName=self.indigoPreferencesPluginDir + "currentVersion")


		if self.indigoInputPORT > 0 and self.IndigoOrSocket == u"socket":
			self.socketServer, self.stackReady	= self.startTcpipListening(self.myIpNumber, self.indigoInputPORT)
		else:
			self.stackReady			= True

		self.lastMinuteChecked	= now.minute
		self.lastHourChecked	= now.hour
		self.lastDayChecked		= [-1 for ii in range(len(self.checkBatteryLevelHours)+2)]
		self.lastSecChecked		= 0
		self.countLoop			= 0


		if self.currentVersion != self.pluginVersion :
			pass
		else:
			pass
		self.lastUpdateSend = time.time()  # used to send updates to all rPis if not done anyway every day
		self.pluginState	= "run"
		self.setCurrentlyBooting(50, setBy="initConcurrentThread")

		return 



	###########################	   cProfile stuff   ############################ START
	####-----------------  ---------
	def getcProfileVariable(self):

		try:
			if self.timeTrVarName in indigo.variables:
				xx = (indigo.variables[self.timeTrVarName].value).strip().lower().split("-")
				if len(xx) ==1: 
					cmd = xx[0]
					pri = ""
				elif len(xx) == 2:
					cmd = xx[0]
					pri = xx[1]
				else:
					cmd = "off"
					pri  = ""
				self.timeTrackWaitTime = 20
				return cmd, pri
		except Exception, e:
			pass

		self.timeTrackWaitTime = 60
		return "off",""

	####-----------------            ---------
	def printcProfileStats(self,pri=""):
		try:
			if pri !="": pick = pri
			else:		 pick = 'cumtime'
			outFile		= self.indigoPreferencesPluginDir+"timeStats"
			indigo.server.log(" print time track stats to: "+outFile+".dump / txt  with option: "+pick)
			self.pr.dump_stats(outFile+".dump")
			sys.stdout 	= open(outFile+".txt", "w")
			stats 		= pstats.Stats(outFile+".dump")
			stats.strip_dirs()
			stats.sort_stats(pick)
			stats.print_stats()
			sys.stdout = sys.__stdout__
		except: pass
		"""
		'calls'			call count
		'cumtime'		cumulative time
		'file'			file name
		'filename'		file name
		'module'		file name
		'pcalls'		primitive call count
		'line'			line number
		'name'			function name
		'nfl'			name/file/line
		'stdname'		standard name
		'time'			internal time
		"""

	####-----------------            ---------
	def checkcProfile(self):
		try: 
			if time.time() - self.lastTimegetcProfileVariable < self.timeTrackWaitTime: 
				return 
		except: 
			self.cProfileVariableLoaded = 0
			self.do_cProfile  			= "x"
			self.timeTrVarName 			= "enableTimeTracking_"+self.pluginShortName
			indigo.server.log("testing if variable "+self.timeTrVarName+" is == on/off/print-option to enable/end/print time tracking of all functions and methods (option:'',calls,cumtime,pcalls,time)")

		self.lastTimegetcProfileVariable = time.time()

		cmd, pri = self.getcProfileVariable()
		if self.do_cProfile != cmd:
			if cmd == "on": 
				if  self.cProfileVariableLoaded ==0:
					indigo.server.log("======>>>>   loading cProfile & pstats libs for time tracking;  starting w cProfile ")
					self.pr = cProfile.Profile()
					self.pr.enable()
					self.cProfileVariableLoaded = 2
				elif  self.cProfileVariableLoaded >1:
					self.quitNow = " restart due to change  ON  requested for print cProfile timers"
			elif cmd == "off" and self.cProfileVariableLoaded >0:
					self.pr.disable()
					self.quitNow = " restart due to  OFF  request for print cProfile timers "
		if cmd == "print"  and self.cProfileVariableLoaded >0:
				self.pr.disable()
				self.printcProfileStats(pri=pri)
				self.pr.enable()
				indigo.variable.updateValue(self.timeTrVarName,"done")

		self.do_cProfile = cmd
		return 

	####-----------------            ---------
	def checkcProfileEND(self):
		if self.do_cProfile in["on","print"] and self.cProfileVariableLoaded >0:
			self.printcProfileStats(pri="")
		return
	###########################	   cProfile stuff   ############################ END



####-----------------   main loop          ---------
	def runConcurrentThread(self):

		self.dorunConcurrentThread()
		self.checkcProfileEND()
		self.sleep(1)
		if self.quitNow !="":
			indigo.server.log( u"runConcurrentThread stopping plugin due to:  ::::: " + self.quitNow + " :::::")
			serverPlugin = indigo.server.getPlugin(self.pluginId)
			serverPlugin.restart(waitUntilDone=False)


		self.indiLOG.log(20, u"killing 2")
		subprocess.call("/bin/kill -9 "+unicode(self.myPID), shell=True )

		return



####-----------------   main loop          ---------
	def dorunConcurrentThread(self): 

		self.initConcurrentThread()


		if self.logFileActive !="standard":
			indigo.server.log(u" ..  initialized")
			self.indiLOG.log(10, u" ..  initialized, starting loop" )
		else:	 
			indigo.server.log(u" ..  initialized, starting loop ")
		theHourToCheckversion = 12

		########   ------- here the loop starts	   --------------
		try:
			while self.quitNow == "":
				self.countLoop += 1
				self.sleep(9.)

				if self.countLoop > 2: 
					anyChange = self.periodCheck()
					if len(self.sendBroadCastEventsList) >0: self.sendBroadCastNOW()

		except self.StopThread:
			indigo.server.log( u"stop requested from indigo ")
		## stop and processing of messages received 
		if self.quitNow !="": indigo.server.log( "quitNow: "+self.quitNow +"--- you might see an indigo error message, can be ignored ")
		else: indigo.server.log( "quitNow:  empty")

		self.stackReady	 = False 
		self.pluginState = "stop"



		self.stopUpdateshellyQueues()
		self.sleep(0.1)
		self.stopUpdateshellyQueues()

		if self.socketServer is not None:  
			lsofCMD	 =u"/usr/sbin/lsof -i tcp:"+unicode(self.indigoInputPORT)
			ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			if len(ret[0]) > 10: indigo.server.log(u".. stopping tcpip stack")
			self.socketServer.shutdown()
			self.socketServer.server_close()



		return

	####----------------- if FINGSCAN is enabled send update signal	 ---------
	def sendBroadCastNOW(self):
		try:
			x = False
			if	self.enableBroadCastEvents =="0":
				self.sendBroadCastEventsList = []
				return x
			if self.sendBroadCastEventsList == []:
				return x
			if self.countLoop < 10:
				self.sendBroadCastEventsList = [] 
				return x  ## only after stable ops for 10 loops ~ 20 secs

			msg = copy.copy(self.sendBroadCastEventsList)
			self.sendBroadCastEventsList = []
			if len(msg) >0:
				msg ={"pluginId":self.pluginId,"data":msg}
				try:
					if self.decideMyLog(u"BC"): self.myLog( text=u"updating BC with " + unicode(msg),mType=u"BroadCast" )
					indigo.server.broadcastToSubscribers(u"deviceStatusChanged", json.dumps(msg))
				except Exception, e:
					if len(unicode(e)) > 5:
						self.indiLOG.log(40, u"updating sendBroadCastNOW has error Line {} has error={};    fingscan update failed".format(sys.exc_traceback.tb_lineno, e))

		except Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(40,u"updating sendBroadCastNOW has error Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			else:
				x = True
		return x

####-------------------------------------------------------------------------####
	def periodCheck(self):
		anyChange= False
		try:
			tt = time.time()
			return 
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		return anyChange


####-------------------------------------------------------------------------####
	def performActionList(self):
		try:
			#if self.actionList["setTime"] != []: 
			ASS	
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		#self.actionList["setTime"] = []
		return


####-------------------------------------------------------------------------####
	def checkDay(self,now):
		return 


####----------------------reset sensor min max at midnight -----------------------------------####
	def resetMinMaxSensors(self, init=False):
		try:
			nHour = (datetime.datetime.now()).hour 
			for dev in indigo.devices.iter(self.pluginId):
				if	dev.enabled: 
					for ttx in _GlobalConst_fillMinMaxStates:
						if ttx in dev.states and ttx+u"MaxToday" in dev.states:
							try:	val = float(dev.states[ttx])
							except: val = 0
							try:
								xxx = unicode(dev.states[ttx]).split(".")
								if len(xxx) ==1:
									decimalPlaces = 1
								else:
									decimalPlaces = len(xxx[1])
							except:
								decimalPlaces = 2

							if init: # at start of pgm
								reset = False
								try: 
									int(dev.states[ttx+u"MinYesterday"])
								except:
									reset = True
								if not reset: 
									try:
										if	(float(dev.states[ttx+u"MaxToday"]) == float(dev.states[ttx+u"MinToday"]) and float(dev.states[ttx+u"MaxToday"]) == 0.) :	 reset = True
									except: pass
								if reset:
									self.addToStatesUpdateDict(dev.id,ttx+u"MaxYesterday", val,decimalPlaces=decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MinYesterday", val,decimalPlaces=decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MaxToday",		val,decimalPlaces=decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MinToday",		val,decimalPlaces=decimalPlaces)

							elif nHour ==0:	 # update at midnight 
									self.addToStatesUpdateDict(dev.id,ttx+u"MaxYesterday", dev.states[ttx+u"MaxToday"], decimalPlaces = decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MinYesterday", dev.states[ttx+u"MinToday"], decimalPlaces = decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MaxToday",		dev.states[ttx], decimalPlaces = decimalPlaces)
									self.addToStatesUpdateDict(dev.id,ttx+u"MinToday",		dev.states[ttx], decimalPlaces = decimalPlaces)
							self.executeUpdateStatesDict(onlyDevID=dev.id,calledFrom="resetMinMaxSensors")
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

####----------------------reset sensor min max at midnight -----------------------------------####
	def fillMinMaxSensors(self,dev,stateName,value,decimalPlaces):
		try:
			if value == "": return 
			if stateName not in _GlobalConst_fillMinMaxStates: return 
			if stateName in dev.states and stateName+u"MaxToday" in dev.states:
				val = float(value)
				if val > float(dev.states[stateName+u"MaxToday"]):
					self.addToStatesUpdateDict(dev.id,stateName+u"MaxToday",	 val, decimalPlaces=decimalPlaces)
				if val < float(dev.states[stateName+u"MinToday"]):
					self.addToStatesUpdateDict(dev.id,stateName+u"MinToday",	 val, decimalPlaces=decimalPlaces)
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

#


####-------------------------------------------------------------------------####
	def addToDataQueue(self, data):	#
		try:
			if not self.stackReady : return 


			## add to message queue
			beaconUpdatedIds =[]
			self.messagesQueue.put((time.time(),data))
			if not self.queueActive: 
				beaconUpdatedIds += self.workOnQueue()



		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,varNameIN+     + varUnicode[0:30])


####-------------------------------------------------------------------------####
	def workOnQueue(self):

		self.queueActive  = True
		while not self.messagesQueue.empty():
			item = self.messagesQueue.get() 
			for ii in range(40):
				if self.queueList ==u"update" : break
				if self.queueList ==u""		  : break
				if ii > 0:	pass
				time.sleep(0.05)
			self.queueList = "update"  
			beaconUpdatedIds += self.execUpdate(item[0],item[1])
			#### indigo.server.log(unicode(item[1])+"  "+ unicode(beaconUpdatedIds)+" "+ item[3])
		self.messagesQueue.task_done()
		self.queueActive  = False
		self.queueList = ""	 
		if len(self.sendBroadCastEventsList): self.sendBroadCastNOW()
		return 
 
####-------------------------------------------------------------------------####
	def execUpdate(self, timeStampOfReceive, data):

		try:

		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,"{}".format(data) )
		return 

####-------------------------------------------------------------------------####
	def getTimetimeFromDateString(self, dateString, fmrt=_defaultDateStampFormat): 
		if len(dateString) > 9:
			try:
				return  time.mktime(  datetime.datetime.strptime(dateString, fmrt).timetuple()  )
			except:
				return 0		
		else:
			return 0




####-------------------------------------------------------------------------####
	def getNumber(self,val):
		# test if a val contains a valid number, if not return ""
		# return the number if any meaningful number (with letters before and after return that number)
		# u"a-123.5e" returns -123.5
		# -1.3e5 returns -130000.0
		# -1.3e-5 returns -0.000013
		# u"1.3e-5" returns -0.000013
		# u"1.3e-5x" returns "" ( - sign not first position	 ..need to include)
		# True, u"truE" u"on" "ON".. returns 1.0;  False u"faLse" u"off" returns 0.0
		# u"1 2 3" returns ""
		# u"1.2.3" returns ""
		# u"12-5" returns ""
		try:
			return float(val)
		except:
			if val == ""														: return "x"
			try:
				ttt = unicode(val).upper()															# if unicode return ""	 (-->except:)
				if ttt== "TRUE"  or ttt ==u"ON"  or ttt == "T" or ttt==u"UP"						: return 1.0	 # true/on	 --> 1
				if ttt== "FALSE" or ttt == "OFF" or ttt == "F" or ttt==u"DOWN" or ttt==  "EXPIRED"	: return 0.0		# false/off --> 0
			except:
				pass
			try:
				xx = ''.join([c for c in val if c in  '-1234567890.'])								# remove non numbers
				lenXX= len(xx)
				if	lenXX > 0:																		# found numbers..if len( ''.join([c for cin xx if c in	'.']) )			  >1	: return "x"		# remove strings that have 2 or more dots " 5.5 6.6"
					if len(''.join([c for c in	xx if c in '-']) )			 >1 : return "x"		# remove strings that have 2 or more -	  u" 5-5 6-6"
					if len( ''.join([c for c  in xx if c in '1234567890']) ) ==0: return "x"		# remove strings that just no numbers, just . amd - eg "abc.xyz- hij"
					if lenXX ==1												: return float(xx)	# just one number
					if xx.find(u"-") > 0										: return "x"		 # reject if "-" is not in first position
					valList =  list(val)															# make it a list
					count =	 0																		# count number of numbers
					for i in range(len(val)-1):														# reject -0 1 2.3 4  not consecutive numbers:..
						if (len(''.join([c for c in valList[i ] if c in	 '-1234567890.'])) ==1 ):  # check if this character is a number, if yes:
							count +=1																#
							if count >= lenXX									: break		 # end of # of numbers, end of test: break, its a number
							if (len(''.join([c for c in valList[i+1] if c in '-1234567890.'])) )== 0:  return "x"  # next is not a number and not all numbers accounted for, so it is numberXnumber
					return														 float(xx)	# must be a real number, everything else is excluded
			except:
				return "x"																			# something failed eg unicode only ==> return ""
		return "x"																					# should not happen just for safety

####-------------------------------------------------------------------------####
	def convTemp(self, temp):
		try:
			useFormat="{:.1f}"
			temp = float(temp)
			if temp == 999.9:
				return 999.9,"badSensor", 1
			if self.tempUnits == u"Fahrenheit":
				temp = temp * 9. / 5. + 32.
				suff = u"ºF"
			elif self.tempUnits == u"Kelvin":
				temp += 273.15
				suff = u"ºK"
			else:
				suff = u"ºC"
			if self.tempDigits == 0:
				cString = "%d"
				useFormat ="{:d}"
			else:
				cString = "%."+unicode(self.tempDigits)+"f"
			tempU = (cString % temp).strip()
			return round(temp,self.tempDigits) , tempU + suff,self.tempDigits, useFormat
		except:pass
		return -99, u"",self.tempDigits, useFormat



####-------------------------------------------------------------------------####
	def convHum(self, hum):
		try:
			humU = (u"%3d" %float(hum)).strip()
			return int(float(hum)), humU + u"%",0
		except:
			return -99, u"",0


####-------------------------------------------------------------------------####
	def getDeviceDisplayStateId(self, dev):
		props = dev.pluginProps
		if u"displayState" in props:
			return props[u"displayState"]
		elif u"displayStatus" in dev.states:
			return	u"displayStatus"
		else:
			return "status"




####------------------rpi update queue management ----------------------------START
####------------------rpi update queue management ----------------------------START
####------------------rpi update queue management ----------------------------START

####-------------------------------------------------------------------------####
	def startUpdateshellyQueues(self, state, piSelect="all"):
		if state =="start":
			self.laststartUpdateshellyQueues = time.time()
			self.indiLOG.log(10, u"starting UpdateshellyQueues ")
			for ipNumber in self.RPI:
				if self.RPI[ipNumber][u"piOnOff"] != "1": continue
				if piSelect == "all" or ipNumber == piSelect:
						self.startOneUpdateRPIqueue(ipNumber)

		elif state =="restart":
			if (piSelect == "all" and time.time() - self.laststartUpdateshellyQueues > 70) or piSelect != "all":
				self.laststartUpdateshellyQueues = time.time()
				for ipNumber in self.RPI:
					if self.RPI[ipNumber][u"piOnOff"] != "1": continue
					if piSelect == "all" or ipNumber == piSelect:
						if time.time() - self.shellyQueues["lastCheck"][ipNumber] > 100:
							self.stopUpdateshellyQueues(piSelect=ipNumber)
							time.sleep(0.5)
						if  time.time() - self.shellyQueues["lastCheck"][ipNumber] > 100:
							self.startOneUpdateRPIqueue(ipNumber, reason="active messages pending timeout")
						elif self.shellyQueues["state"][ipNumber] != "running":
							self.startOneUpdateRPIqueue(ipNumber, reason="not running")
		return 

####-------------------------------------------------------------------------####
	def startOneUpdateRPIqueue(self, ipnumber, reason=""):

		if ipnumber in self.shellyQueues["state"]:
			if self.shellyQueues["state"][ipnumber] == "running":
				self.indiLOG.log(20, u"no need to start Thread, ipnumber {} thread already running".format(ipnumber) )
				return 

		self.indiLOG.log(20, u" .. restarting   thread for ipnumber, state was : {} - {}".format(ipnumber, self.shellyQueues["state"][ipNumber], reason) )
		self.shellyQueues["lastCheck"][ipnumber] = time.time()
		self.shellyQueues["state"][ipnumber]	= "start"
		self.sleep(0.1)
		self.shellyQueues["thread"][ipnumber]  = threading.Thread(name=u'self.updateThread', target=self.updateThread, args=(ipnumber,))
		self.shellyQueues["thread"][ipnumberv].start()
		return 
###-------------------------------------------------------------------------####
	def stopUpdateshellyQueues(self, piSelect="all"):
		self.shellyQueues["reset"]		= {}
		for ipnumber in self.IPNUMBERS:
			if ipNumber == piSelect or piSelect == "all":
				self.stopOneUpdateshellyQueues(ipnumber, reason="")
		return 
###-------------------------------------------------------------------------####
	def stopOneUpdateshellyQueues(self, ipnumber, reason=""):
		self.shellyQueues["state"][ipnumber]	= "stop "+reason
		self.shellyQueues["reset"][ipnumber]	= True
		return 


####-------------------------------------------------------------------------####
	def sendFilesToPiFTP(self, ipnumber, action,endAction="repeatUntilFinished"):
		if time.time() - self.shellyQueues["lastCheck"][ipnumber] > 100 or self.shellyQueues["state"][ipnumber] != "running":
			self.startUpdateshellyQueues("restart", piSelect=ipnumber)
		next = {"ipnumber":ipnumber, "action":action, "endAction":endAction, "tries":0, "exeTime":time.time()}
		if self.testIfAlreadyInQ(next,action): 	return 
		if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(10, u"adding to update list {}".format(next) )
		self.shellyQueues["data"][action].put(next)
		return
####-------------------------------------------------------------------------####
	def resetUpdateQueue(self, ipnumber):
		self.shellyQueues["reset"][ipnumber] = True
		return
####-------------------------------------------------------------------------####
	def testIfAlreadyInQ(self, next, ipnumber):
		currentQueue = list(self.shellyQueues["data"][ipnumber].queue)
		for q in currentQueue:
			if q["ipnumber"] == next["ipnumber"] and q["action"] == next["action"]:
				if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(10, u"NOT adding to update list already presend {}".format(next) )
				return True
		return False

####-------------------------------------------------------------------------####
	def ripNumberpdateThread(self,ipnumber):
		try:
			self.shellyQueues["state"][ipnumber] = "running"
			if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"ripNumberpdateThread starting  for ipnumber# {}".format(ipnumber) )
			while self.shellyQueues["state"][ipnumber] == "running":
				self.shellyQueues["lastCheck"][ipnumber]  = time.time()
				time.sleep(1)
				addBack =[]
				while not self.shellyQueues["data"][ipNumber].empty():
					self.shellyQueues["lastActive"][ipNumber]  = time.time()
					next = self.shellyQueues["data"][ipNumber].get()
					self.shellyQueues["lastData"][ipNumber] = unicode(next)
					##if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"reset on/off  update queue for pi#{} .. {}".format(ipNumber, self.shellyQueues["reset"][ipNumber]) )

					if self.RPI[ipNumber][u"piOnOff"] == "0": 		
						if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"ripNumberpdateThread skipping;  Pi#: {} is OFF".format(ipNumber) )
						self.shellyQueues["reset"][ipNumber] = True
						break
					if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"ripNumberpdateThread executing  {}".format(next) )
					if ipNumber != unicode(next["pi"]): 			
						if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"ripNumberpdateThread skipping; pi numbers wrong  {} vs {} ".format(ipNumber, next["pi"]) )
						continue
					if self.RPI[ipNumber][u"piOnOff"] == "0": 		
						if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"ripNumberpdateThread skipping;  Pi#: {} is OFF".format(ipNumber) )
						continue
					if self.RPI[ipNumber][u"ipNumberPi"] == "": 	
						if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"ripNumberpdateThread skipping pi#:{}  ip number blank".format(ipNumber)  )
						continue
					if ipNumber in self.shellyQueues["reset"] and self.shellyQueues["reset"][ipNumber]: 
						if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"ripNumberpdateThread resetting queue data for pi#:{}".format(ipNumber) )
						continue
					try:
						if  not isvalidIpnumber(self.IPNUMBERS][u"ipNumber"])
							self.shellyQueues["reset"][ipNumber] = True
							if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"device {} not enabled, no sending to RPI".format(ipNumber) )
							continue
					except Exception, e:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						self.indiLOG.log(20,"setting update queue for ipNumber{} to empty".format(ipNumber))
						self.shellyQueues["reset"][ipNumber] = True

					# time for sending?
					if next["exeTime"] > time.time():
						addBack.append((next)) # no , wait 
						continue
					self.RPIBusy[ipNumber] = time.time()

					if next["type"] =="ftp":
						retCode, text = self.execSendFilesToPiFTP(ipNumber, fileToSend=next["fileToSend"], endAction= next["endAction"])
					else:
						retCode, text = self.execSshToRPI(ipNumber, fileToSend=next["fileToSend"], endAction= next["endAction"])

					if retCode ==0: # all ok?
						self.RPI[ipNumber][u"lastMessage"] = time.time()
						continue

					else: # some issues
						next["tries"] +=1
						next["exeTime"]  = time.time()+5

						if 5 < next["tries"] and next["tries"] < 10: # wait a little longer
							if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"last updates were not successful wait, then try again")
							next["exeTime"] = time.time()+10

						elif next["tries"] > 9:  # wait a BIT longer before trying again
							if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"rPi update delayed due to failed updates rPI# {}".format(ipNumber) )
							next["exeTime"]  = time.time()+20
							next["tries"] = 0

						addBack.append(next)
				try: 	self.shellyQueues["data"][ipNumber].task_done()
				except: pass
				if addBack !=[]:
					for nxt in addBack:
						self.shellyQueues["data"][ipNumber].put(nxt)
				self.shellyQueues["reset"][ipNumber] =False
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.indiLOG.log(20, u"rpi: {}  update thread stopped, state was:{}".format(ipNumber,self.shellyQueues["state"][ipNumber] ) )
		self.shellyQueues["state"][ipNumber] = "stopped - exiting thread"
		return



####-------------------------------------------------------------------------####
	def execShellySend(self,  ipNumber, action, endAction="repeatUntilFinished"):
		ret =["",""]
		try:
			if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"enter  execShellySend  action:".format(action) )
			self.lastUpdateSend = time.time()


			pingR = self.testPing(ipNumber)
			if pingR != 0:
				if self.decideMyLog(u"SendToShelly") : self.indiLOG.log(20,u" ipnumber{}  does not answer ping - , skipping update".format(ipNumber) )
				return 1, ["ping offline",""]

			cmd0 = "/usr/bin/expect '" + self.pathToPlugin + fileToSend + u"'" + u" "

			if self.decideMyLog(u"SendToShelly"): self.indiLOG.log(20, u"sending to {} \n{}".format(ipNumber, cmd0) )
			p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			ret = p.communicate()

			if len(ret[1]) > 0:
				self.indiLOG.log(20, u"return code from fix " + unicode(ret))

			return 0, ret
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return 1, ret





####------------------rpi update queue management ----------------------------END
####------------------rpi update queue management ----------------------------END
####------------------rpi update queue management ----------------------------END

####-------------------------------------------------------------------------####
	def testPing(self, ipN):
		try:
			ss = time.time()
			ret = subprocess.call(u"/sbin/ping  -c 1 -W 40 -o " + ipN, shell=True) # send max 2 packets, wait 40 msec   if one gets back stop
			if self.decideMyLog(u"Ping"): self.indiLOG.log(10, u" sbin/ping  -c 1 -W 40 -o {} return-code: {}".format(ipN, ret) )

			#indigo.server.log(  ipN+"-1  "+ unicode(ret) +"  "+ unicode(time.time() - ss)  )

			if int(ret) ==0:  return 0
			self.sleep(0.1)
			ret = subprocess.call(u"/sbin/ping  -c 1 -W 400 -o " + ipN, shell=True)
			if self.decideMyLog(u"Ping"): self.indiLOG.log(10, "/sbin/ping  -c 1 -W 400 -o {} ret-code: ".format(ipN, ret) )

			#indigo.server.log(  ipN+"-2  "+ unicode(ret) +"  "+ unicode(time.time() - ss)  )

			if int(ret) ==0:  return 0
			return 1
		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		#indigo.server.log(  ipN+"-3  "+ unicode(ret) +"  "+ unicode(time.time() - ss)  )
		return 1





	####-----------------
	########################################
	# General Action callback
	######################
	def actionControlUniversal(self, action, dev):
		###### BEEP ######
		if action.deviceAction == indigo.kUniversalAction.Beep:
			# Beep the hardware module (dev) here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"{}\" beep request not implemented".format(dev.name))

		###### STATUS REQUEST ######
		elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
			# Query hardware module (dev) for its current status here:
			# ** IMPLEMENT ME **
			self.indiLOG.log(20,u"sent \"{}\" status request not implemented".format(dev.name))

	########################################
	# Sensor Action callback
	######################
	def actionControlSensor(self, action, dev):
		###### TURN ON ######
		if action.sensorAction == indigo.kSensorAction.TurnOn:
			self.addToStatesUpdateDict(dev.id,u"status", u"up")

		###### TURN OFF ######
		elif action.sensorAction == indigo.kSensorAction.TurnOff:
			self.addToStatesUpdateDict(dev.id,u"status", u"down")

		###### TOGGLE ######
		elif action.sensorAction == indigo.kSensorAction.Toggle:
			if dev.onState: 
				self.addToStatesUpdateDict(dev.id,u"status", "down")
				dev.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
			else:
				self.addToStatesUpdateDict(dev.id,u"status", "up")

		self.executeUpdateStatesDict()

##############################################################################################

	####-----------------	 ---------
	def getJsonFromDevices(self, ipNumber, jsonAction=""):

		try:
			if not self.isValidIP(ipNumber): return {}


			if self.useCurlOrPymethod.find("curl") > -1:
				if len(self.userIDOfShellyDevices) >0:
					uid= " "+self.userIDOfShellyDevices+":"+self.passwordOfShellyDevices+"@"
				else: UID =""
				cmdR  = self.unfiCurl+UID" '//"+ipNumber+":"+self.shellyPort+""/status

				if self.decideMyLog(u"HTTP"): self.indiLOG.log(20,"Connection: "+cmdR )
				try:
					ret = subprocess.Popen(cmdR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
					try:
						jj = json.loads(ret[0])
					except :
						self.indiLOG.log(40,"Shelly repose from {}  no json object returned: {}".format(ipNumberret[0], ret[0]))
						return {}

					if len(ret[1]) >5:
						self.indiLOG.log(40,u" {} Connection error: >>{}<< ..\n>>{}<<".format(ret[0],ret[1]ipNumber))
						return {}

					if  jsonAction=="print":
						self.indiLOG.log(20,u" Connection  info\n{}".format(json.dumps(jj),sort_keys=True, indent=2)) )

					return jj

					return{}}
				except	Exception, e:
					self.indiLOG.log(40,"Connection: in Line {} has error={}   Connection".format(sys.exc_traceback.tb_lineno, e) )


			############# does not work on OSX	el capitan ssl lib too old	##########
			elif self.useCurlOrPymethod =="requests":

				if data =={}: dataDict = ""
				else:		  dataDict = json.dumps(data)
				url = "http://"+ipNumber+":"+self.shellyPort"/status"

				try:
						if len(self.userIDOfShellyDevices) >0:
							resp = requests.get(url,auth=(self.userIDOfShellyDevices, self.passwordOfShellyDevices))
						else:
							resp = requests.get(url)
  
						try:
							jj = resp.json()
						except :
							self.indiLOG.log(40,"CShelly repose from {}  no json object returned:".format(ipNumber,resp)
							return {}
 
						if  jsonAction =="print":
							self.indiLOG.log(20,u" Connection  info\n{}".format(json.dumps(jj),sort_keys=True, indent=2)) )

						return jj

				except	Exception, e:
					self.indiLOG.log(40,"in Line {} has error={}   Connection".format(sys.exc_traceback.tb_lineno, e) )


		except	Exception, e:
			self.indiLOG.log(40,"in Line {} has error={}   Connection".format(sys.exc_traceback.tb_lineno, e))
		return {}



####-------------------------------------------------------------------------####


	def addToStatesUpdateDict(self,devId,key,value,newStates="",decimalPlaces="",uiValue="", force=False):
		devId=unicode(devId)
		try:
			try:

				for ii in range(5):
					if	self.executeUpdateStatesDictActive =="":
						break
					self.sleep(0.05)
				self.executeUpdateStatesDictActive = devId+"-add"


				if devId not in self.updateStatesDict: 
					self.updateStatesDict[devId]={}
				if key in self.updateStatesDict[devId]:
					if value != self.updateStatesDict[devId][key]["value"]:
						self.updateStatesDict[devId][key] = {}
						if newStates !="":
							newStates[key] = {}
				self.updateStatesDict[devId][key] = {"value":value,"decimalPlaces":decimalPlaces,"force":force,"uiValue":uiValue}
				if newStates !="": newStates[key] = value

			except Exception, e:
				if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return newStates
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)   )

			#self.updateStatesDict = local	  
		except Exception, e:
			if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return newStates
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.executeUpdateStatesDictActive = ""
		return newStates

####-------------------------------------------------------------------------####
	def executeUpdateStatesDict(self,onlyDevID="0",calledFrom=""):
		try:
			if len(self.updateStatesDict) ==0: return
			#if "1929700622" in self.updateStatesDict: self.indiLOG.log(10, u"executeUpdateStatesList calledfrom: "+calledFrom +"; onlyDevID: " +onlyDevID +"; updateStatesList: " +unicode(self.updateStatesDict))
			onlyDevID = unicode(onlyDevID)

			for ii in range(5):
				if	self.executeUpdateStatesDictActive =="":
					break
				self.sleep(0.05)

			self.executeUpdateStatesDictActive = onlyDevID+"-exe"


			local ={}
			#		 
			if onlyDevID == "0":
				for ii in range(5):
					try: 
						local = copy.deepcopy(self.updateStatesDict)
						break
					except Exception, e:
						self.sleep(0.05)
				self.updateStatesDict={} 

			elif onlyDevID in self.updateStatesDict:
				for ii in range(5):
					try: 
						local = {onlyDevID: copy.deepcopy(self.updateStatesDict[onlyDevID])}
						break
					except Exception, e:
						self.sleep(0.05)

				try: 
					del self.updateStatesDict[onlyDevID]
				except Exception, e:
					pass
			else:
				self.executeUpdateStatesDictActive = ""
				return 
			self.executeUpdateStatesDictActive = ""

			self.lastexecuteUpdateStatesDictCalledFrom = (calledFrom,onlyDevID)

			changedOnly = {}
			trigStatus	   = ""
			trigRPIchanged = ""
			devnamechangedStat=""
			#devnamechangedRPI =""
			dateString = datetime.datetime.now().strftime(_defaultDateStampFormat)
			for devId in local:
				if onlyDevID !="0" and onlyDevID != devId: continue
				if len(local) > 0:
					dev =indigo.devices[int(devId)]
					nKeys =0
					for key in local[devId]:
						value = local[devId][key]["value"]
						if key not in dev.states and key != "lastSensorChange":
							self.indiLOG.log(20, u"executeUpdateStatesDict: key: {}  not in states for dev:{}".format(key, dev.name) )
						elif key in dev.states:
							upd = False
							if local[devId][key]["decimalPlaces"] != "": # decimal places present?
								try: 
									if round(value,local[devId][key]["decimalPlaces"]) !=	 round(dev.states[key],local[devId][key]["decimalPlaces"]):
										upd=True
								except: 
										upd=True
							else: 
								if unicode(value) != unicode(dev.states[key]):
										upd=True
							if local[devId][key]["force"]: 
										upd=True
							if upd:
								nKeys +=1
								if devId not in changedOnly: changedOnly[devId]={}
								changedOnly[devId][key] = {"value":local[devId][key]["value"], "decimalPlaces":local[devId][key]["decimalPlaces"], "uiValue":local[devId][key]["uiValue"]}
								if "lastSensorChange" in dev.states and "lastSensorChange" not in changedOnly[devId]:
									nKeys +=1
									changedOnly[devId]["lastSensorChange"] = {"value":dateString,"decimalPlaces":"","uiValue":""}

					##if dev.name =="b-radius_3": self.indiLOG.log(10,	u"changedOnly "+unicode(changedOnly))
					if devId in changedOnly and len(changedOnly[devId]) >0:
						chList=[]
						for key in changedOnly[devId]:
							if key ==u"status":	 
								self.statusChanged = max(1,self.statusChanged)
								value =changedOnly[devId][key]["value"]
								if u"lastStatusChange" in dev.states and u"lastStatusChange" not in changedOnly[devId]:
									try:
										st	= unicode(value).lower() 
										if st in ["up","down","expired","on",u"off",u"1","0"]:
											props =dev.pluginProps
											if	self.enableBroadCastEvents == "all" or	("enableBroadCastEvents" in props and props[u"enableBroadCastEvents"] == "1" ):
												msg = {"action":"event", "id":unicode(dev.id), "name":dev.name, "state":"status", "valueForON":"up", "newValue":st}
												if self.decideMyLog(u"BC"): self.indiLOG.log(10, u"executeUpdateStatesDict msg added :" + unicode(msg))
												self.sendBroadCastEventsList.append(msg)
											if dateString != dev.states[u"lastStatusChange"]:
												chList.append({u"key": u"lastStatusChange", u"value":dateString})
									except: pass

								if dev.deviceTypeId ==u"beacon" or dev.deviceTypeId.find(u"rPI") > -1 or dev.deviceTypeId == u"BLEconnect": 
									chList.append({u"key":"displayStatus","value":self.padDisplay(value)+dateString[5:] })
									if	 value == u"up":
										chList.append({u"key":"onOffState","value":True, "uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
									elif value == u"down":
										chList.append({u"key":"onOffState","value":False, "uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
									else:
										chList.append({u"key":"onOffState","value":False, "uiValue":self.padDisplay(value)+dateString[5:] })
										dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

								if "lastSensorChange"  in dev.states and (key != "lastSensorChange" or ( key == "lastSensorChange" and nKeys >0)): 
									chList.append({u"key":"lastSensorChange","value":dateString})

							if changedOnly[devId][key]["uiValue"] != "":
								if changedOnly[devId][key][u"decimalPlaces"] != "" and key in dev.states:
									chList.append({u"key":key,"value":changedOnly[devId][key]["value"], u"decimalPlaces":changedOnly[devId][key]["decimalPlaces"],"uiValue":changedOnly[devId][key]["uiValue"]})
									#indigo.server.log(dev.name+"  into changed1 "+unicode(chList))
								else:
									chList.append({u"key":key,"value":changedOnly[devId][key]["value"],"uiValue":changedOnly[devId][key]["uiValue"]})
									#indigo.server.log(dev.name+"  into changed "+unicode(chList))
							else:
								if changedOnly[devId][key][u"decimalPlaces"] != "" and key in dev.states:
									chList.append({u"key":key,"value":changedOnly[devId][key]["value"], u"decimalPlaces":changedOnly[devId][key]["decimalPlaces"]})
								else:
									chList.append({u"key":key,"value":changedOnly[devId][key]["value"]})

						##if dev.name =="b-radius_3": self.indiLOG.log(10,	u"chList "+unicode(chList))

						self.execUpdateStatesList(dev,chList)

		except Exception, e:
				if	unicode(e).find(u"UnexpectedNullErrorxxxx") >-1: return 
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		self.executeUpdateStatesDictActive = ""
		return

####-------------------------------------------------------------------------####
	def execUpdateStatesList(self,dev,chList):
		try:
			if len(chList) ==0: return
			self.dataStats[u"updates"][u"devs"]	  +=1
			self.dataStats[u"updates"][u"states"] +=len(chList)
			self.dataStats[u"updates"][u"nstates"][min(len(chList),10)]+=1

			if self.indigoVersion >6:
				dev.updateStatesOnServer(chList)

			else:
				for uu in chList:
					dev.updateStateOnServer(uu[u"key"],uu[u"value"])


		except Exception, e:
			self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			self.indiLOG.log(40,u"chList: "+ unicode(chList))

###############################################################################################



####-------------------------------------------------------------------------####
	def convertVariableOrDeviceStateToText(self,textIn,enableEval=False):
		try:
			if not isinstance(textIn, (str, unicode)): return textIn
			oneFound=False
			for ii in range(50):	 # safety, no forever loop
				if textIn.find(u"%%v:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertVariableToText0(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find(u"%%d:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertDeviceStateToText0(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find(u"%%FtoC:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertFtoC(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find(u"%%CtoF:") ==-1: break
				oneFound=True
				textIn,rCode = self.convertCtoF(textIn)
				if not rCode: break
			for ii in range(50):	 # safety, no forever loop
				if textIn.find(u"%%eval:") ==-1: break
				oneFound=True
				textIn,rCode = self.evalString(textIn)
				if not rCode: break
			try:
				if enableEval and oneFound and (textIn.find(u"+")>-1 or	 textIn.find(u"-")>-1 or textIn.find(u"/")>-1 or textIn.find(u"*")>-1):
					textIn = unicode(eval(textIn))
			except: pass
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn
####-------------------------------------------------------------------------####
	def convertFtoC(self,textIn):
		#  converts eg: 
		#"abc%%FtoC:1234%%xyz"	  to abcxyz
		try:
			try:
				start= textIn.find(u"%%FtoC:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+7:]
			end = textOut.find(u"%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= "{:.1f}".format((float(var)-32.)*5./9.)
			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				return textOut, True
			except:
				return textIn, False
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn, False
####-------------------------------------------------------------------------####
	def convertCtoF(self,textIn):
		#  converts eg: 
		#"abc%%FtoC:1234%%xyz"	  to abcxyz
		try:
			try:
				start= textIn.find(u"%%CtoF:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+7:]
			end = textOut.find(u"%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= "{:.1f}".format((float(var)*9./5.) + 32)
			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				return textOut, True
			except:
				return textIn, False
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn, False

####-------------------------------------------------------------------------####
	def evalString(self,textIn):
		#  converts eg: 
		#"abc%%FtoC:1234%%xyz"	  to abcxyz
		try:
			try:
				start= textIn.find(u"%%eval:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+7:]
			end = textOut.find(u"%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= eval(var)
			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(20,var)
				self.indiLOG.log(20,textOut[:50])
				return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					self.indiLOG.log(20,textOut)
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				self.indiLOG.log(20,textOut)
				return textOut, True
			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				return textIn, False
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn, False


####-------------------------------------------------------------------------####
	def convertVariableToText0(self,textIn):
		#  converts eg: 
		#"abc%%v:VariName%%xyz"	  to abcCONTENTSOFVARIABLExyz
		#"abc%%V:VariNumber%%xyz to abcCONTENTSOFVARIABLExyz
		try:
			try:
				start= textIn.find(u"%%v:")
			except:
				return textIn, False

			if start==-1:
				return textIn, False
			textOut= textIn[start+4:]
			end = textOut.find(u"%%")
			if end ==-1:
				return textIn, False
			var = textOut[:end]
			try:
				vText= indigo.variables[int(var)].value
			except:
				try:
					vText= indigo.variables[var].value
				except:
					return textIn, False

			try:
				if end+2 >= len(textOut)-1:
					textOut= textIn[:start]+vText
					return textOut, True
				textOut= textIn[:start]+vText+textOut[end+2:]
				return textOut, True
			except:
				return textIn, False
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn, False



####-------------------------------------------------------------------------####
	def convertDeviceStateToText0(self,textIn):
		#  converts eg: 
		#"abc%%d:devName:stateName%%xyz"   to abcdevicestatexyz
		#"abc%%V:devId:stateName%%xyz to abcdevicestatexyz
		try:
			try:
				start= textIn.find(u"%%d:")
			except:
				return textIn, False
			if start==-1:
				return textIn, False
			textOut= textIn[start+4:]

			secondCol = textOut.find(u":")
			if secondCol ==-1:
				return textIn, False
			dev		= textOut[:secondCol]
			textOut = textOut[secondCol+1:]
			percent = textOut.find(u"%%")

			if percent ==-1: return textIn, False
			state	= textOut[:percent]
			textOut = textOut[percent+2:]
			try:
				vText= unicode(indigo.devices[int(dev)].states[state])
			except:
				try:
					vText= unicode(indigo.devices[dev].states[state])
				except:
					return textIn, False
			try:
				if len(textOut)==0:
					textOut= textIn[:start]+vText
					return textOut, True
				textOut= textIn[:start]+vText+textOut
				return textOut, True
			except:
				return textIn, False
		except Exception, e:
			if len(unicode(e)) > 5 :
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return textIn, False



####-----------------  calc # of blnaks to be added to state column to make things look better aligned. ---------
	def padDisplay(self,status):
		if	 status == "up":		return status.ljust(11)
		elif status == "expired":	return status.ljust(8)
		elif status == "down":		return status.ljust(9)
		elif status == "changed":	return status.ljust(8)
		elif status == "double":	return status.ljust(8)
		elif status == "ignored":	return status.ljust(8)
		else:						return status.ljust(10)



	####-----------------	 ---------
	def completePath(self,inPath):
		if len(inPath) == 0: return ""
		if inPath == " ":	 return ""
		if inPath[-1] !="/": inPath +="/"
		return inPath

########################################
########################################
####----checkPluginPath----
########################################
########################################
	####------ --------
	def checkPluginPath(self, pluginName, pathToPlugin):

		if pathToPlugin.find("/" + self.pluginName + ".indigoPlugin/") == -1:
			self.indiLOG.log(50,u"--------------------------------------------------------------------------------------------------------------")
			self.indiLOG.log(50,u"The pluginName is not correct, please reinstall or rename")
			self.indiLOG.log(50,u"It should be   /Libray/....../Plugins/" + pluginName + ".indigoPlugin")
			p = max(0, pathToPlugin.find("/Contents/Server"))
			self.indiLOG.log(50,u"It is: " + pathToPlugin[:p])
			self.indiLOG.log(50,u"please check your download folder, delete old *.indigoPlugin files or this will happen again during next update")
			self.indiLOG.log(50,u"---------------------------------------------------------------------------------------------------------------")
			self.sleep(100)
			return False
		return True

########################################
########################################
####-----------------  logging ---------
########################################
########################################

	####----------------- ---------
	def setLogfile(self, lgFile):
		self.logFileActive =lgFile
		if   self.logFileActive =="standard":	self.logFile = ""
		elif self.logFileActive =="indigo":		self.logFile = self.indigoPath.split("Plugins/")[0]+"Logs/"+self.pluginId+"/plugin.log"
		else:									self.logFile = self.indigoPreferencesPluginDir +"plugin.log"
		self.myLog( text="myLogSet setting parameters -- logFileActive= {}; logFile= {};  debug plugin:{}   RPI#:{}".format(self.logFileActive, self.logFile, self.debugLevel, self.debugRPI) , destination="standard")



	####-----------------  check logfile sizes ---------
	def checkLogFiles(self):
		return
		try:
			self.lastCheckLogfile = time.time()
			if self.logFileActive =="standard": return 
			
			fn = self.logFile.split(".log")[0]
			if os.path.isfile(fn + ".log"):
				fs = os.path.getsize(fn + ".log")
				if fs > self.maxLogFileSize:  
					if os.path.isfile(fn + "-2.log"):
						os.remove(fn + "-2.log")
					if os.path.isfile(fn + "-1.log"):
						os.rename(fn + ".log", fn + "-2.log")
						os.remove(fn + "-1.log")
					os.rename(fn + ".log", fn + "-1.log")
					indigo.server.log(" reset logfile due to size > %.1f [MB]" %(self.maxLogFileSize/1024./1024.) )
		except	Exception, e:
				self.indiLOG.log(50, u"checkLogFiles Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			
			
	####-----------------	 ---------
	def decideMyLog(self, msgLevel):
		try:
			if msgLevel	 == u"all" or u"all" in self.debugLevel:	 return True
			if msgLevel	 == ""	 and u"all" not in self.debugLevel:	 return False
			if msgLevel in self.debugLevel:							 return True
			return False
		except	Exception, e:
			if len(unicode(e)) > 5:
				indigo.server.log( u"decideMyLog Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		return False

	####-----------------  print to logfile or indigo log  ---------
	def myLog(self,	 text="", mType="", errorType="", showDate=True, destination=""):
		   

		try:
			if	self.logFileActive =="standard" or destination.find("standard") >-1:
				if errorType == u"smallErr":
					self.indiLOG.error(u"------------------------------------------------------------------------------")
					self.indiLOG.error(text.encode(u"utf8"))
					self.indiLOG.error(u"------------------------------------------------------------------------------")

				elif errorType == u"bigErr":
					self.indiLOG.error(u"==================================================================================")
					self.indiLOG.error(text.encode(u"utf8"))
					self.indiLOG.error(u"==================================================================================")

				elif mType == "":
					indigo.server.log(text)
				else:
					indigo.server.log(text, type=mType)


			if	self.logFileActive !="standard":

				ts =""
				try:
					if len(self.logFile) < 3: return # not properly defined
					f =  open(self.logFile,"a")
				except Exception, e:
					indigo.server.log(u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					try:
						f.close()
					except:
						pass
					return
			
				if errorType == u"smallErr":
					if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
					f.write(u"----------------------------------------------------------------------------------\n")
					f.write((ts+u" ".ljust(12)+u"-"+text+u"\n").encode(u"utf8"))
					f.write(u"----------------------------------------------------------------------------------\n")
					f.close()
					return

				if errorType == u"bigErr":
					if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
					f.write(u"==================================================================================\n")
					f.write((ts+u" "+u" ".ljust(12)+u"-"+text+u"\n").encode(u"utf8"))
					f.write(u"==================================================================================\n")
					f.close()
					return
				if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
				if mType == u"":
					f.write((ts+u" " +u" ".ljust(25)  +u"-" + text + u"\n").encode("utf8"))
					#indigo.server.log((ts+u" " +u" ".ljust(25)  +u"-" + text + u"\n").encode("utf8"))
				else:
					f.write((ts+u" " +mType.ljust(25) +u"-" + text + u"\n").encode("utf8"))
					#indigo.server.log((ts+u" " +mType.ljust(25) +u"-" + text + u"\n").encode("utf8"))
				f.close()
				return


		except	Exception, e:
			if len(unicode(e)) > 5:
				self.indiLOG.log(50,u"myLog Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				indigo.server.log(text)
				try: f.close()
				except: pass


##################################################################################################################
##################################################################################################################
##################################################################################################################
###################	 TCPIP listen section  receive data from RPI via socket comm  #####################

####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
	def isValidIP(self, ip0):
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
####-------------------------------------------------------------------------####
	def isValidMAC(self, mac0):
		macx = mac0.split(u":")
		if len(macx) != 6 : # len(mac.split("D0:D2:B0:88:7B:76")): 
			return False
		else:
			for xx in macx:
				if len(xx) !=2:
					return False
		return True


####-------------------------------------------------------------------------####
	def startTcpipListening(self, myIpNumber, indigoInputPORT):
			self.indiLOG.log(10, u" ..   starting tcpip stack" )
			socketServer = None
			stackReady	 = False
			if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"starting tcpip socket listener, for RPI data, might take some time, using: ip#={} ;  port#= {}".format(myIpNumber, indigoInputPORT) )
			tcpStart = time.time()
			lsofCMD	 =u"/usr/sbin/lsof -i tcp:{}".format(indigoInputPORT)
			ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"lsof output:{}".format(ret) )
			self.killHangingProcess(ret)
			for ii in range(60):  #	 gives port busy for ~ 60 secs if restart, new start it is fine, error message continues even if it works -- indicator =ok: if lsof gives port number  
				try:
					socketServer = ThreadedTCPServer((myIpNumber,int(indigoInputPORT)), ThreadedTCPRequestHandler)
					if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"TCPIPsocket:: setting reuse	= 1 " )
					socketServer.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"TCPIPsocket:: setting timout = 5 " )
					socketServer.socket.setsockopt(socket.SOL_SOCKET, socket.timeout, 5 )

				except Exception, e:
					if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"TCPIPsocket:: {0}	  try#: {1:d}	time elapsed: {2:4.1f} secs".format(unicode(e), ii,  (time.time()-tcpStart) ) )
				try:
					ret = subprocess.Popen(lsofCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
					if len(ret[0]) >0: #  if lsof gives port number it works.. 
						if self.decideMyLog(u"Socket"): self.indiLOG.log(10, "{}\n{}".format(lsofCMD, ret[0].strip(u"\n")) )
						TCPserverHandle = threading.Thread(target=socketServer.serve_forever)
						TCPserverHandle.daemon =True # don't hang on exit
						TCPserverHandle.start()
						break
				except Exception, e:
					if unicode(e).find("serve_forever") ==-1:
						self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					self.killHangingProcess(ret)
 
				if	 ii <=2:	tcpWaitTime = 7
				else:			tcpWaitTime = 1
				self.sleep(tcpWaitTime)
			try:
				tcpName = TCPserverHandle.getName() 
				if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u'startTcpipListening tcpip socket listener running; thread:#{}'.format(tcpName) )#	+ " try:"+ unicode(ii)+"  time elapsed:"+ unicode(time.time()-tcpStart) )
				stackReady = True
				self.indiLOG.log(10, u" ..   tcpip stack started" )


			except Exception, e:
				self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				self.indiLOG.log(40,"tcpip stack did not load, restarting.. if this error continues, try restarting indigo server")
				self.quitNow=u" tcpip stack did not load, restart"
			return	socketServer, stackReady

	def killHangingProcess(self, ret):

			test = (ret[0].strip("\n")).split("\n")

			if len(test) ==2:
				try: 
					pidTokill = int((test[1].split())[1])
					killcmd = "/bin/kill -9 {}".format(pidTokill)
					if self.decideMyLog(u"Socket"): self.indiLOG.log(10, u"trying to kill hanging process with: {}".format(killcmd) )
					subprocess.call(killcmd, shell=True)
				except Exception, e:
					self.indiLOG.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

####-------------------------------------------------------------------------####
	def handle(self):
		try:
			data0 =""
			dataS =[]
			tStart=time.time()
			len0 = 0
			piName = "none"
			wrongIP = 0

			if	not indigo.activePlugin.ipNumberOK(self.client_address[0]) : 
				wrongIP = 2
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30, u"TCPIP socket data receiving from {} not in accepted ip number list, please fix in >>initial setup RPI<<".format(self.client_address)  )
				#  add looking for ip = ,"ipAddress":"192.168.1.20"
				# but need first to read data 
				indigo.activePlugin.handlesockReporting(self.client_address[0],0,u"unknown",u"errIP" )
				#self.request.close()
				#return

			# 3 secs should be enough even for slow network mostly one package, should all be send in one package
			self.request.settimeout(5) 

			try: # to catch timeout 
				while True: # until end of message
					buff = self.request.recv(4096)#  max observed is ~ 3000 bytes
					if not buff or len(buff) == 0:#	 or len(buff) < 4096: 
						break
					data0 += buff
					len0  = len(data0)

					### check if package is complete:
					dataS = data0.split(u"x-6-a")
					if len(dataS) == 3 and int(dataS[0]) == len(dataS[2]): 
						break

					#safety valves
					if time.time() - tStart > 15: break 
					if	len0 > 13000: # check for overflow = 12 packages
						indigo.activePlugin.handlesockReporting(self.client_address[0],len0,u"unknown",u"errBuffOvfl" )
						self.request.close()
						return 
			except Exception, e:
				e= unicode(e)
				self.request.settimeout(1) 
				self.request.send(u"error")
				self.request.close()
				if e.find("timed out") ==-1: 
					indigo.activePlugin.indiLOG.log(40,u"ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_traceback.tb_lineno, e) )
					indigo.activePlugin.handlesockReporting( self.client_address[0],len0,piName,e[0:min(10,len(e))] )
				else:
					indigo.activePlugin.handlesockReporting( self.client_address[0],len0,piName,u"timeout" )
				return
			self.request.settimeout(1) 
		   
			try: 
				## dataS =split message should look like:  len-TAG-piName-TAG-data; -TAG- = x-6-a
				if len(dataS) !=3: # tag not found 
					if indigo.activePlugindecideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"TCPIP socket  x-6-a  tag not found: {} ... {}".format(data0[0:50], data0[-10:]) )
					try: self.request.send(u"error-tag missing")
					except: pass
					self.request.send(u"error")
					self.request.close()
					indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"errTag" )
					return

				expLength = int(dataS[0])
				piName	  = dataS[1]
				lenData	  = len(dataS[2])


				if expLength != lenData: # expected # of bytes not received
					if lenData < expLength:
						if indigo.activePlugin.decideMyLog(u"Socket"): indigo.indiLOG.log(30,u"TCPIP socket length of {..} data too short, exp:{};   actual:{};   piName:; {}    ..    {}".format(dataS[0], lenData, piName, dataS[2][0:50], data0[-10:]) )
						try: self.request.send(u"error-lenDatawrong-{}".format(lenData) )
						except: pass
						self.request.send(u"error")
						self.request.close()
						indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"tooShort" )
						return
					else:
						# check if we received a complete package + extra
						package1 = dataS[2][:expLength]
						try:
							json.loads(package1)
							dataS[2] = package1
							if indigo.activePlugindecideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"TCPIP socket length of data wrong -fixed- exp:{};  actual:{};  piName:{}; {}     ..     {}".format(dataS[0], lenData, piName, dataS[2][0:50], data0[-10:]) )
						except:
							if indigo.activePlugindecideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"TCPIP socket length of data wrong exp:{};  actual:{};  piName:{}; {}     ..     {}".format(dataS[0], lenData, piName, dataS[2][0:50], data0[-10:]) )
							try: self.request.send(u"error-lenDatawrong-{}".format(lenData) )
							except: pass
							self.request.send(u"error")
							self.request.close()
							indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"tooLong" )
							return

			except Exception, e:
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30, u"TCPIP socket, len:{0:d} data: {1}  ..  {2}".format(len0, data0[0:50], data0[-10:]) )
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"unknown" )
				self.request.send(u"error")
				self.request.close()
				return

			try: 
				dataJ = json.loads(dataS[2])  # dataJ = json object for data
			except Exception, e:
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"TCPIP socket  json error; len of data: {0:d}  {1}     time used: {2:5.1f}".format(len0, unicode(threading.currentThread()), time.time()-tStart )  )
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,data0[0:50]+u"  ..  {}".format(data0[-10:]) ) 
				try: self.request.send(u"error-Json-{}".format(lenData) )
				except: pass
				indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"errJson" )
				self.request.send(u"error")
				self.request.close()
				return

			if piName.find(u"pi_IN_") != 0 : 
				if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30,u"TCPIP socket  listener bad piName {}".format(piName) )
				indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"badpiName" )
			else:
				wrongIP -= 1
				#### now update Indigo dev/ states 
				indigo.activePlugin.addToDataQueue( piName, dataJ,dataS[2] )
				if wrongIP < 1: indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"ok",msg=data0 )

			try:	
				if wrongIP < 2: 
					if indigo.activePlugin.decideMyLog(u"Socket"): 
						indigo.activePlugin.indiLOG.log(20, u" sending ok to {} data: {}..{}".format(piName.ljust(13), dataS[2][0:50], dataS[2][-20:]) )
					self.request.send(u"ok-{}".format(lenData) )
			except: pass
			self.request.close()



		except Exception, e:
			if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30, u"ThreadedTCPRequestHandler Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			if indigo.activePlugin.decideMyLog(u"Socket"): indigo.activePlugin.indiLOG.log(30, u"TCPIP socket {}".format(data0[0:50]) ) 
			indigo.activePlugin.handlesockReporting(self.client_address[0],len0,piName,u"unknown" )
			self.request.close()
		return
####-------------------------------------------------------------------------####
####-------------------------------------------------------------------------####
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	pass

###################	 TCPIP listen section  receive data from RPI via socket comm  end			 #################
##################################################################################################################
##################################################################################################################




##################################################################################################################
####-----------------  valiable formatter for differnt log levels ---------
# call with: 
# formatter = LevelFormatter(fmt='<default log format>', level_fmts={logging.INFO: '<format string for info>'})
# handler.setFormatter(formatter)
class LevelFormatter(logging.Formatter):
	def __init__(self, fmt=None, datefmt=None, level_fmts={}, level_date={}):
		self._level_formatters = {}
		self._level_date_format = {}
		for level, formt in level_fmts.items():
			# Could optionally support level names too
			self._level_formatters[level] = logging.Formatter(fmt=formt, datefmt=level_date[level])
		# self._fmt will be the default format
		super(LevelFormatter, self).__init__(fmt=formt, datefmt=datefmt)

	def format(self, record):
		if record.levelno in self._level_formatters:
			return self._level_formatters[record.levelno].format(record)

		return super(LevelFormatter, self).format(record)




