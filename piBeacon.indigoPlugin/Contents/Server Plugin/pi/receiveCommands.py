#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7 
##
try: 	import SocketServer as socketserver
except: import socketserver
import re
import json, sys,subprocess, os, time, datetime
import copy
import smbus
import threading
try: import Queue
except: import queue as Queue

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)



sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "receiveCommands"

allowedCommands=["up","down","pulseUp","pulseDown","continuousUpDown","analogWrite","disable","myoutput","omxplayer","display","newMessage","resetDevice",
				"startCalibration","getBeaconParameters","beepBeacon","updateTimeAndZone","file","BLEreport","BLEAnalysis","trackMac"]

externalGPIO = False

####-------------------------------------------------------------------------####
def readPopen(cmd):
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception as e:
			U.logger.log(20,"", exc_info=True)

### ----------------------------------------- ###
### ---------exec commands start------------- ###
### ----------------------------------------- ###

### ----------------------------------------- ###
def OUTPUTi2cRelay(command):
	global myPID
	global threadsActive
	try:
		devType = "OUTPUTi2cRelay"

		for iii in range(1):
			U.logger.log(G.debug*20, "OUTPUTi2cRelay command:{}".format(command) )
			if "cmd" in command:
				cmd= command["cmd"]
				if cmd not in allowedCommands:
					U.logger.log(20, "OUTPUTi2cRelay pid={}d, bad command {}  allowed only: {}".format(myPID, command , allowedCommands )  )
					exit(1)

			if "pin" in command:
				pin= int(command["pin"])
			else:
				U.logger.log(20, "setGPIO pid={}, pin not included,  bad command {}".format(myPID,command) )
				exit(1)

			DEVICE_BUS = 1
			bus = smbus.SMBus(DEVICE_BUS)

			i2cAddress = int(command["i2cAddress"])
			pin = command["pin"]


			delayStart = max(0, U.calcStartTime(command,"startAtDateTime")-time.time())
			if delayStart > 0 and delayStart < 10000000: 
				if sleepForxSecs(delayStart):
					return 

			if "values" in command:
				values =  command["values"]
			else: 
				values =""
	
			try:
				if "pulseUp" in values:		pulseUp = float(values["pulseUp"])
				else:						pulseUp = 0
				if "pulseDown" in values:	pulseDown = float(values["pulseDown"])
				else:						pulseDown = 0
				if "nPulses" in values:		nPulses = int(values["nPulses"])
				else:						nPulses = 0
			except	Exception as e:
				U.logger.log(30,"", exc_info=True)
				exit(0)

			inverseGPIO = False
			if "inverseGPIO" in command:
				inverseGPIO = command["inverseGPIO"]

			if "devId" in command:
				devId = str(command["devId"])
			else: devId = "0"


			try:
				if inverseGPIO: 
					up   = 0x00
					down = 0xff
					on   = "low"
					off  = "high" 
				else:
					up   = 0xff
					down = 0x00
					on   = "high"
					off  = "low" 

				if cmd == "up":
					bus.write_byte_data(i2cAddress, pin, up)
					U.logger.log(20, "relay {} {} {} ".format(i2cAddress, pin, up))
					if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})

				elif cmd == "down":
					U.logger.log(20, "relay {} {} {} ".format(i2cAddress, pin, down))
					bus.write_byte_data(i2cAddress, pin,down)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})

				elif cmd == "pulseUp":
					bus.write_byte_data(i2cAddress, pin, up)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})
					if sleepForxSecs(pulseUp): break
					bus.write_byte_data(i2cAddress, pin, down)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})

				elif cmd == "pulseDown":
					bus.write_byte_data(i2cAddress, pin, down)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})
					if sleepForxSecs(pulseDown): break
					bus.write_byte_data(i2cAddress, pin, up)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})

				elif cmd == "continuousUpDown":
					for ii in range(nPulses):

						bus.write_byte_data(i2cAddress, pin, up)

						if sleepForxSecs(pulseUp): break

						bus.write_byte_data(i2cAddress, pin, down)

						if sleepForxSecs(pulseDown): break

				U.removeOutPutFromFutureCommands(pin, devType)
			

			except Exception as e:
					U.logger.log(40,"", exc_info=True)
	except Exception as e:
			U.logger.log(40,"", exc_info=True)


