#!/bin/bash
####################
# stopAll.sh - stop every piBeacon program, so a measurement tool has the radios to itself
#
# Order matters: the SUPERVISORS go first. master.sh restarts master.py within seconds, and
# master.py restarts everything else - kill the python programs first and they are simply back
# before you have typed the next command.
#
# By default only processes belonging to /home/pi/pibeacon are touched, so system python (and
# anything else you happen to be running) is left alone.
#
# usage:
#    sudo bash stopAll.sh              stop piBeacon (supervisors + its python programs)
#    sudo bash stopAll.sh all          ... and EVERY other python/python3 process as well
#    sudo bash stopAll.sh status       show what is running, kill nothing
#
# restart afterwards:  sudo python3 /home/pi/callbeacon.py &     (or just reboot)
####################

HOMEDIR=/home/pi/pibeacon
MODE="${1:-pibeacon}"

listPiBeacon() {
	# pgrep -af prints "pid full-command-line" and matches the same way the kills below do, so the
	# status output cannot disagree with what actually gets killed
	pgrep -af "python.*${HOMEDIR}" | grep -v stopAll
	pgrep -af "master\.sh" | grep -v stopAll
	pgrep -af "startmaster\.sh" | grep -v stopAll
}

if [ "$MODE" = "status" ]; then
	echo "== piBeacon processes =="
	listPiBeacon
	echo ""
	echo "== all python processes =="
	ps -eo pid,args | grep -E "python[0-9]?" | grep -v grep | grep -v stopAll
	exit 0
fi

echo "== stopping piBeacon =="

# 1. supervisors FIRST - otherwise everything we kill below comes straight back
for pgm in master.sh startmaster.sh; do
	pids=$(pgrep -f "$pgm" | tr '\n' ' ')
	if [ -n "$pids" ]; then
		echo "   stopping $pgm (pids: $pids)"
		sudo pkill -f "$pgm"
	fi
done
sleep 1

# 2. tell the display to get out of its loops. NOT temp/display.stop: that marker is ignored
#    within the first 15 s of a display's life (grace window against stale markers), so it does
#    nothing for a display that has just started. temp/rebooting.now is checked at every loop in
#    display.py and breaks out immediately - and piBeaconUtils.resetRebootingNow() deletes it at
#    the next start, so nothing is left behind.
if pgrep -f "${HOMEDIR}/display.py" > /dev/null; then
	echo "   signalling display.py (temp/rebooting.now)"
	echo "rebooting now" > "${HOMEDIR}/temp/rebooting.now" 2>/dev/null
	chmod 666 "${HOMEDIR}/temp/rebooting.now" 2>/dev/null
	sleep 2
fi

# 3. piBeacon python programs: TERM first so they can close sockets and radios, KILL what is left
pids=$(pgrep -f "python.*${HOMEDIR}" | tr '\n' ' ')
if [ -n "$pids" ]; then
	echo "   TERM: $pids"
	sudo kill -15 $pids 2>/dev/null
	sleep 2
fi
pids=$(pgrep -f "python.*${HOMEDIR}" | tr '\n' ' ')
if [ -n "$pids" ]; then
	echo "   KILL: $pids"
	sudo kill -9 $pids 2>/dev/null
	sleep 1
fi

# 4. optional: everything else python too. Deliberately NOT the default - on a raspberry pi that
#    also hits system services, and this script is meant for a measurement session, not a purge.
if [ "$MODE" = "all" ]; then
	echo "   mode 'all': stopping every other python process too"
	others=$(pgrep -f "python[0-9]\?" | grep -v "^$$\$" | tr '\n' ' ')
	if [ -n "$others" ]; then
		echo "   KILL: $others"
		sudo kill -9 $others 2>/dev/null
	fi
fi

sleep 1
left=$(listPiBeacon)
if [ -z "$left" ]; then
	echo "== all piBeacon programs stopped =="
else
	echo "== still running: =="
	echo "$left"
fi

echo ""
echo "radios are free now - e.g.:  sudo python3 ${HOMEDIR}/qualifyDongle.py 10"
echo "restart piBeacon with:       sudo python3 /home/pi/callbeacon.py &"
