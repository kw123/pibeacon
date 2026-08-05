#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	  --- not implemented yet ..
#
#	 

##

import	sys, os, subprocess, copy
import	time,datetime
import	json

sys.path.append(os.getcwd())
import	piBeaconUtils as U
import	piBeaconGlobals as G



def readParams():
		"""Reads the plugin parameter file and, if its raw content changed since the last read, updates the global actions list from the parsed input.

		Inputs:
		    None.
		Outputs:
		    None: Updates the global actions and oldParams variables
		"""
		global oldParams, actions

		inp, inpRaw, x = U.doRead()
		if inp == "": return

		if inpRaw == oldParams: return
		oldParams = inpRaw

		if "actions"			in inp : actions =			(inp["actions"])


def doActions():
		"""Intended to process the configured actions, but the body currently returns immediately so it performs no work (placeholder/stub wrapped in a try/except that logs exceptions).

		Inputs:
		    None.
		Outputs:
		    None: No-op stub; returns immediately
		"""
		global actions
		try:
			return

### actions: [{1},{2},{3}]
		except Exception as e:
			U.logger.log(20,"", exc_info=True)


#################################



def execMain():
	"""Main entry point for the actions worker process: sets globals, kills stale instances of itself, configures logging, reads action parameters, and runs an endless loop that periodically refreshes an alive heartbeat file, reloads parameters, and executes queued actions.

	Inputs:
	    None.
	Outputs:
	    None: Runs forever; writes heartbeat files, reads params, executes actions, and logs
	"""
	global oldParams,actions
	
	
	###################### constants #################
	G.program = "actions"
	
	oldParams		 = ""
	actions			 = []
	myPID		= str(os.getpid())
	
	U.killOldPgm(myPID,"actions.py")# old old instances of myself if they are still running
	
	U.setLogging()
	
	U.logger.log(20, "starting action program")
	readParams()
	# check if everything is installed
	
	lastAliveFile	= time.time()
	U.doWriteSimpleFile(G.homeDir+"temp/alive.action", lastAliveFile)
	
	
	
	while True:
		try:
			tt= time.time()
			loopCount =1
	
			if loopCount%20 == 0 or tt-lastAliveFile > 100:	# update alive	every 10 seconds or faster
				lastAliveFile = tt
				#print "Updating alive.sensors"
				U.doWriteSimpleFile(G.homeDir+"temp/alive.action", time.time())
				readParams()
	
			if actions == []:
				time.sleep(5)
				continue
			doActions()
	
			time.sleep(0.1)
		except Exception as e:
			U.logger.log(20,"", exc_info=True)
			time.sleep(5.)


sys.exit(0)
