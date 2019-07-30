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
		global pid, defaults, defaultsSunDial, outFile, sunDialFile
		x = self.wfile.write
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		x('<!DOCTYPE html>')
		x('<html>')
		x('<meta http-equiv="Pragma" content="no-cache">')
		x('<meta http-equiv="Expires" content="-1″>')
		x('<meta http-equiv="CACHE-CONTROL" content="NO-CACHE">')
		x(	'<head>')
		x(		'<h3 style="color:rgb(150, 150,150); font-family:Courier; "><b>Enter parameters, eg SID and pass-code for your WiFi, ... </b></h3>')
		x(	'</head>')

		x(	'<body style="background-color:rgb(50, 50,50); font-family:Courier; color:rgb(205, 205,205);">')
		x(		'<form action = "/cgi-bin/get_UID_etc.cgi" method = "get">'+
					'<hr size=4 width="100%">'+
					'SSID................:  <input type = "text" name = "SSID"     value = "do+not+change" maxlength = "35" /> <br> '+
					'passCode............:  <input type = "text" name = "passCode" value = "do+not+change" maxlength = "35" />  <br>'+
					'<hr width="70%">'+
					'Time Zone...........:  <select name="timezone">'+
						'<option value="99">do+not+change+time+zone</option>'+
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
					'</select> <br>')
		if sunDialFile !="":
			x(		'<hr width="70%">')
			x(		'<p><b>SUNDIAL.............:  enter sundial parameters below:</b></p>')
			x(		'= Settings for light, direction, down/shadow, 12/24 hour clock<br>')
			x(		'direction /12/24....:  <select name="mode">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="mode:light">light straight Down</option>'+
						'<option value="mode:shadow">use normal shadow mode</option>'+
						'<option value="mode:12">use 12 hour clock</option>'+
						'<option value="mode:24">use 24 hour clock</option>'+
					'</select> <br>')
			x(		'led factor..........:  <select name="led">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="led:0.15">0.15  dark </option>'+
						'<option value="led:0.2">0.2</option>'+
						'<option value="led:0.3">0.3</option>'+
						'<option value="led:0.5">0.5</option>'+
						'<option value="led:0.7">0.7</option>'+
						'<option value="led:1.0">1.0 normal </option>'+
						'<option value="led:1.5">1.5</option>'+
						'<option value="led:2.0">2.0</option>'+
						'<option value="led:3.0">3.0</option>'+
						'<option value="led:5.0">5.0</option>'+
						'<option value="led:7.5">7.5</option>'+
						'<option value="led:10">10</option>'+
						'<option value="led:15">15</option>'+
						'<option value="led:20">20 bright</option>'+
						'<option value="led:30">30</option>'+
						'<option value="led:50">50</option>'+
						'<option value="led:75">75</option>'+
						'<option value="led:100">100</option>'+
						'<option value="led:150">150</option>'+
						'<option value="led:200">200</option>'+
						'<option value="led:300">300</option>'+
						'<option value="led:500">500  very bright </option>'+
					'</select> <br>')
			x(		'led color...........:  <select name="LED">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="led:200,0,0">red</option>'+
						'<option value="led:0,200,0">green</option>'+
						'<option value="led:0,0,200">blue</option>'+
						'<option value="led:70,90,80">pale blue</option>'+
						'<option value="led:0,130,130">saphire</option>'+
						'<option value="led:130,130,0">yellow</option>'+
						'<option value="led:150,100,0">orange</option>'+
						'<option value="led:130,0,130">pink</option>'+
						'<option value="led:100,100,100">white</option>'+
					'</select> <br>')
			x(		'light sensor Norm...: <select name="lightSensNorm">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="sensorNorm:4500;">  4500 most sensitive </option>'+
						'<option value="sensorNorm:6000;">  6000 </option>'+
						'<option value="sensorNorm:9000;">  9000 </option>'+
						'<option value="sensorNorm:12000;">12000 default </option>'+
						'<option value="sensorNorm:18000;">18000 </option>'+
						'<option value="sensorNorm:24000;">24000 least sensitive</option>'+
					'</select> <br>')
			x(		'<br>')

			x(		'= Calibrations<br>')
			x(		'goto ...............: <select name="goto">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="goNow">goto now = current time </option>'+
						'<option value="led:80,80,80;gohh:0;sleep:5go;hh:3;sleep:5;gohh:6;sleep:5;gohh:9;sleep:5;goNow;">goto hour= 0 3 6 9 </option>'+
						'<option value="led:80,80,80;gohh:0;sleep:5go;hh:6;sleep:5;gohh:12;sleep:5;gohh:18;sleep:5;goNow;">goto hour= 0 6 12 18 </option>'+
					'</select> <br>')
			x(		'offset of arm Pos...: <input type = "text" name = "offsetArm"     value = "do+not+change" maxlength = "4"   /> <br>')

			x(		'calibrate L/R.......: <select name="leftrightcalibration">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="leftrightcalibration" >will start a left right calibration</option>'+
					'</select> <br>')

			x(		'calibrate arm.......: <select name="calibrate">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="calibrate:0" >a) first move arm to 0, then press submit </option>'+
						'<option value="calibrate:6" >b) first move arm to 6, then press submit </option>'+
						'<option value="calibrate:12">c) first move arm to 12, then press submit </option>'+
						'<option value="calibrate:ct">d) first move arm to current time, then press submit </option>'+
					'</select> <br>')
			x(		'<br>')
			x(		'= Raw commands .. experts only!!<br>')
			x(		'command ............: <input type = "text" name = "cmd"     value = "do+not+change" maxlength = "100" /> <br> ')
			x(		'commands avail:<br>')
			x(		'-  restart;reset;shutdown;<br>')
			x(		'-  goStart;goNow;goZero;goHH:hh;goSteps:x;<br>')
			x(		'-  LED:on/off/up/down/x/r,g,b;sleep:x;lightSensNorm:x;<br>')
			x(		'-  mode:shadow/light/12/24;<br>')
			x(		'-  leftrightcalibration;getBoundaries;<br>')
			x(		'-  offsetArm:x;calibrate:currentTime/hh;timeshift:hh,<br>')
			x(		'-  / = options -  hh = hour - x,r,g,b = numbers - ; = sep between cmds')

		x(		'<hr width="70%">')
		x(			'then--------------==> <input type = "submit" value = "Submit" />'
				'<hr size=4 width="100%">'+
				   '</form>')
		x(	'</body>')
		x('</html>')

		items =  urlparse.urlparse(self.path)
		if len(items) < 5: 		 return 
		if len(items.query) < 5: return 
		items = urllib.unquote(items.query)
		items = (items).split("&")
		U.logger.log(20,"1. #items:{}, #ofparamets expected:{}; items{}".format(len(items),len(defaultsSunDial)+ len(defaults), items))

	
		output = {}
		sunDial = ""
		for item1 in items:
			item = item1.split("=")
			if len(item) !=2: continue
			if   item[0] in defaults and item[1] != defaults[item[0]]: 
				output[item[0]] = item[1]
			if   item[0] in defaultsSunDial and item[1] != defaultsSunDial[item[0]]: 
				sunDial += item[1]+";"
		sunDial =  sunDial.strip(";")
		U.logger.log(20,"2. output{} + sunDial:{}".format(output, sunDial))

		for item in output:
			if output[item] != "":
				f=open(outFile,"w")
				f.write(json.dumps(output))
				f.close()
				break

		if sunDial !="" and sunDialFile !="":
			U.logger.log(20,"writing to sundial file{}".format(sunDial))
			f=open(sunDialFile,"w")
			f.write(sunDial)
			f.close()

		##os.system("kill -9 "+str(pid) )
		
		

 

