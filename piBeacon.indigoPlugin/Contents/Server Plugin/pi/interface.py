import subprocess, shutil
# plain shutil: this script does not import piBeaconUtils (it runs as a tiny root helper)
shutil.copy2("/home/pi/pibeacon/interfaces", "/etc/network/interfaces")
shutil.copy2("/home/pi/pibeacon/wpa_supplicant.conf", "/etc/wpa_supplicant/wpa_supplicant.conf")

