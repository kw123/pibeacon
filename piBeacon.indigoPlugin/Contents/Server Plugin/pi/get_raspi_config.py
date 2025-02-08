import subprocess, json
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

def execRaspi(params):
	#print("params:{}".format(params))
	try:
		logFile = ""
		ll = len(params)
		myPath = params[0].split("get_raspi_config.py")[0]
		if len(myPath) == 0:
			noLog = True
		else:
			noLog = False
			if ll != 1:	logFile = params[1]
	except Exception:
		print("error, call: python3 get_raspi_config.py logpath")
		exit()
	
	print("======starting: get_raspi_config.py")
	if os.path.isfile("/boot/firmware/config.txt"): 
		addFirmware = "/boot/firmware/"
	else:
		addFirmware = "/boot/"

	try:
		if logFile != "":
			logging.basicConfig(level=logging.INFO, filename= logFile,format='%(asctime)s %(module)-17s %(funcName)-22s L:%(lineno)-4d Lv:%(levelno)s %(message)s', datefmt='%d-%H:%M:%S')
			logger = logging.getLogger(__name__)
		
		pFile = myPath +"raspiConfig.params"
		if logFile != "":	logger.log(20,"starting with logging to {}, writing results to: {}".format(logFile, pFile))
		else:				print("starting with logging to console writing results to: {}".format(pFile))

		if os.path.exists(pFile):
		  os.remove(pFile)

		#print("======starting:2")
		yy = {}
		for xx in raspiConfigCommand["GET"]:
			cmd		= raspiConfigCommand["GET"][xx]['cmd']

			if cmd.find("/boot/") > 0:
				cmd = cmd.replace("/boot/", addFirmware)
			#print ("cmd:{}".format(cmd))

			res		= raspiConfigCommand["GET"][xx]['results']
			ret	= subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			result 	= ret[0].decode('utf_8').strip("\n")
			err 	= ret[1].decode('utf_8').strip("\n")
			#print("======starting:2.1")
			#print ("result:{}, err:{}".format(result, err))


			if err == "":	rr = res.get(result, res['default'])
			else:			rr = err.replace("\n","")
			if logFile != "": 	logger.log(20,"{:20} {:2s} = {}".format(xx+":", result, rr))
			else:				print(        "{:20} {:2s} = {}".format(xx+":", result, rr))
			yy[xx] = {"result":result, "text":rr,"cmd":cmd}

		#print("======starting:3")
		
		f = open(pFile,"w")
		f.write(json.dumps(yy,sort_keys=True, indent=4))
		f.close()
		
		if logFile != "":	logger.log(20,"\n results written to "+pFile+"\n finished")
		else:				print(        "\n results written to "+pFile+"\n finished")

	except Exception as e:
		print("error, call: python3 get_raspi_config.py logpath.   err={}",format(e))
		exit()
		
	

execRaspi(sys.argv)


