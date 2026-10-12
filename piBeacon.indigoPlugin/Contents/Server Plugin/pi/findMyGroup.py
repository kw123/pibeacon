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
      "maxSlots":               "15",       # how many members may hold a slot (ceiling MAXSLOTS)
      "ambiguityWait":          "55",       # secs to keep re-judging a claim that only ambiguity refuses, 0 = off
      "sendEverySecs":          "60",       # periodic update (trigger "time", batched with beacon msgs)
      "dropFromBeaconPipeline": "1",        # "1": Find My frames are not processed as beacons (no new-beacon spam from rotating macs)
      "calibrationLog":         "0",        # "1": write csv rows to findMyGroup.csv (same columns as findmy_scan.py)
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

VERSION = "1.0"			# printed at startup by U.setLogging() -> U.versionLine()

import os
import time
import datetime
import json
import random

import piBeaconUtils as U
import piBeaconGlobals as G

_findMyGroupDebug = False
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
CSVMAXBYTES  = 20 * 1024 * 1024	# the calibration csv is CAPPED, oldest rows dropped - see trimCsv().
						# 20 MB is about 40 hours at a busy rPi's row rate, which is what this needed to be
						# useful: the questions it answers - where to put join/leave, how long a mac lives,
						# whether nearby and separated rotate on one clock - are all measured over hours,
						# and the 200 kB it used to be held 25 minutes. See findmy_rotation.py.
						# IT COULD ONLY BE 200 kB WHILE IT LIVED IN temp/, a 2 MB tmpfs shared with
						# findMyGroup.state, where an uncapped log would eventually have taken the state
						# file down with it. It does not live there any more - see csvFile in __init__ -
						# so the cap is now only about not filling the card, and 20 MB does not
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
ROTAMBIG     = 55.		# DEFAULT for the group device's "wait out an ambiguous rotation" - 0 there turns
						# this off and restores "refuse at ROTCONFIRM".
						# AMBIGUITY IS NOT A VERDICT, IT IS A "NOT YET". When the only thing left refusing
						# a claim is that two candidates still fit, the claim is kept and re-judged every
						# tick until this, instead of minting a lineage at ROTCONFIRM and giving up.
						# MEASURED, 12:30:24: a newcomer was left holding DC:ED and 19:4D, refused, and took
						# a new tagId - and DC:ED was then claimed by its OWN exact successor 18 s later and
						# committed at 12:31:03. Waiting would have left 19:4D alone and matched it. The
						# evidence was not missing, it had not ARRIVED: one wave's newcomers surface over
						# ~40 s as the rpi first hears each of them, while every claim judged itself at its
						# own +20 s and could not see a rival that would turn up at +38.
						# A candidate set only ever SHRINKS - a candidate speaks again, or somebody else's
						# commit takes it - so waiting can turn two into one but never one into two.
						# 55 AND NOT MORE: the mac is held out of members the whole time, and past
						# memberDownDelaySecs (60, plugin side) the tag's existing device would blink down
						# and come back. This stays under it with room to spare, and 39 s was enough above
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
ROTBATCH     = 5.		# dBm. HOW MUCH BETTER THE WHOLE ANSWER HAS TO BE than the best answer that
						# breaks one pair in it, before that pair is believed - see rotBatchSolve().
						# TAGS ROTATE IN WAVES, not one at a time: measured 2026-09-27, EIGHT of the
						# twelve macs on one rpi were born inside a single TEN SECOND window. Of the 28
						# pairs in that wave, 8 shared a battery word and sat inside ROTRSSI of each
						# other and 4 of those were inside ROTTIE, so the arbitrations came down to 1,
						# 1 and 4 dBm.
						# WHAT IS WRONG WITH THAT IS THE MARGIN, NOT A KNOWN WRONG ANSWER, and the
						# distinction is worth keeping straight: that wave was in fact resolved
						# CORRECTLY - the candidates it turned down were all still alive and came back
						# or rotated later, so the two macs that took fresh tagIds really were new tags.
						# The case for solving a wave as one problem is that 1 dBm is not evidence on a
						# signal that wanders 4.8, and that the contested branch BURNS a lineage for
						# claims that never contested it - both structural, neither yet observed doing
						# damage. So this only ever ADDS a commit the pairwise path would have refused;
						# it never overrides one the pairwise path makes.
						# 5 dBm BECAUSE THAT IS THE NOISE: the smoothed signal of a mac that has not
						# moved wanders a median of 4.8 dBm (range 1.5 to 8.0 over 12 macs on one rpi,
						# same capture). A margin under that is deciding on noise; this is the smallest
						# number that is not. It is bigger than ROTTIE on purpose - ROTTIE separates two
						# claimants for ONE lineage, this asks whether a whole assignment is stable
ROTGRID      = 900.		# seconds. THE ROTATION CLOCK. A find my mac is not replaced at an arbitrary
						# moment - it changes on a 15 minute grid aligned to the unix epoch, IN BOTH MODES,
						# which is what the key schedule behind these addresses would produce.
						# MEASURED, NOT DOCUMENTED - 69 hours on two rpis, 155 usable mac lives. Births
						# taken mod 900 clustered with a mean resultant length of 0.851 over 73 nearby macs
						# at a phase of +12 s, and 0.908 over 14 that had been seen in both modes at +35 s.
						# THE ROW THAT MAKES IT REAL IS 1800: a 1800 or 3600 second grid is also a 900
						# second grid, so a high score at 900 alone proves nothing - but the same macs
						# scored 0.137 at both 1800 and 3600, so the births land on the 900 lattice and on
						# no multiple of it. See findmy_rotation.py, which is the tool that measured this.
ROTGRIDNEAR  = 90.		# seconds either side of a boundary that count as ON it - about one standard
						# deviation of the measured spread (81 s). A newcomer born in here is where a
						# rotation is expected to appear and pays nothing.
						# WIDE ENOUGH TO ABSORB THE PHASE, which is why no phase constant is needed: the
						# observed lag was +2 to +35 s, comfortably inside this, so the boundary can be
						# taken as the epoch multiple itself. It would still hold if another house measured
						# a different lag, as long as it is under a minute and a half
ROTGRIDFAR   = 250.		# and beyond this - about three deviations, ie the middle of a slot - the full
						# penalty. Linear in between, so nothing turns on a hard edge
ROTGRIDTIE   = 0.001	# what the clock is worth INSIDE THE WAVE SOLVE: a tie-break and nothing more.
						# IT MUST NOT ENTER THE COST AT FULL WEIGHT, and the first cut of this did, which a
						# test caught: rotBatchSolve() forces a pair when breaking it costs more than
						# ROTBATCH extra, so anything added to the cost moves that margin - and a penalty on
						# the newcomer that signal FAVOURED subtracts from the very margin that was about to
						# force it. A pairing 6 dBm ahead, forced before, stopped being forced once a 3 point
						# clock penalty ate into its lead. The clock made a correct answer less certain.
						# At this weight it can only separate arrangements that cost EXACTLY the same, where
						# the solver would otherwise pick by iteration order, and three thousandths of a dBm
						# can never reach ROTBATCH. The real use is in the pairwise tie - see ROTGRIDPEN
ROTGRIDPEN   = 3.		# dBm-equivalent. DELIBERATELY EQUAL TO ROTTIE, which is the whole design of
						# this: ROTTIE is the margin inside which two claims are called indistinguishable
						# by signal, so a penalty that cannot exceed it can BREAK A TIE and can never
						# overturn a decision that signal already settled. It is far below ROTTYPEPEN and
						# ROTMODEPEN too, so an apple-type mismatch still outranks it absolutely.
						# ONLY IN THE WAVE SOLVE - see rotBatchSolve(). The pairwise path is untouched: this
						# is a prior about WHEN a rotation happens, and it earns its place where several
						# tags rotate together and the signal test has nothing left to separate them
ROTTYPEPEN   = 100.		# the cost added to a pairing whose apple types are only a SUBSET rather than
						# an exact match. Far beyond any dBm difference, so it cannot be traded against
						# signal - the same rule the pairwise path uses, where exact beats subset
						# outright and signal only ranks within one kind. See resolveRotClaims()
