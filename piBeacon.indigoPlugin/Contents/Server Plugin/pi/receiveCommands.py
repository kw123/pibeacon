#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7 
##
import SocketServer
import re
import json, sys,subprocess, os, time, datetime
import copy

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "receiveCommands"

class MyTCPHandler(SocketServer.BaseRequestHandler):

	def handle(self):
		global currentGPIOValues, piVersion
		# self.request is the TCP socket connected to the client
		data =""
		while True:
			buffer = self.request.recv(2048).strip()
			U.logger.log(10, "len of buffer:"+str(len(buffer)))
			if not buffer:
				break
			data+=buffer 
		
		#U.logger.log(10, "{} wrote:".format(self.client_address[0]))
		try:
			commands = json.loads(data.strip("\n"))
		except	Exception, e:
				U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				U.logger.log(30,"bad command: json failed  "+unicode(buffer))
				return

		U.logger.log(10, "len of package:"+str(len(data)))
			
		for next in commands:
			if execGeneral(next): continue

			cmdJ = json.dumps(next)
			U.logger.log(10,"cmd= "+cmdJ)
			#print cmdJ
			cmdOut="/usr/bin/python "+G.homeDir+"execcommands.py '"+ cmdJ+"'  &"
			os.system(cmdOut)
			time.sleep(0.1)
		readParams()
		return	 
				 
def execGeneral(next):
	global inp
	if "command" not in next:		return False
	if next["command"] !="general": return False
	if "cmdLine" not in next:		return False
	
	try:
		# execute unix command
		if next["cmdLine"].lower().find("sudo reboot")>-1 or next["cmdLine"].lower().find("sudo halt")>-1:
			os.system(next["cmdLine"] )	 
			return True
			
		# execute set time command 
		if next["cmdLine"].find("setTime")>-1:
			tt		   = time.time()
			items	   =  next["cmdLine"].split("=")
			mactime	   = items[1]
			os.system('date -s "'+mactime+'"')
			mactt	   = time.mktime( datetime.datetime.strptime(mactime,"%Y-%m-%d %H:%M:%S.%f").timetuple() )
			deltaTime  = tt - mactt
			U.sendURL(data={"deltaTime":deltaTime},sendAlive="alive", wait=False)
			if "useRTC" in inp and inp["useRTC"] !="":
				os.system("hwclock --systohc") # set hw clock to system time stamp, only works if HW is enabled
			return True
		# execute set time command 
		if next["cmdLine"].find("refreshNTP")>-1:
			U.startNTP()
			return True
		if next["cmdLine"].find("stopNTP")>-1:
			U.stopNTP()
			return True

	except	Exception, e:
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return False

def getcurentCMDS():
	global	execcommands,piVersion, output
	global badi2c
	try:
		if os.path.isfile(G.homeDir+"execcommands.current"):
			f=open(G.homeDir+"execcommands.current","r")
			execcommands=json.loads(f.read())
			f.close()
			if len(unicode(execcommands))< 1:
				currentGPIOValues={}
				return
			keep ={}	
			for pin in execcommands:
				if int(pin) < 1000:
					found = False
					for dev in output:
						for devid in output[dev]:
							U.logger.log(10,unicode(dev)+" "+ unicode(devid)+" "+unicode(output[dev][devid]))
							for nn in range(len(output[dev][devid])):
								if "gpio" in output[dev][devid][nn]:
									if str(output[dev][devid][nn]["gpio"]) == str(pin): 
										found= True
										break
							if found: break
						if found: break	   
					if	found:
						keep[pin]=execcommands[pin]
				else:
					keep[pin] = execcommands[pin]
				try:
					next = execcommands[pin]
				except	Exception, e:
					U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
					continue
				cmdJ = json.dumps(next)
				cmdOut="/usr/bin/python "+G.homeDir+"execcommands.py '"+ cmdJ+"'  &"
				U.logger.log(30,"cmd= "+cmdOut)
				os.system(cmdOut)
				time.sleep(0.3) # give each command time to finish
			if keep!={}:
				f=open(G.homeDir+"execcommands.current","w")
				f.write(json.dumps(keep))
				f.close()
	except	Exception, e:
			U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
				 
def readParams():
	global	output, useLocalTime, myPiNumber, inp
	inp,inpRaw = U.doRead()
	if inp == "": return
	U.getGlobalParams(inp)
	if u"output"			in inp:	 output=				inp["output"]
		 
	try:
		if os.path.isfile(G.homeDir+"temp/networkOFF"):
			f=open(G.homeDir+"\temp\networkOFF","r")
			off = f.read()
			f.close() 
			if off =="off": 
				return 1
	except:
		pass
	return 0

if __name__ == "__main__":
	global	currentGPIOValue, piVersion
	PORT = int(sys.argv[1])
	U.setLogging()

	myPID		= str(os.getpid())
	U.killOldPgm(myPID,G.program+".py")# del old instances of myself if they are still running

	time.sleep(0.5)
	
	readParams()

	if U.getNetwork < 1:
		U.logger.log(30, u"network not active, sleeping ")
		time.sleep(500)# == 500 secs
		exit(0)
	# if not connected to network pass
		
		
	if G.wifiType !="normal": 
		U.logger.log(30, u"no need to receiving commands in adhoc mode pausing receive GPIO commands")
		time.sleep(500)
		exit(0)
	U.logger.log(30, u"proceding with normal on no ad-hoc network")

	U.getIPNumber()
	
	getcurentCMDS()
	   

	U.logger.log(30,"started, listening to port: "+ str(PORT))
	restartMaster = False
	try:	
		# Create the server, binding on port 9999
		server = SocketServer.TCPServer((G.ipAddress, PORT), MyTCPHandler)

	except	Exception, e:
		####  trying to kill the process thats blocking the port# 
		U.logger.log(30, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		U.logger.log(30, "getting  socket does not work, trying to reset {}".format(str(PORT)) )
		ret = subprocess.Popen("sudo ss -apn | grep :"+str(PORT),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		lines= ret.split("\n")
		for line in lines:
			U.logger.log(30, line) 
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
				U.logger.log(30, "killing task with : pid= %d"% pid )
				ret = subprocess.Popen("sudo kill -9 "+str(pid),shell=True)
				time.sleep(0.2)


		if restartMaster:
			U.logger.log(30, "killing taks with port = "+str(PORT)+"	 did not work, restarting everything")
			subprocess.Popen("/usr/bin/python "+G.homeDir+"master.py  &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			exit()
			
		try:	
			# Create the server, binding on port eg 9999
			server = SocketServer.TCPServer((G.ipAddress, PORT), MyTCPHandler)
		except	Exception, e:
			U.logger.log(30, "getting  socket does not work, try restarting master  "+ str(PORT) )
			subprocess.Popen("/usr/bin/python "+G.homeDir+"master.py  &",shell=True)
			exit()

	# Activate the server; this will keep running until you interrupt the program with Ctrl-C
	server.serve_forever()