### ----------------------------------------- ###
def setGPIO(command):
	global PWM, myPID, typeForPWM
	global threadsActive
	devType = "OUTPUTgpio"


	G.debug = 20
	myDebug = G.debug
	#U.logger.log(G.debug*20, "{:.2f} into setGPIO ".format(time.time()) )

	for iiii in range(1):
		try:	PWM= command["PWM"] *100
		except: PWM = 100



		if typeForPWM == "PIGPIO" and U.pgmStillRunning("pigpiod"):
			import pigpio
			PIGPIO = pigpio.pi()
			pwmRange  = PWM
			pwmFreq   = PWM
			typeForPWM = "PIGPIO"
		else:
			typeForPWM = "GPIO"
		

		if "cmd" in command:
			cmd= command["cmd"]
			if cmd not in allowedCommands:
				U.logger.log(20, "setGPIO pid={}, bad command{}  allowed only: {}".format(myPID, command, allowedCommands)  )
				exit(1)

		if "pin" in command:
			pin= int(command["pin"])
		else:
			U.logger.log(20, "setGPIO pid={}, pin not included,  bad command {}".format(myPID, command) )
			exit(1)



		delayStart = min(1000000, max(0,U.calcStartTime(command,"startAtDateTime")-time.time()))
		if delayStart > 0 and delayStart < 10000000: 
			if sleepForxSecs(delayStart):
				return 

		if "values" in command:
			values =  command["values"]

		#	 "values:{analogValue:"analogValue+",pulseUp:"+ pulseUp + ",pulseDown:" + pulseDown + ",nPulses:" + nPulses+"}

		try:
			if "pulseUp" in values:		pulseUp = float(values["pulseUp"])
			else:						pulseUp = 0
			if "pulseDown" in values:	pulseDown = float(values["pulseDown"])
			else:						pulseDown = 0
			if "nPulses" in values:		nPulses = int(values["nPulses"])
			else:						nPulses = 0
			if "analogValue" in values: bits = max(0.,min(100.,float(values["analogValue"])))
			else:						bits = 0
		except	Exception as e:
			U.logger.log(30,"", exc_info=True)
			exit(0)

		inverseGPIO = False
		if "inverseGPIO" in command:
			inverseGPIO = command["inverseGPIO"]

		if "devId" in command:
			devId = str(command["devId"])
		else: devId = "0"

		U.logger.log(myDebug, "{:.2f} bf  GPIO.setup, cmd:{}, pin:{}, command:{} ".format(time.time(), cmd, pin, command) )
		try:
			if inverseGPIO: 
				up   = 0
				down = 1
				on   = "low"
				off  = "high" 
			else:
				up   = 1
				down = 0
				on   = "high"
				off  = "low" 

			if cmd == "up":
				GPIO.setup(pin, GPIO.OUT)
				GPIO.output(pin, up)
				U.logger.log(myDebug, "{:.2f} setGPIO pin={}; set output to {}".format(time.time(), pin, on) )
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})
		

			elif cmd == "down":
				GPIO.setup(pin, GPIO.OUT)
				GPIO.output(pin, down)
				U.logger.log(myDebug, "{:.2f} setGPIO pin={}; set output to {}".format(time.time(), pin, off) )
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})

			elif cmd == "analogWrite":
				if inverseGPIO:
					value = (100-bits)	# duty cycle on xx hz
				else:
					value =   bits	 # duty cycle on xxx hz 
				value = int(value)
				U.logger.log(myDebug, "analogwrite pin = {};    duty cyle: {};  PWM={}; using {}".format(pin, value, PWM, typeForPWM) )
				if value > 0:
					U.sendURL({"outputs":{"OUTPUTgpio-1":{devId:{"actualGpioValue":"high"}}}})
				else:
					U.sendURL({"outputs":{"OUTPUTgpio-1":{devId:{"actualGpioValue":"low"}}}})

				if typeForPWM == "PIGPIO": 	
					#U.logger.log(20, "..  setting PIGPIO {}  {}  {}".format(pwmFreq, pwmRange,  value) )
					PIGPIO.set_mode(pin, pigpio.OUTPUT)
					PIGPIO.set_PWM_frequency(pin, pwmFreq)
					PIGPIO.set_PWM_range(pin, pwmRange)
					PIGPIO.set_PWM_dutycycle(pin, value)

				else:
					GPIO.setup(pin, GPIO.OUT)
					p = GPIO.PWM(pin, PWM)	# 
					p.start(int(value))	 # start the PWM with  the proper duty cycle
				if sleepForxSecs(1000000000): break

			elif cmd == "pulseUp":
				GPIO.setup(pin, GPIO.OUT)
				GPIO.output(pin, up)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})
				if sleepForxSecs(pulseUp): break
				GPIO.output(pin, down)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})

			elif cmd == "pulseDown":
				GPIO.setup(pin, GPIO.OUT)
				GPIO.output(pin, down)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
				if sleepForxSecs(pulseDown): break
				GPIO.output(pin, up)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})

			elif cmd == "continuousUpDown":
				GPIO.setup(pin, GPIO.OUT)
				U.logger.log(myDebug, "continuousUpDown pin = {} start, pulseUp:{}, pulseDown:{}, nPulses:{}".format(pin,  pulseUp, pulseDown, nPulses, inverseGPIO) )
				for ii in range(nPulses):
					GPIO.output(pin, up)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})
					if sleepForxSecs(pulseUp): break
					GPIO.output(pin, down)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
					if sleepForxSecs(pulseDown): break
				U.logger.log(myDebug, "continuousUpDown finished" )


		except	Exception as e:
			U.logger.log(30,"", exc_info=True)

	U.logger.log(myDebug, "exit {}".format(command) )
	U.removeOutPutFromFutureCommands(pin, devType)

	return 


