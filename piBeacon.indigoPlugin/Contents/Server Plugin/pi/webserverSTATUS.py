#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 3 2016
# version 0.5 
##
##	check logfiles sizes and manage
import urllib
import json
import os, sys 
import time
import piBeaconUtils   as U
import piBeaconGlobals as G
import sys

from http.server import BaseHTTPRequestHandler, HTTPServer

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

		data = ""
		try:
			f = open(dataFile,"r")
			data = f.read()
			f.close()
		except Exception as e:
			U.logger.log(30,"", exc_info=True)
			return 
		if len(data) < 2: 
			U.logger.log(40, u"data read {}".format(data))

		x('<!DOCTYPE html>'.encode("utf-8"))
		x('<html>'.encode("utf-8"))
		x('<style> a:link { color: green;  background-color: transparent; text-decoration: none; } </style>'.encode("utf-8"))
		x('<meta http-equiv="Pragma" content="no-cache">'.encode("utf-8"))
		x('<meta http-equiv="Expires" content="-1″>'.encode("utf-8"))
		x('<meta http-equiv="CACHE-CONTROL" content="NO-CACHE">'.encode("utf-8"))
		x('<meta http-equiv="refresh" content="30"">'.encode("utf-8"))
		x('<head style="background-color:rgb(0, 50,50);"> '.encode("utf-8"))
		x('   <style> a:link { color: green;  background-color: transparent; text-decoration: none; } </style>'.encode("utf-8"))
		x('</head>'.encode("utf-8"))
		x('<body style="background-color:rgb(30, 0,30); color:rgb(0, 255,0); font-family:Courier;">'.encode("utf-8"))
		x('<b>'.encode("utf-8"))
		try:
			if len(data) > 0:
				x(data.encode("utf-8"))
		except: 
			U.logger.log(20," web server data {}".format(data) )
		x('</body>'.encode("utf-8"))
		x('</html>'.encode("utf-8"))
 
global pid, dataFile
G.program= "webserverSTATUS"
U.setLogging()

dataFile	= G.homeDir+"temp/webserverSTATUS.show"
try:
	ipNumber	= sys.argv[1]
	port		= int(sys.argv[2])
	dataFile	= sys.argv[3]
except: 
	U.logger.log(30,"Starting web server not working, no ip port # given, command:{}".format(sys.argv))
	exit()
U.logger.log(20,"Starting web server with IP#:{}:{}  dataFile file:{}".format(ipNumber, port, dataFile))

pid =  os.getpid()

U.killOldPgm(str(pid),"webserverSTATUS.py")
time.sleep(0.5)


server = HTTPServer(('', port), GetHandler)
U.logger.log(30,"Starting web server, access at {}:{}".format(ipNumber,port))
server.serve_forever()
