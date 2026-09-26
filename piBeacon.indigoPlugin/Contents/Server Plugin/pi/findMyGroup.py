#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
findMyGroup.py  -  Apple Find My (AirTag ...) group counter for beaconloop.py

Find My tags rotate their BLE mac (every 15 min near the owner, daily when separated), so they
can not be tracked as normal beacons. Instead every Find My mac is a "candidate"; candidates
with a strong smoothed RSSI are "members" (= in this house). memberCount only changes after
the new count held for stableSecs, so a mac rotation (old mac expires, new mac joins) is invisible.

Switched on/off in the parameters file (key missing = off):
  "findMyGroup": {
      "enable":                 "1",        # "0" / "1"
      "devId":                  "12345678", # indigo device that receives the states (0 = do not send)
      "joinRssi":               "-70",      # smoothed rssi to become a member
      "leaveRssi":              "-80",      # smoothed rssi to stop being a member (hysteresis)
      "expireSecs":             "10",       # no packet for xx secs -> mac gone (tags adv every ~2 secs)
      "stableSecs":             "60",       # new count must hold xx secs before memberCount changes
      "smoothN":                "5",        # median over last N packets
      "minPackets":             "3",        # packets needed before a mac can join
      "maxSlots":               "30",       # how many members may hold a slot (ceiling MAXSLOTS)
      "sendEverySecs":          "60",       # periodic update (trigger "time", batched with beacon msgs)
      "dropFromBeaconPipeline": "1",        # "1": Find My frames are not processed as beacons (no new-beacon spam from rotating macs)
      "calibrationLog":         "0",        # "1": write csv rows to temp/findMyGroup.csv (same columns as findmy_scan.py)
      "debug":                  "0",        # "1": summary + the find my frames, "2": + the rejected apple ones
      "debugMac":               "",         # only log frames whose mac contains this
      "logEverySecs":           "10"
  }

Calibration marker (labels a session, stays set until changed):
  echo "tag at street" > /home/pi/pibeacon/temp/findMyGroup.marker
  echo "" > /home/pi/pibeacon/temp/findMyGroup.marker      clears it
The text is written on ONE row when it changes, and restated with every repeated header block -
not on every row, which would be the same sentence a thousand times. A reader FORWARD-FILLS it:
a blank marker cell means "same as above". "-" means the marker was cleared here.

Message to the plugin (sensors path, like the BLE sensors):
  {"sensors": {"BLEfindMyGroup": {devId: {
      "numberOfActive", "numberOfActiveRaw", "numberOfWeak", "numberOfCandidates", "strongestRSSI",
      "numberOfActivePrevious", "numberOfActiveChanged", "trigger": "count"|"members"|"time",
      "members":        {"01": {"mac":.., "rssi":.., "distanceIndicator":.., "battery":.., "appleTypes":..,
                              "hintByte":.., "tagId":..}, "02": {..}},
      "membersHistory": {"01": [macThatLeft, "YYYY-mm-dd HH:MM:SS"], ...}

Named fields, not a positional list: the same structure is written to temp/findMyGroup.state,
which is read by a person whenever the count looks wrong, and ["C7:8B:..", -68, "nearby", "low",
"07|12"] needs this file open beside it to be read at all. The state file is indented for the
same reason.
  }}}}

THE SLOT NUMBERS ARE ASSIGNED HERE, not in the plugin, so that this file, temp/findMyGroup.state
and the indigo member devices (one per slot, "findmy_NN") all say the same "01". A mac KEEPS its slot for as
long as it stays a member; when it goes, the slot is freed and membersHistory records which mac
left it and when. A new mac takes the lowest free slot.
Slots are STICKY on purpose. Ordering them by signal instead would renumber every time two
devices swap rssi rank, and each of those renumbers would look exactly like a rotation in the
history - which is the one thing the history exists to show. The cost is that "01" is not the
nearest device, just the longest-standing one.
The map survives a beaconloop restart: it is read back from temp/findMyGroup.state at startup, so
a tag that is still here keeps its slot number across the restart.
Slot count is MAXSLOTS below and MUST match _GlobalConst_findMyMemberStates in the plugin's
piBeaconConstants.py - the plugin will not make a member device for a slot above that.
"members" still lets several RPis be combined: a tag carries the same mac on every rpi at the
same moment, so the union of the macs is the house count (the slot numbers are per rpi).

WHAT ACTUALLY TURNS UP IN THE COUNT - measured in a real house, not assumed:
  - AIRTAGS and other find my accessories. An airtag a few cm from the rpi read about -32 dBm -
    ON THE DONGLE OF THE DAY, and that number does NOT travel. Measured 2026-09-25 on two rpis
    whose scan radios are the same later model (oui 5C:F3:70): NOTHING EVER READ STRONGER THAN
    -59 dBm, on either machine, across ~3500 packets - 886 of pi5's samples sat at exactly -59
    against 9 at -60. That is the top of that dongle's scale, not a measurement, and everything
    closer than it is indistinguishable.
    SO AN ABSOLUTE LEVEL MEANS NOTHING WITHOUT THE RADIO IT CAME FROM. "-59 must be right next to
    the rpi" cost an hour: it was read as a regression against the -32 above, and both numbers
    were right on their own hardware. joinRssi and leaveRssi are per house for exactly this
    reason - with these dongles the whole usable range is about 11 dB below the ceiling.
  - AIRPODS: one case sent apple types 07 (proximity pairing) AND 12 in the SAME frame, which is
    why the prefilter in beaconloop must be "FF4C00" and not "FF4C0012".
  - NOT IPHONES, NOT MACS, however close they sit. Two iphones 5 cm from the rpi, online and then
    with wifi and cell switched off, never produced a find my frame - the strongest signal of any
    candidate stayed around -66 while the tags next to it read -32.
Live apple devices ARE on the air the whole time, just not here: they advertise nearby-info (0x10),
handoff (0x0C), airplay (0x09/0x16) from RESOLVABLE PRIVATE addresses, first octet 40-7F. Find my
uses a key-derived RANDOM STATIC address, first octet C0-FF. Different messages, different address
space - which is also why appleTypes never shows 0x10 beside 0x12 and cannot tell a phone from a
tag. Offline finding carries LOST and OFFLINE things; a phone with a network of its own reports
its position over the internet and has no reason to shout.
So memberCount is close to "find my accessories in the house" already, and does not need phones
subtracted from it - machinery to do that was built, found to be subtracting nothing, and removed.

WHAT THE RSSI CAN AND CANNOT TELL YOU - measured, one rpi, one dongle:
  - it is FLAT under about a metre. 3 cm and 1 m read the same. A receiver stops discriminating
    at close range, so no threshold in that region can tell "on the desk" from "in the room".
  - beyond that, roughly 3 dB per further metre.
  - the ABSOLUTE numbers belong to the dongle, not to the protocol: -62 touching the rpi and -80
    at four metres on the radio measured here. joinRssi of -55 or -60 would mean "never counted"
    on that hardware while looking like a reasonable setting.
Anything built on rssi has to be calibrated against the radio it will run on, and cannot resolve
distances inside the flat zone at all.

