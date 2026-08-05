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
	"""Finds all sudo processes matching the given program-type string (excluding grep and this killer itself), and force-kills them with 'sudo kill -9', logging which PIDs and programs were killed. Reboots if a 'Too many open files' error occurs.

	Inputs:
	    pgmtype (str): Substring used to match target process command lines in ps output
	Outputs:
	    None: Kills matching sudo processes and logs the result
	"""
	try:
		killedpgms = ""
		verbose = True
		count = 0
		# /proc instead of "ps -ef | grep X | grep sudo | grep -v grep | grep -v killSudos":
		# no shell, no ps, no 4 greps - and matching the command line only, not the ps columns
		# NEVER touch these: master runs killSudos every 10th loop, and killing the "sudo .." / "sh -c
		# sudo .." wrapper of a long running tool does NOT kill its python child - it only orphans it,
		# detaches it from the caller that is waiting for it, and leaves whatever the tool had claimed
		# (radios, pause files) claimed. qualifyDongle runs for ~4 minutes, so it was hit every time.
		neverKill = ["qualifyDongle.py"]
		procs = [[pid, cmd] for pid, cmd in U.procList(pgmtype)
					if cmd.find("sudo") > -1 and (" "+cmd+" ").find(" grep ") < 0 and cmd.find("killSudos") < 0
					and not [1 for nn in neverKill if cmd.find(nn) > -1]]
		if verbose and len(procs) > 0: U.logger.log(20, "==kill sudos: {} sudo process(es) matching {}".format(len(procs), pgmtype) )
		xlist = ""
		for pid, cmdline in procs:
			if pid == myOwnPID: continue
			if verbose: U.logger.log(20, "==kill sudos killing cmd:{}".format(cmdline) )
			xlist += str(pid)+ " "
			count += 1
			killedpgms += cmdline + ";"

		if len(xlist) > 2:
			if verbose:  U.logger.log(20, "== ext-kill /usr/bin/sudo kill -9 {} ".format(xlist) )
			subprocess.call("/usr/bin/sudo kill -9 {}".format(xlist), shell=True)

		if count > 0:
			U.logger.log(20, "==kill sudos finished killed {} programs:{} w pids:{}".format(count, killedpgms, xlist) )

	except Exception as e:
		if str(e).find("Too many open files") >-1:
			U.doReboot(tt=3, text=str(e), force=True)
		if verbose: U.logger.log(20,"", exc_info=True)


execKill("python")
execKill("hcidump")
execKill("lescan")
exit()