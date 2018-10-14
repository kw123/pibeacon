#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 3 2016
# version 0.5 
##
##	check logfiles sizes and manage
import	os, sys

homeDir = "/home/pi/pibeacon/"
logDir	= "/var/log/"
name   = sys.argv[1]
maxSize = int(sys.argv[2])

try:
	fn= logDir+name
	#print " checkLogfile "+ fn
	if os.path.isfile(fn+".log"):
		fs = os.path.getsize(fn+".log")
		#print "fs: ", fs
		if fs> maxSize:
			if os.path.isfile(fn+"-1.log"):
				os.remove(fn+"-1.log")
			os.rename(fn+".log",fn+"-1.log")

	if os.path.isfile(homeDir+"errlog"):
		if os.path.getsize(homeDir+"errlog")> 10000:
			if os.path.isfile(homeDir+"errlog-1"):
				os.remove(homeDir+"errlog-1")
			os.rename(homeDir+"errlog",homeDir+"errlog-1")
except	Exception, e:
	print u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)

