#!/bin/bash

home="/home/pi/pibeacon/"
cd $home

echo "This scripts checks every 25 secs if master.py is running --  if not,  will restart it"

# kill calling sudo bash  master.sh  and old master.sh tasks..
#                  list of master pids    excl grep       excl myself     get pid #s from line(s) in col 2
procsToKill=$(ps -ef | grep 'master.sh' | grep -v grep | grep -v $$ | awk '{print $2}')
#     # of char       >0            then kill the list
if [ ${#procsToKill} -gt 0 ]; then sudo kill -9 $procsToKill; fi
countUpdating=0


#now loop check master.py is running,  .. and if  not restart
while true; do
	if  ps -ef | grep master.py | grep -v grep  > /dev/null 2>&1 
		then
			for i in {1..60}
				do      # a way to to myself is to create a file temp/master.stop
					if [ -f $home"temp/master.stop" ] 
						then 
						echo "exit master.sh  -- requested by temp/master.stop file" 
						exit
					fi
					sleep 1
					echo "loop "$i 
				done
		else
			sleep 1 # test again after 1 sec
			if [ -f $home"temp/updateing" ] && [ $countUpdating -lt 3 ]
			then
				countUpdating=$(($countUpdating+1))
				#echo " incrementing "$countUpdating
				sleep 10
			else
				countUpdating=0
				rm $home"temp/updateing"
				if  ps -ef | grep master.py | grep -v grep  > /dev/null 2>&1
					then 
						echo "master.py is running, no need to restart"
					else 
						#echo " restarting master"
						echo "$(date '+%Y-%m-%d %H:%M:%S') master.sh: master.py not running restarting with  >>sudo /usr/bin/python master.py<<" >> permanent.log
						nohup sudo /usr/bin/python master.py &
				fi
			fi
	fi
done
echo "stopping master.sh"