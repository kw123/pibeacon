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
    def __init__(self, pathToMACFiles = "", refreshFromIeeAfterDays = 10):


        self.mac2VendorDict ={"6":{},"7":{},"9":{}}

        self.MAChome     = os.path.expanduser("~")+"/"
        
        if pathToMACFiles !="":
            self.filePath = pathToMACFiles
            if self.filePath[-1]!="/": self.filePath+="/"
            if not os.path.isdir(self.filePath):
                os.mkdir(self.filePath)
        else:
            self.filePath = self.MAChome+"indigo/mac2Vendor/"
            if not os.path.isdir(self.MAChome+"indigo"):
                os.mkdir(self.MAChome+"indigo")
            if not os.path.isdir(self.filePath):
                os.mkdir(self.filePath)

        self.refreshFromIeeAfterDays = refreshFromIeeAfterDays

        if not os.path.isdir(self.filePath):
            os.mkdir(self.filePath)

       
        if not self.isFileCurrent(self.filePath+"mac2Vendor.json", 700000): 
            self.getFiles()
            return

        self.makeFinalTable()

        return 


    ########################################
    def getFiles(self):

        if ( self.isFileCurrent(self.filePath+"oui",  500000) and 
             self.isFileCurrent(self.filePath+"mam",   30000)  and
             self.isFileCurrent(self.filePath+"oui36", 40000) ):  return

        cmd  =  "rm "+self.filePath+"oui ;"
        cmd +=  "rm "+self.filePath+"mam ;"
        cmd +=  "rm "+self.filePath+"oui36"
        os.system(cmd)

        os.system("/usr/bin/curl -L https://standards.ieee.org/develop/regauth/oui/oui.csv      |  tail -n +2  | cut -d',' -f'2,3' | sed 's/\"//'> '"+self.filePath+"oui' &")
        os.system("/usr/bin/curl -L https://standards.ieee.org/develop/regauth/oui28/mam.csv    |  tail -n +2  | cut -d',' -f'2,3' | sed 's/\"//'> '"+self.filePath+"mam' &")
        os.system("/usr/bin/curl -L https://standards.ieee.org/develop/regauth/oui36/oui36.csv  |  tail -n +2  | cut -d',' -f'2,3' | sed 's/\"//'> '"+self.filePath+"oui36' &")


        return 

    ########################################
    def isFileCurrent(self,fileName,size):
        if os.path.isfile(fileName)  and os.path.getsize(fileName) > size:
            if  time.time() - os.path.getmtime(fileName) < self.refreshFromIeeAfterDays*24*60*60:
                return True
        return False

    ########################################
    def makeFinalTable(self):

        if self.isFileCurrent(self.filePath+"mac2Vendor.json", 700000):
            f = open(self.filePath+"mac2Vendor.json","r")
            self.mac2VendorDict = json.loads(f.read())
            f.close()
            return True
            
        if not self.isFileCurrent(self.filePath+"oui",  500000): return False
        if not self.isFileCurrent(self.filePath+"mam",   30000): return False
        if not self.isFileCurrent(self.filePath+"oui36", 40000): return False

        self.mac2VendorDict ={"6":{},"7":{},"9":{}}

        self.importFile("oui",  "6")
        self.importFile("mam",  "7")
        self.importFile("oui36","9")

        f = open(self.filePath+"mac2Vendor.json","w")
        f.write(json.dumps(self.mac2VendorDict))
        f.close()

        return True


    ########################################
    def importFile(self,fn,size):
        f = open(self.filePath+fn,"r")
        dat = f.readlines()
        f.close()
        for line in dat:
            item= line.split(",")
            if len(item) < 2: continue
            self.mac2VendorDict[size][item[0]]=item[1].strip("\n")
        return

    ########################################
    def getVendorOfMAC(self,MAC):
            mac = MAC.replace(":","").upper()
            if mac[0:6] in self.mac2VendorDict["6"]:        # large  Vendor Space
                return self.mac2VendorDict["6"][mac[0:6]]
            if mac[0:7] in self.mac2VendorDict["7"]:        # medium Vendor Space
                return self.mac2VendorDict["7"][mac[0:7]]
            if mac[0:9] in self.mac2VendorDict["9"]:        # small  Vendor Space
                return self.mac2VendorDict["9"][mac[0:9]]
            return ""
            
    ########################################
    ########  END OF CLASS      ############
    ########################################