ROTMODEPEN   = 200.		# and the cost of a MODE-SWITCH pairing - separated <-> nearby across the rotation,
						# or 07 turning up with nearby. Above ROTTYPEPEN, so a subset match beats it just as
						# an exact one beats a subset. See matchRotation(), where these stopped being refusals.
						# MEASURED 2026-09-28 on one airpods set: separated D4:B9 (12 only) stopped at
						# 10:19:02.6 and nearby CE:25 (07|12) started in the same tenth of a second; later
						# separated CE:25 stopped at 10:41:32.0 and nearby E6:4F (07|12) started at 33.0,
						# same -68, same battery. No lid was opened - 07 comes with being near the owner.
						# Both old tests refused that second one, it minted a fresh lineage, and the set
						# showed as TWO airpods for the length of the plugin's member down-delay
BATCHMAXN    = 8		# most newcomers, and most lineages, in one batch solve. The search is a
BATCHMAXM    = 12		# bitmask DP over the lineages, so it is 2^M * N and both have to be bounded.
						# 8 x 12 is 400k cheap operations at the worst, and it is run once per pass
						# over a set that is normally 3 or 4 macs. Beyond this the pairwise path runs
						# as before and says so in the log - refusing to guess is the fallback, and a
						# batch that big has no clean answer anyway
FEEDTRUST    = 120.		# HOW LONG A SILENT FEED IS BELIEVED before the room really is called empty -
						# see the expiry pass in tick(). A mac is expired after expireSecs without a
						# packet, which is right when that mac stopped; but "last" only moves when a
						# frame is DELIVERED, so a stall in the handoff expires EVERY mac at once while
						# all of them are still in the room. Measured 2026-09-27: 23:F4 was absent from
						# five consecutive summaries and came back with 62 packets in ONE row - the
						# radio had heard it throughout - and 20:23:18 logged 11 s with nothing from
						# anybody, one second past expireSecs for the whole house.
						# IT HAS TO BE BOUNDED, and that is the whole reason for a number here rather
						# than "trust it": a dongle that has genuinely died is also silent, and it must
						# end up reporting an empty room rather than a full one for ever. 120 s, the
						# same as GONEKEEP and for the same reason - past that, silence really has
						# stopped being ambiguous
FEEDMINMACS  = 2		# and it takes at least this many macs to make that inference at all. With ONE
						# mac in range its silence and the feed's silence are the SAME event and there
						# is nothing to tell apart, so holding it would just be a late count. From two
						# up, all of them stopping in the same second is far more likely to be the one
						# thing they share than a coincidence of departures
GAPGRACE     = 60.		# AFTER THE FRAME STREAM ITSELF STOPPED - a beaconloop restart, or the handoff
						# from it stalling - how long a mac that cannot be accounted for is PARKED rather
						# than given a fresh lineage.
						# WHY THIS IS NOT A ROTATION QUESTION AT ALL: every test in matchRotation() reads
						# the recent past, and after a gap there is no recent past to read. The pool is
						# cands + goneTags, both of which a restart empties, so a mac that rotated while we
						# were not listening found NOTHING in range, was not put on rotPending, and minted a
						# fresh lineage on the spot - no ROT~, no ROTCONFIRM, none of the machinery that
						# exists to stop exactly that. The log line even said "none in range at all", which
						# is true and completely misleading: nothing was in range because nothing was
						# remembered.
						# WHAT THE WAIT BUYS, and it is the whole of it: the tags that are STILL HERE come
						# back on their own macs within seconds and take their lineages back through
						# tagIdOf / ownTag, which also pops them out of goneTags. So the pool is worthless
						# at the moment the feed resumes and correct a few seconds later. Parking until then
						# costs the newcomer some latency and turns a guess into an answer.
						# 60 AND NOT MORE, for ROTAMBIG's reason: the mac is held out of members the whole
						# time, and memberDownDelaySecs is 60 on the plugin side. A tag that really is new
						# appears one grace later, once, instead of a restart growing the group by a device
						# for every tag that happened to rotate during it
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


