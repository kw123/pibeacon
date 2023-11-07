#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
## # p3 prept

##	get sensor values and write the to a file in json format for later pickup, 
##	do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##

import	sys, os, time, json, datetime,subprocess,copy

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "FBHtempshow"


version = 1.0
# =========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensor, output, inpRaw, inp
	global oldRaw, lastRead

	try:

		changed = 0
		inpLast = inp
		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)

		if inp == "": 
			inp = inpLast
			return changed


		if lastRead2 == lastRead: return changed

		lastRead  = lastRead2
		if inpRaw == "error":
			U.checkParametersFile( force = True)
		if inpRaw == oldRaw: return changed
		oldRaw	   = inpRaw
		U.getGlobalParams(inp)
		 
		if "output"					in inp:	 output=			 (inp["output"])
		#### G.debug = 2 
		if False and G.program not in output:
			U.logger.log(30," {} is not in parameters = not enabled, stopping" .format(G.program ))
			exit()

		#U.logger.log(20, ":{}".format())

		return changed

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(10)
		return 3

#################################		 
def checkNewtempfile():
	try:

		#U.logger.log(20," checkNewtempfile: start ".format())
		data, raw = U.readJson(G.homeDir+"temp/Wire18B20.dat")
		if len(raw) < 2: 
			U.logger.log(20," checkNewtempfile: no new data ".format())
			return 


		dy = 32
		y0 = int(dy *.5)
		y = y0 + int(dy *.5)

		font = "Arial.ttf"
		frameTextSize = 30
		tempTextSize = dy -3
		totalFrame = [0,0,1280,800]


		# colors
		colorGrey 			= [40,40,40]
		colorWhite 			= [150,150,150]
		colorHeader 		= [100,100,100]
		colorTempLabel 		= [100,100,100]
		colorTempOK 		= [0,100,0]
		colorTempHIGH		= [100,0,0]
		colorTempLOW		= [0,0,100]
		colorTempBadHigh	= [200,0,0]
		colorTempBadLow		= [0,0,200]
		tempOK 				= [0,200,0]

		# temp limits
		tHighVeryBad 	= 75
		tHighBad 		= 50
		tHigh 			= 24
		tLow  			= 18
		tLowBad  		= 10
		tLowVeryBad  	= 0


		# positons and sizes 
		dateWidth = 60
		datePos = [500,totalFrame[3]-dateWidth-5]

		scaleStart 	= 250
		dxperC	  	= 40
		tposZero  	= 15
		xmax 		= 1000

		theList = []
		for devId in data:
			name = data[devId]["name"].split("_")[1]
			if "temp" not in data[devId]: continue
			for nextT in data[devId]["temp"]:
				for serN in nextT:
					temp = nextT[serN]
					if  temp < tLowVeryBad:
						xpos = scaleStart
						tempText = "--------- bad sensor read   --:{:.1f} < {}".format(temp,tLowVeryBad)
						color= colorTempBadLow

					elif temp > tHighVeryBad:
						xpos = scaleStart
						tempText = "--------- bad sensor to high--:{:.1f} > {}".format(temp, tHighVeryBad)
						color= colorTempBadHigh

					else:
						tempText = "{:.1f}".format(temp)
						xpos = int( scaleStart +  max(0,min(xmax, (temp-tposZero)*dxperC -1.5*tempTextSize)) )
						if   temp > tHighBad: 	color = colorTempBadHigh
						elif temp > tHigh: 		color = colorTempHIGH
						elif temp < tLowBad: 	color = colorTempBadLow
						elif temp < tLow: 		color = colorTempLOW
						else: 					color = tempOK

					theList.append([name, tempText, color ,xpos])

		theList = sorted(theList, key=lambda x: (x[0], x[1], x[2]))
		

		#U.logger.log(20," theList:{}".format(theList))


		out = {"resetInitial": "", "repeat": 100000000,"command":[]}
		out["command"].append({"type":"rectangle", 								"fill": colorGrey, 			"position":totalFrame, 	"display":"wait", 		"reset":[50, 50, 50]})
		for ii in range(6):
				temp = ii*5
				xpos = int(  scaleStart +  max(0,min(xmax, temp*dxperC - tempTextSize)) )
				out["command"].append({"type": "text",	"width":tempTextSize,	"fill":colorTempLabel,	 	"position":[xpos,y0], 	"display": "wait", 		"text":"{}".format(temp+tposZero), "font":font})

		for name, text, color, xpos in theList:
			y += dy
			out["command"].append({"type": "text",		"width":tempTextSize,	"fill":colorTempLabel,		"position":[40,y], 		"display": "wait", 		"text":name, 		"font":font})
			out["command"].append({"type": "text",		"width":tempTextSize,	"fill":color,	 			"position":[xpos,y], 	"display": "wait", 		"text":text, 					"font":font})
		out["command"].append({"type":"dateString",  	"width":dateWidth,  	"fill":colorWhite,			"position": datePos,   	"display":"wait", 		"text":"%a, %b  %d, %Y %H:%M:%S", 	"font":font} )
		out["command"].append({"type": "text",			"width":frameTextSize,	"fill":colorHeader,	 		"position":[30,y0], 	"display": "immediate", "text":"Temperatures", 				"font":font })

		outName = G.homeDir+"temp/display.inp"
		#U.logger.log(20,"\n\n out:{}\n outfile: {}\n\n".format(out, outName))
		f = open(outName,"a")
		f.write(json.dumps(out)+"\n")
		f.close()
	

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 



#################################
#################################
#################################
#################################
def fbhexec():
	global sensor, output, inpRaw, lastCl,clockMarks,maRGB
	global oldRaw,	lastRead, inp



	oldRaw						= ""
	lastRead					= 0
	inpRaw						= ""
	inp							= ""
	debug						= 5
	sensor						= G.program
	U.setLogging()

	# check for corrupt parameters file 
	U.checkParametersFile(force = False)


	if readParams() ==3:
			U.logger.log(30," parameters not defined")
			U.checkParametersFile( force = True)
			time.sleep(20)
			U.restartMyself(param=" bad parameters read", reason="")
	

	myPID		= str(os.getpid())
	U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

	subprocess.call("sudo /usr/bin/python3 {}display.py &".format(G.homeDir) , shell=True )


	U.echoLastAlive(G.program)

		
	sleepTime		= 5

	G.lastAliveSend	= time.time() -1000
	loopCounter			= 0

	U.getIPNumber() 

	U.logger.log(20," FBHdisplay looping")

	for ii in range(1000000):

		loopCounter += 1

		ret = readParams() 
		checkNewtempfile()
		time.sleep(5)
		if not U.pgmStillRunning("display.py"):
			subprocess.call("sudo /usr/bin/python3 {}display.py &".format(G.homeDir) , shell=True )



fbhexec()
U.logger.log(30,"end of loop", exc_info=True)
sys.exit(0)
