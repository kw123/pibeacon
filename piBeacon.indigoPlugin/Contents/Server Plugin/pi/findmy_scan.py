#!/usr/bin/env python3
#
# NOTE: python3 ONLY - unlike the rest of pi/*.py this is not py2 compatible (yield from,
# the py3 queue module). That is safe because it is a MANUAL calibration tool: beaconloop
# never imports it, so a py2 rpi is unaffected. Do not "fix" it into the loop.
#
"""
findmy_scan.py  -  Find My (AirTag) calibration logger and group counter

Runs on a Raspberry Pi. Raw HCI socket only (no hcitool / btmon / bluetoothctl).
Detects Apple Find My advertisements (manufacturer 0x004C, Apple type 0x12),
treats every rotating address as a "candidate" and counts candidates with a
strong signal as "members" of the AirTag group.

Outputs
  <logdir>/findmy_<host>_<YYYYMMDD>.csv   one row per active address per interval (calibration data)
  <logdir>/findmy_<host>_events.log       NEW / GONE / JOIN / LEAVE / COUNT / MARKER lines
  <statefile>                             JSON with the group device states (for the plugin)

Markers (label a calibration session; the marker stays set until changed, but is WRITTEN to the
csv only on the row where it changes and at the top of each new file - a reader forward-fills it,
a blank cell means "same as above" and "-" means cleared)
  type a line + Enter in the terminal, or
  echo "tag at street" > /tmp/findmy_marker      (read and deleted; easy to send to all Pis over ssh)
  echo "" > /tmp/findmy_marker                   (clears the marker)

Examples
  sudo python3 findmy_scan.py                     # hci0, configures scanning itself
  sudo python3 findmy_scan.py --hci 1             # use the second dongle
  sudo python3 findmy_scan.py --listen-only       # beaconloop already scans on this hci; just sniff events
  sudo python3 findmy_scan.py --join -70 --leave -80 --stable 90

Status byte: bits 7-6 = battery level per public reverse engineering (0 full .. 3 critical).
The raw hex is logged too, so you can see whether AirPods / iPhones differ from AirTags.
"""

import argparse
import binascii
import collections
import csv
import datetime
import errno
import fcntl
import json
import os
import queue
import select
import signal
import socket
import statistics
import struct
import sys
import threading
import time

# ------------------------------------------------------------------ HCI constants
HCI_COMMAND_PKT = 0x01
HCI_EVENT_PKT = 0x04
EVT_CMD_COMPLETE = 0x0E
EVT_CMD_STATUS = 0x0F
EVT_LE_META = 0x3E
LE_ADV_REPORT = 0x02
LE_EXT_ADV_REPORT = 0x0D
SOL_HCI = 0
HCI_FILTER = 2
HCIDEVUP = 0x400448C9


def hci_opcode(ogf, ocf):
    return (ogf << 10) | ocf


OP_LE_SET_SCAN_PARAMS = hci_opcode(0x08, 0x000B)
OP_LE_SET_SCAN_ENABLE = hci_opcode(0x08, 0x000C)
OP_LE_SET_EXT_SCAN_PARAMS = hci_opcode(0x08, 0x0041)
OP_LE_SET_EXT_SCAN_ENABLE = hci_opcode(0x08, 0x0042)

BATTERY = {0: "full", 1: "medium", 2: "low", 3: "critical"}


def now_iso(ts=None):
    return datetime.datetime.fromtimestamp(ts if ts is not None else time.time()).isoformat(timespec="seconds")


def now_csv(ts=None):
    """Timestamp for the csv: seconds plus TENTHS, "2026-09-23T15:57:12.6".

    The csv used to carry a separate "epoch" column so findmy_merge.py could bin rows without
    parsing a date. A tenth of a second is finer than any bin those rows go into, so the second
    column is gone and this is the only time in the file - the same as findMyGroup.py writes.
    """
    return datetime.datetime.fromtimestamp(ts if ts is not None else time.time()).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-5]


