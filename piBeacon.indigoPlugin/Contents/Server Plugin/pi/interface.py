import subprocess
subprocess.Popen("sudo cp /home/pi/pibeacon/interfaces /etc/network/interfaces ",shell=True)
subprocess.Popen("sudo cp /home/pi/pibeacon/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf ",shell=True)

