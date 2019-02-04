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
import os
import time
import piBeaconUtils   as U
import piBeaconGlobals as G

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
			data = json.loads(f.read())
			f.close()
		except: 
			return 

		x('<!DOCTYPE html>')
		x('<html>')
		x(	'<head style="background-color:rgb(50, 50,50);"> </head>')
		x(	'<body style="background-color:rgb(50, 50,50); color:rgb(150, 150,150); font-family:Courier;">')
		x(		'<b>SunDial Current status</b><br>')
		for item in data:
			x(	item +'<br>')
		x(	'</body>')
		x('</html>')
 
global pid, dataFile
dataFile	= G.homeDir+"temp/sunDial.status"
port 		= 80
try:
	port     = int(sys.argv[1])
	dataFile = sys.argv[2]
except: pass


f=open( G.homeDir+"ipAddress","r")
ipNumber = f.read()
f.close()
pid =  os.getpid()

U.killOldPgm(str(pid),"/webserverWhenOnline.py")
time.sleep(0.5)


server = HTTPServer(('', port), GetHandler)
print "Starting web server, access at "+ipNumber+":"+str(port)
server.serve_forever()