# ------------------------------------------------------------------ parsing (pure functions, testable)
def addr_str(raw6):
    return ":".join("{:02X}".format(b) for b in reversed(raw6))


def parse_le_meta(body):
    """body = LE meta event parameters. Yields (addr, rssi, adv_data)."""
    if not body:
        return
    sub = body[0]
    if sub == LE_ADV_REPORT and len(body) >= 2:
        n, off = body[1], 2
        for _ in range(n):
            if off + 9 > len(body):
                return
            addr = body[off + 2:off + 8]
            dlen = body[off + 8]
            ri = off + 9 + dlen
            if ri >= len(body):
                return
            data = body[off + 9:ri]
            rssi = struct.unpack("b", body[ri:ri + 1])[0]
            yield addr_str(addr), rssi, data
            off = ri + 1
    elif sub == LE_EXT_ADV_REPORT and len(body) >= 2:
        n, off = body[1], 2
        for _ in range(n):
            if off + 24 > len(body):
                return
            addr = body[off + 3:off + 9]
            rssi = struct.unpack("b", body[off + 13:off + 14])[0]
            dlen = body[off + 23]
            data = body[off + 24:off + 24 + dlen]
            yield addr_str(addr), rssi, data
            off += 24 + dlen


def parse_findmy(data):
    """Returns (indicator, status_byte, hint_byte, apple_types) for a Find My advertisement, else None.
    apple_types is every continuity type in the frame - 0x07 proximity pairing carries a model id,
    0x10 nearby info / 0x0C handoff / 0x05 airdrop come from real devices rather than tags.
    indicator: 'separated' (25 byte payload), 'nearby' (2 byte payload) or 'lenNN'. It indicates
    distance from the tag's OWNER, not from this radio - hence the name.
    hint is the LAST byte of the 25 byte payload - no published meaning beyond '0x00 on ios',
    which is why it is logged. The 2 byte nearby payload has none. Same columns as findMyGroup.py."""
    i = 0
    found = None
    types = []
    while i < len(data):
        ln = data[i]
        if ln == 0 or i + 1 + ln > len(data):
            return None
        ad_type, val = data[i + 1], data[i + 2:i + 1 + ln]
        if ad_type == 0xFF and len(val) >= 4 and val[0] == 0x4C and val[1] == 0x00:
            j = 2
            while j + 2 <= len(val):
                t, l = val[j], val[j + 1]
                v = val[j + 2:j + 2 + l]
                types.append(t)
                if t == 0x12 and found is None:
                    indicator = {25: "separated", 2: "nearby"}.get(l, "len{}".format(l))
                    hint = v[24] if len(v) >= 25 else None
                    found = (indicator, (v[0] if v else None), hint)
                j += 2 + l
        i += 1 + ln
    if found is None:
        return None
    return found[0], found[1], found[2], types


