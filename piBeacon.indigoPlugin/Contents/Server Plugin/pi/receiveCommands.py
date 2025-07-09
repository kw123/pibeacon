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
		time.sleep(2)
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

allowedCommands = ["up","down","pulseUp","pulseDown","continuousUpDown","analogWrite","disable","myoutput","omxplayer","display","newMessage","resetDevice","restartDevice",
				"startCalibration","getBeaconParameters","beepBeacon","updateTimeAndZone","file","BLEreport","BLEAnalysis","trackMac"]

externalGPIO = False

mapCmds	= {"pu":"pulseUp","pd":"pulseDown","cup":"continuousUpDown","aw":"analogWrite"}
####-------------------------------------------------------------------------####
def readPopen(cmd):
	global DEBUG
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
	global DEBUG
	try:
		devType = "OUTPUTi2cRelay"

		for iii in range(1):
			U.logger.log(DEBUG, "OUTPUTi2cRelay command:{}".format(command) )
			if "cmd" in command:
				cmd = command["cmd"]
				if False and cmd not in allowedCommands:
					U.logger.log(DEBUG, "OUTPUTi2cRelay pid={}d, bad command {}  allowed only: {}".format(myPID, command , allowedCommands )  )
					exit(1)

			if "pin" in command:
				pin= int(command["pin"])
			else:
				U.logger.log(DEBUG, "setGPIO pid={}, pin not included,  bad command {}".format(myPID,command) )
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
						U.logger.log(30," error reading command values:{}".format(values))
		

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
				U.logger.log(DEBUG, "relay {} {} {} ".format(i2cAddress, pin, up))
				if devId != "0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})

			elif cmd == "down":
				U.logger.log(DEBUG, "relay {} {} {} ".format(i2cAddress, pin, down))
				bus.write_byte_data(i2cAddress, pin,down)
				if devId != "0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})

			elif cmd in ["pulseUp","pulseup"]:
				bus.write_byte_data(i2cAddress, pin, up)
				if devId != "0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})
				if sleepForxSecs(pulseUp): break
				bus.write_byte_data(i2cAddress, pin, down)
				if devId != "0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})

			elif cmd in ["pulseDown","pulsedown"]:
				bus.write_byte_data(i2cAddress, pin, down)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})
				if sleepForxSecs(pulseDown): break
				bus.write_byte_data(i2cAddress, pin, up)
				if devId != "0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})

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
	global DEBUG
	global GPIOZERO
	devType = "OUTPUTgpio"


	#U.logger.log(DEBUG, "{:.2f} into setGPIO command:{}".format(time.time() , command))

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
				U.logger.log(DEBUG, "setGPIO pid={}, bad command{}  allowed only: {}".format(myPID, command, allowedCommands)  )
				exit(1)

		if "pin" in command:
			pin = int(command["pin"])
		else:
			U.logger.log(DEBUG, "setGPIO pid={}, pin not included,  bad command {}".format(myPID, command) )
			exit(1)



		delayStart = min(1000000, max(0,U.calcStartTime(command,"startAtDateTime")-time.time()))
		if delayStart > 0 and delayStart < 10000000: 
			if sleepForxSecs(delayStart):
				return 

		pulseUp = float(command.get("pulseUp",1))
		pulseDown = float(command.get("pulseDown",1))
		nPulses = float(command.get("nPulses",1))
		disableGPIOafterPulse = command.get("disableGPIOafterPulse",True)
		
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
					U.logger.log(30," error reading command values:{}".format(values))
		
		

		#	 "values:{analogValue:"analogValue+",pulseUp:"+ pulseUp + ",pulseDown:" + pulseDown + ",nPulses:" + nPulses+"}


		inverseGPIO = False
		if "inverseGPIO" in command:
			inverseGPIO = command["inverseGPIO"]

		if "devId" in command:
			devId = str(command["devId"])
		else: devId = "0"

		U.logger.log(DEBUG, "{:.2f} bf  GPIO.setup, cmd:{}, pin:{}, useGPIO:{}, command:{} ".format(time.time(), cmd, pin, useGPIO,  command) )
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
				U.logger.log(DEBUG, "{:.2f} setGPIO pin={}; set output to {}".format(time.time(), pin, on) )
				if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
					GPIO.output(pin, up)
				else:
					if pin not in GPIOZERO:
						GPIOZERO[pin] = gpiozero.LED(pin)
					getattr(GPIOZERO[pin], ON)()
					if sleepForxSecs(1000000000): 
						break
		

			elif cmd == "down":
				U.logger.log(DEBUG, "{:.2f} setGPIO pin={}; set output to {}".format(time.time(), pin, off) )
				if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
					GPIO.output(pin, down)
				else:
					if pin not in GPIOZERO:
						GPIOZERO[pin] = gpiozero.LED(pin)
					getattr(GPIOZERO[pin], OFF)()
					if sleepForxSecs(1000000000): 
						break

			elif cmd in ["analogWrite","analogwrite"]:
				if inverseGPIO:
					value = (100-bits)	# duty cycle on xx hz
				else:
					value =   bits	 # duty cycle on xxx hz 
				value = int(value)
				U.logger.log(DEBUG, "analogwrite pin = {};    duty cyle: {};  PWM={}; using {}".format(pin, value, PWM, typeForPWM) )
				if value > 0:
					U.sendURL({"outputs":{"OUTPUTgpio-1":{devId:{"actualGpioValue":"high"}}}})
				else:
					U.sendURL({"outputs":{"OUTPUTgpio-1":{devId:{"actualGpioValue":"low"}}}})

				if typeForPWM == "PIGPIO": 	
					#U.logger.log(DEBUG, "..  setting PIGPIO {}  {}  {}".format(pwmFreq, pwmRange,  value) )
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
						#U.logger.log(DEBUG, "analogWrite action pin = {}  value:{}, v:{}".format(pin,  value, v) )
						if pin not in GPIOZERO:
							GPIOZERO[pin] = gpiozero.PWMLED(pin, frequency=1000)
						GPIOZERO[pin].value = v
						if sleepForxSecs(1000000000): 
							break

			elif cmd in ["pulseUp","pulseup"]:
				U.logger.log(DEBUG, "pulseUp action pin = {} start, pulseLen:{} inverseGPIO:{}, useGPIO:{}".format(pin,  pulseUp, inverseGPIO, useGPIO) )
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
					GPIO.output(pin, up)
				else:
					GPIOZERO[pin] = gpiozero.LED(pin)
					getattr(GPIOZERO[pin], ON)()

				if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})
				if sleepForxSecs(pulseUp): break
				if useGPIO:
					GPIO.output(pin, down)
				else:
					getattr(GPIOZERO[pin], OFF)()
					if disableGPIOafterPulse: GPIOZERO[pin].close()
					
				if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})

			elif cmd in ["pulseDown","pulsedown"]: 
				U.logger.log(DEBUG-10, "pulseDown action pin = {} start, pulseDown:{}, inverseGPIO:{}".format(pin,  pulseDown, inverseGPIO) )
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
					GPIO.output(pin, down)
				else:
					if pin not in GPIOZERO:
						GPIOZERO[pin] = gpiozero.LED(pin)
					getattr(GPIOZERO[pin], OFF)()
				if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
				if sleepForxSecs(pulseDown): break
				U.logger.log(DEBUG-10, "pulseDown action pin = {} back up".format(pin) )
				if useGPIO:
					GPIO.output(pin, up)
				else:
					getattr(GPIOZERO[pin], ON)()
				if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})

			elif cmd in ["continuousUpDown","continuousupdown"]:
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
				else:
					if pin not in GPIOZERO:
						GPIOZERO[pin] = gpiozero.LED(pin)
				#U.logger.log(DEBUG, "continuousUpDown pin = {} start, pulseUp:{}, pulseDown:{}, nPulses:{}".format(pin,  pulseUp, pulseDown, nPulses) )
				for ii in range(nPulses):
					if useGPIO:
						GPIO.output(pin, up)
					else:
						GPIOZERO[pin].on()
					if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})
					if sleepForxSecs(pulseUp): pass
					if useGPIO:
						GPIO.output(pin, down)
					else:
						GPIOZERO[pin].off()
					if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
					if sleepForxSecs(pulseDown): break
				U.logger.log(DEBUG, "continuousUpDown finished" )


		except Exception as e:
			U.logger.log(30,"", exc_info=True)

	U.logger.log(DEBUG, "exit {}".format(command) )
	U.removeOutPutFromFutureCommands(pin, devType)
	if pin in GPIOZERO:
		GPIOZERO[pin].close()
		del GPIOZERO[pin]

	return 


