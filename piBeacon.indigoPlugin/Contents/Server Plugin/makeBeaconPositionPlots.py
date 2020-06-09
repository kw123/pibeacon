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
import random
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import logging
import logging.handlers
global logging, logger
_defaultDateStampFormat				= u"%Y-%m-%d %H:%M:%S"



#
#################################
#################################
   

####### main pgm / loop ############



pluginDir		  = sys.argv[0].split("makeBeaconPositionPlots.py")[0]
indigoDir		  = pluginDir.split("Plugins/")[0]

piPositionsDir  = sys.argv[1]

f=open(piPositionsDir+"positions.json")
plotData = json.loads(f.read())
f.close()

### logfile setup
logLevel = plotData["logLevel"]
logfileName=plotData["logFile"]
#logLevel = True

logging.basicConfig(level=logging.DEBUG, filename= logfileName,format='%(module)-23s L:%(lineno)3d Lv:%(levelno)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)
#
if not logLevel:
	logger.setLevel(logging.ERROR)
else:
	logger.setLevel(logging.DEBUG)

try:
	# print start to logfile 
	logger.log(20,"========= start @ {}  =========== ".format(datetime.datetime.now()) )
	tStart= time.time()

	distanceUnits			= max(0.0254, float(plotData["distanceUnits"]))

	Yscale					= float(plotData["Yscale"])
	Xscale					= float(plotData["Xscale"])

	defaultLabelTextSize 	= 12
	try: 	labelTextSize	= int(plotData["labelTextSize"])
	except: labelTextSize	= defaultLabelTextSize
	labelFactor 			= float(labelTextSize)	   / defaultLabelTextSize

	defaultTitleTextSize 	= 18
	try: 	titleTextSize	= int(plotData["titleTextSize"])
	except: titleTextSize	= defaultTitleTextSize
	titleFactor 			= float(titleTextSize)	   / defaultTitleTextSize

	defaultCaptionTextSize  = 12
	try: captionTextSize	= int(plotData["captionTextSize"])
	except: captionTextSize	= defaultCaptionTextSize
	captionFactor 			= float(captionTextSize) / defaultCaptionTextSize

	try: showTimeStamp		= plotData["showTimeStamp"]
	except: showTimeStamp	= True

	SymbolSize  = 1.0
	try: SymbolSize			= float(plotData["SymbolSize"])
	except: pass

	LargeCircleSize  = 1.0
	try: LargeCircleSize	= float(plotData["LargeCircleSize"])
	except: pass

	textPosLargeCircle  	= "atCircle"
	try: textPosLargeCircle	= plotData["textPosLargeCircle"]
	except: pass



	dotsY					= int(plotData["dotsY"])
	dotsX					= dotsY *( Xscale/Yscale) 
	hatches 				= ["","//","\\","+"]
	Zlevels					= plotData["Zlevels"].split(",")
	nZlevels 				= min(len(Zlevels),4)
	for i in range(nZlevels):
		Zlevels[i] 			= int(Zlevels[i])
	
	randomBeacons  = 0
	try: randomBeacons	= int(plotData["randomBeacons"])
	except: pass


	logger.log(20,"imageYscale        :{}".format(Yscale) )
	logger.log(20,"imageXscale        :{}".format(Xscale) )
	logger.log(20,"imageDotsY         :{}".format(dotsY) )
	logger.log(20,"SymbolSize         :{}".format(SymbolSize) )
	logger.log(20,"textPosLargeCircle :{}".format(textPosLargeCircle) )
	logger.log(20,"LargeCircleSize    :{}".format(LargeCircleSize) )
	logger.log(20,"captionTextSize    :{}".format(captionTextSize) )
	logger.log(20,"labelTextSize      :{}".format(labelTextSize) )
	logger.log(20,"titleTextSize      :{}".format(titleTextSize) )
	logger.log(20,"titleText          :{}".format(plotData["titleText"]) )
	logger.log(20,"titleTextColor     :{}".format(plotData["titleTextColor"]) )
	logger.log(20,"titleTextPos       :{}".format(plotData["titleTextPos"]) )
	logger.log(20,"titleTextRotation  :{}".format(plotData["titleTextRotation"]) )
	logger.log(20,"showTimeStamp      :{}".format(showTimeStamp) )

	logger.log(20,"randomBeacons      :{}".format(randomBeacons) )
	logger.log(20,"distanceUnits      :{}".format(distanceUnits) )
	logger.log(20,"imageOutfile       :{}".format(plotData["Outfile"]) )
	logger.log(20,"compressImage      :{}".format(plotData["compress"]) )
	logger.log(20,"Zlevels            :{}".format(Zlevels) )



	textDeltaYLabel 	= 5. * (Yscale / dotsY) * labelFactor  # move 4 points 
	textDeltaXLabel 	= 6. * (Xscale / dotsX) * labelFactor

	textDeltaXCaption 	= 6. * (Xscale / dotsX) * captionFactor  # move xx oints
	textDeltaYCaption 	= 5. * (Yscale / dotsY) * captionFactor  # move yy points

	logger.log(20,"label delta X     :{}".format(textDeltaXLabel) )
	logger.log(20,"label delta Y     :{}".format(textDeltaYLabel) )
	logger.log(20,"capt delta X      :{}".format(textDeltaXCaption) )
	logger.log(20,"capt delta Y      :{}".format(textDeltaYCaption) )



	imageOutfile			= plotData["Outfile"]
	if imageOutfile =="":
		imageOutfile = piPositionsDir+"beaconPositions.png"


	TransparentBackground = "0.0"

	logger.log(20,"beacon data:")
	for mac in plotData["mac"]:
		logger.log(20,mac+"  {}".format(plotData["mac"][mac]) )



	#
	logger.log(20,"time used {:4.2f} --   setup fig, ax".format((time.time()-tStart)) )
	if labelTextSize !="": plt.rcParams.update({'font.size': int(labelTextSize)})
	plt.figure()
	fig = plt.gcf()
	ax = fig.add_axes([0, 0, 1, 1], frameon=False)

	ax.set_ylim( 0.,Yscale )
	ax.set_xlim( 0.,Xscale )

	# set # of pixels 
	DPI = fig.get_dpi()
	fig.set_size_inches(dotsX/float(DPI),dotsY/float(DPI))	
	#plt.tight_layout()

	# dont show anything
	plt.axis('off')
	#ax.set_axis_off()

	#  
	backgroundFile		  = "background.png"
	ok = False	
	if os.path.isfile((piPositionsDir+backgroundFile).encode('utf8')):
		backGFile = piPositionsDir+backgroundFile
		ok = True
	else:
		ff = imageOutfile.rfind("/")
		p = imageOutfile[:ff+1]
		if os.path.isfile((p+"background.png").encode('utf8')):
			backGFile = p+"background.png"
			ok = True
	if ok: 
		logger.log(20,"time used {:4.2f} --   loading background image file: '{}'".format( (time.time()-tStart),backGFile ) )
		img = plt.imread(backGFile)
		ax.imshow(img, extent=[0., Xscale, 0., Yscale])
	else:
		logger.log(20,"time used     --   background image file not loaded, not found --  background.png  not in {} and not in {}".format(imageOutfile, piPositionsDir) )

	  


	# 
	titleText				= plotData["titleText"]
	if titleText != "": 
		logger.log(20,"time used {:4.2f} --   adding  text".format((time.time()-tStart)) )
		titleTextColor		= plotData["titleTextColor"]
		titleTextPos		= plotData["titleTextPos"].split(",")
		titleTextPos		= [float(titleTextPos[0]),float(titleTextPos[1])]
		titleTextRotation	= int(plotData["titleTextRotation"])
		ax.text(titleTextPos[0],titleTextPos[1],titleText, color=titleTextColor ,size=titleTextSize, rotation=titleTextRotation,clip_on=True)




	piColor = "#00FF00"
  
	logger.log(20,"time used {:4.2f} --   now loop though the beacons and add them".format((time.time()-tStart)) )
	for mac in plotData["mac"]: # get the next beacon
		try:
				this  = plotData["mac"][mac]
				pos   = this["position"]
				try: 	alpha = float(this["symbolAlpha"])
				except:	alpha = 0.5

				if len(pos) !=3: pos= [5,5,5]
				
				randx = 0
				randy = 0
				if this["bType"] != "RPI" and randomBeacons!=0:
					randx =  1.+ 0.01 * (random.randint(0,randomBeacons) - randomBeacons/2.)
					randy =  1.+ 0.01 * (random.randint(0,randomBeacons) - randomBeacons/2.)
					pos[0] *= randx
					pos[1] *= randy
				pos[0] = max(0., min(pos[0], Xscale ))
				pos[1] = max(0., min(pos[1], Yscale ))

				# show the marker
				try:	 distanceToRPI = this["distanceToRPI"] * 0.25
				except:  distanceToRPI  = 1. / distanceUnits
													     #1.7 meter= 6"         0.25 m = 1'
				distanceToRPI = max( min( distanceToRPI, 1.7/distanceUnits ), 0.25/distanceUnits) 
			
				symbol = this["symbolType"].lower()
				edgecolor = this["symbolColor"]
				if len(edgecolor)  != 7: edgecolor ="#0F0FF0"
				color = this["symbolColor"]
				if len(color)  != 7: color ="#0FF00F"
				LargeCircle = False
				if symbol !="text":
					if	  symbol == "dot":
						distanceToRPI  = 0.1 / distanceUnits * SymbolSize
						Dtype = "circle"
	
					elif	symbol =="smallcircle":
						Dtype = "circle"
						distanceToRPI  = 0.4 / distanceUnits * SymbolSize

					elif	symbol =="largecircle":
						LargeCircle = True
						Dtype = "circle"
						distanceToRPI  = max(1, math.sqrt(distanceToRPI*distanceUnits)/distanceUnits) * LargeCircleSize

					elif	symbol =="square": # mostly for RPI
						Dtype = "square"
						distanceToRPI  = 0.35 / distanceUnits * SymbolSize

					elif	symbol =="square45":
						Dtype = "square45"
						distanceToRPI  = 0.5 / distanceUnits * SymbolSize

					else:
						Dtype =""
			
					hatch=""
					for ii in range(nZlevels):
						if int(pos[2]) == Zlevels[ii]:
							hatch = hatches[ii]
							break

					if this["status"] == u"up":
						edgecolor= "#000000"
				
					logger.log(20,"{}  {} color:{} edgecolor:{} type:{} symbol:{} type:{} distanceToRPI:{:5.1f}  hatch:{}  status:{}, random:{:.3f},{:.3f}, pos:{}".format(this["name"].ljust(26) , this["nickName"].ljust(6), color.ljust(7), edgecolor.ljust(7), this["bType"][:3], symbol.ljust(11), Dtype.ljust(8), distanceToRPI, hatch.ljust(2),this["status"],randx,randy,pos) )

					if   Dtype == "circle":
							circle = plt.Circle([pos[0],pos[1]], distanceToRPI, fc=color, ec=edgecolor,alpha=alpha,hatch=hatch)
							ax.add_patch(circle)
					elif Dtype == "square":
							piColor=color
							square = patches.Rectangle((pos[0]- distanceToRPI/2., pos[1]- distanceToRPI/2.), distanceToRPI, distanceToRPI,fc=color, ec=edgecolor,alpha=alpha,hatch=hatch)
							ax.add_patch(square)
					elif Dtype == "square45":
							piColor=color
							square = patches.Rectangle((pos[0]- distanceToRPI/2., pos[1]- distanceToRPI/2.), distanceToRPI, distanceToRPI,angle=45.,fc=color, ec=edgecolor,alpha=alpha,hatch=hatch)
							ax.add_patch(square)
			
				# show the label next to the marker
				if this["nickName"] !="":
					dx = textDeltaXLabel*1.5
					if LargeCircle  == "atRadius" and textPosLargeCircle:
						dx =  distanceToRPI + textDeltaXLabel*.3 
					if symbol == "text": 
						ax.text(pos[0] ,pos[1] ,this["nickName"], color=this["textColor"] ,size="x-small")
						logger.log(20,"{}  {} color:{}   --text only--   status:{}".format(this["name"].ljust(26), this["nickName"].ljust(6), color.ljust(7), this["status"]) )
					else:
						if pos[0] + dx > Xscale:
							dx = - textDeltaXLabel*2
						ax.text(pos[0] + dx ,pos[1]- textDeltaYLabel ,this["nickName"], color=this["textColor"] ,size="x-small")

		except  Exception, e:
			logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e) )
	try:
		if plotData["ShowCaption"] != "0":
			logger.log(20,"Caption: text offset x= {:.2f};   y={:.2f}".format(textDeltaYCaption, textDeltaYCaption) )
			if plotData["ShowCaption"] == "1": 	y = Yscale - textDeltaYCaption*2.5
			else:							 	y = textDeltaYCaption 
			ax.plot(1.5* textDeltaXCaption,y+textDeltaYCaption, ms =captionTextSize, marker="o",color="#9F9F9F", markeredgecolor= "#000000")
			ax.text(3.3* textDeltaXCaption,y,"up" ,size=captionTextSize)

			ax.plot(7.5* textDeltaXCaption,y+textDeltaYCaption, ms =captionTextSize, marker="o",color="#9F9F9F", markeredgecolor= "#FFFFFF")
			ax.text(9.3* textDeltaXCaption,y,"down" ,size=captionTextSize)

			square = patches.Rectangle((17.5* textDeltaXCaption,y), 0.25, 0.25,angle=45.,fc="#9F9F9F", ec="#9F9F9F")
			ax.add_patch(square)
			ax.text(19.3* textDeltaXCaption,y,"expired" ,size=captionTextSize)

			ax.text(29* textDeltaXCaption,y,"levels: {}".format(unicode(hatches).strip("[]" )) ,size=captionTextSize)


			if plotData["ShowRPIs"] != "0":
				ax.plot(54* textDeltaXCaption,y+textDeltaYCaption,marker="s",color=piColor)
				ax.text(56* textDeltaXCaption,y,"RPIs" ,size=captionTextSize)

			if showTimeStamp:
				ax.text(62* textDeltaXCaption,y, "{}".format( datetime.datetime.now().strftime(_defaultDateStampFormat)) ,size=captionTextSize)

		else:
			if showTimeStamp:
				y = textDeltaYCaption 
				ax.text(5* textDeltaXCaption,y, "{}".format( datetime.datetime.now().strftime(_defaultDateStampFormat)) ,size=captionTextSize)

	except  Exception, e:
			logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e) )


	# 
	logger.log(20,"time used {:4.2f} --   making the plot:".format((time.time()-tStart)))
	try: 	plt.savefig((piPositionsDir+"beaconPositions.png").encode('utf8'))	# this does not work ==>   ,bbox_inches = 'tight', pad_inches = 0)
	except  Exception, e:
			logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e) )

	try:	pngSize = os.path.getsize((piPositionsDir+"beaconPositions.png").encode('utf8'))/1024.
	except: pnGsize = 0
	# 

	try:
		if plotData["compress"] :
			logger.log(20,"time used {:4.2f} --   compressing the png file ".format((time.time()-tStart)))
			cmd = "'"+pluginDir+"pngquant' --force --ext .xxx '"+piPositionsDir+"beaconPositions.png"+"'"
			ppp = subprocess.Popen(cmd.encode('utf8'),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  ## creates a file with .xxx, wait for completion
			try:	compSize = os.path.getsize((piPositionsDir+"beaconPositions.xxx").encode('utf8'))/1024.
			except: compSize = 0
			if os.path.isfile((piPositionsDir+"beaconPositions.png").encode('utf8')): os.remove((piPositionsDir+"beaconPositions.png").encode('utf8'))
			os.rename((piPositionsDir+"beaconPositions.xxx").encode('utf8'),(piPositionsDir+"beaconPositions.png").encode('utf8') )
			logger.log(20,"time used {:4.2f} --   file sizes: original file: {:5.1f};  compressed file: {:5.1f}[KB]".format((time.time()-tStart), pngSize,compSize) )
	except  Exception, e:
			logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e)  )
	
	try:
		if imageOutfile != piPositionsDir+"beaconPositions.png":
			logger.log(20,"time used {:4.2f} --   moving file to destination: '{}'".format((time.time()-tStart), imageOutfile) )
			if os.path.isfile((imageOutfile).encode('utf8')): os.remove((imageOutfile).encode('utf8'))
			if os.path.isfile((piPositionsDir+"beaconPositions.png").encode('utf8')):
				os.rename((piPositionsDir+"beaconPositions.png").encode('utf8'),(imageOutfile).encode('utf8') )
				if os.path.isfile((piPositionsDir+"beaconPositions.png").encode('utf8')): os.remove((piPositionsDir+"beaconPositions.png").encode('utf8'))
	except  Exception, e:
			logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e))

	logger.log(20,"time used {:4.2f} --   end  @ {}".format((time.time()-tStart), datetime.datetime.now())  )

except  Exception, e:
	logger.log(30,u"Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e))

sys.exit(0)