# ------------------------------------------------------------------ HCI scanner
class HciScanner:
    def __init__(self, dev_id):
        self.dev_id = dev_id
        self.mode = "listen-only"
        self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)
        try:
            fcntl.ioctl(self.sock.fileno(), HCIDEVUP, dev_id)
        except OSError as e:
            if e.errno != errno.EALREADY:
                print("warning: could not bring hci{} up: {}".format(dev_id, e), file=sys.stderr)
        self.sock.bind((dev_id,))
        type_mask = 1 << HCI_EVENT_PKT
        ev0 = (1 << EVT_CMD_COMPLETE) | (1 << EVT_CMD_STATUS)
        ev1 = 1 << (EVT_LE_META - 32)
        self.sock.setsockopt(SOL_HCI, HCI_FILTER, struct.pack("<IIIH", type_mask, ev0, ev1, 0))

    def command(self, op, params=b"", timeout=2.0):
        """Send an HCI command, return its status byte (0 = ok) or None on timeout."""
        self.sock.send(struct.pack("<BHB", HCI_COMMAND_PKT, op, len(params)) + params)
        end = time.time() + timeout
        while True:
            rem = end - time.time()
            if rem <= 0:
                return None
            r, _, _ = select.select([self.sock], [], [], rem)
            if not r:
                return None
            pkt = self.sock.recv(4096)
            if len(pkt) < 3 or pkt[0] != HCI_EVENT_PKT:
                continue
            evt, body = pkt[1], pkt[3:]
            if evt == EVT_CMD_COMPLETE and len(body) >= 4 and struct.unpack_from("<H", body, 1)[0] == op:
                return body[3]
            if evt == EVT_CMD_STATUS and len(body) >= 4 and struct.unpack_from("<H", body, 2)[0] == op:
                return body[0]

    def start(self, active=False, interval_ms=100, window_ms=100):
        itv, win = int(interval_ms / 0.625), int(window_ms / 0.625)
        stype = 1 if active else 0
        # legacy scan, no duplicate filtering -> every packet gives an RSSI sample
        self.command(OP_LE_SET_SCAN_ENABLE, b"\x00\x00")
        st = self.command(OP_LE_SET_SCAN_PARAMS, struct.pack("<BHHBB", stype, itv, win, 0, 0))
        if st == 0 and self.command(OP_LE_SET_SCAN_ENABLE, b"\x01\x00") == 0:
            self.mode = "legacy"
            return True
        # controller already used extended commands (e.g. bluetoothd) -> must stay extended
        self.command(OP_LE_SET_EXT_SCAN_ENABLE, struct.pack("<BBHH", 0, 0, 0, 0))
        st = self.command(OP_LE_SET_EXT_SCAN_PARAMS, struct.pack("<BBBBHH", 0, 0, 0x01, stype, itv, win))
        if st == 0 and self.command(OP_LE_SET_EXT_SCAN_ENABLE, struct.pack("<BBHH", 1, 0, 0, 0)) == 0:
            self.mode = "extended"
            return True
        self.mode = "listen-only"
        return False

    def stop(self):
        try:
            if self.mode == "legacy":
                self.command(OP_LE_SET_SCAN_ENABLE, b"\x00\x00", timeout=1)
            elif self.mode == "extended":
                self.command(OP_LE_SET_EXT_SCAN_ENABLE, struct.pack("<BBHH", 0, 0, 0, 0), timeout=1)
        finally:
            self.sock.close()

    def reports(self, timeout):
        end = time.time() + timeout
        while True:
            rem = end - time.time()
            if rem <= 0:
                return
            r, _, _ = select.select([self.sock], [], [], rem)
            if not r:
                return
            pkt = self.sock.recv(4096)
            if len(pkt) >= 4 and pkt[0] == HCI_EVENT_PKT and pkt[1] == EVT_LE_META:
                yield from parse_le_meta(pkt[3:])


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
# THE NUMBERS DO NOT HAVE TO BE 4. What matters is that a column is the SAME WIDTH ON EVERY ROW;
# 2, 3, 5 or 6 is just as good where that is the natural size of the thing.
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
    if ii == "separated":    return "sep"
    if ii == "nearby":        return "near"
    if ii[:3] == "len":        return "l" + ii[3:][:3]
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
    if v is None:    return ""
    try:    return "{:>{}.1f}".format(float(v), CSVWIDTH["rssi"])
    except Exception:    return ""


def numCsv(v, n):
    """A non-negative count, ZERO padded to n digits: 842 -> "0842". "" for None.

    ZEROS AND NOT SPACES, which is the difference between a count and a measurement here. A
    leading space in a csv field reads as a missing value at a glance; a leading zero reads as
    part of the number, which is what it is. Nothing negative is ever written through this.
    n is a minimum: 100000 seconds is still written in full rather than cut to fit.
    """
    if v is None:    return ""
    try:    return "{:0{}d}".format(int(v), n)
    except Exception:    return ""


def intCsv(v, n):
    """A whole signed number right aligned in n - rssi_min and rssi_max. "" for None."""
    if v is None:    return ""
    try:    return "{:>{}d}".format(int(v), n)
    except Exception:    return ""


