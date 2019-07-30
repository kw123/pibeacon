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
			U.logger.log(40,"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e)+"   html data", data)
			return 
		#print "webserverSTATUS", data
		x('<!DOCTYPE html>')
		x('<html>')
		x('<style> a:link { color: green;  background-color: transparent; text-decoration: none; } </style>')
		x('<meta http-equiv="Pragma" content="no-cache">')
		x('<meta http-equiv="Expires" content="-1″>')
		x('<meta http-equiv="CACHE-CONTROL" content="NO-CACHE">')
		x('<meta http-equiv="refresh" content="30"">')
		x('<head style="background-color:rgb(0, 50,50);"> ')
		x('   <style> a:link { color: green;  background-color: transparent; text-decoration: none; } </style>')
		x('</head>')
		x('<body style="background-color:rgb(30, 0,30); color:rgb(150, 150,150); font-family:Courier;">')
		x(	'<b>'+data[0]+'</b><br>')
		for nn in range(1,len(data)):
			x(	data[nn] +'<br>')
		x(	'</body>')
		x('</html>')
 
global pid, dataFile
G.program= "webserverSTATUS"
U.setLogging()

dataFile	= G.homeDir+"temp/showOnWebServer"
try:
	ipNumber	= sys.argv[1]
	port		= int(sys.argv[2])
	dataFile	= sys.argv[3]
except: 
	U.logger.log(50,"Starting web server not working, no ip port # given, command:{}".format(sys.argv))
	exit()
U.logger.log(50,"Starting web server with IP#:{}:{}  dataFile file:{}".format(ipNumber, port, dataFile))

pid =  os.getpid()

U.killOldPgm(str(pid),"webserverSTATUS.py")
time.sleep(0.5)


server = HTTPServer(('', port), GetHandler)
U.logger.log(30,"Starting web server, access at {}:{}".format(ipNumber,port))
server.serve_forever()