### ----------------------------------------- ###
def sleepForxSecs(sleepTime):
	global DEBUG
	global threadsActive
	try:
		tDone 	= 0
		dt 		= 0.05
		try: threadName = threading.current_thread().name
		except: return True
		#U.logger.log(DEBUG, "threadName:{}, wait for {} secs".format(threadName, sleepTime))
		while True:
			tDone += dt
			if threadName not in threadsActive: return True
			if threadsActive[threadName]["state"] != "running": return True 
			time.sleep(dt)
			if sleepTime <= tDone: return False
		return False
	except Exception as e:
		U.logger.log(20,"", exc_info=True)
		U.logger.log(DEBUG, "threadsActive{}".format(threadsActive))
	return False

### ----------------------------------------- ###
def execCMDS(nextItem):
	global threadsActive
	global execcommands, PWM
	global py3Cmd, readOutput, readInput
	global usePython3
	global DEBUG


	try:	threadName = threading.current_thread()
	except:	threadName = threading.currentThread()
	#U.logger.log(DEBUG, "{:.2f} into execCMDS, thread name:{}".format(time.time(), threadName))
	DEBUG = 20
	
	for ijji in range(1):



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


			if "debug" in nextItem:
				try: 	DEBUG = int(nextItem.get("debug",20))
				except:	DEBUG = 20

			#U.logger.log(20,"debug:{} cmd: {}".format(DEBUG, cmd))
			
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
						U.logger.log(DEBUG,"write to nextItem {}  {}".format(nextItem["fileName"], fc ))
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
					U.logger.log(DEBUG,"{:.2f} delay start by: {}".format(time.time(), delayStart))
					if sleepForxSecs(delayStart):
						return 
				try:
						U.logger.log(DEBUG, "execcmd. getBeaconParameters, write: ={}".format(nextItem["device"]))
						f = open(G.homeDir+"temp/beaconloop.getBeaconParameters","w")
						f.write(nextItem["device"]) 
						f.close()
				except Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if cmd == "beepBeacon":
				if delayStart > 0 and delayStart < 10000000: 
					U.logger.log(DEBUG,"{:.2f} delay start by: {}".format(time.time(), delayStart))
					if sleepForxSecs(delayStart):
						return 
				try:
						U.logger.log(DEBUG, "execcmd. beep, write: ={}".format(str(nextItem["device"])[:20]))
						f = open(G.homeDir+"temp/beaconloop.beep","a")
						f.write(nextItem["device"]+"\n") 
						f.close()
				except Exception as e:
						U.logger.log(30,"", exc_info=True)
				continue


			if cmd == "updateTimeAndZone":
				try:
						U.logger.log(DEBUG, "execcmd. updateTimeAndZone, write: ={}".format(str(nextItem["device"])[:20]))
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
						U.logger.log(DEBUG, "trackMac, no mac number supplied")
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
							U.logger.log(DEBUG,">>>>>> starting pgm: {}{}{} &".format(py, G.homeDir, pgm))
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
				U.logger.log(DEBUG,"bad cmd (9) dev:{} not in allowed commands {} \n{}".format(device, cmd,  allowedCommands))
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
							U.logger.log(DEBUG,"bad pin {}".format(nextItem))
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
						cmdJ= {"pin":pin,"cmd":cmd,"startAtDateTime":startAtDateTime,"values":values, "inverseGPIO": inverseGPIO,"debug":DEBUG,"PWM":PWM, "devId":devId}
						setGPIO(cmdJ)
						continue


			if  device.find("OUTPUTi2cRelay")> -1:
						try:
							pinI = int(nextItem["pin"])
							pin = str(pinI)
						except Exception as e:
							U.logger.log(30,"", exc_info=True)
							U.logger.log(DEBUG,"bad pin {}".format(nextItem))
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
						cmdJ= {"pin":pinI,"cmd":cmd,"startAtDateTime":startAtDateTime,"values":values, "inverseGPIO": inverseGPIO,"debug":DEBUG,"i2cAddress":nextItem["i2cAddress"], "devId":devId}

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
								U.logger.log(DEBUG, "bad command : player not right =" + cmd)
							if cmdOut != "":
								U.logger.log(10,"cmd= %s"%cmdOut)
								subprocess.call("/usr/bin/python playsound.py '"+cmdOut+"' &" , shell=True)
						except Exception as e:
							U.logger.log(30,"", exc_info=True)
						continue

			U.logger.log(20,"bad device :{}-".format(device))
	if len(execcommandsList) >0:
		f = open(G.homeDir+"execcommandsList.current","w")
		f.write(json.dumps(execcommandsList))
		f.close()
	stopExecCmd(threadName)

	return

				 
