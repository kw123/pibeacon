import subprocess, json
import io
import sys
import os, time, logging



# Karl Wachs
# jan 23 2015
# use as you see fit.
# check
# /usr/bin/raspi-config
# for details 
# 
#  noint = cli mode 
# do_.... sets parameters
# get_... gets the value of the parameters
#
#


raspiConfigCommand = {
	"SET":{  # not used here
		'EXPAND_FS':'sudo raspi-config nonint do_expand_rootfs',
		'HOSTNAME':'sudo raspi-config nonint do_hostname %s',# name of hostname
		'BOOT_CLI_login':'sudo raspi-config nonint do_boot_behaviour B1',
		'BOOT_CLI_autologin':'sudo raspi-config nonint do_boot_behaviour B2', # cli auto login
		'BOOT_GUI_login':'sudo raspi-config nonint do_boot_behaviour B3',
		'BOOT_GUI_autologin':'sudo raspi-config nonint do_boot_behaviour B4',
		'BOOT_WAIT':'sudo raspi-config nonint do_boot_wait %d', # number
		'SPLASH':'sudo raspi-config nonint do_boot_splash %d',
		'OVERSCAN':'sudo raspi-config nonint do_overscan %d',
		'CAMERA':'sudo raspi-config nonint do_camera %d',
		'SSH':'sudo raspi-config nonint do_ssh %d',		# 0/1; 0= enable
		'VNC':'sudo raspi-config nonint do_vnc %d',		# 0/1; 0= enable
		'SPI':'sudo raspi-config nonint do_spi %d',		# 0/1; 0= enable
		'I2C':'sudo raspi-config nonint do_i2c %d',		# 0/1; 0= enable
		'SERIAL_OLD':'sudo raspi-config nonint do_serial %d',  # for  console for older os      0: enable uart, enable consle; 1=disable both, 2 = enable uart,diable
		'SERIAL_CONSOLE':'sudo raspi-config nonint do_serial_cons %d',  # 0/1; 0= enable
		'SERIAL_HARDWARE':'sudo raspi-config nonint do_serial_hw %d',  # 0/1; 0= enable
		'1WIRE':'sudo raspi-config nonint do_onewire %d',
		'RGPIO':'sudo raspi-config nonint do_rgpio %d',
		'OVERCLOCK':'sudo raspi-config nonint do_overclock %s',
		'GPU_MEM':'sudo raspi-config nonint do_memory_split %d',
		'HDMI_GP_MOD':'sudo raspi-config nonint do_resolution %d %d',
		'WIFI_COUNTRY':'sudo raspi-config nonint do_wifi_country %s '
		},
	"GET": { # used
		'CAN_EXPAND':{'cmd':'sudo raspi-config nonint get_can_expand','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'CAN_CONFIGURE':{'cmd':'sudo raspi-config nonint can_configure','results':{'0':'enabled','default':'unknown'}},
		'HOSTNAME':{'cmd':'sudo raspi-config nonint get_hostname','results':{'default':'name'}},
		'BOOT_CLI':{'cmd':'sudo raspi-config nonint get_boot_cli','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'AUTOLOGIN':{'cmd':'sudo raspi-config nonint get_autologin','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'SPLASH':{'cmd':'sudo raspi-config nonint get_boot_splash','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'OVERSCAN':{'cmd':'sudo raspi-config nonint get_overscan','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'CAMERA':{'cmd':'sudo raspi-config nonint get_camera','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'SSH':{'cmd':'sudo raspi-config nonint get_ssh','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'VNC':{'cmd':'sudo raspi-config nonint get_vnc','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'SPI':{'cmd':'sudo raspi-config nonint get_spi','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'I2C':{'cmd':'sudo raspi-config nonint get_i2c','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'SERIAL_CONSOLE':{'cmd':'sudo raspi-config nonint get_serial_cons','results':{'0':'enabled','1':'disabled','default':'unknown'}}, # does not work w old os
		'SERIAL_HARDWARE':{'cmd':'sudo raspi-config nonint get_serial_hw','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'SERIAL_CONSOLE_OLD':{'cmd':'sudo raspi-config nonint get_serial','results':{'0':'enabled','1':'disabled','default':'unknown'}}, # for old systems
		'1WIRE':{'cmd':'sudo raspi-config nonint get_onewire','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'RGPIO':{'cmd':'sudo raspi-config nonint get_rgpio','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'RPI_CONNECT':{'cmd':'sudo raspi-config nonint get_rpi_connect','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'PI_TYPE':{'cmd':'sudo raspi-config nonint get_pi_type','results':{'0':'pi_0','1':'pi_1','2':'pi_2','3':'pi_3','4':'pi_4','5':'pi_5','6':'pi_6','7':'pi_7','8':'pi_8','default':'unknown'}},
		'OVERCLOCK':{'cmd':'sudo raspi-config nonint get_config_var arm_freq /boot/config.txt','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'GPU_MEM':{'cmd':'sudo raspi-config nonint get_config_var gpu_mem /boot/config.txt','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'GPU_MEM_256':{'cmd':'sudo raspi-config nonint get_config_var gpu_mem_256 /boot/config.txt','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'GPU_MEM_512':{'cmd':'sudo raspi-config nonint get_config_var gpu_mem_512 /boot/config.txt','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'GPU_MEM_1K':{'cmd':'sudo raspi-config nonint get_config_var gpu_mem_1024 /boot/config.txt','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'HDMI_GROUP':{'cmd':'sudo raspi-config nonint get_config_var hdmi_group /boot/config.txt','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'HDMI_MODE':{'cmd':'sudo raspi-config nonint get_config_var hdmi_mode /boot/config.txt','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'WIFI_COUNTRY':{'cmd':'sudo raspi-config nonint get_wifi_country','results':{'':'not set','default':'name'}},
		'OVERSCAN_KMS_SCREEN':{'cmd':'sudo raspi-config nonint get_overscan_kms','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'PCI':{'cmd':'sudo raspi-config nonint get_pci','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'PI4VIDEO':{'cmd':'sudo raspi-config nonint get_pi4video','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'COMPOSITE_VIDEO':{'cmd':'sudo raspi-config nonint get_composite','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'BLANKING_SCREEN':{'cmd':'sudo raspi-config nonint get_blanking','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'BOOT_WAIT':{'cmd':'sudo raspi-config nonint get_boot_wait','results':{'0':'enabled','1':'disabled','default':'unknown'}},
		'LEDS':{'cmd':'sudo raspi-config nonint get_leds','results':{'0':'enabled','-1':'notConfigurable','1':'on','default':'unknown'}},
		'FAN':{'cmd':'sudo raspi-config nonint get_fan','results':{'0':'enabled','1':'on','default':'unknown'}},
		'FAN_GPIO':{'cmd':'sudo raspi-config nonint get_fan_gpio','results':{'default':'gpioNumber'}},
		'FAN_TEMP':{'cmd':'sudo raspi-config nonint get_fan_temp','results':{'default':'Temperature C'}},
		'WLAN_INTERFACE':{'cmd':'sudo raspi-config nonint list_wlan_interfaces','results':{'default':'name'}}
		}
	}

def getConfigVar(key, fname):
	"""Same as raspi-config's own get_config_var: every line matching "<key>=" (leading blanks
	allowed, so commented-out lines do NOT count) yields its value, "0" when the key is absent.
	raspi-config implements this in lua on a file we can simply read ourselves - no root, no
	subprocess, no OS-version knowledge involved, so replacing it carries no risk of drifting
	away from what raspi-config does on the next release.

	Inputs:
	    key (str): config.txt key, e.g. "arm_freq"
	    fname (str): path of the config.txt to read
	Outputs:
	    str: the value(s) found (newline separated, as raspi-config prints them), or "0"
	"""
	out = []
	try:
		f = io.open(fname, encoding="utf-8", errors="replace")
		for line in f:
			line = line.strip()
			if line.startswith(key + "="):
				out.append(line.split("=", 1)[1].strip())
		f.close()
	except Exception:
		return "0"
	if len(out) == 0:	return "0"
	return "\n".join(out)


def runRaspiConfigBatch(cmds, scriptPath):
	"""Runs ALL raspi-config getters in ONE sudo/bash round trip instead of one per value.
	raspi-config is a ~2000-line bash script, and paying sudo + its startup ~30 times is what
	makes this script slow; the getters themselves are cheap. The commands are NOT reimplemented -
	raspi-config still answers every one of them, so nothing drifts when the OS changes.

	The generated shell script is WRITTEN OUT (scriptPath) and then executed, so it can be read
	and run by hand when a value looks wrong:  sudo bash <scriptPath>
	It is rebuilt from the raspiConfigCommand table on every run - editing it has no lasting
	effect, add/remove entries in the table instead.

	Output is framed with control characters (0x1e between records, 0x1f between fields) because
	several getters legitimately return multi-line values (list_wlan_interfaces).

	Inputs:
	    cmds (list): [[name, shellCommand], ...] - "sudo " prefixes are stripped, we are root already
	    scriptPath (str): where to write the generated script
	Outputs:
	    dict: {name: [stdout, stderr]} - missing entries mean the batch did not answer, the caller
	          then falls back to running that single command the old way
	"""
	out = {}
	try:
		script = ["#!/bin/bash",
				  "# GENERATED by get_raspi_config.py - rebuilt on every run, edits are lost.",
				  "# Reads every raspi-config value in one go; run by hand with: sudo bash " + scriptPath,
				  "# Output is control-character framed (0x1e record, 0x1f field) for the python side.",
				  "ERRF=$(mktemp)"]
		for name, cmd in cmds:
			inner = cmd.strip()
			if inner.startswith("sudo "):	inner = inner[5:]
			script.append('O=$({} 2>"$ERRF"); E=$(cat "$ERRF"); printf "\\036%s\\037%s\\037%s" "{}" "$O" "$E"'.format(inner, name))
		script.append('rm -f "$ERRF"')
		script.append("")

		f = io.open(scriptPath, "w", encoding="utf-8")
		f.write(u"\n".join(script))
		f.close()
		try:	os.chmod(scriptPath, 0o755)
		except Exception:	pass

		ret = subprocess.Popen("sudo bash " + scriptPath, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		for rec in ret[0].decode('utf_8').split("\036"):
			if rec == "":	continue
			ff = rec.split("\037")
			if len(ff) != 3:	continue
			out[ff[0]] = [ff[1].strip("\n"), ff[2].strip("\n")]
	except Exception:
		pass
	return out


def execRaspi(params):
	#print("params:{}".format(params))
	"""Runs each Raspberry Pi configuration GET command from the raspiConfigCommand table via subprocess, maps the output to a result text, accumulates them in a dict, and writes the collected config as JSON to raspiConfig.params, logging to a file or console.

	Inputs:
	    params (list): argv-style list whose first element is the script path and optional second element is the log file path
	Outputs:
	    None: writes raspiConfig.params JSON file, logs results, and exits on error
	"""
	try:
		logFile = ""
		ll = len(params)
		myPath = params[0].split("get_raspi_config.py")[0]
		if len(myPath) != 0:
			if ll != 1:	logFile = params[1]
	except Exception:
		print("error, call: python3 get_raspi_config.py logpath")
		exit()

	# standalone helper started with sudo: it never calls piBeaconUtils.setLogging, so it also
	# never got the umask(0) that keeps root-created files writable for the pi user
	try:	os.umask(0)
	except Exception:	pass

	print("======starting: get_raspi_config.py")
	if os.path.isfile("/boot/firmware/config.txt"):
		addFirmware = "/boot/firmware/"
	else:
		addFirmware = "/boot/"

	try:
		if logFile != "":
			# a sudo-started helper creates the logfile as root and every later non-root program
			# then logs into the void (python logging hides the PermissionError) - hand it to pi
			try:
				if not os.path.isfile(logFile):
					_f = open(logFile, "a")
					_f.close()
				os.chmod(logFile, 0o666)
				import pwd, grp
				os.chown(logFile, pwd.getpwnam("pi").pw_uid, grp.getgrnam("pi").gr_gid)
			except Exception:	pass
			logging.basicConfig(level=logging.INFO, filename= logFile,format='%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d %(message)s', datefmt='%d-%H:%M:%S')
			class _TenthFmt(logging.Formatter):	# timestamps with tenths of a second, same as piBeaconUtils.setLogging
				def formatTime(self, record, datefmt=None):
					return "{}.{}".format(time.strftime(datefmt or '%d-%H:%M:%S', time.localtime(record.created)), int(record.msecs/100.))
			for _h in logging.getLogger().handlers: _h.setFormatter(_TenthFmt('%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d %(message)s', datefmt='%d-%H:%M:%S'))
			logger = logging.getLogger(__name__)

		pFile = myPath +"raspiConfig.params"
		if logFile != "":	logger.log(20,"starting with logging to {}, writing results to: {}".format(logFile, pFile))
		else:				print("starting with logging to console writing results to: {}".format(pFile))

		if os.path.exists(pFile):
			os.remove(pFile)

		#print("======starting:2")
		yy = {}
		# collect first, then ask raspi-config ONCE for everything it still has to answer
		allCmds  = []
		toRaspi  = []
		for xx in raspiConfigCommand["GET"]:
			cmd		= raspiConfigCommand["GET"][xx]["cmd"]
			if cmd.find("/boot/") > 0:
				cmd = cmd.replace("/boot/", addFirmware)
			allCmds.append([xx, cmd])
			if cmd.find("nonint get_config_var ") < 0:	toRaspi.append([xx, cmd])
		scriptPath = myPath + "getRaspiConfig.sh"
		batched    = runRaspiConfigBatch(toRaspi, scriptPath)
		if logFile != "":	logger.log(20,"raspi-config: {} value(s) answered in one call ({}), {} read from config.txt directly".format(len(batched), scriptPath, len(allCmds)-len(toRaspi)))
		else:				print(        "raspi-config: {} value(s) answered in one call, {} read from config.txt directly".format(len(batched), len(allCmds)-len(toRaspi)))

		for xx, cmd in allCmds:
			res		= raspiConfigCommand["GET"][xx]["results"]
			# "get_config_var <key> <file>" is a plain read of config.txt - do it in python and
			# skip the sudo+bash+raspi-config round trip (7 of them). Everything else still goes
			# through raspi-config on purpose: those answers depend on systemd unit names, boot
			# targets, NetworkManager-vs-wpa_supplicant etc., which change between OS releases -
			# reimplementing them here would drift silently on the next reimage.
			if cmd.find("nonint get_config_var ") > 0:
				parts	= cmd.split("nonint get_config_var ")[1].split()
				result	= getConfigVar(parts[0], parts[1])
				err		= ""
			elif xx in batched:
				result, err = batched[xx][0], batched[xx][1]
			else:
				# batch did not answer this one (no bash? mktemp failed?) - old single-command way
				ret	= subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
				result 	= ret[0].decode('utf_8').strip("\n")
				err 	= ret[1].decode('utf_8').strip("\n")
			#print("======starting:2.1")
			#print ("result:{}, err:{}".format(result, err))


			if err == "":	rr = res.get(result, res["default"])
			else:			rr = err.replace("\n","")
			if logFile != "": 	logger.log(20,"{:20} {:2s} = {}".format(xx+":", result, rr))
			else:				print(        "{:20} {:2s} = {}".format(xx+":", result, rr))
			yy[xx] = {"result":result, "text":rr,"cmd":cmd}

		#print("======starting:3")

		f = open(pFile,"w")
		f.write(json.dumps(yy,sort_keys=True, indent=4))
		f.close()
		try:						# do not leave the params file owned by root
			os.chmod(pFile, 0o666)
			import pwd, grp
			os.chown(pFile, pwd.getpwnam("pi").pw_uid, grp.getgrnam("pi").gr_gid)
		except Exception:	pass

		if logFile != "":	logger.log(20,"results written to "+pFile+"   finished")
		else:				print(        "results written to "+pFile+"   finished")

	except Exception as e:
		print("error, call: python3 get_raspi_config.py logpath.   err={}",format(e))
		exit()

execRaspi(sys.argv)


