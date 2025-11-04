#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	  --- not implemented yet ..
#
#	 

##

import	sys, os, subprocess, copy
import	time,datetime
import	json

sys.path.append(os.getcwd())
import	psutil
import time

def testIfRunningAndPossibleDelete(testPgm, paramsAnd="", paramsNot="",  pidNotkill=0, kill=False):
	if type(testPgm) != type([]): testIfR = [testPgm]
	else: testIfR = testPgm
	retCode = False

	tt = time.time()
	cmd = "ps -ef | grep '{}' | grep -v grep".format(testPgm)
	ret = (subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode('utf-8'))
	print ("ps {}".format(time.time() - tt))


	tt = time.time()
	procs = {}
	for p in psutil.process_iter():
		cmdline = ' '.join(p.cmdline())
		for xx in testIfR:
			if xx in cmdline:
				procs[p.pid] = {"running":p.is_running(), "cmdline":cmdline, "children":p.children(), "name": p.name()}
	print ("psutil {}".format(time.time() - tt))
	print("list: procs:{}".format(procs))
	return False
	if True:
		for p in psutil.process_iter():
			if p.pid not in procs: continue
			cmdLine = procs[p.pid]["cmdline"]
			#print("checking: pid={}, {} cmdline:{}".format(p.pid, p.pid in procs, procs[p.pid]["cmdline"]))
			for xx in testIfR:
				if xx in cmdLine:
					print("checking: pid={}, children:{}, is_running={},  cmdline:{}".format(p.pid, p.children(), p.is_running(), cmdline))
	
					if paramsAnd !="" and paramsAnd not in cmdLine: 
						print(" reject paramsAnd: {}".format(paramsAnd))
						continue
					if paramsNot !="" and paramsNot in cmdLine: 
						print(" reject paramsNot: {}".format(paramsNot))
						continue
					retCode = True 
					print("{}, cmdline:{}".format(p.pid, cmdLine))
					if kill: 
						try:
							p.terminate()
							#p.wait()
							print("kill:{}".format(p.pid, cmdLine))
						except Exception as e:
							print("excetion: {}".format(e))
							
					
	print ("{}".format(time.time() - tt))
	return retCode
	
print ("retcode:{}".format( testIfRunningAndPossibleDelete("webserverINPUT.py", paramsAnd="sudo", pidNotkill=0, kill =True)  ))
#print ("retcode:{}".format( testIfRunningAndPossibleDelete("webserverINPUT.py", paramsAnd="", pidNotkill=21460, kill =True)  ))