### ----------------------------------------- ###
def stopThreadsIfEnded(all=False):
	global threadsActive
	global DEBUG
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
	global DEBUG
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
		global DEBUG
		global threadsActive
		# self.request is the TCP socket connected to the client
		data = ""
		while True:
			buffer = self.request.recv(2048).decode('utf_8')
			#U.logger.log(10, "len of buffer:"+str(len(buffer)))
			if not buffer:
				break
			data += buffer.strip()
		
		#U.logger.log(DEBUG, "===== ip:{}:  data:{}<\n\n".format(self.client_address[0], data))
		try:
			commands = json.loads(data.strip("\n"))
		except Exception as e:
				U.logger.log(30,"", exc_info=True)
				U.logger.log(20,"bad command: json failed {}".format(data))
				return

		#U.logger.log(DEBUG, "{:.2f} MyTCPHandler len:{}  data:{}".format(time.time(),len(data), data) )
			
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
	global DEBUG
	try:
		if "command" not in nextItem: return False
		counter += 1
		
		threadName = ""
		if "pin" in nextItem and nextItem["pin"] != "": 					threadName += "pin-"+str(nextItem["pin"])
		elif "device" in nextItem and nextItem["device"] != "":				threadName = nextItem["device"]
		elif "i2cAddress" in nextItem and nextItem["i2cAddress"] != "": 	threadName += "-"+str(nextItem["i2cAddress"])
		if threadName == "":												threadName = nextItem["command"]

		if threadName in threadsActive:
			if threadsActive[threadName]["state"] != "stop":
				stopExecCmd(threadName)
			
		#U.logger.log(DEBUG, "starting thread={}".format(threadName))
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
			U.logger.log(DEBUG,"thread from:{:}, #:{:3d} started, name={:}, command:{:} ... {:} changed:{:}".format(source, counter, threadName, out[:ll], out[-ll:],  changed))
		else:
			U.logger.log(DEBUG,"thread from:{:}, #:{:3d} started, name={:}, command:{:} ... {:}".format(source,counter, threadName, out[:ll], out[-ll:]))
		
		lastOut = out

		return True

	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	return False



		

