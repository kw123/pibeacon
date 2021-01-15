#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7 
##
import SocketServer
import RPi.GPIO as GPIO
import smbus
import re
import json, sys,subprocess, os, time, datetime
import copy

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "execcommands"

allowedCommands=["up","down","pulseUp","pulseDown","continuousUpDown","analogWrite","disable","myoutput","omxplayer","display","newMessage","resetDevice",
				"startCalibration","getBeaconParameters","beepBeacon","file","BLEreport","BLEAnalysis","trackMac"]


externalGPIO = False



def OUTPUTi2cRelay(command):
	global myPID, debLevel
	import smbus
	try:
		devType = "OUTPUTi2cRelay"

		U.logger.log(10, "OUTPUTi2cRelay command:{}".format(command) )
		if "cmd" in command:
			cmd= command["cmd"]
			if cmd not in allowedCommands:
				U.logger.log(30, "OUTPUTi2cRelay pid=%d, bad command %s  allowed only: %s" %(myPID,unicode(command) ,unicode(allowedCommands))  )
				exit(1)

		if "pin" in command:
			pin= int(command["pin"])
		else:
			U.logger.log(30, "setGPIO pid=%d, pin not included,  bad command %s"%(myPID,unicode(command)) )
			exit(1)

		DEVICE_BUS = 1
		bus = smbus.SMBus(DEVICE_BUS)

		i2cAddress = int(command["i2cAddress"])
		pin = command["pin"]


		delayStart = max(0,U.calcStartTime(command,"startAtDateTime")-time.time())
		if delayStart > 0: 
			time.sleep(delayStart)

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
		except	Exception, e:
			U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
				U.logger.log(20, "relay {} {} {} ".format(i2cAddress, pin, down))
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})

			elif cmd == "down":
				U.logger.log(20, "relay {} {} {} ".format(i2cAddress, pin, down))
				bus.write_byte_data(i2cAddress, pin, 0x00)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})

			elif cmd == "pulseUp":
				bus.write_byte_data(i2cAddress, pin, up)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})
				time.sleep(pulseUp)
				bus.write_byte_data(i2cAddress, pin, down)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})

			elif cmd == "pulseDown":
				bus.write_byte_data(i2cAddress, pin, down)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":off}}}})
				time.sleep(pulseDown)
				bus.write_byte_data(i2cAddress, pin, up)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTi2cRelay":{devId:{"actualGpioValue":on}}}})

			elif cmd == "continuousUpDown":
				for ii in range(nPulses):
					bus.write_byte_data(i2cAddress, pin, up)
					time.sleep(pulseUp)
					bus.write_byte_data(i2cAddress, pin, down)
					time.sleep(pulseDown)

			U.removeOutPutFromFutureCommands(pin, devType)
			

		except Exception, e:
				U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
  	except Exception, e:
			U.logger.log(50, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))





