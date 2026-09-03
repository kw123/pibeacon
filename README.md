# piBeacon

Indigo plugin that uses Raspberry Pis to track iBeacons / BLE devices and to read a wide range of
sensors attached to the Pis. The Pis report to the Indigo server over the network; the plugin manages
device states, triggers, and the sensor programs running on each Pi.

- **Current version:** 2022.191.252 (2026-08-31) — release
- **Author:** Karl Wachs
- **Forum / support:** http://forums.indigodomo.com/viewforum.php?f=164
- **Change log:** see `Contents/changelist.txt`

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
        |                 ~~~> GATT connections    ~~~>  switchbot devices
        |
        +-- IR led        ~~~> 38 kHz remote frames ~~>  air conditioners
            IR receiver  <~~~ a real remote, to record it

   Beacon tracking: every Pi reports RSSI per beacon; the plugin combines the
   reports, estimates distance, sets the beacon device to up/down, tracks the
   "closest rPi", and drives the home/away group triggers.
```

## BLE radios: how many, what they do, which ones to buy

Everything BLE runs in python on the Pi — scanning *and* GATT — through the stdlib modules
`hciRawSocket.py` and `gattAttClient.py`. No hcidump, lescan, hcitool, gatttool or pybluez is needed
on a Pi with python ≥ 3.5. One plugin config switch covers it: *"BLE engine on the rPis — scanning +
connecting"* (python socket / commandline), overridable per Pi in the rPi device edit. Pis that
cannot run it (python < 3.5) fall back to the command-line tools automatically.

### The four roles

Each Pi splits its bluetooth adapters over four jobs:

- **scan** — continuous LE scanning: iBeacons and all broadcast-only BLE sensors.
- **broadcast** — the Pi's own iBeacon advertisement, roughly one every 8–10 s. This radio's MAC is
  the Pi's identity (what other Pis hear, and what the plugin links the rPi device to).
- **BLEconnect** — everything that needs a GATT connection: beep, battery reads, connect-type BLE
  sensors, switchbot, and iPhone/watch presence paging.
- **extListener** — BLE5 extended advertising only, e.g. the full Ruuvi Air E1 data set
  (PM1/2.5/4/10, CO₂, VOC, NOx, T/H/P). Needs a BLE5-capable radio that holds no other role.

Roles are assigned by *measured* quality, not by what a dongle claims. The internal (UART) radio is
never used as a scanner — its scanning fights wifi — but it is the natural home for BLEconnect and
for the broadcast.

### What happens with 1, 2 or 3 radios

- **One radio (internal only)** — it does everything. While a GATT job runs (beep, battery,
  switchbot), the Pi pauses only its own iBeacon advertising; the LE scan keeps running, so beacon
  reception continues and beeps land in ~3.5–8 s. No BLE5.
- **Two radios** — scan and broadcast on the dongle, BLEconnect on the internal radio. No BLE5
  listener: the second radio belongs to BLEconnect, and beep/battery/switchbot outrank E1 reception.
  *Exception:* a BLE5-only dongle (one that refuses BLE4 scan commands with 0x0C, e.g. Barrot /
  UGREEN 33fa:0012) can do nothing else, so it becomes the extended listener while scan, broadcast
  and BLEconnect all stay on the internal radio.
- **Three or more radios** — scan / BLEconnect / extListener each get their own, and the broadcast
  rides along with the scanner (one advertisement per 8–10 s costs it nothing). If the scanner is
  running in extended mode, the broadcast moves to a non-BLE5 radio instead: a legacy advertising
  command locks a controller into the legacy command family and kills extended reception.
- **Not supported:** a BLE5-only dongle with no internal radio — nothing can scan BLE4 and the Pi
  receives no ordinary beacons at all. The Pi logs this and sends an error to Indigo.

Every role can also be **pinned per radio** in the rPi device edit. A USB radio is only offered the
scanner variants it was *measured* to manage ("scanner BLE4", "scanner BLE5", "scanner BLE4 + BLE5"),
the internal radio is only offered BLEconnect, and any radio (except the last one) can be set to
"ignore". A pin also lifts the "BLE5 needs three radios" rule — you have said which radio does it.

Each radio has its own device state `hci0`…`hci3`, holding
`mac / bus / usb-id / UP-DOWN / BLE4+5 / scan4+5`, so what the Pi found and what it decided is
visible in Indigo.

### Testing dongles: "Qualify the BLE dongles of one RPI.."

The menu item runs `pi/qualifyDongle.py` on one Pi and prints the report into the Indigo log. It
answers the deployment question — *which of the four roles can this adapter actually do* — and it
trusts nothing the hardware claims; only delivered packets count. (LE feature bit 12 is set by
dongles that deliver zero extended reports, and dongles that pass the extended test can be useless
as scanners.) Phases: fingerprint (bus, OUI, ACL MTU, USB VID:PID, kernel), health after a reset,
claimed BLE5 features, extended reception, legacy reception (including whether the commands were
*accepted* at all), advertising, and an optional connect test against a real tag, repeated N times —
one lucky connect proves nothing. Each measuring phase also profiles per-second buckets and the
longest silence (an average hides a radio that delivers one burst and then stops) plus the RSSI
distribution as a sensitivity proxy.

beaconloop and BLEconnect are paused while the test runs, so no beacons are received for those
seconds — run it when a short gap does not matter. Results are appended to a shared
`dongleCatalogue.json` in the plugin's preferences folder, keyed by USB VID:PID, and they are what
the per-radio pin menus offer.

One thing the report says that does *not* depend on your surroundings: an **ACL MTU ≤ 400** marks a
CSR8510 clone — scans fine, unreliable for connects.

### Measured dongle types

Compare dongles only against each other **on the same Pi in the same place**: how many packets a
radio delivers depends entirely on how many BLE devices are talking around it, so the plugin judges
a radio relative to what the other radios in that Pi hear, never against a number from someone
else's house. What follows is therefore a ranking, not a specification.

- **Pi internal, Broadcom (`B8:27:EB`)** — the fastest scanner of the lot, no BLE5. It is
  deliberately kept for connects and broadcast anyway, because scanning on it fights wifi.
- **Broadcom BCM20702A0 (`0a5c:21e8`)** — nearly as fast as the internal radio, no BLE5, connect
  proven. An excellent BLE4-only scanner.
- **Realtek ASUS USB-BT500 (`0b05:190e`), Realtek BT5.3 (`0bda:a729`), Realtek BT6.0 (`0bda:a760`)** —
  clearly slower than the Broadcoms in BLE4, but they receive extended advertising well and connect
  reliably. The all-rounders: BLE4 + BLE5 in one dongle, and the ones to buy for E1 reception.
- **Barrot USB2.0-BT (`33fa:0010`)** — refuses BLE4 scan commands entirely, and is the strongest
  extended receiver measured. Excellent extended listener, useless as a scanner.
- **UGREEN BT6.0 (`33fa:0012`)** — also BLE4-deaf, and its extended reception is weak. Extended
  listener and broadcast only.
- **Mercusys MA530 (`2c4e:0115`)** — delivered nothing in either mode: broadcast only. Do not buy for
  this job.
- **CSR8510 clones** — scan acceptably but their ACL MTU gives them away; they get the scan or
  broadcast role and are kept away from connects.

## Supported iBeacon types

Any tag that broadcasts standard **iBeacon / Eddystone** advertisements works. The file
`Contents/beaconTypes.txt` contains a detailed comparison (form factor, battery, beep support,
battery-level reporting). Highlights:

- **iTrack** (sold in the EU by **Musegear**, its EU distributor) — top pick: beep, battery reading,
  and a **button press that can trigger an Indigo action**; regular / mini / card
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

## Position plot of the beacons

Beyond "which Pi is closest", the plugin can draw the beacons onto a **map of your home** as a PNG
that refreshes by itself — enable it in the plugin config ("Create png file of x,y,z positions of
iBeacons") with an update interval of 30 s to 10 minutes, or only when a beacon has moved by a
chosen number of distance units.

How it works: each rPi device gets accurate x,y,z coordinates, each beacon its TX power, and the
position is interpolated from the strongest and second-strongest Pi signal. Floors are handled with
**z levels** — one number per floor (e.g. `0,5,10,15`), used again in the rPi device edit, and
beacons on different floors are drawn with different hatching.

- Drop a `background.png` (your floor plan) into the plugin's `plotPositions/` preferences folder or
  into the output path you configure, and the beacons are drawn on top of it.
- X/Y scale are given in your own distance units (e.g. 20 by 30 m), image size by the number of
  y-dots; the output file location is configurable.
- Per beacon, in the device edit: whether it appears at all, its symbol (text label, dot, small
  circle, circle sized by the distance to the closest Pi, square), symbol colour, transparency, text
  colour and a short nickname.
- Options for showing the rPis themselves, showing or hiding expired beacons, symbol size, caption,
  timestamp and a free title with position and rotation.
- BLE-connect devices are plotted along with the beacons; expired ones switch to a distinct symbol.

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

## Sensor statistics: min/max, average, trend — and how to switch them off

Every sensor value the plugin tracks (temperature, humidity, pressure, CO₂, VOC, illuminance,
moisture, conductivity, rain rate, counts, generic INPUTs, …) can carry a set of derived states:

- **min/max block** — `…MinToday` / `…MaxToday` with the time they happened (`…MinTodayAt` /
  `…MaxTodayAt`), the same four for yesterday, plus `…AveToday` / `…AveYesterday` and
  `…MeasurementsToday` / `…MeasurementsYesterday`. Everything rolls over at midnight.
- **changes + trend block** — `…ChangeMinutes05/10/20` and `…ChangeHours01/02/06/12/24/48`, and the
  `…Trend` derived from them.

**Switching them on and off.** Both blocks are two *independent* checkboxes per value in the device
edit, and whole value families (Temperature, Humidity, Pressure, CO₂, VOC, Illuminance,
acceleration) can be switched off entirely — a value family that is off has no states at all, and
its min/max and changes checkboxes are forced off with it. With everything off a RuuviTag drops from
82 states to 7. Every option defaults to ON, so devices you never edit keep exactly the states they
had. The exceptions are hardware-driven: the RuuviAir has no battery states (it is USB-C powered)
and its illuminance defaults to off, because Ruuvi dropped the light sensor from that model.

**The daily average is time-weighted.** A reading counts for *how long it was valid*, not for how
often it arrived. This matters because sensors report on value-change **or** on an idle timer, so a
fast-moving value reports far more often than a quiet one — a plain sum/count lets a short hectic
period outweigh a long calm one. A day of 20 h at 10 °C followed by 4 h at 20 °C is now reported as
**11.7 °C**, where counting each reading equally gave **17.5 °C**. The accumulator is persisted with
the change history (saved hourly and on plugin stop), so a restart does not throw away the part of
the day already measured.

## Air conditioners over IR

An **OUTPUT-Thermostat-IR-AC** device drives an air conditioner through an infrared LED on a Pi
GPIO pin. It appears in Indigo as an ordinary thermostat — mode, setpoint and fan — and the
protocol is a device setting, currently **Toshiba** (RAS series) and **Gree**.

IR is one way: nothing is read back, so the device states are what the plugin *believes* the AC is
doing. That stays true until somebody picks up the hand remote.

### The hardware

One GPIO pin, a transistor and an IR LED. Measured in a normal room: **three IR940 LEDs in series
at ~120 mA reach the AC from anywhere in the room**, pointed at it or away — the reflections are
enough, so the LED does not have to be aimed and needs no long cable. A single LED works too, but
must point at the unit, and reaches about 3 m.

![the IR LED driver](irLedCircuit.svg)

```
  +5V  o----+---------------------+
            |                     |
           ---                   ---
           \ /    IR940  >>      \ /    green >
           ---                   ---
            |                     |
           ---                   [#]    4.7k
           \ /    IR940           |
           ---                    |
            |                     |
           ---                    |
           \ /    IR940           |
           ---                    |
            |                     |
           [#]    2 ohm           |
            |                     |
            +---------------+-----+
                            |
                            |  collector
                           |/
GPIO18 o--+--[####]--------|   NPN
          |  560           |\
         [#]                v  emitter
          |  15k            |
  GND  o--+-----------------+
```

- gpio → **560 Ω** → NPN base, **15 kΩ** from the gpio line to ground
- collector → **2 Ω** → 3 × IR940 → +5 V
- a **green LED + 4.7 kΩ** across that same branch, so you can see it sending
- the pull-down matters: a Pi pin is an *input* until a program drives it, and an open base lets
  the transistor conduct on noise

The base resistor sets the working point, not the ballast. 560 Ω from a 3.3 V pin gives ~4.6 mA of
base current, and at the hFE a small NPN has left at this current (~25) that is the ~120 mA
measured through the IR string. The transistor is running in its active region rather than
saturated, which is what makes the current predictable from the base side.

The 2 Ω looks pointless next to three LEDs and is not. At 120 mA the IR forward voltage has risen
to about 1.35 V each, leaving roughly **0.7 V** of headroom on a 5 V rail — so the 240 mV the
resistor takes is a third of what is left. Against an LED's steep I-V curve that is real negative
feedback: it costs nothing at the working point and quietly limits what a hotter day or a
higher-gain transistor could otherwise pull.

The green LED is worth the two parts. It draws about 0.6 mA and turns "is the pin doing anything
at all" into a glance — the eye cannot see 38 kHz inside a burst, but it sees a ~300 ms
transmission perfectly well.

The 38 kHz carrier is generated by pigpio's DMA waveforms, so its timing is unaffected by CPU load.

### Recording a remote

**Menu → "Record an IR remote (TSOP receiver).."** reads a real remote through a 38 kHz IR receiver
(TSOP38238, CHQ1838 or similar) on any free GPIO, and prints to the Indigo log: the header and bit
timings, the frames, the bytes in both bit orders, and — when it recognises the protocol — a plain
reading of what the remote asked for. It records a **sequence** of presses and diffs them, so
"which bits carry the temperature" is answered by pressing up/down/up/down.

That is how the Gree support here was built: every field was measured off a real remote rather than
taken from a datasheet, and `greeIR.py`'s self-test rebuilds two dozen recorded states byte for
byte. Wiring is OUT → gpio, GND, and VS through **100 Ω** with **4.7 µF** to ground — a receiver
without that filter reads supply ripple as signal.

A receiver is blind to one thing, and it is worth knowing before spending an evening on it: it
**demodulates the carrier away** and reports only the envelope. So a recording, a loopback and a
pulse-by-pulse comparison against the remote can all agree perfectly while the frequency inside
the marks is wrong. It was not the problem on either unit here — both answer across 26–40 kHz —
so there is no carrier setting in the dialog, but if a future one ignores a frame that reads
correctly, `pi/irScan.py` walks 25–48 kHz in 1 kHz steps sending a real command at each.

### What each protocol carries

Both send the **complete state** — there is no "just change the fan".

Indigo's thermostat and an AC do not line up exactly, and two mappings are worth knowing. The
**fan** in Indigo is only *auto* or *always on*, so the device carries a setting for what
"always on" means (Gree default speed 3); the plugin's own action and menu reach every speed.
And Indigo's **auto** mode normally switches between heating and cooling by comparing the room to
`heatSetpoint` and `coolSetpoint` — it cannot do that here, because an IR device is
blind and nothing reports back. The AC's own auto does the same job with its own sensor, so the
two are sent as their **midpoint** and the unit decides.

- **Toshiba**: 9 or 10 byte message, unit code a/b, five fan speeds, modes auto/cool/dry/heat, and
  *off is a mode*. Setpoint 17–30 °C.
- **Gree**: 8 byte state sent as two blocks, modes auto/cool/dry/fan/heat, a real **power bit**
  (so "off" leaves the mode alone), both louvers with all their positions, sleep, health/ioniser,
  display light, turbo and xfan. Setpoint 16–30 °C — and in **dry mode the temperature field is
  the humidity setting instead**.

  The fan is **five speeds** — silent, 1, 2, 3, 4 — plus auto, using the remote's own labels. The
  fan field in the frame is only **two bits and saturates at 3**, so the real position rides in a
  later message of the sequence; that is why speeds above 3 are reachable at all. The remote's
  **full** is not a fan position: it is the turbo bit, so asking for "full" sends the top speed
  with turbo set.

  One press is **four messages**, ~40 ms apart, and the unit acts on nothing less. Repeating a
  single frame does not work — not four times over, and not at any carrier from 26 to 40 kHz.
  They are told apart by byte 3's high nibble, which is a *message index*: **5** carries the full
  state, **6** and **7** carry the command bytes only, and **A** carries no command at all and
  ends the transmission. Only message 5 carries the louvers, even when the louvers are what
  changed. `buildSequence()` generates all four from the state, and the self-test rebuilds a full
  ten-press cycle recorded from the remote — every frame of every step — on every run.

  Worth knowing if you ever meet a similar unit: the frames were byte-perfect against the remote
  from early on, and a receiver read our transmissions back cleanly. None of that says anything
  about whether the AC will obey, because a receiver cannot see the carrier and a frame that is
  correct in isolation can still be an incomplete *conversation*.

### Controls

- **Menu → "Send an IR-AC command.."** — pick a device and send a complete state. The mode, fan and
  temperature lists follow that device's brand, so a Gree device is never offered a Toshiba speed.
- **Actions**: set fan speed, set mode, set louvers, set sleep/health/light — for everything
  Indigo's own thermostat control has no name for. Each stores the choice on the device and resends
  the whole state.
- **TEST LED** in the device dialog blinks the LED for a second at a time so you can see it in a
  phone camera; **TEST VARIANTS** walks the Toshiba protocol variants, switching the AC on at a
  different temperature for each, so the unit itself tells you which one it answers.

### Adding a brand

Two halves, and only one can be done at the desk.

The **encoder** comes from recordings alone: press the remote through a TSOP, diff the presses to
see which bits carry what, and let the checksum tell you a frame is a frame. `greeIR` was built
that way and its output was provably identical to the remote's before the unit ever obeyed one.

Whether a correct frame is **sufficient** cannot be learned that way. This Gree wants the whole
four-message press and ignores a single frame however often it is repeated — nothing in a capture
of one press hints at that. Nor can a capture tell you the carrier, which the receiver strips
before you see it. And a field can lie: byte 0's fan saturates at 3, so ordinary captures suggest
three speeds when the remote has five.

So expect an evening of recordings for the encoder, then a session at the unit itself.

### The beep is the oracle

A Gree unit **beeps on every frame it accepts**, and that is worth more than the display, because
it separates the two failures that look identical from across the room:

- **beep, nothing changes** — the frame was received and applied. Whatever field you moved is not
  the one the unit reads for that setting. This is how the fan turned out to live in a later
  message rather than in byte 0.
- **no beep** — not received at all: the carrier, the aim, or a malformed frame.

Without it, "no reaction" covers both, and the two want opposite investigations.

### When an AC ignores everything

On the Pi, `irTest.sh` is the whole toolbox, and the order below is the order that isolates
fastest — each step removes one explanation:

```
irTest.sh a              record a real remote press, save the pulse list
irTest.sh b              replay it at every carrier, 8 s apart
irTest.sh m <hz> <n>     replay only the first n messages of that press
irTest.sh r <hz> <n>     replay the whole press n times at one carrier
irTest.sh c <hz> <n>     send the ENCODER's frames, 21/25 °C alternating
irTest.sh s              scan 25–48 kHz in 1 kHz steps
```

Put the unit in the *opposite* state with its own remote before replaying, so a success is
visible and cannot be confused with the AC still obeying the button press it just heard. And
never conclude anything from a single success: a marginal link produces one, and two of the
false leads in this protocol's history came from exactly that.

## Outputs

- **GPIO**: on/off pin, dimmer (PWM)
- **Relays**: i2c relay boards, switchbot bot (press/pulse), switchbot curtain (incl. v3s)
- **Analog / DAC**: MCP4725 (12-bit), PCF8591 (8-bit)
- **Displays**: LCD/OLED/e-ink displays (`display.py`, incl. extra pages sent from Indigo),
  xWindows output, distance display
- **LEDs**: NeoPixel strips/matrices, NeoPixel dimmer, NeoPixel clock, sundial clock
- **Motion**: stepper motors
- **Air conditioners**: IR remote control of Toshiba and Gree units — see above
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
- **IR air conditioners**: set fan speed, set mode, set louvers, set sleep / health / light
- **Device utilities**: set/get any device property, set any device state

A parallel set of interactive **menu items** covers setup (create/config/replace Pis, fix IP or
duplicate Pi numbers), beacon management (accept/ignore, replace, battery, beep, fast
beacon→switchbot actions), diagnostics (track MACs, special logging, print configs,
**qualify the BLE dongles of a Pi**), output testing, and the two IR items above —
**send an IR-AC command** and **record an IR remote**.

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
  - `toshibaIR.py` / `greeIR.py` — the AC remote encoders, one per protocol. Each runs its own
    self-test when executed directly, rebuilding states recorded from a real remote
  - `irRecord.py` — reads a remote through a TSOP receiver and decodes it; can echo what it
    recorded straight back out on the LED
  - `irReplay.py` — sends a recorded pulse list, one message per waveform, keeping the gaps
  - `irScan.py` — walks the carrier frequency, sending a real command at each step
  - `irTest.sh` — the record / replay / scan steps as single commands
  - `irRecord.py` — records and decodes a real IR remote; `irReplay.py` sends a recorded pulse
    list back out unchanged
  - `qualifyDongle.py`, `extScanTest.py`, `ruuviPrint.py` — standalone diagnostic tools that can
    also be run by hand on a Pi
- `Contents/changelist.txt` — version history
- `Contents/beaconTypes.txt` — beacon hardware comparison
- `Contents/BLE-sensorTypes.txt` — BLE sensor hardware details
