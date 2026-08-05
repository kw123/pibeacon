# piBeacon

Indigo plugin that uses Raspberry Pis to track iBeacons / BLE devices and to read a wide range of
sensors attached to the Pis. The Pis report to the Indigo server over the network; the plugin manages
device states, triggers, and the sensor programs running on each Pi.

- **Current version:** 2022.191.248 (2026-08-03) — release. Everything since .171 in short:
  **all BLE work runs in python now**, scanning *and* GATT — no hcidump / lescan / hcitool /
  gatttool / pybluez on a python 3.5+ rPi, via the new stdlib modules `gattAttClient.py` and
  `hciRawSocket.py`. That choice is now **one switch instead of two**: plugin config *"BLE engine
  on the rPis — scanning + connecting"* (python socket / commandline), overridable per rPi; the two
  old prefs meant the same decision and could be set contradictingly. **BLE5 / extended
  advertising** brings the Ruuvi Air E1 full data set (PM1/2.5/4/10, CO₂, VOC, NOx, T/H/P) on a
  BLE5-capable dongle, delivery-tested rather than trusted. **Radios are assigned to
  scan / connect / broadcast / extended-listener by measured quality**, and each role can be
  **pinned per radio** in the rPi device edit — where a USB radio only offers the scanner variants
  it was *measured* to manage, the internal radio is never a scanner, and any radio can be ignored.
  The new menu item **"Qualify the BLE dongles of one RPI.."** does that measuring: scan rate, BT5
  delivery, advertising, stability, sensitivity and a real connect test, feeding a dongle catalogue.
  Each radio now has **its own device state `hci0`…`hci3`**
  (`mac/bus/usb-id/UP/BLE4+5/scan4+5`), replacing `hciInfo`, `hciInfo_beacons`, `hciInfo_beep`,
  `hciInfo_BLEconnect` and `supportsBLE5`. **Beep** is reliable and ~2× faster, battery reads follow
  the tags' wake-up order, and **single-dongle rPis** can beep / read battery / drive switchbots.
  **States are optional**: Ruuvi value families, and min/max vs changes+trend as two independent
  checkboxes on 64 device types (a RuuviTag drops from 82 states to 7) — all default ON. **The
  daily average is time-weighted.** Device dialogs are generated, show **rPi names** and **group
  names**, gained group membership on 21 more types, and are uniformly sectioned. The **status
  column** is aligned by real pixel measurement of the 13 pt system font, with a new config for
  where the date column starts — and changing it re-aligns every existing device at once. Indigo
  state writes are down ~25%. On the rPi side, shell calls (`rm`/`mkdir`/`cp`/`echo >`) were
  replaced by python helpers with atomic writes, the `/var/log/pibeacon` root-ownership trap that
  silently killed logging is fixed, apt no longer retries packages the OS does not have
  (`libgpiod2` → `libgpiod3` on trixie), and the plot scripts no longer flood the log with
  matplotlib/PIL chatter. See `Contents/changelist.txt` for the full list, including ~30 fixes.
