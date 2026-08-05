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

		# /proc instead of "ps -ef | grep X | grep -v grep | grep -v <pid> | grep -v sudo":
		# no shell, no ps, no 4 greps - and the match is against the COMMAND LINE only, so a pid
		# or user name in the ps columns can no longer produce a hit. Same exclusions as before:
		# grep processes, our own pid, and the sudo wrapper of the process we are about to kill.
		procs = U.procList(pgmToKill)
		if verbose: U.logger.log(20, "== ext-kill== 2 looking for:{} {} {} (excl grep/sudo/own pid), candidates:{}, {}".format(pgmToKill, param1, param2, len(procs), delList) )

		xlist = ""
		for pid, cmd in procs:
			if (" " + cmd + " ").find(" grep ") > -1:	continue
			if cmd.find("sudo") > -1:					continue
			if param1 != "" and cmd.find(param1) < 0:	continue
			if param2 != "" and cmd.find(param2) < 0:	continue
			if pid == int(myPID): 
				if verbose: U.logger.log(20, "== ext-kill== 3 not killing pid={}, cmd:{}".format( pid, cmd) )
				continue
			if pid == int(myOwnPID): continue
			# the stop marker belongs AFTER the pid checks: it asks a display to shut itself down
			# before we kill it, so it must only be written for a process we are ACTUALLY killing.
			# Written earlier it also hit the caller's own display (display.py kills its older
			# instances and passes its own pid), which then read the marker and stopped itself
			# ~15 s later - "exiting - stop was requested" right after a normal start.
			if cmd.find("display") > -1:
				U.logger.log(20, "== ext-kill== WRITING {}temp/display.stop for pid {} (cmd:{}), ts:{:.1f}".format(G.homeDir, pid, cmd, time.time()))
				f=open(G.homeDir+"temp/display.stop","w")
				f.write("stop")
				f.close()
				time.sleep(1)
			if verbose: U.logger.log(20, "== ext-kill== 3 killing {}  {}  {}, pid={}, cmd:{}".format( pgmToKill, param1, param2, pid,  cmd ) )
			xlist += str(pid)+ " "
			count += 1
		if len(xlist) > 3:
			if verbose: 
				U.logger.log(20,"== ext-kill== 4 /usr/bin/sudo kill -9 {} ".format(xlist) )
			subprocess.call("/usr/bin/sudo kill -15 {}".format(xlist), shell=True)
except Exception as e:
		if str(e).find("Too many open files") >-1:
			U.doReboot(tt=3, text=str(e), force=True)
		if verbose: U.logger.log(20,"", exc_info=True)
