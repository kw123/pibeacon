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
import base64

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


def gattviaBLEconnect():
	"""Returns True if BLEconnect.py is alive on this rpi (alive file younger than 90 secs) -
	then gatt jobs for beacon tags (beep / battery read) are routed to BLEconnect (usually on
	the second BLE adapter -> no interruption of beaconloop scanning); otherwise beaconloop
	handles them itself as before."""
	try:
		fn = G.homeDir+"temp/alive.BLEconnect"
		if os.path.isfile(fn) and time.time() - os.path.getmtime(fn) < 90.: return True
	except Exception:
		pass
	return False

G.program = "receiveCommands"

allowedCommands = ["up","down","pulseUp","pulseDown","continuousUpDown","analogWrite","disable","myoutput","omxplayer","display","newMessage","resetDevice","restartDevice",
				"startCalibration","getBeaconParameters","beepBeacon","updateTimeAndZone","file","BLEreport","BLEAnalysis","trackMac"]

externalGPIO = False
getBeaconParametersLock = threading.Lock()	# command threads must not race on the getBeaconParameters merge-write

# WHO OWNS A GPIO PIN RIGHT NOW. threadsActive is keyed by pin name, and stopExecCmd waits only
# 0.07 s before deleting the entry while setupexecThreads immediately re-registers the SAME name
# with state "running" - so an old thread sleeping in sleepForxSecs (0.05 s poll) can miss the stop
# window, see its name "running" again and sleep on. When it finally woke it closed GPIOZERO[pin],
# which by then belonged to the NEWER command: the output dropped with nothing in the log to
# explain it. Every setGPIO call takes the next generation for its pin and only touches the
# hardware object at the end if it still holds it.
gpioGeneration	= 0
gpioOwner		= {}	# pin -> generation of the call that currently drives it
gpioOwnerLock	= threading.Lock()

PIGPIOhandle	= None	# ONE shared pigpio client for the whole process, see getPigpio()

mapCmds	= {"pu":"pulseUp","pd":"pulseDown","cup":"continuousUpDown","aw":"analogWrite"}
####-------------------------------------------------------------------------####
def claimGPIOpin(pin):
	"""Takes ownership of a pin and returns the generation number that proves it.

	Inputs:
	    pin (int): the GPIO pin this call is about to drive
	Outputs:
	    int: the generation of THIS call - pass it to releaseGPIOpin()
	"""
	global gpioGeneration
	with gpioOwnerLock:
		gpioGeneration += 1
		gpioOwner[pin] = gpioGeneration
		return gpioGeneration


def ownsGPIOpin(pin, myGen):
	"""True while `myGen` is still the current owner of `pin`, and drops the claim when it is.

	A missing entry counts as ours: nothing else has claimed the pin, so the cleanup is safe.

	Inputs:
	    pin (int): the GPIO pin
	    myGen (int): what claimGPIOpin() returned
	Outputs:
	    bool: True when this call may close/reset the pin
	"""
	with gpioOwnerLock:
		if gpioOwner.get(pin, myGen) != myGen:	return False
		try:	del gpioOwner[pin]
		except Exception:	pass
		return True


def gpioPinTakenOver(pin, myGen):
	"""True as soon as a NEWER setGPIO call has claimed this pin.

	This, not threadsActive, is the reliable "you are done" signal. stopExecCmd holds the stop flag
	for only 0.07 s and then re-registers the SAME thread name as "running", while sleepForxSecs
	looks every 0.05 s - a busy rpi can make a thread miss that 20 ms margin, and it then carries on
	driving a pin somebody else owns: a 5 s pulseUp that was overridden by an "up" after 1 s would
	still switch the pin OFF at second 5, leaving the newer command sitting in its hold loop
	believing the output is on. A claim cannot be missed - it stays until the owner clears it.

	Inputs:
	    pin (int): the GPIO pin
	    myGen (int): what claimGPIOpin() returned
	Outputs:
	    bool: True when this call must stop touching the pin
	"""
	with gpioOwnerLock:
		return gpioOwner.get(pin, myGen) != myGen


def sleepOwningPin(sleepTime, pin, myGen):
	"""sleepForxSecs(), but it also gives up as soon as another command takes the pin over.

	Every wait inside setGPIO that has hardware writes after it goes through here, so a command
	that lost its pin stops at the next 0.05 s tick instead of finishing its sequence on top of
	the new one.

	Inputs:
	    sleepTime (float): seconds to wait
	    pin (int): the GPIO pin
	    myGen (int): the generation that owns it
	Outputs:
	    bool: True when the wait was cut short - thread stopped, or pin taken over
	"""
	tDone = 0.
	while tDone < sleepTime:
		step = min(0.05, sleepTime - tDone)
		if sleepForxSecs(step):				return True
		tDone += step
		if gpioPinTakenOver(pin, myGen):	return True
	return False


