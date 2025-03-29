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
import math

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "neopixelClock"
import	RPi.GPIO as GPIO


version = 2.3
status = "ok"

#  for knight rider
# echo '{"resetInitial": "[0,0,0]", "repeat": -1,"command":[{"type": "ckr", "position": [0.01, 100, 100, 30, 0, 0, 0, 30, 0, 0, 0, 30]}]}' > neopixel.inp

#


# ------------------    ------------------ 

def getWifiInfo(longShort=0):
	global eth0IP, wifi0IP

	labels = [["o","off"],["A","active"],["P","search"],["I","adhoc"]]
	wifiInfo = labels[0][longShort]
	try:
		if G.wifiType == "adhoc":
			wifiInfo = labels[3][longShort]
		elif G.wifiEnabled:
			if wifi0IP !="":
				wifiInfo = labels[1][longShort]
			else:
				wifiInfo = labels[2][longShort]
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return wifiInfo

# ------------------    ------------------ 
def updatewebserverStatus():
	global eth0IP, wifi0IP, LEDintensityFactor, clockLightSetOverWrite, clockLightSet, timeZone, lightSensorValue
	global lightOnOff, lightSensorSlope
	global clockDict
	try: 
		xxx	= []
		xxx.append('')
		xxx.append( "Neopixel CLOCK current Status, updated every 3 secs<br> ")
		xxx.append( "time........... = "+ datetime.datetime.now().strftime("%H:%M:%S") )
		xxx.append( "time zone...... = "+ str(timeZone) )
		xxx.append( "IP-Number..wifi = "+ wifi0IP  )
		xxx.append( 'to set params.. =  <a href="http://{}:8010" style="color:rgb(255,255,255)">{}:8010 </a>  click here'.format(G.ipAddress,G.ipAddress))
		xxx.append( "WiFi enabled... = "+ str(G.wifiEnabled)  )
		xxx.append( "ClockLightSet.. = "+ str(clockDict["clockLightSet"])  )
		xxx.append( "LightSensorRaw. = {:.3f}".format(lightSensorValue)  )
		xxx.append( "LightSensorSlp. = {:.3f}".format(clockDict["lightSensorSlope"])  )
		xxx.append( "lightOnOff..... = {:.0f}".format(clockDict["lightOnOff"])  )
		xxx.append( "Marks-HH....... = "+ str(clockDict["marks"]["HH"])  )
		xxx.append( "Marks-MM....... = "+ str(clockDict["marks"]["MM"])  )
		xxx.append( "Marks-SS....... = "+ str(clockDict["marks"]["SS"])  )
		xxx.append( "Ticks-HH....... = "+ str(clockDict["ticks"]["HH"])  )
		xxx.append( "Ticks-MM....... = "+ str(clockDict["ticks"]["MM"])  )
		xxx.append( "Ticks-SS....... = "+ str(clockDict["ticks"]["SS"])  )
		xxx.append( '')

		statusData = ""
		for x in xxx:
			statusData += (x +"<br>")
		U.logger.log(10, "web status update:{}".format(xxx) )

		U.writeJson(G.homeDir+"statusData."+ G.myPiNumber, xxx, sort_keys=True, indent=2 )
		U.updateWebStatus(statusData)
	except Exception as e:
		U.logger.log(30,"", exc_info=True)

def removebracketsetc(data):
	out = "{}".format(data).replace("[","").replace("]","").replace(" ","")


# ------------------    ------------------ 
def webServerInputExtraText():
	try:
		xxx = []
		y  = ""
		y +=	'<hr align="left" width="70%" >'
		y +=	'<p><b>WALLClock.............:  enter clock parameters below:</b>'
		xxx.append(y)
		y  =	'led on/off..........:  <select name="LED">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="led:Off">off</option>'
		y +=			'<option value="led:On">on</option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'light sensor slope. : <select name="lightSensor">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="lightSensor:0.016;">*64 highest</option>'
		y +=			'<option value="lightSensor:0.031;">*32 </option>'
		y +=			'<option value="lightSensor:0.063;">*16 </option>'
		y +=			'<option value="lightSensor:0.125;">*8 </option>'
		y +=			'<option value="lightSensor:0.25;">*4 </option>'
		y +=			'<option value="lightSensor:0.50;">*2 </option>'
		y +=			'<option value="lightSensor:1.00;">normal default </option>'
		y +=			'<option value="lightSensor:2.00;">/2</option>'
		y +=			'<option value="lightSensor:4.00;">/4</option>'
		y +=			'<option value="lightSensor:8.00;">/8</option>'
		y +=			'<option value="lightSensor:16.00;">/16</option>'
		y +=			'<option value="lightSensor:32.00;">/32</option>'
		y +=			'<option value="lightSensor:64.00;">/64 lowest</option>'
		y +=		'</select>'
		xxx.append(y)
#		y  =	'marks mode......... : <select name="marksMode">'
#		y +=			'<option value="-1">do+not+change</option>'
#		y +=			'<option value="marksMode:auto;">auto</option>'
#		y +=			'<option value="marksMode:offoff;">off</option>'
#		y +=			'<option value="marksMode:nightoff;">nightoff</option>'
#		y +=			'<option value="marksMode:nightdim;">nightdim</option>'
#		y +=			'<option value="marksMode:daylow;">daylow</option>'
#		y +=			'<option value="marksMode:daymedium;">daymedium</option>'
#		y +=			'<option value="marksMode:dayhigh;">dayhigh</option>'
#		y +=		'</select>'
#		xxx.append(y)
		y  =	'hoursMarks......... : <select name="hoursMarks">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="HoursMarks:0;">off<//option>'
		y +=			'<option value="HoursMarks:1;">4+0 dots<//option>'
		y +=			'<option value="HoursMarks:2;">0+12<//option>'
		y +=			'<option value="HoursMarks:3;">12+4<//option>'
		y +=			'<option value="HoursMarks:4;">12+4+1<//option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'minutesMode........ : <select name="minutesMode">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="minutesMode:0;">dot<//option>'
		y +=			'<option value="minutesMode:3;">band</option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'hoursMode.......... : <select name="hoursMode">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="hoursMode:0;">1 dot outer ring -1<//option>'
		y +=			'<option value="hoursMode:5;">1 dot outer ring<//option>'
		y +=			'<option value="hoursMode:4;">2 dots outer rings<//option>'
		y +=			'<option value="hoursMode:1;">2 dots inner ring<//option>'
		y +=			'<option value="hoursMode:2;">3 dots<//option>'
		y +=			'<option value="hoursMode:3;">4 dots<//option>'
		y +=		'</select>'
		xxx.append(y)
		xxx.append('<br>')
		y  =	'show ip number..... : <select name="showipnumber">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="showipnumber"  >show ip number(last digit), 235-> ring1=2, ring2=3, ring3=5</option>'
		y +=		'</select>'
		xxx.append(y)
		xxx.append('<br>')
		y  =	'reboot, shutdown etc: <select name="re">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="restart"  >soft restart clock </option>'
		y +=			'<option value="reboot"   >powercycle clock </option>'
		y +=			'<option value="reset"    >reset parameters and reboot </option>'
		y +=			'<option value="shutdown" >shutdown clock, wait 30 secs before power off switch</option>'
		y +=			'<option value="halt"     >halt clock, wait 30 secs before power off switch</option>'
		y +=		'</select>'
		xxx.append(y)
		xxx.append('<br>')
		y =	'<p><b>Running line..:  enter parameters below:</b>'
		xxx.append(y)
		y  =	'Line Color......... : <select name="lineC">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="lineC:color" >bunt</option>'
		y +=			'<option value="lineC:red" >rot</option>'
		y +=			'<option value="lineC:yellow" >gelb</option>'
		y +=			'<option value="lineC:green" >gruen</option>'
		y +=			'<option value="lineC:blue" >blau</option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'Line Number........ : <select name="lineN">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="lineN:3"  >3 LED </option>'
		y +=			'<option value="lineN:6"  >6 LED</option>'
		y +=			'<option value="lineN:12" >12 LED</option>'
		y +=			'<option value="lineN:18" >18 LED</option>'
		y +=			'<option value="lineN:24" >24 LED</option>'
		y +=			'<option value="lineN:36" >36 LED</option>'
		y +=			'<option value="lineN:48" >48 LED</option>'
		y +=			'<option value="lineN:60" >60 LED</option>'
		y +=			'<option value="lineN:72" >72 LED</option>'
		y +=			'<option value="lineN:84" >84 LED</option>'
		y +=		'</select>'
		xxx.append(y)
		y  =	'Line Time.......... : <select name="lineT">'
		y +=			'<option value="-1">do+not+change</option>'
		y +=			'<option value="lineT:15"  >15 sec </option>'
		y +=			'<option value="lineT:30"  >30 sec </option>'
		y +=			'<option value="lineT:60"  >60 sec </option>'
		y +=			'<option value="lineT:90"  >90 sec </option>'
		y +=			'<option value="lineT:120"  >2 minutes </option>'
		y +=			'<option value="lineT:180"  >3 minutes </option>'
		y +=			'<option value="lineT:240"  >4 minutes </option>'
		y +=			'<option value="lineT:300"  >5 minutes </option>'
		y +=			'<option value="lineT:600"  >10 minutes </option>'
		y +=			'<option value="lineT:1200"  >20 minutes </option>'
		y +=			'<option value="lineT:3600"  >1 hour</option>'
		y +=			'<option value="lineT:7200"  >2 hours</option>'
		y +=			'<option value="lineT:10800" >3 hours</option>'
		y +=			'<option value="lineT:21400" >6 hours</option>'
		y +=		'</select>'
		xxx.append(y)
		xxx.append('<br>')
		defaults	= {"re":"-1","LED":"-1","calibrate":"-1","marksMode":"-1","lightSensor":"-1","lightoff":"-1",
						"hoursMarks":"-1","minutesMode":"-1","hoursMode":"-1","autoupdate":"-1",
						"lineC":"-1","lineN":"-1","lineT":"-1","showipnumber":"-1"}

		webServerInputHTML = ""
		for x in xxx:
			webServerInputHTML += (x +"<br>")
		out = json.dumps({"webServerInputHTML":webServerInputHTML,"defaults":defaults,"outputFile":G.homeDir+"temp/neopixelClock.cmd"})
		U.logger.log(10, "web status update:{}".format(out) )
		U.updateWebINPUT(out)
	except Exception as e:
		U.logger.log(30,"", exc_info=True)