# ------------------------------------------------------------------ group logic
class Candidate:
    def __init__(self, addr, now, smooth_n):
        self.addr = addr
        self.first = self.last = now
        self.rssi = collections.deque(maxlen=smooth_n)
        self.interval_rssi = []
        self.indicator = ""
        self.status = None
        self.hint = None
        self.raw = ""
        self.types = set()
        self.member = False

    def smoothed(self):
        return statistics.median(self.rssi) if self.rssi else None


class GroupTracker:
    """memberCount only changes after the raw count has been stable for `stable` seconds,
    so an address rotation (old address expires, new one joins) is invisible."""

    def __init__(self, join=-70, leave=-80, expire=10, stable=60, smooth=5, min_packets=3):
        self.join, self.leave, self.expire, self.stable = join, leave, expire, stable
        self.smooth, self.min_packets = smooth, min_packets
        self.cands = {}
        self.stable_count = 0
        self.previous_count = 0
        self.raw_count = 0
        self.pending = 0
        self.pending_since = time.time()
        self.last_change = None
        self.events = []

    def update(self, addr, indicator, status, rssi, now, hint=None, types=None, raw=None):
        c = self.cands.get(addr)
        if c is None:
            c = self.cands[addr] = Candidate(addr, now, self.smooth)
            self.events.append((now, "NEW    {} dist={} rssi={}".format(addr, indicator, rssi)))
        c.last = now
        c.rssi.append(rssi)
        c.interval_rssi.append(rssi)
        c.indicator, c.status = indicator, status
        # only when this frame had one - a nearby frame would otherwise wipe it
        if hint is not None:
            c.hint = hint
        # the raw frame, most recent wins. Unlike the hint there is no "this one had none":
        # every frame has a raw form, and raw_len says which kind of payload it was
        if raw:
            c.raw = raw
        # types accumulate: a device does not put them all in one advertisement
        if types:
            c.types.update(types)
        s = c.smoothed()
        if not c.member and len(c.rssi) >= self.min_packets and s >= self.join:
            c.member = True
            self.events.append((now, "JOIN   {} rssi~{}".format(addr, s)))
        elif c.member and s < self.leave:
            c.member = False
            self.events.append((now, "LEAVE  {} rssi~{}".format(addr, s)))

    def tick(self, now):
        for addr, c in list(self.cands.items()):
            if now - c.last > self.expire:
                del self.cands[addr]
                self.events.append((now, "GONE   {} after {:.0f}s member={}".format(addr, c.last - c.first, c.member)))
        self.raw_count = sum(1 for c in self.cands.values() if c.member)
        if self.raw_count != self.pending:
            self.pending, self.pending_since = self.raw_count, now
        if self.pending != self.stable_count and now - self.pending_since >= self.stable:
            self.previous_count, self.stable_count, self.last_change = self.stable_count, self.pending, now
            self.events.append((now, "COUNT  {} -> {}".format(self.previous_count, self.stable_count)))
        return self.raw_count

    def state(self, now):
        active = list(self.cands.values())
        members = [c for c in active if c.member]
        strongest = max((c.smoothed() for c in active if c.rssi), default=None)
        return {
            "memberCount": self.stable_count,
            "memberCountRaw": self.raw_count,
            "nearbyCount": len(active) - len(members),
            "candidates": len(active),
            "strongestRSSI": strongest,
            "previousCount": self.previous_count,
            "lastCountChange": now_iso(self.last_change) if self.last_change else "",
            "members": [{"mac": c.addr, "rssi": c.smoothed(), "distanceIndicator": c.indicator,
                         "battery": BATTERY.get((c.status or 0) >> 6 & 3) if c.status is not None else ""}
                        for c in members],
            "timestamp": now_iso(now),
        }