def getPigpio():
	"""The process-wide pigpio client, created on demand and reused.

	pigpio.pi() opens a socket to pigpiod AND starts a notification thread. It used to be called at
	the TOP of setGPIO - so for up/down/pulse too, not only for analogWrite - and was never
	stopped, so every gpio command leaked one socket and one thread until the rpi ran out of file
	descriptors. One client is enough: pigpiod holds the pin and PWM state itself, the client only
	sends commands, and the state survives the client going away. Recreated when the daemon was
	restarted underneath us.

	Inputs:
	    None
	Outputs:
	    pigpio.pi instance, or None when pigpiod cannot be reached
	"""
	global PIGPIOhandle
	try:
		import pigpio
		if PIGPIOhandle is not None:
			try:
				if PIGPIOhandle.connected:	return PIGPIOhandle
			except Exception:	pass
			try:	PIGPIOhandle.stop()			# dead handle: give its socket and thread back
			except Exception:	pass
			PIGPIOhandle = None
		PIGPIOhandle = pigpio.pi()
		if not PIGPIOhandle.connected:
			try:	PIGPIOhandle.stop()
			except Exception:	pass
			PIGPIOhandle = None
	except Exception:
		U.logger.log(20,"", exc_info=True)
		PIGPIOhandle = None
	return PIGPIOhandle