#################################		 
def readCommand():
	global DEVID, clockDict, timeWait
	restart = 0

	try:
		if not os.path.isfile(G.homeDir+"temp/neopixelClock.cmd"): return  restart

		f=open(G.homeDir+"temp/neopixelClock.cmd","r")
		cmds = f.read().strip()
		f.close()
		os.system("rm  "+ G.homeDir+"temp/neopixelClock.cmd > /dev/null 2>&1 ")

		if len(cmds) < 2: return restart
		cmds = cmds.lower().replace(" ","").strip(";")
	### cmds: =["go0","getBoundaries","doLR","RGB:"]
		U.logger.log(20, "cmds: >>{}<<".format(cmds))
	## Lv:20 cmds: >>led:high;lightoff:0,0;lightsensor:0.016;;hoursmarks:on;;minutesmode:dot;;hoursmode:2dots;;reboot<<
	## cmds: >>hoursmarks:3;;minutesmode:3;;hoursmode:2<<

		pos = [0.01, 240, 1]
		cnrCmd = {"resetInitial": "[0,0,0]", "repeat": -1,"command":[{"type":"", "position": pos}]}
		numberOfLed = 0
		wait = 0
		color = ""

		restCount = 0
		cmds = cmds.split(";")
		for cmd in cmds:
			cmd = cmd.strip().lower()
			if len(cmd) < 2: continue

			U.logger.log(20, "readCommand :{} ".format(cmd) )

			if cmd.find("lightsensor:") > -1:
				clockDict["lightSensorSlope"] = 1./max(0.016,float(cmd.split(":")[1]))
				restart = 2
				continue

			if cmd.find("led:") > -1:
				value = cmd.split(":")[1]
				if value == "off":		clockDict["lightOnOff"] = 0
				else:					clockDict["lightOnOff"] = 1.
				restart = 2
				continue

			if cmd.find("line") == 0 and cmd.find(":") > 0:
				knType , value = cmd.split(":")
				knType = knType[-1]
				U.logger.log(20, f"knType:{knType:}, value:{value:}")
				if knType == "c": 
					color = value[0]
					if color in ["c"]:				cnrCmd["command"][0]["type"]	= "ckrr" 
					if color in ["r","g","b","y"]: 	cnrCmd["command"][0]["type"] 	= "kr" 

				if knType == "n": 					numberOfLed 					= int(value)
				if knType == "t": 					wait 							= int(value)



			if cmd.find("hoursmarks:") > -1:
				if setHHMarksTo(cmd.split(":")[1]): restart = 2
				restart = 2
				continue

			if cmd.find("minutesmode:") > -1:
				if setMMModeTo(cmd.split(":")[1]): restart = 2
				continue

			if cmd.find("hoursmode:") > -1:
				if setHHModeTo(cmd.split(":")[1]): restart = 2
				continue

			if cmd.find("marksmode:") > -1:
				clockLightSet = cmd.split(":")[1]
				clockDict["clockLightSet"]	= clockLightSet
				U.logger.log(20, "clockLightSet saved: {} dict:{}".format(clockLightSet, clockDict))
				restart = 2
				continue

			if cmd.find("restart") > -1:
				U.restartMyself(reason="shutdown send")
				continue

			if cmd.find("reboot") > -1:
				U.logger.log(20,  "reboot send")
				reboot()
				continue

			if cmd.find("reset") > -1:
				U.logger.log(20,  "reboot/restore send")
				resetEverything()
				signalShutDown()
				reboot()
				continue

			if cmd.find("shutdown") > -1:
				U.logger.log(20,  "shutdown send")
				subprocess.call("sudo killall -9 python3; sudo sync;sleep 2; sudo shutdown now", shell=True)
				continue

			if cmd.find("halt") > -1:
				subprocess.call("sudo killall -9 python3; sudo sync;sleep 2; sudo shutdown -H now", shell=True)
				continue

			if cmd.find("showipnumber") == 0:
				showIPnumber()
				continue

		if cnrCmd["command"][0]["type"] != "" and numberOfLed != 0 and wait != 0:
			if color == "c":
				cnrCmd["command"][0]["position"] += [numberOfLed]
				cnrCmd["command"][0]["position"] += calcRGBdimm([30,0,0], lightSensorValueREAD, minLight=True)+calcRGBdimm([0,30,0], lightSensorValueREAD, minLight=True)+calcRGBdimm([0,0,30], lightSensorValueREAD, minLight=True)
			else:
				cnrCmd["command"][0]["position"]  +=  [numberOfLed]
				if color == "r":  cnrCmd["command"][0]["position"]  +=  calcRGBdimm([30,0,0], lightSensorValueREAD, minLight=True)
				if color == "g":  cnrCmd["command"][0]["position"]  +=  calcRGBdimm([0,30,0], lightSensorValueREAD, minLight=True)
				if color == "b":  cnrCmd["command"][0]["position"]  +=  calcRGBdimm([0,0,30], lightSensorValueREAD, minLight=True)
				if color == "y":  cnrCmd["command"][0]["position"]  +=  calcRGBdimm([15,15,0], lightSensorValueREAD, minLight=True)
	
			setNEOinput(cnrCmd)
			timeWait = time.time() + wait - 10


		if restart in [1,2,3]:		
			saveParameters()
		if restart in [2]:		
			startNEOPIXEL(calledFrom="read command", force=True)

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return restart
	