def setGPIO(command):
	global PWM, myPID, typeForPWM, debLevel
	import RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	devType = "OUTPUTgpio"



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
			U.logger.log(30, "setGPIO pid=%d, bad command %s  allowed only: %s" %(myPID,unicode(command) ,unicode(allowedCommands))  )
			exit(1)

	if "pin" in command:
		pin= int(command["pin"])
	else:
		U.logger.log(30, "setGPIO pid=%d, pin not included,  bad command %s"%(myPID,unicode(command)) )
		exit(1)



	delayStart = max(0,U.calcStartTime(command,"startAtDateTime")-time.time())
	if delayStart > 0: 
		time.sleep(delayStart)

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
	except	Exception, e:
		U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		exit(0)

	inverseGPIO = False
	if "inverseGPIO" in command:
		inverseGPIO = command["inverseGPIO"]

	if "devId" in command:
		devId = str(command["devId"])
	else: devId = "0"


	try:
		if cmd == "up":
			GPIO.setup(pin, GPIO.OUT)
			if inverseGPIO: 
				GPIO.output(pin, False)
				U.logger.log(debLevel, "setGPIO pin={}; command {}".format(pin,False) )
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"low"}}}})
			else:
				GPIO.output(pin, True)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"high"}}}})
				U.logger.log(debLevel, "setGPIO pin={}; command {}".format(pin,True) )
		

		elif cmd == "down":
			GPIO.setup(pin, GPIO.OUT)
			if inverseGPIO: 
				GPIO.output(pin, True)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"high"}}}})
				U.logger.log(debLevel, "setGPIO pin={}; command {}".format(pin,True) )
			else: 
				GPIO.output(pin, False )
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"low"}}}})
				U.logger.log(debLevel, "setGPIO pin={}; command {}".format(pin,False) )

		elif cmd == "analogWrite":
			if inverseGPIO:
				value = (100-bits)	# duty cycle on xx hz
			else:
				value =   bits	 # duty cycle on xxx hz 
			value = int(value)
			U.logger.log(debLevel, "analogwrite pin = {};    duty cyle: {};  PWM={}; using {}".format(pin, value, PWM, typeForPWM) )
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
			time.sleep(1000000000)	# we need to keep it alive otherwise it will stop  this is > 1000 days ~ 3 years


		elif cmd == "pulseUp":
			GPIO.setup(pin, GPIO.OUT)
			if inverseGPIO: 
				GPIO.output(pin, False)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"low"}}}})
			else:		
				GPIO.output(pin, True)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"high"}}}})
			time.sleep(pulseUp)
			if not inverseGPIO: 
				GPIO.output(pin, False)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"low"}}}})
			else:		
				GPIO.output(pin, True)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"high"}}}})



		elif cmd == "pulseDown":
			GPIO.setup(pin, GPIO.OUT)
			if not inverseGPIO: 
				GPIO.output(pin, False)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"low"}}}})
			else:		
				GPIO.output(pin, True)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"high"}}}})
			time.sleep(pulseDown)
			if  inverseGPIO: 
				GPIO.output(pin, False)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"low"}}}})
			else:		
				GPIO.output(pin, True)
				if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"high"}}}})

		elif cmd == "continuousUpDown":
			GPIO.setup(pin, GPIO.OUT)
			for ii in range(nPulses):
				if inverseGPIO: 
					GPIO.output(pin, False)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"low"}}}})
				else:		
					GPIO.output(pin, True)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"high"}}}})
				time.sleep(pulseUp)
				if not inverseGPIO: 
					GPIO.output(pin, False)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"low"}}}})
				else:		
					GPIO.output(pin, True)
					if devId !="0": U.sendURL({"outputs":{"OUTPUTgpio-1-ONoff":{devId:{"actualGpioValue":"high"}}}})
				time.sleep(pulseDown)

		U.removeOutPutFromFutureCommands(pin, devType)
			


	except	Exception, e:
		U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	return 


