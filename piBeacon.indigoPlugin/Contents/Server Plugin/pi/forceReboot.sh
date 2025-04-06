echo "rebooting now" > temp/rebooting.now
sudo killall -9 python3
sudo killall -9 python2
sudo killall -9 python
sudo sync
sleep 8
sudo reboot -f 