# ------------------------------------------------------------------ markers
class MarkerSource:
    def __init__(self, path):
        self.path, self.current = path, ""
        self.q = queue.Queue()
        if sys.stdin and sys.stdin.isatty():
            threading.Thread(target=self._stdin, daemon=True).start()

    def _stdin(self):
        for line in sys.stdin:
            self.q.put(line.strip())

    def poll(self):
        new = None
        while not self.q.empty():
            new = self.q.get()
        try:
            if os.path.exists(self.path):
                with open(self.path) as f:
                    new = f.read().strip()
                os.remove(self.path)
        except OSError:
            pass
        if new is not None and new != self.current:
            self.current = new
            return True
        return False


# ------------------------------------------------------------------ main
# THE SAME COLUMNS AS findMyGroup.py - findmy_merge.py reads both by name and there is one
# schema, not two. One time column: timestamp carries tenths, which is what "epoch" was for.
# NO "hci" COLUMN ANY MORE. It dates from when an rpi ran several ble dongles as equals; the
# radios have had fixed roles for a long time now, and findMyGroup.py never had a per-frame hci
# to put in it, so on that side the column was written empty for its whole life. This scanner
# does know its radio - --hci picks it - and still says so in its startup line and its state
# file; it just does not repeat it on every row of a file that is about one radio anyway.
# raw_hex is the WHOLE advertisement of the most recent frame, raw_len its length IN BYTES, and
# the length comes first because it is the thing you filter on: 25 means a separated payload,
# which is the only kind with a hint byte. Last on the row because it is much the longest field
CSV_FIELDS = ["timestamp", "host", "mac", "distanceIndicator", "status", "hintByte", "appleTypes", "battery", "packets",
              "rssi_median", "rssi_min", "rssi_max", "rssi_smoothed", "member", "age_s", "marker",
              "raw_len", "raw_hex"]


