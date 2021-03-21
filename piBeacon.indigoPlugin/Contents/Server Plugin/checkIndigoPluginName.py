#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Developed by Karl Wachs
# karlwachs@me.com

# ===========================================================================
# ch eck for proper plugin name
# ===========================================================================

def checkIndigoPluginName(self, indigo):
	if self.pathToPlugin.find(u"/"+self.pluginName+".indigoPlugin/") ==-1:
		indigo.server.log(u"-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log(u"-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log(u"-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log(u"-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log(u"-----------------------------------------------------------------------------------------------------------------------" )
		self.errorLog(u"The pluginname is not correct, please reinstall or rename")
		self.errorLog(u"It should be   /Libray/....../Plugins/{}.indigPlugin".format(self.pluginName))
		p=max(0,self.pathToPlugin.find(u"/Contents/Server"))
		self.errorLog(u"It is: {}".format(self.pathToPlugin[:p]))
		self.errorLog(u"please check your download folder, delete old *.indigoPlugin files or this will happen again during next update" )
		self.errorLog(u"This happens eg when you download a new version and and old with the same name is still in the download folder" )
		self.errorLog(u" ")
		self.errorLog(u"=== and brute force fix method: === ")
		self.errorLog(u"Shut down the Indigo Server by selecting the Indigo Stop Server menu item in the Mac client " )
		self.errorLog(u"   (you can leave the client app running).")
		self.errorLog(u"Open the following folder in the Finder: /Library/Application Support/Perceptive Automation/Indigo x.y/ " )
		self.errorLog(u"  (you can select the Go→Go to Folder… menu item in the Finder and paste in the path to open a Finder window)." )
		self.errorLog(u"  In that Finder window you'll see two folders: " )
		self.errorLog(u"Plugins and Plugins (Disabled). Depending on whether the plugin is enabled or not will determine which folder it's in." )
		self.errorLog(u"Open the appropriate folder and delete the unwanted plugin." )
		self.errorLog(u"Switch back to the Indigo Mac client and click on the Start Local Server… button in the Server Connection Status dialog." )
		self.errorLog(u"Then reinstall the plugin" )
		indigo.server.log(u"-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log(u"-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log(u"-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log(u"-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log(u"-----------------------------------------------------------------------------------------------------------------------" )
		self.sleep(100000)
		self.quitNOW="wrong plugin name"
		return False
	return True
