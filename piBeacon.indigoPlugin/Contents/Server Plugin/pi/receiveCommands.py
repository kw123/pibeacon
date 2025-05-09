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


try:
	#1/0 # use GPIO
	if subprocess.Popen("/usr/bin/ps -ef | /usr/bin/grep pigpiod  | /usr/bin/grep -v grep",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf-8').find("pigpiod")< 5:
		subprocess.call("/usr/bin/sudo /usr/bin/pigpiod &", shell=True)
	import gpiozero
	from gpiozero.pins.pigpio import PiGPIOFactory
	from gpiozero import Device
	Device.pin_factory = PiGPIOFactory()
	useGPIO = False
except:
	try:
		import RPi.GPIO as GPIO
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		useGPIO = True
	except: pass



sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G

G.program = "receiveCommands"

allowedCommands=["up","down","pulseUp","pulseDown","continuousUpDown","analogWrite","disable","myoutput","omxplayer","display","newMessage","resetDevice","restartDevice",
				"startCalibration","getBeaconParameters","beepBeacon","updateTimeAndZone","file","BLEreport","BLEAnalysis","trackMac"]

externalGPIO = False

mapCmds			= {"pu":"pulseUp","pd":"pulseDown","cup":"continuousUpDown","aw":"analogWrite"}
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
				cmd = command["cmd"]
				if False and cmd not in allowedCommands:
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

			pulseUp = float(command.get("pulseUp",1))
			pulseDown = float(command.get("pulseDown",1))
			nPulses = float(command.get("nPulses",1))

			if "values" in command:
				values =  command.get("values",{})
				if values != {}:
					try:
						pulseUp = float(values.get("pulseUp",1))
						pulseDown = float(values.get("pulseDown",1))
						nPulses = int(values.get("nPulses",1))
					except Exception as e:
						U.logger.log(20," error reading command values:{}".format(values))
		

			inverseGPIO = False
			if "inverseGPIO" in command:
				inverseGPIO = command["inverseGPIO"]

			if "devId" in command:
				devId = str(command["devId"])
			else: devId = "0"


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

			elif cmd in ["pulseUp","pulseup"]:
				bus.write_byte_data(i2cAddress, pin, up)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})
				if sleepForxSecs(pulseUp): break
				bus.write_byte_data(i2cAddress, pin, down)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})

			elif cmd in ["pulseDown","pulsedown"]:
				bus.write_byte_data(i2cAddress, pin, down)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})
				if sleepForxSecs(pulseDown): break
				bus.write_byte_data(i2cAddress, pin, up)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})

			elif cmd in ["continuousUpDown","continuousupdown"]:
				for ii in range(nPulses):

					bus.write_byte_data(i2cAddress, pin, up)

					if sleepForxSecs(pulseUp): break

					bus.write_byte_data(i2cAddress, pin, down)

					if sleepForxSecs(pulseDown): break

			U.removeOutPutFromFutureCommands(pin, devType)
			
	except Exception as e:
			U.logger.log(40,"", exc_info=True)


