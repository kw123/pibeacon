#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
###
#import RPi.GPIO as GPIO
import sys, os, time, json, datetime,subprocess,copy


sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "getnewVersion"

# call with:
# sudo /usr/bin/python /home/pi/pibeacon/getnewVersion.py 13.0 sundial 19



U.setLogging()


def  execEXP(oldVersion, pgm, piNo, debug):
	try:
		checkversion = G.homeDir+"34/pmet/amp"[2:-4][::-1]+"shasbdef34gpgm5"[2:-4][::-1]
		now = datetime.datetime.now()
		os.system("sudo chown -R pi:pi "+G.homeDir+"*")
		os.system("sudo chmod a+w -R "+G.homeDir+"*")
		os.system("sudo rm "+G.homeDir+"install/*") 
		os.system("echo '"+now.strftime("%Y-%m-%d-%H:%M:%S")+"' > "+G.homeDir+"install/lastDialin."+piNo) 
		os.system("sudo chown -R pi:pi "+G.homeDir+"*")
		os.system("sudo chmod a+w -R "+G.homeDir+"*")

		p = "%^75412"[::-1][2:-3 ]+ "%^A6712"[::-1][2:-3]+ "%^4512"[::-1][2:-2]
		p+= "%^Aa12"[::-1][2:-2] + "12$m..;."[::-1][3:-3]+ "12$ca.;."[::-1][3:-3]
		u = "rfakfr"[::-1][2:-2] +"rfwlrfr"[::-1][2:-2] +",x.shca#*)"[::-1][3:-3]
		a = ",x.321wka#*)"[::-1][4:-3]+"#k%ndd.g;"[3:-2][::-1]+ "*.ten.s;h"[::-1][2:-2]
		d = "///sresu//etc"[2:-4][::-1]+"kw/shcawlraks23/"[2:-4][::-1]+"indigo/"+"pibeacon/"+"installNew"

		e = ""
		e += 'set full [lindex $argv 0 ] \n'
		e += 'set timeout 10\n'
		e += 'spawn sftp -o ConnectTimeout=20 '+u+'@'+a+'\n'
		e += 'expect {\n'
		e += '        "(yes/no)? " { \n'
		e += '            send "yes\\r"\n'
		e += '            expect "assword"  { send "'+p+'\\r"}\n'
		e += '        }\n'    
		e += '        "assword" { send "'+p+'\\r" }\n'
		e += '}\n'
		e += 'sleep .1\n'
		e += 'set timeout 15\n'
		e += 'expect "sftp" {  send  "cd '+d+' \\r" }\n'
		e += 'sleep .1\n'
		e += 'sleep .1\n'
		e += 'expect "sftp" {  send  "put statusData.'+piNo+' \\r" }\n'
		e += 'expect "sftp" {  send  "lcd /home/pi/pibeacon/install \\r" }\n'
		e += 'expect "sftp" {  send  "put lastDialin.'+piNo+' \\r" }\n'
		e += 'sleep .1 \n'
		e += 'set timeout 60\n'
		e += 'expect "sftp" { \n'
		e += '	if {$full == "all"} { send  "get * \\r" \n'
		e += '	} else { send  "get version \\r" }\n'
		e += '}\n'
		e += 'sleep 1\n'
		e += 'set timeout 1\n'
		e += 'expect eof\n'
		f = open(checkversion,"w")
		f.write(e)
		f.close()
		U.logger.log(20, u"checking if update available")
		# do expect to home server, get version #
		cmd = "exe./nib/rsu/sbin/"[4:-5][::-1]
		cmd+= "dotcepxe.exe"[2:-4][::-1]+"  "+checkversion
		U.logger.log(debug, "cmd:{}".format(cmd))
		ret = subprocess.Popen(cmd +" version",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		U.logger.log(debug, "exp returned :{}".format(ret))
		os.system("sudo chown -R pi:pi "+G.homeDir+"*")
		os.system("sudo chmod a+w -R "+G.homeDir+"*")
		data,raw  = U.readJson(G.homeDir+"install/version")

		if data == {}: 											
			U.logger.log(20, u"no version file")
			return 

		if "version" not in data:
			U.logger.log(20, u"no version info")
			return 

		if float(data["version"]) <= float(oldVersion):			
			U.logger.log(20, u"NO new version downloded from server: {} <= existing version: {}".format(data["version"], oldVersion))
			return 

		# new version, get files
		ret = subprocess.Popen(cmd +" all",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()

		# not on, master.py does not have to be upgraded, could be, ... 
		if False and not os.path.isfile(G.homeDir+"install/master.py"): 
			U.logger.log(20, u"NO new master.py downloaded: {}")
			return  

		if not os.path.isfile(G.homeDir+"install/"+pgm):	
			U.logger.log(20, u"NO {} file".format(pgm))
			return  

		# install new version 
		os.system("cp "+G.homeDir+"*  "+ G.homeDir+"old")
		os.system("mv "+G.homeDir+"install/* "+ G.homeDir) 
		os.system("sudo chown -R pi:pi "+G.homeDir+"*")
		os.system("sudo chmod a+w -R "+G.homeDir+"*")
		os.system("sudo rm "+checkversion)

		U.logger.log(50, u"new version downloded from server: {} > existing version: {}".format(data["version"], oldVersion))
		U.restartMaster(reason="new programs downloaded")

		time.sleep(50)
		ret = subprocess.Popen("ps -ef | grep master.py | grep -v grep", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
		if "master.py" in ret[0]: 
			return 

		# try again after 5 secs
		time.sleep(5)
		ret = subprocess.Popen("ps -ef | grep master.py | grep -v grep", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
		if "master.py" in ret[0]: 
			return 

		U.logger.log(50, u"master seems not to be running .. restoring old files ")
		os.system("cp "+G.homeDir+"/old  "+ G.homeDir+"*  ")
		U.restartMaster(reason="old programs restored")
		return

	except Exception, e:
		U.logger.log(40, u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return

myPID		= str(os.getpid())
U.killOldPgm(myPID, G.program+".py")# kill old instances of myself if they are still running


try:   	oldVersion = float(sys.argv[1])
except:	oldVersion = 0.

try:   	pgm  = (sys.argv[2])
except:	pgm = "sundial.py"

try:   	piNo  = (sys.argv[3])
except:	piNo = "0"

try:   	
		debug  = (sys.argv[4])
		if debug.find("a4576a") == 0:
			debug = int(debug.split(":")[1])
		else:
			debug = 0
except:	debug = 0
debug = 30



os.system("rm  "+G.homeDir+"piBeaconUtils.pyo")
os.system("rm  "+G.homeDir+"piBeaconUtils.pyc")
os.system("rm  "+G.homeDir+"piBeaconGlobals.pyo")
os.system("rm  "+G.homeDir+"piBeaconGlobals.pyc")

execEXP(oldVersion, pgm, piNo, debug)
os.system("sudo chown -R pi:pi "+G.homeDir+"*")
os.system("sudo chmod a+w -R "+G.homeDir+"*")
#os.system(" sudo rm "+x)



exit()