### ----------------------------------------- ###
def stopExecCmd(threadName):
	global inp
	global threadsActive
	global DEBUG
	try:
		if threadName in threadsActive:
			#U.logger.log(DEBUG, "stop issuing thread={}, comment: {}".format(threadName, str(threadsActive[threadName]["comment"])[0:10]))
			if threadsActive[threadName]["state"] == "stop": return 
			threadsActive[threadName]["state"] = "stop"
			time.sleep(0.07)
			#U.logger.log(DEBUG, "stop finished after wait thread={}".format(threadName))
	except Exception as e:
		U.logger.log(30,"", exc_info=True)
	try: 	del threadsActive[threadName]
	except: pass
	return 


### ----------------------------------------- ###
def getcurentCMDS():
	global	execcommandsList, output, execcommandsListAction
	global DEBUG
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
	global DEBUG
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
	global DEBUG
	global threadsActive
	threadName = "readTempDir"
	fName = G.homeDir+"temp/receiveCommands.input"	
	tempcmdCount = 0
	U.logger.log(DEBUG, "readTempDirThread started: state:{}".format( threadsActive[threadName]["state"]))
	lastlog = time.time()
	try:
		while  threadsActive[threadName]["state"] == "running":
	
			time.sleep(0.05)
			commandList = []
			rawRead = U.doReadSimpleFile(fName)
				
			if rawRead != "":
				try:
					# should be something like this:  '[{"device": "OUTPUTgpio-1", "devId:"1234", "command": "up", "pin": "19"}]'
					# should be something like this:  '[{"device": "OUTPUTgpio-1", "command": "continuousUpDown", "values":{"nPulses":4, "pulseUp":2, "pulseDown":2},  "pin": "19"}]'
					# should be something like this:  '[{"device": "OUTPUTgpio-1", "command": "pulseUp", "values":{"pulseUp":2},  "pin": "19"}]'
					for line in rawRead.split("\n"):
						if len(line) > 2:
							commandList.append(json.loads(line))
				except:
					U.logger.log(DEBUG, "readTempDirThread bad read:{}".format(rawRead))
				U.logger.log(20, "from file:{}".format(commandList))
	
				subprocess.call("sudo rm  "+fName+" > /dev/null 2>&1 ", shell=True)

				if commandList != []:
					for commands in commandList:
						for nextItem in commands:
							U.logger.log(DEBUG, "readTempDirThread nextItem:{}".format(nextItem))
							if execSimple(nextItem): continue
							tag = str(time.time())
							tempcmdCount += 1
							setupexecThreads(nextItem, "tempdir"+str(tempcmdCount))
	
	
			#'[{"device": "OUTPUTgpio-1", "command": "up", "pin": "19"}]'
	except Exception as e:
		U.logger.log(30,"", exc_info=True)

	U.logger.log(DEBUG, "readTempDirThread exit")