### ----------------------------------------- ###
def setGPIO(command):
	global PWM, myPID, typeForPWM
	global threadsActive
	devType = "OUTPUTgpio"


	GPIOZERO = ""
	G.debug = 20
	myDebug = G.debug
	#U.logger.log(20, "{:.2f} into setGPIO command:{}".format(time.time() , command))

	for iiii in range(1):
		try:	PWM = int(command["PWM"])
		except: PWM = 100



		if typeForPWM == "PIGPIO" and U.pgmStillRunning("pigpiod"):
			import pigpio
			PIGPIO 		= pigpio.pi()
			pwmRange  	= PWM
			pwmFreq   	= PWM
			typeForPWM 	= "PIGPIO"
		else:
			typeForPWM 	= "GPIO"
		


		if "cmd" in command:
			cmd = command["cmd"]
			if False and cmd not in allowedCommands:
				U.logger.log(20, "setGPIO pid={}, bad command{}  allowed only: {}".format(myPID, command, allowedCommands)  )
				exit(1)

		if "pin" in command:
			pin = int(command["pin"])
		else:
			U.logger.log(20, "setGPIO pid={}, pin not included,  bad command {}".format(myPID, command) )
			exit(1)



		delayStart = min(1000000, max(0,U.calcStartTime(command,"startAtDateTime")-time.time()))
		if delayStart > 0 and delayStart < 10000000: 
			if sleepForxSecs(delayStart):
				return 

		pulseUp = float(command.get("pulseUp",1))
		pulseDown = float(command.get("pulseDown",1))
		nPulses = float(command.get("nPulses",1))

		if "values" in command:
			values =  command.get("values",{})
			if values != {}:
				try:
					pulseUp = float(values.get("pulseUp",1))
					pulseDown = float(values.get("pulseDown",1))
					nPulses = int(values.get("nPulses",1))
					bits = min(100,int(values.get("bits",-1)))
					analogValue = min(100.,values.get("analogValue",-1))
					if bits == -1: bits = analogValue
					if bits == -1: bits = 0
				except Exception as e:
					U.logger.log(20," error reading command values:{}".format(values))
		
		

		#	 "values:{analogValue:"analogValue+",pulseUp:"+ pulseUp + ",pulseDown:" + pulseDown + ",nPulses:" + nPulses+"}


		inverseGPIO = False
		if "inverseGPIO" in command:
			inverseGPIO = command["inverseGPIO"]

		if "devId" in command:
			devId = str(command["devId"])
		else: devId = "0"

		U.logger.log(20, "{:.2f} bf  GPIO.setup, cmd:{}, pin:{}, useGPIO:{}, command:{} ".format(time.time(), cmd, pin,useGPIO,  command) )
		try:
			if inverseGPIO: 
				up   = 0
				down = 1
				on   = "low"
				off  = "high" 
				ON   = "off"
				OFF  = "on"
			else:
				up   = 1
				down = 0
				on   = "high"
				off  = "low" 
				ON   = "on"
				OFF  = "off"

			if cmd == "up":
				U.logger.log(myDebug, "{:.2f} setGPIO pin={}; set output to {}".format(time.time(), pin, on) )
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
					GPIO.output(pin, up)
				else:
					GPIOZERO = gpiozero.LED(pin)
					getattr(GPIOZERO, ON)()
					if sleepForxSecs(1000000000): 
						break
		

			elif cmd == "down":
				U.logger.log(myDebug, "{:.2f} setGPIO pin={}; set output to {}".format(time.time(), pin, off) )
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
					GPIO.output(pin, down)
				else:
					GPIOZERO = gpiozero.LED(pin)
					getattr(GPIOZERO, OFF)()
					if sleepForxSecs(1000000000): 
						break

			elif cmd in ["analogWrite","analogwrite"]:
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
					if useGPIO:
						GPIO.setup(pin, GPIO.OUT)
						p = GPIO.PWM(pin, PWM)	# 
						p.start(int(value))	 # start the PWM with  the proper duty cycle
						if sleepForxSecs(1000000000): break
					else:
						v = float(value) / 100.
						#U.logger.log(myDebug, "analogWrite action pin = {}  value:{}, v:{}".format(pin,  value, v) )
						GPIOZERO = gpiozero.PWMLED(pin, frequency=1000)
						GPIOZERO.value = v
						if sleepForxSecs(1000000000): 
							break

			elif cmd in ["pulseUp","pulseup"]: # ignoe inverse
				U.logger.log(myDebug, "pulseDown action pin = {} start, pulseDown:{}, inverseGPIO:{}, useGPIO:{}".format(pin,  pulseDown, inverseGPIO, useGPIO) )
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
					GPIO.output(pin, up)
				else:
					GPIOZERO = gpiozero.LED(pin)
					getattr(GPIOZERO, ON)()

				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})
				if sleepForxSecs(pulseUp): break
				if useGPIO:
					GPIO.output(pin, down)
				else:
					getattr(GPIOZERO, OFF)()
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})

			elif cmd in ["pulseDown","pulsedown"]: # ignoe inverse
				U.logger.log(myDebug, "pulseDown action pin = {} start, pulseDown:{}, inverseGPIO:{}".format(pin,  pulseDown, inverseGPIO) )
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
					GPIO.output(pin, down)
				else:
					GPIOZERO = gpiozero.LED(pin)
					getattr(GPIOZERO, OFF)()
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
				if sleepForxSecs(pulseDown): break
				U.logger.log(myDebug, "pulseDown action pin = {} back up".format(pin) )
				if useGPIO:
					GPIO.output(pin, up)
				else:
					getattr(GPIOZERO, ON)()
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})

			elif cmd in ["continuousUpDown","continuousupdown"]: # ignoe inverse
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
				else:
					GPIOZERO = gpiozero.LED(pin)
				#U.logger.log(myDebug, "continuousUpDown pin = {} start, pulseUp:{}, pulseDown:{}, nPulses:{}".format(pin,  pulseUp, pulseDown, nPulses) )
				for ii in range(nPulses):
					if useGPIO:
						GPIO.output(pin, up)
					else:
						GPIOZERO.on()
					if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})
					if sleepForxSecs(pulseUp): pass
					if useGPIO:
						GPIO.output(pin, down)
					else:
						GPIOZERO.off()
					if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
					if sleepForxSecs(pulseDown): break
				U.logger.log(myDebug, "continuousUpDown finished" )


		except Exception as e:
			U.logger.log(30,"", exc_info=True)

	U.logger.log(myDebug, "exit {}".format(command) )
	U.removeOutPutFromFutureCommands(pin, devType)
	if GPIOZERO != "": GPIOZERO.close()

	return 


