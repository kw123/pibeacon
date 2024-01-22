#!/usr/bin/python
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import sys
import json
import os
import datetime
import subprocess
#sys.path.append(os.getcwd())
#sys.path.append('/usr/lib/python3/dist-packages') 

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

U.setLogging()

program = "killOldPgm"

myOwnPID		= str(os.getpid())

myPID = ""
pgmToKill = ""
delList = []
param1 = ""
param2 = ""
verbose = True
count = 0
try: 
	myPID 		= sys.argv[1]
	pgmToKill 	= sys.argv[2]
	param1 		= sys.argv[3]
	param2 		= sys.argv[4]
except:pass

if myPID == "": sys.exit() 
if verbose: 
	print("== ext-kill== 1 argv: {};  myOwnPID:{}".format(sys.argv, myOwnPID) )
	U.logger.log(20,"== ext-kill== 1 argv: {};  myOwnPID:{}".format(sys.argv, myOwnPID) )

try:

		#print "killOldPgm ",pgmToKill,str(myPID)
		cmd= "ps -ef | grep '{}' | grep -v grep | grep -v ' {} ' | grep -v ' {} ' | grep -v sudo".format(pgmToKill, myOwnPID, myPID  )
		if param1 !="":
			cmd = "{} | grep {}".format(cmd,param1)
		if param2 !="":
			cmd = "{} | grep ".format(cmd,param2)
		if verbose: U.logger.log(20, u"== ext-kill== 2 kill command {}, {}".format(cmd, delList) )

		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
		lines=ret.split("\n")
		del ret
		xlist = ""
		for line in lines:
			if len(line) < 10: continue
			items=line.split()
			pid=int(items[1])
			if pid == int(myPID): continue
			if pid == int(myOwnPID): continue
			if verbose: U.logger.log(20, u"== ext-kill== 3 killing {}  {}  {}, pid={}, line:{}".format( pgmToKill, param1, param2, pid, (" ").join(items[8:])) )
			xlist += str(pid)+ " "
			count += 1
		if len(xlist) > 3:
			if verbose: 
				U.logger.log(20,u"== ext-kill== 4 /usr/bin/sudo kill -9 {} ".format(xlist) )
			subprocess.call("/usr/bin/sudo kill -9 {}".format(xlist), shell=True)
except Exception as e:
		if str(e).find("Too many open files") >-1:
			doReboot(tt=3, text=str(e), force=True)
		if verbose: U.logger.log(30,"", exc_info=True)
