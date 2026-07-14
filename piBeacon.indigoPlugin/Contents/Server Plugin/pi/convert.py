#!/usr/bin/ python
homeDir = "/home/pi/pibeacon/"
logDir	= "/var/log/"
import	sys, os, subprocess, copy
import	time,datetime
from PIL import ImageFont, ImageDraw, Image
import json
sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "ccs811"

############# oled import ####################################
	
# by Karl Wachs
# oct 3 2016
# version 0.2
##
##	 convert png files to display format
#
##


def readParams():
		"""Reads the JSON parameters file from the home directory and applies the parsed settings via U.getGlobalParams; silently returns if the file content is not valid JSON.

		Inputs:
		    None.
		Outputs:
		    None: Loads global parameters from the parameters file; no return value
		"""
		global debug
		f=open(homeDir+"parameters","r")
		try:	inp =json.loads(f.read())
		except: return
		f.close()
		U.getGlobalParams(inp)

######### main	########

U.setLogging()
readParams()
U.setLogLevel()

try:
	myPID		= str(os.getpid())
	xxx			= sys.argv[1]
	U.logger.log(10, xxx )
	im = Image.open("/home/pi/pibeacon/displayfiles/"+xxx)
	out = im.convert("1")
	out.save("/home/pi/pibeacon/displayfiles/"+xxx, "PNG")
except Exception as e:
	U.logger.log(30,"", exc_info=True)

try: 	G.sendThread["run"] = False; time.sleep(1)
except: pass
		
sys.exit(0)		   