####-------------------------------------------------------------------------####
def readPopen(cmd):
	"""Runs a shell command via subprocess.Popen, captures stdout and stderr, and returns them as decoded UTF-8 strings.

	Inputs:
	    cmd (str): Shell command line to execute
	Outputs:
	    tuple: (stdout, stderr) decoded UTF-8 strings, or None on exception
	"""
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
	"""Drives an I2C relay board over the SMBus, interpreting a command dict to set a relay pin up/down or pulse it (with optional inversion, delayed start, and repeated pulses), and reports the resulting state back via sendURL.

	Inputs:
	    command (dict): Relay command with cmd, pin, i2cAddress, pulse/timing and devId fields
	Outputs:
	    None: Writes relay bytes to the I2C bus, sends state updates via URL, and logs
	"""
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
			# int, not float: continuousUpDown feeds this to range(), which refuses a float. It only
			# ever became an int inside the "values" block below, so a command without values threw
			# TypeError into the catch-all and the relay never pulsed.
			try:	nPulses = int(float(command.get("nPulses",1)))
			except Exception:	nPulses = 1

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
	"""Drives a GPIO output pin per a command dict, handling up/down, analogWrite (PWM via pigpio, RPi.GPIO, or gpiozero), and pulseUp/pulseDown actions with optional inversion and delayed start, while reporting actual GPIO values back via sendURL.

	Inputs:
	    command (dict): GPIO command with cmd, pin, PWM, pulse/value and devId fields
	Outputs:
	    None: Configures and drives GPIO/PWM hardware, sends state updates, and logs
	"""
	global PWM, myPID
	global threadsActive
	global DEBUG
	global GPIOZERO
	devType = "OUTPUTgpio"


	#U.logger.log(DEBUG, "{:.2f} into setGPIO command:{}".format(time.time() , command))

	for iiii in range(1):
		try:	PWM = int(command["PWM"])
		except: PWM = 100



		# NOTHING about PWM is decided here any more - see the analogWrite branch below. This used
		# to sit in the path of EVERY command, up/down/pulse included, and did two things it had no
		# business doing per command: open a pigpio client (a socket + a thread, never closed), and
		# probe /proc for pigpiod, which costs 0.1-0.4 s on an older rpi.
		


		# always bound: cmd is used in the log line further down, which sits OUTSIDE the try below,
		# so a command without a "cmd" key used to throw NameError straight out of setGPIO
		cmd = "{}".format(command.get("cmd",""))
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

		# DEFAULTS FIRST, so every branch below has something to work with. They used to be set only
		# inside the "values" block: a command without values left bits undefined (analogWrite then
		# died with NameError) and nPulses a FLOAT, which range() refuses - both swallowed by the
		# catch-all further down, so the command silently did nothing.
		pulseUp = float(command.get("pulseUp",1))
		pulseDown = float(command.get("pulseDown",1))
		try:	nPulses = int(float(command.get("nPulses",1)))
		except Exception:	nPulses = 1
		bits = 0		# analogWrite duty cycle in percent
		# (there was a disableGPIOafterPulse option here: the key is never part of a command, so it
		#  was always True, and the unconditional close at the end of this function made it a no-op
		#  either way. The pin is released at the end, once, and only if we still own it.)

		if "values" in command:
			values =  command.get("values",{})
			if values != {}:
				try:
					pulseUp = float(values.get("pulseUp",1))
					pulseDown = float(values.get("pulseDown",1))
					nPulses = int(float(values.get("nPulses",1)))
					bits = min(100,int(values.get("bits",-1)))
					analogValue = min(100.,float(values.get("analogValue",-1)))
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

		# claim the pin HERE, not before the delayStart wait above: a command scheduled for tonight
		# must not take the pin away from the one driving it right now.
		myGen = claimGPIOpin(pin)

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
					if sleepOwningPin(1000000000, pin, myGen):
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
					if sleepOwningPin(1000000000, pin, myGen):
						break

			elif cmd in ["analogWrite","analogwrite"]:
				if inverseGPIO:
					value = (100-bits)	# duty cycle on xx hz
				else:
					value =   bits	 # duty cycle on xxx hz 
				value = int(value)
				# decided HERE, where PWM is the point, and with a CACHED pigpiod probe (a daemon
				# that runs stays running - U.pigpiodRunning remembers a positive answer).
				# The verdict is a LOCAL: this used to write the global typeForPWM, so one moment
				# with pigpiod down demoted the whole program to "GPIO" for every later command,
				# until some later readParams() happened to restore it from the parameters file.
				pwmRange   = PWM
				pwmFreq    = PWM
				usePWMtype = "PIGPIO" if (typeForPWM == "PIGPIO" and U.pigpiodRunning()) else "GPIO"
				U.logger.log(DEBUG, "analogwrite pin = {};    duty cyle: {};  PWM={}; using {}".format(pin, value, PWM, usePWMtype) )
				# same devId guard as every other branch - without it a command that carries no
				# device id reported the state against devId "0", which matches no indigo device
				if devId != "0":
					if value > 0:
						U.sendURL({"outputs":{"OUTPUTgpio-1":{devId:{"actualGpioValue":"high"}}}})
					else:
						U.sendURL({"outputs":{"OUTPUTgpio-1":{devId:{"actualGpioValue":"low"}}}})

				if usePWMtype == "PIGPIO":
					#U.logger.log(DEBUG, "..  setting PIGPIO {}  {}  {}".format(pwmFreq, pwmRange,  value) )
					import pigpio
					PIGPIO = getPigpio()			# shared client, not a fresh connection per command
					if PIGPIO is None:
						U.logger.log(20, "analogWrite pin={}: pigpiod not reachable, PWM not set".format(pin) )
					else:
						PIGPIO.set_mode(pin, pigpio.OUTPUT)
						PIGPIO.set_PWM_frequency(pin, pwmFreq)
						PIGPIO.set_PWM_range(pin, pwmRange)
						PIGPIO.set_PWM_dutycycle(pin, value)

				else:
					if useGPIO:
						GPIO.setup(pin, GPIO.OUT)
						p = GPIO.PWM(pin, PWM)	#
						p.start(int(value))	 # start the PWM with  the proper duty cycle
						if sleepOwningPin(1000000000, pin, myGen):
							# stop it before letting go. RPi.GPIO runs the PWM in its own thread and
							# it lived on until the object happened to be garbage collected - so the
							# next command's GPIO.output() on this pin fought a PWM that was still
							# toggling it. Stopping here happens BEFORE the successor writes: it is
							# started ~0.07 s after the stop flag, we react within 0.05 s.
							try:	p.stop()
							except Exception:	pass
							break
					else:
						v = float(value) / 100.
						#U.logger.log(DEBUG, "analogWrite action pin = {}  value:{}, v:{}".format(pin,  value, v) )
						if pin not in GPIOZERO:
							GPIOZERO[pin] = gpiozero.PWMLED(pin, frequency=1000)
						GPIOZERO[pin].value = v
						if sleepOwningPin(1000000000, pin, myGen):
							break

			elif cmd in ["pulseUp","pulseup"]:
				U.logger.log(DEBUG, "pulseUp action pin = {} start, pulseLen:{} inverseGPIO:{}, useGPIO:{}".format(pin,  pulseUp, inverseGPIO, useGPIO) )
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
					GPIO.output(pin, up)
				else:
					# the ON call belongs OUTSIDE the "not in GPIOZERO" test - inside it, a pin whose
					# object already existed was never switched on and the pulse silently did nothing
					# but wait. Same shape as pulseDown below.
					try:
						if pin not in GPIOZERO:
							GPIOZERO[pin] = gpiozero.LED(pin)
						getattr(GPIOZERO[pin], ON)()
					except:
						time.sleep(0.1)
						if pin not in GPIOZERO:
							GPIOZERO[pin] = gpiozero.LED(pin)
						getattr(GPIOZERO[pin], ON)()

				if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":on}}}})
				if sleepOwningPin(pulseUp, pin, myGen): break

				if useGPIO:
					GPIO.output(pin, down)
				else:
					# SWITCH THE EXISTING OBJECT OFF. This used to re-create gpiozero.LED(pin), which
					# switches nothing off - it only worked because the old object still held the pin,
					# so gpiozero raised GPIOPinInUse and the except branch did the real work, after a
					# fixed 0.1 s wait on every single pulse. When the construction DID succeed it
					# drove the pin low, which is the wrong level with inverseGPIO set, and left the
					# old object open.
					try:
						if pin not in GPIOZERO:
							GPIOZERO[pin] = gpiozero.LED(pin)
						getattr(GPIOZERO[pin], OFF)()
					except:
						time.sleep(0.1)
						if pin not in GPIOZERO:
							GPIOZERO[pin] = gpiozero.LED(pin)
						getattr(GPIOZERO[pin], OFF)()

				if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})

			elif cmd in ["pulseDown","pulsedown"]: 
				U.logger.log(DEBUG-10, "pulseDown action pin = {} start, pulseDown:{}, inverseGPIO:{}".format(pin,  pulseDown, inverseGPIO) )
				if useGPIO:
					GPIO.setup(pin, GPIO.OUT)
					GPIO.output(pin, down)
				else:
					try:
						if pin not in GPIOZERO:
							GPIOZERO[pin] = gpiozero.LED(pin)
						getattr(GPIOZERO[pin], OFF)()
					except:
						time.sleep(0.1)
						if pin not in GPIOZERO:
							GPIOZERO[pin] = gpiozero.LED(pin)
						getattr(GPIOZERO[pin], OFF)()
		

				if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
				if sleepOwningPin(pulseDown, pin, myGen): break
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
					if sleepOwningPin(pulseUp, pin, myGen):
						# this was "pass": a stop request during the UP half was ignored for the rest
						# of that half, and worse, the loop then ran on. Leave, but put the output
						# down first - on the RPi.GPIO path nothing resets the pin at the end, so an
						# aborted cycle used to leave it energised until the next command. Unless
						# another command owns the pin now: then it is ITS level, do not touch it.
						if not gpioPinTakenOver(pin, myGen):
							if useGPIO:	GPIO.output(pin, down)
							else:		GPIOZERO[pin].off()
							if devId != "0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
						break
					if useGPIO:
						GPIO.output(pin, down)
					else:
						GPIOZERO[pin].off()
					if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":off}}}})
					if sleepOwningPin(pulseDown, pin, myGen): break
				U.logger.log(DEBUG, "continuousUpDown finished" )


		except Exception as e:
			U.logger.log(20,"", exc_info=True)

	U.logger.log(DEBUG, "exit {}".format(command) )
	U.removeOutPutFromFutureCommands(pin, devType)

	# HANDOVER GRACE - closing the pin object RELEASES the pin (gpiozero hands it back to the pin
	# factory and the level goes with it). On a retrigger, the successor stops this thread ~0.05 s
	# before it claims the pin itself, so closing right here opens a 20-50 ms hole in between: a
	# pulseUp of 5 s re-triggered at second 3 dropped LOW for that long before going high again -
	# invisible on an LED, a chatter on a relay. So wait a moment for a successor to announce
	# itself. If one does, it inherits the still-open, still-driven object and the level never
	# moves. If none comes - a plain stop, or a successor that is scheduled for later and claims
	# the pin only when its delay expires - the pin is released exactly as before, 0.15 s later.
	for _ in range(6):
		if gpioPinTakenOver(pin, myGen):	break
		time.sleep(0.025)

	# release the pin ONLY if no newer command has taken it over - see the comment at gpioOwner.
	# A stale thread closing GPIOZERO[pin] here is exactly how an output that had just been
	# switched on dropped again a moment later.
	if ownsGPIOpin(pin, myGen):
		if pin in GPIOZERO:
			GPIOZERO[pin].close()
			del GPIOZERO[pin]
	else:
		U.logger.log(DEBUG, "setGPIO pin={}: generation {} is done, but a newer command owns the pin now - leaving its output alone".format(pin, myGen) )

	return


