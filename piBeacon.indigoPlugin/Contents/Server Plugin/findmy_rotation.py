#!/usr/bin/env python3
#
# WHERE THIS LIVES: Contents/Server Plugin/, beside findmy_merge.py and the plugin's other
# mac-side tools. It never goes near an rpi. python3 only, stdlib only, same as its neighbour.
#
"""
findmy_rotation.py  -  when does a Find My mac rotate, and is NEARBY on the same clock as SEPARATED?

  python3 findmy_rotation.py pi2.csv pi5.csv
  python3 findmy_rotation.py *.csv --period 900 --out rotation.csv

THE QUESTION THIS EXISTS FOR. An offline-finding (separated) advertisement carries the tag's
current rotating public key, and the BLE address is the first 6 bytes of that same key. If the
address is derived from the key chain WHATEVER the tag is broadcasting, then a precomputed list
of a tag's future macs identifies it exactly - in both modes - and the whole rotation-matching
machinery in pi/findMyGroup.py becomes unnecessary for tags whose keys you hold.

A tag in NEARBY mode sends the short 2-byte payload with no key bytes in it. So the payload
cannot answer this. The ADDRESS can: if nearby macs are born on the same 15-minute grid, at the
same phase, as separated ones, they are coming off the same schedule. If nearby macs are born at
arbitrary times, they are not, and key matching would only ever identify a tag while it is away
from its owner - which indoors is backwards.

THIS COSTS NOTHING TO RUN AND NEEDS NO KEYS. It is the test to do BEFORE going after key
material, because it decides whether any of that is worth doing.

Prints
  1. observation window and whether there is enough of it to conclude anything
  2. mac lifetimes, split by the mode(s) that mac was ever seen in
  3. the rotation clock - how tightly mac BIRTHS cluster on a candidate period, per mode
  4. macs seen in BOTH modes, which is direct evidence that a mode switch alone does not
     rotate the address
Writes (--out)
  one row per mac: birth, death, lifetime, modes, whether the measurement was cut off

Input is the rPi's /home/pi/pibeacon/findMyGroup.csv ("write a calibration log on the rPi" in
the group device's dialog, under EXPERTS ONLY), fetched with scp - there is no button for it.
It holds about 40 hours, so one pull is normally the whole measurement.
Several rPis' files can be given at once - a mac is one tag whichever rPi heard it, so they are
merged on the mac, and a tag heard continuously by EITHER rPi counts as continuously heard.
Pi clocks must be NTP-synced.
"""

import argparse
import cmath
import collections
import csv
import datetime
import bisect
import math
import statistics
import time


# The writer's column order, used when a file starts mid-stream and has no header row - which is
# what an excerpt pasted out of a terminal looks like. A real findMyGroup.csv always begins with
# one and repeats it every 10 minutes; see CSV_FIELDS in pi/findMyGroup.py, and keep these in step
FIELDS = ["timestamp", "host", "mac", "distanceIndicator", "status", "hintByte", "appleTypes",
          "battery", "packets", "rssi_median", "rssi_min", "rssi_max", "rssi_smoothed", "member",
          "age_s", "marker", "raw_len", "raw_hex"]