- Before that, .220 (2026-08-02) — **the dongle qualification tool works end to
  end**, and the device-edit dialogs are generated instead of copy-pasted. qualifyDongle no longer
  wedges the rPi: it used to hold beaconloop and BLEconnect paused indefinitely, because the tool
  never exited (piBeaconUtils' send thread is not a daemon, so the process hung after printing its
  report) while the caller kept refreshing the pause files. The pause now has a hard cap, the caller
  waits with a timeout and reads a file instead of a pipe, and the tool exits after flushing. Its
  **connect test was measuring nothing**: it paged tags as *public* addresses (0x01 is
  BDADDR_LE_PUBLIC, random is 0x02), so every attempt on every radio timed out and looked like bad
  hardware — 0% became 100% on all three radios once the address type was derived from the tag.
  Role verdicts are reconciled now: a measured 100% grants "connect" whatever the ACL MTU says, a
  measured 0% withholds it, and every MTU band explains itself. **SwitchBot contact sensors stopped
  firing phantom triggers** — the type-4 frame has no button counter (nibble 13 there is a rotating
  open indicator), but it was read as one, written to indigo and used to overwrite the real counter
  from the type-3 frame; that produced two spurious state changes roughly every 20 minutes.
  **Device dialogs:** the rpi-selection and group-membership blocks are built at runtime by
  `getDeviceConfigUiXml`, so Devices.xml lost ~4,300 lines of duplicated `<Field>` markup, rpi
  checkboxes now carry the **rPi name** and group checkboxes the **configured group name**, group
  membership works on 21 more device types, and "Other5" is finally reachable. Section headers are
  uniform (green, `====`) and denser; "state column" is called "status column" everywhere.
  Internally `plugin.py` is sorted into 13 labelled sections, its ~900 lines of static tables moved
  to `piBeaconConstants.py`, and the cProfile machinery is gone.
- Before that, .185 (2026-07-28): **device states are optional now**: Ruuvi
  sensors can switch whole value families off in device edit (temperature, humidity, pressure,
  CO2, VOC, illuminance, acceleration), and on *every* sensor the min/max block and the
  changed-values/trend block are two independent checkboxes — a RuuviTag drops from 82 states
  to 7 with everything off. All default ON, so existing devices are untouched until edited.
  **The daily average is time-weighted** now: readings are weighted by how long they were
  valid instead of counting each equally, which was wrong because sensors report far more
  often while a value is moving (a day of 20 h at 10 °C then 4 h at 20 °C reported 17.5 °C
  instead of 11.7 °C). RuuviAir matched to its hardware: no battery states (it is USB-C
  powered) and illuminance off by default (Ruuvi dropped the light sensor). Internally,
  `plugin.py` moved to py3 f-strings.
- Before that, .184 (2026-07-26): BLE5 live-verified end to end (dongle receives Ruuvi Air E1
  incl. PM1/PM4/PM10; delivery-tested probe with persisted verdict, strict 3-radio role rule
  scan/connect/broadcast, new rpi state "supportsBLE5", extScanTest.py tests all adapters in one
  run); indigo update-load cut ~25% (lastUpdateFromRPI now debug-gated, TxPowerReceived on
  delta>5 only); coin-cell battery% temperature-compensated correctly (whole voltage window
  shifts with cold, not just the empty point); i2c_active ghost addresses fixed; socket comm
  hardening (sendall + receiver typo).
- Before that, .181–.183 (2026-07-24):
  **single-dongle GATT root cause found and fixed** — the old pause pre-disabled the LE scan
  behind the kernel's back, which made every create-connection on the onboard radio time out;
  the pause now stops only the iBeacon advertising and the kernel manages the scan itself
  around its connect ("keepScan"). Beeps land in ~3.5–8 s on a single onboard radio that
  keeps scanning throughout (no pre-listen for the ATT engine — the kernel's pending
  create-connection is the listener; two short pending windows re-roll a silently wedged
  initiator; fast ENOSYS retries; rssi-tagged diagnostics; gatttool as automatic last-resort
  fallback). Battery batches: any adv counts as "tag online" and beacon tracking continues
  during every read. **Smart dongle auto-assignment** ("let the RPi decide"): the good
  adapter goes to connects (beep/battery/iphone/switchbot), the other — even a known-bad
  CSR clone — to scanning, with a problem-triggered warning when a clone struggles.
  **attSocket is now the default gatt engine** (and "socket" the default scan method) on
  every install — rPis that cannot run it (py < 3.5) fall back to gatttool automatically.
  Also: no more parameter-file reprocess churn on the rPis (timestamp-only resends are
  ignored); `acceptNewiBeacons` renamed to `acceptNewBeaconsMinSIgnal` with a safe OFF
  default (stops the beacon_parameters file from flooding with drive-by beacons); rPi log
  timestamps with tenths of a second and without the redundant Lv column.
  Before that, .172–.180, the BLE modernization: **all GATT work runs without
  gatttool/pybluez/hcitool on py3.5+ rPis** (opt-in "attSocket" mode) — stdlib ATT client
  over LE L2CAP for beep/battery/time-set, BLE sensors and switchbot incl. curtain feedback;
  iPhone/watch presence via classic-BT paging (stdlib sockets, `iphoneDebug` switch);
  **"socket" as the default scan method** (full hcidump parity, new-kernel HCI-filter fix);
  battery batches read in wake-up order; pixel-accurate device-list column alignment.
  See `Contents/changelist.txt` for the full history.
