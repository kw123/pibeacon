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
import sys

from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer

class GetHandler(BaseHTTPRequestHandler):

	def do_HEAD(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
 
	def do_GET(self):
		global pid, outPut, outFile
		x = self.wfile.write
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		x('<!DOCTYPE html>')
		x('<html>')

		x(	'<head>')
		x(		'<h3 style="color:rgb(150, 150,150); font-family:Courier; "> Enter SID and pass-code for your wifi </h3>')
		x(	'</head>')

		x(	'<body style="background-color:rgb(90, 90,90); font-family:Courier;"color:rgb(255, 255,255);">')
		x(		'<form action = "/cgi-bin/get_UID_etc.cgi" method = "get">'+
					'SSID......:  <input type = "text" name = "SSID"     value = "do not change" maxlength = "35" /> <br> '+
					'passCode..:  <input type = "text" name = "passCode" value = "do not change" maxlength = "35" />  <br>'+
					'Time Zone.:  <select name="timezone">'+
						'<option value="99">do not change time zone</option>'+
						'<option value="12">Pacific/Auckland(+12)</option>'+
						'<option value="11">Pacific/Pohnpei (+11)</option>'+
						'<option value="10">Australia/Melbourne (+10)</option>'+
						'<option value="9">Asia/Tokyo (+9)</option>'+
						'<option value="8">Asia/Shanghai (+8)</option>'+
						'<option value="7">Asia/Saigon (+7)</option>'+
						'<option value="6">Asia/Dacca (+6)</option>'+
						'<option value="5">Asia/Karachi (+5)</option>'+
						'<option value="4">Asia/Dubai (+4)</option>'+
						'<option value="3">/Europe/Moscow (+3)</option>'+
						'<option value="2">/Europe/Helsinki (+2)</option>'+
						'<option value="1">Central-EU (+1)</option>'+
						'<option value="0">UK (GMT) </option>'+
						'<option value="-5">US-East Coast (-5)</option>'+
						'<option value="-6">US-Central (-6)</option>'+
						'<option value="-7">US-Mountain< (-7)/option>'+
						'<option value="-8">US-West Coast(-8)</option>'+
						'<option value="-9">US-Alaska (-9)</option>'+
						'<option value="-10">Pacific/Honolulu (-10)</option>'+
						'<option value="-11">US-Samoa (-11)</option>'+
					'</select> <br>'+
					'..........: <input type = "submit" value = "Submit" />'+
				   '</form>')
		x(	'</body>')
		x('</html>')

		items =  urlparse.urlparse(self.path)
		if len(items) < 5: 		 return 
		if len(items.query) < 5: return 
		items = urllib.unquote(items.query)
		items = (items).split("&")

		if len(items) != len(outPut): return
		
		for item1 in items:
			item = item1.split("=")
			if len(item) !=2: continue
			if   item[0] in outPut: 	outPut[item[0]] = item[1]
		one = False
		for item in outPut:
			if outPut[item] != "": one = True 
		if not one: return 
		f=open(outFile,"w")
		f.write(json.dumps(outPut))
		f.close()
		##os.system("kill -9 "+str(pid) )
		
		

 

global pid, outPut, outFile
outFile	= G.homeDir+"temp/webparameters.Input"
outPut	= {"SSID":"", "timezone":"","passCode":""}
port = 8000


try:
	port    = int(sys.argv[1])
	outFile = sys.argv[2]
except: pass


f=open( G.homeDir+"ipAddress","r")
ipNumber = f.read()
f.close()
pid =  os.getpid()

if os.path.isfile(outFile):
	os.system("rm "+outFile)

U.killOldPgm(str(pid),"webserverINPUT.py")
time.sleep(0.5)


server = HTTPServer(('', port), GetHandler)
print "Starting server, access at "+ipNumber+":"+str(port)
server.serve_forever()
