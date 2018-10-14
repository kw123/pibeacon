#!/usr/bin/ python
homeDir = "/home/pi/pibeacon/"
logDir	= "/var/log/"
import	sys, os, subprocess, copy
import	time,datetime
from PIL import ImageFont, ImageDraw, Image
import json
	
############# oled import ####################################
	
# by Karl Wachs
# oct 3 2016
# version 0.2
##
##	 convert png files to display format
#
##


def toLog(lvl,msg):
		global debug
		if lvl<debug :
			f=open(logDir+"convert.log","a")
			f.write(datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" "+msg+"\n")
			f.close()
def readParams():
		global debug
		f=open(homeDir+"parameters","r")
		try:	inp =json.loads(f.read())
		except: return
		f.close()
		if u"debugRPI"			in inp:	 debug=				int(inp["debugRPI"]["debugRPICALL"])

######### main	########

debug=0
readParams()

try:
	myPID		= str(os.getpid())
	xxx			= sys.argv[1]
	toLog(1, xxx )
	im = Image.open("/home/pi/pibeacon/displayfiles/"+xxx)
	out = im.convert("1")
	out.save("/home/pi/pibeacon/displayfiles/"+xxx, "PNG")
except	Exception, e:
	toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

		
sys.exit(0)		   