### ----------------------------------------- ###
def sleepForxSecs(sleepTime):
	global threadsActive
	try:
		tDone 	= 0
		dt 		= 0.05
		try: threadName = threading.currentThread().getName()
		except: return True
		#U.logger.log(20, u"threadName:{}, wait for {} secs".format(threadName, sleepTime))
		while True:
			tDone += dt
			if threadName not in threadsActive: return True
			if threadsActive[threadName]["state"] != "running": return True 
			time.sleep(dt)
			if sleepTime <= tDone: return False
		return False
	except	Exception as e:
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20, u"threadsActive{}".format(threadsActive))
	return False

### ----------------------------------------- ###
def execCMDS(next):
	global threadsActive
	global execcommands, PWM
	global py3Cmd, readOutput, readInput
	global usePython3

	threadName = threading.currentThread().getName()
	#U.logger.log(G.debug*20, u"{:.2f} into execCMDS, thread name:{}".format(time.time(), threadName))

	for ijji in range(1):

			#U.logger.log(20,"{:.2f} next command: {}".format(time.time(), next))
			cmd = next["command"]

			for cc in next:
				if cc == "startAtDateTime":
					next["startAtDateTime"] = time.time() + next["startAtDateTime"]
				


			if "restoreAfterBoot" in next:
				restoreAfterBoot= next["restoreAfterBoot"]
			else:
				restoreAfterBoot="0"


			if cmd =="general":
				if "cmdLine" in next:
					subprocess.call(next["cmdLine"] , shell=True)	 
					continue


			if cmd == "file":
				if "fileName" in next and "fileContents" in next:
					#print next
					try:
						m = "w"
						if "fileMode" in next and next["fileMode"].lower() == "a": m = "a"
						fc = json.dumps(next["fileContents"])
						U.logger.log(20,"write to next {}  {}".format(next["fileName"], fc ))
						f = open(next["fileName"], m)
						f.write("{}".format(fc)) 
						f.close()
						if "touchFile" in next and next["touchFile"]:
							subprocess.call("echo	 "+str(time.time())+" > "+G.homeDir+"temp/touchFile" , shell=True)
						subprocess.call("sudo chown -R  pi  "+G.homeDir, shell=True)
					except	Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if cmd == "getBeaconParameters":
				try:
						U.logger.log(20, u"execcmd. getBeaconParameters, write: ={}".format(next["device"]))
						f = open(G.homeDir+"temp/beaconloop.getBeaconParameters","w")
						f.write(next[u"device"]) 
						f.close()
				except	Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if cmd == "beepBeacon":
				try:
						U.logger.log(20, u"execcmd. beep, write: ={}".format(next["device"]))
						f = open(G.homeDir+"temp/beaconloop.beep","a")
						f.write(next["device"]+"\n") 
						f.close()
				except	Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if cmd == "updateTimeAndZone":
				try:
						U.logger.log(20, u"execcmd. updateTimeAndZone, write: ={}".format(next["device"]))
						f = open(G.homeDir+"temp/beaconloop.updateTimeAndZone","a")
						f.write(next["device"]+"\n") 
						f.close()
				except	Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue

			if	cmd == "BLEAnalysis":
					if "minRSSI" not in next: minRSSI = "-61"
					else:					  minRSSI = next["minRSSI"]
					subprocess.call("echo "+minRSSI+" > "+G.homeDir+"temp/beaconloop.BLEAnalysis", shell=True)
					continue

			if	cmd == "trackMac":
					if "mac" in next: 
						subprocess.call("echo '"+next["mac"]+"' > "+G.homeDir+"temp/beaconloop.trackmac", shell=True)
					else:
						U.logger.log(20, u"trackMac, no mac number supplied")
					continue


			if "device" not in next:
				U.logger.log(20," bad cmd no device given {}".format(next))
				continue
				

			device = next["device"]

			
			if device.lower()=="setsteppermotor":
				cmdOut = json.dumps(next)
				if cmdOut != "":
					try:
						f=open(G.homeDir+"temp/setStepperMotor.inp","a")
						f.write(cmdOut+"\n")
						f.close()
					except	Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue
			
			if device.lower()=="output-display":
				cmdOut = json.dumps(next)
				if cmdOut != "":
					try:
						#print "execcmd", cmdOut
						if not U.pgmStillRunning("display.py"):
							subprocess.call("{} {}display.py &".format(py3Cmd, G.homeDir), shell=True)
						f=open(G.homeDir+"temp/display.inp","a")
						f.write(cmdOut+"\n")
						f.close()
						f=open(G.homeDir+"display.inp","w")
						f.write(cmdOut+"\n")
						f.close()
					except	Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if device.lower().find("neopixel") > -1:### OUTPUT-neopixel
				cmdOut = json.dumps(next)
				if "neopixel" not in output: continue
				if usePython3:	py2orpy3 = "py3"
				else:			py2orpy3 = "py2"
				#U.logger.log(30,"usePython3:{}, py2orpy3:{}".format(usePython3,py2orpy3 ))

				if cmdOut != "":
					try:
						if py2orpy3 == "py2":
							py = "/usr/bin/python "
							pgm ="neopixel2.py"
						else:							
							py = "/usr/bin/python3 "
							pgm ="neopixel3.py"
						if	not U.pgmStillRunning(pgm[:-3]+".py"):
							subprocess.call("{}{}{} &".format(py, G.homeDir, pgm), shell=True)
							U.logger.log(20,">>>>>> starting pgm: {}{}{} &".format(py, G.homeDir, pgm))
						else:
							f=open(G.homeDir+"temp/neopixel.inp","a")
							f.write(cmdOut+"\n")
							f.close()
							f=open(G.homeDir+"neopixel.inp","w")
							f.write(cmdOut+"\n")
							f.close()
					except	Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if cmd not in allowedCommands:
				U.logger.log(20,"bad cmd (9) dev:{} not in allowed commands {} \n{}".format(device, cmd,  allowedCommands))
				continue


			if "values" in next:
				values = next["values"]
			else:
				values =""

			startAtDateTime = "{}".format(time.time())
			if "startAtDateTime" in next:
				startAtDateTime = next["startAtDateTime"]

			if "inverseGPIO" in next:
				inverseGPIO = next["inverseGPIO"]
			else:
				inverseGPIO = False


			if "devId" in next:
				devId = next["devId"]
			else:
				devId = 0




			if	cmd == "newMessage":
						if next["device"].find(",")> 1:
							list = next["device"].split(",")
						elif next["device"]== "all":
							list = G.programFiles + G.specialSensorList + G.specialOutputList + G.programFiles
						else:
							list = [next["device"]]
						for pgm in list:
							subprocess.call("echo x > "+G.homeDir+"temp/"+pgm+".now", shell=True)
						continue


			if	cmd == "resetDevice":
						if next["device"].find(",")> 1:
							list = next["device"].split(",")
						elif next["device"]== "all":
							list = G.programFiles + G.specialSensorList + G.specialOutputList + G.programFiles
						else:
							list = [next["device"]]
						for pgm in list:
							subprocess.call("echo x > "+G.homeDir+"temp/"+pgm+".reset", shell=True)
						continue




			if	cmd == "startCalibration":
						if next["device"].find(",")> 1:
							list = next["device"].split(",")
						elif next["device"]== "all":
							list = G.specialSensorList
						else:
							list = [next["device"]]
						for pgm in list:
							subprocess.call("echo x > "+G.homeDir+"temp/"+pgm+".startCalibration", shell=True)
						continue




			if device=="setMCP4725":
						try:
							i2cAddress = U.getI2cAddress(next, default =0)
							if cmd =="disable" :
								if sthreadName in execcommandsList:
									del execcommandsList[threadName]

							cmdJ= json.dumps({"cmd":cmd,"i2cAddress":i2cAddress,"startAtDateTime":startAtDateTime,"values":values, "devId":devId })
							U.logger.log(10,json.dumps(next))
							cmdOut="/usr/bin/python "+G.homeDir+"setmcp4725.py '"+ cmdJ+"'  &"
							U.logger.log(10," cmd= %s"%cmdOut)
							subprocess.call(cmdOut, shell=True)
							if restoreAfterBoot == "1":
								execcommandsList[threadName] = next
							else:
								try: del execcommandsList[threadName]
								except:pass

						except	Exception as e:
							U.logger.log(30,"", exc_info=True)
						continue

			if device=="setPCF8591dac":
						try:
							i2cAddress = U.getI2cAddress(next, default =0)
							if cmd =="disable":
								del execcommandsList[threadName]
								continue
							cmdJ= json.dumps({"cmd":cmd,"i2cAddress":i2cAddress,"startAtDateTime":startAtDateTime,"values":values, "devId":devId})
							U.logger.log(10,json.dumps(next))
							cmdOut="/usr/bin/python "+G.homeDir+"setPCF8591dac.py '"+ cmdJ+"'  &"
							U.logger.log(10," cmd= %s"%cmdOut)
							subprocess.call(cmdOut, shell=True)
							if restoreAfterBoot == "1":
								execcommandsList[threadName] = next
							else:
								try: del execcommandsList[threadName]
								except:pass

						except	Exception as e:
							U.logger.log(30,"", exc_info=True)
						continue


			if device=="OUTgpio" or device.find("OUTPUTgpio")> -1:
						#U.logger.log(G.debug*20, u"{:.2f} into if OUTgpio".format(time.time()))
						try:
							pinI = int(next["pin"])
							pin = str(pinI)
						except	Exception as e:
							U.logger.log(30,"", exc_info=True)
							U.logger.log(20,"bad pin {}".format(next))
							continue
						#print "pin ok"
						if "values" in next: values= next["values"]
						else:				 values= {}
   
						if restoreAfterBoot == "1":
							execcommandsList[threadName] = next
						else:
							try: del execcommandsList[threadName]
							except: pass
						if cmd == "disable":
							continue
						cmdJ= {"pin":pin,"cmd":cmd,"startAtDateTime":startAtDateTime,"values":values, "inverseGPIO": inverseGPIO,"debug":G.debug,"PWM":PWM, "devId":devId}
						setGPIO(cmdJ)
						continue


			if  device.find("OUTPUTi2cRelay")> -1:
						try:
							pinI = int(next["pin"])
							pin = str(pinI)
						except	Exception as e:
							U.logger.log(30,"", exc_info=True)
							U.logger.log(20,"bad pin {}".format(next))
							continue
						#print "pin ok"
						if "values" in next: values= next["values"]
						else:				 values={}
   
						if restoreAfterBoot == "1":
							execcommandsList[threadName] = next

						else:
							try: del execcommandsList[threadName]
							except: pass

						if cmd =="disable":
							continue
						cmdJ= {"pin":pinI,"cmd":cmd,"startAtDateTime":startAtDateTime,"values":values, "inverseGPIO": inverseGPIO,"debug":G.debug,"i2cAddress":next["i2cAddress"], "devId":devId}

						OUTPUTi2cRelay(cmdJ)
						continue

			if device=="myoutput":
						try:
							text   = next["text"]
							cmdOut= "/usr/bin/python "+G.homeDir+"myoutput.py "+text+" &"
							U.logger.log(10,"cmd= %s"%cmdOut)
							subprocess.call(cmdOut, shell=True)
						except	Exception as e:
							U.logger.log(30,"", exc_info=True)
						continue

			if device=="playSound":
						cmdOut=""
						try:
							if	 cmd  == "omxplayer":
								cmdOut = json.dumps({"player":"omxplayer","file":G.homeDir+"soundfiles/"+next["soundFile"]})
							elif cmd  == "aplay":
								cmdOut = json.dumps({"player":"aplay","file":G.homeDir+"soundfiles/"+next["soundFile"]})
							else:
								U.logger.log(20, u"bad command : player not right =" + cmd)
							if cmdOut != "":
								U.logger.log(10,"cmd= %s"%cmdOut)
								subprocess.call("/usr/bin/python playsound.py '"+cmdOut+"' &" , shell=True)
						except	Exception as e:
							U.logger.log(30,"", exc_info=True)
						continue

			U.logger.log(20,"bad device number/number: "+device)
	if len(execcommandsList) >0:
		f = open(G.homeDir+"execcommandsList.current","w")
		f.write(json.dumps(execcommandsList))
		f.close()
	stopExecCmd(threadName)

	return

				 
