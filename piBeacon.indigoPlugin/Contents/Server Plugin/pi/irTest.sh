#!/bin/bash
# irTest.sh - record a real IR remote, then send that same recording back out on the IR led.
#
#    ./irTest.sh a     record: press ONE button on the remote
#    ./irTest.sh b     play it back at every carrier frequency, 8 s apart
#    ./irTest.sh s     scan 25..48 kHz in 1 kHz steps, 5 s apart, temperature 19/21 alternating
#    ./irTest.sh d     walk the ac through on/temp/fan/louver/off, 10 s apart, and WATCH it
#
# Put the ac in the OPPOSITE state with the remote between a and b: record an ON command and
# switch it off, or record an OFF command and switch it on. Then only the led can change it.
# The WHOLE press is replayed, every message with the gap the remote left after it - this remote
# sends four and they are not all the same, so replaying only the first is not what it does.
# No sudo: killSudos kills anything with "python" and "sudo" in it every 10th master loop.

# LEAD-IN: every mode that TRANSMITS waits before it starts, so the run can be kicked off here
# and watched at the ac in the other room. Recording does not wait - it already waits for a
# button press. Override with LEADIN=<seconds>, LEADIN=0 to start at once.
LEADIN=${LEADIN:-15}
leadin() {
	[ "$LEADIN" -le 0 ] && return 0
	echo "== starting in $LEADIN s - go to the ac now"
	n=$LEADIN
	while [ "$n" -gt 0 ]; do
		echo "   ... $n s"
		if [ "$n" -gt 5 ]; then sleep 5; n=$((n-5)); else sleep "$n"; n=0; fi
	done
	echo "== go"
	echo ""
}
# the python tools do their own lead-in when started directly; this stops them repeating it
export IRLEADIN=0

# once, here at the start. Not for "a" - recording already waits for a button press - and not for
# an unknown argument, which should print the usage straight away.
case "$1" in
	b|c|d|m|r|s)	leadin ;;
esac

if [ "$1" = "a" ]; then
	python3 -u /home/pi/pibeacon/irRecord.py 10 30 | tee /tmp/rec.txt
	sed -n '/raw pulse list/,/first message only/p' /tmp/rec.txt | sed '1d;$d' > /tmp/pulses.txt
fi

if [ "$1" = "b" ]; then
	for f in 25000 26000 28000 30000 32000 33000 34000 36000 38000 40000 44000; do
		echo "== $f Hz"
		python3 /home/pi/pibeacon/irReplay.py 18 /tmp/pulses.txt 0.5 $f
		sleep 8
	done
fi

# c: sends through greeIR - ONE frame, the encoder's own repeats - at a fixed carrier,
# alternating 21 C and 25 C so the ac's display counts the hits.
#
# The carrier is settled: a full replay works from 26 to 40 kHz, and one greeIR frame works at
# none of them. So it is the SEQUENCE. What is left to find is whether the ac wants more
# repeats, or specifically the differing messages 2-4 the remote sends.
#    ./irTest.sh c 38000 6       the encoder's 4-MESSAGE SEQUENCE - this is the real test now
#    ./irTest.sh c 38000 6 4     four repeats of one frame, the old behaviour, for comparison
#    ./irTest.sh m 38000 3       the first 3 RECORDED messages - is the terminator needed?
if [ "$1" = "c" ]; then
	python3 - "${2:-38000}" "${3:-10}" "${4:-0}" <<'PY'
import sys, time
sys.path.insert(0, "/home/pi/pibeacon")
import pigpio, greeIR
hz = int(sys.argv[1]); n = int(sys.argv[2]); rep = int(sys.argv[3])
pi = pigpio.pi()
if not pi.connected:
	print("cannot reach pigpiod"); sys.exit(1)
try:
	for ii in range(n):
		temp  = 21 if ii % 2 == 0 else 25
		state = greeIR.buildState("cool", temp, "auto", True)
		if rep == 0:
			greeIR.sendSequence(pi, 18, state, carrierHz=hz)
			what = "4-message sequence"
		else:
			greeIR.sendState(pi, 18, state, repeats=rep, carrierHz=hz)
			what = "%d repeats of one frame" % rep
		print("   %2d/%d   %d C at %d Hz, %s   %s" % (
				ii + 1, n, temp, hz, what, greeIR.stateToHex(state)))
		time.sleep(5)
finally:
	pi.stop()
print("the display should have stepped 21/25/21/25 - every step it missed is a failure")
PY
fi

# s: the carrier scan. Goes through greeIR, not through a replay, so nothing can be split.
#    ./irTest.sh s            25..48 kHz, 1 kHz steps, 5 s apart
#    ./irTest.sh s 30 40 1 8  a narrower range, 8 s apart
if [ "$1" = "s" ]; then
	shift
	# -s, not -f: a file can arrive EMPTY. sftp "put *" copies whatever is on disk at that
	# instant, so a push that happens while a file is being written lands a 0 byte copy - and
	# python3 runs an empty file happily, exits 0 and prints nothing, which looks exactly like
	# a command that did nothing
	if [ ! -s /home/pi/pibeacon/irScan.py ]; then
		echo "irScan.py is missing or EMPTY on this rpi ($(wc -c < /home/pi/pibeacon/irScan.py 2>/dev/null || echo 0) bytes)"
		echo "send the plugin files to the rpis again"
		exit 1
	fi
	python3 -u /home/pi/pibeacon/irScan.py "$@"
