#!/usr/bin/env python3
#
# WHERE THIS LIVES: Contents/Server Plugin/, with the plugin's OTHER mac-side tools -
# makeBeaconPositionPlots.py, makeCameraPlot.py, makeLidar360Plot.py, MAC2Vendor.py. It is not
# in pi/ because it never goes near an rpi, and it is not loose in Contents/ because nothing
# else is: Contents/ holds Info.plist, the changelist and the type tables, and one stray .py
# sitting beside them looked exactly like the accident it was mistaken for.
# Its companion findmy_scan.py DOES live in pi/ and does run on an rpi; the two are described
# together everywhere, which is the only reason this one ever looks misplaced.
# python3 ONLY - yield from, the py3 queue module - which for a file that never goes near an
# rpi costs nothing. findmy_scan.py is py3-only as well, and is safe for a different reason:
# beaconloop never imports it. Neither belongs in the loop; do not "fix" either into it.
#
"""
findmy_merge.py  -  combine findMyGroup / findmy_scan CSV logs from several Pis (stdlib only, runs on the Mac too)

  python3 findmy_merge.py pi1/*.csv pi2/*.csv pi3/*.csv --join -70 --min-pis 2 --out merged.csv

Prints
  1. count timeline  - per time bin: members by "best Pi >= join" vs "at least N Pis >= join"
                       (only bins where a count changes). A rotation inside a bin can show a +1 blip;
                       the live scanner hides that with its --stable timer.
  2. calibration     - per marker and address: best-Pi RSSI min / median / max and how many Pis heard it.
                       The marker is written once when it changes and restated with each repeated
                       header block, so it is FORWARD-FILLED here: a blank cell means "same as
                       above", "-" means cleared. Filling restarts at every file.
                       Pick --join / --leave in the gap between "farthest inside" and "just outside".
Writes
  merged CSV         - one row per (bin, address) with the RSSI seen by each Pi.
Pi clocks must be NTP-synced.
"""

import argparse
import collections
import csv
import datetime
import statistics
import time


def cell(row, name):
    """One csv field, stripped. The writers PAD every text column to a fixed width so the file
    lines up when read in a terminal, which puts the spaces inside the value - so "sep " and
    "kitchen " arrive here with them and nothing may be compared raw."""
    return (row.get(name) or "").strip()


def epochOf(ts):
    """Epoch seconds from the csv timestamp, with or without the tenths.

    The rPi files used to carry a separate "epoch" column purely so this did not have to parse a
    date. That column is gone - timestamp now has tenths of a second, which is finer than any bin
    these rows get put in - so the parsing happens here instead.
    """
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return time.mktime(datetime.datetime.strptime(ts, fmt).timetuple())
        except (ValueError, TypeError):
            pass
    raise ValueError("bad timestamp: {}".format(ts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--bin", type=int, default=30, help="seconds per time bin")
    ap.add_argument("--join", type=float, default=-70)
    ap.add_argument("--min-pis", type=int, default=2)
    ap.add_argument("--out", default="findmy_merged.csv")
    args = ap.parse_args()

    samples = collections.defaultdict(lambda: collections.defaultdict(list))  # (bin, mac) -> host -> [rssi]
    inds, markers, hosts = {}, collections.defaultdict(set), set()

    for path in args.files:
        # THE MARKER IS FORWARD-FILLED, and per FILE - one file is one rpi's log, and carrying a
        # marker from the end of one into the start of another would label rows with a session
        # they were not part of. The writers put the text on ONE row when it changes and restate
        # it with each repeated header block, rather than on every row: a blank cell means "same
        # as the row above", and "-" means the marker was cleared at that point.
        carry = ""
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                # the column header is REPEATED every 10 min in the rPi files, so it arrives here
                # as an ordinary row - skip it before anything tries to parse "timestamp" as a date
                if cell(row, "timestamp") == "timestamp":
                    continue
                # EVERY TEXT COLUMN IS PADDED to a fixed width in the csv so the file can be read
                # by eye, which means the spaces are INSIDE the value and everything must strip
                mark = cell(row, "marker")
                if mark == "-":
                    carry = ""
                elif mark:
                    carry = mark
                try:
                    b = int(epochOf(cell(row, "timestamp")) // args.bin) * args.bin
                    rssi = float(row["rssi_median"])
                except (KeyError, ValueError, TypeError):
                    continue
                host = cell(row, "host")
                key = (b, cell(row, "mac"))
                samples[key][host].append(rssi)
                inds[key] = cell(row, "distanceIndicator")
                hosts.add(host)
                if carry:
                    markers[b].add(carry)

    hosts = sorted(hosts)
    rows, per_bin = [], collections.defaultdict(list)
    for (b, mac), by_host in sorted(samples.items()):
        med = {h: statistics.median(v) for h, v in by_host.items()}
        best_host = max(med, key=med.get)
        r = {"bin": b, "mac": mac, "indicator": inds[(b, mac)], "best": med[best_host], "best_host": best_host,
             "pis_heard": len(med), "pis_strong": sum(1 for v in med.values() if v >= args.join),
             "marker": " | ".join(sorted(markers[b])), "per_host": med}
        rows.append(r)
        per_bin[b].append(r)

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "mac", "distanceIndicator", "best_rssi", "best_pi", "pis_heard", "pis_strong", "marker"] + hosts)
        for r in rows:
            w.writerow([datetime.datetime.fromtimestamp(r["bin"]).isoformat(timespec="seconds"), r["mac"], r["indicator"],
                        r["best"], r["best_host"], r["pis_heard"], r["pis_strong"], r["marker"]]
                       + [r["per_host"].get(h, "") for h in hosts])

    print("hosts: {}   bins: {}   rows: {}   -> {}".format(", ".join(hosts), len(per_bin), len(rows), args.out))
    print("\n== count timeline (changes only) ==")
    print("{:19}  {:>9}  {:>9}  {}".format("time", "best>=join", "{}Pi>=join".format(args.min_pis), "marker"))
    last = None
    for b in sorted(per_bin):
        best_cnt = sum(1 for r in per_bin[b] if r["best"] >= args.join)
        multi_cnt = sum(1 for r in per_bin[b] if r["pis_strong"] >= args.min_pis)
        m = " | ".join(sorted(markers[b]))
        if (best_cnt, multi_cnt, m) != last:
            print("{:19}  {:>9}  {:>9}  {}".format(
                datetime.datetime.fromtimestamp(b).isoformat(timespec="seconds"), best_cnt, multi_cnt, m))
            last = (best_cnt, multi_cnt, m)

    print("\n== calibration: best-Pi RSSI per marker / address ==")
    groups = collections.defaultdict(list)
    for r in rows:
        if r["marker"]:
            groups[(r["marker"], r["mac"])].append(r)
    print("{:28}  {:17}  {:>5}  {:>6}  {:>6}  {:>6}  {:>7}".format("marker", "mac", "bins", "min", "median", "max", "pisHeard"))
    for (m, mac), rs in sorted(groups.items()):
        vals = [r["best"] for r in rs]
        print("{:28}  {:17}  {:>5}  {:>6.0f}  {:>6.0f}  {:>6.0f}  {:>7.1f}".format(
            m[:28], mac, len(rs), min(vals), statistics.median(vals), max(vals),
            statistics.mean(r["pis_heard"] for r in rs)))


if __name__ == "__main__":
    main()