### ----------------------------------------- ###
def stopThreadsIfEnded(all=False):
	global threadsActive
	try:
		stopThreads = {}
		for threadName in threadsActive:
			if all: stopThreads[threadName] = True

			elif threadsActive[threadName]["state"] != "running":
				stopThreads[threadName] = True

		for threadName in stopThreads:
			stopExecCmd(threadName)
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)

				 
### ----------------------------------------- ###
def execSimple(next):
	global inp
	if "command" not in next:		 return False
	if next["command"] != "general": return False
	if "cmdLine" not in next:		 return False
	
	try:
		# execute unix command
		if next["cmdLine"].lower().find("sudo reboot" )> -1 or next["cmdLine"].lower().find("sudo halt") > -1:
			stopThreadsIfEnded(all=True)
			subprocess.call(next["cmdLine"] , shell=True)	 


			return True
			
		# execute set time command 
		if next["cmdLine"].find("setTime")>-1:
			tt		   = time.time()
			items	   =  next["cmdLine"].split("=")
			mactime	   = items[1]
			subprocess.call('date -s "'+mactime+'"', shell=True)
			mactt	   = U.getTimetimeFromDateString(mactime)
			deltaTime  = tt - mactt
			U.sendURL(data={"deltaTime":deltaTime},sendAlive="alive", wait=False)
			if "useRTC" in inp and inp["useRTC"] !="":
				subprocess.call("hwclock --systohc", shell=True) # set hw clock to system time stamp, only works if HW is enabled
			return True
		# execute set time command 
		if next["cmdLine"].find("refreshNTP")>-1:
			U.startNTP()
			return True
		if next["cmdLine"].find("stopNTP")>-1:
			U.stopNTP()
			return True

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return False

	### ----------------------------------------- ###
	### ---------exec commands end -------------- ###
	### ----------------------------------------- ###




