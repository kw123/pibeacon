#! /usr/bin/env python
# -*- coding: utf-8 -*-
# karl wachs oct/12, 2017
# use at your own risk
#  v 1.0
# change log
#
#
#
#
 
import sys, os, subprocess
import time
import datetime 
import json
import math
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as patches
import logging
import logging.handlers
global logging, logger
import copy



#
#################################
#################################
   

####### main pgm / loop ############




tStart			  = time.time()

DPI = 300

pluginDir		= sys.argv[0].split("makeRdlidarPlot.py")[0]
indigoDir		= pluginDir.split("Plugins/")[0]
imageParams 	= json.loads(sys.argv[1])
logfileName		= imageParams["logFile"]



logLevel		  = imageParams["logLevel"] in ["2","3"]
logging.basicConfig(level=logging.DEBUG, filename= logfileName,format='%(module)-23s L:%(lineno)3d Lv:%(levelno)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)
if  not logLevel:
	logger.setLevel(logging.ERROR)
else:
	logger.setLevel(logging.DEBUG)





color ={"current":"#FF0000","calibrated":"#00FF00","last":"#0000FF","background":"#5A5A5A"}
	


imageOutfile	  		= imageParams["fileName"] 

imageDir = logfileName[0:imageOutfile.rfind('/')]
if not os.path.exists(imageDir):
	os.mkdir(imageDir)


try: 	anglesInOneBin	= int(imageParams["anglesInOneBin"])
except: anglesInOneBin	= 1

try: 	DPI				= int(imageParams["DPI"])
except: DPI			 	= 400

try: 	numberOfDotsX	= int(imageParams["numberOfDotsX"])
except: numberOfDotsX 	= 4000

try: 	numberOfDotsY	= int(imageParams["numberOfDotsY"])
except: numberOfDotsY 	= 4000

try: 	compress		= imageParams["compress"]	 =="1"
except:	compress		= Flase
try:	yOffset 		= int(imageParams["yOffset"])
except: yOffset 		= 0

try:	xOffset 		= int(imageParams["xOffset"])
except: xOffset 		= 0

try:	scalefactor 	= float (imageParams["scalefactor"])
except: scalefactor 	= 1.

try:	phiOffset 		= float (imageParams["phiOffset"])
except: phiOffset 		= 0.


try: 	color["current"] = imageParams["colorCurrent"]
except: color["current"] = "red"

try: 	color["calibrated"]   = imageParams["colorCalibrated"]
except: color["calibrated"]	 = "green"

try: 	color["last"]	= imageParams["colorLast"]
except: color["last"]	= "blue"

try: 	xMin 			= float(imageParams["xMin"])
except: xMin 			= 0

try: 	xMax 			= float(imageParams["xMax"])
except: xMax 			= 0

try: 	yMin 			= float(imageParams["yMin"])
except: yMin 			= 0

try: 	yMax 			= float(imageParams["yMax"])
except: yMax			= 0

try: 	frameON 		= imageParams["frameON"] == "1"
except: frameON 		= True

try: 	frameTight 		= imageParams["frameTight"] == "1"
except: frameTight		= False

try: 	showLegend 		= imageParams["showLegend"]
except: showLegend 		= ""

try: 	showPhi0 		= imageParams["showPhi0"] == "1"
except: showPhi0 		= False

try: 	topText 		= imageParams["topText"]
except: topText 		= ""

try: 	showTriggerValues = imageParams["showTriggerValues"]
except: showTriggerValues = ""

try: 	fontSize 		= int(imageParams["fontSize"])
except: fontSize 		= 20


try: 	showTimeStamp 	= imageParams["showTimeStamp"]
except: showTimeStamp 	= ""

try: 	showZeroDot 	= imageParams["showZeroDot"] == "1"
except: showZeroDot 	= True


try: 	showZeroValues 	= imageParams["showZeroValues"] == "1"
except: showZeroValues 	= False

try: 	showDoNotTrigger 	= imageParams["showDoNotTrigger"] == "1"
except: showDoNotTrigger 	= True

try: 	
	doNotUseDataRanges = []
	doNotUseDataRangesShow 	= imageParams["doNotUseDataRanges"]
	if len(doNotUseDataRangesShow) > 2:
		ddd = doNotUseDataRangesShow.split(";")
		for dd in ddd: 
			if len(dd) > 2 and "-" in dd:
				d = dd.split("-")
				doNotUseDataRanges.append([int(d[0]),int(d[1])])
				#logger.log(20,u"dd {} d {} doNotUseDataRanges:{}".format(dd, d, doNotUseDataRanges)  )
		
except: doNotUseDataRanges 	= []

try: 	dataFile 	= imageParams["dataFile"] 
except: dataFile 	= "/tmp/makerdlidar.dat"

try:
	f = open(dataFile,"r")
	data = json.loads(f.read())
	f.close()
except  Exception, e:
	logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e)  )
	exit()