def execCMDS(data):
	global execcommands, PWM, debLevel

	for ijji in range(1):
			next =""
			try:
				next = json.loads(data)
			except	Exception, e:
					U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					U.logger.log(30," bad command: json failed  %s"%unicode(data))
					continue

			#print next
			#print "next command: "+unicode(next)
			U.logger.log(debLevel,"next command: "+unicode(data))
			cmd= next["command"]

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


			if cmd =="file":
				if "fileName" in next and "fileContents" in next:
					#print next
					try:
						m = "w"
						if "fileMode" in next and next["fileMode"].lower() =="a": m="a"
						#print "write to",next["fileName"], json.dumps(next["fileContents"]), m
						f = open(next["fileName"],m)
						f.write("{}".format(json.dumps(next["fileContents"]) )) 
						f.close()
						if "touchFile" in next and next["touchFile"]:
							subprocess.call("echo	 "+str(time.time())+" > "+G.homeDir+"temp/touchFile" , shell=True)
						subprocess.call("sudo chown -R  pi  "+G.homeDir, shell=True)
					except	Exception, e:
						U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				continue


			if cmd =="getBeaconParameters":
				try:
						U.logger.log(20, u"execcmd. getBeaconParameters, write: ={}".format(next["device"]))
						f = open(G.homeDir+"temp/beaconloop.getBeaconParameters","w")
						f.write(next[u"device"]) 
						f.close()
				except	Exception, e:
						U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				continue


			if cmd =="beepBeacon":
				try:
						U.logger.log(20, u"execcmd. beep, write: ={}".format(next["device"]))
						f = open(G.homeDir+"temp/beaconloop.beep","a")
						f.write(next["device"]+"\n") 
						f.close()
				except	Exception, e:
						U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
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
						U.logger.log(30, u"trackMac, no mac number supplied")
					continue


			if "device" not in next:
				U.logger.log(30," bad cmd no device given "+unicode(next))
				continue
				

			device = next["device"]

			
			if device.lower()=="setsteppermotor":
				cmdOut = json.dumps(next)
				if cmdOut != "":
					try:
						f=open(G.homeDir+"temp/setStepperMotor.inp","a")
						f.write(cmdOut+"\n")
						f.close()
					except	Exception, e:
						U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				continue
			
			if device.lower()=="output-display":
				cmdOut = json.dumps(next)
				if cmdOut != "":
					try:
						#print "execcmd", cmdOut
						if not U.pgmStillRunning("display.py"):
							subprocess.call("/usr/bin/python "+G.homeDir+"display.py &" , shell=True)
						f=open(G.homeDir+"temp/display.inp","a")
						f.write(cmdOut+"\n")
						f.close()
						f=open(G.homeDir+"display.inp","w")
						f.write(cmdOut+"\n")
						f.close()
					except	Exception, e:
						U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				continue


			if device.lower() == "output-neopixel":### OUTPUT-neopixel
				cmdOut = json.dumps(next)
				if cmdOut != "":
					try:
						#print "execcmd", cmdOut
						if	not U.pgmStillRunning("neopixel.py"):
							subprocess.call("/usr/bin/python "+G.homeDir+"neopixel.py	 &" , shell=True)
						else:
							f=open(G.homeDir+"temp/neopixel.inp","a")
							f.write(cmdOut+"\n")
							f.close()
							f=open(G.homeDir+"neopixel.inp","w")
							f.write(cmdOut+"\n")
							f.close()
					except	Exception, e:
						U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				continue




			if cmd not in allowedCommands:
				U.logger.log(30," bad cmd not in allowed commands {} \n{}".format(cmd, allowedCommands))
				continue


			if "values" in next:
				values = next["values"]
			else:
				values =""

			startAtDateTime =unicode(time.time())
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
								if str(int(i2cAddress)+1000) in execcommands:
									del execcommands[str(int(i2cAddress)+1000)]
							cmdJ= json.dumps({"cmd":cmd,"i2cAddress":i2cAddress,"startAtDateTime":startAtDateTime,"values":values, "devId":devId })
							U.logger.log(10,json.dumps(next))
							cmdOut="python "+G.homeDir+"setmcp4725.py '"+ cmdJ+"'  &"
							U.logger.log(10," cmd= %s"%cmdOut)
							subprocess.call(cmdOut, shell=True)
							if restoreAfterBoot == "1":
								execcommands[str(int(i2cAddress)+1000)] = next
							else:
								try: del execcommands[str(int(i2cAddress)+1000)]
								except:pass

						except	Exception, e:
							U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						continue

			if device=="setPCF8591dac":
						try:
							i2cAddress = U.getI2cAddress(next, default =0)
							if cmd =="disable" :
								del execcommands[str(int(i2cAddress)+1000)]
								continue
							cmdJ= json.dumps({"cmd":cmd,"i2cAddress":i2cAddress,"startAtDateTime":startAtDateTime,"values":values, "devId":devId})
							U.logger.log(10,json.dumps(next))
							cmdOut="python "+G.homeDir+"setPCF8591dac.py '"+ cmdJ+"'  &"
							U.logger.log(10," cmd= %s"%cmdOut)
							subprocess.call(cmdOut, shell=True)
							if restoreAfterBoot == "1":
								execcommands[str(int(i2cAddress)+1000)] = next
							else:
								try: del execcommands[str(int(i2cAddress)+1000)]
								except:pass

						except	Exception, e:
							U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						continue


			if device=="OUTgpio" or device.find("OUTPUTgpio")> -1:
						try:
							pinI = int(next["pin"])
							pin = str(pinI)
						except	Exception, e:
							U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							U.logger.log(30,"bad pin "+unicode(next))
							continue
						#print "pin ok"
						if "values" in next: values= next["values"]
						else:				 values={}
   
						if restoreAfterBoot == "1":
							execcommands[str(pin)] = next
						else:
							try: del execcommands[str(pin)]
							except: pass
						if not externalGPIO:
							#kill last execcommand for THIS pin, ps -ef grep string: eg '"pin": "12"'  with '' !!!
							psefString = (json.dumps({"pin":str(pin)})).strip("{}")
							U.killOldPgm(myPID,"execcommands.py ", param1="'"+psefString+"'")
						if cmd =="disable":
							continue
						cmdJ= {"pin":pin,"cmd":cmd,"startAtDateTime":startAtDateTime,"values":values, "inverseGPIO": inverseGPIO,"debug":G.debug,"PWM":PWM, "devId":devId}
						cmdJD = json.dumps(cmdJ)
						if externalGPIO:
							cmdOut="python "+G.homeDir+"setGPIO.py '"+ cmdJD+"' &"
							U.logger.log(10,"cmd= %s"%cmdOut)
							subprocess.call(cmdOut, shell=True)
						else:
							U.logger.log(10, "setGPIO curr_pid=%d,  command :%s" %(myPID,cmdJD) )
							setGPIO(cmdJ)
						continue


			if  device.find("OUTPUTi2cRelay")> -1:
						try:
							pinI = int(next["pin"])
							pin = str(pinI)
						except	Exception, e:
							U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
							U.logger.log(30,"bad pin "+unicode(next))
							continue
						#print "pin ok"
						if "values" in next: values= next["values"]
						else:				 values={}
   
						if restoreAfterBoot == "1":
							execcommands[str(pin)] = next
						else:
							try: del execcommands[str(pin)]
							except: pass
						if not externalGPIO:
							#kill last execcommand for THIS pin, ps -ef grep string: eg '"pin": "12"'  with '' !!!
							psefString = (json.dumps({"pin":str(pin)})).strip("{}")
							U.killOldPgm(myPID,"execcommands.py ", param1="'"+psefString+"'")
						if cmd =="disable":
							continue
						cmdJ= {"pin":pinI,"cmd":cmd,"startAtDateTime":startAtDateTime,"values":values, "inverseGPIO": inverseGPIO,"debug":G.debug,"i2cAddress":next["i2cAddress"], "devId":devId}
						cmdJD = json.dumps(cmdJ)

						OUTPUTi2cRelay(cmdJ)
						continue

			if device=="myoutput":
						try:
							text   = next["text"]
							cmdOut= "/usr/bin/python "+G.homeDir+"myoutput.py "+text+"	&"
							U.logger.log(10,"cmd= %s"%cmdOut)
							subprocess.call(cmdOut, shell=True)
						except	Exception, e:
							U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						continue

			if device=="playSound":
						cmdOut=""
						try:
							if	 cmd  == "omxplayer":
								cmdOut = json.dumps({"player":"omxplayer","file":G.homeDir+"soundfiles/"+next["soundFile"]})
							elif cmd  == "aplay":
								cmdOut = json.dumps({"player":"aplay","file":G.homeDir+"soundfiles/"+next["soundFile"]})
							else:
								U.logger.log(30, u"bad command : player not right =" + cmd)
							if cmdOut != "":
								U.logger.log(10,"cmd= %s"%cmdOut)
								subprocess.call("/usr/bin/python playsound.py '"+cmdOut+"' &" , shell=True)
						except	Exception, e:
							U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
						continue

			U.logger.log(30,"bad device number/number: "+device)
	f=open(G.homeDir+"execcommands.current","w")
	f.write(json.dumps(execcommands))
	f.close()

	return


