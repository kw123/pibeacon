#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 3 2016
# version 0.5 
##
##	check logfiles sizes and manage
from BaseHTTPServer import BaseHTTPRequestHandler

class GetHandler(BaseHTTPRequestHandler):

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
 
    def do_GET(self):
        x = self.wfile.write
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # <--- HTML starts here --->
        x("<html>")
        # <--- HEAD starts here --->
        x("<head>")
        x("<title>enert SID and passcode for your wifi</title>")
        x("</head>")
        # <--- HEAD ends here --->
        # <--- BODY starts here --->
        x("<body>")
        x('<form action = "/cgi-bin/hello_get.cgi" method = "get">'+
         'SID     :  <input type = "text" name = "first_name" value = "" maxlength = "100" /> <br />'+
         'passCode:  <input type = "text" name = "last_name"  value = "" maxlength = "100" />'+
         '<input type = "submit" value = "Submit" />'+
         ' </form>')
        x("</body>")
        # <--- BODY ends here --->
        x("</html>")
        # <--- HTML ends here --->

 
from BaseHTTPServer import HTTPServer

server = HTTPServer(('', 8000), GetHandler)
print 'Starting server, use <Ctrl + F2> to stop'
server.serve_forever()
