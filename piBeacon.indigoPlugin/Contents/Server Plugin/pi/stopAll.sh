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

# master.py is started as "python3 -E master.py" from INSIDE $HOMEDIR - a RELATIVE path, so its
# command line does not contain /home/pi/pibeacon and "python.*${HOMEDIR}" never matched it. The
# result was the worst kind of failure: stopAll printed "all piBeacon programs stopped" while
# master.py was still running, restarted beaconloop/BLEconnect within seconds, and killed the
# measurement tool's "sudo .." wrapper through its own killSudos - so qualifyDongle died silently
# right after "resetting all adapters" with no traceback and no report. callbeacon.py is started
# from /home/pi and is relative in the same way.
# Two patterns, because no single one sees everything piBeacon starts:
#   PYPAT - the python programs. master.py and callbeacon.py are the relative ones described above.
#   SHPAT - the supervisors AND the shell helpers that live in $HOMEDIR (getRaspiConfig.sh and
#           friends). Those are not python at all, so every python pattern is blind to them and
#           they were left running by every previous version - visible as "bash
#           /home/pi/pibeacon/getRaspiConfig.sh" surviving a "all piBeacon programs stopped".
PYPAT="python.*(${HOMEDIR}|master\.py|callbeacon\.py)"
SHPAT="(master\.sh|startmaster\.sh|${HOMEDIR}/[^ ]*\.sh)"

# every piBeacon process, as "pid command-line". This script, its sudo wrapper and its shell all
# carry "stopAll" in their own command line (SHPAT matches $HOMEDIR/stopAll.sh), so they are
# filtered out by name; $$ / $PPID in pibPids below catch anything the name filter misses.
listPiBeacon() {
	{ pgrep -af "$PYPAT"; pgrep -af "$SHPAT"; } 2>/dev/null | grep -v stopAll | sort -un -k1,1
}

# the same set as PIDs only, de-duplicated. ONE source for the listing and for the kills, so the
# "all piBeacon programs stopped" line can never again claim success while something is still up.
pibPids() {
	listPiBeacon | awk '{print $1}' | grep -vx -e "$$" -e "$PPID" | sort -un
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

# 3. piBeacon programs: TERM first so they can close sockets and radios, KILL what is left
pids=$(pibPids | tr '\n' ' ')
if [ -n "$pids" ]; then
	echo "   TERM: $pids"
	sudo kill -15 $pids 2>/dev/null
	sleep 2
fi
pids=$(pibPids | tr '\n' ' ')
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