- **Author:** Karl Wachs
- **Forum / support:** http://forums.indigodomo.com/viewforum.php?f=164

## Setup

Setup is automatic. All you need is a working Raspberry Pi on the network with a known IP number
(and its login credentials). Enter the IP in the plugin's setup menu ("Initial BASIC setup of rPi
servers") — the plugin connects via SSH/FTP and pushes everything to the rPi: all program files,
required libraries, and the configuration. It creates the Indigo devices and keeps the rPi's files
up to date automatically after plugin upgrades. Whenever you change sensors or outputs in Indigo,
the updated config and any needed files are pushed to the rPi again — no manual editing on the Pi
is required.

**Note:** if you replace the plugin bundle in Indigo's Plugins folder manually or via a sync tool
(instead of double-clicking the .indigoPlugin, which does this for you), always **reload the plugin
in Indigo afterwards**. A running plugin whose folder was replaced underneath it keeps working, but
every command it spawns logs harmless `shell-init: getcwd` warnings until it is restarted.

## How the communication works

```
                             INDIGO SERVER (Mac)
   +-------------------------------------------------------------------+
   |   Indigo  <------------->  plugin.py (piBeacon)                   |
   |   devices, states,          - creates/updates Indigo devices      |
   |   triggers, actions         - listens on a TCP socket for Pi data |
   |                             - sends config/commands to the Pis    |
   +---------------+------------------------------^--------------------+
                   |                              |
     config, files, commands, programs       sensor data, beacon reports,
     via  SSH / FTP / TCP socket             status (JSON via TCP socket)
                   |                              |
        +----------+---------------+--------------+------+
        v          v               v                     v
   +---------+ +---------+    +---------+          +---------+
   | RPi #0  | | RPi #1  |    | RPi #2  |   ...    | RPi #n  |
   +----+----+ +---------+    +---------+          +---------+
        |
        |  master.py - supervisor: starts/watches all programs below
        |  receiveCommands.py - executes commands from the Indigo server
        |  beaconloop.py / BLEconnect.py - BLE scanning + GATT connections
        |  one program per sensor type (e.g. bme680.py, INPUTgpio.py, ...)
        |  output programs (display.py, neopixel3.py, setStepperMotor.py, ...)
        |
        +-- i2c / SPI / GPIO / 1-wire / serial -->  wired sensors & outputs
        |
        +-- BLE dongle(s) <~~~ BLE advertisements ~~~<  iBeacons, BLE sensors,
                          ~~~> GATT connections    ~~~>  switchbot devices

   Beacon tracking: every Pi reports RSSI per beacon; the plugin combines the
   reports, estimates distance, sets the beacon device to up/down, tracks the
   "closest rPi", and drives the home/away group triggers.
```

## Supported iBeacon types

Any tag that broadcasts standard **iBeacon / Eddystone** advertisements works. The file
`Contents/beaconTypes.txt` contains a detailed comparison (form factor, battery, beep support,
battery-level reporting). Highlights:

