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
import codecs

# ===========================================================================
# MAP2Vendor Class
# ===========================================================================

class MAP2Vendor:

	########################################
	def __init__(self, pathToMACFiles = "", refreshFromIeeAfterDays = 10, myLogger = ""):


		"""Initializes the MAC2Vendor lookup object: resolves and creates the directory holding the IEEE OUI/MAC files, stores the logger and refresh interval, and either kicks off a download of the raw files or builds the in-memory vendor lookup table if a current cached JSON exists.

		Inputs:
		    pathToMACFiles (str): Directory to store/read MAC vendor files; defaults to ~/indigo/mac2Vendor/ if empty
		    refreshFromIeeAfterDays (int): Age in days after which cached IEEE files are considered stale
		    myLogger (callable): Logging callable invoked as myLogger(level, message)
		Outputs:
		    None: Sets up instance state, creates directories, and triggers file download or table build
		"""
		self.lastFinishedMessage = 0
		self.myLogger = myLogger
		self.myLogger(10, "MAP2Vendor initializing with python v:{}".format(sys.version_info[0]))

		self.minSizeOfFiles = {"mac2Vendor.json":700000, "oui":500000,"mam": 30000, "oui36":40000}

		self.getFilesStatus = "init" 

		self.mac2VendorDict = {"6":{},"7":{},"9":{}}

		self.MAChome	 	= os.path.expanduser("~")+"/"

		if pathToMACFiles != "":
			self.filePath = pathToMACFiles
			if self.filePath[-1]!="/": self.filePath+="/"
			if not os.path.isdir(self.filePath):
				self.myLogger(10, "MAP2Vendor (i) making directory:" +self.filePath)
				os.mkdir(self.filePath)
		else:
			self.filePath = self.MAChome+"indigo/mac2Vendor/"
			if not os.path.isdir(self.MAChome+"indigo"):
				self.myLogger(10, "MAP2Vendor (ii) making directory:" +self.MAChome+"indigo")
				os.mkdir(self.MAChome+"indigo'")
			if not os.path.isdir(self.filePath):
				self.myLogger(10, "MAP2Vendor (iii) making directory:" +self.filePath)
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

		"""Downloads the raw IEEE OUI/MAM/OUI36 registration CSV files via curl (in the background) if the cached copies are stale, stripping headers and extracting the relevant columns; sets getFilesStatus accordingly.

		Inputs:
		    None.
		Outputs:
		    None: Removes old files, launches background curl downloads, and updates self.getFilesStatus
		"""
		if ( self.isFileCurrent("oui")   and 
			 self.isFileCurrent("mam")   and
			 self.isFileCurrent("oui36") ):
			self.getFilesStatus = "finished"
			return

		self.myLogger(10,"MAP2Vendor  downloading raw files, will take some minutes")
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
		"""Checks whether a cached MAC file exists, exceeds its required minimum size, and was modified more recently than the configured refresh interval.

		Inputs:
		    fileName (str): Base name of the file to check (key into minSizeOfFiles)
		Outputs:
		    bool: True if the file exists, is large enough, and is fresh; otherwise False
		"""
		fn = self.filePath+fileName
		if os.path.isfile(fn)  and os.path.getsize(fn) > self.minSizeOfFiles[fileName]:
			if  time.time() - os.path.getmtime(fn) < self.refreshFromIeeAfterDays*24*60*60:
				return True
		return False

	########################################
	def makeFinalTable(self):
		"""Builds the consolidated MAC-to-vendor lookup dictionary: loads it from the cached mac2Vendor.json if current and large enough, otherwise imports the raw oui/mam/oui36 files into nested dicts keyed by prefix length and writes the merged result back to mac2Vendor.json.

		Inputs:
		    None.
		Outputs:
		    bool: True on success or when waiting on downloads completes; False if data is missing or downloads not yet ready
		"""
		try:

			if self.isFileCurrent("mac2Vendor.json"):
				test = {}
				try:
					f = self.openEncoding(self.filePath+"mac2Vendor.json","r")
					test = json.loads(f.read())
					f.close()
				except Exception as e:
					self.myLogger(30, "error reading file {} in prefs dir, errcode:{}".format("mac2Vendor.json", e))
	
				if "6" in test:
					if len(test["6"]) < 10000:
						return False
				else:
						return False

				self.mac2VendorDict = test
				if time.time() - self.lastFinishedMessage >1:
					self.myLogger(10,"MAP2Vendor initializing  finished, read from mac2Vendor.json file")
				self.lastFinishedMessage  = time.time()
				return True
			
			if not ( self.isFileCurrent("oui") or
					 self.isFileCurrent("mam" )  or
					 self.isFileCurrent("oui36") ):
					if  self.getFilesStatus == "submitted"  :
						self.myLogger(10, "MAP2Vendor initializing still waiting for download")
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
			self.myLogger(30,"error reading file {}, errcode:{}".format("mac2Vendor.json", e))
		return True


	########################################
	def importFile(self, fn, size):
		"""Reads one raw IEEE vendor file line by line, splitting each line on commas and storing the MAC prefix to vendor-name mapping into the prefix-length bucket of mac2VendorDict.

		Inputs:
		    fn (str): Base filename of the raw vendor file to read
		    size (str): Dict key (prefix-length bucket, e.g. '6', '7', '9') to populate
		Outputs:
		    None: Populates self.mac2VendorDict[size] with prefix-to-vendor entries
		"""
		try:
			f = self.openEncoding(self.filePath+fn,"r")
			dat = f.readlines()
			f.close()
			for line in dat:
				item= line.split(",")
				if len(item) < 2: continue
				self.mac2VendorDict[size][item[0]]=item[1].strip("\n")
		except Exception as e:
			self.myLogger(30, "error reading file {}, errcode:{}".format(fn, e))
			
		return



	########################################
	def getVendorOfMAC(self,MAC):
			"""Looks up the manufacturer/vendor name for a given MAC address by normalizing it and matching successively longer prefixes (6, 7, then 9 hex chars) against the loaded lookup table; rebuilds the table if it appears unpopulated.

			Inputs:
			    MAC (str): MAC address string, possibly colon-separated
			Outputs:
			    str: The matched vendor name, or empty string if not found
			"""
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

		"""Opens a file with UTF-8 encoding in a way compatible with both Python 2 and Python 3, using the built-in open on Py3 and codecs.open on Py2.

		Inputs:
		    ff (str): Path of the file to open
		    readOrWrite (str): File mode such as 'r' or 'w'
		Outputs:
		    file: An open UTF-8 file handle
		"""
		if sys.version_info[0]  > 2:
			return open( ff, readOrWrite, encoding="utf-8")
		else:
			return codecs.open( ff ,readOrWrite, "utf-8")

		
	########################################
	########  END OF CLASS	  ############
	########################################