def main():
    ap = argparse.ArgumentParser(description="Find My (AirTag) calibration logger / group counter")
    ap.add_argument("--hci", type=int, default=0)
    ap.add_argument("--listen-only", action="store_true", help="do not configure scanning (another process scans)")
    ap.add_argument("--active", action="store_true", help="active scanning (not needed for Find My)")
    ap.add_argument("--join", type=float, default=-70, help="smoothed RSSI to become a member")
    ap.add_argument("--leave", type=float, default=-80, help="smoothed RSSI to stop being a member")
    ap.add_argument("--expire", type=float, default=10, help="secs without packets before an address is gone")
    ap.add_argument("--stable", type=float, default=60, help="secs a new count must hold before memberCount changes")
    ap.add_argument("--smooth", type=int, default=5, help="median over last N packets")
    ap.add_argument("--min-packets", type=int, default=3)
    ap.add_argument("--interval", type=float, default=10, help="secs between CSV rows / state writes")
    ap.add_argument("--logdir", default="findmy_logs")
    ap.add_argument("--statefile", default="", help="default <logdir>/findmy_state.json")
    ap.add_argument("--marker-file", default="/tmp/findmy_marker")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    host = socket.gethostname()
    os.makedirs(args.logdir, exist_ok=True)
    statefile = args.statefile or os.path.join(args.logdir, "findmy_state.json")
    events_path = os.path.join(args.logdir, "findmy_{}_events.log".format(host))

    scanner = HciScanner(args.hci)
    if not args.listen_only and not scanner.start(active=args.active):
        print("warning: could not configure scanning on hci{}, listening only".format(args.hci), file=sys.stderr)
    print("hci{} mode={} join={} leave={} logdir={}".format(args.hci, scanner.mode, args.join, args.leave, args.logdir))

    tracker = GroupTracker(args.join, args.leave, args.expire, args.stable, args.smooth, args.min_packets)
    markers = MarkerSource(args.marker_file)
    marker_due, marker_cell = False, ""      # see the csv write below - written once, not per row

    running = [True]
    signal.signal(signal.SIGINT, lambda *a: running.__setitem__(0, False))
    signal.signal(signal.SIGTERM, lambda *a: running.__setitem__(0, False))

    next_tick = time.time() + args.interval
    try:
        while running[0]:
            for addr, rssi, data in scanner.reports(timeout=0.5):
                fm = parse_findmy(data)
                if fm:
                    tracker.update(addr, fm[0], fm[1], rssi, time.time(), fm[2], fm[3],
                                   binascii.hexlify(data).decode("ascii").upper())

            now = time.time()
            if now < next_tick:
                continue
            next_tick = max(next_tick + args.interval, now + 1)

            if markers.poll():
                tracker.events.append((now, "MARKER '{}'".format(markers.current or "(cleared)")))
                marker_due = True
            raw = tracker.tick(now)

            csv_path = os.path.join(args.logdir, "findmy_{}_{}.csv".format(host, time.strftime("%Y%m%d")))
            new_file = not os.path.exists(csv_path)

            # THE MARKER GOES ON ONE ROW, NOT ON ALL OF THEM - same rule as findMyGroup.py, one
            # schema. It is an EVENT ("from here on the tag is at the street door"), and the same
            # sentence on every row of a ten minute session is one fact written a thousand times.
            # A reader FORWARD-FILLS it - findmy_merge.py does - so a blank cell means "same as
            # the row above". Restated at the top of each new file, because filling restarts
            # there. "-" means CLEARED, which an empty cell cannot say.
            if marker_due:
                marker_cell = markers.current if markers.current != "" else "-"
            elif new_file and markers.current != "":
                marker_cell = markers.current
            else:
                marker_cell = ""
            with open(csv_path, "a", newline="") as f:
                w = csv.writer(f)
                if new_file:
                    w.writerow(CSV_FIELDS)
                for c in tracker.cands.values():
                    if not c.interval_rssi:
                        continue
                    r = c.interval_rssi
                    w.writerow([now_csv(now), host, c.addr, padCsv(indCsv(c.indicator), CSVWIDTH["distanceIndicator"]),
                                padCsv(None if c.status is None else "{:02X}".format(c.status), CSVWIDTH["status"]),
                                padCsv(None if c.hint is None else "{:02X}".format(c.hint), CSVWIDTH["hintByte"]),
                                padCsv(typesCsv(c.types), CSVWIDTH["appleTypes"]),
                                padCsv(None if c.status is None else battCsv(BATTERY[c.status >> 6 & 3]), CSVWIDTH["battery"]),
                                numCsv(len(r), CSVWIDTH["packets"]),
                                rssiCsv(statistics.median(r)),
                                intCsv(min(r), CSVWIDTH["rssi_minmax"]), intCsv(max(r), CSVWIDTH["rssi_minmax"]),
                                rssiCsv(c.smoothed()),
                                int(c.member),
                                numCsv(now - c.first, CSVWIDTH["age_s"]),
                                padCsv(marker_cell, CSVWIDTH["marker"]),
                                numCsv(len(c.raw) // 2, CSVWIDTH["raw_len"]), c.raw])
                    marker_cell = ""        # one row carries it; the rest of this batch does not
                    marker_due = False
                    c.interval_rssi = []

            if tracker.events:
                with open(events_path, "a") as f:
                    for ts, text in tracker.events:
                        line = "{} {}".format(now_iso(ts), text)
                        f.write(line + "\n")
                        if not args.quiet:
                            print(line)
                tracker.events = []

            st = tracker.state(now)
            st.update({"host": host, "hci": args.hci, "marker": markers.current})
            tmp = statefile + ".tmp"
            with open(tmp, "w") as f:
                json.dump(st, f, indent=1)
            os.replace(tmp, statefile)

            if not args.quiet:
                print("{} memberCount={} raw={} nearby={} candidates={} strongest={} marker='{}'".format(
                    now_iso(now), st["memberCount"], raw, st["nearbyCount"], st["candidates"],
                    st["strongestRSSI"], markers.current))
    finally:
        scanner.stop()


if __name__ == "__main__":
    main()
