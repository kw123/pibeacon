#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# march 2
# this program will be called if indigo plugin sends a myoutput command
##
import json
import sys
import subprocess
import time
import datetime
import os


sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G

G.program = "myoutput"
## ===========================================================================
# utils do not chnage
#  ===========================================================================

def readParams():
	inp, inpRaw, x = U.doRead()
	if inp == "": return
	U.getGlobalParams(inp)


# ===========================================================================
# Main
# ===========================================================================

U.setLogging()

try:
		readParams()

		myPID = str(os.getpid())
		U.killOldPgm(myPID,"myoutput.py")# kill  old instances of myself if they are still running

		U.logger.log(30, "myoutput  received text :{}".format(sys.argv))

		# rest is up to you  the text indgo has send is in sys.argv[1] [2] ....
		if len(sys.argv) >1 :
			text = sys.argv[1]

			#eg reboot if you send the reboot command
			if "{}".format(text).find("reboot") > -1 :
				subprocess.call("reboot", shell=True)


				# if set gpoio high ..
			elif "{}".format(text).find("gpio 21 high") > -1:
				import RPi.GPIO as GPIO
				GPIO.setmode(GPIO.BCM)
				GPIO.setwarnings(False)
				GPIO.setup(21, GPIO.OUT)
				GPIO.output(21, True)


except  Exception as e:
		U.logger.log(20,"", exc_info=True)

exit(0)