### ----------------------------------------- ###
def sleepForxSecs(sleepTime):
	"""Sleeps in small increments for up to the requested number of seconds, aborting early and returning True if the current thread is no longer active or its state is no longer 'running'; returns False if the full sleep completes.

	Inputs:
	    sleepTime (float): Total seconds to wait before completing normally
	Outputs:
	    bool: True if interrupted/aborted, False if the full sleep elapsed
	"""
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
def runQualifyDongle(params):
	"""Runs pi/qualifyDongle.py for the plugin menu and sends the report back to indigo.

	Three things have to be true while it runs:
	  - the radios must be FREE: beaconloop pauses on temp/beaconloop.pause (timestamp content,
	    55 s failsafe - so it has to be REFRESHED, not written once), BLEconnect on
	    temp/BLEconnect.pause. Neither program is killed, they resume by themselves.
	  - master.py must not think anything is stuck: it judges by temp/alive.<pgm> and restarts a
	    program whose timestamp is older than ~200 s. A paused beaconloop does not write its own,
	    so this thread writes them for both while the test runs.
	  - the report has to reach indigo: stdout of the tool is captured and sent as one string.

	Inputs:
	    params (str): "secs;connectMac;tries" as built by the plugin menu
	Outputs:
	    None
	"""
	pauseFiles = [G.homeDir+"temp/beaconloop.pause", G.homeDir+"temp/BLEconnect.pause"]
	keepGoing  = [True]
	# HARD CAP on how long the radios may stay handed over. The refresh below defeats BOTH failsafes
	# (beaconloop 55 s, BLEconnect 120 s) by design, so as long as this thread runs the two programs
	# are pinned - if the tool hangs, or its sudo/sh wrappers get killed under it (killSudos runs every
	# 10 master loops) and the pipe read below never returns, nothing else would ever free the radios.
	# 3 adapters x (2 measuring phases + 3 connect attempts) is ~4 min, so 10 min is generous.
	maxRunSecs = 600.
	tStart     = time.time()
	th         = None

	def keepAlive():
		# refresh the pause files AND the alive files every few seconds for the whole run
		while keepGoing[0]:
			tt = time.time()
			if tt - tStart > maxRunSecs:
				U.logger.log(20, "qualifyDongle: {:.0f}s cap reached - releasing beaconloop/BLEconnect while the tool keeps running".format(maxRunSecs))
				break
			for ff in pauseFiles:
				try:	U.doWriteSimpleFile(ff, "{}".format(tt))
				except Exception:	pass
			for pgm in ["beaconloop", "BLEconnect"]:
				try:	U.doWriteSimpleFile("{}temp/alive.{}".format(G.homeDir, pgm), "{}".format(tt))
				except Exception:	pass
			time.sleep(5)
		keepGoing[0] = False
		for ff in pauseFiles:					# stop refreshing AND clear, so the radios come back now
			try:
				if os.path.isfile(ff):	os.remove(ff)
			except Exception:	pass

	try:
		secs, mac, tries = "10", "", "3"
		pp = "{}".format(params).split(";")
		if len(pp) > 0 and pp[0].strip() != "":	secs  = pp[0].strip()
		if len(pp) > 1:							mac   = pp[1].strip()
		if len(pp) > 2 and pp[2].strip() != "":	tries = pp[2].strip()

		U.logger.log(20, "qualifyDongle: pausing beaconloop/BLEconnect, {}s per phase{}".format(
						secs, ", connect test to {} x{}".format(mac, tries) if mac else ""))
		th = threading.Thread(target=keepAlive)
		th.daemon = True
		th.start()
		time.sleep(3)			# let beaconloop/BLEconnect notice the pause and let go of the radios

		# output goes to a FILE, not to a PIPE + communicate(): communicate() returns only when every
		# writer of the pipe is gone, and the write end is inherited by the sudo/sh wrappers AND by
		# every helper qualifyDongle spawns. killSudos (master, every 10th loop) kills the "sudo .."
		# and "/bin/sh -c sudo .." wrappers - which does NOT kill the python child, it only orphans it -
		# and a single surviving holder of that fd blocks communicate() forever, with the pause files
		# being refreshed all the while. A file has no such coupling, and poll() below is bounded.
		outFile  = G.homeDir+"temp/qualifyDongle.out"
		jsonFile = G.homeDir+"temp/qualifyDongle.json"
		for ff in [outFile, jsonFile]:				# old results must not be mistaken for this run
			try:
				if os.path.isfile(ff):	os.remove(ff)
			except Exception:	pass
		# -u: unbuffered. print() into a redirected file is block buffered (8 kB), so without it the
		# whole report appears only when the tool exits - and "tail -f temp/qualifyDongle.out" shows
		# nothing at all while the ~4 min run is in progress, exactly when you want to watch it.
		# NO send=yes: the tool writes its result to the two files above and WE send both, in one
		# message. It then needs no sendURL and no piBeaconUtils at all - which is what used to keep
		# it alive after it was done (non-daemon send thread) and left the radios paused.
		# catalogue=none: no per-rpi copy on the pi. The catalogue that counts is the plugin's, in the
		# indigo preferences directory, fed by every rpi - we forward the structured result for it.
		cmd = "sudo python3 -u {}qualifyDongle.py {} catalogue=none".format(G.homeDir, secs)
		if mac != "":	cmd += " connect={} tries={}".format(mac, tries)
		U.logger.log(20, "qualifyDongle: running: {} > {} 2>&1".format(cmd, outFile))
		proc = subprocess.Popen("{} > {} 2>&1".format(cmd, outFile), shell=True)
		while proc.poll() is None:			# no communicate(timeout=..), that is python3 only
			if time.time() - tStart > maxRunSecs:
				U.logger.log(20, "qualifyDongle: still running after {:.0f}s - giving up waiting, radios released".format(maxRunSecs))
				break
			time.sleep(1)

		out = ""
		try:	out = U.doReadSimpleFile(outFile)
		except Exception:	pass
		if not isinstance(out, str):	out = out.decode("utf-8", "replace")

		entries = ""
		try:
			if os.path.isfile(jsonFile):	entries = U.doReadSimpleFile(jsonFile).strip()
		except Exception:	pass

		payload = {}
		if out.strip() != "":		payload["dongleQualifyReport"] = out		# full text -> indigo log
		if entries      != "":		payload["dongleQualify"]       = entries	# structured -> catalogue
		if payload != {}:
			# ONE message with both keys - the plugin handler logs the report and then merges the
			# entries into its dongleCatalogue.json from the same varJson.
			U.logger.log(20, "qualifyDongle: finished, sending {} chars of report{} back to indigo".format(
							len(out), " + catalogue entries" if entries != "" else " (no structured result)"))
			U.sendURL(data={"data": payload}, squeeze=False, wait=False)
		else:
			U.logger.log(20, "qualifyDongle: no output produced - nothing sent to indigo")
	except Exception:
		U.logger.log(20, "", exc_info=True)
	finally:
		keepGoing[0] = False
		try:
			if th is not None:	th.join(12)					# let the refresh thread stop BEFORE deleting, else it
		except Exception:	pass			# re-creates the pause files right after the remove below
		for ff in pauseFiles:
			try:
				if os.path.isfile(ff):	os.remove(ff)
			except Exception:	pass
		U.logger.log(20, "qualifyDongle: beaconloop/BLEconnect released")
	return