py2 / py3 compatible, no extra libraries.
"""

import os
import time
import datetime
import json

import piBeaconUtils as U
import piBeaconGlobals as G

SENSOR_NAME = "BLEfindMyGroup"
MAXSLOTS    = 60		# THE CEILING, not the setting - the group device's "maxSlots" picks the number
						# actually in use and is clamped to this. Must match _GlobalConst_findMyMemberStates
						# in the plugin's piBeaconConstants.py: both sides hand out and expect the SAME slot
						# numbers, so a slot this side invents that the plugin will not create is a tag with
						# nowhere to go.
						# WAS 20, and all twenty filled in ten hours - the twenty-first mac, which could have
						# been a real tag arriving, got no slot and no device at all. The cap silently
						# deciding which tags exist is a worse failure than a long device list.
						# HEADROOM IS NOT A FIX: what filled them was nearby apple devices hovering on
						# joinRssi, and they will fill sixty just as happily. The cures for that are the
						# delete-when-down housekeeping and counting only separated macs.
						# STILL TWO DIGITS at 60, which the "{:02d}" slot format and every "01".."NN" state
						# quietly depend on. Going past 99 is not a constant change
SLOTHOLDSECS = 300.		# a slot stays reserved for its mac this long after it expires - see assignSlots
MINSENDSECS  = 5.		# floor between two "members" triggers - see the send logic in tick()
MACHISTORY   = 5		# macs kept per slot in the state file - must match the plugin
MAXWEAK      = 40		# most "heard but not counted" macs carried in one message - see states()
PERSISTSECS  = 200.		# how often the state file and the calibration csv are also copied out of the
						# tmpfs to the pibeacon dir - see send(). 200 s is 432 writes a day of a file a few
						# kB long, which an SD card does not notice, and it caps what a reboot can lose
HEADEREVERY  = 600.		# how often the csv column header is repeated - see writeCalibrationRows()
CSVMAXBYTES  = 200 * 1024	# the calibration csv is CAPPED, oldest rows dropped - see trimCsv().
						# temp/ is a 2 MB tmpfs shared with the state file, so an uncapped log there would
						# eventually fill it and take findMyGroup.state down with it
# A TAG KEEPS ITS tagId ACROSS A MAC ROTATION - see matchRotation(). The mac is the only thing
# that joins two rPis at one instant; the tagId is the only thing that joins one rPi across time,
# and the plugin needs both to keep an indigo device on the same physical tag when the mac changes.
ROTGAP       = 15.		# the new mac's FIRST packet must fall this close to the old one's LAST.
						# MEASURED, not guessed. 6 s refused 23 real rotations in ten minutes with gaps of
						# 6.2 to 13.3 s, and the next candidate up was 55.7 - an unrelated mac. The whole band
						# from 13.3 to 55.7 was EMPTY, so the threshold sits in open space rather than on a
						# judgement call. The gap is not the tag's doing: the rPi does not hear every packet,
						# so the old mac's last HEARD frame is already seconds before it really stopped and the
						# new mac's first HEARD frame is seconds after it really started. Both errors add.
						# WIDENING IT CANNOT MAKE MATCHING WORSE by much: more candidates reach the later
						# tests, and when two of them still fit, matchRotation refuses as before
ROTCONFIRM   = 20.		# HOW LONG THE OLD MAC MUST STAY SILENT AFTER THE NEWCOMER APPEARED, before its
						# lineage is handed over. This REPLACED a 3 s "is it quiet" test taken at the instant
						# of the join, and the reason is in the log that test left behind: EVERY refusal it ever
						# wrote was between 0.1 and 2.7 s. It was throwing out candidates FOR HANDING OVER
						# CLEANLY - a real rotation is seamless, so the tighter the handover, the more certain
						# the old test became that it could not be one.
						# SILENCE AFTERWARDS IS THE EVIDENCE, not silence at one instant. A mac that never went
						# anywhere carries on advertising and takes itself out of the running; one that really
						# rotated never speaks again. Measured: a tag was robbed of its lineage at 18:48:48 and
						# kept transmitting for seven more minutes - waiting sees that, an instant cannot.
						# IT ALSO SETTLES "could be any of ..", which had become the commonest refusal of all.
						# Two candidates are rarely both really gone - usually one is merely quiet, and 479 s
						# later it turns up again on its own mac. Waiting lets it eliminate itself.
						# 20 s, because the device this was built for gaps past ten seconds between
						# advertisements often enough to expire spuriously - see the age_s resets in the csv.
						# THE NEWCOMER IS HELD OUT OF members while it waits, so the plugin never sees a member
						# without a lineage and cannot give it a slot of its own. At sendEverySecs 60 the whole
						# wait usually falls inside one send and never reaches indigo at all
ROTSPOKE     = 1.		# slack on "spoke again": the candidate's last packet time must advance by MORE
						# than this to count as still being on the air. Without it the comparison can fire on
						# the very packet the claim was made from
ROTTIE       = 3		# dBm. TWO NEWCOMERS, ONE LINEAGE - the mirror of "could be any of", and it exists
						# only because waiting makes it possible: claims now overlap in time where each used to
						# be settled on the spot. Seen at 21:00:04.9, where a stranger claimed the airpods
						# case's lineage 1.4 s before the case's own next mac did. The closer smoothed signal
						# takes it, and only if it is closer by MORE than this - inside it neither gets the
						# lineage, which is the old refuse-rather-than-guess rule applied in a new place.
						# ONLY CONSULTED BETWEEN CLAIMANTS OF THE SAME KIND. An exact apple-type match
						# settles it outright first - see resolveRotClaims - because signal here is
						# quantised to 3 dB steps by the dongle, so "0 vs 0 dBm off" is the normal case
						# for two devices in one room and not a coincidence worth refusing over
ROTBACK      = 120.		# a lineage that just moved A -> B may not move B -> A within this. A rotation
						# is ONE WAY, so a reversal is two wrong matches, not two right ones - and it is the
						# shape a pair of lookalike tags makes when they keep stealing each other's identity
ROTRSSI      = 8		# dBm the smoothed signal may differ by: the tag has not moved in that second
CARRYBACK    = 120.		# A MAC COMING BACK INSIDE THIS IS THE SAME MAC, and keeps the "first" and the
						# apple types it had before it went. NOT cosmetic - measured on a real miss:
						# an airpods case sent one frame at 21:45:00.8, was not heard again for 12 s,
						# tripped expireSecs 10 before it had even joined, and came back 2 s later as a
						# candidate born at 21:45:12.8. matchRotation measures the gap from "first", so
						# THE REBUILD MOVED THE GAP BY TWELVE SECONDS - from a certain pass to sitting on
						# top of ROTGAP 15 - and the rotation was refused. Its accumulated types went the
						# same way, which is what inverts the subset test ("types 07|12 not within 12").
						# WHY NOT JUST RAISE expireSecs: what it races is RECEPTION, not the tag. The rpi
						# does not hear every advertisement and the scan radio is shared, so the observed
						# gap runs from 2 s to a whole 10 s cycle on one device in one minute. Any value
						# is wrong on a busier minute, and a value safely above them all would leave a tag
						# that really went sitting "here" for just as long. This does not care how long
						# the gap was: the mac is the mac, and only "last" moves.
						# 120 s, the same as GONEKEEP and for the same reason - beyond that a returning mac
						# really has been away, and an age measured from before it went says nothing
GONEKEEP     = 120.		# how long an expired lineage can still be inherited BY A DIFFERENT MAC
OWNKEEP      = 2 * 86400.	# and how long a mac is remembered as owning ITS OWN lineage. FAR LONGER,
						# and it can be: this one is only ever matched by the identical mac, so there is no
						# guess in it and nothing to get wrong. GONEKEEP has to stay short for the opposite
						# reason - it is the pool somebody ELSE inherits from, and a rotation happens within
						# seconds, so a long memory there only breeds ambiguity.
						# MEASURED: airpods earpieces stop advertising and come back ON THE SAME MAC every
						# 3 to 4 minutes. At GONEKEEP every one of those returns found its own lineage
						# already thrown away, so it re-entered matchRotation as a mac nobody had ever seen
						# and competed for OTHER tags' lineages - which is where the "could be any of .."
						# refusals were coming from. They were not ambiguous tags, they were amnesiac ones.
						# TWO DAYS, because a SEPARATED tag rotates only once a DAY - anything shorter than
						# that guarantees amnesia for precisely the devices that rotate least, and an
						# earpiece left in its case overnight is the ordinary case, not the awkward one.
						# It is bounded by OWNMAX rather than by time alone, and it is written to the state
						# file, so a beaconloop restart does not throw the whole thing away
OWNMAX       = 500		# most macs remembered that way. A house has nothing like this many, but the
						# air outside it does - passing phones and neighbours' tags all get an entry - and a
						# dict with no ceiling is a leak with a long fuse. Oldest goes first
BATTERY     = {0: "full", 1: "medium", 2: "low", 3: "critical"}
CSV_FIELDS  = ["timestamp", "host", "mac", "distanceIndicator", "status", "hintByte", "appleTypes", "battery", "packets",
               "rssi_median", "rssi_min", "rssi_max", "rssi_smoothed", "member", "age_s", "marker",
               "raw_len", "raw_hex"]
			   # NO "hci" COLUMN. It dates from when an rpi ran several ble dongles as equals; the
			   # radios have had fixed ROLES for a long time now - one scans, and a ble5 dongle
			   # only listens - so the column said nothing that host did not already say, and
			   # findMyGroup never had a per-frame hci to put in it anyway. It was written empty
			   # for its whole life. Do not add it back without a reason that is about the data.
			   # "hintByte" is the last byte of the separated payload - see parseFindMy.
			   # RAW LAST, AND THE LENGTH BEFORE IT. raw_hex is the WHOLE advertisement of the most
			   # recent frame from this mac, as hex - everything the other columns were decoded out
			   # of, kept so a theory about a byte can be tested against rows already written
			   # instead of waiting for the tag to come round again with new logging in place.
			   # The length is its own column and comes first because it is the thing you filter
			   # on: 25-byte payloads are the separated frames and the only ones with a hint byte,
			   # 2-byte ones are nearby. It is BYTES, not hex characters.
			   # Last on the row on purpose - it is the longest field by far, and a variable-width
			   # column in the middle makes every row after it unreadable in a terminal
			   # ONE TIME COLUMN, not two. "epoch" was here so findmy_merge.py could bin without
			   # parsing a date; timestamp now carries tenths of a second, which is finer than any
			   # binning these rows are used for, so merge parses it and the duplicate is gone.
			   # findmy_merge.py reads BY NAME, so column order here does not matter to it


# EVERY TEXT COLUMN IS 4 CHARACTERS, which is what makes the rows scannable - and the three that
# do not fit in 4 are ABBREVIATED rather than widened. Padding alone would have aligned nothing:
# "separated" is 9, "05|0C|10|12" is 11 and "critical" is 8.
# NOTHING IS LOST BY IT. raw_hex on the same row is the whole frame these three were decoded out
# of, so the abbreviation is a convenience and never the only record - which is exactly what
# makes abbreviating acceptable here and would not have been before raw_hex existed.
#   distanceIndicator  sep  separated - the tag believes its owner is NOT with it
#                      near nearby    - it believes its owner is
#                      lNN  a payload of NN bytes that is neither
#   status             2 hex digits, or blank when the frame carried none
#   hintByte           the same, and blank for a mac that only sends the nearby payload
#   appleTypes         ONE LETTER PER CONTINUITY TYPE, always in this order, so the letters
#                      present are the set: a=05 airdrop, p=07 proximity pairing, h=0C handoff,
#                      n=10 nearby info, f=12 find my. "ahnf" is a phone or a mac, "pf" an
#                      airpods case, "f" alone a tag and nothing else. An unknown type adds "?".
#                      f is in every row by construction - these are find my frames - and it is
#                      kept anyway so the column reads as a set rather than as "the others"
#   battery            full / med / low / crit
#   packets / age_s / raw_len  counts, ZERO padded - a count has no sign and a leading zero
#                      reads as one number, where a leading space reads as a missing field
#   rssi_median / rssi_smoothed   -xx.y, space padded. NOT whole numbers: a median over an even
#                      number of packets is a half and strongHalf averages
#   rssi_min / rssi_max  single measured packets, so genuinely whole. Space padded, no decimal
#   marker             the calibration annotation, which changes as you move the tag about
# NOT PADDED, AND THEY DO NOT NEED TO BE: timestamp is a fixed 21, mac a fixed 17, and host is
# CONSTANT WITHIN A FILE - one rpi writes one file - so its column is already the same width on
# every row of it. Padding them would only add bytes to every row of a file that runs all day.
# raw_hex is last and free to be any length, which is why it was put last.
CSVWIDTH  = {"distanceIndicator": 4, "status": 4, "hintByte": 4, "appleTypes": 4, "battery": 4,
			 "packets": 3, "rssi": 6, "rssi_minmax": 4, "member": 1, "age_s": 4,
			 "marker": 8, "raw_len": 2}
CSVBATT   = {"full": "full", "medium": "med", "low": "low", "critical": "crit"}
CSVTYPE   = {0x05: "a", 0x07: "p", 0x0C: "h", 0x10: "n", 0x12: "f"}


def padCsv(x, n):
	"""A csv text column left aligned in n characters. "" for None.

	THESE ROWS ARE READ IN A TERMINAL far more often than by a parser. Unpadded, "nearby" sat
	under "separated" and "low" under "critical", so every column to the right of them moved on
	every row and the file could not be scanned by eye at all.
	PADDED, NEVER TRUNCATED: n is a minimum, not a maximum. A column that cuts its own data down
	to look tidy is not a calibration log, so a value longer than its width simply pushes that
	one row out and every other row stays lined up.
	ANYTHING THAT PARSES THIS MUST strip(): the spaces are inside the csv value, not between
	fields. The header row is NOT padded, because it is read by name.
	"""
	return "{:<{}}".format("" if x is None else x, n)


def indCsv(indicator):
	"""distanceIndicator abbreviated to 4: separated -> sep, nearby -> near, lenNN -> lNN."""
	ii = "{}".format(indicator or "")
	if ii == "separated":	return "sep"
	if ii == "nearby":		return "near"
	if ii[:3] == "len":		return "l" + ii[3:][:3]
	return ii[:4]


def battCsv(word):
	"""battery abbreviated to 4: full / med / low / crit. Anything unexpected is cut to 4."""
	ww = "{}".format(word or "")
	return CSVBATT.get(ww, ww[:4])


def typesCsv(codes):
	"""The apple continuity types as one letter each, in code order: 05 07 0C 10 12 -> a p h n f.

	FOUR CHARACTERS FOR THE COMMON CASES and five for the rare all-five one, against 11 for
	"05|0C|10|12". The letters are a SET, not a sequence - which types this mac has been seen
	sending, accumulated over its whole life, because a device does not put them all in one frame.
	An unrecognised type adds "?" rather than being dropped: a type nobody has a letter for is
	the one worth noticing, and raw_hex on the same row has its code.
	"""
	out = ""
	for t in sorted(codes or []):
		out += CSVTYPE.get(t, "?")
	return out


def rssiCsv(v):
	"""An rssi written as -xx.y, right aligned in CSVWIDTH["rssi"]. "" for None.

	MEDIAN AND SMOOTHED ARE NOT INTEGERS and never were: a median over an even number of packets
	is a half, and strongHalf averages. Written raw they came out as "-59" on one row and
	"-62.5" on the next, which is two different column widths AND two different apparent
	precisions for the same measurement. One decimal everywhere says what the number actually is.
	NOT ROUNDED TO INTEGERS to tidy it, because half a dB is inside what these rows are for: the
	whole point of the calibration log is comparing levels that differ by a few dB.
	rssi_min and rssi_max are left alone - they are single measured packets and genuinely whole.
	"""
	if v is None:	return ""
	try:	return "{:>{}.1f}".format(float(v), CSVWIDTH["rssi"])
	except Exception:	return ""


def numCsv(v, n):
	"""A non-negative count, ZERO padded to n digits: 842 -> "0842". "" for None.

	ZEROS AND NOT SPACES, which is the difference between a count and a measurement here. A
	leading space in a csv field reads as a missing value at a glance; a leading zero reads as
	part of the number, which is what it is. Nothing negative is ever written through this.
	n is a minimum: 100000 seconds is still written in full rather than cut to fit.
	"""
	if v is None:	return ""
	try:	return "{:0{}d}".format(int(v), n)
	except Exception:	return ""


def intCsv(v, n):
	"""A whole signed number right aligned in n - rssi_min and rssi_max. "" for None."""
	if v is None:	return ""
	try:	return "{:>{}d}".format(int(v), n)
	except Exception:	return ""


def median(values):
	vv = sorted(values)
	n = len(vv)
	if n == 0: return None
	if n % 2: return vv[n // 2]
	return (vv[n // 2 - 1] + vv[n // 2]) / 2.


def parseFindMy(advHex):
	"""advHex: AD structures as uppercase hex (beaconloop hexstr[14:-2]).
	Returns (indicator, statusByte, hintByte, appleTypes) for a Find My advertisement (Apple 0x004C,
	type 0x12), else None. indicator: "separated" (25 byte payload), "nearby" (2 byte payload) or
	"lenNN". appleTypes is EVERY continuity type in the frame, find my included.

	IT IS AN INDICATOR OF DISTANCE FROM THE OWNER, NOT A DISTANCE FROM THIS RPI - hence the name.
	"nearby" means the tag believes its owner's phone is with it, "separated" means it does not and
	is broadcasting the rotating key so any passing apple device can report where it is. The
	distance from THIS rpi is worked out from rssi, in the plugin, and the two are independent: a
	separated tag can be on the desk here, a nearby one two rooms away.

	THERE IS NO DEVICE TYPE IN THIS FRAME and there is not meant to be: offline finding works by
	every apple device relaying sightings of lost things, so an advertisement that said "iphone",
	or carried anything stable, would let anyone with a scanner follow people around. The 22 key
	bytes rotate every 15 min and are deliberately uncorrelatable with the previous set, which is
	why they are read past and thrown away here.
	What is left is the status byte - bits 7-6 are the battery level and the other SIX HAVE NO
	CONFIRMED MEANING, so statusBits() prints them raw rather than inventing labels - and the HINT
	byte - the last of the 25, and
	the only field published work has no explanation for beyond "0x00 on ios reports". It is
	carried out to the calibration csv for exactly that reason: it is the one byte that might
	separate a tag from a phone, and the only way to find out is to log it next to devices whose
	identity is known."""
	try:
		data = bytearray.fromhex(advHex)
	except Exception:
		return None
	i     = 0
	found = None
	types = []
	while i < len(data):
		ln = data[i]
		if ln == 0 or i + 1 + ln > len(data): return None
		adType = data[i + 1]
		val    = data[i + 2:i + 1 + ln]
		if adType == 0xFF and len(val) >= 4 and val[0] == 0x4C and val[1] == 0x00:
			j = 2
			while j + 2 <= len(val):
				t, l = val[j], val[j + 1]
				v = val[j + 2:j + 2 + l]
				# EVERY apple continuity type in this frame, not just find my. One manufacturer
				# blob can carry several, and which ones a mac sends is the strongest hint at what
				# it IS that costs nothing to collect: 0x07 proximity pairing carries a model id,
				# 0x10 nearby info comes from a real device rather than a tag, 0x0C handoff and
				# 0x05 airdrop likewise. Walking past them and keeping only 0x12 threw that away
				types.append(t)
				if t == 0x12 and found is None:
					indicator = {25: "separated", 2: "nearby"}.get(l, "len{}".format(l))
					# payload: status, 22 key bytes, a byte with the top 2 bits of the key, hint.
					# The 2 byte nearby payload stops after the status, so it has no hint at all
					hint = v[24] if len(v) >= 25 else None
					found = (indicator, (v[0] if len(v) > 0 else None), hint)
				j += 2 + l
		i += 1 + ln
	if found is None: return None
	return found[0], found[1], found[2], types


def appleTypesIn(advHex):
	"""The apple continuity types in a frame, find my or not. DEBUG ONLY - it exists so the log can
	say what a rejected frame actually was, instead of leaving it as "something apple".

	Inputs:
	    advHex (str): AD structures as uppercase hex
	Outputs:
	    list: the type bytes, in the order they appear
	"""
	out = []
	try:
		data = bytearray.fromhex(advHex)
	except Exception:
		return out
	i = 0
	while i < len(data):
		ln = data[i]
		if ln == 0 or i + 1 + ln > len(data): break
		val = data[i + 2:i + 1 + ln]
		if data[i + 1] == 0xFF and len(val) >= 4 and val[0] == 0x4C and val[1] == 0x00:
			j = 2
			while j + 2 <= len(val):
				out.append(val[j])
				j += 2 + val[j + 1]
		i += 1 + ln
	return out


def strongHalf(values):
	"""The median of the STRONGER half of the readings - what a find my mac's signal actually needs.

	A tag does not produce one clean rssi. Measured on an airtag 24 cm from the rpi, the same mac
	in the same second:
	    20:41:17.1  -68      20:41:17.2  -24
	    20:41:19.1  -68      20:41:19.1  -24
	The weak copies come every couple of seconds whatever the distance; the strong ones track it.
	CAUSE, confirmed: this rpi scans with TWO radios - a ble4 dongle and a ble5 listener - and
	beaconloop merges both into one message stream with nothing to say which heard what. The two
	do not agree on rssi, and the weaker one barely varies with distance, so every mac arrives
	here as two interleaved series.
	The window is therefore BIMODAL, and a plain median lands on whichever radio sent more packets.
	It scored that tag at -82 while it sat next to the rpi, put it below joinRssi, and dropped it
	out of the members.
	It is NOT a parsing bug, which was the first guess: extAdvToLegacyHex in beaconloop reads the
	extended report's rssi at byte 13 of the report, which is the spec offset (tx power is 12), and
	it round-trips correctly. The ble5 dongle simply reports a level that barely moves - it also
	hears far fewer packets than the ble4 radio, so it is the weaker receiver in both senses.
	NOTE FOR ANYTHING ELSE READING RSSI: this pooling is not specific to find my. Any beacon or
	sensor whose distance or presence comes from rssi on a multi-radio rpi is averaging two radios
	that disagree. Nothing here can fix that - the source is not in the stream - it is only worked
	around by preferring the stronger readings.
	The strongest reading is the meaningful one for "how close is this": the weak copies are
	attenuated versions of the same transmission. Taking the median of the stronger half rather
	than the single maximum keeps one freak reading from carrying the decision.

	Inputs:
	    values (list): the recent rssi readings
	Outputs:
	    float or None: the statistic, None for an empty list
	"""
	if not values: return None
	vv = sorted(values, reverse=True)
	return median(vv[:max(1, len(vv) // 2)])


class FindMyGroup(object):

	def __init__(self):
		self.enabled                = False
		self.devId                  = "0"
		self.joinRssi               = -70.
		self.leaveRssi              = -80.
		self.expireSecs             = 10.
		self.stableSecs             = 60.
		self.smoothN                = 5
		self.minPackets             = 3
		self.maxSlots               = 30
		self.sendEverySecs          = 60.
		self.dropFromBeaconPipeline = True
		self.calibrationLog         = False
		self.rssiStat               = "strong"
		self.debug                  = 0		# the EFFECTIVE level - the file wins over the dialog
		self.debugParam             = 0		# what the parameters file (ie the device dialog) asked for
		self.debugMac               = ""
		self.lastDebugCheck         = 0.
		self.debugFiles             = [G.homeDir + "temp/findmy.debug", G.homeDir + "temp/findMyGroup.debug"]
		self.logEverySecs           = 10.
		# ONE file, fixed name, beside the state file. Not /var/log and not a file per day: it is
		# read with "cat" while standing next to the rPi, it is written by the pi user without
		# any root dance, and it is size-capped rather than age-cleaned, so there is nothing to
		# sweep up. master is told NOT to delete it when it empties temp/
		self.csvFile                = G.homeDir + "temp/findMyGroup.csv"
		self.markerFile             = G.homeDir + "temp/findMyGroup.marker"
		self.stateFile              = G.homeDir + "temp/findMyGroup.state"
		# temp/ IS A TMPFS: writing there every send costs no SD wear but does not survive a
		# reboot, so the same content goes to the pibeacon dir every PERSISTSECS and is read back
		# when temp/ comes up empty. Losing 5 minutes of it is fine; losing the whole trail is not
		self.persistFile            = G.homeDir + "findMyGroup.state"
		# THE CALIBRATION LOG GOES OUT THE SAME WAY, and it needs it more than the state file does.
		# The state file is rebuilt within seconds by the tags themselves; the csv is a TRAIL, and a
		# row that is not written again is gone. A reboot empties the tmpfs and took the lot.
		# Copied only when it has actually changed - see persistCsvFile()
		self.persistCsv             = G.homeDir + "findMyGroup.csv"
		self.reset()
		self.restoreSlots()
		# BEFORE ANYTHING CAN APPEND. A freshly empty temp file copied out over a full one would
		# finish the job the reboot started
		self.restoreCsv()

	def reset(self, now=None):
		if now is None: now = time.time()
		self.cands          = {}
		self.stableCount    = 0
		self.previousCount  = 0
		self.rawCount       = 0
		self.pending        = 0
		self.pendingSince   = now
		self.lastChange     = 0.
		self.lastTick       = 0.
		self.lastSend       = now
		self.lastLog        = now
		self.lastPersist    = 0.
		self.lastRotWhy     = []	# why matchRotation turned each candidate down - see logRot()
		self.lastCsvCopy    = (0, 0.)		# size and mtime of the csv as it was last copied out
		self.lastHeader     = 0.
		self.marker         = ""
		self.markerDue      = False		# the marker changed and has not been written to a row yet
		self.startTime      = now
		self.startupSent    = False
		self.lastMemberSet  = None		# the macs in the last message, see the "members" trigger
		self.slots          = {}	# "01".."50" -> mac currently in that slot
		self.slotHistory    = {}	# "01".."50" -> [[mac that left it, "YYYY-mm-ddTHH:MM:SS"], ...]
									# NEWEST FIRST, at most MACHISTORY of them. Goes out in the state
									# file as "membersHistory" and comes back through restoreSlots()
		self.slotHold       = {}	# "01".."50" -> [mac, freedAt] - expired, slot RESERVED for it
		self.tagIdOf        = {}	# mac -> tagId. THE LINEAGE, which survives a mac rotation
		self.goneTags       = {}	# mac -> lineage of an expired mac, inheritable for GONEKEEP
		self.ownTag         = {}	# mac -> ITS OWN lineage, kept OWNKEEP for an exact return
		self.rotLast        = {}	# tagId -> (fromMac, toMac, when) of its last move - see ROTBACK
		# mac -> the lineages it MIGHT be the continuation of, waiting for ROTCONFIRM of silence
		# from them before one is handed over. Deliberately NOT in the state file: a claim is
		# seconds old and means nothing after a restart, and reviving one would hand a lineage
		# over on evidence nobody can check any more
		self.rotPending     = {}
		# mac -> what a RETURNING mac takes back: {"first", "last", "types"}. Separate from ownTag
		# on purpose and NOT in the state file. ownTag is the lineage memory and is only written
		# for a mac that HAD a lineage - and the case this exists for is a mac that expired before
		# it ever joined, which has none. Kept CARRYBACK, so it is bounded by the macs heard in the
		# last two minutes rather than by OWNMAX
		self.macCarry       = {}
		self.nextTagId      = 1		# NEVER REUSED. A small reused pool - the slots - is ambiguous:
									# slot 03 an hour from now is a different tag, and that is exactly the
									# doubt this is meant to remove. Persisted in the state file

	# ------------------------------------------------------------ slots
	def restoreSlots(self):
		"""Reads the slot map back from the state file, so a restart does not renumber the house.

		The macs rotate anyway, but a tag that is still here comes back within seconds and keeps
		the number indigo already has for it. Anything that does NOT come back is freed by the
		first assignSlots() after the warm-up, and is recorded in the history then - which is
		true: it went while we were not looking.

		THE TEMP FILE IS PUT BACK HERE, not just read past. temp/ is a tmpfs so a reboot empties
		it, and reading the pibeacon-dir copy while leaving temp/findMyGroup.state missing meant
		the file everybody looks at - "cat temp/findMyGroup.state" is the first thing anyone does -
		did not exist until the first send, up to sendEverySecs later. Nothing else copies it:
		master only spares the name from its wipe, it does not restore it.
		"""
		try:
			if not os.path.isfile(self.stateFile) and os.path.isfile(self.persistFile):
				U.copyFile(self.persistFile, self.stateFile)
				U.makeOwnFileWritable(self.stateFile)
				U.logger.log(20, "findMyGroup temp state file was gone (reboot?), restored from {}".format(self.persistFile))

			old = U.readJson(self.stateFile)[0]
			src = self.stateFile
			if not isinstance(old, dict) or not old.get("members") and not old.get("membersHistory"):
				# the temp file is there but says nothing - first ever start, or it was truncated.
				# The pibeacon-dir copy is at most PERSISTSECS behind
				old = U.readJson(self.persistFile)[0]
				src = self.persistFile
			if not isinstance(old, dict): return
			mm = old.get("members", {})
			if isinstance(mm, dict):
				for slot in mm:
					try:
						# dict since the mac/rssi/distance/... rename; a state file written by an
						# older version still has the plain list, and a restart across the
						# upgrade should not throw the slot map away
						if   isinstance(mm[slot], dict):						self.slots[slot] = mm[slot].get("mac", "")
						elif isinstance(mm[slot], list) and len(mm[slot]) > 0:	self.slots[slot] = mm[slot][0]
						if self.slots.get(slot, "") == "":						self.slots.pop(slot, None)
						# the lineage comes back with the mac: a tag still here re-joins on the SAME mac
						# within seconds, and the indigo device must not be told it is a different tag
						# just because this program restarted
						if isinstance(mm[slot], dict) and mm[slot].get("tagId") is not None:
							self.tagIdOf[mm[slot].get("mac", "")] = int(mm[slot]["tagId"])
					except Exception:	pass
			hh = old.get("membersHistory", {})
			if isinstance(hh, dict):
				for slot in hh:
					h = hh[slot]
					# a list of [mac, when] pairs; a single pair is what versions before .56 wrote
					if   isinstance(h, list) and h and isinstance(h[0], list):	self.slotHistory[slot] = h[:MACHISTORY]
					elif isinstance(h, list) and len(h) > 1:					self.slotHistory[slot] = [list(h)]

			# NEVER BACKWARDS, and never below a lineage that is already out there: a reused tagId
			# would look to the plugin like a rotation of whatever held it last
			try:	self.nextTagId = max(int(old.get("nextTagId", 1)), self.nextTagId)
			except Exception:	pass
			for mac in self.tagIdOf:
				if self.tagIdOf[mac] >= self.nextTagId:	self.nextTagId = self.tagIdOf[mac] + 1

			# the mac -> own lineage memory, so a restart does not make every sleeping device a
			# stranger again. Silently skipped when an older state file has none
			try:
				for mm, vv in (old.get("ownTags", {}) or {}).items():
					if not isinstance(vv, list) or len(vv) < 2:	continue
					self.ownTag[mm] = {"tagId": int(vv[0]), "last": float(vv[1])}
					if int(vv[0]) >= self.nextTagId:	self.nextTagId = int(vv[0]) + 1
			except Exception:
				U.logger.log(20, "", exc_info=True)

			if len(self.slots) > 0 or len(self.slotHistory) > 0:
				U.logger.log(20, "findMyGroup restored {} slot(s), {} tagId(s), {} remembered mac(s) and history for {} from {}".format(
						len(self.slots), len(self.tagIdOf), len(self.ownTag), len(self.slotHistory), src))
		except Exception:
			U.logger.log(20, "", exc_info=True)

	def restoreCsv(self):
		"""Puts the calibration csv back from the pibeacon dir when temp/ has come up empty.

		The same reason the state file is put back, and it matters more here: the state file is
		rebuilt within seconds by the tags themselves, the csv is a trail that only exists because
		it was written down. temp/ is a tmpfs, so a reboot took all of it.

		ONLY WHEN THE TEMP FILE IS MISSING. A csv that is already there is the live one and is
		ahead of the copy - overwriting it with the copy would throw away everything since the last
		persist, which is the opposite of the point.
		"""
		try:
			if os.path.isfile(self.csvFile):		return
			if not os.path.isfile(self.persistCsv):	return
			U.copyFile(self.persistCsv, self.csvFile)
			U.makeOwnFileWritable(self.csvFile)
			self.lastCsvCopy = self.csvStamp()
			U.logger.log(20, "findMyGroup calibration csv was gone (reboot?), restored {} bytes from {}".format(
					os.path.getsize(self.csvFile), self.persistCsv))
		except Exception:
			U.logger.log(20, "", exc_info=True)

	def csvStamp(self):
		"""(size, mtime) of the calibration csv, or (0, 0.) when there is not one."""
		try:
			st = os.stat(self.csvFile)
			return (st.st_size, st.st_mtime)
		except Exception:
			return (0, 0.)

	def persistCsvFile(self):
		"""Copies the calibration csv out of the tmpfs to the pibeacon dir - ONLY WHEN IT CHANGED.

		That check is the whole difference between this and a blind copy. The csv runs up to
		CSVMAXBYTES, so copying it on every tick would be ~80 MB a day onto a card that has to last,
		nearly all of it re-writing bytes that had not moved. With the calibration log switched off
		nothing is ever written to it, so nothing is ever copied and this costs nothing at all.
		"""
		try:
			stamp = self.csvStamp()
			if stamp == (0, 0.):			return		# no csv - calibration log off, or nothing logged yet
			if stamp == self.lastCsvCopy:	return		# not one byte added since the last copy
			U.copyFile(self.csvFile, self.persistCsv)
			U.makeOwnFileWritable(self.persistCsv)
			self.lastCsvCopy = stamp
		except Exception:
			U.logger.log(20, "", exc_info=True)

	def addHistory(self, slot, mac, freedAt):
		"""Puts one departed mac at the front of a slot's history and writes the file.

		At most MACHISTORY per slot, newest first, and the same mac is never recorded twice in a
		row - a tag that expires and comes back after SLOTHOLDSECS would otherwise fill the list
		with itself and push out the rotations, which are the entries worth having.

		Inputs:
		    slot (str): "01".."NN"
		    mac (str): the mac that left
		    freedAt (float): epoch seconds when it was freed
		Outputs:
		    None: updates self.slotHistory
		"""
		try:
			when = datetime.datetime.fromtimestamp(freedAt).strftime("%Y-%m-%dT%H:%M:%S")
			hh   = self.slotHistory.get(slot)
			if not isinstance(hh, list):	hh = []
			if hh and isinstance(hh[0], list) and hh[0][0] == mac:	return
			hh.insert(0, [mac, when])
			self.slotHistory[slot] = hh[:MACHISTORY]
			# not written to a file here: the state file carries the history and is written on the
			# next send, at most sendEverySecs away and usually sooner - a slot changing hands changes
			# the member set, which triggers a send of its own
		except Exception:
			U.logger.log(20, "", exc_info=True)

	def assignSlots(self, macs, now):
		"""Keeps the slot -> mac map.

		Timestamps are written with a "T" between date and time, NOT a blank: a blank inside a
		value does not survive the trip to the plugin - "2026-09-22 17:53:02" arrives there as
		"2026-09-2217:53:02" - so the plugin puts the blank back, where nothing can eat it. The
		year stays: a member device holds its last change until that slot moves again, which can
		be weeks. macs comes in strongest first, which only decides who gets
		the lowest free slot - it does NOT reorder anything already assigned.

		Inputs:
		    macs (list): the member macs, strongest signal first
		    now (float): epoch seconds
		Outputs:
		    None: updates self.slots and self.slotHistory
		"""
		have  = {}
		for mac in macs: have[mac] = 1

		# A mac that is no longer a member gives up its slot, but the slot is HELD for it rather
		# than freed outright. expireSecs is 10 by default and a tag advertises every ~2 s, so a
		# handful of lost packets expires a mac that never went anywhere; without the hold it came
		# back into a DIFFERENT slot, wrote a history entry for a departure that never happened,
		# and moved the indigo device it was bound to. Measured in a real house: one mac left slot
		# 05 and reappeared in slot 03 two minutes later.
		# SLOTHOLDSECS is under the 15 min rotation on purpose - a genuine rotation must still read
		# as a change of occupant, because that is the one thing the history exists to show
		for slot in sorted(self.slots.keys()):
			if self.slots[slot] not in have:
				self.slotHold[slot] = [self.slots[slot], now]
				del self.slots[slot]

		# a held mac that came back takes its own slot again - no history, nothing moved
		for slot in sorted(self.slotHold.keys()):
			mac, freedAt = self.slotHold[slot]
			if mac in have and slot not in self.slots:
				self.slots[slot] = mac
				del self.slotHold[slot]
			elif now - freedAt > SLOTHOLDSECS:
				# gone long enough to mean it. NOW it is a departure, and now it is history
				self.addHistory(slot, mac, freedAt)
				del self.slotHold[slot]

		taken = {}
		for slot in self.slots: taken[self.slots[slot]] = 1
		# a held slot is not free: it belongs to a mac that may be one packet away from returning
		free = ["{:02d}".format(ii) for ii in range(1, self.maxSlots + 1)
					if "{:02d}".format(ii) not in self.slots and "{:02d}".format(ii) not in self.slotHold]
		for mac in macs:
			if mac in taken:	continue
			if len(free) == 0:
				# every slot is live or held. Take the slot held LONGEST - it is the likeliest to
				# be a real departure - and record that departure before handing the slot over
				if len(self.slotHold) == 0:	break
				slot = sorted(self.slotHold.keys(), key=lambda k: self.slotHold[k][1])[0]
				old, freedAt = self.slotHold[slot]
				self.addHistory(slot, old, freedAt)
				del self.slotHold[slot]
			else:
				slot = free.pop(0)
			self.slots[slot] = mac
			taken[mac] = 1

	# ------------------------------------------------------------ params
	def setParams(self, inp):
		"""Call from readParams() with the parameters dict. Missing key = disabled."""
		pp = inp.get("findMyGroup", {}) if isinstance(inp, dict) else {}
		if not isinstance(pp, dict): pp = {}

		def num(key, default, cast=float):
			try:	return cast(pp.get(key, default))
			except Exception: return default

		wasEnabled                  = self.enabled
		self.enabled                = str(pp.get("enable", "0")) in ["1", "true", "True", "on"]
		self.devId                  = str(pp.get("devId", "0"))
		self.joinRssi               = num("joinRssi", -70.)
		self.leaveRssi              = min(num("leaveRssi", -80.), self.joinRssi)
		self.expireSecs             = max(3., num("expireSecs", 10.))
		self.stableSecs             = max(0., num("stableSecs", 60.))
		self.smoothN                = max(1, num("smoothN", 5, int))
		self.minPackets             = max(1, num("minPackets", 3, int))
		# CLAMPED, NOT TRUSTED. The plugin clamps the same value against its own copy of the ceiling,
		# so a dialog that grows past the constant cannot make this side hand out slots the other
		# side will never create - see MAXSLOTS
		self.maxSlots               = max(1, min(MAXSLOTS, num("maxSlots", 30, int)))
		self.sendEverySecs          = max(10., num("sendEverySecs", 60.))
		self.dropFromBeaconPipeline = str(pp.get("dropFromBeaconPipeline", "1")) in ["1", "true", "True", "on"]
		self.calibrationLog         = str(pp.get("calibrationLog", "0")) in ["1", "true", "True", "on"]
		# 0 off; 1 the summary plus one line per FIND MY frame - the ones that count; 2 that plus
		# every other apple frame that was looked at and rejected.
		# Logged at 20 like everything else on the rpi, so it is readable without putting the whole
		# pi into debug - which is the point: this is for watching find my, not everything
		# "strong" (default) or "median" - see strongHalf. "median" is the old behaviour and is
		# wrong wherever a mac arrives at two very different signal levels, which is everywhere
		self.rssiStat               = str(pp.get("rssiStat", "strong")).strip().lower()
		self.debugParam             = num("debug", 0, int)
		self.debug                  = self.debugParam		# checkDebugFile overrides it if the file is there
		self.debugMac               = str(pp.get("debugMac", "")).strip().upper()
		self.logEverySecs           = max(2., num("logEverySecs", 10.))

		if self.enabled != wasEnabled:
			self.reset()
			U.logger.log(20, "findMyGroup {}: devId:{} join:{} leave:{} stable:{}s drop:{} calibrationLog:{}".format(
				"ON" if self.enabled else "OFF", self.devId, self.joinRssi, self.leaveRssi, self.stableSecs,
				self.dropFromBeaconPipeline, self.calibrationLog))

	def smoothed(self, c):
		"""The signal this candidate is judged on - see strongHalf, or median with rssiStat "median"."""
		if self.rssiStat == "median":	return median(c["rssi"])
		return strongHalf(c["rssi"])

	# ------------------------------------------------------------ per frame
	def feed(self, hexstr, mac, rssi, now=None):
		"""hexstr: beaconloop frame after fillHCIdump (mac-rev 12 chars, len 2 chars, adv data, rssi 2 chars).
		Returns True if this was a Find My frame."""
		if not self.enabled: return False
		adv = hexstr[14:-2]
		fm  = parseFindMy(adv)
		if fm is None:
			# beaconloop hands over EVERY apple frame, so this is where the non-find-my ones stop.
			# MEASURED, because a pre-scan was written to avoid this call and then deleted: the
			# full parse is 0.53 us and a hex-only scan for the type byte 0.50 us - 1.1x, on
			# something that costs 0.1 ms per second at real frame rates. A second decoder to
			# maintain in step with this one, for that, is a bad trade.
			if self.debug >= 2 and (self.debugMac == "" or self.debugMac in mac):
				tt = appleTypesIn(adv)
				U.logger.log(20, "findMyGroup seen  {}  rssi:{:>4}  apple types:{:<12} -> no find my (12) in it, ignored".format(
						mac, rssi, "|".join("{:02X}".format(t) for t in tt) or "none"))
			return False
		if now is None: now = time.time()
		self.update(mac, fm[0], fm[1], rssi, now, fm[2], fm[3], adv)
		return True

	def update(self, mac, indicator, status, rssi, now, hint=None, types=None, raw=None):
		c = self.cands.get(mac)
		if c is None:
			c = {"first": now, "last": now, "rssi": [], "interval": [], "indicator": indicator, "inds": {}, "status": status,
					"hint": hint, "raw": raw, "types": {}, "member": False}
			self.cands[mac] = c
			# THE SAME MAC COMING BACK IS NOT A NEW DEVICE - see CARRYBACK. Only "last" moves; the
			# age and the accumulated types are the TAG's and survive the record being rebuilt.
			# The lineage is NOT taken back here: that is decided at join, where ownTag already
			# does it and logs why - this is about identity, not about which tag it is
			back = self.macCarry.get(mac)
			if back is not None and now - back.get("last", 0.) <= CARRYBACK:
				c["first"] = back.get("first", now)
				if back.get("types"):	c["types"] = dict(back["types"])
				if back.get("inds"):	c["inds"]  = dict(back["inds"])
				U.logger.log(10, "findMyGroup BACK  {} after {:.0f}s, keeps age {:.0f}s and types {}".format(
						mac, now - back.get("last", now), now - c["first"],
						"|".join("{:02X}".format(t) for t in sorted(c["types"])) or "-"))
			else:
				U.logger.log(10, "findMyGroup NEW   {} dist:{} rssi:{}".format(mac, indicator, rssi))
		c["last"]      = now
		c["indicator"] = indicator
		# AND EVERY INDICATOR IT HAS EVER SENT, for the same reason the apple types accumulate.
		# "indicator" alone is the LAST frame's kind and it flaps: a tag changing mode sends both
		# for a while. Measured at 23:49 - the newcomer sent nearby for 20 s and then separated,
		# while the mac it had rotated from had just gone separated, so two snapshots of one
		# device disagreed and the rotation was refused. What is stable is the SET
		c.setdefault("inds", {})[indicator] = 1
		c["status"] = status
		# only when this frame HAD one: a tag alternating separated and nearby frames would
		# otherwise wipe the hint every time the 2 byte nearby payload came round
		if hint is not None:	c["hint"] = hint
		# THE RAW FRAME, most recent wins - kept for the calibration csv and nothing else. Unlike
		# the hint it is NOT held across a frame that lacks one, because there is no such thing:
		# every frame has a raw form, and the useful question about it is "what did this mac send
		# last", with raw_len saying which kind of payload that was
		if raw is not None:		c["raw"] = raw
		# apple types ACCUMULATE over every frame this mac sends - a device does not put them all
		# in one advertisement, so a single frame proves nothing absent
		if types:
			if "types" not in c: c["types"] = {}
			for t in types: c["types"][t] = 1
		c["pkts"]   = c.get("pkts", 0) + 1
		c["rssi"].append(rssi)
		if len(c["rssi"]) > self.smoothN: del c["rssi"][0]
		# level 1: the frames that COUNT. level 2 adds the apple frames that were looked at and
		# turned out not to be find my - see feed()
		if self.debug >= 1 and (self.debugMac == "" or self.debugMac in mac):
			# EVERY COLUMN FIXED WIDTH - mac 17, dist 9, status 26 (statusBits pads the battery
			# word inside it), hint 2, types 11. pkt# is last, where a long one costs nothing
			U.logger.log(20, "findMyGroup frame sl:{:<2} {:<17}  rssi:{:>4}  dist:{:<9}  status:{}  hint:{:<2}  types:{:<11}  pkt#{}".format(
					self.slotOf(mac), mac, rssi, indicator,
					self.statusBits(status),
					"--" if c.get("hint") is None else "{:02X}".format(c["hint"]),
					"|".join("{:02X}".format(t) for t in sorted(c.get("types", {}))) or "-",
					c["pkts"]))
		c["interval"].append(rssi)
		s = self.smoothed(c)
		if not c["member"] and len(c["rssi"]) >= self.minPackets and s >= self.joinRssi:
			# THE LINEAGE IS DECIDED HERE, at join, not at the first packet: by now there are
			# minPackets of signal to compare and the apple types have had a chance to accumulate,
			# and it is still only a few seconds after the old mac fell silent
			if c.get("tagId") is None and mac not in self.rotPending:
				if mac in self.tagIdOf:
					# same mac as before a restart, or a tag that dropped out and came back on its own
					# mac - the lineage never ended
					c["tagId"] = self.tagIdOf[mac]
				elif mac in self.ownTag:
					# THE SAME MAC, BACK AFTER IT EXPIRED, and it keeps what it already owned.
					# A tag that misses expireSecs of packets - ten seconds, which these do all
					# the time - leaves cands and its lineage leaves tagIdOf. Without this branch
					# it came back as a mac nobody had ever seen and went to matchRotation, which
					# could hand it SOMEBODY ELSE'S lineage while its own sat unclaimed.
					# IT COULD NOT RECLAIM ITS OWN THROUGH matchRotation EITHER, and that is
					# arithmetic rather than bad luck: its own entry is at least expireSecs old by
					# definition, so the gap test always threw away the one lineage guaranteed to
					# be right. Taken directly here - there is no guess in it, it is the same mac.
					# WHY ownTag AND NOT goneTags: goneTags is the pool a DIFFERENT mac inherits
					# from and must stay short, or every stale lineage becomes a rival candidate.
					# This one is matched by the identical mac only, so it is kept OWNKEEP - long
					# enough for an earpiece that sleeps in its case for minutes at a time
					gone = now - self.ownTag[mac]["last"]
					c["tagId"] = self.ownTag[mac]["tagId"]
					del self.ownTag[mac]
					self.goneTags.pop(mac, None)		# it is back; nobody else may inherit it now
					self.logRot("ROT=  {} same mac back after {:.0f}s, keeps its own tagId:{}".format(mac, gone, c["tagId"]))
				else:
					c["tagId"] = self.matchRotation(mac, c, now)
					if c["tagId"] is None and mac not in self.rotPending:
						c["tagId"]     = self.nextTagId
						self.nextTagId += 1
						# A MAC NOBODY COULD ACCOUNT FOR. Either a tag that really is new to this
						# rpi, or a rotation that was not recognised - and from indigo those two
						# look identical, because both arrive as a member device that was not
						# there before. Saying which is which is the whole question when devices
						# multiply, so it is said here rather than left to be inferred
						self.logRot("ROTX  {} no lineage matched, fresh tagId:{} - {} candidate(s) turned down: {}".format(
								mac, c["tagId"], len(getattr(self, "lastRotWhy", [])),
								"; ".join(getattr(self, "lastRotWhy", [])[:8]) or "none in range at all"))
				if c["tagId"] is not None:	self.tagIdOf[mac] = c["tagId"]
			# HELD, NOT JOINED, while a claim on somebody else's lineage waits to be confirmed.
			# IT MATTERS THAT THIS IS "not a member" AND NOT "a member with tagId None": a member
			# travels to the plugin, and one arriving without a lineage is given a slot and an
			# indigo device of its own - which is the exact outcome the wait exists to avoid. Held
			# it reads as "heard but not counted", which for ROTCONFIRM seconds is simply true.
			# resolveRotClaims() settles it; the next frame after that comes through here and joins
			if mac not in self.rotPending:
				c["member"] = True
				U.logger.log(10, "findMyGroup JOIN  {} rssi~{} tagId:{}".format(mac, s, c.get("tagId")))
		elif c["member"] and s < self.leaveRssi:
			c["member"] = False
			U.logger.log(10, "findMyGroup LEAVE {} rssi~{}".format(mac, s))

		# ITS LINEAGE WAS TAKEN AND IT IS STILL HERE.
		# A BACKSTOP NOW, NOT THE NORMAL CASE. It used to be routine: a lineage was handed over on
		# the strength of a 3 s silence, which at roughly one advertisement every 2 s is a single
		# missed packet, so a mac that never went anywhere could be robbed and then carry on
		# transmitting with none. ROTCONFIRM ended that - a candidate that is still on the air says
		# so during the wait and takes itself out of the running. What is left for this to catch is
		# the genuinely unlucky: a mac silent for the whole confirmation window that then comes back.
		# KEPT, AND NOT BECAUSE IT MIGHT STILL FIRE: if it ever does, this is the difference between
		# one surprising device and a mac that reports no lineage for the rest of its life.
		# IT NEVER GOT ANOTHER ONE, because the assignment above runs only at JOIN and this mac had
		# already joined. It then reported no lineage for the rest of its life, the plugin could not
		# follow its NEXT rotation, and made a new indigo device for it every single time. Seen in a
		# real house: two member devices both showing tagId "5-1", neither having ever changed mac.
		# A FRESH ONE, NOT THE OLD ONE BACK: the old lineage has moved on and must not be held twice -
		# undoing that here would put the duplicate back. The trail really was broken, and a new
		# lineage from this point is what is true.
		if c["member"] and c.get("tagId") is None:
			c["tagId"]        = self.nextTagId
			self.nextTagId   += 1
			self.tagIdOf[mac] = c["tagId"]
			U.logger.log(20, "findMyGroup {} is still here but its lineage was given to a rotation - new tagId:{}".format(
					mac, c["tagId"]))

	# ------------------------------------------------------------ periodic
	def tick(self, now=None):
		"""Call often from the main loop (rate limited to 1/sec inside).
		Returns a packet for checkIfDelaySend() / sendURL() or None."""
		if not self.enabled: return None
		if now is None: now = time.time()
		if now - self.lastTick < 1.: return None
		self.lastTick = now
		self.checkDebugFile(now)

		for mac in list(self.cands):
			c = self.cands[mac]
			if now - c["last"] > self.expireSecs:
				U.logger.log(10, "findMyGroup GONE  {} after {:.0f}s member:{} tagId:{}".format(
						mac, c["last"] - c["first"], c["member"], c.get("tagId")))
				# an expired lineage stays inheritable for GONEKEEP: the rotation may only be noticed
				# when the new mac JOINS, which is minPackets of frames after it first appeared
				if c.get("tagId") is not None:
					self.ownTag[mac] = {"tagId": c["tagId"], "last": c["last"]}
					self.goneTags[mac] = {"tagId": c["tagId"], "last": c["last"], "rssi": self.smoothed(c),
										"battery": self.battery(c.get("status")),
										"inds": dict(c.get("inds", {})),
										"types": "|".join("{:02X}".format(t) for t in sorted(c.get("types", {})))}
				# EVERY mac, not just the ones with a lineage - the miss this was written for was a
				# mac that expired before it had joined, so ownTag and goneTags both skipped it
				self.macCarry[mac] = {"first": c["first"], "last": c["last"],
										"types": dict(c.get("types", {})), "inds": dict(c.get("inds", {}))}
				self.tagIdOf.pop(mac, None)
				del self.cands[mac]

		for oMac in list(self.macCarry):
			if now - self.macCarry[oMac]["last"] > CARRYBACK:	del self.macCarry[oMac]
		for oMac in list(self.goneTags):
			if now - self.goneTags[oMac]["last"] > GONEKEEP:	del self.goneTags[oMac]
		for oMac in list(self.ownTag):
			if now - self.ownTag[oMac]["last"] > OWNKEEP:		del self.ownTag[oMac]
		if len(self.ownTag) > OWNMAX:
			# oldest first: the least recently heard mac is the least likely to come back, and
			# with a two day memory the pruning above will not do this on its own
			for oMac in sorted(self.ownTag, key=lambda m: self.ownTag[m]["last"])[:len(self.ownTag) - OWNMAX]:
				del self.ownTag[oMac]

		# AFTER the expiry pass above, not before: a candidate that has just gone quiet only
		# reaches goneTags there, and a claim on it has to see it where it now lives
		self.resolveRotClaims(now)

		self.rawCount = sum(1 for c in self.cands.values() if c["member"])
		if self.rawCount != self.pending:
			self.pending, self.pendingSince = self.rawCount, now

		# WHICH macs, not how many. A tag rotating its mac swaps one member for another and leaves
		# the COUNT untouched, so a count-only trigger says nothing and the plugin goes on working
		# from the old mac until the next periodic refresh - up to sendEverySecs later. Harmless
		# with one rpi; wrong with several, because the plugin merges the rpis BY MAC and a stale
		# mac from one rpi beside the fresh one from another is two members for one tag
		memberSet = frozenset(mac for mac, c in self.cands.items() if c["member"])

		trigger = ""
		warmup  = self.stableSecs + self.expireSecs + 2. * self.minPackets
		if now - self.startTime < warmup:
			# after (re)start: take the count as is, send nothing -> no false "0" to indigo
			self.stableCount   = self.pending
			self.lastSend      = now - self.sendEverySecs
			self.lastMemberSet = memberSet		# so the first real send is "startup", not "members"
		elif not self.startupSent:
			self.startupSent = True
			trigger = "startup"						# first real count after warmup, sent at once
		elif self.pending != self.stableCount and now - self.pendingSince >= self.stableSecs:
			self.previousCount, self.stableCount, self.lastChange = self.stableCount, self.pending, now
			U.logger.log(20, "findMyGroup memberCount {} -> {}".format(self.previousCount, self.stableCount))
			trigger = "count"
		elif self.lastMemberSet is not None and memberSet != self.lastMemberSet and now - self.lastSend >= MINSENDSECS:
			# the membership changed while the count did not - a rotation, or one tag leaving as
			# another arrives. Held to MINSENDSECS so a tag flickering at the edge of range cannot
			# turn this into a message every loop
			trigger = "members"
		elif now - self.lastSend >= self.sendEverySecs:
			trigger = "time"

		self.checkMarker()
		if self.calibrationLog and now - self.lastLog >= self.logEverySecs:
			self.lastLog = now
			self.writeCalibrationRows(now)
		else:
			if not self.calibrationLog:
				for c in self.cands.values(): c["interval"] = []

		if trigger == "": return None
		self.lastSend      = now
		self.lastMemberSet = memberSet
		data = self.states(now)
		# indented: this file is read by a person far more often than by the program - "cat
		# temp/findMyGroup.state" is the first thing anybody does when the count looks wrong, and
		# one unbroken line of json is not an answer to anything
		U.writeJson(self.stateFile, data, sort_keys=False, indent=2)
		# and to the SD card every PERSISTSECS, so a reboot does not lose the slot map, the mac
		# history or the calibration trail. Not every send: that would be ~1440 writes a day on a
		# card that has to last, for a file that changes very little between two of them
		if now - self.lastPersist >= PERSISTSECS:
			self.lastPersist = now
			U.writeJson(self.persistFile, data, sort_keys=False, indent=2)
			self.persistCsvFile()
		if self.debug >= 1: self.logSummary(now, trigger)
		if self.devId in ["", "0"]: return None
		data["trigger"] = trigger
		return {"sensors": {SENSOR_NAME: {self.devId: data}}}

	def logRot(self, txt):
		"""One line about a lineage decision. ROT matched, ROT? refused as ambiguous, ROTX no match.

		ALL THREE START "ROT" ON PURPOSE, so one grep catches every decision and nothing else:

		    grep "findMyGroup ROT" /var/log/pibeacon

		"NEW" would have read better and is already taken - update() logs "NEW <mac> dist:.." for
		a candidate nobody has seen before, which is a different event entirely.

		LEVEL 20 WHEN THE DEBUG MENU IS ON, level 10 otherwise - the same deal logSummary makes.
		These lines are the entire evidence for "is a rotation being followed", and needing the
		whole pi in debug to see them meant nobody ever did. There are only a few an hour: a tag
		rotates about every 15 min near its owner and once a DAY when separated.
		No timestamp of its own - the log format already stamps every line.

		Inputs:
		    txt (str): the line, already formatted
		Outputs:
		    None
		"""
		U.logger.log(20 if self.debug >= 1 else 10, "findMyGroup {}".format(txt))

	def logSummary(self, now, trigger):
		"""The decoded picture at the moment a message goes out - the key fields, named, not hex.

		Switched on with "debug":"1". Members are listed in SLOT order so the lines match the
		indigo member devices; everything else heard follows with the REASON it is not a member,
		because "why is that tag not counted" is the question this is here to answer.

		Inputs:
		    now (float): epoch seconds
		    trigger (str): startup / count / time - what caused this send
		Outputs:
		    None
		"""
		try:
			active  = list(self.cands.items())
			members = [(mac, c) for mac, c in active if c["member"]]
			rssis   = [self.smoothed(c) for mac, c in active if c["rssi"]]
			# WHICH mac is the strongest, not just the number. "strongest:-68" on its own invites
			# "but I can see -32 in the frame lines" - and the answer is usually that the -32 mac
			# had expired by the time this ran, or is on another rpi. Naming it ends the argument
			strongest, strongestMac = -999, "-"
			for mac, c in active:
				if not c["rssi"]: continue
				sm = self.smoothed(c)
				if sm > strongest: strongest, strongestMac = sm, mac
			U.logger.log(20, "findMyGroup ==== {}  trigger:{}  members:{} (raw {})  candidates:{}  nearby:{}  strongest:{} ({})  join:{:.0f} leave:{:.0f}".format(
					datetime.datetime.fromtimestamp(now).strftime("%H:%M:%S"), trigger,
					self.stableCount, self.rawCount, len(active), len(active) - len(members),
					int(strongest) if rssis else -999, strongestMac, self.joinRssi, self.leaveRssi))
			U.logger.log(20, "findMyGroup      sl mac                rssi  dist       battery   types      age   pkts")

			bySlot = {}
			for slot in self.slots: bySlot[self.slots[slot]] = slot

			def line(slot, mac, c, tail=""):
				U.logger.log(20, "findMyGroup      {:<2} {:<17} {:>5}  {:<9}  {:<8}  {:<9} {:>5}s {:>5}{}".format(
						slot, mac,
						int(self.smoothed(c)) if c["rssi"] else -999,
						c["indicator"], self.battery(c["status"]) or "-",
						"|".join("{:02X}".format(t) for t in sorted(c.get("types", {}))) or "-",
						int(now - c["first"]), c.get("pkts", 0), tail))

			for slot in sorted(self.slots.keys()):
				c = self.cands.get(self.slots[slot])
				if c is not None: line(slot, self.slots[slot], c)

			for mac, c in sorted(active, key=lambda mc: self.smoothed(mc[1]) if mc[1]["rssi"] else -999, reverse=True):
				if mac in bySlot: continue
				sm = self.smoothed(c)
				if len(c["rssi"]) < self.minPackets:		why = "  (only {} packets, needs {})".format(len(c["rssi"]), self.minPackets)
				elif sm is not None and sm < self.joinRssi:	why = "  (weaker than join {:.0f})".format(self.joinRssi)
				else:										why = "  (not a member)"
				line("-", mac, c, why)

			for slot in sorted(self.slotHold.keys()):
				mac, freedAt = self.slotHold[slot]
				U.logger.log(20, "findMyGroup      {:<2} {:<17} HELD - gone {:.0f}s, slot kept {:.0f}s more".format(
						slot, mac, now - freedAt, max(0., SLOTHOLDSECS - (now - freedAt))))
		except Exception:
			U.logger.log(20, "", exc_info=True)

	def states(self, now):
		active  = list(self.cands.items())
		members = [(mac, c) for mac, c in active if c["member"]]
		rssis   = [self.smoothed(c) for mac, c in active if c["rssi"]]

		# strongest first, which decides only who takes the lowest FREE slot - see assignSlots
		members.sort(key=lambda mc: self.smoothed(mc[1]) if mc[1]["rssi"] else -999, reverse=True)
		self.assignSlots([mac for mac, c in members], now)

		byMac = {}
		for mac, c in members: byMac[mac] = c
		mem = {}
		for slot in sorted(self.slots.keys()):
			c = byMac.get(self.slots[slot])
			if c is None: continue				# restored slot whose mac has not come back yet
			# 5th field: the apple continuity types this mac has been seen sending, "05|0C|10|12".
			# THIS is what separates a phone from a tag - a tag sends 0x12 and nothing else, while
			# a phone or a mac also sends nearby-info (0x10), handoff (0x0C), airdrop (0x05).
			# There is no device type in a find my frame and never will be; which OTHER messages
			# the same mac sends is the closest thing to one, and it costs nothing to carry
			mem[slot] = {"mac":        self.slots[slot],
						"rssi":       int(self.smoothed(c)),
						"distanceIndicator": c["indicator"],
						"battery":    self.battery(c["status"]),
						"appleTypes": "|".join("{:02X}".format(t) for t in sorted(c.get("types", {}))),
						# THE LAST BYTE OF THE SEPARATED PAYLOAD, as two hex characters, or "" for a
						# mac that has only ever sent the 2 byte nearby payload - that one has no
						# hint byte at all, so "" means "never said" and not "said zero".
						# SENT AS TEXT, NOT A NUMBER: nothing adds it up, it is read by eye against
						# other macs, and 8D beats 141 for that. No published meaning beyond "0x00
						# on ios", which is exactly why it is worth carrying - it can only be
						# correlated against devices whose identity is known, and that happens on
						# the indigo side where the devices have names
						"hintByte":   "" if c.get("hint") is None else "{:02X}".format(c["hint"]),
						# THE LINEAGE. The slot is a small reused pool and says nothing across time;
						# this is never reused and SURVIVES A MAC ROTATION, so the plugin can keep an
						# indigo device on the same physical tag when its mac changes. Only meaningful
						# together with this rPi's number - rPi 2's tagId 7 is not rPi 5's tagId 7
						"tagId":      c.get("tagId")}

		# EVERY MAC THIS RPI HEARS BUT DOES NOT COUNT - below joinRssi, or still short of
		# minPackets. They have NO SLOT and never will, so they cannot travel in "members" and go
		# separately as mac -> rssi. It is what lets a member device say "that rPi CAN hear the
		# tag, it is just too weak to count" instead of the same "down" it shows for a tag that is
		# not there at all. Those two looked identical from the plugin side and are not remotely
		# the same thing - one is a threshold to adjust, the other is a tag that has left.
		# CAPPED AT MAXWEAK, strongest first: a busy place hears a lot of find my traffic and this
		# message goes out every sendEverySecs. A mac 30 dB down is not about to become a member,
		# so it is the strongest of them that are worth the bytes
		weak    = {}
		notMem  = [mc for mc in active if not mc[1]["member"]]
		notMem.sort(key=lambda mc: self.smoothed(mc[1]) if mc[1]["rssi"] else -999, reverse=True)
		for mac, c in notMem[:MAXWEAK]:
			weak[mac] = int(self.smoothed(c)) if c["rssi"] else -999

		return {
			"numberOfActive":     self.stableCount,
			"numberOfActiveRaw":  self.rawCount,
			"numberOfWeak":     len(active) - len(members),
			"numberOfCandidates":      len(active),
			"strongestRSSI":   int(max(rssis)) if rssis else -999,
			"numberOfActivePrevious":   self.previousCount,
			# "T" for the same reason as in assignSlots - a blank does not survive the trip and the
			# plugin puts it back. The year stays here: a count change can be days old
			"numberOfActiveChanged": datetime.datetime.fromtimestamp(self.lastChange).strftime("%Y-%m-%dT%H:%M:%S") if self.lastChange > 0 else "",
			"members":         mem,
			"weak":            weak,
			"membersHistory":  self.slotHistory,
			# so the counter never goes backwards over a restart and hands a NEW tag an id that an
			# indigo device still remembers as something else
			"nextTagId":       self.nextTagId,
			# WHICH MAC OWNS WHICH LINEAGE, so two days of memory is not undone by one restart.
			# Compact on purpose - [tagId, last] rather than named fields - because at OWNMAX this
			# is the biggest thing in the file and it is written every send
			"ownTags":         dict((m, [self.ownTag[m]["tagId"], int(self.ownTag[m]["last"])]) for m in self.ownTag),
		}

	def matchRotation(self, mac, c, now):
		"""The tagId of the lineage this mac is the continuation of, or None.

		WHY THIS IS HERE AND NOT IN THE PLUGIN: the plugin sees a summary every sendEverySecs, so a
		rotation reaches it as "somewhere in the last minute one mac left and another arrived" - and
		a minute is long enough for several things to happen. Here the old mac's last packet and the
		new one's first are a fraction of a second apart, and that resolution is the whole evidence.

		NOTHING IN THE FRAME IDENTIFIES A TAG - a find my mac is derived from a rotating key and
		every other field is either the same on all tags or undocumented. So this is an INFERENCE
		from continuity, and it refuses rather than guesses:
		  - the old mac stopped within ROTGAP of this one starting
		  - the smoothed signal matches within ROTRSSI - it has not moved in that second
		  - the battery word is identical, and the newcomer's appleTypes are a SUBSET of the old
		    mac's rather than equal to them - see the test itself for why equality was wrong.
		    Neither identifies anything alone; together they
		    throw away most wrong candidates for free
		  - and EXACTLY ONE lineage fits. Two candidates means we do not know, and a wrong carry-over
		    silently renames somebody's tag, which is worse than an extra device appearing

		IT NO LONGER DECIDES ANYTHING - IT NARROWS THE FIELD. Every test above reads one instant,
		and at one instant a tag that rotated and a tag that missed a packet are identical. The
		question that separates them - does the old mac EVER SPEAK AGAIN - is about the future, so
		the survivors go on self.rotPending and resolveRotClaims() settles it ROTCONFIRM later.
		So None from here means "nothing fitted" ONLY when the mac is absent from rotPending;
		otherwise it means "ask again shortly", and the caller must not mint a lineage meanwhile.

		Inputs:
		    mac (str): the mac that has just joined
		    c (dict): its candidate record
		    now (float): epoch seconds
		Outputs:
		    int or None: the tagId to inherit
		"""
		try:
			first = c.get("first", now)
			rssi  = self.smoothed(c)
			batt  = self.battery(c.get("status"))
			inds  = set(c.get("inds", {}))
			types = "|".join("{:02X}".format(t) for t in sorted(c.get("types", {})))

			# every lineage that could be the one: still-known macs that have gone quiet, and macs
			# that have already expired. Both are kept with their last packet time
			pool = []
			for oMac in self.cands:
				if oMac == mac:									continue
				oc = self.cands[oMac]
				if oc.get("tagId") is None:						continue
				pool.append((oMac, oc.get("tagId"), oc.get("last", 0.), self.smoothed(oc),
							self.battery(oc.get("status")),
							"|".join("{:02X}".format(t) for t in sorted(oc.get("types", {}))),
							set(oc.get("inds", {}))))
			for oMac in self.goneTags:
				if oMac == mac:									continue	# its own, handled by the caller
				g = self.goneTags[oMac]
				pool.append((oMac, g["tagId"], g["last"], g["rssi"], g["battery"], g["types"], set(g.get("inds", {}))))

			# WHY EACH ONE WAS TURNED DOWN, not just that none fitted. The line that mattered used
			# to say only "no lineage matched", which left tuning these to guesswork - and one bad
			# guess at a threshold cost an afternoon. It is worth more than it looks: it was these
			# reasons, read back in bulk, that showed the quiet test only ever refused good matches.
			# The list is carried on into the claim so a refusal ROTCONFIRM later still says why
			hits, why = [], []
			for oMac, tagId, last, oRssi, oBatt, oTypes, oInds in pool:
				tail = oMac[-5:]
				if abs(first - last) > ROTGAP:
					why.append("{} gap {:.1f}s>{:.0f}".format(tail, abs(first - last), ROTGAP));	continue
				# NO "HAS IT BEEN QUIET" TEST HERE ANY MORE - see ROTCONFIRM. It asked at the instant
				# of the join whether the old mac had stopped, which at a 2 s advertising interval is
				# asking whether it missed one packet. Every refusal it ever logged was under 3 s,
				# because the cleaner the handover the more certain it was. What it was reaching for
				# is real and is now tested properly: the old mac has to STAY silent, which is a
				# question about the future and cannot be answered here. resolveRotClaims() answers it
				if abs(oRssi - rssi) > ROTRSSI:
					why.append("{} rssi {:.0f}vs{:.0f}".format(tail, oRssi, rssi));					continue
				if oBatt != batt:
					why.append("{} batt {}vs{}".format(tail, oBatt or "-", batt or "-"));			continue
				# TYPES ACCUMULATE, so equality was the wrong test and it was biased against the
				# very candidate being judged: the old mac has collected its types over minutes of
				# frames, the newcomer has minPackets of them. An airpods case sends 07 AND 12 and
				# does not put both in every frame, so a new mac that had only shown "12" yet was
				# refused a lineage it plainly owned - and earned a new indigo device every time
				# it rotated. Airpods going to sleep in the case and coming back makes this happen
				# far more than it does to a tag, which is why they multiplied the fastest.
				# SUBSET, NOT EQUALITY: everything the newcomer has sent, the old mac sent too. A
				# type the old one NEVER sent is a real difference and still refuses the match, so
				# a tag cannot inherit a phone's lineage - which is what this test is here for
				if not set([t for t in types.split("|") if t]) <= set([t for t in oTypes.split("|") if t]):
					why.append("{} types {} not within {}".format(tail, types or "-", oTypes or "-"));	continue
				# SEPARATED IS NOT NEARBY. The indicator is the TAG'S OWN STATEMENT about whether
				# its owner is with it, and a mac rotation does not change it - the owner walking
				# away does. So two macs disagreeing about it at one instant are not one tag, and
				# this test was simply missing. Caught it doing real damage: D3:3C (nearby) and
				# FF:C5 (separated) handed tagId 1 back and forth twice in seven seconds, and
				# every other test passed them both - same battery, same types, both -59 dBm.
				# BLANK EITHER SIDE IS NOT A DISAGREEMENT: an unknown length reads as "lenNN" and
				# a gone entry from an older state file has none, and neither is evidence.
				# SETS, NOT SNAPSHOTS, and this is the whole of what that test got wrong. A device
				# changing mode sends both kinds for a while, so the two macs either side of a
				# rotation can disagree about the LAST frame while being the same tag - seen at
				# 23:49:07, where the newcomer had sent only nearby so far and went separated itself
				# twenty seconds later. Sharing NOTHING is the real disagreement, and that is still
				# refused: the pair this was written for (D3:3C nearby, FF:C5 separated) never sent
				# anything but its own kind, so their sets stay disjoint and they stay apart
				if inds and oInds and not (inds & oInds):
					why.append("{} {} shares nothing with {}".format(
							tail, "|".join(sorted(inds)), "|".join(sorted(oInds))));				continue
				# AND IT MAY NOT GO STRAIGHT BACK. A lineage that has just moved A -> B cannot
				# move B -> A moments later: a rotation is one way, so a reversal is two wrong
				# matches rather than two right ones. The pair above did exactly that
				wasFrom, wasTo, wasAt = self.rotLast.get(tagId, ("", "", 0.))
				if wasFrom == mac and wasTo == oMac and now - wasAt < ROTBACK:
					why.append("{} would hand {} straight back ({:.0f}s)".format(tail, tagId, now - wasAt));	continue
				hits.append((oMac, tagId, last, oRssi, oTypes))
			# kept on self rather than returned: the return value is the tagId and has one job
			self.lastRotWhy = why

			# NOTHING IS DECIDED HERE ANY MORE, and that is the whole change. Everything above is
			# evidence available at ONE INSTANT, and at one instant a tag that has rotated and a tag
			# that merely missed a packet look exactly alike - which is how a mac that never moved
			# had its lineage taken at 18:48:48 while it went on transmitting for another seven
			# minutes. What tells them apart is what the OLD mac does NEXT, and that has not
			# happened yet. So the survivors are written down and tick() settles it ROTCONFIRM
			# later - see resolveRotClaims(), which is where ROT / ROT? / ROTX now come from.
			# RETURNING None IS NOT "no match" ANY MORE: the caller tells the two apart by whether
			# this mac is in self.rotPending, and must not mint a fresh tagId while it is
			if not hits:		return None
			self.rotPending[mac] = {"at": now, "rssi": rssi, "types": types, "why": list(why),
									"cands": dict((h[0], (h[1], h[2], h[3], h[4])) for h in hits)}
			self.logRot("ROT~  {} waiting {:.0f}s on {} candidate(s): {}".format(
					mac, ROTCONFIRM, len(hits), ",".join(sorted(h[0][-5:] for h in hits))))
			return None
		except Exception:
			U.logger.log(20, "", exc_info=True)
		return None

	def rotStillSilent(self, oMac, tagId, lastAtClaim):
		"""Whether oMac still holds tagId and has not transmitted since a claim was made on it.

		Three answers, not two. None means the lineage is not oMac's to give any more - it expired
		out of goneTags, or another claim settled first and took it - and a claim naming it must
		simply drop it rather than treat the silence as evidence.

		Inputs:
		    oMac (str): the mac whose lineage is being claimed
		    tagId (int): the lineage as it stood when the claim was made
		    lastAtClaim (float): oMac's last packet time then
		Outputs:
		    bool or None: True still silent, False spoke again, None lineage gone
		"""
		if oMac in self.cands:
			if self.cands[oMac].get("tagId") != tagId:	return None
			return self.cands[oMac]["last"] <= lastAtClaim + ROTSPOKE
		if oMac in self.goneTags:
			if self.goneTags[oMac]["tagId"] != tagId:	return None
			return self.goneTags[oMac]["last"] <= lastAtClaim + ROTSPOKE
		return None

	def rotAlive(self, mac):
		"""The candidates of one pending claim that are still silent, with why the others went.

		Recomputed at the moment a claim is settled rather than kept up to date as packets arrive:
		an earlier claim settled in the same pass may already have taken one of these lineages, and
		that has to be seen.

		Inputs:
		    mac (str): the mac holding the claim
		PURE ON PURPOSE - it reports, it does not record. This runs once a second for EVERY claim
		in flight, so appending the reasons to the claim itself wrote the same line over and over
		and put reasons on claims that were not being settled at all. The caller keeps what it needs.

		Outputs:
		    tuple: ({oMac: (tagId, rssi, types)} survivors, [str] why the others are out)
		"""
		p, alive, why = self.rotPending[mac], {}, []
		for oMac in sorted(p["cands"]):
			tagId, lastAt, oRssi, oTypes = p["cands"][oMac]
			still = self.rotStillSilent(oMac, tagId, lastAt)
			if still is None:
				why.append("{} lineage {} is no longer its to give".format(oMac[-5:], tagId));	continue
			if not still:
				why.append("{} spoke again after the claim".format(oMac[-5:]));					continue
			alive[oMac] = (tagId, oRssi, oTypes)
		return alive, why

	def resolveRotClaims(self, now):
		"""Settles every claim that has waited ROTCONFIRM, and mints a lineage for the ones that fail.

		THIS IS WHERE A ROTATION IS ACTUALLY DECIDED. matchRotation() only narrows the field; the
		evidence it cannot have is whether the old mac ever speaks again, and that arrives here.
		A candidate that has gone on advertising eliminates ITSELF, which does two things at once:
		a live mac can no longer be robbed of a lineage it is still using, and "could be any of .."
		largely stops happening, because two candidates are rarely both really gone - usually one
		is merely quiet and says so within the wait.

		WHAT WAITING COSTS, and it is paid here rather than hidden: the mac has been held out of
		members since it joined, so a real new tag reaches indigo ROTCONFIRM later than it used to.
		Against stableSecs 60 that is noise, and it buys the one thing no instant can give.

		Inputs:
		    now (float): epoch seconds
		Outputs:
		    None
		"""
		try:
			if not self.rotPending:	return
			# WHO ELSE IS AFTER THE SAME LINEAGE, worked out over every claim in flight and not just
			# the ones falling due: a rival that has not waited its turn yet is still a rival
			rivals = dict((m, (self.rotPending[m]["rssi"], self.rotPending[m].get("types", "")))
								for m in self.rotPending)
			others = dict((m, self.rotAlive(m)[0]) for m in self.rotPending)
			for mac in [m for m in sorted(self.rotPending) if now - self.rotPending[m]["at"] >= ROTCONFIRM]:
				mine, why = self.rotAlive(mac)
				p         = self.rotPending.pop(mac)
				p["why"].extend(why)
				c    = self.cands.get(mac)
				if c is None:
					# the newcomer itself went away while we waited. Nothing to hand a lineage to, and
					# the old one keeps it - which is right: a mac that lasted seconds rotated nowhere
					self.logRot("ROTD  {} gone before its claim settled - no lineage moved".format(mac))
					continue
				keep = {}
				for oMac in sorted(mine):
					tagId, oRssi, oTypes = mine[oMac]
					# EXACTLY THE SAME APPLE TYPES, or merely a subset of them? The subset test that let
					# this candidate through is deliberately one-way - everything the newcomer sends, the
					# old mac sent too - and that asymmetry runs the WRONG WAY for a device that sends
					# more than one type. A bare tag sending 12 passes {12} <= {07,12} and may claim an
					# airpods case's lineage, while the case can never claim the tag's. Measured at
					# 23:15:26: a plain tag and the case's own next mac both claimed D2:82, both at -68,
					# so ROTTIE could not separate them and the case lost its own lineage to a stranger.
					# An EXACT match is strictly stronger evidence than a subset, and it is evidence we
					# already had and were throwing away by going straight to signal
					mineD, mineSame     = abs(p["rssi"] - oRssi), (p.get("types", "") == oTypes)
					best,  bestSame     = None, False
					for m2 in sorted(others):
						if m2 == mac or oMac not in others[m2]:	continue
						d2, same2 = abs(rivals[m2][0] - oRssi), (rivals[m2][1] == oTypes)
						# the STRONGEST rival, not the closest one: exact beats subset, and signal
						# only ranks within the same kind
						if best is None or (same2, -d2) > (bestSame, -best):	best, bestSame = d2, same2
					if best is not None and mineSame != bestSame:
						# ONE OF US IS AN EXACT MATCH AND THE OTHER IS NOT, so there is nothing to
						# arbitrate and signal is not consulted at all. The loser simply steps aside -
						# NOT burnt, because the winner is entitled to it, and when the winner's own
						# claim settles the loser's will find the lineage already gone
						if not mineSame:
							p["why"].append("{} claimed by an exact type match, ours is only a subset".format(
									oMac[-5:]));		continue
					elif best is not None and mineD - best > ROTTIE:
						# THE RIVAL IS CLEARLY CLOSER, so this is not a contest - it is a loss, and the
						# two are not the same thing. Burning the lineage here would deny it to a claim
						# that plainly deserves it, which is the very mistake the arbitration exists to
						# stop. Step aside instead and let the better claim take it when it settles
						p["why"].append("{} claimed by a closer mac ({:.0f} vs {:.0f} dBm off)".format(
								oMac[-5:], mineD, best));		continue
					elif best is not None and best - mineD <= ROTTIE:
						p["why"].append("{} also claimed by another mac ({:.0f} vs {:.0f} dBm off)".format(
								oMac[-5:], mineD, best))
						# AND IT IS BURNT FOR THE RIVAL TOO. Refusing only OUR claim would hand the
						# lineage to whichever of us happened to fall due second, because by then the
						# first claim has been popped and there is no rival left to see. Contested
						# means NOBODY gets it - the same rule as "could be any of ..", applied to the
						# other side of the contest. Their other candidates are untouched
						for m2 in sorted(others):
							if m2 == mac or oMac not in others[m2]:		continue
							del others[m2][oMac]
							if m2 in self.rotPending:
								self.rotPending[m2]["cands"].pop(oMac, None)
								self.rotPending[m2]["why"].append("{} contested with {} - neither took it".format(
										oMac[-5:], mac[-5:]))
						continue
					keep[oMac] = tagId
				if len(keep) == 1:
					oMac = sorted(keep)[0]
					self.commitRotation(mac, oMac, keep[oMac], now)
					continue
				if len(keep) > 1:
					self.logRot("ROT?  {} could be any of {} - refusing, it takes a new tagId".format(
							mac, ",".join(sorted(keep))))
				c["tagId"]        = self.nextTagId
				self.nextTagId   += 1
				self.tagIdOf[mac] = c["tagId"]
				self.logRot("ROTX  {} no lineage matched, fresh tagId:{} - {} candidate(s) turned down: {}".format(
						mac, c["tagId"], len(p["why"]), "; ".join(p["why"][:8]) or "none in range at all"))
		except Exception:
			U.logger.log(20, "", exc_info=True)

	def commitRotation(self, mac, oMac, tagId, now):
		"""Hands one lineage from oMac to mac, once the wait has confirmed oMac really stopped.

		Lifted out of matchRotation() unchanged when the decision moved here, so that the bookkeeping
		that keeps a lineage from being held twice lives in exactly one place.

		Inputs:
		    mac (str): the mac inheriting
		    oMac (str): the mac it is the continuation of
		    tagId (int): the lineage
		    now (float): epoch seconds
		Outputs:
		    None
		"""
		# the lineage has moved on: it must not be inherited a second time
		if oMac in self.goneTags:	del self.goneTags[oMac]
		# and it no longer owns it either - the lineage has moved to the new mac, and leaving
		# it in ownTag would hand it back the moment the old mac reappeared
		self.ownTag.pop(oMac, None)
		if oMac in self.cands:		self.cands[oMac]["tagId"] = None
		self.tagIdOf.pop(oMac, None)
		self.rotLast[tagId] = (oMac, mac, now)
		if mac in self.cands:		self.cands[mac]["tagId"] = tagId
		self.tagIdOf[mac] = tagId
		self.logRot("ROT   {} -> {} same tag, tagId {} kept - silent {:.0f}s since the claim".format(
				oMac, mac, tagId, ROTCONFIRM))

	def slotOf(self, mac):
		"""The slot this mac holds, or "--" while it holds none.

		"--" is the normal state for most of what this sees: a mac only gets a slot once it is a
		MEMBER, so candidates below joinRssi, frames still short of minPackets, and anything
		arriving after all MAXSLOTS are taken all read "--". That is the useful part of putting it
		on the frame line - it says at a glance whether this frame is feeding a counted tag or
		just being watched.

		Inputs:
		    mac (str): the mac to look up
		Outputs:
		    str: "01".."NN", or "--"
		"""
		for slot in self.slots:
			if self.slots[slot] == mac: return slot
		return "--"

	@staticmethod
	def battery(status):
		if status is None: return ""
		return BATTERY[(status >> 6) & 3]

	@staticmethod
	def statusBits(status):
		"""The status byte spelled out: "14=00|010100 batt:full". ALWAYS 26 CHARACTERS.

		ONLY THE TOP TWO BITS ARE ESTABLISHED - they are the battery level, decoded here at the
		end. The other six have no confirmed meaning in any published work on offline finding, so
		they are printed raw rather than given invented labels, split off by the "|" so it is
		obvious which half is known and which is guesswork waiting to happen. Same reasoning as
		the hint byte: this is logged so it can be correlated against devices whose identity is
		known, and a label that turns out to be wrong is worse than no label.

		THE BATTERY WORD IS PADDED, and that is the point of the fixed width: it runs from "low"
		to "critical", so an unpadded one walks every column after it sideways and the log stops
		being scannable.

		Inputs:
		    status (int or None): the status byte
		Outputs:
		    str: "14=00|010100 batt:full  ", or "--" padded to the same width
		"""
		if status is None: return "{:<26}".format("--")
		return "{:02X}={:02b}|{:06b} batt:{:<8}".format(
				status, (status >> 6) & 3, status & 0x3F, BATTERY[(status >> 6) & 3])

	def checkDebugFile(self, now):
		"""Lets the debug level be set ON THE RPI, without going through indigo and a parameter push:

		    echo 2 > /home/pi/pibeacon/temp/findmy.debug     # + the apple frames that were rejected
		    echo 1 > /home/pi/pibeacon/temp/findmy.debug     # summary + the find my frames only
		    echo 0 > /home/pi/pibeacon/temp/findmy.debug     # off
		    rm       /home/pi/pibeacon/temp/findmy.debug     # back to whatever the device says

		0/1/2 and 0/10/20 are both accepted - 10 and 20 read as 1 and 2, since the log levels are
		the numbers most likely to be typed here out of habit.
		The FILE WINS while it exists, and deleting it hands control back to the device dialog.
		Unlike the marker file this one is not consumed: it is a switch, not a message, and a
		switch that erased itself would be off again a second later.
		Checked every 5 s, so a change takes effect within about that - including the filter width
		in beaconloop, which reads this level on every frame.

		Inputs:
		    now (float): epoch seconds
		Outputs:
		    None
		"""
		if now - self.lastDebugCheck < 5.: return
		self.lastDebugCheck = now
		want = None
		src  = "device"
		try:
			for fName in self.debugFiles:
				if not os.path.isfile(fName): continue
				f = open(fName, "r")
				txt = f.read().strip().lower()
				f.close()
				want = {"0": 0, "1": 1, "2": 2, "10": 1, "20": 2, "off": 0, "on": 1}.get(txt)
				if want is None:
					U.logger.log(20, "findMyGroup {}: '{}' is not a debug level - use 0, 1 (or 10), 2 (or 20)".format(fName, txt))
					return
				src = fName
				break
			if want is None: want = self.debugParam		# no file - the device dialog decides again
			if want != self.debug:
				U.logger.log(20, "findMyGroup debug level {} -> {}  (from {})".format(self.debug, want, src))
				self.debug = want
		except Exception:
			U.logger.log(20, "", exc_info=True)

	# ------------------------------------------------------------ calibration
	def checkMarker(self):
		try:
			if os.path.isfile(self.markerFile):
				f = open(self.markerFile, "r")
				mm = f.read().strip().replace(",", ";")
				f.close()
				os.remove(self.markerFile)
				if mm != self.marker:
					self.marker    = mm
					# WRITTEN ONCE, NOT ON EVERY ROW - see writeCalibrationRows(). The next batch
					# of rows carries it and the ones after that leave the column empty
					self.markerDue = True
					U.logger.log(20, "findMyGroup marker: '{}'".format(mm or "(cleared)"))
		except Exception:
			U.logger.log(20, "", exc_info=True)

	def trimCsv(self, fName):
		"""Drops the OLDEST rows so the calibration csv stays under CSVMAXBYTES.

		A SIZE CAP, NOT AN AGE ONE, because temp/ is a 2 MB tmpfs holding findMyGroup.state as well:
		what matters is that this file cannot grow into that, not how old its rows are. It also means
		there is nothing to sweep up on a schedule and no second file to keep track of.

		The newest rows are the ones worth keeping - this is a rolling record of what is on the air
		now - so the tail survives and the head goes. Cut on LINE boundaries, never mid-row, and the
		column header is written back at the top so a trimmed file still starts by saying what its
		columns are.

		Inputs:
		    fName (str): the csv
		Outputs:
		    None
		"""
		try:
			keepBytes = int(CSVMAXBYTES * 0.75)		# leaves room to grow again before the next trim
			f = open(fName)
			lines = f.readlines()
			f.close()
			total, out = 0, []
			for ln in reversed(lines):
				total += len(ln)
				if total > keepBytes:	break
				out.append(ln)
			out.reverse()
			f = open(fName, "w")
			f.write(",".join(CSV_FIELDS) + "\n")
			f.writelines(out)
			f.close()
			self.lastHeader = time.time()		# one was just written, do not follow it with another
			U.logger.log(20, "findMyGroup calibration csv over {}kB, oldest rows dropped, {} rows kept".format(
					CSVMAXBYTES // 1024, len(out)))
		except Exception:
			U.logger.log(20, "", exc_info=True)

	def writeCalibrationRows(self, now):
		try:
			host    = "pi{}".format(G.myPiNumber)
			fName   = self.csvFile
			newFile = not os.path.isfile(fName)
			rows = []
			# THE HEADER DECISION IS MADE HERE, not after the rows, because the marker rides with
			# it - see markerCell below. It is still only ACTED on if there turn out to be rows
			wantHeader = newFile or now - self.lastHeader >= HEADEREVERY

			# THE MARKER GOES ON ONE ROW, NOT ON ALL OF THEM. It is an EVENT - "from here on, the
			# tag is at the street door" - and the same sentence repeated on every row of a ten
			# minute session is the same fact written a thousand times, in a file capped at
			# CSVMAXBYTES on a 2 MB tmpfs. Whoever reads the file forward-fills it instead;
			# findmy_merge.py does exactly that.
			# RESTATED WITH EVERY HEADER BLOCK, and for the same reason the header is repeated:
			# these files are read by scrolling into the middle of one, and a marker written once
			# at the top is no more use there than a header written once at the top. It also
			# survives trimCsv(), which drops the OLDEST rows - a marker written exactly once
			# would eventually be trimmed away and orphan every row after it.
			# "-" MEANS CLEARED, and is the one thing an empty cell cannot say: a blank means
			# "same as the row above" to anything forward-filling, so clearing the marker needs a
			# mark of its own. Only ever written on the row where the clearing happened
			if self.markerDue:								markerCell = self.marker if self.marker != "" else "-"
			elif wantHeader and self.marker != "":			markerCell = self.marker
			else:											markerCell = ""

			# tenths: "2026-09-23T15:57:12.6". %f is 6 digits, one is plenty for rows written
			# every logEverySecs, and it is what "epoch" used to be kept around for
			ts = datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-5]
			for mac, c in self.cands.items():
				rr = c["interval"]
				if not rr: continue
				st = c["status"]
				hi = c.get("hint")
				rw = c.get("raw") or ""
				ty = "|".join("{:02X}".format(t) for t in sorted(c.get("types", {})))	# "|", the row joins on ","
				rows.append(",".join(str(x) for x in [
					ts, host, mac, padCsv(indCsv(c["indicator"]), CSVWIDTH["distanceIndicator"]),
					padCsv(None if st is None else "{:02X}".format(st), CSVWIDTH["status"]),
					padCsv(None if hi is None else "{:02X}".format(hi), CSVWIDTH["hintByte"]),
					padCsv(typesCsv(c.get("types", {})), CSVWIDTH["appleTypes"]),
					padCsv(battCsv(self.battery(st)), CSVWIDTH["battery"]),
					numCsv(len(rr), CSVWIDTH["packets"]),
					rssiCsv(median(rr)),
					intCsv(min(rr), CSVWIDTH["rssi_minmax"]), intCsv(max(rr), CSVWIDTH["rssi_minmax"]),
					rssiCsv(self.smoothed(c)),
					1 if c["member"] else 0,
					numCsv(now - c["first"], CSVWIDTH["age_s"]),
					padCsv(markerCell, CSVWIDTH["marker"]),
					numCsv(len(rw) // 2, CSVWIDTH["raw_len"]), rw]))
				markerCell = ""			# one row carries it; the rest of this batch does not
				c["interval"] = []
			lines = []
			if rows:
				# THE HEADER IS REPEATED every HEADEREVERY, not written once at the top. These
				# files run for a day and are read by scrolling into the middle of one, where a
				# header at line 1 is no help at all - 18 unlabelled columns is not something
				# anybody counts out by hand. Only ever emitted in front of real rows, so an idle
				# period cannot fill the file with headers.
				# NOTE for anything parsing this: the repeated header appears as a DATA ROW. Skip
				# lines starting with "timestamp,".
				if wantHeader:
					self.lastHeader = now
					lines.append(",".join(CSV_FIELDS))
				# CONSUMED ONLY NOW, and not when the rows were built: a pass in which nothing had
				# a reading writes no rows at all, and a marker that was stamped onto a row that
				# never reached the file would be lost. It waits for a batch that exists
				self.markerDue = False
				lines.extend(rows)

			if lines:
				# temp/ belongs to the pi user, so this is a plain append - no writeFileAsRoot and
				# no chown, which is the whole reason the file moved here
				f = open(fName, "a")
				f.write("\n".join(lines) + "\n")
				f.close()
				if os.path.getsize(fName) > CSVMAXBYTES:	self.trimCsv(fName)
		except Exception:
			U.logger.log(20, "", exc_info=True)
