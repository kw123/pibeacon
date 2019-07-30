#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##	 read output and GPIO OUTPUT and send http to indigo with data
#
#	 GPIO pins as OUTPUTs: GPIO:but#	 ={"27":"0","22":"1","25":"2","24":"3","23":"4","18":"5"}

##

import	sys, os, subprocess, copy
import	time,datetime
import	json
import	RPi.GPIO as GPIO  

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "OUTPUTgpio"



def readParams():
		global output
		global INPgpioType,OUTPUTlastvalue
		global oldRaw, lastRead


		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw
		oldoutput		  = output

		U.getGlobalParams(inp)
		if "output"			in inp : output =				(inp["output"])
		if "debugRPI"		in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPIOUTPUT"])


		restart = False
			
		if "OUTPUTgpio-1-ONoff" not in output:
			print "OUTPUTgpio-1-ONoff not in output" 
			exit()
				
		if restart:
			U.restartMyself(reason="new parameters")


	   




global output
global output,lastGPIO
global oldRaw, lastRead
oldRaw				= ""
lastRead			= 0


###################### constants #################

####################  OUTPUT gios   ...allrpi	  only rpi2 and rpi0--
OUTPUTlastvalue	  = ["-1" for i in range(100)]
#####################  init parameters that are read from file 
U.setLogging()

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# old old instances of myself if they are still running


outp			  = G.program
output			  = {}
sList			  = ""
loopCount		  = 0

U.logger.log(30, "starting "+G.program+" program")

readParams()


G.lastAliveSend		= time.time()
# set alive file at startup


lastData		= {}

#print "shortWait",shortWait	 

if U.getIPNumber() > 0:
	U.logger.log(30," output no ip number  exiting ")
	time.sleep(10)
	exit()


lastMsg = time.time()
quick  = 0
qCount = 0

G.tStart = time.time() 
lastRead = time.time()
shortWait =0.5

while True:
	try:
		data0 = {} 
		tt= time.time()
		for out in output:
			if out != "OUTPUTgpio-1-ONoff": continue
			for devId in output[out]:
				if output[out][devId] =="": continue
				if "gpio" not in output[out][devId][0]: continue
				gpio = output[out][devId][0]["gpio"]
				data0[devId]={}
				if subprocess.Popen("gpio -g read "+gpio,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].strip("\n").strip("\r") =="1" : 
					data0[devId]={"actualGpioValue":"high"}
				else: 
					data0[devId]={"actualGpioValue":"low"}
				
		if	data0 != {}:
			if data0 != lastData or (tt-lastMsg > G.sendToIndigoSecs) or quick: 
				lastMsg=tt
				lastData=copy.copy(data0)
				data  = {"outputs":{"OUTPUTgpio-1-ONoff":data0}}
				U.sendURL(data)

		quick = U.checkNowFile(G.program)
		time.sleep(shortWait)

		if time.time()- lastRead > 90:
			readParams()
			lastRead = time.time()

		if loopCount%100==0:
			U.echoLastAlive(G.program)

		loopCount+=1
				
	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)


sys.exit(0)