- **Musegear iTrack (EU)** — top pick: beep, battery reading, button press detectable; regular / mini / card
- Rechargeable with beep + battery: Nonda Aiko, Nonda iHere, Smart Tracker
- CR2032 with beep + battery: NutFind 3 / Nutale / Nut Pro, Vozni iTrack, SpotyPal, Rinex / Njoii iTrack
- Beep, no battery reading: Innway Tag / Chip / Card, Cube, Orbit, Safedome (card)
- Beacon + sensor combos: ruuviTag (T/H/P/accel), myBlueT (temp)
- Pure iBeacon/Eddystone: BlueCharm BC011, MiniBeacon, Feasy (USB + triangle), SocialRetail, Radius,
  and most generic ~$5 iBeacon tags
- Fun extras: anything that advertises — e.g. Tovala oven, Oral-B toothbrush
- Not recommended: Tile (post-2018), XY4, swiftFind/ZenLife, iSearching-type tags

The plugin can auto-accept new beacons, beep beacons that support it, read battery levels, and
track cars (dedicated *Car* device with per-car beacon assignment).

## Supported BLE sensors (no pairing — data via broadcast or GATT)

Reaction time for buttons is < 0.4 s; battery friendly. Full details in `Contents/BLE-sensorTypes.txt`.

- **ruuvi**: RuuviTag (T/H/P/accel), RuuviAir (T/H/P/CO2…)
- **INGICS iBS01/02/03/04**: on/off button, magnet contact, IR/PIR motion, temp, probe temp, XYZ accel
- **Xiaomi MiJia**: LYWSD02 clock, LYWSDCGQ round, LYWSD03MMC square, formaldehyde MJHFD1,
  VegTrug / Flower Care (moisture + conductivity)
- **switchbot**: temp/hum, temp/hum/CO2, humidifier, mm-wave motion (occupancy), motion, contact,
  remote button (WoBtn) — can be beeped to locate it
- **Minew**: E8 (XYZ accel), S1 (temp/hum), S1 Plus (accel + T/H)
- **Kaipule iSensor**: on/off, magnet, water, PIR, temp/hum, 4-button remote key fob
- **Shelly**: door, button, motion
- **Govee** temp/hum (H5101/H5075/H5177/H5174), **ThermoBeacon**, **Thermopro**, **InkBird Pool 01B**,
  **TempSpike** meat thermometer, **april Brother** ABN01/ABN03, **blueradio SensorBug**,
  **Satech STixx**, **iTrack / Musegear button**, **Hunter Node BT**, **meeblue**, **myBlueT**
- **BLE-connect**: generic GATT connect device for sensors that need an active connection

## Supported wired sensors (INPUT devices on the Pi)

**Temperature / pressure / humidity**
1-wire DS18B20, DHT, tmp117, TMP102, MCP9808, LM75A/LM35, T5403, MS5803, BMPxx/BMP280, BMP388,
SHT21, AM2320, BME280, BME680 (+air quality), si7021, max31865 (platinum RTD),
tmp006/tmp007 + mlx90614 (remote infrared)

**Air quality / gas**
particulate matter (PM) sensor, sgp30 (CO2/VOC), scd30, scd40 (CO2/T/H), sgp40 (VOC),
MH-Zxx CO2 (i2c + serial), ccs811 (CO2/VOC)

**Light / color / UV**
TCS34725 (lux+RGB), MAX44009, as726x (spectral), OPT3001, VEML7700, VEML6030, VEML6040 (RGBW),
VEML6070 (UV), VEML6075 (UVA/UVB), TSL2561 (ambient+IR)

**Distance / proximity / imaging**
ultrasound, VL53L0X / VL53L1X (time-of-flight), vcnl4010, vl6180 (TOF+lux), apds9960 (proximity),
amg88xx + mlx90640 (IR cameras), 360° lidar

**Motion / orientation**
l3g4200/l3gd20h gyro, mag3110 + hmc5883L (3-axis), lsm303 + mpu6050 (6-axis),
BNO055 + mpu9255 (9-axis)

