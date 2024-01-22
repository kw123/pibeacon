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

program = "killSudos"

myOwnPID		= str(os.getpid())



def execKill():
	try:
		verbose = False
		count = 0
		cmd= "ps -ef | grep 'python' | grep sudo | grep -v grep | grep -v killSudos"
		if verbose: U.logger.log(20, u"==grep result:{}, ".format(cmd) )
	
		ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
		lines=ret.split("\n")
		del ret
		xlist = ""
		for line in lines:
			if len(line) < 10: continue
			items=line.split()
			pid=int(items[1])
			if pid == int(myOwnPID): continue
			if verbose: U.logger.log(20, u"==kill sudos killing line:{}".format( (" ").join(items[7:])) )
			xlist += str(pid)+ " "
			count += 1
		if len(xlist) > 3:
			if verbose: 
				U.logger.log(20,u"== ext-kill /usr/bin/sudo kill -9 {} ".format(xlist) )
			subprocess.call("/usr/bin/sudo kill -9 {}".format(xlist), shell=True)
		if count > 0:
			U.logger.log(20,u"==kill sudos finished killed {} programs".format(count) )
	except Exception as e:
		if str(e).find("Too many open files") >-1:
			doReboot(tt=3, text=str(e), force=True)
		if verbose: U.logger.log(30,"", exc_info=True)

execKill()
exit()