class MyTCPHandler(socketserver.BaseRequestHandler):

	### ----------------------------------------- ###
	def handle(self):
		global threadsActive
		# self.request is the TCP socket connected to the client
		data = ""
		while True:
			buffer = self.request.recv(2048).decode('utf_8')
			#U.logger.log(10, "len of buffer:"+str(len(buffer)))
			if not buffer:
				break
			data += buffer.strip()
		
		#U.logger.log(20, u"===== ip:{}:  data:{}<\n\n".format(self.client_address[0], data))
		try:
			commands = json.loads(data.strip("\n"))
		except	Exception as e:
				U.logger.log(30,"", exc_info=True)
				U.logger.log(20,"bad command: json failed {}".format(data))
				return

		#U.logger.log(20, "{:.2f} MyTCPHandler len:{}  data:{}".format(time.time(),len(data), data) )
			
		for next in commands:
			if execSimple(next): continue
			setupexecThreads(next)
 
		readParams()
		stopThreadsIfEnded()
		return	 

### ----------------------------------------- ###
def setupexecThreads(next):
	global inp
	global threadsActive
	try:
		if "command" not in next: return False
		
		threadName = ""
		if "device" in next and next["device"] != "":				threadName = next["device"]
		if "pin" in next and next["pin"] != "": 					threadName += "-"+str(next["pin"])
		elif "i2cAddress" in next and next["i2cAddress"] != "": 	threadName += "-"+str(next["i2cAddress"])
		if threadName =="":											threadName = next["command"]

		if threadName in threadsActive:
			if threadsActive[threadName]["state"] != "stop":
				stopExecCmd(threadName)
			
		#U.logger.log(20, u"starting thread={}".format(threadName))
		threadsActive[threadName] = {"state":"running", "thread": threading.Thread(name=threadName, target=execCMDS, args=(next,))}	
		threadsActive[threadName]["thread"].daemon = True
		threadsActive[threadName]["thread"].start()

		out = "{}".format(next)
		ll = min(len(out),100)
		U.logger.log(20,"thread started: {}, command:{} ... {}".format(threadName, out[:ll], out[-ll:] ))

		return True

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return False


