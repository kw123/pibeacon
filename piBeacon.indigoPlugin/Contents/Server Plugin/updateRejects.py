#

import sys, os, subprocess
import time
import datetime
import json
import logging
import logging.handlers
global logging, logger
  

####### main pgm / loop ############
#################################
def readRejects():
	global dataDir, rejectsIn, rejectExisting, nFiles, nExistingMacs
	rejectsIn=[]
	for pi in range(11):
		pis=str(pi)
		file=""
		if  os.path.isfile(dataDir+"rejects."+pis): 
			file=dataDir+"rejects."+pis
			nFiles +=1
		
			f=open(file,"r")
			for line in f.readlines():
				os.system("echo "+line+" >> "+homeDir+"rejected/rejects.in" )
				line=line.strip("\n")
				if len(line) < 30: continue
				if len(line) > 500: continue
				lll=line.split(";")
				if len(lll) != 4: continue
				try: 
					float(lll[0])
				except:
					pass   
				rejectsIn.append(pis+";"+line)
			f.close()
			try:	os.remove(dataDir+"rejected/rejects."+pis)
			except: pass
			try:	os.remove(dataDir+"rejects."+pis)
			except: pass
		
	try:
		rejectExisting={}
		nExistingMacs=""
		if  os.path.isfile(dataDir+"rejectedByPi.json"): 
			file=dataDir+"rejectedByPi.json"
			f=open(file,"r")
			rejectExisting= json.loads(f.read())
			f.close()
			nExistingMacs = len(rejectExisting)
	except:
		logger.log(20,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		pass
	
#################################
def writeRejects():
	global homeDir, rejectsIn, rejectExisting, nRejects
	
	for r in rejectsIn:
		r=r.replace(" ","")
		## pi#;9637500; UUID; ff4c000c0e00b60bbd8008f77d53-28183-15529;  71:21:38:7D:33:DA
		#print r
		logger.log(20,Macs: " +r)
		items   = r.split(";")
		rPi	 = items[0]
		try:
			items[1]=float(items[1])
			timeSt  = time.strftime('%Y-%m-%d %H:%M:%S',  time.localtime(items[1]))
		except  Exception, e:
			logger.log(20,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
			logger.log(20,items[1])
			#exit()
		reason  = items[2]
		uuid	= items[3]
		mac	 = items[4]
		
		if mac not in  rejectExisting:
			 rejectExisting[mac]={"uuid":uuid,"first":timeSt,"last":timeSt,"reason":reason,"count":1,"rPi":rPi}
			 #print "adding "+ mac
		else: 
			try:
				if  rejectExisting[mac]["last"] < timeSt:
					rejectExisting[mac]["last"]=timeSt
				if  rejectExisting[mac]["first"] > timeSt:
					rejectExisting[mac]["first"]=timeSt
				if ","+rPi not in  rejectExisting[mac]["rPi"] and rejectExisting[mac]["rPi"].find(rPi) != 0:  
					rejectExisting[mac]["rPi"]+=","+rPi
				rejectExisting[mac]["rPi"] = rejectExisting[mac]["rPi"].strip(",")
				rejectExisting[mac]["count"]+=1
			except  Exception, e:
				logger.log(20,"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))

	
	#print  rejectExisting   
	out0=[]
	lastDate = []
	n=0

	for mac in rejectExisting:
		try:
			lastDate.append([rejectExisting[mac]["last"],n])
			n+=1
			out ='\n"'+mac+'":{'
			out+= ('"uuid":"'   +rejectExisting[mac]["uuid"]+'"').ljust(54)
			out+= ',"first":"'  +rejectExisting[mac]["first"]+'"'
			out+= ',"last":"'   +rejectExisting[mac]["last"]+'"'
			out+= (',"count":'  +str(rejectExisting[mac]["count"])).ljust(20)
			out+=  ',"reason":"'+(rejectExisting[mac]["reason"]+'"').ljust(8)
			out+= ',"rPi":"'	+rejectExisting[mac]["rPi"]+'"'
			out+=  '},'
			out0.append(out)
			logger.log(20,"\n"+out)
		except: 
			logger.log(20,"error for "+ mac)
			logger.log(20,(unicode(rejectExisting[mac]))
	lastDate.sort()	 
	nRejects = len(out0)
	out1=[]
	#print lastDate
	for ii in range(len(lastDate)):
		out1.append(out0[lastDate[ii][1]])
		logger.log(20,+"{} {}".format(lastDate[ii], out0[lastDate[ii][1]]) )
	
	if nRejects>0:
		logger.log(20,nunber of macs rejected: %d"%nRejects) 
		out1[n-1]=out1[n-1].strip(",")
		f=open(dataDir+"rejectedByPi.json","w")
		f.write("{")
		for line in out1:
			f.write(line)	   
		f.write("\n}")
		f.close()
	

	

####### main pgm / loop ############
global dataDir, rejectsIn, rejectExisting
global logfileName, logLevel, printON, nRejects, nFiles, nExistingMacs

printON 		= False
nRejects 		= 0
nFiles 			= 0
nExistingMacs 	= 0

pluginDir		= sys.argv[0].split("updateRejects.py")[0]
indigoDir		= pluginDir.split("Plugins/")[0]
dataDir 		= indigoDir+"Preferences/Plugins/com.karlwachs.piBeacon/rejected/"
logfileName 	= indigoDir+"Logs/com.karlwachs.piBeacon/plugin.log"
### logfile setup
try: logLevel = sys.argv[1] == "1"
except: logLevel = False

logging.basicConfig(level=logging.DEBUG, filename= logfileName,format='%(module)-23s L:%(lineno)3d Lv:%(levelno)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)
#
if not logLevel:
	logger.setLevel(logging.ERROR)
else:
	logger.setLevel(logging.DEBUG)


	
logger.log(20,"========= start    @ {}  =========== ".format(datetime.datetime.now() )
readRejects()
writeRejects()

logger.log(20,"========= finished @ {}; read {} files from RPIs ;  MACs in reject list before {},  after: {}"format(datetime.datetime.now(), nFiles, nExistingMacs, nRejects) )
sys.exit(0)		
