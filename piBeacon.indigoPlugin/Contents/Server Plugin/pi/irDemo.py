#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# irDemo  version 1.0
#
# Walks an AC through a scripted sequence of commands with a pause between each, so the unit can
# be WATCHED doing what it was told. One thing changes per step - the temperature, or the fan, or
# a louver - which is what makes a wrong step obvious: the display should follow the printed line.
#
# Each step is a COMPLETE state, because that is all an AC frame carries. The script keeps the
# running state and edits one field per step, exactly as a remote does.
#
# This exercises the encoder, the four message sequence and the emitter. It does NOT go through
# indigo, so it says nothing about the plugin's actions or device props - for that, drive the
# device from indigo and watch the same way.
#
# usage:
#    python3 irDemo.py                     the default walk on gpio 18, 10 s apart
#    python3 irDemo.py 18 5                gpio 18, 5 s apart
#    python3 irDemo.py 18 10 toshiba       the same shape for a toshiba unit
#    python3 irDemo.py louver              the louvers instead, both axes
#    python3 irDemo.py louver 18 5         ... on gpio 18, 5 s apart
#    python3 irDemo.py louver2             two positions per axis, 20 s apart to let them travel
#
# NO sudo: it reaches the gpio through the pigpiod socket, and killSudos kills anything whose
# command line holds "python" and "sudo".
#
# python2 AND python3 compatible, like every other program in this directory.
####################
from __future__ import print_function
import os
import sys
import time

try:
	import pigpio
except Exception:
	pigpio = None
try:
	import greeIR
except Exception:
	greeIR = None
try:
	import toshibaIR
except Exception:
	toshibaIR = None

VERSION	= "1.0"
GPIO	= 18
WAIT	= 10.
BRAND	= "gree"

# the walk. Each entry is (what to say, what to change) and everything else carries over, so one
# setting moves per step and the ac's display can be followed line by line.
STEPS = [
		# off first, so switching on is a transition that has to show - asking for a state the
		# unit is already in looks exactly like a step it ignored
		# 25 C here so that "temperature 20" two steps later is a real change and not a no-op
		("power OFF  (so step 2 shows)",	dict(power=False, mode="cool", temperature=25, fan="auto")),
		("power ON, cool, fan auto",		dict(power=True)),

		("temperature 20",					dict(temperature=20)),
		("temperature 21",					dict(temperature=21)),
		("temperature 23",					dict(temperature=23)),

		# the fan: byte 0 saturates at 3, so from "2" upwards only byte 6 of message 3 separates
		# these - which is the thing under test
		("fan silent",						dict(fan="silent")),
		("fan 1",							dict(fan="1")),
		("fan 2",							dict(fan="2")),
		("fan 3",							dict(fan="3")),
		("fan 4  (the top speed)",			dict(fan="4")),

		("power OFF",						dict(power=False)),
		]

# the louvers, both axes. Vertical is byte 4's low nibble, horizontal its high nibble - and the
# remote sends swingV "auto" together with the swing-auto bit in byte 0, so that step sets both.
STEPSLOUVER = [
		# NOTHING here touches the temperature or the fan - they are carried unchanged in every
		# frame, so anything that moves during this walk moved because of a louver
		("power OFF  (so step 2 shows)",	dict(power=False, swingV="last", swingH="off", swingAuto=0)),
		("power ON, louvers untouched",		dict(power=True)),

		("VERTICAL  up",					dict(swingV="up")),
		("VERTICAL  middle-up",				dict(swingV="middleUp")),
		("VERTICAL  middle",				dict(swingV="middle")),
		("VERTICAL  middle-down",			dict(swingV="middleDown")),
		("VERTICAL  down",					dict(swingV="down")),
		("VERTICAL  auto  (swings)",		dict(swingV="auto", swingAuto=1)),
		("VERTICAL  back to untouched",		dict(swingV="last", swingAuto=0)),

		("HORIZONTAL  max left   (facing the ac)",			dict(swingH="maxLeft")),
		("HORIZONTAL  left       (facing the ac)",				dict(swingH="left")),
		("HORIZONTAL  middle",				dict(swingH="middle")),
		("HORIZONTAL  right      (facing the ac)",				dict(swingH="right")),
		("HORIZONTAL  max right  (facing the ac)",			dict(swingH="maxRight")),
		("HORIZONTAL  auto  (swings)",		dict(swingH="auto")),
		("HORIZONTAL  off",					dict(swingH="off")),

		("power OFF",						dict(power=False)),
		]