#

try:
	# print start to logfile 
	logger.log(20,"========= start @ {}  =========== ".format(datetime.datetime.now()) )
	tStart= time.time()

	logger.log(20,"pluginDir          :{}".format(pluginDir) )
	logger.log(20,"indigoDir          :{}".format(indigoDir) )
	logger.log(20,"imageOutfile       :{}".format(imageOutfile) )
	logger.log(20,"compressImage      :{}".format(compress) )
	logger.log(20,"dataInFile         :{}".format(imageParams["dataFile"]) )
	logger.log(20,"x from to          :{} / {}".format(xMin,xMax) )
	logger.log(20,"offset x,y         :{} / {}".format(xOffset, yOffset) )
	logger.log(20,"numberOfDotsX,Y    :{} / {}".format(numberOfDotsX, numberOfDotsY) )
	logger.log(20,"anglesInOneBin     :{}".format(anglesInOneBin) )
	logger.log(20,"DPI                :{}".format(DPI) )
	logger.log(20,"scalefactor        :{}".format(scalefactor) )
	logger.log(20,"phiOffset          :{}".format(phiOffset) )
	logger.log(20,"frameTight         :{}".format(frameTight) )
	logger.log(20,"frameON            :{}".format(frameON) )
	logger.log(20,"showPhi0           :{}".format(showPhi0) )
	logger.log(20,"showLegend         :{}".format(showLegend) )
	logger.log(20,"showTimeStamp      :{}".format(showTimeStamp) )
	logger.log(20,"showZeroDot        :{}".format(showZeroDot) )
	logger.log(20,"showZeroValues     :{}".format(showZeroValues) )
	logger.log(20,"showDoNotTrigger   :{}".format(showDoNotTrigger) )
	logger.log(20,"showTriggerValues  :{}".format(showTriggerValues) )
	logger.log(20,"topText            :{}".format(topText) )
	logger.log(20,"fontSize           :{}".format(fontSize) )
	logger.log(20,"colorCurrent       :{}".format(color["current"]) )
	logger.log(20,"colorCalibrated    :{}".format(color["calibrated"]) )
	logger.log(20,"colorprevious      :{}".format(color["last"]) )
	logger.log(20,"colorBackground    :{}".format(color["background"]) )