####################
def execCMDS(nextItem):
	"""Worker run by a thread that interprets a command dict and dispatches it to the appropriate action: running shell commands, writing files, signaling the beacon loop (beep, getBeaconParameters, updateTimeAndZone, BLEAnalysis, trackMac), or handing off to stepper-motor, display, and neopixel helper programs.

	Inputs:
	    nextItem (dict): Command descriptor with command, device, values and timing fields
	Outputs:
	    None: Executes commands, writes signal/input files, spawns helper processes, and logs
	"""
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
							U.doWriteSimpleFile("{}temp/touchFile".format(G.homeDir), time.time())
						subprocess.call("sudo chown -R  pi  "+G.homeDir, shell=True)
					except Exception as e:
						U.logger.log(20,"", exc_info=True)
				continue


			if cmd == "getBeaconParameters":
				if delayStart > 0 and delayStart < 10000000: 
					U.logger.log(DEBUG,"{:.2f} delay start by: {}".format(time.time(), delayStart))
					if sleepForxSecs(delayStart):
						return 
				try:
						gattTarget = "BLEconnect" if gattviaBLEconnect() else "beaconloop"
						U.logger.log(DEBUG, "execcmd. getBeaconParameters -> {}, write: ={}".format(gattTarget, nextItem["device"]))
						fn = G.homeDir+"temp/"+gattTarget+".getBeaconParameters"
						# MERGE with a not-yet-consumed request instead of overwriting it (command
						# threads can race; overwrite lost macs). A mac already listed stays as it
						# is - the second request for the same mac is ignored, no double read.
						with getBeaconParametersLock:
							devs = json.loads(nextItem["device"])
							if os.path.isfile(fn):
								try:
									old = json.load(open(fn))
									for bMac in old: devs[bMac] = old[bMac]
								except Exception: pass
							f = open(fn,"w")
							f.write(json.dumps(devs))
							f.close()
				except Exception as e:
						U.logger.log(20,"", exc_info=True)
				continue


			if cmd == "beepBeacon":
				if delayStart > 0 and delayStart < 10000000: 
					U.logger.log(DEBUG,"{:.2f} delay start by: {}".format(time.time(), delayStart))
					if sleepForxSecs(delayStart):
						return 
				try:
						gattTarget = "BLEconnect" if gattviaBLEconnect() else "beaconloop"
						U.logger.log(DEBUG, "execcmd. beep -> {}, write: ={}".format(gattTarget, str(nextItem["device"])[:20]))
						f = open(G.homeDir+"temp/"+gattTarget+".beep","a")
						f.write(nextItem["device"]+"\n") 
						f.close()
				except Exception as e:
						U.logger.log(20,"", exc_info=True)
				continue


			if cmd == "updateTimeAndZone":
				try:
						gattTarget = "BLEconnect" if gattviaBLEconnect() else "beaconloop"
						U.logger.log(DEBUG, "execcmd. updateTimeAndZone -> {}, write: ={}".format(gattTarget, str(nextItem["device"])[:20]))
						f = open(G.homeDir+"temp/"+gattTarget+".updateTimeAndZone","a")
						f.write(nextItem["device"]+"\n") 
						f.close()
				except Exception as e:
						U.logger.log(20,"", exc_info=True)
				continue

			if	cmd == "qualifyDongle":
				# long running (3 phases x secs + resets): own thread, so the command socket is
				# not blocked and the plugin gets its ack straight away
				try:
					# level 20 on purpose: this is a manual, rare action started from the plugin menu -
					# if it does not arrive, the first question is whether the rpi saw it at all
					U.logger.log(20, "execcmd. qualifyDongle RECEIVED, params:>{}<".format(nextItem.get("device", "")))
					thQ = threading.Thread(target=runQualifyDongle, args=("{}".format(nextItem.get("device", "")),))
					thQ.daemon = True
					thQ.start()
				except Exception:
					U.logger.log(20, "", exc_info=True)
				continue


			if	cmd == "BLEAnalysis":
					if "minRSSI" not in nextItem: minRSSI = "-61"
					else:					  minRSSI = nextItem["minRSSI"]
					U.doWriteSimpleFile(G.homeDir+"temp/beaconloop.BLEAnalysis", minRSSI)
					continue

			if	cmd == "trackMac":
					if "mac" in nextItem: 
						U.doWriteSimpleFile(G.homeDir+"temp/beaconloop.trackmac", nextItem["mac"])
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
						U.logger.log(20,"", exc_info=True)
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
						U.logger.log(20,"", exc_info=True)
				continue


			if device.lower().find("neopixel") > -1:### OUTPUT-neopixel
				cmdOut = json.dumps(nextItem)
				if "neopixel" not in output: continue
				if usePython3:	py2orpy3 = "py3"
				else:			py2orpy3 = "py2"
				#U.logger.log(20,"usePython3:{}, py2orpy3:{}".format(usePython3,py2orpy3 ))

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
						U.logger.log(20,"", exc_info=True)
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
							U.touchFile(G.homeDir + "temp/" + pgm + ".now")
						continue


			if	cmd == "resetDevice":
						if nextItem["device"].find(",") > 1:
							list = nextItem["device"].split(",")
						elif nextItem["device"] == "all":
							list = G.programFiles + G.specialSensorList + G.specialOutputList + G.programFiles
						else:
							list = [nextItem["device"]]
						for pgm in list:
							U.touchFile(G.homeDir + "temp/" + pgm + ".reset")
						continue


			if	cmd == "restartDevice":
						if nextItem["device"].find(",") > 1:
							list = nextItem["device"].split(",")
						elif nextItem["device"] == "all":
							list = G.programFiles + G.specialSensorList + G.specialOutputList + G.programFiles
						else:
							list = [nextItem["device"]]
						for pgm in list:
							U.touchFile(G.homeDir + "temp/" + pgm + ".restart")
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
							#U.logger.log(20,"xxx= {}".format(xxx))
							if len(xxx) > 0:
								fname  = '{}temp/{}.startCalibration'.format(G.homeDir, xxx[0])
								out = '{{"value":{}}}'.format(  xxx[1])
								U.logger.log(20," start calibration..  pgm:{}, data:{}".format(xxx[0], out))
								f = open(fname,"w")
								f.write(out)
								f.close()
							else:
								U.logger.log(20," start calibration ..  for pgm:{}".format(xxx[0]))
								U.touchFile("{}temp/{}.startCalibration".format( G.homeDir, xxx[0]))
						continue




			if device == "setMCP4725":
						try:
							i2cAddress = U.getI2cAddress(nextItem, default =0)
							if cmd == "disable" :
								if threadName in execcommandsList:
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
							U.logger.log(20,"", exc_info=True)
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
							U.logger.log(20,"", exc_info=True)
						continue


			if device == "OUTgpio" or device.find("OUTPUTgpio")> -1:
						#U.logger.log(G.debug*20, "{:.2f} into if OUTgpio".format(time.time()))
						try:
							pinI = int(nextItem["pin"])
							pin = str(pinI)
						except Exception as e:
							U.logger.log(20,"", exc_info=True)
							U.logger.log(DEBUG,"bad pin {}".format(nextItem))
							continue

						if "aw" 				in nextItem: nextItem["analogwrite"] 		= nextItem["aw"]
						if "cup" 				in nextItem: nextItem["continuousupdown"] 	= nextItem["cup"]
						if "pu" 				in nextItem: nextItem["pulseup"] 			= nextItem["pu"]
						if "pd" 				in nextItem: nextItem["pulsedown"]			= nextItem["pd"]
						if "np" 				in nextItem: nextItem["npulses"] 			= nextItem["np"]
						# "analogValue", NOT "analogwrite": setGPIO reads values["analogValue"] (or
						# values["bits"]). Under the old name the duty cycle never arrived, both
						# lookups fell through to their -1 default and the pin was driven with 0% -
						# a short-form "aw=60" simply switched the output off.
						if "analogwrite" 		in nextItem: values["analogValue"] 			= float(nextItem.get("analogwrite",1))
						# NOTE values["continuousUpDown"] is not read anywhere - the number of pulses
						# comes from "np"/"npulses" below. Left as it is: what a bare "cup=<n>" was
						# once meant to set cannot be told from the code.
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
							U.logger.log(20,"", exc_info=True)
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
						# "analogValue", NOT "analogwrite": setGPIO reads values["analogValue"] (or
						# values["bits"]). Under the old name the duty cycle never arrived, both
						# lookups fell through to their -1 default and the pin was driven with 0% -
						# a short-form "aw=60" simply switched the output off.
						if "analogwrite" 		in nextItem: values["analogValue"] 			= float(nextItem.get("analogwrite",1))
						# NOTE values["continuousUpDown"] is not read anywhere - the number of pulses
						# comes from "np"/"npulses" below. Left as it is: what a bare "cup=<n>" was
						# once meant to set cannot be told from the code.
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
							U.logger.log(20,"", exc_info=True)
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
							U.logger.log(20,"", exc_info=True)
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
	"""Scans the active-threads registry and stops command threads, either all of them when all=True or only those whose state is no longer 'running', by calling stopExecCmd on each.

	Inputs:
	    all (bool): If True stop every thread, otherwise only non-running ones
	Outputs:
	    None: Stops matching threads via stopExecCmd and logs on error
	"""
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
		U.logger.log(20,"", exc_info=True)

				 