# the short louver confirmation: two positions on each axis, far apart so the travel is obvious,
# and nothing but a louver moving per step. A vane takes longer than ten seconds to swing end to
# end, so this walk carries its own slower default.
STEPSLOUVER2 = [
		("power OFF  (so step 2 shows)",	dict(power=False, swingV="last", swingH="off", swingAuto=0)),
		("power ON, louvers untouched",		dict(power=True)),
		("VERTICAL  up",					dict(swingV="up")),
		("VERTICAL  down",					dict(swingV="down")),
		("HORIZONTAL  max left   (facing the ac)",			dict(swingH="maxLeft")),
		("HORIZONTAL  max right  (facing the ac)",			dict(swingH="maxRight")),
		("power OFF",						dict(power=False)),
		]

# name -> (steps, seconds between them). An explicit seconds argument still wins.
WALKS = {"basic":   (STEPS,        10.),
		 "louver":  (STEPSLOUVER,  10.),
		 "louver2": (STEPSLOUVER2, 20.)}


####-------------------------------------------------------------------------####
def sendGree(pi, pin, state, fan, dutyCycle=0.5):
	"""Sends one gree press - all four messages - and returns them for the log.

	Inputs:
	    pi (pigpio.pi): connected client
	    pin (int): gpio the ir led is on
	    state (bytearray): the state to command
	    fan (str): the fan it was built with, which byte 6 of message 3 needs
	    dutyCycle (float): carrier duty
	Outputs:
	    list: the four messages as hex strings
	"""
	greeIR.sendSequence(pi, pin, state, fan=fan, dutyCycle=dutyCycle)
	return [greeIR.stateToHex(m) for m in greeIR.buildSequence(state, fan=fan)]


####-------------------------------------------------------------------------####
def leadIn():
	"""Waits before the first send, so the run can be started here and watched at the ac.

	Seconds come from the IRLEADIN environment variable, 15 by default. irTest.sh does its own
	countdown and then sets IRLEADIN=0, so starting through it does not wait twice.

	Inputs:
	    none
	Outputs:
	    None
	"""
	try:	secs = float(os.environ.get("IRLEADIN", 15))
	except Exception:	secs = 15.
	if secs <= 0:	return
	print("== starting in {:.0f} s - go to the ac now".format(secs))
	while secs > 0:
		print("   ... {:.0f} s".format(secs))
		nap = 5. if secs > 5 else secs
		time.sleep(nap)
		secs -= nap
	print("== go")
	print("")


