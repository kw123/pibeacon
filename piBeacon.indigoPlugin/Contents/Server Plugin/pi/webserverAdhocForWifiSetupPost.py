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
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
import cgi

class GetHandler(BaseHTTPRequestHandler):

	def do_HEAD(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()

	def do_POST(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		return 
		x = self.wfile.write
		x('<!DOCTYPE html>')
		x('<html>')

		x(	'<head>')
		x(		'<h3 style="color:rgb(150, 150,150); font-family:Courier; "> Enter SID and pass-code for your wifi </h3>')
		x(	'</head>')

		x(	'<body style="background-color:rgb(90, 90,90); font-family:Courier;"color:rgb(255, 255,255);">')
		x(		'<form action = "/uid" method = "post">'+
					'SID.......:  <input type = "text" name = "SID"	  value = "" maxlength = "35" /> <br> '+
					'passCode..:  <input type = "text" name = "passCode" value = "" maxlength = "35" />  <br>'+
					'Time Zone.:  <select name="timezone">'+
						'<option value="11">Pacific/Auckland(+12)</option>'+
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
			
		# Parse the form data posted
		form = cgi.FieldStorage( fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD':'POST', 'CONTENT_TYPE':self.headers['Content-Type'], })
		try:
			for field in form.keys():  ## does not work: not indexable
				field_item = form[field]
				print( unicode(field) +":::"+unicode(field_item)+"\n")
		except  Exception, e:
			print (u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )
		msg = unicode(form)
			
	 #			self.request.close()


	def do_GETx(self):
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
					'SID.......:  <input type = "text" name = "SID"	  value = "" maxlength = "35" /> <br> '+
					'passCode..:  <input type = "text" name = "passCode" value = "" maxlength = "35" />  <br>'+
					'Time Zone.:  <select name="timezone">'+
						'<option value="11">Pacific/Auckland(+12)</option>'+
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
		print outPut
		for item in outPut:
			if outPut[item] == "": return 
		f=open(outFile,"w")
		f.write(json.dumps(outPut))
		f.close()
		os.system("kill -9 "+str(pid) )
		
		

 

global pid, outPut, outFile
outFile	= "/home/pi/pibeacon/webparameters.dat"
outPut	= {"SID":"", "timezone":"","passCode":""}
port = 8000


os.system("rm "+outFile)
pid =  os.getpid()

server = HTTPServer(('', port), GetHandler)
print 'Starting server, use <Ctrl + F2> to stop'
server.serve_forever()