### ----------------------------------------- ###
def sleepForxSecs(sleepTime):
	global threadsActive
	try:
		tDone 	= 0
		dt 		= 0.05
		try: threadName = threading.currentThread().getName()
		except: return True
		#U.logger.log(20, "threadName:{}, wait for {} secs".format(threadName, sleepTime))
		while True:
			tDone += dt
			if threadName not in threadsActive: return True
			if threadsActive[threadName]["state"] != "running": return True 
			time.sleep(dt)
			if sleepTime <= tDone: return False
		return False
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		U.logger.log(20, "threadsActive{}".format(threadsActive))
	return False

### ----------------------------------------- ###
def execCMDS(nextItem):
	global threadsActive
	global execcommands, PWM
	global py3Cmd, readOutput, readInput
	global usePython3


	try:	threadName = threading.current_thread()
	except:	threadName = threading.currentThread()
	#U.logger.log(G.debug*20, "{:.2f} into execCMDS, thread name:{}".format(time.time(), threadName))

	for ijji in range(1):

			#U.logger.log(20,"{:.2f} nextItem command: {}".format(time.time(), nextItem))


			delayStart = min(1000000, max(0,U.calcStartTime(nextItem,"startAtDateTime")-time.time()))


			# make lower case available
			for nI in copy.copy(nextItem):
				if nI != nI.lower(): 
					nextItem[nI.lower()] = nextItem[nI]

			try:
				if nextItem["command"] in mapCmds:
					nextItem["command"] = mapCmds[nextItem["command"]]
			except: pass

			cmd = nextItem["command"]

			if "restoreAfterBoot" in nextItem:
				restoreAfterBoot= nextItem["restoreAfterBoot"]
			else:
				restoreAfterBoot="0"


			if cmd == "general":
				if "cmdLine" in nextItem:
					subprocess.call(nextItem["cmdLine"] , shell=True)	 
					continue


			if cmd == "file":
				if "fileName" in nextItem and "fileContents" in nextItem:
					#print nextItem
					try:
						m = "w"
						if "fileMode" in nextItem and nextItem["fileMode"].lower() == "a": m = "a"
						fc = json.dumps(nextItem["fileContents"])
						U.logger.log(20,"write to nextItem {}  {}".format(nextItem["fileName"], fc ))
						f = open(nextItem["fileName"], m)
						f.write("{}".format(fc)) 
						f.close()
						if "touchFile" in nextItem and nextItem["touchFile"]:
							subprocess.call("echo	 {} > {}temp/touchFile".format(time.time(), G.homeDir) , shell=True)
						subprocess.call("sudo chown -R  pi  "+G.homeDir, shell=True)
					except Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if cmd == "getBeaconParameters":
				if delayStart > 0 and delayStart < 10000000: 
					U.logger.log(20,"{:.2f} delay start by: {}".format(time.time(), delayStart))
					if sleepForxSecs(delayStart):
						return 
				try:
						U.logger.log(20, "execcmd. getBeaconParameters, write: ={}".format(nextItem["device"]))
						f = open(G.homeDir+"temp/beaconloop.getBeaconParameters","w")
						f.write(nextItem["device"]) 
						f.close()
				except Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if cmd == "beepBeacon":
				if delayStart > 0 and delayStart < 10000000: 
					U.logger.log(20,"{:.2f} delay start by: {}".format(time.time(), delayStart))
					if sleepForxSecs(delayStart):
						return 
				try:
						U.logger.log(20, "execcmd. beep, write: ={}".format(str(nextItem["device"])[:20]))
						f = open(G.homeDir+"temp/beaconloop.beep","a")
						f.write(nextItem["device"]+"\n") 
						f.close()
				except Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if cmd == "updateTimeAndZone":
				try:
						U.logger.log(20, "execcmd. updateTimeAndZone, write: ={}".format(str(nextItem["device"])[:20]))
						f = open(G.homeDir+"temp/beaconloop.updateTimeAndZone","a")
						f.write(nextItem["device"]+"\n") 
						f.close()
				except Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue

			if	cmd == "BLEAnalysis":
					if "minRSSI" not in nextItem: minRSSI = "-61"
					else:					  minRSSI = nextItem["minRSSI"]
					subprocess.call("echo "+minRSSI+" > "+G.homeDir+"temp/beaconloop.BLEAnalysis", shell=True)
					continue

			if	cmd == "trackMac":
					if "mac" in nextItem: 
						subprocess.call("echo '"+nextItem["mac"]+"' > "+G.homeDir+"temp/beaconloop.trackmac", shell=True)
					else:
						U.logger.log(20, "trackMac, no mac number supplied")
					continue


			if "device" not in nextItem:
				U.logger.log(20," bad cmd no device given {}".format(nextItem))
				continue
				

			device = nextItem["device"]

			
			if device.lower() == "setsteppermotor":
				cmdOut = json.dumps(nextItem)
				if cmdOut != "":
					try:
						f=open(G.homeDir+"temp/setStepperMotor.inp","a")
						f.write(cmdOut+"\n")
						f.close()
					except Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue
			
			if device.lower()=="output-display":
				cmdOut = json.dumps(nextItem)
				if cmdOut != "":
					try:
						#print "execcmd", cmdOut
						if not U.pgmStillRunning("display.py"):
							subprocess.call("{} {}display.py &".format(py3Cmd, G.homeDir), shell=True)
						f = open(G.homeDir+"temp/display.inp","a")
						f.write(cmdOut+"\n")
						f.close()
						f = open(G.homeDir+"display.inp","w")
						f.write(cmdOut+"\n")
						f.close()
					except Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if device.lower().find("neopixel") > -1:### OUTPUT-neopixel
				cmdOut = json.dumps(nextItem)
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
							f = open(G.homeDir+"neopixel.inp","w")
							f.write(cmdOut+"\n")
							f.close()
					except Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if False and cmd not in allowedCommands:
				U.logger.log(20,"bad cmd (9) dev:{} not in allowed commands {} \n{}".format(device, cmd,  allowedCommands))
				continue


			if "values" in nextItem:
				values = nextItem["values"]
			else:
				values = { }

			startAtDateTime = "{}".format(time.time())
			if "startAtDateTime" in nextItem:
				startAtDateTime = nextItem["startAtDateTime"]

			if "inverseGPIO" in nextItem:
				inverseGPIO = nextItem["inverseGPIO"]
			else:
				inverseGPIO = False


			if "devId" in nextItem:
				devId = nextItem["devId"]
			else:
				devId = 0




			if	cmd == "newMessage":
						if nextItem["device"].find(",") > 1:
							list = nextItem["device"].split(",")
						elif nextItem["device"]== "all":
							list = G.programFiles + G.specialSensorList + G.specialOutputList + G.programFiles
						else:
							list = [nextItem["device"]]
						for pgm in list:
							subprocess.call("touch "+G.homeDir+"temp/"+pgm+".now", shell=True)
						continue


			if	cmd == "resetDevice":
						if nextItem["device"].find(",") > 1:
							list = nextItem["device"].split(",")
						elif nextItem["device"] == "all":
							list = G.programFiles + G.specialSensorList + G.specialOutputList + G.programFiles
						else:
							list = [nextItem["device"]]
						for pgm in list:
							subprocess.call("touch "+G.homeDir+"temp/"+pgm+".reset", shell=True)
						continue


			if	cmd == "restartDevice":
						if nextItem["device"].find(",") > 1:
							list = nextItem["device"].split(",")
						elif nextItem["device"] == "all":
							list = G.programFiles + G.specialSensorList + G.specialOutputList + G.programFiles
						else:
							list = [nextItem["device"]]
						for pgm in list:
							subprocess.call("touch "+G.homeDir+"temp/"+pgm+".restart", shell=True)
						continue


			if	cmd == "startCalibration":
						if nextItem["device"].find(",") > 1:
							list = nextItem["device"].split(",")
						elif nextItem["device"] == "all":
							list = G.specialSensorList
						else:
							list = [nextItem["device"]]
						for xxx in list:
							xxx = xxx.split(".")
							#U.logger.log(30,"xxx= {}".format(xxx))
							if len(xxx) > 0:
								fname  = '{}temp/{}.startCalibration'.format(G.homeDir, xxx[0])
								out = '{{"value":{}}}'.format(  xxx[1])
								U.logger.log(30," start calibration..  pgm:{}, data:{}".format(xxx[0], out))
								f = open(fname,"w")
								f.write(out)
								f.close()
							else:
								U.logger.log(30," start calibration ..  for pgm:{}".format(xxx[0]))
								subprocess.call("touch {}temp/{}.startCalibration".format( G.homeDir, xxx[0]), shell=True)
						continue




			if device == "setMCP4725":
						try:
							i2cAddress = U.getI2cAddress(nextItem, default =0)
							if cmd == "disable" :
								if sthreadName in execcommandsList:
									del execcommandsList[threadName]

							cmdJ= json.dumps({"cmd":cmd,"i2cAddress":i2cAddress,"startAtDateTime":startAtDateTime,"values":values, "devId":devId })
							U.logger.log(10,json.dumps(nextItem))
							cmdOut="/usr/bin/python "+G.homeDir+"setmcp4725.py '"+ cmdJ+"'  &"
							U.logger.log(10," cmd= %s"%cmdOut)
							subprocess.call(cmdOut, shell=True)
							if restoreAfterBoot == "1":
								execcommandsList[threadName] = nextItem
							else:
								try: del execcommandsList[threadName]
								except:pass

						except Exception as e:
							U.logger.log(30,"", exc_info=True)
						continue

			if device == "setPCF8591dac":
						try:
							i2cAddress = U.getI2cAddress(nextItem, default =0)
							if cmd == "disable":
								del execcommandsList[threadName]
								continue
							cmdJ= json.dumps({"cmd":cmd,"i2cAddress":i2cAddress,"startAtDateTime":startAtDateTime,"values":values, "devId":devId})
							U.logger.log(10,json.dumps(nextItem))
							cmdOut="/usr/bin/python "+G.homeDir+"setPCF8591dac.py '"+ cmdJ+"'  &"
							U.logger.log(10," cmd= %s"%cmdOut)
							subprocess.call(cmdOut, shell=True)
							if restoreAfterBoot == "1":
								execcommandsList[threadName] = nextItem
							else:
								try: del execcommandsList[threadName]
								except:pass

						except Exception as e:
							U.logger.log(30,"", exc_info=True)
						continue


			if device == "OUTgpio" or device.find("OUTPUTgpio")> -1:
						#U.logger.log(G.debug*20, "{:.2f} into if OUTgpio".format(time.time()))
						try:
							pinI = int(nextItem["pin"])
							pin = str(pinI)
						except Exception as e:
							U.logger.log(30,"", exc_info=True)
							U.logger.log(20,"bad pin {}".format(nextItem))
							continue

						if "aw" 				in nextItem: nextItem["analogwrite"] 		= nextItem["aw"]
						if "cup" 				in nextItem: nextItem["continuousupdown"] 	= nextItem["cup"]
						if "pu" 				in nextItem: nextItem["pulseup"] 			= nextItem["pu"]
						if "pd" 				in nextItem: nextItem["pulsedown"]			= nextItem["pd"]
						if "np" 				in nextItem: nextItem["npulses"] 			= nextItem["np"]
						if "analogwrite" 		in nextItem: values["analogwrite"] 			= float(nextItem.get("analogwrite",1))
						if "continuousupdown" 	in nextItem: values["continuousUpDown"] 	= float(nextItem.get("continuousupdown",1))
						if "pulseup" 			in nextItem: values["pulseUp"] 				= float(nextItem.get("pulseup",1))
						if "pulsedown" 			in nextItem: values["pulseDown"] 			= float(nextItem.get("pulsedown",1))
						if "npulses" 			in nextItem: values["nPulses"] 				= int(nextItem.get("npulses",0))

   
						if restoreAfterBoot == "1":
							execcommandsList[threadName] = nextItem
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
							pinI = int(nextItem["pin"])
							pin = str(pinI)
						except Exception as e:
							U.logger.log(30,"", exc_info=True)
							U.logger.log(20,"bad pin {}".format(nextItem))
							continue
						#print "pin ok"
						if "values" in nextItem: values= nextItem["values"]
						else:				 values={}
   
						if restoreAfterBoot == "1":
							execcommandsList[threadName] = nextItem

						else:
							try: del execcommandsList[threadName]
							except: pass

						if "aw" 				in nextItem: nextItem["analogwrite"] 		= nextItem["aw"]
						if "cup" 				in nextItem: nextItem["continuousupdown"] 	= nextItem["cup"]
						if "pu" 				in nextItem: nextItem["pulseup"] 			= nextItem["pu"]
						if "pd" 				in nextItem: nextItem["pulsedown"]			= nextItem["pd"]
						if "np" 				in nextItem: nextItem["npulses"] 			= nextItem["np"]
						if "analogwrite" 		in nextItem: values["analogwrite"] 			= float(nextItem.get("analogwrite",1))
						if "continuousupdown" 	in nextItem: values["continuousUpDown"] 	= float(nextItem.get("continuousupdown",1))
						if "pulseup" 			in nextItem: values["pulseUp"] 				= float(nextItem.get("pulseup",1))
						if "pulsedown" 			in nextItem: values["pulseDown"] 			= float(nextItem.get("pulsedown",1))
						if "npulses" 			in nextItem: values["nPulses"] 				= int(nextItem.get("npulses",0))

						if cmd =="disable":
							continue
						cmdJ= {"pin":pinI,"cmd":cmd,"startAtDateTime":startAtDateTime,"values":values, "inverseGPIO": inverseGPIO,"debug":G.debug,"i2cAddress":nextItem["i2cAddress"], "devId":devId}

						OUTPUTi2cRelay(cmdJ)
						continue

			if device == "myoutput":
						try:
							text   = nextItem["text"]
							cmdOut= "/usr/bin/python "+G.homeDir+"myoutput.py "+text+" &"
							U.logger.log(10,"cmd= %s"%cmdOut)
							subprocess.call(cmdOut, shell=True)
						except Exception as e:
							U.logger.log(30,"", exc_info=True)
						continue

			if device == "playSound":
						cmdOut = ""
						try:
							if	 cmd  == "omxplayer":
								cmdOut = json.dumps({"player":"omxplayer","file":G.homeDir+"soundfiles/"+nextItem["soundFile"]})
							elif cmd  == "aplay":
								cmdOut = json.dumps({"player":"aplay","file":G.homeDir+"soundfiles/"+nextItem["soundFile"]})
							else:
								U.logger.log(20, "bad command : player not right =" + cmd)
							if cmdOut != "":
								U.logger.log(10,"cmd= %s"%cmdOut)
								subprocess.call("/usr/bin/python playsound.py '"+cmdOut+"' &" , shell=True)
						except Exception as e:
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
	except Exception as e:
		U.logger.log(30,"", exc_info=True)

				 
