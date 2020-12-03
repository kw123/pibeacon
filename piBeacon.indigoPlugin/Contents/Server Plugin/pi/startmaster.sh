#!/bin/bash
# start master.py if not running , called from xwindows 
sleep 2
while [ 1 ]
do
 ps -ef | grep 'master.py' | grep -v grep || nohup sudo /usr/bin/python /home/pi/pibeacon/master.py
 sleep 20
done