#### prep data ######################

	#phiOffset = 0
	dataToPlot = {"dots":{"current":[[],[],[]],"calibrated":[[],[],[]],"last":[[],[],[]]},"doNotTrigger":[[],[]], "trigger":{"current":{"LT":[],"GT":[]},"calibrated":{"LT":[],"GT":[]}},"xy0":[],"zero":[],"time":[]}

	useBins = 360 / anglesInOneBin
	bins = [[math.cos( -float(ii*anglesInOneBin+phiOffset)*(3.141/180.) ), math.sin(-float(ii*anglesInOneBin+phiOffset)*(3.141/180.) ) ] for ii in range(useBins)]
	phiOff = [math.cos( -float(+phiOffset)*(3.141/180.) ), math.sin( -float(+phiOffset)*(3.141/180.) ) ]
	
	dotSize = {"current":int( numberOfDotsX*(20./1000.) ) ,"calibrated":int( numberOfDotsX*(10./1000.) ),"last":int( numberOfDotsX*(10./1000.) )}


	for kk in ["current","calibrated","last"]:
		dd = data[kk]
		for ii in range(len(dd)):
			try:	
				value = float(dd[ii])
				if value == 0 and not showZeroValues: continue
				dataToPlot["dots"][kk][0].append( int( scalefactor*(bins[ii][0]*value+xOffset) ) )	
				dataToPlot["dots"][kk][1].append( int( scalefactor*(bins[ii][1]*value+yOffset) ) )	
				dataToPlot["dots"][kk][2].append( dotSize[kk] )	
			except Exception, e:
				logger.log(20,"Line {} has error={}, ii: {}; kk:{}".format(sys.exc_traceback.tb_lineno, e, ii, kk))
				break

	
	for kk in doNotUseDataRanges:
			try:	
				dataToPlot["doNotTrigger"][0].append( int( scalefactor*(xOffset) ) )	
				dataToPlot["doNotTrigger"][1].append( int( scalefactor*(yOffset) ) )	
				ii  = kk[0]
				ii2 = kk[1]
				value = (float(data["calibrated"][ii]) + float(data["calibrated"][ii2]))/4
				dataToPlot["doNotTrigger"][0].append( int( scalefactor*(bins[ii][0]*value+xOffset) ) )	
				dataToPlot["doNotTrigger"][1].append( int( scalefactor*(bins[ii][1]*value+yOffset) ) )	
				dataToPlot["doNotTrigger"][0].append( int( scalefactor*(bins[ii2][0]*value+xOffset) ) )	
				dataToPlot["doNotTrigger"][1].append( int( scalefactor*(bins[ii2][1]*value+yOffset) ) )	
				dataToPlot["doNotTrigger"][0].append( int( scalefactor*(xOffset) ) )	
				dataToPlot["doNotTrigger"][1].append( int( scalefactor*(yOffset) ) )	
			except Exception, e:
				logger.log(20,"Line {} has error={}, ii: {}; kk:{}".format(sys.exc_traceback.tb_lineno, e, ii, kk))
				break
	logger.log(30,"doNotTrigger:{},  {}".format(doNotUseDataRanges, dataToPlot["doNotTrigger"]) )

	for kk in ["current","calibrated"]:
		dd = data[kk]
		for LTGT in["LT","GT"]:
			tr = data["triggerValues"][kk][LTGT]["sections"]
			for ii in range(len(tr)):
				try:	
					ll1 = tr[ii]["bins"][0]
					ll2 = tr[ii]["bins"][1]
					if ll1 >= ll2 : continue
					dataToPlot["trigger"][kk][LTGT].append( [[],[]] )	
					for jj in range(ll1,ll2+1):
						value = float(dd[jj])
						if value == 0: continue
						dataToPlot["trigger"][kk][LTGT][-1][0].append( int( scalefactor*(bins[jj][0]*value+xOffset) ) )	
						dataToPlot["trigger"][kk][LTGT][-1][1].append( int( scalefactor*(bins[jj][1]*value+yOffset) ) )	
				except Exception, e:
					logger.log(20,"Line {} has error={}, ii: {}; tr:{}".format(sys.exc_traceback.tb_lineno, e, ii, tr))
					break
		#logger.log(20,"kk {}; pld:{}".format(kk, dataToPlot["trigger"][kk]))

	dataToPlot["xy0"] = [ [ scalefactor*xOffset,scalefactor*(numberOfDotsX/3*phiOff[0] + xOffset) ], [ scalefactor*yOffset,scalefactor*(numberOfDotsX/3*phiOff[1] + yOffset) ]]
	dataToPlot["zero"] =  [ scalefactor*xOffset,scalefactor*yOffset]
	dataToPlot["time"] =  [ scalefactor*xOffset,scalefactor*yOffset]
#### prep data ###################### END