**Analog (ADC) / power**
ADC121, ina219 + ina3221 (V/A metering), MCP3008 (SPI 8×10bit), ADS1115, PCF8591

**GPIO & switches**
GPIO inputs (1/4/8/26 pins), pulse counter, coincidence detector, touch pads (1/4/12/16),
rotary switch (absolute + incremental)

**Other**
DF2301Q voice recognition, face-gesture sensor, RG11 rain sensor, moisture sensor,
as3935 lightning detector

**Custom**: `mysensors.py` / `myprogram.py` device types run your own code on the Pi;
`SPECIAL-launchpgm.py` starts/supervises any external program.

## Outputs

- **GPIO**: on/off pin, dimmer (PWM)
- **Relays**: i2c relay boards, switchbot bot (press/pulse), switchbot curtain (incl. v3s)
- **Analog / DAC**: MCP4725 (12-bit), PCF8591 (8-bit)
- **Displays**: LCD/OLED/e-ink displays (`display.py`, incl. extra pages sent from Indigo),
  xWindows output, distance display
- **LEDs**: NeoPixel strips/matrices, NeoPixel dimmer, NeoPixel clock, sundial clock
- **Motion**: stepper motors
- **Misc**: FM radio TEA5767, sprinkler controller, garage door, sound playback on the Pi,
  `myoutput.py` for custom output code

## Actions (Indigo action groups / scripts)

- **Pi management**: send config via FTP or socket, reboot / shutdown via SSH or socket
  (incl. hard variants), stop/refresh NTP, set Pi time, send arbitrary unix command,
  play sound file, restart plugin
- **Sensors**: pause / reset / restart a sensor device, request fresh data, calibrate sensors,
  reset GPIO/touch/pulse counters
- **Outputs**: set GPIO pin high/low, set i2c relay, switchbot relay / curtain,
  set DAC value (MCP4725 / PCF8591), FM radio tuning, NeoPixel pixels, display text/graphs,
  extra display pages, stepper motor commands, send text to `myoutput.py`
- **Beacons**: get battery level (one/all), beep a beacon (incl. the SwitchBot remote button)
- **Device utilities**: set/get any device property, set any device state

A parallel set of interactive **menu items** covers setup (create/config/replace Pis, fix IP or
duplicate Pi numbers), beacon management (accept/ignore, replace, battery, beep, fast
beacon→switchbot actions), diagnostics (track MACs, special logging, print configs,
**qualify the BLE dongles of a Pi**), and output testing.

## Trigger events

- Group presence: **Family / Guests / Other1 / Other2 / Other3** × **allHome / oneHome / allAway /
  oneAway** (20 combinations)
- **someStatusHasChanged** — any beacon changed up/down
- **someClosestrPiHasChanged** — any beacon's closest-Pi changed (room-level tracking)

## Layout

- `Contents/Server Plugin/plugin.py` — the Indigo server plugin
- `Contents/Server Plugin/piBeaconConstants.py` — the plugin's static tables (prefs defaults,
  device-type/state maps, allowed sensor and output lists); split out of `plugin.py`
- `Contents/Server Plugin/pi/` — programs deployed to and run on the Raspberry Pis
  (`master.py` supervises; one program per sensor type)
  - `beaconloop.py` — BLE scanning, radio-role assignment, beacon decoding
  - `BLEconnect.py` — GATT work: beep, battery, BLE sensors, switchbot, iPhone presence
  - `gattAttClient.py` / `hciRawSocket.py` — the python-stdlib GATT/ATT and raw-HCI backends
    (no gatttool, hcitool, hcidump or pybluez needed; python ≥ 3.5)
  - `qualifyDongle.py`, `extScanTest.py`, `ruuviPrint.py` — standalone diagnostic tools that can
    also be run by hand on a Pi
- `Contents/changelist.txt` — version history
- `Contents/beaconTypes.txt` — beacon hardware comparison
- `Contents/BLE-sensorTypes.txt` — BLE sensor hardware details
