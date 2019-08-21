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
		global pid, defaults, defaultssundial, outFile, sundialFile
		global lastCommand, ignoreCashedEntry
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
		x(		'<h3 style="background-color:rgb(30, 0, 30); color:rgb(0, 255, 0); font-family:Courier; "><b>Enter parameters, eg SID and pass-code for your WiFi, ... </b></h3>')
		x(	'</head>')

		x(	'<body style="background-color:rgb(30, 0, 30); font-family:Courier; color:rgb(0, 255, 0);">')
		x(		'<form action = "/cgi-bin/get_UID_etc.cgi" method = "get" id="myForm">'+
					'<hr size=4 width="100%">'+
					'SSID................:  <input type = "text" name = "SSID"     value = "do+not+change" maxlength = "35" /> <br> '+
					'passCode............:  <input type = "text" name = "passCode" value = "do+not+change" maxlength = "35" />  <br>')
		x(			'. . . . . . . . . . .<br>')
		x(			'Time Zone...........:  <select name="timezone">'+
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
		x(			'<br>')
#		x(			'then--------------==> <input type = "submit" value = "Submit General Parameters" />')
		x(			'then--------------==> <input type="button" onclick="submit()" value="Submit General Parameters"/>')
		if sundialFile !="":
			x(		'<hr align="left" width="70%" >')
			x(		'<p><b>SUNDIAL.............:  enter sundial parameters below:</b></p>')
			x(		'= Settings for light, direction, down/shadow, 12/24 hour<br>')
			x(		'direction /12/24....:  <select name="mode">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="mode:d">light straight Down</option>'+
						'<option value="mode:n">use normal shadow mode</option>'+
						'<option value="mode:12">use 12 hour clock</option>'+
						'<option value="mode:24">use 24 hour clock</option>'+
					'</select> <br>')
			x(		'led slope...........:  <select name="led">'+
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
						'<option value="led:220,0,0">red</option>'+
						'<option value="led:30,0,0">red dark</option>'+
						'<option value="led:0,220,0">green</option>'+
						'<option value="led:0,30,0">green dark</option>'+
						'<option value="led:0,0,220">blue</option>'+
						'<option value="led:0,0,30">blue dark</option>'+
						'<option value="led:0,120,120">saphire</option>'+
						'<option value="led:120,120,0">yellow</option>'+
						'<option value="led:150,100,0">orange</option>'+
						'<option value="led:130,0,130">pink</option>'+
						'<option value="led:30,30,30">grey</option>'+
						'<option value="led:100,100,100">white</option>'+
					'</select> <br>')
			x(		'led off..on hours...:  <select name="lightoff">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="lightoff:0,0">on</option>'+
						'<option value="lightoff:22,6">off between 22..6</option>'+
						'<option value="lightoff:23,6">off between 23..6</option>'+
						'<option value="lightoff:24,6">off between 24..6</option>'+
						'<option value="lightoff:22,7">off between 22..7</option>'+
						'<option value="lightoff:23,7">off between 23..7</option>'+
						'<option value="lightoff:24,7">off between 24..7</option>'+
						'<option value="lightoff:22,8">off between 22..8</option>'+
						'<option value="lightoff:23,8">off between 23..8</option>'+
						'<option value="lightoff:24,8">off between 24..8</option>'+
					'</select> <br>')
			x(		'light sensor slope..: <select name="lightSensor">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="lightSensor:0.016;">*64 highest</option>'+
						'<option value="lightSensor:0.031;">*32 </option>'+
						'<option value="lightSensor:0.063;">*16 </option>'+
						'<option value="lightSensor:0.125;>"*8 </option>'+
						'<option value="lightSensor:0.25;">*4 </option>'+
						'<option value="lightSensor:0.50;">*2 </option>'+
						'<option value="lightSensor:1.00;">normal default </option>'+
						'<option value="lightSensor:2.00;">/2</option>'+
						'<option value="lightSensor:4.00;">/4</option>'+
						'<option value="lightSensor:8.00;">/8</option>'+
						'<option value="lightSensor:16.00;">/16</option>'+
						'<option value="lightSensor:32.00;">/32</option>'+
						'<option value="lightSensor:64.00;">/64 lowest</option>'+
					'</select> <br>')
			x(		'<br>')


			x(		'= Calibrations<br>')
			x(		'move arm to.........: <select name="goto">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="goNow">goto now = current time </option>'+
						'<option value="led:80,80,80;gohh:0;sleep:3;gohh:3;sleep:3;gohh:6;sleep:3;gohh:9;sleep:3;gohh:11;sleep:3;goNow;">goto hour= 0 3 6 9 11 </option>'+
						'<option value="led:80,80,80;gohh:0;sleep:3;gohh:3;sleep:3;gohh:12;sleep:3;gohh:18;sleep:3;gohh:23;sleep:3;goNow;">goto hour= 0 6 12 18 23 </option>'+
					'</select> <br>')
			x(		'adjust arm offset...: <select name="offsetArm">'+
						'<option value="0">do+not+change</option>'+
						'<option value="offsetArm:-200">200 click left ~ 1/4 turn</option>'+
						'<option value="offsetArm:-100">100 click left</option>'+
						'<option value="offsetArm:-50">50 click left</option>'+
						'<option value="offsetArm:-20">20 click left ~-38 minutes</option>'+
						'<option value="offsetArm:-10">10 click left </option>'+
						'<option value="offsetArm:-9">9 click left</option>'+
						'<option value="offsetArm:-8">8 click left</option>'+
						'<option value="offsetArm:-7">7 click left</option>'+
						'<option value="offsetArm:-6">6 click left</option>'+
						'<option value="offsetArm:-5">5 click left</option>'+
						'<option value="offsetArm:-4">4 click left</option>'+
						'<option value="offsetArm:-3">3 click left</option>'+
						'<option value="offsetArm:-2">2 click left</option>'+
						'<option value="offsetArm:-1">1 click left ~ -2 minutes</option>'+
						'<option value="offsetArm:1">1 click right ~ +2 minutes</option>'+
						'<option value="offsetArm:2">2 click right</option>'+
						'<option value="offsetArm:3">3 click right</option>'+
						'<option value="offsetArm:4">4 click right</option>'+
						'<option value="offsetArm:5">5 click right</option>'+
						'<option value="offsetArm:6">6 click right</option>'+
						'<option value="offsetArm:7">7 click right</option>'+
						'<option value="offsetArm:8">8 click right</option>'+
						'<option value="offsetArm:9">9 click right</option>'+
						'<option value="offsetArm:10">10 click right</option>'+
						'<option value="offsetArm:10">20 click right ~+38 minutes</option>'+
						'<option value="offsetArm:10">50 click right</option>'+
						'<option value="offsetArm:10">100 click right</option>'+
						'<option value="offsetArm:10">200 click right ~ 1/4 turn</option>'+
					'</select> <br>')

			x(		'calibrate arm.......: <select name="calibrate">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="calibrate:12">move arm to 12, then submit; must be 24, normal light mode)</option>'+
					'</select> <br>')
			x(		'<br>')
			x(		'set speed to (demo).: <select name="speed">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="speed:1;gohh:0;sleep:1;gonow"   > normal speed </option>'+
						'<option value="speed:60"  > 1 minute in 1 secs </option>'+
						'<option value="speed:120" > 2 minutes in 1 sec ~ one move/sec</option>'+
						'<option value="speed:300" > 5 minutes in 1 sec, one day in 288 secs </option>'+
						'<option value="speed:600" > 10 minutes in 1 sec, one day in 144 secs </option>'+
						'<option value="speed:1200"> 1 hour in 3 sec, one day in 72 secs</option>'+
					'</select> <br>')
			x(		'<br>')
			x(		're-boot shutdown etc: <select name="re">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="restart"  >soft restart clock </option>'+
						'<option value="reboot"   >powercycle clock </option>'+
						'<option value="shutdown" >shutdown clock, wait 30 secs before power off switch</option>'+
						'<option value="halt"     >halt clock, wait 30 secs before power off switch</option>'+
					'</select> <br>')
			x(		'enable auto update..: <select name="autoupdate">'+
						'<option value="-1">do+not+change</option>'+
						'<option value="E" >Enable</option>'+
						'<option value="D" >Disable</option>'+
					'</select> <br>')
			x(		'<br>')
			x(		'= Raw commands ... experts only!<br>')
			x(		'command .........: <input type = "text" name = "cmd"     value = "none" maxlength = "100" /> <br> ')
			x(		'-restart.........: (soft) restarts the clock<br>')
			x(		'-reboot..........: power cycle the clock<br>')
			x(		'-shutdown........: power down the clock - shutdown<br>')
			x(		'-halt............: power down the clock - halt<br>')
			x(		'-reset;reset.....: resets the params, needs calibration<br>')
			x(		'-goNow...........: go to current time<br>')
			x(		'-goHH:hh.........: go to hour:0-24<br>')
			x(		'-goSteps:x.......: go x steps (0..+-800) forward/backwards<br>')
			x(		'-speed:x.........: set demo speed, eg x= 1=normal, 50, 100 .. <br>')
			x(		'-LED:up/down.....: increase / decrease LED intensity */ 2<br>')
			x(		'-LED:x...........: set LED slope to 0-500<br>')
			x(		'-LED:r,g,b.......: set LED RGB values to 0-100,0-100,0-100<br>')
			x(		'-lightoff:x,y....: set LED off between hours [x,y]<br>')
			x(		'-lightSensor:x...: set light sensor slope to 0.01-100<br>')
			x(		'-sleep:x.........: stop any move for x secs <br>')
			x(		'-mode:N/D........: set mode to Normal, or light straight Down<br>')
			x(		'-mode:12/24......: sets mode to 12 hour or 24 hour mode<br>')
			x(		'-getBoundaries...: find absolute cable boundaries<br>')
			x(		'-offsetArm:x.....: adjust rel offset to current <br>')
			x(		'-calibrate:N/hh..: move arm to pos. Now or hour, then Submit<br>')
			x(		'-autoupdate:E/D..: Enable/Disable auto update download)<br>')
			x(		'-timeshift:hh....: change time by hh hours (for testing)<br>')
			x(		'lower case ok, command concatenation w. ; eg LED:50;sleep:5')
			x(		'<br>')
			x(		'<br>')
##			x(		'then--------------==> <input type = "submit" value = "Submit SUNDIAL Parameters" />')
			x(		'then--------------==> <input type="button" onclick="submit()" value="Submit SUNDIAL Parameters"/>')
		x(		'<hr size=4 width="100%">')
		x(		'</form>')
		x(		'<script>')
		x(		'	function submit() {')
		x(		'	  /*Put all the data posting code here*/')
		x(		'	 document.getElementById("myForm").reset();')
		x(		'		}')
		x(		'</script>')
 
		x(	'</body>')
		x('</html>')

		items =  urlparse.urlparse(self.path)
		if len(items) < 5: 		 return 
		if len(items.query) < 5: return 
		items = urllib.unquote(items.query)
		items = (items).split("&")
		U.logger.log(10,"1. #items:{}, #ofparamets expected:{}; items{}".format(len(items),len(defaultssundial)+ len(defaults), items))

	
		output = {}
		sundial = ""
		for item1 in items:
			item = item1.split("=")
			if len(item) !=2: continue
			# skip input after start to not repeat submit of last cashed values
			if False:
				if item[0] not in lastCommand:
					lastCommand[item[0]] = ""
					continue
			lastCommand[item[0]] = item[1] 
			if   item[0] in defaults and item[1] != defaults[item[0]] and len(item[1]) > 0: 
				output[item[0]] = item[1]
			if   item[0] in defaultssundial and item[1] != defaultssundial[item[0]] and len(item[1]) > 0: 
				sundial += item[1]+";"
		sundial =  sundial.strip(";")
		U.logger.log(20,"2. general:{} + sundial:{}".format(output, sundial))

		for item in output:
			if output[item] != "":
				f=open(outFile,"w")
				f.write(json.dumps(output))
				f.close()
				break

		if sundial !="" and sundialFile !="":
			U.logger.log(10,"writing to sundial file:>>{}<<".format(sundial))
			f=open(sundialFile,"w")
			f.write(sundial)
			f.close()

		##os.system("kill -9 "+str(pid) )
		
		

 

global pid, defaults, defaultssundial, outFile, sundialFile
global lastCommand, ignoreCashedEntry

lastCommand ={}
outFile	= G.homeDir+"temp/webparameters.input"
sundialFile = ""
port = 8000

G.program= "webserverINPUT"
U.setLogging()

try:
	ipNumber	= sys.argv[1]
	port		= int(sys.argv[2])
	outFile		= sys.argv[3]
	defaults	= {"SSID":"do+not+change", "timezone":"99","passCode":"do+not+change"}
	defaultssundial	= {"autoupdate":"-1","re":"-1","speed":"-1","mode":"-1","led":"-1","LED":"-1","calibrate":"-1","lightSensor":"-1","lightoff":"-1","offsetArm":"0","goto":"-1","cmd":"none","leftrightcalib":"-1"}
	if len(sys.argv) ==5:
		sundialFile = sys.argv[4]
except: 
	U.logger.log(30,"Starting web server not working, no ip port # given, command:{}".format(sys.argv))
	exit()
U.logger.log(20,"Starting web server with IP#:{}:{}  output file:{}, sundial:{}".format(ipNumber, port, outFile, sundialFile))



pid =  os.getpid()

if os.path.isfile(outFile):
	os.system("rm "+outFile)

U.killOldPgm(str(pid),"webserverINPUT.py")
time.sleep(0.5)


server = HTTPServer(('', port), GetHandler)
U.logger.log(30,"Starting server, access at {}:{}".format(ipNumber,port))
server.serve_forever()