#### fill plot  ######################

	logger.log(20,"time used {:4.2f} --   setup fig, ax".format((time.time()-tStart)) )
	plt.figure()
	fig = plt.gcf()
	#mpl.rcParams['savefig.pad_inches'] = 0
	#plt.autoscale(tight=True)

	plt.box(frameON) 

	plt.rcParams['axes.facecolor'] 		= color["background"]
	plt.rcParams['savefig.facecolor'] 	= color["background"]

	plt.rcParams['font.size'] =  fontSize

	ax = fig.add_axes([0,0,1,1])
	# for differnt versions 
	try: 	ax.set_facecolor(color["background"]) # 3.x
	except: ax.set_axis_bgcolor(color["background"]) #2.x


	if xMax !=0. and yMax !=0:
		ax.set_xlim(yMin, yMax) 
		ax.set_ylim(xMin, xMax) 

	if not frameON: 	
		plt.axis('off')

	if len(topText) > 0: 
		plt.title(topText)

	#DPI = fig.get_dpi()
	fig.set_size_inches(int(numberOfDotsX/float(DPI)),int(numberOfDotsY/float(DPI)))	

  
	logger.log(20,"time used {:4.2f} --   now loop though the dots and add them".format((time.time()-tStart)) )

	DotsAt4000Point = 25
	normDot 		= max(4,int( (DotsAt4000Point*numberOfDotsX) /4000. ))
	sizeDots 		= {"current":normDot,				"calibrated":max(1,int(normDot*0.6)),	"last":max(1,int(normDot*.4)), "phi0":max(1,int(normDot*.07)), "zero":max(1,int(normDot))}
	labelsDots		= {"current":"current",				"calibrated":"Calibrated room",	"last":"previous"}
	linewidthTR		= {"current":max(2,int(normDot)),	"calibrated":max(2,int(normDot)), "notTrigger":max(1,int(normDot*.08)) }
	LTGTstyle		= {"LT":"<",		"GT":">"}
	LTGTlabel		= {"LT":"Closer",	"GT":"Further"}

	for kk in ["current","calibrated","last"]:
		if color[kk] !="#000000": 
			ax.plot(dataToPlot["dots"][kk][0], dataToPlot["dots"][kk][1], '-', color=color[kk], linewidth=int(max(1,sizeDots[kk]/3)), label=labelsDots[kk])
			#ax.plot(dataToPlot["dots"][kk][0], dataToPlot["dots"][kk][1], 'o', color=color[kk], markersize=sizeDots[kk], label=labelsDots[kk])

	show = {"LT":True,"GT":True}
	for kk in ["current","calibrated"]:
		for LTGT in ["LT","GT"]:
			for dd in dataToPlot["trigger"][kk][LTGT]:
				if len(dd) >0:
					if show[LTGT]: 
						ax.plot(dd[0], dd[1], LTGTstyle[LTGT], color=color[kk],  markersize=linewidthTR[kk],label=LTGTlabel[LTGT]) 
						show[LTGT] = False
					else:
						ax.plot(dd[0], dd[1], LTGTstyle[LTGT], color=color[kk],  markersize=linewidthTR[kk]) 

	if showZeroDot:# zero dot 
		ax.plot(dataToPlot["zero"][0], dataToPlot["zero"][1],'o', color='black',linewidth=sizeDots["zero"])

	if showPhi0:
		ax.plot(dataToPlot["xy0"][0], dataToPlot["xy0"][1], color='black',linewidth=sizeDots["phi0"], label="phi=0")


	if showDoNotTrigger:
		ax.plot(dataToPlot["doNotTrigger"][0], dataToPlot["doNotTrigger"][1], color='grey',linewidth=linewidthTR["notTrigger"], label="notTrigger")

	if showTimeStamp !="":
		try:
				yOutside = 1.02
				yInside  = 0.98
				xLeft    = 0.01
				xCenter  = 0.49
				xRight   = 0.95

				if	  showTimeStamp =="top center inside":	pos =[xCenter,yInside]
				elif  showTimeStamp =="top center outside":	pos =[xCenter,yOutside]
				elif  showTimeStamp =="top right inside":	pos =[xRight,yInside]
				elif  showTimeStamp =="top right outside":	pos =[xRight,yOutside]
				elif  showTimeStamp =="top left outside":	pos =[xRight,yOutside]
				elif  showTimeStamp =="top left outside":	pos =[xLeft,yOutside]
				else:										pos =[xLeft,yInside]
				dd = datetime.datetime.fromtimestamp(data["timestamp"]).strftime("%H:%M:%S")
				ax.text(pos[0], pos[1], dd,  horizontalalignment='left',  verticalalignment='top',   transform=ax.transAxes)
		except: pass

	if showTriggerValues !="":
		try:
				yOutside = 1.02
				yInside  = 0.96
				xLeft    = 0.01
				xCenter  = 0.49
				xRight   = 0.96

				if	  showTriggerValues =="top center inside":	pos =[xCenter,yInside]
				elif  showTriggerValues =="top center outside":	pos =[xCenter,yOutside]
				elif  showTriggerValues =="top right inside":	pos =[xRight,yInside]
				elif  showTriggerValues =="top right outside":	pos =[xRight,yOutside]
				elif  showTriggerValues =="top left outside":	pos =[xRight,yOutside]
				elif  showTriggerValues =="top left outside":	pos =[xLeft,yOutside]
				else:											pos =[xLeft,yInside]
				## make a nice looking sjon dumps for the trigger info, combine list to one line and remove empty structures 
				out = copy.deepcopy(data["triggerValues"])
				for kk in ["current","calibrated"]:
					dd = data["triggerValues"][kk]
					for LTGT in["LT","GT"]:
						ltr= len(tr)
						tr = data["triggerValues"][kk][LTGT]["sections"]
						ltr= len(tr)
						if ltr ==0: 
							out[kk][LTGT]={}
						else:
							for ii in range(ltr):
								out[kk][LTGT]["sections"][ii]["bins"] = unicode(data["triggerValues"][kk][LTGT]["sections"][ii]["bins"])
				out["off-x/y/phi"] = "{:.0f}/{:.0f}/{:.0f}".format(xOffset, yOffset,phiOffset)
				out["doNotUse"] = "{}".format(doNotUseDataRangesShow)
				#del out["doNotUseDataRanges"]
				dd = json.dumps(out,sort_keys=True, indent=2)
				ax.text(pos[0], pos[1], dd,  horizontalalignment='left',  verticalalignment='top',   transform=ax.transAxes)
		except  Exception, e:
			logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e) )


	if showLegend !="":
		plt.legend(fontsize = fontSize, loc=showLegend)