### ----------------------------------------- ###
def execSimple(nextItem):
	"""Quickly handles simple 'general' commands inline (without spawning a thread): executes reboot/halt, setTime, refreshNTP, and stopNTP command lines, returning True if it handled one and False otherwise.

	Inputs:
	    nextItem (dict): Command descriptor expected to have command and cmdLine fields
	Outputs:
	    bool: True if a simple command was executed, False if not applicable
	"""
	global DEBUG
	global inp
	if "command" not in nextItem:		 return False
	try: 
		if nextItem["command"] != "general": return False
	except:
		U.logger.log(20,"nextItem >>{}<<".format(nextItem))
		return False
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
		U.logger.log(20,"", exc_info=True)
	return False

	### ----------------------------------------- ###
	### ---------exec commands end -------------- ###
	### ----------------------------------------- ###




class MyTCPHandler(socketserver.BaseRequestHandler):

	### ----------------------------------------- ###
	def handle(self):
		"""TCP socket request handler that reads the full client message, parses it as a JSON list of commands, and processes each either inline via execSimple or by spawning a command thread via setupexecThreads, then refreshes params and reaps finished threads.

		Inputs:
		    None.
		Outputs:
		    None: Reads the socket, dispatches commands, and refreshes params/threads
		"""
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
				U.logger.log(20,"", exc_info=True)
				U.logger.log(20,"bad command: json failed {}".format(data))
				return

		#U.logger.log(20, "commands:{}".format(commands) )
			
		for nextItem in commands:
			if execSimple(nextItem): continue
			setupexecThreads(nextItem, "socket")
 
		readParams()
		stopThreadsIfEnded()
		return	 