### ----------------------------------------- ###
def execSimple(nextItem):
	global inp
	if "command" not in nextItem:		 return False
	if nextItem["command"] != "general": return False
	if "cmdLine" not in nextItem:		 return False
	
	try:
		# execute unix command
		if nextItem["cmdLine"].lower().find("sudo reboot" )> -1 or nextItem["cmdLine"].lower().find("sudo halt") > -1:
			stopThreadsIfEnded(all=True)
			subprocess.call(nextItem["cmdLine"] , shell=True)	 


			return True
			
		# execute set time command 
		if nextItem["cmdLine"].find("setTime")>-1:
			tt		   = time.time()
			items	   =  nextItem["cmdLine"].split("=")
			mactime	   = items[1]
			subprocess.call('date -s "'+mactime+'"', shell=True)
			mactt	   = U.getTimetimeFromDateString(mactime)
			deltaTime  = tt - mactt
			U.sendURL(data={"deltaTime":deltaTime},sendAlive="alive", wait=False)
			if "useRTC" in inp and inp["useRTC"] !="":
				subprocess.call("hwclock --systohc", shell=True) # set hw clock to system time stamp, only works if HW is enabled
			return True
		# execute set time command 
		if nextItem["cmdLine"].find("refreshNTP")>-1:
			U.startNTP()
			return True
		if nextItem["cmdLine"].find("stopNTP")>-1:
			U.stopNTP()
			return True

	except Exception as e:
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
		
		#U.logger.log(20, "===== ip:{}:  data:{}<\n\n".format(self.client_address[0], data))
		try:
			commands = json.loads(data.strip("\n"))
		except Exception as e:
				U.logger.log(30,"", exc_info=True)
				U.logger.log(20,"bad command: json failed {}".format(data))
				return

		#U.logger.log(20, "{:.2f} MyTCPHandler len:{}  data:{}".format(time.time(),len(data), data) )
			
		for nextItem in commands:
			if execSimple(nextItem): continue
			setupexecThreads(nextItem, "socket")
 
		readParams()
		stopThreadsIfEnded()
		return	 