#################################		 
def toggleSnake(color, wait ):
	global lastSnakeLen, snakeLenToggle, lightSensorValueREAD, timeWait

	try:
		pos = [0.01, 240, 1]
		cnrCmd = {"resetInitial": "[0,0,0]", "repeat": -1,"command":[{"type":"", "position": pos}]}
		lastSnakeLen +=1
		if lastSnakeLen >= len(snakeLenToggle): lastSnakeLen = 0
		numberOfLed = snakeLenToggle[lastSnakeLen]

		if color == "c":
			cnrCmd["command"][0]["type"]	= "ckrr" 
			cnrCmd["command"][0]["position"] += [numberOfLed]
			cnrCmd["command"][0]["position"] += calcRGBdimm([30,0,0], lightSensorValueREAD, minLight=True)+calcRGBdimm([0,30,0], lightSensorValueREAD, minLight=True)+calcRGBdimm([0,0,30], lightSensorValueREAD, minLight=True)
		else:
			cnrCmd["command"][0]["type"]	= "kr" 
			cnrCmd["command"][0]["position"]  +=  [numberOfLed]
			if color == "r":  cnrCmd["command"][0]["position"]  +=  calcRGBdimm([30,0,0], lightSensorValueREAD, minLight=True)
			if color == "g":  cnrCmd["command"][0]["position"]  +=  calcRGBdimm([0,30,0], lightSensorValueREAD, minLight=True)
			if color == "b":  cnrCmd["command"][0]["position"]  +=  calcRGBdimm([0,0,30], lightSensorValueREAD, minLight=True)
			if color == "y":  cnrCmd["command"][0]["position"]  +=  calcRGBdimm([15,15,0], lightSensorValueREAD, minLight=True)

		U.logger.log(20, f' c:{color:}, w:{wait:},  nL:{numberOfLed:} ')

		setNEOinput(cnrCmd)
		timeWait = time.time() + wait - 10

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
#################################		 
def toggleModes(tMode):
	global lastMMmode, lastHHmode, lastMarksMode, maxHHMode, maxMMMode, maxMarksMode
	try:


		U.logger.log(20, f' mode:{tMode:} mm:{lastMMmode:}, HH:{lastHHmode:}, MK:{lastMarksMode:}')
		if tMode == "MM":
			lastMMmode += 3
			if lastMMmode > maxMMMode: lastMMmode = 0
			setMMModeTo(lastMMmode)
			saveParameters()

		elif tMode == "HH":
			lastHHmode += 1
			if lastHHmode > maxHHMode: lastHHmode = 0
			setHHModeTo(lastHHmode)
			saveParameters()

		elif tMode == "Marks":
			lastMarksMode += 1
			if lastMarksMode > maxMarksMode: lastMarksMode = 0
			setHHMarksTo(lastMarksMode)
			saveParameters()

		else:
			return

		startNEOPIXEL(calledFrom="toggleModes", force=True)


		
	except Exception as e:
		U.logger.log(30,"", exc_info=True)

# ===========================================================================
# read params
# ===========================================================================

#################################		 
def readParams():
	global sensor, output, inpRaw, inp, DEVID,useRTC
	global clockDict, devTypeLEDs, speed, speedOfChange, setClock, clockMode, gpiopinSET, minLightNotOff
	global lastCl, timeZone, currTZ
	global oldRaw, lastRead
	global doReadParameters
	try:

		if not doReadParameters: return
		changed =0
		inpLast= inp
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
		 
		if "useRTC"					in inp:	 useRTC=			 (inp["useRTC"])
		if "output"					in inp:	 output=			 (inp["output"])
		#### G.debug = 2 
		if "neopixelClock" not in output:
			U.logger.log(30, "neopixel-clock	 is not in parameters = not enabled, stopping "+ G.program+".py" )
			exit()

		#U.logger.log(20, "clockDict:{}".format(clockDict))
		#only overwrite stored valeus if empty , use parameters
		if clockDict == {}:
			clock = output["neopixelClock"]
			for devId in  clock:
				DEVID = devId
				clockDict= copy.deepcopy(clock[devId][0])
				clockDict["lightSensorSlope"] = 1.0
				clockDict["lightOnOff"] = 1.0
				minLightNotOff =  int(clockDict.get("minLightNotOff")) #,minLightNotOff))
				clu= "{}".format(clockDict)
				if lastCl == clu: 
					return changed

				lastCl = clu
				if "devTypeLEDs"	 not in clockDict: continue
				#if clockDict		!= "start" and json.dumps(clockDict)  != json.dumps(cl["neoPixelClock"]):	return 1
				changed = 1
				if "devTypeLEDs"	 in clockDict: 
					if devTypeLEDs !="start" and devTypeLEDs != clockDict["devTypeLEDs"]:
						changed = 2	  
					devTypeLEDs		=  clockDict["devTypeLEDs"]
				else:
						changed = 3	  
				if "timeZone"			 in clockDict:	
					if timeZone !=			   (clockDict["timeZone"]):
						changed = max(2, changed)  
						timeZone =				   (clockDict["timeZone"])
						tznew  = int(timeZone.split(" ")[0])
						if tznew != currTZ:
							U.logger.log(30, "changing timezone from "+str(currTZ)+"  "+G.timeZones[currTZ+12]+" to "+str(tznew)+"  "+G.timeZones[tznew+12])
							subprocess.call("sudo cp /usr/share/zoneinfo/"+G.timeZones[tznew+12]+" /etc/localtime", shell=True)
							currTZ = tznew

				U.logger.log(20, "G.timeZones:{}".format(G.timeZones))
				time.sleep(5)
				clockDict["timeZone"] = str(currTZ)+" "+ G.timeZones[currTZ+12]
				
				if "speedOfChange"	 in clockDict: speedOfChange   =  clockDict["speedOfChange"]
				if "speed"			 in clockDict: speed		   =  clockDict["speed"]

				U.logger.log(20, "\nclockDict2:{}\n".format(clockDict))
				saveParameters()
				break
		try:
			if "GPIOsetA"			 in clockDict: gpiopinSET["setA"]			 =	int(clockDict["GPIOsetA"])
			if "GPIOsetB"			 in clockDict: gpiopinSET["setB"]			 =	int(clockDict["GPIOsetB"])
			if "GPIOsetC"			 in clockDict: gpiopinSET["setC"]			 =	int(clockDict["GPIOsetC"])
			if "GPIOup"				 in clockDict: gpiopinSET["up"]				 =	int(clockDict["GPIOup"])
			if "GPIOdown"			 in clockDict: gpiopinSET["down"]			 =	int(clockDict["GPIOdown"])
		except:
			pass

		return changed

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		time.sleep(10)
		return 3

#################################		 
def startNEOPIXEL(setClock="", off=False, calledFrom="", force=False):
	global devTypeLEDs, speed, speedOfChange, clockMode, clockLightSetOverWrite, LEDintensityFactor, lightSensorValue, lightSensorValueREAD, minLightNotOff
	global DEVID, clockDict, inp 
	try:
		#U.logger.log(20, "startNEOPIXEL.. ")

		# define short cuts
		clockDict["LEDsum"]		=[]
		clockDict["LEDstart"]	=[]
	
		HHMMSSDDnofTicks={"HH":12,"MM":60,"SS":60}

		lightset = clockDict["clockLightSet"]
		if lightset == "auto":
			lightset = clockLightSetOverWrite  ## put here input from light sensor 


		if clockDict["clockLightSet"].lower() == "auto":
			multHMS = lightSensorValueREAD
			multMark = lightSensorValueREAD
		else:
			if	 True										: multHMS = 1.	; multMark=1.

			if	 LEDintensityFactor.lower() =="offoff"		: multHMS = 0.005; multMark = 0.005
			elif LEDintensityFactor.lower() =="nightoff"	: multHMS = 0.01;  multMark = 0.01
			elif LEDintensityFactor.lower() =="nightdim"	: multHMS = 0.05;  multMark = 0.05
			elif LEDintensityFactor.lower() =="daylow"		: multHMS = 0.1;   multMark = 0.1
			elif LEDintensityFactor.lower() =="daymedium"	: multHMS = 0.50;  multMark =0.5
			elif LEDintensityFactor.lower() =="dayhigh"		: multHMS = 1.0 ;  multMark =1.0

		U.logger.log(20,f"called from:{calledFrom:},  lightSensorValueREAD:{lightSensorValueREAD:.4f},  auto?:{clockDict['clockLightSet']:},  minLightNotOff:{minLightNotOff:}")


		lll = 0
		for r in clockDict["rings"]:
			clockDict["LEDstart"].append(lll)
			lll+=r
			clockDict["LEDsum"].append(lll)
		maxLED = lll
		
		for tt in ["HH","MM","SS"]:
			lll = 0
			for r in clockDict["ticks"][tt]["ringNo"]:
				lll +=clockDict["rings"][r]
			clockDict["ticks"][tt]["LEDsum"]   = lll
			clockDict["ticks"][tt]["LEDstart"] = 0
			if len(clockDict["ticks"][tt]["ringNo"]) > 0:
				clockDict["ticks"][tt]["LEDstart"] = clockDict["LEDstart"][clockDict["ticks"][tt]["ringNo"][0]]
			lll = 0
			for r in clockDict["marks"][tt]["ringNo"]:
				lll +=clockDict["rings"][r]
			clockDict["marks"][tt]["LEDsum"]   = lll
			clockDict["marks"][tt]["LEDstart"] = 0
			if len(clockDict["marks"][tt]["ringNo"]) > 0:
				clockDict["marks"][tt]["LEDstart"] = clockDict["LEDstart"][clockDict["marks"][tt]["ringNo"][0]]


		string = ""
		for tt in ["HH","MM","SS"]:
			string+=  " {}:{}".format(tt, clockDict["marks"][tt])
		U.logger.log(10, "startNEOPIXEL..lightset: {}".format(lightset)+string)