### ----------------------------------------- ###
def stopExecCmd(threadName):
	global inp
	global threadsActive
	try:
		if threadName in threadsActive:
			#U.logger.log(20, u"stop issuing thread={}".format(threadName))
			if threadsActive[threadName]["state"] == "stop": return 
			threadsActive[threadName]["state"] = "stop"
			time.sleep(0.07)
			#U.logger.log(20, u"stop finished after wait thread={}".format(threadName))
	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	try: 	del threadsActive[threadName]
	except: pass
	return 


### ----------------------------------------- ###
def getcurentCMDS():
	global	execcommandsList, output, execcommandsListAction
	try:
		execcommandsList = {}
		if execcommandsListAction == "delete":
			try: os.remove(G.homeDir+"execcommandsList.current")
			except:	pass
			return

		if os.path.isfile(G.homeDir+"execcommandsList.current"):
			f = open(G.homeDir+"execcommandsList.current","r")
			readCmds = f.read()
			f.close()
			use = True
			if len(readCmds) < 5: use = False 
			else:
				try:	execcommandsList = json.loads(readCmds)
				except: use = False 
			if not use:
				os.remove(G.homeDir+"execcommandsList.current")
				return 

			keep = {}	
			for threadName in execcommandsList:
				keep[threadName] = execcommandsList[threadName]
				try:
					next = execcommandsList[threadName]
				except	Exception as e:
					U.logger.log(30,"", exc_info=True)
					continue
				setupexecThreads(next)

			f = open(G.homeDir+"execcommandsList.current","w")
			f.write(json.dumps(keep))
			f.close()

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 


				 
### ----------------------------------------- ###
def readParams():
	global	output, useLocalTime, myPiNumber, inp, readOutput, readInput, execcommandsListAction, PWM, typeForPWM
	global usePython3
	inp,inpRaw = U.doRead()
	if inp == "": return

	U.getGlobalParams(inp)
	try:
		output =				inp.get("output",output)
		readOutput = 			inp.get("output",output)
		PWM =				int(inp.get("GPIOpwm",PWM))
		typeForPWM =			inp.get("typeForPWM",typeForPWM)
		execcommandsListAction=	inp.get("execcommandsListAction","delete")
		readInput  = 			inp.get("input",{})
		usePython3 =			inp.get("usePython3","") == "1"

	except	Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 