### ----------------------------------------- ###
def setupexecThreads(nextItem, source):
	global inp
	global threadsActive
	global lastOut
	global counter
	try:
		if "command" not in nextItem: return False
		counter += 1
		
		threadName = ""
		if "pin" in nextItem and nextItem["pin"] != "": 					threadName += "pin-"+str(nextItem["pin"])
		elif "device" in nextItem and nextItem["device"] != "":				threadName = nextItem["device"]
		elif "i2cAddress" in nextItem and nextItem["i2cAddress"] != "": 	threadName += "-"+str(nextItem["i2cAddress"])
		if threadName =="":													threadName = nextItem["command"]

		if threadName in threadsActive:
			if threadsActive[threadName]["state"] != "stop":
				stopExecCmd(threadName)
			
		#U.logger.log(20, "starting thread={}".format(threadName))
		threadsActive[threadName] = {"state":"running", "thread": threading.Thread(name=threadName, target=execCMDS, args=(nextItem,))}	
		threadsActive[threadName]["thread"].daemon = True
		threadsActive[threadName]["thread"].start()
		threadsActive[threadName]["comment"] = nextItem
		out = "{}".format(nextItem)
		ll = min(len(out),50)
		changed = ""
		if len(lastOut) > 10:
			for ii in range(len(out)):
				if ii+1 > len(lastOut):
					changed = out[ii:ii+10] 
					break
				if lastOut[ii] != out[ii]:
					changed = ">>"+ out[ii:ii+10] + "<< != >>" + lastOut[ii:ii+10] + "<<"
					break
				
		#U.logger.log(20,"thread started: {}, command:{} ".format(threadName, out))
		if changed != "":
			U.logger.log(20,"thread from:{:}, #:{:3d} started: {:}, command:{:} ... {:} changed:{:}".format(source, counter, threadName, out[:ll], out[-ll:],  changed))
		else:
			U.logger.log(20,"thread from:{:}, #:{:3d} started: {:}, command:{:} ... {:}".format(source,counter, threadName, out[:ll], out[-ll:]))
		
		lastOut = out

		return True

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return False



		

