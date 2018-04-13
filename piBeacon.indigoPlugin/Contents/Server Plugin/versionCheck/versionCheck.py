from distutils.version import LooseVersion
import datetime
import requests
import sys
def versionCheck(pluginId,pluginVersion,indigo,theHourToCheckversion,theMinuteToCheckversion, printToLog="no"):
    global lastDayversionCheck
    dd =  datetime.datetime.now()

    if dd.hour   != theHourToCheckversion :         return "" 
    if dd.minute <  theMinuteToCheckversion :       return ""
    if dd.minute >  theMinuteToCheckversion+10 :    return ""
    if "lastDayversionCheck" in vars() or "lastDayversionCheck" in globals():
        if dd.day  == lastDayversionCheck:  return ""
    lastDayversionCheck  = dd.day

    if printToLog =="log":
        indigo.server.log("versionCheck for "+unicode(pluginId)+"  installed: "+unicode(pluginVersion))
    
    # Create some URLs we'll use later on
    current_version_url = "https://api.indigodomo.com/api/v2/pluginstore/plugin-version-info.json?pluginId={}".format(pluginId)
    store_detail_url    = "https://www.indigodomo.com/pluginstore/{}/"
    try:
        # GET the url from the servers with a short timeout (avoids hanging the plugin)
        reply  = requests.get(current_version_url, timeout=5)
        # This will raise an exception if the server returned an error
        reply.raise_for_status()
        # We now have a good reply so we get the json
        reply_dict  = reply.json()
        plugin_dict = reply_dict["plugins"][0]
        # Make sure that the 'latestRelease' element is a dict (could be a string for built-in plugins).
        latest_release = plugin_dict["latestRelease"]
          # Compare the current version with the one returned in the reply dict
        if isinstance(latest_release, dict):
            if LooseVersion(latest_release["number"]) > LooseVersion(pluginVersion):
                    # The release in the store is newer than the current version.
                    # We'll do a couple of things: first, we'll just log it
                    if printToLog =="log":
                        indigo.server.log("A new version of the plugin (v{}) is available at: {}".format(
                          latest_release["number"], store_detail_url.format(plugin_dict["id"])  )  )
            else:
                    if printToLog =="log":
                        indigo.server.log("the version of the plugin is up to date; version on server:{}".format(latest_release["number"]) )
            return latest_release["number"]
        return latest_release
    except  Exception, e:
        if printToLog =="log":
            indigo.server.log("version_check:  Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
    return ""
### print versionCheck("com.karlwachs.pibeacon","1.2.3",printToLog="print" )