####-------------------------------------------------------------------------####
def main():
	"""Command line entry point: gpio, seconds between steps, brand."""
	args	= sys.argv[1:]
	walk	= "basic"
	if args and args[0] in WALKS:		# a walk name may come first: irDemo.py louver 18 10
		walk = args[0]
		args = args[1:]
	steps, wait	= WALKS[walk]
	pin		= GPIO
	brand	= BRAND
	duty	= 0.5
	if len(args) > 0:
		try:	pin = int(args[0])
		except Exception:	pass
	if len(args) > 1:
		try:	wait = float(args[1])
		except Exception:	pass
	if len(args) > 2:	brand = "{}".format(args[2]).strip().lower()
	if len(args) > 3:
		try:	duty = float(args[3])
		except Exception:	pass

	if args and args[0] not in ("18",) and not args[0].replace(".", "").isdigit() and walk == "basic":
		print("ERROR: '{}' is not a walk. Known walks: {}".format(args[0], ", ".join(sorted(WALKS))))
		return 1
	if pigpio is None:
		print("ERROR: the pigpio module is not installed on this rpi")
		return 1
	if brand not in ("gree", "toshiba"):
		print("ERROR: brand must be gree or toshiba, not '{}'".format(brand))
		return 1
	if brand == "gree" and greeIR is None:
		print("ERROR: greeIR.py is not on this rpi - send the plugin files to the rpis")
		return 1
	if brand == "toshiba" and toshibaIR is None:
		print("ERROR: toshibaIR.py is not on this rpi - send the plugin files to the rpis")
		return 1
	if not (0 < pin < 28):
		print("ERROR: {} is not a gpio number".format(pin))
		return 1

	print("irDemo v{}: {} \"{}\" walk on gpio {}, {} steps, {:.0f} s apart - about {:.0f} s in all".format(
			VERSION, brand, walk, pin, len(steps), wait, len(steps) * wait))
	print("WATCH THE AC: its display should follow each line below. One setting moves per step,")
	print("so a step it does not follow is the one to look at.")
	print("")
	print("Give it the whole run - {:.0f} s. A step that asks for what the unit ALREADY has looks".format(len(steps) * WAIT))
	print("exactly like a step it ignored, which is why this starts by switching off.")
	print("")
	print("LISTEN AS WELL AS WATCH - the ac BEEPS on every frame it accepts, and that separates")
	print("the two failures that look alike:")
	print("   beep, nothing changes -> the frame was accepted and applied; the field we moved is")
	print("                            not the one the unit reads for that setting")
	print("   no beep               -> not received at all: the carrier, the aim, or the frame")
	print("")
	leadIn()

	# The running state, edited one field per step, the way a remote holds its own settings.
	#
	# It starts with the louvers UNTOUCHED - swingV "last", swingH "off", byte 4 = 00 - so step 1
	# is byte for byte the command that is known to work. Setting them ("middle"/"middle", byte 4
	# = 44) was the only difference between this walk and that command, and the walk got no
	# reaction: a unit with no horizontal louver has no use for swingH. The louver steps below
	# therefore move swingV only and leave swingH off.
	now = dict(mode="cool", temperature=25, fan="auto", power=True,
				swingV="last", swingH="off", light=1)

	pi = pigpio.pi()
	if not pi.connected:
		print("ERROR: cannot reach pigpiod - is it running?")
		return 1
	try:
		for ii in range(len(steps)):
			label, change = steps[ii]
			now.update(change)
			if brand == "gree":
				state = greeIR.buildState(**now)
				msgs  = sendGree(pi, pin, state, now.get("fan", "auto"), duty)
				print("   {:2d}/{}  {:<30} {}   {}".format(
						ii + 1, len(steps), label, msgs[0], time.strftime("%H:%M:%S")))
				for extra in msgs[1:]:
					print("{}{}".format(" " * 40, extra))
			else:
				frame = toshibaIR.modeFanTemp(
							mode		= "off" if not now["power"] else now["mode"],
							temperature	= now["temperature"],
							fan			= now["fan"] if now["fan"] in ("auto","1","2","3","4","5") else "auto")
				toshibaIR.sendFrame(pi, pin, frame, dutyCycle=duty)
				print("   {:2d}/{}  {:<30} {}   {}".format(
						ii + 1, len(steps), label, toshibaIR.frameToHex(frame), time.strftime("%H:%M:%S")))
			if ii < len(steps) - 1:
				time.sleep(wait)
	except KeyboardInterrupt:
		print("\n   stopped")
	finally:
		try:	pi.stop()
		except Exception:	pass

	print("")
	print("done. Count the beeps: one per step means every frame was accepted, and any setting")
	print("that did not move is then a field question, not a reception one.")
	print("")
	print("Every step the ac followed is one more thing working end to end - the encoder,")
	print("the message sequence and the emitter. A step it ignored names what to look at:")
	print("   a fan step      -> the fan table in greeIR, and BYTE6FROMFAN - with it False every")
	print("                      press carries the same byte 6, which is the frame that worked")
	print("   a louver step   -> byte 4, which only message 1 carries")
	print("   all of them     -> the emitter or the aim, not the frames")
	return 0


if __name__ == "__main__":
	sys.exit(main())