### ----------------------------------------- ###
def stopExecCmd(threadName):
	global inp
	global threadsActive
	try:
		if threadName in threadsActive:
			#U.logger.log(20, "stop issuing thread={}, comment: {}".format(threadName, str(threadsActive[threadName]["comment"])[0:10]))
			if threadsActive[threadName]["state"] == "stop": return 
			threadsActive[threadName]["state"] = "stop"
			time.sleep(0.07)
			#U.logger.log(20, "stop finished after wait thread={}".format(threadName))
	except Exception as e:
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

		readCmds = U.doReadSimpleFile(G.homeDir+"execcommandsList.current")
		if readCmds != "":
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
					nextItem = execcommandsList[threadName]
				except Exception as e:
					U.logger.log(30,"", exc_info=True)
					continue
				setupexecThreads(nextItem, "current")

			f = open(G.homeDir+"execcommandsList.current","w")
			f.write(json.dumps(keep))
			f.close()

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return 



### ----------------------------------------- ###
### -- read from file in temp dir and then execute command--- ###
### ----------------------------------------- ###
def setupReadTempDirThread():
	global threadsActive
	threadName = "readTempDir"
	try:
		threadsActive[threadName] = {"state":"running", "thread": threading.Thread(name=threadName, target=readTempDirThread, args=())}	
		threadsActive[threadName]["thread"].daemon = True
		threadsActive[threadName]["thread"].start()
		return True

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return False