### ----------------------------------------- ###
if __name__ == "__main__":
	global	currentGPIOValue
	global execcommandsList, PWM, typeForPWM
	global threadsActive
	global py3Cmd
	global output
	global usePython3
	PWM 				= 100
	typeForPWM			= "GPIO"
	myPID				= str(os.getpid())
	threadsActive		= {}
	execcommandsList	= {}
	output				= {}

	PORT = int(sys.argv[1])

	U.setLogging()

	U.killOldPgm(myPID,G.program+".py")# del old instances of myself if they are still running

	time.sleep(0.5)
	
	readParams()

	if U.getNetwork() == "off":
		U.logger.log(20, u"network not active, sleeping ")
		time.sleep(500)# == 500 secs
		exit(0)
	# if not connected to network pass
		
		
	if G.wifiType !="normal": 
		U.logger.log(20, u"no need to receiving commands in adhoc mode pausing receive GPIO commands")
		time.sleep(500)
		exit(0)
	U.logger.log(20, u"proceding with normal on no ad-hoc network")

	U.getIPNumber()
	
	getcurentCMDS()
	py3Cmd = "/usr/bin/python"
	if sys.version[0] == "3" or usePython3:
		py3Cmd = "/usr/bin/python3"


	U.logger.log(30,"started, listening to port: "+ str(PORT))
	restartMaster = False
	try:	
		# Create the server, binding on port 9999
		server = socketserver.TCPServer((G.ipAddress, PORT), MyTCPHandler)

	except	Exception as e:
		####  trying to kill the process thats blocking the port# 
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30, "getting  socket does not work, trying to reset {}".format(PORT) )
		ret = readPopen("sudo ss -apn | grep :{}".format(PORT))[0]
		lines= ret.split("\n")
		for line in lines:
			U.logger.log(20, line) 
			pidString = line.split(",pid=")
			for ppp in pidString:
				pid = ppp.split(",")[0]
				if pid == myPID: continue
				try:
					pid = int(pid)
					if pid < 99: continue
				except: continue

				if len (subprocess.Popen("ps -ef | grep "+str(pid)+"| grep -v grep | grep master.py",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]) >5:
					restartMaster=True
					# will need to restart the whole things
				U.logger.log(20, "killing task with : pid= %d"% pid )
				ret = subprocess.Popen("sudo kill -9 "+str(pid),shell=True)
				time.sleep(0.2)


		if restartMaster:
			U.logger.log(20, "killing taks with port = "+str(PORT)+"	 did not work, restarting everything")
			subprocess.Popen("/usr/bin/python "+G.homeDir+"master.py  &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			exit()
			
		try:	
			# Create the server, binding on port eg 9999
			server = socketserver.TCPServer((G.ipAddress, PORT), MyTCPHandler)
		except	Exception as e:
			U.logger.log(20, "getting  socket does not work, try restarting master  "+ str(PORT) )
			subprocess.Popen("/usr/bin/python "+G.homeDir+"master.py  &",shell=True)
			exit()

	# Activate the server; this will keep running until you interrupt the program with Ctrl-C
	server.serve_forever()