### ----------------------------------------- ###
### -- END read from file in temp dir and then execute command--- ###
### ----------------------------------------- ###
### ----------------------------------------- ###
	
				 
### ----------------------------------------- ###
def readParams():
	global	output, useLocalTime, myPiNumber, inp, readOutput, readInput, execcommandsListAction, PWM, typeForPWM
	global usePython3, tempcmdCount
	global DEBUG

	inp, inpRaw, x = U.doRead()
	if inp == "": return
	tempcmdCount = 0

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
	global DEBUG
	global GPIOZERO
	
	GPIOZERO			= {}
	DEBUG				= 10
	counter				= 0
	lastOut				= ""
	PWM 				= 100
	typeForPWM			= "GPIO"
	myPID				= str(os.getpid())
	threadsActive		= {}
	execcommandsList	= {}
	output				= {}


	py3Cmd = "/usr/bin/python "
	if sys.version[0] == "3" or usePython3:
		py3Cmd = "/usr/bin/python3 "

	PORT = int(sys.argv[1])

	U.setLogging()

	U.killOldPgm(myPID,G.program+".py")# del old instances of myself if they are still running

	time.sleep(0.5)
	
	readParams()

	if U.getNetwork() == "off":
		U.logger.log(DEBUG, "network not active, sleeping ")
		time.sleep(500)# == 500 secs
		exit(0)
	# if not connected to network pass
		
		
	if G.wifiType != "normal": 
		U.logger.log(DEBUG, "no need to receiving commands in adhoc mode pausing receive GPIO commands")
		time.sleep(500)
		exit(0)
	U.logger.log(DEBUG, "proceding with normal on no ad-hoc network")

	U.getIPNumber()
	
	getcurentCMDS()

	setupReadTempDirThread()

	U.logger.log(20,"starting, listening to port: "+ str(PORT))
	restartMaster = False
	try:	
		# Create the server, binding on port 9999
		server = socketserver.TCPServer((G.ipAddress, PORT), MyTCPHandler)

	except Exception as e:
		####  trying to kill the process thats blocking the port# 
		#U.logger.log(30,"", exc_info=True)
		U.logger.log(30, "getting  socket does not work, trying to reset port {}".format(PORT) )
		ret = readPopen("sudo ss -apn | grep :{}".format(PORT))[0]
		lines = ret.split("\n")
		for line in lines:
			U.logger.log(DEBUG, line) 
			pidString = line.split(",pid=")
			for ppp in pidString:
				pid = ppp.split(",")[0]
				if pid == myPID: continue
				try:
					pid = int(pid)
					if pid < 99: continue
				except: continue

				if len (subprocess.Popen("ps -ef | grep "+str(pid)+"| grep -v grep | grep master.py",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]) >5:
					restartMaster = True
					# will need to restart the whole things
				U.logger.log(DEBUG, "killing task with : pid= %d"% pid )
				ret = subprocess.Popen("sudo kill -9 "+str(pid),shell=True)
				time.sleep(0.2)


		cmd = py3Cmd + G.homeDir+"master.py  &"
		if restartMaster:
			U.logger.log(20, "getting  socket port ={} does not work, try restarting master {} ".format(PORT, cmd) )
			subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			exit()
			
		try:	
			# Create the server, binding on port eg 9999
			U.logger.log(20, "starting  socketserver")
			server = socketserver.TCPServer((G.ipAddress, PORT), MyTCPHandler)

		except Exception as e:
			U.logger.log(20, "getting  socket port ={} does not work, try restarting master {} ".format(PORT, cmd) )
			subprocess.Popen(cmd, shell=True)
			exit()

	# Activate the server; this will keep running until you interrupt the program with Ctrl-C
	server.serve_forever()
