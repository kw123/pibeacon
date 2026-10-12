Bluetooth controller PATCH RAM firmware (.hcd), installed to /lib/firmware/brcm/ by
installBTfirmware.py (called from master.py at startup, and idempotent - it does nothing
once the patch is in place).

WHY THIS EXISTS
A BCM20702 without its patch runs on ROM firmware and falls off the usb bus whenever it is
reset. Measured on rpi-2: the dongle re-enumerated about once per qualifyDongle run, came back
under a NEW hci number every time, and in between produced exactly the symptoms that look like
dead hardware - a radio that accepts every scan command with status 0 and delivers nothing,
"adapter does not come up properly - unusable", and roles silently landing on the wrong radio
because the hci numbers had moved. After installing the patch: 10 down/up cycles in a row, same
hci number, UP RUNNING every time, ZERO re-enumerations.

    before:  BCM20702A1 (001.002.014) build 0000      <- ROM, "Patch file not found"
    after:   BCM20702A1 'brcm/BCM20702A1-0a5c-21e8.hcd' Patch
             BCM20702A1 (001.002.014) build 1764      <- patched

FILE NAMING
The kernel asks for brcm/<CHIP>-<vid>-<pid>.hcd and prints the names it tried when it finds
none ("dmesg | grep -i 'Patch file not found' -A4"). The vid-pid in the file name is what
installBTfirmware.py uses to find the usb device it has to re-probe, so keep the kernel's
spelling exactly.

BCM20702A1-0a5c-21e8.hcd   35934 bytes
    sha256 521d4297ffb1f055e600abeb3ce7a2062956ec158af38cc361da68d6136b1e4f
    for Broadcom Corp BCM20702A0 Bluetooth 4.0 dongles (usb id 0a5c:21e8)

LICENCE: proprietary Broadcom firmware. It is not packaged by Debian/Raspberry Pi OS, which is
why it has to be carried here. Redistributed as a binary blob.