#### fill plot  ###################### END


#### make plotfile  ###################### 
	logger.log(20,"time used {:4.2f} --   filling the plot:".format((time.time()-tStart)))
	try: 	
			if frameTight : plt.savefig((imageOutfile).encode('utf8'), bbox_inches='tight')
			else: 			plt.savefig((imageOutfile).encode('utf8'))
	except  Exception, e:
			logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e) )

	try:	pngSize = os.path.getsize((imageOutfile).encode('utf8'))/1024.
	except: pngSize = 0
#### make plotfile  ###################### END



	
#### compress plotfile  ###################### 
	if compress:
		try:
			xxxFileName = imageOutfile.replace(".png","")+".xxx"
			if os.path.isfile((xxxFileName).encode('utf8')): os.remove((xxxFileName).encode('utf8'))
			logger.log(20,"time used {:4.2f} --   compressing the png file ".format((time.time()-tStart)))
			cmd = "'"+pluginDir+"pngquant' --force --ext .xxx '"+imageOutfile+"'"
			ppp = subprocess.Popen(cmd.encode('utf8'),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  ## creates a file with .xxx, wait for completion
			try:	compSize = os.path.getsize((xxxFileName).encode('utf8'))/1024.
			except: compSize = 0
			try: os.rename((xxxFileName).encode('utf8'),(imageOutfile).encode('utf8') )
			except: pass
			logger.log(20,"time used {:4.2f} --   file sizes: original file: {:5.1f};  compressed file: {:5.1f}[KB]".format((time.time()-tStart), pngSize,compSize) )
		except  Exception, e:
			logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e)  )
#### compress plotfile  ###################### END



	logger.log(20,"time used {:4.2f} --   end  @ {}".format((time.time()-tStart), datetime.datetime.now())  )

except  Exception, e:
	logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e))

sys.exit(0)