##20181122-02:21:04 startNEOPIXEL..lightset: offoff;  clockDict[marks] {u'MM': {'LEDstart': 0, u'RGB': [0, 0, 0], u'ringNo': [], 'LEDsum': 0, u'marks': []}, u'SS': {'LEDstart': 0, u'RGB': [0, 0, 0], u'ringNo': [], 'LEDsum': 0, u'marks': []}, u'DD': {'LEDstart': 0, u'RGB': [0, 0, 0], u'ringNo': [], 'LEDsum': 0, u'marks': []}, u'HH': {'LEDstart': 0, u'RGB': [0, 0, 0], u'ringNo': [], 'LEDsum': 0, u'marks': []}}

		pos={}
		for tt in ["HH","MM","SS"]:
			ticks = HHMMSSDDnofTicks[tt]
			ind =[]
			nRings		= len(clockDict["ticks"][tt]["ringNo"])
			if nRings ==0: continue
			ringNo		= clockDict["ticks"][tt]["ringNo"]
			if ringNo ==[]: continue
			LEDstart	= clockDict["ticks"][tt]["LEDstart"]
			LEDsInRing0 = clockDict["rings"][ringNo[0]]
			LEDsum		= clockDict["ticks"][tt]["LEDsum"]
		
			if clockDict["ticks"][tt]["npix"] == 3:	# only for single ring
				for ii in range(clockDict["rings"][ringNo[0]]):
					left		= ii+LEDstart - 1
					mid			= ii+LEDstart
					right		= ii+LEDstart + 1
					if left	 <	LEDstart:			left   = LEDstart + LEDsum -1
					if right >= LEDstart + LEDsum:	right  = LEDstart
					ind.append([left,mid,right])
				RGB= calcRGBdimm(clockDict["ticks"][tt]["RGB"], multHMS, minLight=True)
				pos[tt]= {"RGB":RGB,"index":ind,"blink":clockDict["ticks"][tt]["blink"]}

			elif clockDict["ticks"][tt]["npix"] == -1: #fill ring up to number
				for tick in range(ticks): 
					tIndex =[]
					##for jj in range(LEDsInRing0):
					for nR in range(nRings):  ### add if # of tick < # of led in ring 
						LEDsinRING		= clockDict["rings"][ringNo[nR]]
						LEDStartinRING	= clockDict["LEDstart"][ringNo[nR]]
						if	 ticks > LEDsinRING:  maxT = int(tick / (float(ticks)/LEDsinRING))
						elif ticks < LEDsinRING:  maxT = int(tick * (float(LEDsinRING)/ticks)) 
						else:					  maxT = tick 
						fromT =0
						if maxT == LEDsinRING-1: # starts at 0 otherwise no -1 
							fromT=1
						for ii in range(fromT,maxT+1):
							tIndex.append(ii+ LEDStartinRING)
					ind.append(tIndex)
				RGB = calcRGBdimm(clockDict["ticks"][tt]["RGB"], multHMS, minLight=True)
				pos[tt]= {"RGB":RGB,"index":ind,"blink":clockDict["ticks"][tt]["blink"]}

			elif clockDict["ticks"][tt]["npix"] == 1: # single led 
				for tick in range(ticks): 
					tIndex =[]
					##for jj in range(LEDsInRing0):
					for nR in range(nRings):  ### add if # of tick < # of led in ring 
						LEDsinRING		= clockDict["rings"][ringNo[nR]]
						LEDStartinRING	= clockDict["LEDstart"][ringNo[nR]]
						if ticks > LEDsinRING:
							tIndex.append(int(tick / (float(ticks)/LEDsinRING)) + LEDStartinRING)
						elif ticks < LEDsinRING:
							tIndex.append(int(tick * (float(LEDsinRING)/ticks)) + LEDStartinRING)
						else:
							tIndex.append(tick + LEDStartinRING)
					ind.append(tIndex)
				RGB = calcRGBdimm(clockDict["ticks"][tt]["RGB"], multHMS, minLight=True)
				pos[tt]= {"RGB":RGB,"index":ind,"blink":clockDict["ticks"][tt]["blink"]}

			elif clockDict["ticks"][tt]["npix"] ==0: # do not show
				pass

		marks={}
		if clockDict["lightOnOff"] != 0:
			if True or (lightset.lower()).find("off") == -1: 
				#U.logger.log(20, "marks {} ".format(clockDict["marks"]))
				for tt in ["HH","MM","SS"]:
					#U.logger.log(20, "marks tt:{} ".format(tt))
					index=[[]]
					if tt not in clockDict["marks"]			 : continue
					if clockDict["marks"][tt] == {}			 : continue
					if clockDict["marks"][tt]["marks"] == [] : continue
					#U.logger.log(20, "marks pix: {} ".format(clockDict["marks"][tt]))
					ticks = HHMMSSDDnofTicks[tt]
					for nR in range(len(clockDict["marks"][tt]["ringNo"])):
						ringNo		= clockDict["marks"][tt]["ringNo"][nR]
						LEDstart	= clockDict["LEDstart"][ringNo]
						LEDsinRING	= clockDict["rings"][ringNo]
						mult = float(LEDsinRING) / ticks
						for ll in clockDict["marks"][tt]["marks"]:
							ii = int(ll*mult + LEDstart)
							if ii < maxLED:
								index[0].append(ii)
					marks[tt] = {"RGB":[min(int(multMark*x),255) for x in clockDict["marks"][tt]["RGB"]],"index":index}

		if marks == {}: 
			marks = ""
		pos["marks"] = marks

		pos["speed"] = speed

		pos["extraLED"] =""
		if clockDict["lightOnOff"] != 0:
			if "extraLED" in clockDict and clockDict["extraLED"] !="":
				pos["extraLED"] = {}
				if "RGB" in clockDict["extraLED"]:
					pos["extraLED"]["RGB"]	 = clockDict["extraLED"]["RGB"]
				else:
					pos["extraLED"]["RGB"]	 = [100 ,100 ,100 ]
				if "blink" in clockDict["extraLED"]:
					pos["extraLED"]["blink"] = clockDict["extraLED"]["blink"]
				else:
					pos["extraLED"]["blink"] = [1,1]
				ind =[]
				for tick in clockDict["extraLED"]["ticks"]:
					ind.append(tick)
				pos["extraLED"]["index"] = [ind]
			


		U.logger.log(10, " starting neopixel with:{}".format(pos) )	 

		out={"resetInitial": "", "repeat": -1,"command":[{"type": "clock","position":pos, "display": "immediate","speedOfChange":speedOfChange,"marks":marks,"speed":speed}]}
		if setClock !="":
			out["setClock"] = setClock
			clockMode ="setClockStarted"
		else:
			clockMode ="run"

		if off: out["setClock"] = "off"
		
		if not U.pgmStillRunning("neopixel3.py neopixelClock"):
			U.killOldPgm(myPID,"neopixel3.py",verbose=True, wait=True)
			time.sleep(3)
			subprocess.call("/usr/bin/python3 "+G.homeDir+"neopixel3.py neopixelClock &", shell=True)
			U.logger.log(20, "starting /usr/bin/python3 "+G.homeDir+"neopixel3.py neopixelClock &")

		if os.path.isfile(G.homeDir+"temp/neopixel.busy") and not force:
			os.remove(G.homeDir+"temp/neopixel.busy")
		else:
			U.logger.log(20, "waitime:{}, checking if waiting for new cmd {} ".format(time.time() > timeWait , os.path.isfile(G.homeDir+"temp/neopixel.waiting")))
			if time.time() > timeWait or os.path.isfile(G.homeDir+"temp/neopixel.waiting"):
				setNEOinput(out)

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 


#################################
def calcRGBdimm(input ,multHMS, minLight=False):
	global clockDict, minLightNotOff
	RGB= []
	for x in input:
		x *= clockDict["lightOnOff"]
		if x==0 :
			rgb = 0
		elif x <minLightNotOff and not minLight: 
			rgb = 0
		else:	  
			if minLight:
				rgb = max(  min( int(multHMS*(x-minLightNotOff-1) + minLightNotOff),255 ), minLightNotOff  )
			else:
				rgb = min(int(multHMS*(x-minLightNotOff-1) + minLightNotOff),255)
		RGB.append(rgb)
	return RGB