def epochOf(ts):
    """Epoch seconds from the csv timestamp, with or without the tenths."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return time.mktime(datetime.datetime.strptime(ts, fmt).timetuple())
        except (ValueError, TypeError):
            pass
    raise ValueError("bad timestamp: {}".format(ts))


def readRows(paths, report):
    """Every data row from every file, as dicts. Repeated header rows are dropped.

    EVERY TEXT COLUMN IS PADDED in the csv so the file lines up in a terminal, which puts the
    spaces INSIDE the value - so everything is stripped here and nothing downstream may compare
    a raw cell.

    COUNTED PER FILE, because "12 files" and "the 11 you meant plus one that gave nothing" print
    the same total otherwise. The commonest way to get one of those is this tool's OWN --out file
    being caught by the same *.csv that fed it, which is recognised and skipped by name rather
    than being dropped silently, one unparseable row at a time.
    """
    for path in paths:
        n = 0
        with open(path, newline="") as f:
            first = f.readline()
            f.seek(0)
            if first.startswith("mac,birth,death"):
                report.append((path, 0, "this tool's own --out file, skipped"))
                continue
            names = None if first.startswith("timestamp,") else FIELDS
            for row in csv.DictReader(f, fieldnames=names):
                if (row.get("timestamp") or "").strip() == "timestamp":
                    continue        # the header, repeated every 10 minutes, arrives as a row
                out = {}
                for k in FIELDS:
                    out[k] = (row.get(k) or "").strip()
                if out["timestamp"] == "" or out["mac"] == "":
                    continue
                try:
                    out["at"] = epochOf(out["timestamp"])
                except ValueError:
                    continue
                n += 1
                yield out
        report.append((path, n, "" if n else "no rows parsed - is this a findMyGroup.csv?"))


def circular(values, period):
    """How tightly a set of times clusters within a repeating period.

    R IS THE MEAN RESULTANT LENGTH: each time becomes an angle round a circle of one period, and
    R is the length of the average of those unit vectors. 1.0 is every event at the same phase,
    0.0 is spread evenly round the period - and evenly spread is exactly what "not on this clock"
    looks like. An ordinary mean or standard deviation cannot say this at all: times of 1s and
    899s are 2 seconds apart on a 900 second circle and 898 apart on a number line.

    Returns (R, phase seconds, n).
    """
    if not values:
        return 0., 0., 0
    vecs = [cmath.exp(2j * math.pi * ((v % period) / period)) for v in values]
    mean = sum(vecs) / len(vecs)
    phase = (cmath.phase(mean) / (2 * math.pi)) * period
    if phase < 0:
        phase += period
    return abs(mean), phase, len(values)


def coverageOf(byHost):
    """How much of a mac's observed span it was actually being heard for, 0..1.

    PER RPI, AND THE BEST ONE WINS. The question is "was this mac heard CONTINUOUSLY by anybody",
    and asking it of the merged stream cannot work: two rPis do not report in step, so their rows
    interleave and the spacing between consecutive rows of the merge is nothing like the spacing
    at which either of them reports. Measured on one rPi's rows at a time, the spacing is just
    logEverySecs and a hole is obvious.

    THE BASELINE IS THE SMALLEST GAP, NOT THE MEDIAN, and that is the second thing this got wrong.
    A tag heard in three brief bursts has gaps like 10, 400, 10, 500 - half of them holes - so the
    MEDIAN gap is 205s and, judged against that, a 400s hole is not a hole. The smallest gap is
    the rate the rPi actually reports at, which is what a hole has to be measured against.

    THE SPAN IS FIRST ROW TO LAST ROW, deliberately not birth to death. birth comes from age_s and
    can predate the first row in the file by a long way - the mac was being heard then, the rows
    have simply been dropped by trimCsv(). Counting that as absence would mark every mac in a
    trimmed file as intermittent, which is every mac in any file long enough to be worth reading.
    """
    best = 0.
    for times in byHost.values():
        times = sorted(times)
        if len(times) < 3:
            continue
        gaps = [b - a for a, b in zip(times, times[1:]) if b > a]
        if not gaps:
            continue
        base = min(gaps)
        span = times[-1] - times[0]
        if span <= 0 or base <= 0:
            continue
        holes = sum(g - base for g in gaps if g > 3. * base)
        best  = max(best, max(0., min(1., 1. - holes / span)))
    return best


def modeOf(inds):
    """The mode bucket for one mac, from every distanceIndicator it was ever written with.

    "sep" and "near" are what indCsv() abbreviates separated and nearby to. A mac carrying BOTH
    is the interesting one - see the last section - and "len.." is a payload length the rPi has
    no name for, which is kept apart rather than guessed at.
    """
    s = set(inds)
    odd = set(x for x in s if x not in ("sep", "near"))
    if odd:
        return "other"
    if s == {"sep"}:
        return "sep"
    if s == {"near"}:
        return "near"
    return "both"


def describe(lives):
    """n / median / quartiles of a list of lifetimes, as a printable string."""
    if not lives:
        return "{:>5}".format(0) + "  " + "        -" * 4
    q = statistics.quantiles(lives, n=4) if len(lives) > 3 else [min(lives), statistics.median(lives), max(lives)]
    return "{:>5}  {:>8.0f} {:>8.0f} {:>8.0f} {:>8.0f}".format(len(lives), min(lives), q[0], statistics.median(lives), max(lives))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--period", type=float, action="append", default=None,
                    help="candidate rotation period in seconds, repeatable (default: 900 1800 3600 86400)")
    ap.add_argument("--tail", type=float, default=0,
                    help="a mac last heard within this many seconds of the end of the data is still "
                         "alive and its lifetime is a floor, not a measurement (default: 3x the row cadence)")
    ap.add_argument("--min-coverage", type=float, default=0.7,
                    help="a mac must have been heard for this fraction of its life to count as a "
                         "measured rotation rather than something that drifted past (default 0.7)")
    ap.add_argument("--min-life", type=float, default=60.,
                    help="and its life must be at least this long. COVERAGE ALONE CANNOT CATCH a mac "
                         "seen in one burst of two rows: 2 rows x 10s cadence over a 10s life scores "
                         "1.0 by construction. A rotation is ~15 minutes; nothing under a minute is "
                         "one (default 60)")
    ap.add_argument("--succ-gap", type=float, default=30.,
                    help="a death and a birth this close are taken to be one tag rotating. "
                         "pi/findMyGroup.py uses ROTGAP=15 on the frames themselves; this is more "
                         "generous because the csv only samples every logEverySecs, so a handover "
                         "that really took 0s can be observed up to two rows apart (default 30)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    periods = args.period or [900., 1800., 3600., 86400.]

    report = []
    rows = list(readRows(args.files, report))
    if not rows:
        print("no rows read - is this a findMyGroup.csv?")
        return

    stamps = sorted(set(r["at"] for r in rows))
    tStart, tEnd = stamps[0], stamps[-1]
    # THE ROW CADENCE, measured rather than assumed: it is logEverySecs on the rPi, but a merged
    # set of files from several rPis interleaves and a trimmed file has gaps. The median gap
    # between distinct timestamps is what a "still being heard" test has to be scaled against
    gaps = [b - a for a, b in zip(stamps, stamps[1:]) if b > a]
    cadence = statistics.median(gaps) if gaps else 10.
    tail = args.tail if args.tail > 0 else max(3. * cadence, 30.)

    # ---- one record per mac, merged across rPis ----
    # A MAC IS ONE TAG whichever rPi heard it, so nothing here is per host: two rPis hearing the
    # same mac is one life, not two, and splitting it would halve every lifetime in the sample.
    first, last, inds, hosts = {}, {}, collections.defaultdict(set), collections.defaultdict(set)
    birth  = {}
    seenAt = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        m = r["mac"]
        if m not in first or r["at"] < first[m]:
            first[m] = r["at"]
        if m not in last or r["at"] > last[m]:
            last[m] = r["at"]
        if r["distanceIndicator"]:
            inds[m].add(r["distanceIndicator"])
        hosts[m].add(r["host"])
        seenAt[m][r["host"]].add(r["at"])
        # age_s IS WHAT MAKES THIS MEASURABLE AT ALL. It is written as "now - first heard", so the
        # mac's true birth can be recovered from ANY row it appears in - including the first row
        # of a file that started in the middle of the mac's life, or of one trimCsv() has already
        # dropped the beginning of. Without it every mac alive when logging started would look
        # newborn, and the whole lifetime distribution would be pulled towards zero
        try:
            b = r["at"] - float(r["age_s"])
        except (ValueError, TypeError):
            b = r["at"]
        if m not in birth or b < birth[m]:
            birth[m] = b

    recs = []
    for m in sorted(first):
        alive = last[m] >= tEnd - tail      # still being heard when the data runs out
        life  = last[m] - birth[m]
        # COVERAGE: how much of its OBSERVED span the mac was actually being heard for - see
        # coverageOf(), which measures the holes rather than counting rows against a cadence.
        # WHY IT HAS TO BE HERE. A mac that vanishes because it ROTATED and a mac that vanishes
        # because it drifted out of range look identical from a lifetime alone, and the second
        # kind is the majority of what a busy street puts on the air: a neighbour's tag heard for
        # two rows at -95 contributes a "lifetime" of 10 seconds that is not a rotation interval
        # and a "birth" that is not a rotation boundary. Left in, they flatten the lifetime
        # distribution towards zero and push R towards 0 for every mode equally - which is the
        # same shape as the answer "nearby is not on this clock", and would be read as it.
        # A mac heard from birth to death scores ~1.0; one heard in two short bursts scores ~0.1
        cov = coverageOf(seenAt[m])
        recs.append({"mac": m, "birth": birth[m], "death": last[m], "life": life,
                     "mode": modeOf(inds[m]), "inds": "|".join(sorted(inds[m])),
                     "pis": len(hosts[m]), "censored": alive,
                     "rows": sum(len(v) for v in seenAt[m].values()), "cov": cov})

    span = tEnd - tStart
    print("== what was read ==")
    print("  files      : {}".format(len(report)))
    for path, n, why in report:
        if why or len(report) > 1:
            print("      {:>7} rows  {}{}".format(n, path, "   <-- " + why if why else ""))
    print("  rows       : {}   rPis: {}".format(len(rows), ", ".join(sorted(set(r["host"] for r in rows)))))
    print("  window     : {} .. {}   ({:.1f} h)".format(
        datetime.datetime.fromtimestamp(tStart).isoformat(timespec="seconds"),
        datetime.datetime.fromtimestamp(tEnd).isoformat(timespec="seconds"), span / 3600.))
    print("  row cadence: {:.0f}s   still-alive cutoff: last heard within {:.0f}s of the end".format(cadence, tail))
    print("  macs       : {}   of which still alive at the end: {}".format(
        len(recs), sum(1 for r in recs if r["censored"])))

    def measurable(r):
        return r["cov"] >= args.min_coverage and r["life"] >= args.min_life and r["rows"] >= 3
    # ---- did this life END in a rotation, and did it BEGIN in one? ----
    # WHAT COVERAGE CANNOT CATCH, and the live data showed it immediately: a tag that is heard
    # continuously and then WALKS OUT OF RANGE scores a perfect coverage and contributes a
    # "lifetime" that is not a rotation interval and a "death" that is not a rotation boundary.
    # Three separated macs living 249-264s against a 15 minute rotation were exactly that.
    # A ROTATION HAS A SUCCESSOR. The tag does not stop advertising, it changes address, so the
    # old mac's last packet and the new mac's first are all but simultaneous - which is the whole
    # basis of the matching in pi/findMyGroup.py. A departure has no successor. Nothing here tries
    # to say WHICH mac succeeded which, because with several tags in the house that cannot be done
    # from timing alone; only whether a partner exists at all, which is enough to tell the two
    # kinds of death apart in bulk.
    # THE PAIRING RATE IS REPORTED because it is the honest check on this: in a quiet house nearly
    # every death should pair, and if only half of them do then either tags are coming and going
    # or succGap is too tight, and the numbers below are built on a guess either way.
    births = sorted(r["birth"] for r in recs)
    deaths = sorted(r["death"] for r in recs)
    for r in recs:
        # a birth strictly after this death and within succGap, belonging to some OTHER mac.
        # "some other mac" is not tested: a mac cannot be born after its own death
        i = bisect.bisect_left(births, r["death"])
        r["hasSucc"] = i < len(births) and births[i] <= r["death"] + args.succ_gap
        j = bisect.bisect_right(deaths, r["birth"])
        r["hasPred"] = j > 0 and deaths[j - 1] >= r["birth"] - args.succ_gap

    complete = [r for r in recs if not r["censored"]]
    done     = [r for r in complete if measurable(r)]
    thin     = [r for r in complete if not measurable(r)]
    print("  measured   : {} complete lives, of which {} are measurable "
          "(heard for >={:.0%} of a life of >={:.0f}s, over >=3 rows)".format(
              len(complete), len(done), args.min_coverage, args.min_life))
    if thin:
        tooShort = sum(1 for r in thin if r["life"] < args.min_life or r["rows"] < 3)
        print("  dropped    : {} macs that cannot carry a rotation interval - {} too brief to be one "
              "at all, {} heard too intermittently across their span (median coverage {:.0%}). "
              "Passers-by, not rotations".format(
                  len(thin), tooShort, len(thin) - tooShort,
                  statistics.median([r["cov"] for r in thin])))
    # WHY A FLOOR AND NOT A WARNING TO IGNORE: a rotation is ~15 minutes, so a window of two hours
    # holds about eight of them per tag. Under that there are not enough completed lives for the
    # clustering below to mean anything, and a confident-looking R from six samples is worse than
    # no answer. Say so plainly rather than printing numbers that read as a result
    if span < 7200 or len(done) < 20:
        print("\n  !! NOT ENOUGH DATA TO CONCLUDE ANYTHING. This needs several hours - a rotation is")
        print("     about 15 minutes, so a 2 hour window is roughly 8 per tag - and at least ~20 macs")
        print("     whose life both started and ended inside it. There are {} such.".format(len(done)))
        print("     Everything below is printed so the parsing can be checked, not to be read as an answer.")

    rot = [r for r in done if r["hasSucc"]]
    gone = [r for r in done if not r["hasSucc"]]
    print("\n== how each measurable life ENDED ==")
    print("  {:>4} rotated - another mac appeared within {:.0f}s, so the tag changed address".format(len(rot), args.succ_gap))
    print("  {:>4} left    - nothing appeared, so the tag went out of range or stopped advertising.".format(len(gone)))
    print("        Their lifetimes are NOT rotation intervals and they are excluded below.")

    print("\n== mac lifetimes, seconds - lives that ended in a rotation ==")
    print("  {:8} {:>5}  {:>8} {:>8} {:>8} {:>8}".format("mode", "macs", "min", "q1", "median", "max"))
    for mode in ("sep", "near", "both", "other"):
        lives = [r["life"] for r in rot if r["mode"] == mode]
        print("  {:8} {}".format(mode, describe(lives)))
    print("  (a life is from age_s-corrected birth to the last time the mac was heard, merged over rPis)")

    # THE HISTOGRAM EARNS ITS PLACE BECAUSE IT WORKS ON LESS DATA THAN R DOES. R needs the window
    # to cover the period several times before it means anything; a pile of lives sitting on one
    # value is visible the moment there are a dozen of them, and it says the period outright
    print("\n== the same lives as a histogram, 60s buckets - look for a pile, that is the period ==")
    # THE LAST BUCKET IS AN OVERFLOW AND SAYS SO. It used to fold everything at or above the cap
    # into the top 60s bucket under that bucket's own label, which did not merely lose detail - it
    # INVENTED A PILE: five separated lives of 3797, 4293, 4988 and 11767s printed as "5 macs at
    # 3540-3599s", which reads as a tight cluster at 59 minutes and is the exact thing this
    # histogram exists to show. Anything a bucket cannot hold is now labelled ">= cap" and carries
    # its own median, so a wide spread cannot be mistaken for a period again
    CAP = 3600
    top = CAP // 60
    for mode in ("sep", "near", "both"):
        lives = [r["life"] for r in rot if r["mode"] == mode]
        if not lives:
            continue
        buckets = collections.defaultdict(list)
        for v in lives:
            buckets[min(int(v // 60), top)].append(v)
        peak = max(len(v) for v in buckets.values())
        print("  {} ({} macs)".format(mode, len(lives)))
        for b in sorted(buckets):
            vv = sorted(buckets[b])
            n  = len(vv)
            if b >= top:
                label = ">= {}s".format(CAP)
                extra = "   ({:.0f}..{:.0f}s, median {:.0f})".format(vv[0], vv[-1], statistics.median(vv))
            else:
                label = "{}-{}s".format(b * 60, b * 60 + 59)
                extra = ""
            print("    {:>12}  {:>3}  {}{}".format(label, n, "#" * int(round(20. * n / peak)), extra))

    print("\n== the rotation clock: how tightly mac BIRTHS fall on a repeating period ==")
    print("  R is 1.0 when every birth is at the same point in the period and 0.0 when they are")
    print("  spread evenly round it. The period with the highest R is the one the tags are using.")
    print("  THE ANSWER TO THE QUESTION is whether 'near' matches 'sep' - same period, and a phase")
    print("  within a minute or two of it. If it does, the address comes off the key chain in both")
    print("  modes and a precomputed mac identifies a tag whatever it is broadcasting.")
    # TWO WAYS THIS NUMBER LIES, both of them by looking CONFIDENT, which is why they are
    # marked on the line rather than left to be noticed:
    #  1. R IS 1.0 FOR ONE SAMPLE and near 1.0 for two, always, whatever the period - a single
    #     vector is its own mean. Nothing under about 8 births is worth reading.
    #  2. R IS NEAR 1.0 FOR ANY PERIOD LONGER THAN THE WINDOW, for the same reason: if every
    #     birth happened inside one 24 hour period then every birth is at a different phase of
    #     it only in the sense that they are all in the same part of it. The window has to cover
    #     the period several times over before "evenly spread round it" is even possible
    print("\n  {:>9}  {:8} {:>5}  {:>6}  {:>9}  {}".format("period", "mode", "macs", "R", "phase +s", "note"))
    for p in periods:
        tooLong = span < 3. * p
        for mode in ("sep", "near", "both"):
            vals = [r["birth"] for r in done if r["mode"] == mode and r["hasPred"]]
            R, ph, n = circular(vals, p)
            if n == 0:
                continue
            note = []
            if tooLong:
                note.append("MEANINGLESS: window is {:.1f}x this period, needs 3x+".format(span / p))
            if n < 8:
                note.append("only {} birth(s), R is not informative below ~8".format(n))
            print("  {:>9.0f}  {:8} {:>5}  {:>6.3f}  {:>9.0f}  {}".format(p, mode, n, R, ph, "; ".join(note)))

    both = [r for r in recs if r["mode"] == "both"]
    print("\n== macs seen in BOTH modes: {} ==".format(len(both)))
    print("  Each one is a tag that switched between nearby and separated WITHOUT changing its")
    print("  address. That is worth knowing on its own: it says the mode switch alone does not")
    print("  rotate the mac, so the two modes are not running separate address schedules.")
    print("  None of these is evidence either way if the list is empty - it may simply mean no")
    print("  tag changed mode while this was being logged.")
    for r in sorted(both, key=lambda x: -x["life"])[:15]:
        print("  {:17}  life {:>7.0f}s  {:<10}  rPis:{}{}".format(
            r["mac"], r["life"], r["inds"], r["pis"], "   (still alive)" if r["censored"] else ""))

    if args.out:
        with open(args.out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["mac", "birth", "death", "life_s", "mode", "indicators", "pis_heard",
                        "still_alive", "rows", "coverage", "born_in_rotation", "died_in_rotation"])
            for r in sorted(recs, key=lambda x: x["birth"]):
                w.writerow([r["mac"],
                            datetime.datetime.fromtimestamp(r["birth"]).isoformat(timespec="seconds"),
                            datetime.datetime.fromtimestamp(r["death"]).isoformat(timespec="seconds"),
                            "{:.0f}".format(r["life"]), r["mode"], r["inds"], r["pis"],
                            1 if r["censored"] else 0, r["rows"], "{:.2f}".format(r["cov"]),
                            1 if r["hasPred"] else 0, 1 if r["hasSucc"] else 0])
        print("\nwrote {}".format(args.out))


if __name__ == "__main__":
    main()
