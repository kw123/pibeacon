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
G.debug = 0

############# oled import ####################################
	
# by Karl Wachs
# oct 3 2016
# version 0.2
##
##	 convert png files to display format
#
##


def readParams():
		global debug
		f=open(homeDir+"parameters","r")
		try:	inp =json.loads(f.read())
		except: return
		f.close()
		if u"debugRPI"			in inp:	 debug=				int(inp["debugRPI"]["debugRPICALL"])

######### main	########

debug=0
U.setLogging()
readParams()

try:
	myPID		= str(os.getpid())
	xxx			= sys.argv[1]
	U.logger.log(10, xxx )
	im = Image.open("/home/pi/pibeacon/displayfiles/"+xxx)
	out = im.convert("1")
	out.save("/home/pi/pibeacon/displayfiles/"+xxx, "PNG")
except	Exception, e:
	U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

		
sys.exit(0)		   
