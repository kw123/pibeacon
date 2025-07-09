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
	global oldRaw, lastRead, targetData

	try:

		changed = 0
		inpLast = inp
		inp, inpRaw, lastRead2 = U.doRead(lastTimeStamp=lastRead)

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

		try:
			for idx in output[G.program]:
				targetData = output[G.program][idx][0]["data"]
				break
		except: targetData = {}
		#U.logger.log(20, ":{}".format())

		return changed

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(10)
		return 3

#################################		 
def checkNewtempfile():
	global lastOut, lastRaw, targetData
	try:

		#U.logger.log(20," checkNewtempfile: start ".format())
		data, raw = U.readJson(G.homeDir+"temp/Wire18B20.dat")
		if len(raw) < 2: 
			U.logger.log(20," checkNewtempfile: no new data ".format())
			return 
		if raw == lastRaw and time.time() - lastOut > 60: return 
		lastRaw = raw
		U.logger.log(20,"targetData:{}".format(targetData))

		# all in pixels
		lineSpacing			= 32 # line spacing
		y0 					= int(lineSpacing *.5)
		y 					= y0 + int(lineSpacing *.5)

		font 				= "Arial.ttf"
		frameTextSize 		= 30
		tempTextSize 		= lineSpacing -3
		tempTextSizeHalf	= int(tempTextSize/2.)
		totalFrame			= [0,0,1280,800]

		# positons and sizes 
		dateWidthPix 		= 60
		datePosPix 			= [500,				totalFrame[3]-dateWidthPix-5]
		legendPix1 			= [10,				totalFrame[3]-lineSpacing-5]
		legendPix2 			= [tempTextSize*5,	totalFrame[3]-lineSpacing-5]
		legendPix3 			= [tempTextSize*5*2,totalFrame[3]-lineSpacing-5]

		valvePosPix			= 125
		tempNumberPosPix 	= 180
		scaleStartDotsX		= 250
		dotsPerC			= 50 
		maxDotsX 			= 1000


		# colors in EGB
		colorGrey 			= [40,40,40]
		colorWhite 			= [150,150,150]
		colorHeader 		= [100,100,100]
		colorTempLabel 		= [100,100,100]
		colorTarget			= [0,100,100]
		colorRoomT			= [200,0,200]
		colorValvePos		= [100,100,0]
		colorTempHIGH		= [100,0,0]
		colorTempLOW		= [0,0,100]
		colorTempBadHigh	= [200,0,0]
		colorTempBadLow		= [0,0,200]
		tempOK 				= [0,200,0]

		# temp limits in C
		tHighVeryBad 		= 36
		tHighBad 			= 35
		tHigh 				= 30
		tLow  				= 18
		tLowBad  			= 15
		tLowVeryBad  		= 14.5
		tposZero  			= 15 



		theList = []
		for devId in data:
			name = "{}".format(data[devId]["name"].split("_")[1])
			if devId in targetData: 	
				U.logger.log(20," devId:{}, targetData:{}".format(devId, targetData[devId]))
				LEVEL = targetData[devId].get("LEVEL",-1)
				setpointHeat = int(targetData[devId].get("setpointHeat",0))
				roomTemperature = int(targetData[devId].get("roomTemperature",0))
			else: 
				roomTemperature = -1
				setpointHeat = -1
				LEVEL = -1
			if "temp" not in data[devId]: continue
			for nextT in data[devId]["temp"]:
				for serN in nextT:
					temp = nextT[serN]
					if  temp < tLowVeryBad:
						xpos = scaleStartDotsX
						tempText = "  ----- bad sensor read   --:{:.1f} < {}".format(temp,tLowVeryBad)
						color= colorTempBadLow

					elif temp > tHighVeryBad:
						xpos = scaleStartDotsX
						tempText = " ---- bad sensor to high--:{:.1f} > {}".format(temp, tHighVeryBad)
						color= colorTempBadHigh

					else:
						tempText = "{:.1f}".format(temp)
						xpos = int( scaleStartDotsX +  max(0,min(maxDotsX, (temp-tposZero)*dotsPerC - tempTextSizeHalf)) )
						if   temp > tHighBad: 	color = colorTempBadHigh
						elif temp > tHigh: 		color = colorTempHIGH
						elif temp < tLowBad: 	color = colorTempBadLow
						elif temp < tLow: 		color = colorTempLOW
						else: 					color = tempOK

					if setpointHeat > 0: setpointHeat = int( scaleStartDotsX +  max(0,min(maxDotsX, (setpointHeat-tposZero)*dotsPerC - tempTextSizeHalf)) )
					if roomTemperature > 0: roomTemperature = int( scaleStartDotsX +  max(0,min(maxDotsX, (roomTemperature-tposZero)*dotsPerC - tempTextSizeHalf)) )
					theList.append([name, tempText,  color ,xpos, setpointHeat, LEVEL, roomTemperature])

		theList = sorted(theList, key=lambda x: (x[0], x[1]))
		

		U.logger.log(20," theList:{}".format(theList))


		out = {"resetInitial": "", "repeat": 100000000, "delayAfterRepeat":7., "command":[]}
		# frame
		out["command"].append({"type":"rectangle", 								"fill": colorGrey, 			"position":totalFrame, 				"display":"wait", 		"reset":[50, 50, 50]})
		for ii in range(11):
				temp = ii*2
				xpos = int(  scaleStartDotsX +  max(-10,min(maxDotsX, temp*dotsPerC - tempTextSize) ))
				out["command"].append({"type": "text",	"width":tempTextSize,	"fill":colorTempLabel,		"position":[xpos,y0], 				"display": "wait", 		"text":"{}".format(temp+tposZero), "font":font})

		# values
		for name, value, color, xpos, setpointHeat, LEVEL, roomTemperature in theList:
			y += lineSpacing
			dyAst= int(lineSpacing*.2)

			if setpointHeat >= 0:
				out["command"].append({"type": "text",	"width":tempTextSize,	"fill":colorTarget,			"position":[setpointHeat,y], 		"display": "wait", 		"text":"T", 						"font":font})
			if roomTemperature >= 0:
				out["command"].append({"type": "text",	"width":tempTextSize,	"fill":colorRoomT,			"position":[roomTemperature,y], 	"display": "wait", 		"text":"R", 						"font":font})

			if LEVEL > 0:
				out["command"].append({"type": "text",	"width":tempTextSize,	"fill":colorValvePos, 		"position":[valvePosPix,y], 		"display": "wait", 		"text":"{:3d}".format(LEVEL), 	"font":font})

			out["command"].append({"type": "text",		"width":tempTextSize,	"fill":colorTempLabel,		"position":[10,y], 					"display": "wait", 		"text":name, 						"font":font})
			out["command"].append({"type": "text",		"width":tempTextSize,	"fill":color,				"position":[tempNumberPosPix,y], 	"display": "wait", 		"text":value, 						"font":font})
			out["command"].append({"type": "text",		"width":tempTextSize,	"fill":color,				"position":[xpos,y+dyAst],			"display": "wait", 		"text":"*", 						"font":font})

		out["command"].append({"type":"dateString",  	"width":dateWidthPix,  	"fill":colorWhite,			"position": datePosPix,   			"display": "wait", 		"text":"%a, %b  %d, %Y %H:%M:%S", 	"font":font} )
		out["command"].append({"type": "text",			"width":frameTextSize,	"fill":colorTarget,			"position":legendPix1, 				"display": "wait", 		"text":"T=Target", 					"font":font })
		out["command"].append({"type": "text",			"width":frameTextSize,	"fill":colorRoomT,			"position":legendPix2, 				"display": "wait", 		"text":"R=RoomT", 					"font":font })
		out["command"].append({"type": "text",			"width":frameTextSize,	"fill":tempOK,				"position":legendPix3, 				"display": "wait", 		"text":"*=WaterT", 					"font":font })
		out["command"].append({"type": "text",			"width":frameTextSize,	"fill":colorHeader,			"position":[10,y0], 				"display": "immediate", "text":"V#,       Pos,  T", 		"font":font })

		lastOut = time.time()
		outName = G.homeDir+"temp/display.inp"
		#U.logger.log(20,"outfile: {}; json:{}".format( outName, str(out)[0:50] ))
		f = open(outName,"w")
		f.write(json.dumps(out)+"\n")
		f.close()
		if time.time() - lastOut  < 15:
			time.sleep(15 -(time.time() - lastOut))
	

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		lastOut = 0
		time.sleep(3)
	return 



#################################
#################################
#################################
#################################
def fbhexec():
	global sensor, output, inpRaw, lastCl,clockMarks,maRGB
	global oldRaw,	lastRead, inp, lastOut, lastRaw, output

	output						= {}
	lastRaw						= ""
	lastOut						= 0
	oldRaw						= ""
	lastRead					= 0
	inpRaw						= ""
	inp							= ""
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

	#subprocess.call("sudo /usr/bin/python3 {}display.py &".format(G.homeDir) , shell=True )


	U.echoLastAlive(G.program)

		
	G.lastAliveSend	= time.time() -1000
	loopCounter			= 0

	U.getIPNumber() 

	U.logger.log(20," FBHdisplay looping")

	for ii in range(1000000):

		loopCounter += 1

		readParams()
		checkNewtempfile()
		time.sleep(5)
		if not U.pgmStillRunning("display.py"):
			subprocess.call("sudo /usr/bin/python3 {}display.py &".format(G.homeDir) , shell=True )



fbhexec()
U.logger.log(30,"end of loop", exc_info=True)
sys.exit(0)