### ----------------------------------------- ###
def readTempDirThread():
	global threadsActive
	threadName = "readTempDir"
	fName = G.homeDir+"temp/file.cmd"	

	U.logger.log(20, "readTempDirThread started:")
	while  threadsActive[threadName]["state"] == "running":
		#U.logger.log(20, "readTempDirThread looping trough:{}".format(G.homeDir+"temp/fileCommand.inp"))
		time.sleep(1.5)
		commands = {}
		rawRead = U.doReadSimpleFile(fName)
		if rawRead != "":
			try:
				# should be something like this:  '[{"device": "OUTPUTgpio-1", "command": "up", "pin": "19"}]'
				# should be something like this:  '[{"device": "OUTPUTgpio-1", "command": "continuousUpDown", "values":{"nPulses":4, "pulseUp":2, "pulseDown":2},  "pin": "19"}]'
				# should be something like this:  '[{"device": "OUTPUTgpio-1", "command": "pulseUp", "values":{"pulseUp":2},  "pin": "19"}]'
				commands = json.loads(rawRead.strip("\n"))
			except:
				U.logger.log(20, "readTempDirThread bad read:{}".format(rawRead))
			U.logger.log(20, "readTempDirThread commands:{}".format(commands))

			os.remove(fName)
			if commands != {}:
				for nextItem in commands:
					#U.logger.log(20, "readTempDirThread nextItem:{}".format(nextItem))
					if execSimple(nextItem): continue
					setupexecThreads(nextItem, "tempdir")


			#'[{"device": "OUTPUTgpio-1", "command": "up", "pin": "19"}]'

