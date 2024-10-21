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
import	piBeaconUtils	as U
import	piBeaconGlobals as G

sys.path.append(os.getcwd())

U.setLogging()

program = "killSudos"

myOwnPID = int(os.getpid())

def execKill(pgmtype):
	try:
		killedpgms = ""
		verbose = True
		count = 0
		cmd = "ps -ef | grep '"+pgmtype+"' | grep sudo | grep -v grep | grep -v killSudos"
	
		ret = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8')
		if verbose and len(ret) > 10: U.logger.log(20, "==grep cmd:{}, \nresult:{}< ".format(cmd, ret) )
		lines = ret.split("\n")
		del ret
		xlist = ""
		for line in lines:
			if len(line) > 10: 
				items = line.split()
				pid = int(items[1])
				if pid != myOwnPID: 
		
					if verbose: U.logger.log(20, "==kill sudos killing line:{}".format( (" ").join(items[7:])) )
					xlist += str(pid)+ " "
					count += 1
					killedpgms += (" ").join(items[7:])+";"

		if len(xlist) > 2:
			if verbose:  U.logger.log(20, "== ext-kill /usr/bin/sudo kill -9 {} ".format(xlist) )
			subprocess.call("/usr/bin/sudo kill -9 {}".format(xlist), shell=True)

		if count > 0:
			U.logger.log(20, "==kill sudos finished killed {} programs:{} w pids:{}".format(count, killedpgms, xlist) )

	except Exception as e:
		if str(e).find("Too many open files") >-1:
			doReboot(tt=3, text=str(e), force=True)
		if verbose: U.logger.log(30,"", exc_info=True)


execKill("python")
execKill("hcidump")
execKill("lescan")
exit()