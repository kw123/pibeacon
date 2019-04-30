#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 3 2016
# version 0.5 
##
##	check logfiles sizes and manage
import urllib
import json
import urlparse
import os, sys 
import time
import piBeaconUtils   as U
import piBeaconGlobals as G
import sys

from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer

class GetHandler(BaseHTTPRequestHandler):

	def do_HEAD(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
 
	def do_GET(self):
		global pid, dataFile
		x = self.wfile.write
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()

		data ={}
		try:
			f= open(dataFile,"r")
			ddd = f.read()
			data = json.loads(ddd)
			f.close()
		except	Exception, e:
			print  u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)+"   bad sensor data", data
			return 
		#print "webserverSTATUS", data
		x('<!DOCTYPE html>')
		x('<html>')
		x(	'<head style="background-color:rgb(50, 50,50);"> </head>')
		x(	'<body style="background-color:rgb(50, 50,50); color:rgb(150, 150,150); font-family:Courier;">')
		x(		'<b>'+data[0]+'</b><br>')
		for nn in range(1,len(data)):
			x(	data[nn] +'<br>')
		x(	'</body>')
		x('</html>')
 
global pid, dataFile
dataFile	= G.homeDir+"temp/showOnWebServer"
port 		= 80
try:
	port     = int(sys.argv[1])
	dataFile = sys.argv[2]
except: pass


f=open( G.homeDir+"ipAddress","r")
ipNumber = f.read()
f.close()
pid =  os.getpid()

U.killOldPgm(str(pid),"webserverSTATUS.py")
time.sleep(0.5)


server = HTTPServer(('', port), GetHandler)
print "Starting web server, access at "+ipNumber+":"+str(port)
server.serve_forever()