#################################
def setNEOinput(out):
		global lastNeoParamsSet
		f=open(G.homeDir+"temp/neopixel.inp","a")
		f.write(json.dumps(out)+"\n") 
		f.close()
		lastNeoParamsSet = time.time()
		#print " new neo paramers written", datetime.datetime.now()
		return

#################################
def setupGPIOs():
	global gpiopinSET 
	try: 
		GPIO.setwarnings(False)
		GPIO.cleanup() 
		GPIO.setmode(GPIO.BCM)

		U.logger.log(20, "setupGPIOs  {}".format(gpiopinSET))
		GPIO.setup(gpiopinSET["setA"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(gpiopinSET["setB"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(gpiopinSET["setC"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(gpiopinSET["up"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(gpiopinSET["down"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

	except Exception as e:
		U.logger.log(30,"", exc_info=True)

	return


#################################
def makeTZ(tz):
	global inp, clockDict, DEVID, currTZ
	clockDict["timeZone"] = str(currTZ)+" "+tz
	#print "sudo cp /usr/share/zoneinfo/"+tz+" /etc/localtime"
	U.writeTZ(  cTZ="tz" )
	return

#################################
def writeTZ(tz ):
	subprocess.call("sudo cp /usr/share/zoneinfo/"+tz+" /etc/localtime", shell=True)
	return


#################################
def setExtraLEDoff():
	global DEVID, clockDict, inp
	try:
		if clockDict["extraLED"] !="":
			clockDict["extraLED"] = ""
			saveParameters()
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return

#################################
def startNEOPIXELNewTime(h,m,d,tz=""):
	U.logger.log(10,"startNEOPIXELNewTime "+	 str(d)+"  "+ str(h)+"	"+ str(m)) 
	if h <	0:	h = 23
	if h > 23:	h =	 0
	if m <	0:	m = 59
	if m > 59:	m =	 0
	currHH = h
	currMM = m
	currdd = d
	dd = datetime.datetime.now()
	if dd.day == d:
		newDate = dd.strftime("%Y-%m-%d ")+"%02d"%h+":"+"%02d"%m+":00"
	else:
		dd = datetime.datetime.now() - datetime.timedelta(d-dd.day)
		newDate = dd.strftime("%Y-%m-%d ")+"%02d"%h+":"+"%02d"%m+":00"
	U.logger.log(10, 'bf startNEOPIXEL:	;;; date -s "'+newDate+'"')
	#subprocess.call("date -s '"+newDate+"'", shell=True)
	startNEOPIXEL(setClock="%02d"%d+":%02d"%h+":%02d"%m+":00")
	return
 



#################################
def setPatternUPdown(upDown):
	global inp,	 DEVID
	global marksONoff, hoursPix, minutesPix,ticksMMHH
	global marksOptions, ticksOptions
	U.logger.log(10,"setPattern {}".format(upDown) )
	U.logger.log(10, "{}".format( clockDict["clockLightSet"] )) 
	
	getCurrentPatterns()

	if upDown =="DOWN":
		if marksONoff < 4:	setPatternTo(ticks=ticksMMHH,marks=marksONoff+1, save=True,restart=True, ExtraLED=True)
		else:				setPatternTo(ticks=ticksMMHH,marks=0,			 save=True,restart=True, ExtraLED=True)
	else:
		if ticksMMHH < 3:	setPatternTo(ticks=ticksMMHH+1,marks=marksONoff, save=True,restart=True, ExtraLED=True)
		else:				setPatternTo(ticks=0,		   marks=marksONoff, save=True,restart=True, ExtraLED=True)
	return

#################################
def getCurrentPatterns():
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global clockDict, inp 
	marksONoff = 0 
	ticksMMHH = 0
	minutesPix = 1
	hoursPix = 1
	try:
		if clockDict["ticks"]["MM"]["npix"] ==1:						minutesPix = 1
		else:															minutesPix = -1
		if clockDict["ticks"]["HH"]["ringNo"] == [8,1]:					hoursPix   = 1
		elif clockDict["ticks"]["HH"]["ringNo"] == [8,6,4]:				hoursPix   = 3
		elif clockDict["ticks"]["HH"]["ringNo"] == [4,1]:				hoursPix   = 4
		else:															hoursPix   = 5

		if	 minutesPix ==	1 and hoursPix ==1: ticksMMHH = 0  # this is the fewest pixel mode 
		elif minutesPix ==	1 and hoursPix ==3: ticksMMHH = 1  
		elif minutesPix ==	1 and hoursPix ==4: ticksMMHH = 2
		elif minutesPix == -1 and hoursPix ==3: ticksMMHH = 3
		elif minutesPix == -1 and hoursPix ==4: ticksMMHH = 4
		elif minutesPix == -1 and hoursPix ==5: ticksMMHH = 4
		else:									ticksMMHH = 4

		if		 clockDict["marks"]["MM"]["marks"] == []:				marksONoff = 0 # = no marks
		elif	 clockDict["marks"]["MM"]["marks"] == [0, 15, 30, 45]:	marksONoff = 1
		else: #must be:[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
			if	 clockDict["marks"]["SS"]["marks"] == []:				marksONoff = 2
			elif clockDict["marks"]["HH"]["marks"] == [0]:				marksONoff = 4
			else:														marksONoff = 3
	except Exception as e:
		U.logger.log(30,"", exc_info=True)


#################################
def setPatternTo(ticks="" ,marks="", save=True, restart=True, ExtraLED=False):
	global inp, clockDict, DEVID
	global ticksOptions, marksOptions
	try:
		if ticks !="":
			clockDict["ticks"]									= copy.deepcopy(ticksOptions[ticks])
		if marks !="":
			clockDict["marks"]									= copy.deepcopy(marksOptions[marks])
		if ExtraLED and ticks !="" and marks !="":
			l0 = 60 + 48 + 40 +32 +1
			clockDict["extraLED"]	= {"ticks":[ii+l0 for ii in range(ticks+4*marks)], "RGB":[100,100,100],"blink":[1,0]} # start on 8 ring 
		
		getCurrentPatterns()
		if save:
			saveParameters()
		if restart:
			startNEOPIXEL(force=True)
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		
	return
	
##
#################################
def setHHMarksTo(yy):
	global inp, clockDict, DEVID
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global ticksOptions, marksOptions
	global maxHHMode, maxMMMode, maxMarksMode
	try:
		xx = int(yy)
		if xx in range(maxMarksMode+1): 
			setPatternTo(marks=xx, save=False, restart=False)
		else:
			return  False
		U.logger.log(20, "setHHMarksTo {}".format(xx))
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return True

#################################
def setMMModeTo(yy):
	global inp, clockDict, DEVID
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global ticksOptions, marksOptions
	global maxHHMode, maxMMMode, maxMarksMode

	try:
		xx = int(yy)
		zz ="MM"
		if xx in range(maxMMMode+1): 
			U.logger.log(20, "setMMModeTo {}".format(xx))
			clockDict["ticks"][zz] = copy.deepcopy(ticksOptions[xx][zz])
		else:
			return  False
		U.logger.log(20, "setMMModeTo {}".format(xx))
		getCurrentPatterns()
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return True

#################################
def setHHModeTo(yy):
	global inp, clockDict, DEVID
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global ticksOptions, marksOptions
	global maxHHMode, maxMMMode, maxMarksMode
	try:
		getCurrentPatterns()
		xx = int(yy)
		zz = "HH"
		if xx in range(maxHHMode+1): 
			clockDict["ticks"][zz] = copy.deepcopy(ticksOptions[xx][zz])
		else:
			return  False
		U.logger.log(20, "setHHModeTo #{}".format(xx ))
		getCurrentPatterns()
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30, "ticksOptions {} ".format(ticksOptions))
	return True


#################################
def setNightPatterns():
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global marksONoffLAST, hoursPixLAST, minutesPixLAST, ticksMMHHLAST
	global nightMode

	if nightMode !=1:	 
		marksONoffLAST, hoursPixLAST, minutesPixLAST, ticksMMHHLAST = marksONoff, hoursPix, minutesPix, ticksMMHH
		nightMode = 1
		setPatternTo(ticks=1 ,marks=0, save=False, restart=False, ExtraLED=False)
	return

#################################
def setNightOffPatterns():
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global marksONoffLAST, hoursPixLAST, minutesPixLAST, ticksMMHHLAST
	global nightMode

	if nightMode !=2: 
		marksONoffLAST, hoursPixLAST, minutesPixLAST, ticksMMHHLAST = marksONoff, hoursPix, minutesPix, ticksMMHH
		nightMode = 2
		setPatternTo(ticks=0, marks=0, save=False, restart=False, ExtraLED=False)
	return 

#################################
def	 restorefromNightPatterns():
	global marksONoff, hoursPix, minutesPix, ticksMMHH
	global marksONoffLAST, hoursPixLAST, minutesPixLAST, ticksMMHHLAST
	global nightMode

	if nightMode >0:
		setPatternTo(ticks=ticksMMHHLAST ,marks=marksONoffLAST, save=False, restart=False, ExtraLED=False)
		nightMode = 0
	return


	

#################################
def saveParameters():
	global clockDict
	global lastNeoParamsSet
	global clockDict

	try:
		f = open(G.homeDir+"neopixelClock.clockDict","w")
		f.write(json.dumps(clockDict, sort_keys=True, indent=2))
		f.close()
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return


#################################
def readLocalParams():
	global clockDict, minLightNotOff
	initlocalParams()
	try:
		f= open(G.homeDir+"neopixelClock.clockDict","r")
		xx = f.read()
		f.close()
		clockDict = json.loads(xx)
		U.logger.log(20, f" minLightNotOff:{clockDict['minLightNotOff']:}")
		minLightNotOff = int(clockDict.get('minLightNotOff', minLightNotOff))
	except: pass
	if len(clockDict) < 2 :
		initlocalParams()
	return


#################################
def initlocalParams():
	global clockDict
	clockDict = {}
	return

 
#################################
def setLightfromSensor():
	global clockLightSetOverWrite, lightSensorValueLast, lightSensorValue, lightSensorValueREAD
	global lastTimeStampSensorFile, clockLightSetOverWriteOld,  LEDintensityFactor, LEDintensityFactorOld
	global clockDict
	try:

		try:	ii = lastTimeStampSensorFile
		except: 
			lastTimeStampSensorFile	  = 0
			clockLightSetOverWriteOld = ""
			LEDintensityFactorOld 	  = ""
			lightSensorValue          = 0


		if not os.path.isfile(G.homeDir+"temp/lightSensor.dat"): return
		t = os.path.getmtime(G.homeDir+"temp/lightSensor.dat")
		U.logger.log(10, "setLightfromSensor  == reading sensor ==")
	
		maxRange = 10000.
		sensor = ""
		xx, raw = U.readJson(G.homeDir+"temp/lightSensor.dat")
		U.logger.log(10, "setLightfromSensor  == reading sensor ==:{}".format(xx))
		if xx == {}: 				return
		if "sensors" not in xx: 	return
		if "time" not in xx: 		return
		tt		= xx["time"]
		sensors = xx["sensors"]
		if lastTimeStampSensorFile == tt: return 
		lastTimeStampSensorFile = tt


		for sensor in sensors:
			yy = sensors[sensor]
			try:
				for sensorId in yy: 
					rr = yy[sensorId]
					U.logger.log(10, "setLightfromSensor  == reading sensor ==:{}".format(rr))
					lightSensorValueREAD = rr["light"]
					if sensor == "i2cTSL2561":
						maxRange = 12000.
					elif sensor == "i2cOPT3001":
						maxRange =	20000.
					elif sensor == "i2cVEML6030":
						maxRange =	4000.
					elif sensor == "i2cIS1145":
						maxRange =	2000.

					#print "lastTimeStampSensorFile, tt", lastTimeStampSensorFile, tt
			except:
				U.logger.log(30, "error reading light sensor")
				return

		lightSensorValue = lightSensorValueREAD *(1./maxRange)* clockDict["lightSensorSlope"]
		lightSensorValueREAD = lightSensorValue

		if lightSensorValueREAD == 0 and lightSensorValueLast !=0: 
				lightSensorValueLast = lightSensorValueREAD
				return
		lightSensorValueLast = lightSensorValueREAD

		if	 lightSensorValue < 0.005:	   CLS ="offoff"  
		elif lightSensorValue < 0.01:	   CLS ="nightoff"  
		elif lightSensorValue < 0.05:	   CLS ="nightdim"  
		elif lightSensorValue < 0.1:	   CLS ="daylow"	   
		elif lightSensorValue < 0.5:	   CLS ="daymedium" 
		else:							   CLS ="dayhigh"   
		
		restartstartNEOPIXEL = False 
		if LEDintensityFactorOld  != CLS:
			LEDintensityFactorOld 	= LEDintensityFactor
			LEDintensityFactor 		= CLS
			restartstartNEOPIXEL = True 
		if clockDict["clockLightSet"].lower() == "auto": 
			if clockLightSetOverWriteOld !=	  CLS:
				clockLightSetOverWriteOld 	= clockLightSetOverWrite
				clockLightSetOverWrite 		= CLS
				restartstartNEOPIXEL 		= True 
				
		if restartstartNEOPIXEL:
			#U.logger.log(20, "setLightfromSensor  bf restartstartNEOPIXEL")
			try:
				startNEOPIXEL(calledFrom=f"set light form sensor", force=True)
			except Exception as e:
				U.logger.log(30,"", exc_info=True)
			
		#print  "setting lightSenVREAD lightSenV, clockLSetOW, maxRange, clockDict["clockLightSet"], LEDintF:"+str(int(lightSensorValueREAD))+"  "+str(int(lightSensorValue))+" "+str(clockLightSetOverWrite)+"  "+str(int(maxRange))+" "+clockDict["clockLightSet"]+"  "+str(LEDintensityFactor) 
		U.logger.log(10, "setting lightSenVREAD lightSenV, clockLSetOW, maxRange, clockLightSet, LEDintF:"+str(int(lightSensorValueREAD))+"  "+str(int(lightSensorValue))+" "+str(clockLightSetOverWrite)+"  "+str(int(maxRange))+" "+clockDict["clockLightSet"]+"  "+str(LEDintensityFactor))
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return




#################################
def afterAdhocWifistartedSetLED(maxTime):
	global DEVID, clockDict, inp 
	l0 = 60 + 48 + 40 
	clockDict["extraLED"]	  = {"ticks":[ii+l0 for ii in range(int(maxTime))], "RGB":[0,0,200],"blink":[1,1]} # blink led 7 on 8 ring 
	return



#################################
def resetEverything():
	U.killOldPgm(myPID,"neopixel.py")
	subprocess.call('sudo cp '+G.homeDir+'neopixelClock.clockDict-backup '+G.homeDir+'neopixelClock.clockDict', shell=True)
	subprocess.call('sudo cp '+G.homeDir+'neopixelClock.interfaces /etc/network/interfaces', shell=True)
	subprocess.call('sudo cp '+G.homeDir+'neopixelClock.parameters '+G.homeDir+'parameters', shell=True)
	subprocess.call('sudo cp '+G.homeDir+'neopixelClock.wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf', shell=True)
	restorePattern()
	time.sleep(2)
	subprocess.call("sudo killall -9 python; sudo sync;sleep 2; sudo reboot -f", shell=True)
	return ## dummy

#################################
def shutdown():
	print (" we are shutting down now")
	time.sleep(2)
	subprocess.call("sudo killall -9 python;sleep 2; shutdown now", shell=True)
	return ## dummy
#################################
def reboot():
	print (" we are rebooting now")
	time.sleep(2)
	subprocess.call("sudo killall -9 python;sleep 2; reboot now", shell=True)
	return ## dummy


#################################
def readMarksFile():
	global marksOptions,ticksOptions, clockDict
	rr, raw = U.readJson(G.homeDir+"neopixelClock.patterns")
	if rr == {} or "marks" not in rr:
		restorePattern()
		rr, raw = U.readJson(G.homeDir+"neopixelClock.patterns")
	if rr == {} or "marks" not in rr:
		U.logger.log(40, " fatal error pattern file destroyed, backup did not work " )
	else:	
		marksOptions   = copy.deepcopy(rr["marks"])
		ticksOptions   = copy.deepcopy(rr["ticks"])
	#U.logger.log(20, "readMarksFile marksOptions:{} ".format(marksOptions))
	#U.logger.log(20, "readMarksFile ticksOptions:{} ".format(ticksOptions))
	return
	
#################################
def restorePattern():
	U.logger.log(30, "restoring pattern files ")
	subprocess.call("cp "+G.homeDir+"neopixelClock.patterns-backup " +G.homeDir+"neopixelClock.patterns", shell=True) 
	return 
	
def signalShutDown(fast=False):
	if fast: delta = 0.49
	else:	 delta = 0.96
	for ii in range(8):
		ticks = []
		for ind in range(ii, 8):
			ticks.append(ind + 60 + 48 + 40 + 32 + 24 + 16 + 12)
		clockDict["extraLED"] = {"ticks":ticks, "RGB":[int(100/(ii*2+1)),int(100/(ii*2+1)),int(100/(ii*2+1))],"blink":[1,0]} # show all 8 led on ring w 8 led = dim white blinking
		startNEOPIXEL(calledFrom="signalShutDown 1", force=True)
		time.sleep(delta)
	startNEOPIXEL(off=True, calledFrom="signalShutDown 2", force=True)
	time.sleep(1)
	return

#################################
def showIPnumber():
	global wifi0IP
	global networkIndicatorON
	global adhocWifiStarted


	lastIP = wifi0IP.split(".")
	
	if len(lastIP) == 4:
		npDots = int(lastIP[3])
	else:
		return 

	n100 = npDots//100
	n10  = (npDots-n100*100 )//10
	n    = npDots - n100*100 - n10*10 
	networkIndicatorON = -1

	if adhocWifiStarted < 0:
		ticks = []
		if n100 > 0:
			ticks = [ii for ii in range(n100)]
		if n10 > 0:
			ticks += [ii+60 for ii in range(n10)]
		if n > 0:
			ticks += [ii+60+48 for ii in range(n)]
		U.logger.log(20,f"npDots:{npDots:}, ring1:n100={n100:} ring2:n10={n10:}, ring3:n={n:} ")

		clockDict["extraLED"]  = { "ticks":ticks, "RGB":[20,20,20],"blink":[1,0]} 

		startNEOPIXEL(calledFrom="showIPnumber", force=True)
		networkIndicatorON	= time.time()+30





#################################
#################################
#################################
#################################
global clockDict
global switchON, minLightNotOff
global sensor, output, inpRaw, lastCl,clockMarks,maRGB
global oldRaw,	lastRead, inp
global gpiopinSET
global clockLightSetOverWrite, useRTC, DEVID
global timeZone
global lightSensorValueLast, lightSensorValue
global doReadParameters
global nightMode
global networkIndicatorON
global lastNeoParamsSet
global clockLightSetOverWrite, clockLightSetOverWriteOld, LEDintensityFactorOld, LEDintensityFactor
global eth0IP, wifi0IP
global timeWait
global networkIndicatorON
global adhocWifiStarted
global lightSensorValueREAD
global lastSnakeLen, snakeLenToggle
global lastMMmode, lastHHmode, lastMarksMode
global maxHHMode, maxMMMode, maxMarksMode

maxHHMode			= 5
maxMMMode			= 4
maxMarksMode		= 4

lastMMmode			= 0
lastHHmode			= 0
lastMarksMode		= 0

lastSnakeLen		= 0
snakeLenToggle		= [3,12,24,60]
lightSensorValueREAD = 1
adhocWifiStarted	= False
networkIndicatorON	= -1
timeWait			= 0
lastNeoParamsSet	= time.time()
nightMode			= 0

doReadParameters	= True
timeZone			= ""

#delta to UTC:
JulDelta = int(int(subprocess.Popen("date -d '1 Jul' +%z " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0])/100)
JanDelta = int(int(subprocess.Popen("date -d '1 Jan' +%z " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0])/100)
NowDelta = int(int(subprocess.Popen("date  +%z "		   ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0])/100)

currTZ = JanDelta

#print "current tz:", currTZ,JulDelta,JanDelta,NowDelta, G.timeZones[currTZ+12], G.timeZones


minLightNotOff				= 45
switchON					= [False,False,False,False]
DEVID						= "0"
gpiopinSET					= {"setA": 13,"setB":21,"setC":12,"up":19,"down":26} # default 
dd							= datetime.datetime.now()
currHH						= dd.hour
currMM						= dd.minute
currDD						= dd.day
useRTC						= ""
lightSensorValueLast		= -1
lightSensorValue			= -1
clockLightSetOverWrite		= "offoff"
clockLightSetOverWriteOld	= ""
LEDintensityFactorOld		= ""
LEDintensityFactor			= "offoff"
lastButtonTime				= {"setA": 0,"setB":0,"setC":0,"UP":0,"DOWN":0}
oldRaw						= ""
lastRead					= 0
clockMode					= "run"
clockDict					= {}
speed						= 1
speedOfChange				= 0
lastCl						= ""
devTypeLEDs					= "start"
inpRaw						= ""
inp							= ""
debug						= 5
first						= False
sensor						= G.program
eth0IP						=""
wifi0IP						=""
U.setLogging()

# check for corrupt parameters file 
U.checkParametersFile(force = False)

readLocalParams()

if readParams() ==3:
		U.logger.log(30," parameters not defined")
		U.checkParametersFile( force = True)
		time.sleep(20)
		U.restartMyself(param=" bad parameters read", reason="")
	

myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running

U.killOldPgm(myPID,"neopixel.py",verbose=True)

readMarksFile()
getCurrentPatterns()

U.echoLastAlive(G.program)

setupGPIOs()

#save old wifi setting
subprocess.call('cp /etc/network/interfaces '+G.homeDir+'interfaces-old', shell=True)

# stop x11 vnc listener
#subprocess.call('sudo systemctl stop vncserver-x11-serviced.service', shell=True)

	
maxWifiAdHocTime	= 12
if U.whichWifi() == "normal":
	adhocWifiStarted = -1
	adhocWifiStartedLastTest = 99999999999999999999.
else:
	adhocWifiStarted			= time.time()
	adhocWifiStartedLastTest = int(time.time())
	afterAdhocWifistartedSetLED(maxWifiAdHocTime)

		
slTime 			= 1.5
sleepTime		= slTime

G.lastAliveSend	= time.time() -1000
loopCounter			= 0

lastWIFITest	= -1
lastShutDownTest = -1
lastRebootDownTest = -1

lastRESETTest	= -1
lastSnakeTest	= -1
lastConfigtest	= -1

U.testNetwork()

U.getIPNumber() 
eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()

U.logger.log(30,"adhocWifiStarted:{}; networkStatus:{}; ipOfRouter{}".format(adhocWifiStarted, G.networkStatus, G.ipOfRouter)) 



U.checkParametersFile()

getCurrentPatterns()
updatewebserverStatus()
webServerInputExtraText()

showIPnumber()



sendClockevery = 300
while True:
	loopCounter += 1
	sleepTime = slTime
	try:
	
	
		if networkIndicatorON > 0 and (time.time() > networkIndicatorON) :
			setExtraLEDoff() 
			networkIndicatorON = -1
			startNEOPIXEL(calledFrom="start of loop, tt > networkIndicatorON ", force=True)

		if loopCounter % 600 ==0:	 ### every 10 minutes check if parametersfile is ok, if not, restore default 
			U.checkParametersFile()

		if readCommand(): 
			pass
				
		if loopCounter % 10 ==0: # every 30 secs read parameters file 
			timeZoneOpsys = U.getTZ()
			if "timeZone" not in clockDict:
				U.logger.log(10,  "tz:{}<< timeZone not in clockDict".format(timeZoneOpsys))
			else:
				U.logger.log(10,  "tz:{}<< clockDict>>{}<<".format(timeZoneOpsys, clockDict["timeZone"]))
			updatewebserverStatus()
			webServerInputExtraText()
			# set neopixel params file if not set for 1 minutes 

			if timeWait > 0 or os.path.isfile(G.homeDir+"temp/neopixel.waiting"):
				if os.path.isfile(G.homeDir+"temp/neopixel.waiting"):
					timeWait = 0

				elif time.time() - timeWait  < 0:
					time.sleep(3)
					lastNeoParamsSet = time.time() - (sendClockevery-5) # skip next checks
				else:
					lastNeoParamsSet = time.time() - (sendClockevery-1) # skip this check for new startNEOPIXEL
					timeWait = 0

			if time.time() - lastNeoParamsSet > sendClockevery or os.path.isfile(G.homeDir+"temp/neopixel.waiting"): 
				timeWait = 0
				setExtraLEDoff() 
				startNEOPIXEL(calledFrom=" > 300 secs", force=True)


			ret = readParams() 
			if ret == 1: 
				startNEOPIXEL(calledFrom="readParams ==1", force=True)
			elif ret == 2: 
				U.restartMyself(reason="restarting due to new device specs")
			elif ret == 3: 
				U.checkParametersFile()
				time.sleep(20) # wait for some time for good parameters
				U.restartMyself(param=" bad parameters read", reason="")
	
		if U.checkifRebooting():
			signalShutDown()
			exit()
			
	
		if loopCounter % 5 == 0: # every 5 secs read parameters file 
			setLightfromSensor()
			U.echoLastAlive(G.program)
			updatewebserverStatus()
		time.sleep(sleepTime)


		#						A B C   up or dn
		#	shutdown:			0 0 0 + ^ ^
		#	RESET:				0 0 1 + ^ ^
		#	RESTART:			0 1 0 + ^ ^

		#	Show IP#			0 1 1 + ^

		#	toggle Min#			1 0 0 + ^
		#	toggle hour#		1 0 0 +   ^
		#	toggle marks#		1 0 0 + ^ ^

		#	toggle snake#		1 1 0 + ^    	red  3/12/24/60  for 80 secs
		#	toggle snake#		1 1 0 +   ^  	blue 3/12/24/60  for 80 secs 
		#	toggle snake#		1 1 0 + ^ ^  	color 3/12/24/60 for 80 secs

		#	START AdHoc WiFi	1 1 1 + ^ ^
		#

		### test for shutdown
		if GPIO.input(gpiopinSET["setA"]) == 0 and GPIO.input(gpiopinSET["setB"]) == 0 and GPIO.input(gpiopinSET["setC"]) == 0: 
			if GPIO.input(gpiopinSET["up"]) == 0 and GPIO.input(gpiopinSET["down"]) == 0 :
				lastRebootDownTest += 1
				if lastRebootDownTest > 2:
					U.logger.log(20,  "shutdown pressed")
					signalShutDown()
					shutdown()
			else:
				lastRebootDownTest = 0

		### test for reset requested
		if GPIO.input(gpiopinSET["setA"]) == 0 and GPIO.input(gpiopinSET["setB"]) == 0 and GPIO.input(gpiopinSET["setC"]) == 1: 
			if GPIO.input(gpiopinSET["down"]) == 0 and	GPIO.input(gpiopinSET["up"]) == 0:
				lastRESETTest += 1
				if lastRESETTest > 4:
					signalShutDown(fast=True)
					resetEverything() # restores config files to default 
					time.sleep(10) # should not come back
					U.restartMyself(param="reset parameters", reason="")
			else:
				lastRESETTest = 0


		### test for reboot
		if GPIO.input(gpiopinSET["setA"]) == 0 and GPIO.input(gpiopinSET["setB"]) == 1 and GPIO.input(gpiopinSET["setC"]) == 0: 
			if GPIO.input(gpiopinSET["up"]) == 0 and GPIO.input(gpiopinSET["down"]) == 0 :
				lastShutDownTest += 1
				if lastShutDownTest > 2:
					U.logger.log(20,  "reboot pressed")
					signalShutDown()
					reboot()
			else:
				lastShutDownTest = 0


		### show network
		if GPIO.input(gpiopinSET["setA"]) == 0 and GPIO.input(gpiopinSET["setB"]) == 1 and GPIO.input(gpiopinSET["setC"]) == 1: 
			if GPIO.input(gpiopinSET["down"]) == 0 or	GPIO.input(gpiopinSET["up"]) == 0:
				showIPnumber()
				time.sleep(10) # should not come back


		###  show snakes
		if GPIO.input(gpiopinSET["setA"]) == 1 and GPIO.input(gpiopinSET["setB"]) == 1 and GPIO.input(gpiopinSET["setC"]) == 0: 
			if GPIO.input(gpiopinSET["down"]) == 0 and	GPIO.input(gpiopinSET["up"]) == 1:
				lastSnakeTest += 1
				if lastSnakeTest == 2:
					toggleSnake("r", 80 )
					time.sleep(1)

			elif GPIO.input(gpiopinSET["down"]) == 1 and	GPIO.input(gpiopinSET["up"]) == 0:
				lastSnakeTest += 1
				if lastSnakeTest == 2:	
					toggleSnake("b", 80 )
					time.sleep(1)

			elif GPIO.input(gpiopinSET["down"]) == 0 and	GPIO.input(gpiopinSET["up"]) == 0:
				lastSnakeTest += 1
				if lastSnakeTest == 2:
					toggleSnake("c", 80 )
					time.sleep(1)

			else: lastSnakeTest = 0


		###  toggle config
		if GPIO.input(gpiopinSET["setA"]) == 1 and GPIO.input(gpiopinSET["setB"]) == 0 and GPIO.input(gpiopinSET["setC"]) == 0: 
			if GPIO.input(gpiopinSET["down"]) == 0 and	GPIO.input(gpiopinSET["up"]) == 1:
				lastConfigtest += 1
				if lastConfigtest == 2:	
					toggleModes("MM")
					time.sleep(1)
				

			elif GPIO.input(gpiopinSET["down"]) == 1 and	GPIO.input(gpiopinSET["up"]) == 0:
				lastConfigtest += 1
				if lastConfigtest == 2:	
					toggleModes("HH")
					time.sleep(1)

			elif GPIO.input(gpiopinSET["down"]) == 0 and	GPIO.input(gpiopinSET["up"]) == 0:
				lastConfigtest += 1
				if lastConfigtest == 2:
					toggleModes("Marks")
					time.sleep(1)

			else:	lastConfigtest = 0

		###  LED on/off
		if GPIO.input(gpiopinSET["setA"]) == 1 and GPIO.input(gpiopinSET["setB"]) == 0 and GPIO.input(gpiopinSET["setC"]) == 1: 
			#U.logger.log(20,  "gpio values: A:{} b:{} C:{} U:{} D:{}".format(GPIO.input(gpiopinSET["setA"]), GPIO.input(gpiopinSET["setB"]),GPIO.input(gpiopinSET["setC"]),GPIO.input(gpiopinSET["up"]),GPIO.input(gpiopinSET["down"])))
			if GPIO.input(gpiopinSET["down"]) == 0 and	GPIO.input(gpiopinSET["up"]) == 1:
				lastConfigtest += 1
				if lastConfigtest == 2:	
					clockDict["lightOnOff"] = 1
					saveParameters()
					startNEOPIXEL(calledFrom="set LED on", force=True)

			elif GPIO.input(gpiopinSET["down"]) == 1 and	GPIO.input(gpiopinSET["up"]) == 0:
				lastConfigtest += 1
				if lastConfigtest == 2:	
					clockDict["lightOnOff"] = 0
					saveParameters()
					startNEOPIXEL(calledFrom="set LED off", force=True)

			else:	lastConfigtest = 0


		### test for wifi adhoc setup requested ... and reset to regular wifi after reboot 
		if GPIO.input(gpiopinSET["setA"]) == 1 and GPIO.input(gpiopinSET["setB"]) == 1 and GPIO.input(gpiopinSET["setC"]) == 1: 
			if GPIO.input(gpiopinSET["up"]) == 0  and GPIO.input(gpiopinSET["up"]) == 0 :
				lastWIFITest +=  1
				if lastWIFITest > 4: 
					U.logger.log(20,  "wifi adhoc start pressed")
					if adhocWifiStarted ==-1: 
						afterAdhocWifistartedSetLED(maxWifiAdHocTime)
						startNEOPIXEL(calledFrom="read command", force=True)
						time.sleep(2)
						U.setStartAdhocWiFi()
						adhocWifiStarted = time.time()
			else:
				lastWIFITest = 0

		if adhocWifiStarted > 10:
			if (time.time() - adhocWifiStarted >maxWifiAdHocTime*60 ): # reset wifi after maxWifiAdHocTime minutes
				U.setStopAdhocWiFi() 
			iTT= int(time.time())
			if	iTT	 - adhocWifiStartedLastTest > 60: # count down LEDs
				l1 = maxWifiAdHocTime - (iTT - int(adhocWifiStarted))/60
				afterAdhocWifistartedSetLED(l1)
				startNEOPIXEL(calledFrom="count down leds", force=True)
				adhocWifiStartedLastTest = iTT


		#U.logger.log(20,  "gpio values: A:{} b:{} C:{} U:{} D:{}".format(GPIO.input(gpiopinSET["setA"]), GPIO.input(gpiopinSET["setB"]),GPIO.input(gpiopinSET["setC"]),GPIO.input(gpiopinSET["up"]),GPIO.input(gpiopinSET["down"])))

			
	except Exception as e:
		U.logger.log(30,"except at end of loop", exc_info=True)
		time.sleep(10.)
		if "{}".format(e).find("string indices must be integers") >-1:
			U.logger.log(30,"clockDict: {}<<".format(clockDict) )
			U.logger.log(30,"inp: {}<<".format(inp))
			U.restartMyself(reason=" string error")
sys.exit(0)