def bestAssignment(cost, n, m, forbid=None):
	"""The cheapest way to pair n newcomers with m lineages, at most one each - see rotBatchSolve().

	MOST PAIRS FIRST, THEN CHEAPEST. A rotation wave conserves count: the macs that appeared are the
	macs that left, so an answer that accounts for five of them beats one that accounts for four at
	any price. Cost only ranks answers that explain the same number of tags.

	A BITMASK DP AND NOT A PERMUTATION SEARCH, because the sets are not the same size and need not be:
	eight newcomers can face six lineages, two of them really new. Walking the newcomers in order and
	carrying "which lineages are spoken for" as a bit per lineage handles both, and it is 2^m * n
	states rather than the m! a permutation search would need - at BATCHMAXN/BATCHMAXM that is the
	difference between 400 thousand operations and forty million.

	NOT HUNGARIAN, deliberately: this has to be read and trusted by whoever is looking at a wrong
	rotation six months from now, and it is called on sets of three or four. An O(n^3) algorithm that
	nobody in this house can check is a bad trade for microseconds nothing is waiting on.

	Inputs:
	    cost (dict): {(i, j): float} the cost of pairing newcomer i with lineage j. A pair that is
	            not in here is not allowed at all - that is where every hard filter has already been
	            applied, in matchRotation() and rotAlive()
	    n (int): how many newcomers
	    m (int): how many lineages
	    forbid (tuple): one (i, j) to pretend is not allowed, for the stability test
	Outputs:
	    tuple: (pairs matched, total cost, {i: j}) - ({}, and 0 pairs, when nothing can be paired)
	"""
	# dp[mask] = (-pairs, cost, {i: j}) for the newcomers seen so far, "mask" = lineages taken.
	# MINIMISED AS A TUPLE, so -pairs in front is what makes "most pairs" beat "cheapest"
	dp = {0: (0, 0., {})}
	for ii in range(n):
		nxt = {}
		for mask in dp:
			negP, cc, pairs = dp[mask]
			# this newcomer takes nothing - always allowed, and it is what lets a genuinely new tag
			# fall out of the batch instead of being forced onto somebody's lineage
			if mask not in nxt or (negP, cc) < nxt[mask][:2]:	nxt[mask] = (negP, cc, pairs)
			for jj in range(m):
				if mask & (1 << jj):					continue
				if (ii, jj) not in cost:				continue
				if forbid is not None and forbid == (ii, jj):	continue
				mk = mask | (1 << jj)
				cand = (negP - 1, cc + cost[(ii, jj)])
				if mk not in nxt or cand < nxt[mk][:2]:
					pp = dict(pairs); pp[ii] = jj
					nxt[mk] = (cand[0], cand[1], pp)
		dp = nxt
	best = None
	for mask in dp:
		negP, cc, pairs = dp[mask]
		if best is None or (negP, cc) < (best[0], best[1]):	best = (negP, cc, pairs)
	if best is None:	return (0, 0., {})
	return (-best[0], best[1], best[2])


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
		self.maxSlots               = 15
		self.rotAmbig               = ROTAMBIG
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
		# ONE file, fixed name, in the pibeacon dir. Not /var/log and not a file per day: it is
		# read with "cat" while standing next to the rPi, it is written by the pi user without
		# any root dance, and it is size-capped rather than age-cleaned, so there is nothing to
		# sweep up.
		# WRITTEN STRAIGHT TO THE CARD, and no longer to temp/ with a copy out every PERSISTSECS.
		# That arrangement was there to spare the card the 10 second appends, and it cost more
		# than it saved: it copied the WHOLE file every time one row had been added to it, so a
		# 200 kB log wrote 200 kB to the card 432 times a day - about 86 MB - to carry 12 MB of
		# actual rows. Appending the rows where they belong writes those 12 MB and nothing else,
		# which is SEVEN TIMES LESS card traffic, in more writes of much smaller size.
		# AND IT IS WHAT MAKES A USEFUL CAP POSSIBLE. In temp/ the log was bounded by a 2 MB tmpfs
		# it had to share with the state file; here it is bounded by the card, so 20 MB and 40
		# hours of history costs nothing and the file survives a reboot by itself. The restore
		# dance that used to put it back after one - restoreCsv(), persistCsvFile(), csvStamp() -
		# is gone with the reason for it.
		# THE COST, so it is on the record: appends go from 432 a day to 8640. The bytes are what
		# wears a card rather than the syscalls, and they went DOWN - but if this ever needs to be
		# gentler still, buffer the rows in memory and flush them on the PERSISTSECS tick. It is
		# not done here because the file is read live during a calibration walk, and a log that is
		# up to 200 s behind what the rPi is hearing is a different tool
		self.csvFile                = G.homeDir + "findMyGroup.csv"
		self.markerFile             = G.homeDir + "temp/findMyGroup.marker"
		self.stateFile              = G.homeDir + "temp/findMyGroup.state"
		# temp/ IS A TMPFS: writing there every send costs no SD wear but does not survive a
		# reboot, so the same content goes to the pibeacon dir every PERSISTSECS and is read back
		# when temp/ comes up empty. Losing 5 minutes of it is fine; losing the whole trail is not
		self.persistFile            = G.homeDir + "findMyGroup.state"
		self.reset()
		self.restoreSlots()

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
		# THE FEED'S OWN LIVENESS, which is not the same question as any one mac's - see GAPGRACE.
		# A mac's silence only means something if SOMEBODY ELSE was heard during it. One mac missing
		# while eleven others report every sample is that mac; all twelve going quiet together is
		# the stream, and carries no information about any tag at all. Measured 13:40:21-13:41:03:
		# 23:F4 alone was absent for 52 s and came back with 62 packets in one row - the radio had
		# heard it the whole time - while it sat in another mac's candidate list as "gone"
		self.lastFrame      = 0.	# when a find my frame from ANY mac last arrived, 0 = none yet
		self.feedGap        = 0.	# the measured length of the gap still inside GAPGRACE, 0 = none
		# A (RE)START IS A FEED GAP and the largest one there is: everything before it went unheard
		# by definition. Set here rather than waiting to measure one, because lastFrame is 0 and
		# there is nothing to measure it against - the gap is known without being observed
		self.feedGapUntil   = now + GAPGRACE
		self.feedGapWhy     = "restart"		# what caused the gap in force - see gapWhy()
		self.feedHeld       = False			# the expiry pass is holding a silent feed - see tick()
		self.lastRotWhy     = []	# why matchRotation turned each candidate down - see logRot()
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
		# WHICH NUMBERING THE tagIds BELONG TO, and it is not a process id - it identifies the COUNTER.
		# nextTagId is only meaningful inside one run of it: if the state file cannot be read the
		# counter restarts at 1 and starts handing out ids the plugin still remembers as OTHER tags,
		# and a tagId is worth nothing the moment it can mean two things. The plugin cannot tell that
		# from the counter alone - after one restart every id is small, so the next restart climbs
		# past them within minutes and nothing looks wrong. So the numbering says who it is.
		# MINTED HERE AND OVERWRITTEN BY restoreSlots() when there IS something to restore, which is
		# exactly the rule wanted: a clean restart keeps its id along with its counter, and a lost
		# state file gets a new one. reset() is also called when the group is switched on or off, and
		# that restarts the counter too, so minting there is right rather than incidental
		# RANDOM, NOT DERIVED FROM THE CLOCK AND THE PID. That was the first cut and a test caught it:
		# two mints inside the same second from the same process produced the SAME id, so a restart
		# that lands in one second - or a pid that repeats modulo the byte kept - would have looked
		# like the same numbering and the stale lineages would have been trusted. The low 16 bits of
		# the clock are kept in front because they make the ids read in order in a log, which is worth
		# something when two rPis are being compared; the 24 random bits after them are what actually
		# make it unique. Only a collision with the IMMEDIATELY PRECEDING id could mislead - a stress
		# test of 2000 mints showed the birthday rate over 16 bits was visible, so it is 24: one in
		# 16.7 million per restart, against a consequence of one wrong device
		self.runId          = "{:04x}{:06x}".format(int(now) & 0xFFFF, random.randint(0, 0xFFFFFF))
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
			srcAt = 0.
			if not os.path.isfile(self.stateFile) and os.path.isfile(self.persistFile):
				# READ BEFORE THE COPY. The copy's own mtime says "a moment ago" and would claim every
				# mac in it was a member just now - which after a reboot is precisely what it was not,
				# and that timestamp is what dates the restored lineages below
				try:	srcAt = os.path.getmtime(self.persistFile)
				except Exception:	pass
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
			# WHEN THE MACS IN THIS FILE WERE LAST KNOWN TO BE HERE. members carries no timestamp of
			# its own - it is written from the live candidates - so the file's own mtime is the best
			# statement there is, and it is what dates the lineages restored out of it
			if srcAt <= 0.:
				try:	srcAt = os.path.getmtime(src)
				except Exception:	srcAt = time.time()
			lineages = 0
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
						# THE LINEAGE COMES BACK WITH THE MAC: a tag still here re-joins on the SAME mac
						# within seconds, and the indigo device must not be told it is a different tag
						# just because this program restarted.
						# INTO ownTag AND NOT tagIdOf. tagIdOf is the LIVE map: the only place an entry
						# is written is at join, and the only place one is removed is the expiry pass in
						# tick(), which walks self.cands. A mac restored from a FILE is not in cands, so
						# an entry for one that never came back was never pruned at all - it sat there
						# for the life of the process holding a lineage nothing could inherit, because
						# matchRotation() pools cands + goneTags and never looks at tagIdOf. Worse than
						# the bytes, it was unbounded IN TIME: a state file written a fortnight ago
						# still handed its macs their lineages silently, straight past the two days
						# ownTag deliberately allows and without the ROT= line that says it happened.
						# NOTHING IS LOST BY MOVING IT - ownTag is the same statement, "this mac owns
						# this lineage", matched by the identical mac only, and it already has OWNKEEP,
						# the OWNMAX ceiling and the log line. The tag gets the same tagId, one branch
						# later. And tagIdOf now means what it says: a mac that is here
						if isinstance(mm[slot], dict) and mm[slot].get("tagId") is not None:
							oMac = mm[slot].get("mac", "")
							if oMac != "":
								tagId = int(mm[slot]["tagId"])
								self.ownTag[oMac] = {"tagId": tagId, "last": srcAt}
								lineages += 1
								if tagId >= self.nextTagId:	self.nextTagId = tagId + 1
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
			# THE NUMBERING COMES BACK WITH THE COUNTER, and the two belong together - see runId in
			# reset(). Keeping it is what tells the plugin this is the SAME numbering it already knows,
			# so nothing it has stored is thrown away by an ordinary restart.
			# A STATE FILE FROM BEFORE THIS VERSION HAS NONE, and then the freshly minted one stands:
			# the plugin sees a numbering it has not met and drops its stored lineages once, on the
			# upgrade. One device per tag, once - the alternative is trusting ids whose provenance
			# genuinely is unknown, which is the whole thing being fixed
			rid = "{}".format(old.get("runId", "")).strip()
			if rid != "":	self.runId = rid
			try:	self.nextTagId = max(int(old.get("nextTagId", 1)), self.nextTagId)
			except Exception:	pass
			# the member lineages raise it as they are read, above - there is no pass over tagIdOf to
			# do it in any more, because nothing restores into tagIdOf. Whichever is higher wins, so
			# the order of the two does not matter

			# the mac -> own lineage memory, so a restart does not make every sleeping device a
			# stranger again. Silently skipped when an older state file has none
			try:
				for mm, vv in (old.get("ownTags", {}) or {}).items():
					if not isinstance(vv, list) or len(vv) < 2:	continue
					# DO NOT CLOBBER A MEMBER-DERIVED ENTRY read above. Its "last" is the file's mtime,
					# when the mac was still counted; an ownTags entry records when a mac EXPIRED, which
					# is necessarily earlier. The two cannot really describe the same mac at the same
					# time - a member is not expired - but a hand-edited file can say anything, and the
					# later of the two is the one that is true about when it was last here
					if mm in self.ownTag and self.ownTag[mm]["last"] >= float(vv[1]):
						if int(vv[0]) >= self.nextTagId:	self.nextTagId = int(vv[0]) + 1
						continue
					self.ownTag[mm] = {"tagId": int(vv[0]), "last": float(vv[1])}
					if int(vv[0]) >= self.nextTagId:	self.nextTagId = int(vv[0]) + 1
			except Exception:
				U.logger.log(20, "", exc_info=True)

			if len(self.slots) > 0 or len(self.slotHistory) > 0:
				U.logger.log(20, "findMyGroup restored {} slot(s), {} member lineage(s), {} remembered mac(s) and history for {} from {}, last written {:.0f}s ago".format(
						len(self.slots), lineages, len(self.ownTag), len(self.slotHistory), src,
						max(0., time.time() - srcAt)))
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
		self.maxSlots               = max(1, min(MAXSLOTS, num("maxSlots", 15, int)))
		# 0 TURNS IT OFF and the claim is refused the moment ROTCONFIRM is up, which is what this
		# did before the wait existed. Never shorter than ROTCONFIRM when on - a wait that expires
		# before the first judgement would be a setting that does nothing but look like it does
		self.rotAmbig               = num("ambiguityWait", ROTAMBIG)
		if self.rotAmbig > 0.:	self.rotAmbig = max(ROTCONFIRM, min(300., self.rotAmbig))
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
		self.debug                  = self.debugParam	and _findMyGroupDebug	# checkDebugFile overrides it if the file is there
		self.debugMac               = str(pp.get("debugMac", "")).strip().upper()
		self.logEverySecs           = max(2., num("logEverySecs", 10.))

		if self.enabled != wasEnabled:
			self.reset()
			# AND READ THE STATE FILE BACK, because the reset above has just thrown away everything
			# __init__ restored. THIS IS THE BUG THAT MADE "the state file is lost at every restart",
			# and the file was never the problem - the RESTORE was being discarded. __init__ sets
			# enabled False, resets, and restoreSlots() brings back nextTagId, the slot map, tagIdOf,
			# ownTag and the runId; then beaconloop's first readParams() lands here, enabled goes
			# False -> True, and the reset wiped the lot seconds later. restoreSlots() was never
			# called again, so nextTagId was 1 on EVERY start, every lineage was re-minted, and each
			# restart looked to indigo like a houseful of new devices. Measured on 2026-09-27: tagIds
			# re-numbered at 15:51 and again at 19:13, previousTagIds in the 2-20..2-29 range sitting
			# beside current ones of 2-1..2-9, and the same lineage id held by two devices at once.
			# ONLY WHEN IT IS NOW ON. Going the other way the reset is the whole point - the feature
			# was switched off, nothing should be left running - and there is nothing to come back to.
			# SWITCHED OFF AND ON AGAIN ALSO RESTORES, and that is right rather than incidental: the
			# indigo devices did not go anywhere while it was off, so their slots and lineages are
			# still the truth and forgetting them would renumber the house for no reason
			if self.enabled:	self.restoreSlots()
			if self.debug: U.logger.log(20, "findMyGroup {}: devId:{} join:{} leave:{} stable:{}s drop:{} calibrationLog:{}".format(
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
				if self.debug: U.logger.log(20, "findMyGroup seen  {}  rssi:{:>4}  apple types:{:<12} -> no find my (12) in it, ignored".format(
						mac, rssi, "|".join("{:02X}".format(t) for t in tt) or "none"))
			return False
		if now is None: now = time.time()
		self.update(mac, fm[0], fm[1], rssi, now, fm[2], fm[3], adv)
		return True

	def update(self, mac, indicator, status, rssi, now, hint=None, types=None, raw=None):
		# THE GAP IS MEASURED WHERE IT BECOMES VISIBLE, which is on the way back IN. tick() can only
		# ever see "it is quiet right now", and from up there a room that has genuinely emptied looks
		# exactly like a stalled feed - so a test there would either trust a dead radio forever or
		# expire a live tag anyway. Here it is a length between two frames that both arrived, so a
		# feed that never resumes never claims a gap, and nothing has to be believed on faith.
		# AGAINST expireSecs, not some new number: a gap shorter than that could not have expired
		# anybody, so it changed nothing and is not worth a word in the log
		if self.lastFrame > 0. and now - self.lastFrame > self.expireSecs:
			self.feedGap      = now - self.lastFrame
			self.feedGapUntil = now + GAPGRACE
			self.feedGapWhy   = "feed gap of {:.0f}s".format(self.feedGap)
			# LEVEL 20 AND NOT logRot, which is the only line here that breaks that rule on purpose.
			# The ROT lines are decisions and belong to whoever turned the debug menu on; this one is
			# the rpi saying it stopped hearing anything at all, and it is the first thing anybody
			# asking "why did a device appear" needs to see. Keeps the "ROT" prefix so the one grep
			# in logRot() still catches it along with the decisions it explains
			if self.debug: U.logger.log(20, "findMyGroup ROTG  no find my frame from ANY mac for {:.0f}s - a rotation across that cannot be inferred, newcomers parked {:.0f}s".format(
					self.feedGap, GAPGRACE))
		self.lastFrame = now
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
				if self.debug: U.logger.log(10, "findMyGroup BACK  {} after {:.0f}s, keeps age {:.0f}s and types {}".format(
						mac, now - back.get("last", now), now - c["first"],
						"|".join("{:02X}".format(t) for t in sorted(c["types"])) or "-"))
			else:
				if self.debug: U.logger.log(10, "findMyGroup NEW   {} dist:{} rssi:{}".format(mac, indicator, rssi))
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
			if self.debug: U.logger.log(20, "findMyGroup frame sl:{:<2} {:<17}  rssi:{:>4}  dist:{:<9}  status:{}  hint:{:<2}  types:{:<11}  pkt#{}".format(
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
					# A BACKSTOP SINCE 2026-09-27, not the restart path any more. It used to catch the
					# mac that was a member when the state file was written; that now comes back through
					# ownTag below, which dates it and logs ROT=. What is left for this to catch is a
					# mac that is in cands with a lineage and reaches JOIN again without having expired
					# - it cannot happen by any path here, and if it ever does, keeping the lineage is
					# the right answer. Cheap to leave, and the alternative is minting a duplicate
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
			if self.debug: U.logger.log(20, "findMyGroup {} is still here but its lineage was given to a rotation - new tagId:{}".format(
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

		# NOTHING AT ALL HAS BEEN HEARD, so nothing has been learned about any ONE tag - see
		# FEEDTRUST. A mac's silence is evidence when OTHER macs are being heard through it; when
		# every one of them stops in the same second, the one thing they share is the feed, and
		# expiring them all says the house emptied when what actually happened is that the rpi
		# stopped listening. The rotation side of this is already handled (see GAPGRACE) - this is
		# the COUNT, which until now fell to zero and climbed back on every stall.
		# HELD, NOT RESET: nothing is expired, so "last" and the member flags stay exactly as they
		# were and the macs that come back need no re-joining. Anything that genuinely went while
		# the feed was down expires on the first pass after it returns, one expireSecs later
		quiet = (now - self.lastFrame) if self.lastFrame > 0. else 0.
		hold  = (len(self.cands) >= FEEDMINMACS and self.expireSecs < quiet <= FEEDTRUST)
		if hold and not self.feedHeld:
			self.feedHeld = True
			if self.debug: U.logger.log(20, "findMyGroup ROTH  nothing heard from ANY of {} macs for {:.0f}s - holding them rather than reporting an empty room, for up to {:.0f}s".format(
					len(self.cands), quiet, FEEDTRUST))
		elif self.feedHeld and not hold:
			self.feedHeld = False
			if quiet > FEEDTRUST:
				if self.debug: U.logger.log(20, "findMyGroup ROTH! still nothing after {:.0f}s - the silence is no longer ambiguous, expiring normally. Check the radio".format(quiet))
			else:
				if self.debug: U.logger.log(20, "findMyGroup ROTH= feed is back after {:.0f}s - expiring normally again, nothing was lost".format(quiet))

		for mac in ([] if hold else list(self.cands)):
			c = self.cands[mac]
			if now - c["last"] > self.expireSecs:
				if self.debug: U.logger.log(10, "findMyGroup GONE  {} after {:.0f}s member:{} tagId:{}".format(
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
		# THE INVARIANT, MADE SELF-HEALING RATHER THAN ASSUMED: every tagIdOf entry belongs to a mac
		# that is HERE. It is written at join and removed by the expiry pass above, and those are the
		# only two places - so the dict can only hold macs in cands. That was NOT true before
		# 2026-09-27: restoreSlots() wrote entries for macs that had never been in cands, and nothing
		# walked them, so one for a mac that never came back was immortal - see the comment there.
		# One line, over at most maxSlots keys, so a future path that forgets cannot rebuild the leak
		for oMac in [m for m in self.tagIdOf if m not in self.cands]:
			del self.tagIdOf[oMac]
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
			if self.debug: U.logger.log(20, "findMyGroup memberCount {} -> {}".format(self.previousCount, self.stableCount))
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
		# and to the SD card every PERSISTSECS, so a reboot does not lose the slot map or the mac
		# history. Not every send: that would be ~1440 writes a day on a card that has to last, for
		# a file that changes very little between two of them.
		# THE CALIBRATION CSV IS NOT IN HERE ANY MORE. It is written straight to the card as its
		# rows are produced - see csvFile in __init__ - so it has nothing to be copied out of
		if now - self.lastPersist >= PERSISTSECS:
			self.lastPersist = now
			U.writeJson(self.persistFile, data, sort_keys=False, indent=2)
		if self.debug >= 1: self.logSummary(now, trigger)
		if self.devId in ["", "0"]: return None
		data["trigger"] = trigger
		return {"sensors": {SENSOR_NAME: {self.devId: data}}}

	def logRot(self, txt):
		"""One line about a lineage decision. ROT matched, ROT? refused as ambiguous, ROTX no match.

		ROTP AND ROTG ARE THE FEED, not a decision - see GAPGRACE. ROTG says the frame stream stopped
		and ROTP that a newcomer is parked because of it, and they carry the prefix so they turn up in
		the grep beside the decisions they explain. ROTG is the one line here logged at 20 whatever
		the debug menu says, because it is the answer to "why did a device appear" and needing debug
		on to see it meant it was never seen.

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
		if self.debug: U.logger.log(20 if self.debug >= 1 else 10, "findMyGroup {}".format(txt))

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
			if self.debug: U.logger.log(20, "findMyGroup ==== {}  trigger:{}  members:{} (raw {})  candidates:{}  nearby:{}  strongest:{} ({})  join:{:.0f} leave:{:.0f}".format(
					datetime.datetime.fromtimestamp(now).strftime("%H:%M:%S"), trigger,
					self.stableCount, self.rawCount, len(active), len(active) - len(members),
					int(strongest) if rssis else -999, strongestMac, self.joinRssi, self.leaveRssi))
			if self.debug: U.logger.log(20, "findMyGroup      sl mac                rssi  dist       battery   types      age   pkts")

			bySlot = {}
			for slot in self.slots: bySlot[self.slots[slot]] = slot

			def line(slot, mac, c, tail=""):
				if self.debug: U.logger.log(20, "findMyGroup      {:<2} {:<17} {:>5}  {:<9}  {:<8}  {:<9} {:>5}s {:>5}{}".format(
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
				if self.debug: U.logger.log(20, "findMyGroup      {:<2} {:<17} HELD - gone {:.0f}s, slot kept {:.0f}s more".format(
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
			# AND WHICH NUMBERING THOSE IDS BELONG TO - see runId in reset(). The counter alone cannot
			# say: after one lost state file every id is small, so the next loss climbs past them and
			# looks like ordinary progress. This changes only when the counter restarts, which is the
			# one moment every id already out there stops meaning what it did
			"runId":           self.runId,
			# WHICH MAC OWNS WHICH LINEAGE, so two days of memory is not undone by one restart.
			# Compact on purpose - [tagId, last] rather than named fields - because at OWNMAX this
			# is the biggest thing in the file and it is written every send
			"ownTags":         dict((m, [self.ownTag[m]["tagId"], int(self.ownTag[m]["last"])]) for m in self.ownTag),
		}

	def noteFeedGap(self, why, secs=0., now=None):
		"""beaconloop says the frame stream stopped, for a reason only beaconloop can know.

		WHAT THE lastFrame TEST CANNOT SEE, and this is the whole reason for a second way in: that
		one measures a hole BETWEEN TWO FRAMES, so it needs the feed to come back before it can say
		anything, and it cannot say why. A radio put back into scan role, an hci reset, a dongle
		re-init, a role re-assert after a collision - the stream stops for as long as that takes, and
		the only process that knows it is about to happen is the one doing it. Told rather than
		inferred, the grace starts at the right moment instead of one expireSecs after the fact, and
		the log names the cause instead of a length.

		BOTH WAYS STAY: this one is exact but only covers what beaconloop thinks to report, and the
		measured test is the backstop for every stall nobody anticipated - which is the kind that
		costs an afternoon. They do not conflict, they extend whichever grace is longer.

		SAFE BEFORE setParams: called during beaconloop's own start-up, when enable and the
		thresholds have not been read yet. It touches nothing but the gap fields, and if the group
		is switched off nothing ever reads them.

		Inputs:
		    why (str): what interrupted it, for the log - "beaconloop start", "hci0 reset", ...
		    secs (float): how long it lasted if that is known, 0 when it is not
		    now (float): epoch seconds, None for time.time()
		Outputs:
		    None
		"""
		try:
			if now is None: now = time.time()
			if secs > 0.:	self.feedGap = max(secs, self.feedGap if now < self.feedGapUntil else 0.)
			self.feedGapWhy   = why if secs <= 0. else "{} ({:.0f}s)".format(why, secs)
			# LONGER WINS. Two of these inside one grace, or one arriving while a measured gap is
			# still in force, must not shorten the wait that is already running
			self.feedGapUntil = max(self.feedGapUntil, now + GAPGRACE)
			if self.debug: U.logger.log(20, "findMyGroup ROTG  {} - a rotation across that cannot be inferred, newcomers parked {:.0f}s".format(
					self.feedGapWhy, self.feedGapUntil - now))
		except Exception:
			U.logger.log(20, "", exc_info=True)

	def gapWhy(self):
		"""The feed gap still in force, named for a log line or a refusal reason.

		THE KINDS READ DIFFERENTLY ON PURPOSE. A measured one has a length, because two frames
		arrived either side of it and that length IS the evidence. One beaconloop reported has a
		cause, which is better than a length. A restart has neither - nothing was heard before it by
		definition - and naming it beats saying "gap of 0s".

		Inputs:
		    none
		Outputs:
		    str: "feed gap of 52s", "hci0 reset (12s)", "restart"
		"""
		return self.feedGapWhy or "restart"

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
		  - EXCEPT A SEPARATED -> NEARBY SWITCH, which rotates the mac and adds 07 on an airpods set.
		    That is let through as a MODE match - see ROTMODEPEN - the weakest kind, taken only when
		    the old mac stopped before the new one started and nothing ordinary survives the wait
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
			hits, why, modes = [], [], {}
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
				# EXCEPT 07 ARRIVING WITH NEARBY - see ROTMODEPEN. Separated, an airpods set sends 12 and
				# nothing else; back near its owner it rotates and sends 07|12 in every frame. That is
				# the one extra type a mode switch explains, so it is let through as a MODE match -
				# weaker than any exact or subset match - and any other extra type still refuses
				mode   = []
				newSet = set([t for t in types.split("|") if t])
				oldSet = set([t for t in oTypes.split("|") if t])
				if not newSet <= oldSet:
					if newSet - oldSet == set(["07"]) and "nearby" in inds:
						mode.append("types {} from {}".format(types, oTypes or "-"))
					else:
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
				# NO LONGER A REFUSAL, A MODE MATCH - see ROTMODEPEN. The premise above, that a rotation
				# does not change the indicator, is wrong for separated -> nearby: coming back to its
				# owner is itself what rotated the mac. What the pair this was written for really needed
				# is now tested properly - both of them went on transmitting, so ROTCONFIRM throws out
				# the candidate the moment it speaks again, and ROTBACK below still stops a hand-back.
				# A mode match only wins as the SOLE survivor of the silence wait and loses to any
				# ordinary match - see resolveRotClaims()
				# ONE DIRECTION ONLY: separated -> nearby. The other way does not rotate - CE:25 went
				# from nearby to separated at 10:41 on 2026-09-28 and kept its mac - so a separated
				# newcomer after a nearby mac is still a different tag, and is still refused
				if inds and oInds and not (inds & oInds):
					if "nearby" in inds and "separated" in oInds:
						mode.append("{} from {}".format("|".join(sorted(inds)), "|".join(sorted(oInds))))
					else:
						why.append("{} {} shares nothing with {}".format(
								tail, "|".join(sorted(inds)), "|".join(sorted(oInds))));			continue
				# AND IT MAY NOT GO STRAIGHT BACK. A lineage that has just moved A -> B cannot
				# move B -> A moments later: a rotation is one way, so a reversal is two wrong
				# matches rather than two right ones. The pair above did exactly that
				wasFrom, wasTo, wasAt = self.rotLast.get(tagId, ("", "", 0.))
				if wasFrom == mac and wasTo == oMac and now - wasAt < ROTBACK:
					why.append("{} would hand {} straight back ({:.0f}s)".format(tail, tagId, now - wasAt));	continue
				# A MODE MATCH MUST BE A SWITCH, not an overlap: the old mac cannot still be sending
				# after its own successor started. Only asked of mode matches, which have nothing
				# else going for them - at 10:41 on 2026-09-28 it is what separates the airpods'
				# CE:25 (last 32.0, newcomer first 33.0) from F7:AA (last 36.2), which also went
				# silent and would otherwise have left two survivors and no answer
				if mode and last > first + ROTSPOKE:
					why.append("{} still sending {:.1f}s after this one started, not a mode switch".format(
							tail, last - first));										continue
				hits.append((oMac, tagId, last, oRssi, oTypes))
				if mode:	modes[oMac] = ", ".join(mode)
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
			# NOTHING FITTED MEANS TWO DIFFERENT THINGS - see GAPGRACE. Normally the pool was looked
			# at and held no lineage this mac could be, which is a real answer. Inside the grace after
			# a feed gap it means there was no pool to look at: a restart empties cands and goneTags,
			# and a stall fills goneTags with macs that were never gone. Minting there was the entire
			# cost of a gap - a tag that rotated while nobody was listening became a SECOND indigo
			# device immediately, without passing through any of the confirmation this file exists
			# for, and the log said "none in range at all" as though it had checked.
			# PARKED ON THE MECHANISM A CLAIM ALREADY USES, not a new one: an entry on rotPending is
			# held out of members by update(), is dropped with ROTD if the mac vanishes meanwhile, and
			# is minted with its reasons by resolveRotClaims() when it falls due. The only thing that
			# differs is that it names no candidates and falls due when the feed is evidence again
			if not hits:
				if now < self.feedGapUntil:
					# THE REASON IS STORED, not looked up again when the claim settles: a second gap
					# can happen during the grace, and the line that explains this decision has to
					# name the gap that CAUSED it rather than whichever one is current a minute later
					self.rotPending[mac] = {"at": now, "due": self.feedGapUntil, "rssi": rssi,
									"types": types, "cands": {}, "gap": self.gapWhy(),
									"why": list(why) + ["nothing to match against - {}".format(self.gapWhy())]}
					if self.debug: self.logRot("ROTP  {} joined right after a {} - parked {:.0f}s, there is nothing to match it against yet".format(
							mac, self.gapWhy(), self.feedGapUntil - now))
				return None
			# AND A REAL CLAIM MADE INSIDE THE GRACE WAITS FOR THE FEED TOO, not just ROTCONFIRM. The
			# one thing the wait establishes is that the old mac STAYS silent, and silence measured
			# across a gap is not silence - it is us not listening. Whichever of the two is later
			self.rotPending[mac] = {"at": now, "due": max(now + ROTCONFIRM, self.feedGapUntil),
									"rssi": rssi, "types": types, "why": list(why),
									"cands": dict((h[0], (h[1], h[2], h[3], h[4])) for h in hits),
									"modes": modes}
			self.logRot("ROT~  {} waiting {:.0f}s on {} candidate(s): {}".format(
					mac, self.rotPending[mac]["due"] - now, len(hits),
					",".join(sorted(h[0][-5:] + ("(mode)" if h[0] in modes else "") for h in hits))))
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

	def gridOff(self, mac):
		"""How far this mac's FIRST packet fell from a rotation boundary, in seconds.

		0 means it appeared exactly on one; ROTGRID/2 means the middle of a slot, as far from a
		boundary as it is possible to be. The boundary is the unix epoch multiple itself - see
		ROTGRIDNEAR for why no phase term is needed.
		c["first"] IS THE RIGHT TIME and not c["last"] or the claim time: it is when this mac was
		first heard at all, and CARRYBACK preserves it across a short gap, so a mac that flickers
		does not get a new birth every time it comes back.

		Inputs:
		    mac (str): the mac
		Outputs:
		    float or None: seconds from the nearest boundary, None if the mac has gone
		"""
		try:	t = self.cands[mac]["first"]
		except Exception:	return None
		off = t % ROTGRID
		return min(off, ROTGRID - off)

	def gridPenalty(self, mac):
		"""ROTGRIDPEN scaled by how far off the rotation clock this mac was born - 0 on it.

		Flat zero inside ROTGRIDNEAR, flat ROTGRIDPEN beyond ROTGRIDFAR, linear between, so no
		decision turns on a hard edge. A mac whose birth cannot be read costs nothing: the prior
		has to be able to say "no opinion", or an unknown would read as evidence against.
		"""
		off = self.gridOff(mac)
		if off is None:				return 0.
		if off <= ROTGRIDNEAR:		return 0.
		if off >= ROTGRIDFAR:		return ROTGRIDPEN
		return ROTGRIDPEN * (off - ROTGRIDNEAR) / (ROTGRIDFAR - ROTGRIDNEAR)

	def rotBatchSolve(self, others, rivals, modePairs=None):
		"""Which pairings in a whole wave of rotations are forced, and which are still a guess.

		WHAT THE PAIRWISE CONTEST IS NOT SHAPED FOR. resolveRotClaims() judges one claim at a time
		against its rivals, which is right when one tag rotates. Tags rotate in WAVES - eight of twelve
		macs inside one ten second window, measured 2026-09-27 - and then every newcomer is a rival of
		every other for the same handful of lineages, the arbitrations come down to 1 and 4 dBm on a
		signal that wanders 4.8, and the contested branch burns a lineage for claims that never
		contested it.
		AND THAT WAVE WAS STILL RESOLVED CORRECTLY, which is the honest state of the evidence and is
		why this is additive: every candidate it turned down was in fact still alive and came back or
		rotated later, so the two macs that took fresh tagIds really were new tags. Nothing here is
		fixing an observed wrong answer - it is removing a way of arriving at one.

		A WAVE HAS ONE ANSWER, NOT N ANSWERS. Every lineage goes to at most one mac and every mac
		takes at most one lineage, so the question is which whole assignment is best - and that is
		worth asking because a pairing that looks poor on its own can be the only way the REST of the
		wave works out. Solved as one problem, the answer is often unique where no single pair was.

		AND IT COMMITS ONLY WHAT IS FORCED. The cheapest assignment is not evidence by itself; what
		matters is whether there is a comparable answer that pairs somebody differently. So each pair
		in the best assignment is put to the test: forbid just that pair, solve again, and if the best
		remaining answer explains fewer tags - or costs more than ROTBATCH extra - then nothing else
		fits and the pair is forced. If a near-equal alternative exists, the pair is NOT committed and
		the claim waits, exactly as an ambiguous one does. Refusing is still the default; this only
		finds the pairs where refusing would be the wrong answer.
		THE TEST IS PER PAIR AND NOT PER ASSIGNMENT, which is what makes it degrade gracefully: in a
		wave where the near tags separate cleanly and the far ones do not, the near ones commit and the
		far ones wait for the next pass, instead of the whole wave being refused together.

		Inputs:
		    others (dict): {mac: {oMac: (tagId, rssi, types)}} every claim in flight and its candidates
		            that are still silent - the bipartite graph, with every hard filter already applied
		    rivals (dict): {mac: (rssi, types)} each claimant's own smoothed signal and apple types
		    modePairs (set): {(mac, oMac)} pairings that only fit as a separated <-> nearby switch
		Outputs:
		    tuple: ({mac: oMac} forced pairings, set(mac) every mac in a wave worth solving)
		"""
		forced, inBatch = {}, set()
		try:
			macs = sorted(m for m in others if others[m])
			if len(macs) < 2:	return forced, inBatch
			lins = sorted(set(o for m in macs for o in others[m]))
			# ONLY A WAVE, not two unrelated rotations that happen to be in flight together. If no
			# lineage is wanted by more than one mac there is nothing to arbitrate and the ordinary
			# path already handles each of them correctly
			if not any(sum(1 for m in macs if o in others[m]) > 1 for o in lins):
				return forced, inBatch
			if len(macs) > BATCHMAXN or len(lins) > BATCHMAXM:
				self.logRot("ROTB? {} newcomer(s) and {} lineage(s) in flight - too many to solve as one wave, judging them pairwise as before".format(
						len(macs), len(lins)))
				return forced, inBatch
			inBatch = set(macs)

			cost = {}
			for ii in range(len(macs)):
				mac = macs[ii]
				myRssi, myTypes = rivals.get(mac, (0., ""))
				# WHEN THIS NEWCOMER APPEARED, against the 15 minute clock every find my mac rotates
				# on - see ROTGRID. It is a property of the MAC and not of the pairing, so it is the
				# same for every lineage this one could take and cannot pick between them. What it
				# does decide is which NEWCOMER inherits when there are fewer lineages than macs
				# wanting them: one that appeared on a boundary is where a rotation is expected,
				# one that appeared in the middle of a slot is far more likely to be a genuinely new
				# tag that has simply turned up mid-wave.
				# CARRIED AT ROTGRIDTIE WEIGHT HERE, ie as a tie-break only - see that constant for
				# what happened when it was carried at full weight. Where the clock is actually
				# given something to decide is the pairwise tie below
				gridPen = self.gridPenalty(mac)
				for jj in range(len(lins)):
					oMac = lins[jj]
					if oMac not in others[mac]:	continue
					tagId, oRssi, oTypes = others[mac][oMac]
					# THE SAME TWO THINGS THE PAIRWISE PATH WEIGHS, in the same order of importance:
					# an exact apple-type match outranks a subset outright - a bare 12 tag must not
					# take an airpods case's 07|12 lineage while the case can never take the tag's -
					# and signal only ranks pairings of the same kind. ROTTYPEPEN is past any dBm
					# difference, so the two can never be traded against each other
					cc = abs(myRssi - oRssi) + ROTGRIDTIE * gridPen
					# and a mode switch ranks below both, by the same margin - see ROTMODEPEN
					if modePairs and (mac, oMac) in modePairs:	cc += ROTMODEPEN
					elif myTypes != oTypes:						cc += ROTTYPEPEN
					cost[(ii, jj)] = cc
			if not cost:	return forced, inBatch

			pairs0, cost0, best = bestAssignment(cost, len(macs), len(lins))
			if pairs0 == 0:	return forced, inBatch
			for ii in sorted(best):
				jj = best[ii]
				pairsX, costX, _alt = bestAssignment(cost, len(macs), len(lins), forbid=(ii, jj))
				# FEWER TAGS EXPLAINED, or the same number at a cost this pair was carrying: either way
				# there is no comparable answer without it
				if pairsX < pairs0 or (costX - cost0) > ROTBATCH:
					forced[macs[ii]] = lins[jj]
			self.logRot("ROTB  wave of {} newcomer(s) over {} lineage(s): best answer pairs {} of them, {} forced{}".format(
					len(macs), len(lins), pairs0, len(forced),
					" - " + ", ".join("{}->{}".format(m[-5:], forced[m][-5:]) for m in sorted(forced)) if forced else " (nothing is certain yet, they wait)"))
			# WHERE EACH ONE FELL ON THE ROTATION CLOCK, printed whenever the prior actually did
			# something - ie at least one newcomer was off the grid. Silent when they all appeared
			# on it, which is the normal case and says nothing worth a line
			offs = [(m, self.gridOff(m), self.gridPenalty(m)) for m in macs]
			if any(pp > 0. for _m, _o, pp in offs):
				self.logRot("ROTB~ on the {:.0f}s rotation clock: {}".format(ROTGRID, ", ".join(
						"{} {}s{}".format(m[-5:], "?" if o is None else "{:.0f}".format(o),
											"" if pp <= 0. else " (+{:.1f})".format(pp))
						for m, o, pp in offs)))
		except Exception:
			U.logger.log(20, "", exc_info=True)
			return {}, set()
		return forced, inBatch

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
			# which claim-to-lineage pairings only fit as a separated <-> nearby switch - see ROTMODEPEN.
			# Taken before the loop pops anything, like rivals, so every claim sees every other's
			modePairs = set((m, o) for m in self.rotPending for o in self.rotPending[m].get("modes", {}))
			# AND THE WHOLE WAVE AT ONCE, before any single claim is judged - see rotBatchSolve().
			# Recomputed every pass on purpose: candidates eliminate themselves by speaking, and
			# commits take lineages out, so a wave that is ambiguous now is often forced a few seconds
			# later. That is the same reason ROTAMBIG waits rather than deciding
			forced, inBatch = self.rotBatchSolve(others, rivals, modePairs)
			# DUE, NOT "at + ROTCONFIRM" - see GAPGRACE. A claim made across a feed gap waits for the
			# FEED rather than for the clock, because the silence it is built on was not measured on a
			# running one; and a mac parked with no candidates at all waits the whole grace out. The
			# .get() default is the old arithmetic, so a claim written by a hand-edit that predates
			# this key still falls due instead of being stranded in flight forever
			for mac in [m for m in sorted(self.rotPending)
							if now >= self.rotPending[m].get("due", self.rotPending[m]["at"] + ROTCONFIRM)]:
				mine, why = self.rotAlive(mac)
				p         = self.rotPending.pop(mac)
				# NOT written into the claim yet: this pass may end in a WAIT and run again on the
				# next tick, and reasons appended every second would stack up in the log line.
				# Only a pass that actually settles keeps them
				whyNow    = list(p["why"]) + why
				c    = self.cands.get(mac)
				if c is None:
					# the newcomer itself went away while we waited. Nothing to hand a lineage to, and
					# the old one keeps it - which is right: a mac that lasted seconds rotated nowhere
					self.logRot("ROTD  {} gone before its claim settled - no lineage moved".format(mac))
					continue
				# THE WAVE ANSWERED IT, and that answer is stronger than anything the pairwise contest
				# below can work out - it is the only pairing that lets the REST of the wave work out
				# too, which is evidence no single comparison has. Still checked against "mine": an
				# earlier claim settling in this same pass can have taken the lineage, and rotAlive()
				# is recomputed per claim so it already knows
				if mac in forced and forced[mac] in mine:
					oMac = forced[mac]
					self.logRot("ROTB= {} -> {} taken from the wave - forced, nothing else fits".format(oMac, mac))
					self.commitRotation(mac, oMac, mine[oMac][0], now, p.get("modes", {}).get(oMac, ""))
					continue
				# NOT FORCED BY THE WAVE, so the pairwise path below decides exactly as it always has.
				# IT IS NOT OVERRIDDEN, and that is deliberate: ROTBATCH is stricter than ROTTIE, so a
				# wave solve that refused whatever it could not force would THROW AWAY pairings the
				# pairwise path gets right. Replayed against the wave of 2026-09-27 13:30 that is not
				# hypothetical - 4C:98 -> BB:AF was 4 dBm against 0 for its rival, which ROTTIE settles
				# correctly and a 5 dBm margin will not. So the wave only ever ADDS a commit above, and
				# the two places below are the only ones where it changes what the pairwise path does
				keep  = {}
				modes = p.get("modes", {})
				for oMac in sorted(mine):
					tagId, oRssi, oTypes = mine[oMac]
					# A MODE MATCH STEPS ASIDE FOR ANY ORDINARY CLAIM ON THE SAME LINEAGE - see ROTMODEPEN.
					# It is the weakest kind of match there is, so there is nothing to arbitrate: a mac
					# whose types and indicator both carry straight on is the better explanation. Not
					# burnt - the rival is entitled to it
					if oMac in modes and any(m2 != mac and oMac in others[m2] and (m2, oMac) not in modePairs
												for m2 in others):
						whyNow.append("{} claimed by an ordinary match, ours is a mode switch".format(oMac[-5:]))
						continue
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
					bestMac             = None		# WHICH rival, so the rotation clock can be asked about it below
					for m2 in sorted(others):
						if m2 == mac or oMac not in others[m2]:	continue
						# a MODE rival does not contest an ordinary claim - it steps aside above when its
						# own turn comes, so counting it here would burn a lineage it could never take
						if oMac not in modes and (m2, oMac) in modePairs:	continue
						d2, same2 = abs(rivals[m2][0] - oRssi), (rivals[m2][1] == oTypes)
						# the STRONGEST rival, not the closest one: exact beats subset, and signal
						# only ranks within the same kind
						if best is None or (same2, -d2) > (bestSame, -best):	best, bestSame, bestMac = d2, same2, m2
					if best is not None and mineSame != bestSame:
						# ONE OF US IS AN EXACT MATCH AND THE OTHER IS NOT, so there is nothing to
						# arbitrate and signal is not consulted at all. The loser simply steps aside -
						# NOT burnt, because the winner is entitled to it, and when the winner's own
						# claim settles the loser's will find the lineage already gone
						if not mineSame:
							whyNow.append("{} claimed by an exact type match, ours is only a subset".format(
									oMac[-5:]));		continue
					elif best is not None and mineD - best > ROTTIE:
						# THE RIVAL IS CLEARLY CLOSER, so this is not a contest - it is a loss, and the
						# two are not the same thing. Burning the lineage here would deny it to a claim
						# that plainly deserves it, which is the very mistake the arbitration exists to
						# stop. Step aside instead and let the better claim take it when it settles
						whyNow.append("{} claimed by a closer mac ({:.0f} vs {:.0f} dBm off)".format(
								oMac[-5:], mineD, best));		continue
					elif (best is not None and best - mineD <= ROTTIE and bestMac is not None
							and self.gridPenalty(mac) >= ROTGRIDPEN and self.gridPenalty(bestMac) <= 0.):
						# SIGNAL HAS TIED AND THE CLOCK HAS NOT - see ROTGRID. A find my mac is
						# replaced on a 15 minute grid, so a newcomer that appeared ON one is where a
						# rotation is expected and a newcomer that appeared in the MIDDLE of a slot is
						# far more likely to be a tag that has simply turned up. Both of us are inside
						# ROTTIE, which is the module saying signal cannot tell us apart, and this is
						# the one other thing known about us that can.
						# ONLY AT THE TWO ENDS OF THE RAMP: we are past ROTGRIDFAR and the rival is
						# inside ROTGRIDNEAR. Anything in between is not worth acting on - the measured
						# spread is about 81 s against a 900 s period, which separates a boundary from
						# mid-slot and nothing finer.
						# STEPPING ASIDE, NOT WINNING, which is why this sits here rather than in a new
						# commit path: it is the same move the "clearly closer" case above makes, with
						# the same consequence, and it REPLACES an outcome where the lineage was burnt
						# for both of us and nobody got it. One of us having it is strictly better than
						# neither, when there is a reason to prefer one
						whyNow.append("{} claimed by a mac that appeared on the {:.0f}s rotation clock ({:.0f}s off it) while ours appeared {:.0f}s off, mid-slot - signal could not separate us ({:.0f} vs {:.0f} dBm)".format(
								oMac[-5:], ROTGRID, self.gridOff(bestMac) or 0., self.gridOff(mac) or 0., mineD, best))
						continue
					elif best is not None and best - mineD <= ROTTIE:
						whyNow.append("{} also claimed by another mac ({:.0f} vs {:.0f} dBm off)".format(
								oMac[-5:], mineD, best))
						# NOT BURNT INSIDE A WAVE, and this is the one thing the wave solve takes away
						# from the pairwise path. The burn below is right when two claims contest one
						# lineage in isolation - nobody may have it - but inside a wave it destroys the
						# very evidence rotBatchSolve() needs: it removes the lineage from claims that
						# never contested anything, and a pairing that looks poor on its own is often
						# the only way the REST of the wave works out. Left alone, the candidate is
						# re-judged next pass, when rivals have spoken and commits have removed
						# lineages, and the wave is frequently forced by then. The claim still gets no
						# lineage THIS pass - only the burning of everyone else's is skipped
						if mac in inBatch:
							p["cands"].pop(oMac, None)
							continue
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
						# AND FOR US. It used to be enough to skip it for this pass, because the
						# pass always ended in a fresh tagId - now the claim can come round again,
						# and the rival's copy is already gone, so a retry would find no contest
						# and quietly take the thing neither of us was allowed to have
						p["cands"].pop(oMac, None)
						continue
					keep[oMac] = tagId
				# AN ORDINARY SURVIVOR OUTRANKS EVERY MODE ONE - see ROTMODEPEN. A mode match is only
				# taken when nothing better is left after the silence wait, which at 10:41 on
				# 2026-09-28 is exactly what happened: 91:4B and 6C:63 spoke again within 3 s and the
				# airpods' own CE:25 was the only lineage still silent
				if any(o not in modes for o in keep):
					for o in [o for o in keep if o in modes]:
						whyNow.append("{} only fits as a mode switch, an ordinary match outranks it".format(o[-5:]))
						del keep[o]
				if len(keep) == 1:
					oMac = sorted(keep)[0]
					self.commitRotation(mac, oMac, keep[oMac], now, modes.get(oMac, ""))
					continue
				if len(keep) > 1 and now - p["at"] < self.rotAmbig:
					# STILL TOO MANY, BUT NOT FOR LONG ENOUGH TO GIVE UP - see ROTAMBIG. Put back
					# untouched and judged again next tick: the set can only shrink, so this either
					# becomes a match or runs out of time, and it cannot become more wrong
					if not p.get("waited"):
						p["waited"] = True
						self.logRot("ROT+  {} still {} candidates after {:.0f}s, waiting up to {:.0f}s for one to be taken or speak: {}".format(
								mac, len(keep), now - p["at"], self.rotAmbig, ",".join(sorted(k[-5:] for k in keep))))
					self.rotPending[mac] = p
					continue
				if len(keep) > 1:
					self.logRot("ROT?  {} could be any of {} after {:.0f}s - refusing, it takes a new tagId".format(
							mac, ",".join(sorted(keep)), now - p["at"]))
				# ONE LAST WAIT IF IT IS PART OF A WAVE. Everything above has failed to give this mac a
				# lineage, and the next line mints one - which is the answer that cannot be taken back,
				# because the plugin makes an indigo device for it. Inside a wave that is premature:
				# the claims settle over tens of seconds as the rpi first hears each new mac, rivals
				# take themselves out by speaking, and commits remove lineages - so the set can only
				# shrink and rotBatchSolve() is run again from scratch every pass. A mac that nothing
				# forces now is often forced two passes later. Bounded by ROTAMBIG exactly as the
				# "could be any of" wait is, and for the same reason: the tag is held out of members
				# while it waits, so this cannot run past the plugin's member down-delay
				if mac in inBatch and now - p["at"] < self.rotAmbig:
					if not p.get("waitedBatch"):
						p["waitedBatch"] = True
						self.logRot("ROTB~ {} is one of a wave and nothing forces its pairing yet - waiting up to {:.0f}s before minting a lineage".format(
								mac, self.rotAmbig))
					p["why"] = list(p["why"])		# the reasons above were for THIS pass only
					self.rotPending[mac] = p
					continue
				c["tagId"]        = self.nextTagId
				self.nextTagId   += 1
				self.tagIdOf[mac] = c["tagId"]
				if p.get("gap"):
					# PARKED, NOT REFUSED, and the line has to say so - see GAPGRACE. Nothing was
					# turned down because there was nothing to turn down, and "0 candidate(s) turned
					# down: none in range at all" was the old way of saying that, which read like a
					# search that came back empty rather than a memory that was never there
					self.logRot("ROTX  {} nothing to inherit after a {} - fresh tagId:{}, parked {:.0f}s and neither its own mac nor a lineage turned up".format(
							mac, p["gap"], c["tagId"], now - p["at"]))
				else:
					self.logRot("ROTX  {} no lineage matched, fresh tagId:{} - {} candidate(s) turned down: {}".format(
							mac, c["tagId"], len(whyNow), "; ".join(whyNow[:8]) or "none in range at all"))
		except Exception:
			U.logger.log(20, "", exc_info=True)

	def commitRotation(self, mac, oMac, tagId, now, mode=""):
		"""Hands one lineage from oMac to mac, once the wait has confirmed oMac really stopped.

		Lifted out of matchRotation() unchanged when the decision moved here, so that the bookkeeping
		that keeps a lineage from being held twice lives in exactly one place.

		Inputs:
		    mac (str): the mac inheriting
		    oMac (str): the mac it is the continuation of
		    tagId (int): the lineage
		    now (float): epoch seconds
		    mode (str): what the separated <-> nearby switch changed, "" for an ordinary match
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
		self.logRot("ROT   {} -> {} same tag, tagId {} kept - silent {:.0f}s since the claim{}".format(
				oMac, mac, tagId, ROTCONFIRM, " - MODE SWITCH, " + mode if mode else ""))

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
					if self.debug: U.logger.log(20, "findMyGroup {}: '{}' is not a debug level - use 0, 1 (or 10), 2 (or 20)".format(fName, txt))
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

		A SIZE CAP, NOT AN AGE ONE: what matters is that this file cannot grow without bound, not how
		old its rows are, and a size is the thing that can be checked on the write that just happened.
		It also means there is nothing to sweep up on a schedule and no second file to keep track of.
		THE CAP USED TO BE ABOUT temp/, a 2 MB tmpfs it shared with findMyGroup.state, and it was
		200 kB because of that. The file is on the card now and the cap is 20 MB - see CSVMAXBYTES.

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
			if self.debug: U.logger.log(20, "findMyGroup calibration csv over {}kB, oldest rows dropped, {} rows kept".format(CSVMAXBYTES // 1024, len(out)))
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
			# CSVMAXBYTES. Whoever reads the file forward-fills it instead;
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
				# the pibeacon dir belongs to the pi user, so this is a plain append - no
				# writeFileAsRoot and no chown on the write path itself
				f = open(fName, "a")
				f.write("\n".join(lines) + "\n")
				f.close()
				# ONLY WHEN WE JUST MADE IT. umask 0 covers a file this process creates, but one
				# left behind by an older version running as root keeps its 0644/root and appending
				# to it does not change that - so the one cheap syscall is spent on the pass that
				# created the file, and never again
				if newFile:	U.makeOwnFileWritable(fName)
				if os.path.getsize(fName) > CSVMAXBYTES:	self.trimCsv(fName)
		except Exception:
			U.logger.log(20, "", exc_info=True)