### ----------------------------------------- ###
def setupexecThreads(nextItem, source):
	"""Builds a thread name from the command's pin/device/i2cAddress/command, stops any existing thread with that name, then starts a new daemon thread running execCMDS for the command and records it in the active-threads registry with logging of changes.

	Inputs:
	    nextItem (dict): Command descriptor used to derive the thread name and run
	    source (str): Origin label of the command for logging (e.g. 'socket')
	Outputs:
	    bool: True if a thread was started, False on missing command or error
	"""
	global inp
	global threadsActive
	global lastOut
	global counter
	global DEBUG
	global displayCounter
	try:
		if "command" not in nextItem: return False
		counter += 1
		
		threadName = ""
		if "pin" in nextItem and nextItem["pin"] != "": 					threadName += "pin-"+str(nextItem["pin"])
		elif "device" in nextItem and nextItem["device"] != "":				threadName = nextItem["device"]
		elif "i2cAddress" in nextItem and nextItem["i2cAddress"] != "": 	threadName += "-"+str(nextItem["i2cAddress"])
		if threadName == "":												
			try:
				threadName = nextItem["command"]
			except:
				threadName = "xxx"
				
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
		if displayCounter < 3:
			displayCounter +=1
			if changed != "":
				U.logger.log(DEBUG,"{:.2f} thread from:{:}, #:{:3d} started, name={:}, command:{:} ... {:} changed:{:}".format(time.time(), source, counter, threadName, out[:ll], out[-ll:],  changed))
			else:
				U.logger.log(DEBUG,"thread from:{:}, #:{:3d} started, name={:}, command:{:} ... {:}".format(source,counter, threadName, out[:ll], out[-ll:]))
		
		lastOut = out

		return True

	except Exception as e:
		U.logger.log(20,"", exc_info=True)
	return False



		

