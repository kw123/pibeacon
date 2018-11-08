######################################################################################
# .logfile handling 
######################################################################################
import indigo
import os 
import sys
import datetime
import time



class MLX():

    def __init__(self):
        self.logFile        = ""
        self.logFileActive  = False
        self.debugLevel     = []
        self.maxFileSize    = 5000000
        self.lastCheck      = time.time()


####-----------------  set paramete rs ---------
    def myLogSet(self, **kwargs ):# eg (debugLevel = "abc",logFileActive=True/False ,logFile = "pathToLogFile",  maxFileSize = 10000000)
        for key, value in kwargs.iteritems():
            try:
                if key == "logFileActive":
                    self.logFileActive    = value
            
                elif key == "logFile":
                    self.logFile    = value
            
                elif key == "debugLevel":
                    self.debugLevel     = value

                elif key == "maxFileSize" :
                    self.maxFileSize     = int(value)
                    
            except  Exception, e:
                if len(unicode(e)) > 5:
                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        indigo.server.log(u"myLogSet setting parameters -- logFileActive= "+ unicode(self.logFileActive) + ";  logFile= "+ unicode(self.logFile)  + ";  debugLevel= "+ unicode(self.debugLevel) +"; maxFileSize= "+ unicode(self.maxFileSize))


####-----------------  check logfile sizes ---------
    def checkLogFiles(self):
        try:
            self.lastCheck = time.time()
            if self.logFileActive =="standard": return 
            
            fn = self.logFile.split(".log")[0]
            if os.path.isfile(fn + ".log"):
                fs = os.path.getsize(fn + ".log")
                if fs > self.maxFileSize:  
                    self.myLog("all", " reset logfile due to size > " +unicode(self.maxFileSize))
                    if os.path.isfile(fn + "-2.log"):
                        os.remove(fn + "-2.log")
                    if os.path.isfile(fn + "-1.log"):
                        os.rename(fn + ".log", fn + "-2.log")
                        os.remove(fn + "-1.log")
                    os.rename(fn + ".log", fn + "-1.log")
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log( u"checkLogFiles in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            
            
####-----------------    ---------
    def decideMyLog(self, msgLevel):
        try:
            if msgLevel  == u"all" or u"all" in self.debugLevel:     return True
            if msgLevel  == ""   and u"all" not in self.debugLevel:  return False
            if msgLevel in self.debugLevel:                          return True
            return False
        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log( u"decideMyLog in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return False

####-----------------  print to logfile or indigo log  ---------
    def myLog(self,  text="", mType="", errorType="", showDate=True):
           
    
        if  time.time() - self.lastCheck > 100:
             self.checkLogFiles()

      
        try:
            if  self.logFileActive =="standard":
                if errorType == u"smallErr":
                    indigo.server.log(u"------------------------------------------------------------------------------")
                    indigo.server.log(text)
                    indigo.server.log(u"------------------------------------------------------------------------------")
                    return

                if errorType == u"bigErr":
                    self.errorLog(u"==================================================================================")
                    self.errorLog(text)
                    self.errorLog(u"==================================================================================")
                    return

                if mType == "":
                    indigo.server.log(text)
                else:
                    indigo.server.log(text, type=mType)
                return


            else: # print to external logfile


                ts =""
                try:
                    if len(self.logFile) < 3: return # not properly defined
                    f =  open(self.logFile,"a")
                except  Exception, e:
                    indigo.server.log(u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                    try:
                        f.close()
                    except:
                        pass
                    return

                if errorType == u"smallErr":
                    if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
                    f.write(u"----------------------------------------------------------------------------------\n")
                    f.write((ts+u" ".ljust(12)+u"-"+text+u"\n").encode(u"utf8"))
                    f.write(u"----------------------------------------------------------------------------------\n")
                    f.close()
                    return

                if errorType == u"bigErr":
                    if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
                    ts = datetime.datetime.now().strftime(u"%H:%M:%S")
                    f.write(u"==================================================================================\n")
                    f.write((ts+u" "+u" ".ljust(12)+u"-"+text+u"\n").encode(u"utf8"))
                    f.write(u"==================================================================================\n")
                    f.close()
                    return

                if showDate: ts = datetime.datetime.now().strftime(u"%H:%M:%S")
                if mType == u"":
                    f.write((ts+u" " +u" ".ljust(25)  +u"-" + text + u"\n").encode("utf8"))
                else:
                    f.write((ts+u" " +mType.ljust(25) +u"-" + text + u"\n").encode("utf8"))
                f.close()
                return


        except  Exception, e:
            if len(unicode(e)) > 5:
                indigo.server.log(u"myLog in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                indigo.server.log(text)
                try: f.close()
                except: pass


