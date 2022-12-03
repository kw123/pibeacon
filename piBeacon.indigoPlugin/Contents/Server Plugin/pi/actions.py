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
print sys.path
import	piBeaconUtils as U
import	piBeaconGlobals as G



def readParams():
		global oldParams, actions

		inp,inpRaw = doRead()
		if inp == "": return

		if inpRaw == oldParams: return
		oldParams = inpRaw

		if "actions"			in inp : actions =			(inp["actions"])


def doActions():
		global actions
		try:
			return

### actions: [{1},{2},{3}]
		except	Exception as e:
			U.logger.log(30,"", exc_info=True)


#################################




global oldParams,actions


###################### constants #################
G.program = "actions"

oldParams		 = ""
actions			 = []
myPID		= str(os.getpid())

killOldPgm(myPID,"actions.py")# old old instances of myself if they are still running

U.setLogging()

loopCount		  = 0
U.logger.log(30, "starting action program")
readParams()
# check if everything is installed

lastAliveFile	= time.time()
print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" action: setting alive file"
subprocess.call("echo "+str(lastAliveFile)+" > "+ G.homeDir+"temp/alive.action  &", shell=True)



tStart = time.time() 

while True:
	try:
		tt= time.time()
		loopCount =1

		if loopCount%(20) == 0 or tt-lastAliveFile > 100:	# update alive	every 10 seconds or faster
			lastAliveFile = tt
			#print "Updating alive.sensors"
			subprocess.call("echo "+str(time.time())+" > "+ G.homeDir+"temp/alive.action	&", shell=True )
			readParams()

		if actions == []:
			time.sleep(5)
			continue
		doActions()

		time.sleep(0.1)
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(5.)


sys.exit(0)
