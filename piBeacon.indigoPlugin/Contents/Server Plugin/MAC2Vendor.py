#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# get mac to vendor table local 
# Developed by Karl Wachs
# karlwachs@me.com
import subprocess
import os
import sys
import time
import json

# ===========================================================================
# MAP2Vendor Class
# ===========================================================================

class MAP2Vendor:

	########################################
	def __init__(self, pathToMACFiles = "", refreshFromIeeAfterDays = 10, myLogger = ""):


		self.lastFinishedMessage = 0
		self.myLogger = myLogger
		self.myLogger(10, u"MAP2Vendor initializing with python v:{}".format(sys.version_info[0]))

		self.minSizeOfFiles = {"mac2Vendor.json":700000, "oui":500000,"mam": 30000, "oui36":40000}

		self.getFilesStatus = "init" 

		self.mac2VendorDict = {"6":{},"7":{},"9":{}}

		self.MAChome	 	= os.path.expanduser("~")+"/"

		if pathToMACFiles != "":
			self.filePath = pathToMACFiles
			if self.filePath[-1]!="/": self.filePath+="/"
			if not os.path.isdir(self.filePath):
				self.myLogger(10, u"MAP2Vendor (i) making directory:" +self.filePath)
				os.mkdir(self.filePath)
		else:
			self.filePath = self.MAChome+"indigo/mac2Vendor/"
			if not os.path.isdir(self.MAChome+"indigo"):
				self.myLogger(10, u"MAP2Vendor (ii) making directory:" +self.MAChome+"indigo")
				os.mkdir(self.MAChome+"indigo'")
			if not os.path.isdir(self.filePath):
				self.myLogger(10, u"MAP2Vendor (iii) making directory:" +self.filePath)
				os.mkdir(self.filePath)

		self.refreshFromIeeAfterDays = refreshFromIeeAfterDays

		if not os.path.isdir(self.filePath):
			subprocess.call("mkdir "+self.filePath, shell=True)

	   
		if not self.isFileCurrent("mac2Vendor.json"): 
			self.getFiles()
			return

		self.makeFinalTable()


		return 

	########################################
	def getFiles(self):

		if ( self.isFileCurrent("oui")   and 
			 self.isFileCurrent("mam")   and
			 self.isFileCurrent("oui36") ):
			self.getFilesStatus = "finished"
			return

		self.myLogger(10,u"MAP2Vendor  downloading raw files, will take some minutes")
		cmd  =  "rm "+self.filePath+"oui ;"
		cmd +=  "rm "+self.filePath+"mam ;"
		cmd +=  "rm "+self.filePath+"oui36"
		os.system(cmd)

		os.system("/usr/bin/curl -L https://standards.ieee.org/develop/regauth/oui/oui.csv      |  tail -n +2  | cut -d',' -f'2,3' | sed 's/\"//'> '"+self.filePath+"oui' &")
		os.system("/usr/bin/curl -L https://standards.ieee.org/develop/regauth/oui28/mam.csv    |  tail -n +2  | cut -d',' -f'2,3' | sed 's/\"//'> '"+self.filePath+"mam' &")
		os.system("/usr/bin/curl -L https://standards.ieee.org/develop/regauth/oui36/oui36.csv  |  tail -n +2  | cut -d',' -f'2,3' | sed 's/\"//'> '"+self.filePath+"oui36' &")

		self.getFilesStatus = "submitted" 

		return 

	########################################
	def isFileCurrent(self, fileName):
		fn = self.filePath+fileName
		if os.path.isfile(fn)  and os.path.getsize(fn) > self.minSizeOfFiles[fileName]:
			if  time.time() - os.path.getmtime(fn) < self.refreshFromIeeAfterDays*24*60*60:
				return True
		return False

	########################################
	def makeFinalTable(self):
		try:

			if self.isFileCurrent("mac2Vendor.json"):
				test = {}
				try:
					f = self.openEncoding(self.filePath+"mac2Vendor.json","r")
					test = json.loads(f.read())
					f.close()
				except Exception as e:
					self.myLogger(30, u"error reading file {} in prefs dir, errcode:{}".format("mac2Vendor.json", e))
	
				if "6" in test:
					if len(test["6"]) < 10000:
						return False
				else:
						return False

				self.mac2VendorDict = test
				if time.time() - self.lastFinishedMessage >1:
					self.myLogger(10,u"MAP2Vendor initializing  finished, read from mac2Vendor.json file")
				self.lastFinishedMessage  = time.time()
				return True
			
			if not ( self.isFileCurrent("oui") or
					 self.isFileCurrent("mam" )  or
					 self.isFileCurrent("oui36") ):
					if  self.getFilesStatus == "submitted"  :
						self.myLogger(10, u"MAP2Vendor initializing still waiting for download")
					return False

			self.getFilesStatus = "finished" 

			self.mac2VendorDict ={"6":{},"7":{},"9":{}}

			self.importFile("oui",  "6")
			self.importFile("mam",  "7")
			self.importFile("oui36","9")

			f = self.openEncoding(self.filePath+"mac2Vendor.json","w")
			f.write(json.dumps(self.mac2VendorDict))
			f.close()

			return True
		except Exception as e:
			self.myLogger(30,u"error reading file {}, errcode:{}".format("mac2Vendor.json", e))
		return True


	########################################
	def importFile(self, fn, size):
		try:
			f = self.openEncoding(self.filePath+fn,"r")
			dat = f.readlines()
			f.close()
			for line in dat:
				item= line.split(",")
				if len(item) < 2: continue
				self.mac2VendorDict[size][item[0]]=item[1].strip("\n")
		except Exception as e:
			self.myLogger(30, u"error reading file {}, errcode:{}".format(fn, e))
			
		return



	########################################
	def getVendorOfMAC(self,MAC):
			if "6" not in self.mac2VendorDict: 
				return ""
			if len(self.mac2VendorDict["6"]) < 1000:
				self.makeFinalTable()
				return ""

			mac = MAC.replace(":","").upper()
			if mac[0:6] in self.mac2VendorDict["6"]:		# large  Vendor Space
				return self.mac2VendorDict["6"][mac[0:6]]
			if mac[0:7] in self.mac2VendorDict["7"]:		# medium Vendor Space
				return self.mac2VendorDict["7"][mac[0:7]]
			if mac[0:9] in self.mac2VendorDict["9"]:		# small  Vendor Space
				return self.mac2VendorDict["9"][mac[0:9]]
			return ""
	

####-------------------------------------------------------------------------####
	def openEncoding(self, ff, readOrWrite):

		if sys.version_info[0]  > 2:
			return open( ff, readOrWrite, encoding="utf-8")
		else:
			return codecs.open( ff ,readOrWrite, "utf-8")

		
	########################################
	########  END OF CLASS	  ############
	########################################