def readParams():
	global execcommands, PWM, typeForPWM, killMyselfAtEnd
	killMyselfAtEnd = True
	typeForPWM = "GPIO"
	inp,inpRaw = U.doRead()
	if inp == "": return
	U.getGlobalParams(inp)
	try:
		if u"GPIOpwm"				in inp:	 PWM=			int(inp["GPIOpwm"])
		if u"typeForPWM"			in inp:	 typeForPWM=	inp["typeForPWM"]
	except	Exception, e:
		U.logger.log(30, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))


### main pgm 		 
global execcommands, PWM, myPID, killMyselfAtEnd
global debLevel
if True: #__name__ == "__main__":
	debLevel = 0
	PWM = 100
	myPID = int(os.getpid())
	U.setLogging()
	readParams()
	#G.debug  = 1
#### read exec command list for restart values, update if needed and write back
	execcommands={}
	#print "execcommands" , sys.argv
	if os.path.isfile(G.homeDir+"execcommands.current"):
		try:
			f = open(G.homeDir+"execcommands.current","r")
			xx = f.read()
			f.close()
			execcommands=json.loads(xx)
		except:
			try:	f.close()
			except: pass
			execcommands={}
	else:
		execcommands={}

	U.logger.log(10, u"exec cmd: {}".format(sys.argv))
		
	execCMDS(sys.argv[1])
	time.sleep(0.5)
	if killMyselfAtEnd: 
		#U.logger.log(20, u"exec cmd: killing myself at PID {}".format(myPID))
		#U.killOldPgm(myPID, G.program, param1="",param2="")
		time.sleep(5)
		subprocess.call("sudo kill -9 "+str(myPID) , shell=True)
	exit(0)