### ----------------------------------------- ###
def stopExecCmd(threadName):
	"""Signals a named command thread to stop by setting its state to 'stop', waits briefly for it to notice, and removes it from the active-threads registry.

	Inputs:
	    threadName (str): Key of the thread in the active-threads registry to stop
	Outputs:
	    None: Marks the thread to stop and deletes its registry entry
	"""
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
		U.logger.log(20,"", exc_info=True)
	try: 	del threadsActive[threadName]
	except: pass
	return 


### ----------------------------------------- ###
def getcurentCMDS():
	"""Loads the persisted execcommandsList.current JSON file and, unless the action is 'delete', restarts an exec thread for each stored command entry, then rewrites the file with the retained commands; deletes the file on a delete action or if the contents are invalid.

	Inputs:
	    None.
	Outputs:
	    None: restarts exec threads, rewrites/deletes the execcommandsList.current file, and logs errors
	"""
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
					U.logger.log(20,"", exc_info=True)
					continue
				setupexecThreads(nextItem, "current")

			f = open(G.homeDir+"execcommandsList.current","w")
			f.write(json.dumps(keep))
			f.close()

	except Exception as e:
		U.logger.log(20,"", exc_info=True)
	return 



### ----------------------------------------- ###
### -- read from file in temp dir and then execute command--- ###
### ----------------------------------------- ###
def setupReadTempDirThread():
	"""Creates and starts a daemon background thread named 'readTempDir' that runs readTempDirThread, registering it in the global threadsActive dict.

	Inputs:
	    None.
	Outputs:
	    bool: True if the thread started successfully, False on exception
	"""
	global DEBUG
	global threadsActive
	threadName = "readTempDir"
	try:
		threadsActive[threadName] = {"state":"running", "thread": threading.Thread(name=threadName, target=readTempDirThread, args=())}	
		threadsActive[threadName]["thread"].daemon = True
		threadsActive[threadName]["thread"].start()
		return True

	except Exception as e:
		U.logger.log(20,"", exc_info=True)
	return False

### ----------------------------------------- ###
def readTempDirThread():
	"""Long-running thread loop that polls the temp/receiveCommands.input file every 50ms, parses each JSON command line, deletes the file, and dispatches each command either inline via execSimple or by spawning an exec thread.

	Inputs:
	    None.
	Outputs:
	    None: runs until thread state changes; executes commands, deletes input file, and logs
	"""
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
				U.logger.log(DEBUG, "from file:>>{}<<, type:{}".format(commandList, type(commandList)))
	
				U.removeFile(fName)

				if commandList != []:
					for commands in commandList:
						if type(commands) == type({}):
							useList = [commands]
						else:
							useList = commands
						for nextItem in useList:
							U.logger.log(DEBUG, "readTempDirThread nextItem:{}, type:{}".format(nextItem,  type(nextItem)))
							if execSimple(nextItem): continue
							tag = str(time.time())
							tempcmdCount += 1
							setupexecThreads(nextItem, "tempdir"+str(tempcmdCount))
	
	
			#'[{"device": "OUTPUTgpio-1", "command": "up", "pin": "19"}]'
	except Exception as e:
		U.logger.log(20,"", exc_info=True)

	U.logger.log(DEBUG, "readTempDirThread exit")

### ----------------------------------------- ###
### -- END read from file in temp dir and then execute command--- ###
### ----------------------------------------- ###
### ----------------------------------------- ###
	
				 
### ----------------------------------------- ###
def readParams():
	"""Reads the plugin input via U.doRead, applies global params, and populates module globals (output, readOutput, PWM, typeForPWM, execcommandsListAction, readInput, usePython3) from the parsed input dict.

	Inputs:
	    None.
	Outputs:
	    None: sets module-level globals from input and logs errors
	"""
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
		U.logger.log(20,"", exc_info=True)
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
	global displayCounter
	
	
	displayCounter		= 0
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
		#U.logger.log(20,"", exc_info=True)
		U.logger.log(20, "getting  socket does not work, trying to reset port {}".format(PORT) )
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

				# is THIS pid master.py? the old grep searched the pid as a STRING anywhere in the
				# ps line, so it also hit rows where our pid was the PARENT pid, or part of a time
				# field - asking /proc for the pid itself cannot be ambiguous
				if len([1 for _pp, _cc in U.procList("master.py") if _pp == pid]) > 0:
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
