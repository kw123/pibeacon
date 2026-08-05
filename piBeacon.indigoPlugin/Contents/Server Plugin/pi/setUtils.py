import subprocess
import os
import sys
import getpass

# create shortcuts:  tm and tf ==  tail -F /home/pi/pibeacon/messageSend amd tail -F /var/log/pibeacon


import	piBeaconUtils	as U
import	piBeaconGlobals as G

bashFile = "{}.bashrc".format(G.homeDir0)
program = "setUtils"

if getpass.getuser() !="root":
	cmd = "sudo python3 {}{}.py &".format(G.homeDir, program)
	print(" not root, restarting with  "+ cmd)
	subprocess.call(cmd, shell=True)
	exit()

sys.path.append(os.getcwd())

U.setLogging()



def execAddingUtils():
	"""Creates convenience shell helper scripts (tf, tm, ct, py) in the plugin home directory for tailing logs and viewing parameters, and appends the home directory to the shell PATH in the bash profile if not already present.

	Inputs:
	    None.
	Outputs:
	    None: writes helper scripts, modifies bash profile PATH, logs
	"""
	try:
		if True:
			U.logger.log(20, "creating tf tm  py ct util commands")
			# four one-line helper scripts - write + chmod directly, no shell needed
			for nn, content in [["tf", "tail -F /var/log/pibeacon"],
								["tm", "tail -F {}temp/messageSend".format(G.homeDir)],
								["ct", "cat  {}parameters".format(G.homeDir)],
								["py", "ps -ef | grep py"]]:
				U.doWriteSimpleFile("{}{}".format(G.homeDir, nn), content + "\n")
				try:	os.chmod("{}{}".format(G.homeDir, nn), 0o755)
				except Exception:	pass
	
		# add local dir to PATH
		out = subprocess.Popen("cat {} ".format(bashFile), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode('utf_8')
		if out.find("{}".format(G.homeDir.rstrip("/"))) == -1: 
			U.logger.log(20, "adding  homedir to PATH")
			cmd = "echo '\nexport PATH=$PATH:{}' >> {}".format(G.homeDir.rstrip("/"), bashFile)
			U.logger.log(20, "adding {} to PATH  with: {}; will be active after next reboot".format(G.homeDir, cmd))
			subprocess.call(cmd, shell=True)

	except Exception as e:
		U.logger.log(20,"", exc_info=True)



execAddingUtils()