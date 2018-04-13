#

import sys, os, subprocess
import time
import json


#################################
def readRejects():
    global homeDir, rejectsIn, rejectExiting
    rejectsIn=[]
    for pi in range(11):
        pis=str(pi)
        file=""
        if  os.path.isfile(homeDir+"rejected/rejects."+pis): 
            file=homeDir+"rejected/rejects."+pis
        
            f=open(file,"r")
            for line in f.readlines():
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
            try:    os.remove(homeDir+"rejected/rejects."+pis)
            except: pass
            try:    os.remove(homeDir+"rejects."+pis)
            except: pass
        
    try:
        rejectExiting={}
        file=""
        if  os.path.isfile(homeDir+"rejected/rejectedByPi.json"): 
            file=homeDir+"rejected/rejectedByPi.json"
            f=open(file,"r")
            rejectExiting= json.loads(f.read())
            f.close()
    except:
        pass
    
#################################
def writeRejects():
    global homeDir, rejectsIn, rejectExiting
    
    for r in rejectsIn:
        r=r.replace(" ","")
        ## pi#;9637500; UUID; ff4c000c0e00b60bbd8008f77d53-28183-15529;  71:21:38:7D:33:DA
        #print r
        items   = r.split(";")
        rPi     = items[0]
        try:
            items[1]=float(items[1])
            timeSt  = time.strftime('%Y-%m-%d %H:%M:%S',  time.localtime(items[1]))
        except  Exception, e:
            print u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)
            print ">>"+items[1]+"<<"
            print r
            #exit()
        reason  = items[2]
        uuid    = items[3]
        mac     = items[4]
        
        if mac not in  rejectExiting:
             rejectExiting[mac]={"uuid":uuid,"first":timeSt,"last":timeSt,"reason":reason,"count":1,"rPi":rPi}
             #print "adding "+ mac
        else: 
            if  rejectExiting[mac]["last"] < timeSt:
                rejectExiting[mac]["last"]=timeSt
            if  rejectExiting[mac]["first"] > timeSt:
                rejectExiting[mac]["first"]=timeSt
            if ","+rPi not in  rejectExiting[mac]["rPi"] and rejectExiting[mac]["rPi"].find(rPi)!=0:  
                rejectExiting[mac]["rPi"]+=","+rPi
            rejectExiting[mac]["count"]+=1
    
    #print  rejectExiting   
    out0=[]
    lastDate = []
    n=0
    for mac in rejectExiting:
        lastDate.append([rejectExiting[mac]["last"],n])
        n+=1
        out ='\n"'+mac+'":{'
        out+= ('"uuid":"'   +rejectExiting[mac]["uuid"]+'"').ljust(54)
        out+= ',"first":"'  +rejectExiting[mac]["first"]+'"'
        out+= ',"last":"'   +rejectExiting[mac]["last"]+'"'
        out+= (',"count":'  +str(rejectExiting[mac]["count"])).ljust(20)
        out+=  ',"reason":"'+(rejectExiting[mac]["reason"]+'"').ljust(8)
        out+= ',"rPi":"'    +rejectExiting[mac]["rPi"]+'"'
        out+=  '},'
        out0.append(out)
    lastDate.sort()     
    n = len(out0)
    out1=[]
    #print lastDate
    for ii in range(len(lastDate)):
        out1.append(out0[lastDate[ii][1]])
        #print lastDate[ii], out0[lastDate[ii][1]]
    
    if n>0:
        print "nunber of macs rejected: ",  n
        out1[n-1]=out1[n-1].strip(",")
        f=open(homeDir+"rejected/rejectedByPi.json","w")
        f.write("{")
        for line in out1:
            f.write(line)       
        f.write("\n}")
    #    f.write(json.dumps(rejectExiting,sort_keys=True, indent=2))
        f.close()
    

    

####### main pgm / loop ############
global homeDir, rejectsIn, rejectExiting
homeDir= sys.argv[1]
if homeDir[-1:] !="/": homeDir+="/"
    
print " starting checkRejects ", homeDir 

readRejects()
#print rejectsIn
writeRejects()

print "end of checkRejects"    
sys.exit(0)        
