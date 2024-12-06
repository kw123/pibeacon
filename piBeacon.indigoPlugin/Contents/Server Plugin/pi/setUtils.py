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
	try:
		if not os.path.isfile(G.homeDir+"tm"): 
			U.logger.log(20, "creating tf and tm util commands")
			subprocess.call("echo 'tail -F /var/log/pibeacon' > {}tf;chmod +x {}tf ".format(G.homeDir,G.homeDir), shell=True)
			subprocess.call("echo 'tail -F {}temp/messageSend' > {}tm;chmod +x {}tm ".format(G.homeDir,G.homeDir,G.homeDir), shell=True)
	
		# add local dir to PATH
		out = subprocess.Popen("cat {} | grep {}".format(bashFile,G.homeDir), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode('utf_8')
		if out.find("export PATH=$PATH:".format(G.homeDir)) == -1: 
			U.logger.log(20, "adding  homedir to PATH")
			cmd = "echo '\nexport PATH=$PATH:{}' >> {}".format(G.homeDir, bashFile)
			U.logger.log(20, "adding {} to PATH  with: {}; will be active after next reboot".format(G.homeDir, cmd))
			subprocess.call(cmd, shell=True)

	except Exception as e:
		U.logger.log(30,"", exc_info=True)


execAddingUtils()