global pid, defaults, defaultsSunDial, outFile, sunDialFile
outFile	= G.homeDir+"temp/webparameters.Input"
sunDialFile = ""
port = 8000

G.program= "webserverINPUT"
U.setLogging()

try:
	ipNumber	= sys.argv[1]
	port		= int(sys.argv[2])
	outFile		= sys.argv[3]
	defaults	= {"SSID":"do+not+change", "timezone":"99","passCode":"do+not+change"}
	defaultsSunDial	= {"mode":"-1","led":"-1","LED":"-1","calibrate":"-1","lightSensNorm":"-1","offsetArm":"do+not+change","goto":"-1","cmd":"do+not+change","leftrightcalibration":"-1"}
	if len(sys.argv) ==5:
		sunDialFile = sys.argv[4]
except: 
	U.logger.log(50,"Starting web server not working, no ip port # given, command:{}".format(sys.argv))
	exit()
U.logger.log(30,"Starting web server with IP#:{}:{}  output file:{}, sundial:{}".format(ipNumber, port, outFile, sunDialFile))

pid =  os.getpid()

if os.path.isfile(outFile):
	os.system("rm "+outFile)

U.killOldPgm(str(pid),"webserverINPUT.py")
time.sleep(0.5)


server = HTTPServer(('', port), GetHandler)
U.logger.log(30,"Starting server, access at {}:{}".format(ipNumber,port))
server.serve_forever()