fi

# anything else, including no argument at all, says so instead of exiting silently - an old copy
# of this script on the rpi is otherwise indistinguishable from a command that did nothing
case "$1" in
	a|b|c|d|m|r|s)	;;
	*)	echo "irTest.sh - IR test helper"
		echo "   ./irTest.sh a                     record a remote press, save the whole capture"
		echo "   ./irTest.sh b                     replay it at every carrier, 8 s apart"
		echo "   ./irTest.sh c <hz> <n> [repeats]  n sends, 21/25 C alternating; repeats 0 = full sequence"
		echo "   ./irTest.sh m <hz> <count>        replay only the first <count> recorded messages"
		echo "   ./irTest.sh r <hz> <n> [secs]     replay the WHOLE press n times at one carrier"
		echo "   ./irTest.sh s [first last step secs]   scan 25..48 kHz, 1 kHz steps, 19/21 C"
		echo "   ./irTest.sh d [gpio secs]         walk on/temp/fan/louver/off, watch the ac"
		echo ""
		echo "   every mode that transmits waits ${LEADIN}s first, so you can walk to the ac."
		echo "   LEADIN=0 ./irTest.sh d     start at once      LEADIN=30 ./irTest.sh d   wait longer"
		exit 1
		;;
esac

# m: replay only the first COUNT messages of the recording, so the sequence can be bisected.
# The whole press works; one frame does not. m 1, m 2, m 3 says where the line is - and it uses
# the REAL recorded frames, so the encoder is out of the question entirely.
#    ./irTest.sh m 38000 2
if [ "$1" = "m" ]; then
	python3 - "${2:-38000}" "${3:-1}" <<'PY'
import sys
sys.path.insert(0, "/home/pi/pibeacon")
import pigpio, irReplay
hz = int(sys.argv[1]); count = int(sys.argv[2])
pulses = irReplay.readPulses("/tmp/pulses.txt")
msgs   = irReplay.splitMessages(pulses)
print("recording holds %d message(s), sending the first %d at %d Hz" % (len(msgs), count, hz))
keep = []
for msg, gap in msgs[:count]:
	keep += msg + ([gap] if gap else [])
pi = pigpio.pi()
if not pi.connected:
	print("cannot reach pigpiod"); sys.exit(1)
try:
	took = irReplay.send(pi, 18, keep, carrierHz=hz)
	print("sent %d pulses in %.3f s - watch the ac" % (len(keep), took))
finally:
	pi.stop()
PY
fi

# r: the whole recorded press, n times, at ONE carrier. This separates the two things b changes
# at once. b replays the press 11 times, once per frequency; m replays it ONCE. m fails and b
# works, so what b has is ATTEMPTS, not frequency diversity - and this measures that directly.
#    ./irTest.sh r 38000 12
if [ "$1" = "r" ]; then
	python3 - "${2:-38000}" "${3:-12}" "${4:-5}" <<'PY'
import sys, time
sys.path.insert(0, "/home/pi/pibeacon")
import pigpio, irReplay
hz = int(sys.argv[1]); n = int(sys.argv[2]); wait = float(sys.argv[3])
pulses = irReplay.readPulses("/tmp/pulses.txt")
msgs   = irReplay.splitMessages(pulses)
print("replaying the whole press (%d messages, %d pulses) %d times at %d Hz, %.0f s apart"
		% (len(msgs), len(pulses), n, hz, wait))
pi = pigpio.pi()
if not pi.connected:
	print("cannot reach pigpiod"); sys.exit(1)
try:
	for ii in range(n):
		took = irReplay.send(pi, 18, pulses, carrierHz=hz)
		print("   %2d/%d  sent in %.3f s   %s" % (ii + 1, n, took, time.strftime("%H:%M:%S")))
		if ii < n - 1:
			time.sleep(wait)
finally:
	pi.stop()
print("")
print("reacted on some attempt -> the link is MARGINAL: it is optical power and aim, not the")
print("   frequency and not the frame. Note WHICH attempt, that is the hit rate.")
print("reacted on none -> attempts are not what b has either, and something else differs")
PY
fi

# d: the scripted walk - on, temperature, the five fan speeds, the louvers, off - one setting
# moving per step so the ac's display can be followed line by line.
#    ./irTest.sh d          10 s between steps
#    ./irTest.sh d 18 5     gpio 18, 5 s between steps
if [ "$1" = "d" ]; then
	shift
	if [ ! -s /home/pi/pibeacon/irDemo.py ]; then
		echo "irDemo.py is missing or EMPTY on this rpi - send the plugin files to the rpis again"
		exit 1
	fi
	python3 -u /home/pi/pibeacon/irDemo.py "$@"
fi
