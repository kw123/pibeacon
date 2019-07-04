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
import matplotlib.pyplot as plt
import matplotlib.patches as patches

#################################
#################################
   

def toLog(text, force=False):
	global logfileName, logLevel, printON
	if not logLevel and not force: return 

	l=open(logfileName,"a")
	l.write("plotPosition: {}\n".format(text) )
	l.close()
	if printON:
		print text

####### main pgm / loop ############
global logfileName, logLevel, printON

printON = False


pluginDir		  = sys.argv[0].split("makeBeaconPositionPlots.py")[0]
indigoDir		  = pluginDir.split("Plugins/")[0]

piPositionsDir  = sys.argv[1]

f=open(piPositionsDir+"positions.json")
plotData = json.loads(f.read())
f.close()

### logfile setup
logLevel = plotData["logLevel"]
logfileName=plotData["logFile"]

try:
	if printON:  print logLevel, logfileName


	# print start to logfile 
	toLog("========= start @ {}  =========== ".format(datetime.datetime.now()) )
	tStart= time.time()

	toLog("imageYscale        :"+unicode(plotData["Yscale"]) )
	toLog("imageXscale        :"+unicode(plotData["Xscale"]) )
	toLog("imageDotsY         :"+unicode(plotData["dotsY"]) )
	toLog("imageText          :"+unicode(plotData["Text"]) )
	toLog("imageTextColor     :"+unicode(plotData["TextColor"]) )
	toLog("imageTextPos       :"+unicode(plotData["TextPos"]) )
	toLog("imageTextRotation  :"+unicode(plotData["TextRotation"]) )
	toLog("distanceUnits      :"+unicode(plotData["distanceUnits"]) )
	toLog("imageOutfile       :"+unicode(plotData["Outfile"]) )
	toLog("compressImage      :"+unicode(plotData["compress"]) )
	toLog("Zlevels            :"+unicode(plotData["Zlevels"]) )



	distanceUnits		= float(plotData["distanceUnits"])
	Yscale				= float(plotData["Yscale"])
	Xscale				= float(plotData["Xscale"])
	dotsY				= int(plotData["dotsY"])
	dotsX				= dotsY *( Xscale/Yscale) 
	Zlevels				= plotData["Zlevels"].split(",")
	nZlevels = min(len(Zlevels),4)
	for i in range(nZlevels):
		Zlevels[i] = int(Zlevels[i])
	hatches = ["","//","\\","+"]


	textOffY = 4 *Yscale/ dotsY  # move 4 points 
	toLog("textOffY	        :"+unicode(textOffY) )
	textOffX = 5 *Xscale/ dotsX  # move 4 points 
	toLog("textOffX	        :"+unicode(textOffX) )

	imageOutfile			= plotData["Outfile"]
	if imageOutfile =="":
		imageOutfile = piPositionsDir+"beaconPositions.png"


	TransparentBackground = "0.0"

	toLog("beacon data:")
	for mac in plotData["mac"]:
		toLog(mac+"  "+unicode(plotData["mac"][mac]) )



	#
	toLog("time used {:4.2f} --   setup fig, ax".format((time.time()-tStart)) )
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
		toLog("time used {:4.2f} --   loading background image file: '{}'".format( (time.time()-tStart),backGFile ) )
		img = plt.imread(backGFile)
		ax.imshow(img, extent=[0., Xscale, 0., Yscale])
	else:
		toLog("time used     --   background image file not loaded, not found --  background.png  not in {} and not in {}".format(imageOutfile, piPositionsDir) )

	  


	# 
	imageText				= plotData["Text"]
	if imageText != "": 
		toLog("time used {:4.2f} --   adding  text".format((time.time()-tStart)) )
		imageTextColor		= plotData["TextColor"]
		imageTextSize		= int(plotData["TextSize"])
		imageTextPos		= plotData["TextPos"].split(",")
		imageTextPos		= [float(imageTextPos[0]),float(imageTextPos[1])]
		imageTextRotation	= int(plotData["TextRotation"])
		ax.text(imageTextPos[0],imageTextPos[1],imageText, color=imageTextColor ,size=imageTextSize, rotation=imageTextRotation,clip_on=True)




	piColor = "#00FF00"
  
	toLog("time used {:4.2f} --   now loop though the beacons and add them".format((time.time()-tStart)) )
	for mac in plotData["mac"]: # get the next beacon
		try:
				this  = plotData["mac"][mac]
				pos   = this["position"]
				try: 	alpha = float(this["symbolAlpha"])
				except:	alpha = 0.5

				if len(pos) !=3: pos= [5,5,5]
				pos[0] = max(0., min(pos[0], Xscale ))
				pos[1] = max(0., min(pos[1], Yscale ))
				# show the marker
				try:	 distanceToRPI = this["distanceToRPI"] *0.5 / distanceUnits
				except:  distanceToRPI  = 0.5 / distanceUnits
				distanceToRPI = max( min(distanceToRPI, 3./distanceUnits), 0.2/distanceUnits) 
			
				symbol = this["symbolType"].lower()
				edgecolor = this["symbolColor"]
				if len(edgecolor)  != 7: edgecolor ="#0F0FF0"
				color = this["symbolColor"]
				if len(color)  != 7: color ="#0FF00F"
				if symbol !="text":
					if	  symbol =="dot":
						distanceToRPI  = 0.1 / distanceUnits
						Dtype ="circle"
					elif	symbol =="smallcircle":
						Dtype ="circle"
						distanceToRPI  = 0.3 / distanceUnits
					elif	symbol =="largecircle":
						Dtype ="circle"
						distanceToRPI  = 0.5* distanceToRPI / distanceUnits
					elif	symbol =="square":
						Dtype ="square"
						distanceToRPI  = 0.7 / distanceUnits
					elif	symbol =="square45":
						Dtype ="square45"
						distanceToRPI  = 0.7 / distanceUnits
					else:
						Dtype =""
			
					hatch=""
					for ii in range(nZlevels):
						if int(pos[2]) == Zlevels[ii]:
							hatch = hatches[ii]
							break

					if this["status"] == u"up":
						edgecolor= "#000000"
				
					toLog(this["name"].ljust(26)+"  "+ this["nickName"].ljust(6) +"  color:"+ color.ljust(7)+ "  edgecolor:"+ edgecolor.ljust(7) +" symbol:"+ symbol.ljust(11)+" type:"+ Dtype.ljust(8) +" distanceToRPI:%5.1f"%distanceToRPI+"  hatch:" +hatch.ljust(2) +"  status:"+ this["status"])

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
					if symbol =="text": 
						ax.text(pos[0] ,pos[1] ,this["nickName"], color=this["textColor"] ,size="x-small")
						toLog(this["name"].ljust(26)+"  "+ this["nickName"].ljust(6) +"  color:"+ color.ljust(7)  +"  status:"+ this["status"]+"  use nickname text, no symbol")
					else:
						ax.text(pos[0]+ textOffX ,pos[1]- textOffY ,this["nickName"], color=this["textColor"] ,size="x-small")

		except  Exception, e:
			toLog(u"in Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e),  force=True )

	try:
		if plotData["ShowCaption"] != "0":
			textDeltaX = 6  *Xscale / dotsX  # move 8 points 
			textDeltaY = 5  *Yscale / dotsY  # move 12 points 
			toLog("Caption: text offset x= %.2f"%textDeltaX+";   y=%.2f"%textDeltaY )
			if plotData["ShowCaption"]=="1": y = Yscale - textDeltaY
			else:							 y = textDeltaY 

			ax.plot(textDeltaX,y+textOffY,marker="o",color="#9F9F9F", markeredgecolor= "#000000")
			ax.text(textDeltaX*2,y,"up" ,size=imageTextSize-3)

			ax.plot(textDeltaX*5,y+textOffY,marker="o",color="#9F9F9F", markeredgecolor= "#FFFFFF")
			ax.text(textDeltaX*6,y,"down" ,size=imageTextSize-3)

			square = patches.Rectangle((textDeltaX*11,y), 0.25, 0.25,angle=45.,fc="#9F9F9F", ec="#9F9F9F")
			ax.add_patch(square)
			ax.text(textDeltaX*12,y,"expired" ,size=imageTextSize-3)

			ax.text(textDeltaX*18,y,"levels "+unicode(hatches) ,size=imageTextSize-3)
			#ax.plot(textDeltaX*14,y+textOffY,marker="o",color="#9F9F9F", markeredgecolor= "#FFFFFF")


			if plotData["ShowRPIs"] != "0":
				ax.plot(textDeltaX*34,y+textOffY,marker="s",color=piColor)
				ax.text(textDeltaX*35,y,"RPIs" ,size=imageTextSize-3)

	except  Exception, e:
			toLog(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), force=True )


	# 
	toLog("time used {:4.2f} --   making the plot:".format((time.time()-tStart)))
	try: 	plt.savefig((piPositionsDir+"beaconPositions.png").encode('utf8'))	# this does not work ==>   ,bbox_inches = 'tight', pad_inches = 0)
	except  Exception, e:
			toLog(u"in Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e),  force=True )


	try:	pngSize = os.path.getsize((piPositionsDir+"beaconPositions.png").encode('utf8'))/1024.
	except: pnGsize = 0
	# 

	try:
		if plotData["compress"] :
			toLog("time used {:4.2f} --   compressing the png file ".format((time.time()-tStart)))
			cmd = "'"+pluginDir+"pngquant' --force --ext .xxx '"+piPositionsDir+"beaconPositions.png"+"'"
			ppp = subprocess.Popen(cmd.encode('utf8'),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  ## creates a file with .xxx, wait for completion
			try:	compSize = os.path.getsize((piPositionsDir+"beaconPositions.xxx").encode('utf8'))/1024.
			except: compSize = 0
			if os.path.isfile((piPositionsDir+"beaconPositions.png").encode('utf8')): os.remove((piPositionsDir+"beaconPositions.png").encode('utf8'))
			os.rename((piPositionsDir+"beaconPositions.xxx").encode('utf8'),(piPositionsDir+"beaconPositions.png").encode('utf8') )
			toLog("time used {:4.2f}  --   file sizes: original file: {:5.1f};  compressed file: {:5.1f}[KB]".format((time.time()-tStart), pngSize,compSize) )
	except  Exception, e:
			toLog(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e), force=True )
	
	try:
		if imageOutfile != piPositionsDir+"beaconPositions.png":
			toLog("time used {:4.2f} --   moving file to destination: '{}'".format((time.time()-tStart), imageOutfile) )
			if os.path.isfile((imageOutfile).encode('utf8')): os.remove((imageOutfile).encode('utf8'))
			if os.path.isfile((piPositionsDir+"beaconPositions.png").encode('utf8')):
				os.rename((piPositionsDir+"beaconPositions.png").encode('utf8'),(imageOutfile).encode('utf8') )
				if os.path.isfile((piPositionsDir+"beaconPositions.png").encode('utf8')): os.remove((piPositionsDir+"beaconPositions.png").encode('utf8'))
	except  Exception, e:
			toLog(u"in Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e), force=True )

	toLog("time used {:4.2f} --   end  @ {}".format((time.time()-tStart), datetime.datetime.now())  )

except  Exception, e:
	toLog(u"in Line {} has error={}" .format(sys.exc_traceback.tb_lineno, e), force=True )

sys.exit(0)