### ----------------------------------------- ###
### -- END read from file in temp dir and then execute command--- ###
### ----------------------------------------- ###
### ----------------------------------------- ###
	
				 
### ----------------------------------------- ###
def readParams():
	global	output, useLocalTime, myPiNumber, inp, readOutput, readInput, execcommandsListAction, PWM, typeForPWM
	global usePython3
	inp, inpRaw, x = U.doRead()
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

	except Exception as e:
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
	global lastOut, counter
	counter				= 0
	lastOut				= ""
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
		U.logger.log(20, "network not active, sleeping ")
		time.sleep(500)# == 500 secs
		exit(0)
	# if not connected to network pass
		
		
	if G.wifiType != "normal": 
		U.logger.log(20, "no need to receiving commands in adhoc mode pausing receive GPIO commands")
		time.sleep(500)
		exit(0)
	U.logger.log(20, "proceding with normal on no ad-hoc network")

	U.getIPNumber()
	
	getcurentCMDS()
	py3Cmd = "/usr/bin/python"
	if sys.version[0] == "3" or usePython3:
		py3Cmd = "/usr/bin/python3"

	setupReadTempDirThread()

	U.logger.log(20,"started, listening to port: "+ str(PORT))
	restartMaster = False
	try:	
		# Create the server, binding on port 9999
		server = socketserver.TCPServer((G.ipAddress, PORT), MyTCPHandler)

	except Exception as e:
		####  trying to kill the process thats blocking the port# 
		U.logger.log(30,"", exc_info=True)
		U.logger.log(30, "getting  socket does not work, trying to reset {}".format(PORT) )
		ret = readPopen("sudo ss -apn | grep :{}".format(PORT))[0]
		lines = ret.split("\n")
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
		except Exception as e:
			U.logger.log(20, "getting  socket does not work, try restarting master  "+ str(PORT) )
			subprocess.Popen("/usr/bin/python "+G.homeDir+"master.py  &",shell=True)
			exit()

	# Activate the server; this will keep running until you interrupt the program with Ctrl-C
	server.serve_forever()
