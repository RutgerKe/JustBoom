![Alt text](https://user-images.githubusercontent.com/1878314/73881011-7e819e80-4857-11ea-886f-25fa23f721ce.png)
# JustBoom

## Modifications in this repo
As my use case is slightly different, I have a justboom amp hat connected to a Pi which also controls a [Magic Mirror](https://magicmirror.builders/), I changed a bit of the functionality:
- The button turns the screen on/off (via MQTT)
- Changes via the rotary encoder are communicated over MQTT, and the program also listens on MQTT

MQTT commands supported:
- 'Mute', 'Unmute' and 'Toggle mute'
- 'Change volume' and 'Set volume'

This is implemented by making the already existing 'EasyMixer' a subclass of the paho.mqtt.Client. I also edited some files to work with python 3

### Command examples:
The mute topic just takes a word (MUTE, UNMUTE or TOGGLE): `mosquitto_pub -h localhost -t magicmirror/justboom/set/MUTE -m 'TOGGLE'`

The volume topic takes a json object: `mosquitto_pub -h localhost -t magicmirror/justboom/set/VOLUME -m '{"COMMAND": "SET", "VALUE": 55}'`

Negative changes are supported: `mosquitto_pub -h localhost -t magicmirror/justboom/set/VOLUME -m '{"COMMAND": "CHANGE", "VALUE": -5}'`

The default rotary turn increment is used if not specified: `mosquitto_pub -h localhost -t magicmirror/justboom/set/VOLUME -m '{"COMMAND": "CHANGE", "DIRECTION": "DOWN"}'`

## Rotary encoder volume control
jb-rotary enables control of volume level via the rotary encoder and mute/unmute function via its push button.
### Installation
1. Login via SSH or via the console.
2. Update the list of available software packages:
```
sudo apt-get update
```
3. Run the following command and the JustBoom rotary and push button code will be configured and installed:
```bash
curl -sSL https://pisupp.ly/jb-rotarycode | sudo bash
```
### Usage
The default settings for the script are:
* Start Volume = 0
* Volume increment/decrement steps = 1
* Rotary pins = 16,18 (Board notation)
* Button pin = 10 (Board notation)

Script usage:
```
Usage:  jb_rotary [-sirtbv]
        jb_rotary {-h|--help}         Script usage information

        -s --startvol    start volume level
        -i --volinc      volume increments/decrements
        -r --rotary      rotary encoder pins
        -t --type        rotary encoder type ['standard', 'keyes']
        -b --button      button pin
```
Example:

```
sudo python jb-rotary.py -s 20 -i 5       Changes the starting volume and step increments
sudo python jb-rotary.py -r 19,21 -b 15   Remaps the rotary and the button pins
sudo python jb-rotary.py -t keyes         Configure the rotary encoder as Keyes
```
*Note that the default setting for the button requires that you disable the onboard UART. This is mostly required when using the rotary encoder with the JustBoom Amp HAT via the P2 connector. [Check our main site JustBoom.co for the full pinout](https://www.justboom.co/technical-guides/boards-pinout/).*

### Digi boards
Since the Digi boards haven't got a volume control we need to create one for the script to work.
``` bash
sudo nano /etc/asound.conf
```
Add the following contents:
```
pcm.justboom-softvol {
    type softvol
    slave.pcm "plughw:0"
    control.name "SoftMaster"
    control.card 0
}

pcm.!default {
    type             plug
    slave.pcm       "justboom-softvol"
}
```
Run this command which will test and CREATE the mixer control:
``` bash
speaker-test -D justboom-softvol -c 2 -twav -l 1
```
*Note that due to the fact that SoftMaster isn't a real control the mute doesn't behave as for the Amp and DAC cards. In the case of the Digi the volume will be set to zero on mute and will NOT go back to where it was before after pressing the button once again.*

If you are using MPD you should change the configuration to the following one.
``` bash
sudo nano /etc/mpd.conf
```
```
follow_outside_symlinks         "yes"
follow_inside_symlinks          "yes"
music_directory                 "/var/lib/mpd/music"
playlist_directory              "/var/lib/mpd/playlists"
db_file                         "/var/lib/mpd/tag_cache"
log_file                        "/var/log/mpd/mpd.log"
pid_file                        "/run/mpd/pid"
state_file                      "/var/lib/mpd/state"
sticker_file                    "/var/lib/mpd/sticker.sql"

user                            "mpd"

bind_to_address         "localhost"

input {
        plugin "curl"
}

audio_output {
        type            "alsa"
        name            "JustBoom"
        device          "justboom-softvol"
        mixer_type      "software"
        mixer_device    "SoftMaster"
}
```

### Disable the UART on Raspberry Pi Zero, A+, B+ and 2B
on the command line execute these two commands:
``` bash
sudo systemctl stop serial-getty@ttyAMA0.service
sudo systemctl disable serial-getty@ttyAMA0.service
```
reboot the system.

### Disable the UART on Raspberry Pi 3B and Raspberry Pi Zero W
on the command line execute these two commands:
``` bash
sudo systemctl stop serial-getty@ttyS0.service
sudo systemctl disable serial-getty@ttyS0.service
```
and remove the following line from `/boot/cmdline.txt`
```
console=serial0,115200
```
reboot the system

### Wiring for the rotary encoders
#### Standard
Both the rotary pins and the button are configured to pull down. For example in the default configuration the pins will have to be connected as follows:
```
Rotary Left pin   -> pin 16
Rotary Middle pin -> GND (pin 14)
Rotary Right pin  -> pin 18

Button one pin    -> pin 10
Button other pin  -> GND (pin 9)
```
#### Keyes
The rotary pins are configured to pull up and the button is configured to pull down. For example in the default configuration the pins will have to be connected as follows:
```
Rotary CLK        -> pin 16
Rotary DT         -> pin 18
Rotary SW         -> pin 10
Rotary +          -> 3V3 (pin 1)
Rotary GND        -> GND (pin 14)
```
You can find the [assembly steps for the standard rotary encoder](https://www.justboom.co/tutorials/add-rotary-encoder-justboom-boards/) on our website. You can find the [standard rotary encoder](https://www.pi-supply.com/product/rotary-encoder-push-switch/) on our site.

If you are planning on installing the rotary encoder on the [JustBoom DAC HAT, check the FAQ](https://www.justboom.co/faqs/#FAQ-7) on the website for additional details.

## LIRC lircd.conf
This is the configuration file for the JustBoom IR Remote to be used in conjunction with LIRC.
A tutorial that guides you through the whole installation of LIRC and the remote configuration can be found via [this link](https://www.justboom.co/tutorials/configure-justboom-ir-remote-lirc/).

## Smart Remote HEX codes
The smart remote appears to the OS as a normal HID device. If the distribution you are using already makes use of such devices like for the Kodi ones than the remote is entirely plug and play. Should you want to integrate it in your applications or create a plugin for a specific OS these are the hex codes for the various buttons:

```
Function        Code    Keymap
Power           0x30    KEY_POWER
Home            0x223   KEY_HOMEPAGE
Mute            0xE2    KEY_MUTE
Up              0x42    KEY_UP
Left            0x44    KEY_LEFT
OK              0x41    KEY_SELECT
Right           0x45    KEY_RIGHT
Down            0x43    KEY_DOWN
Menu            0x40    KEY_MENU
Back            0x224   KEY_BACK
Vol-            0xEA    KEY_VOLUMEDOWN
Vol+            0xE9    KEY_VOLUMEUP
```
The mouse mode is activated by pressing the button in between `Vol-` and `Vol+`. The pointer is controlled by the built in gyroscope.
In this mode the OK button changes function and becomes a mouse left button.

```
Function        Code    Keymap
OK              0x90001 BTN_LEFT
X               <Range> REL_X
Y               <Range> REL_Y
```
The remote will revert back to keyboard emulation by pressing one of the arrow buttons.

### Kodi - OK and Menu buttons no longer work
There are some issues with the OK and Menu buttons no longer working on Kodi based distros like LibreELEC. This is apparently caused by a [kernel problem](https://forum.libreelec.tv/thread/20122-mce-keyboard-mce-kbd-not-working-for-text-keys-after-upgrading-to-versions-9-1-0/?postID=125984#post125984) and can be fixed with the following workaround based on a [forum post in LibreELEC by HiassofT](https://forum.libreelec.tv/thread/10563-ok-button-doesn-t-work-on-h1-remote/).

#### Automated fix
Run the following script
```bash
curl -sSL https://pisupp.ly/smartremotefix | bash
```
then reboot the system

#### Manual fix
Create the following file
```bash
cat > /storage/.config/hwdb.d/70-local-keyboard.hwdbe << EOF
evdev:input:b0003v2252p0120*
 KEYBOARD_KEY_c0041=enter
 KEYBOARD_KEY_c0040=c
EOF
```
and run this command
```bash
udevadm hwdb --update && udevadm trigger -s input
```
finally reboot the system

## ALSA file for Surround Systems
`JustBoomDigi.conf` enables passthrough DTS for surround systems. The file needs to be saved under `/usr/share/alsa/cards`

## Chips, I2C and Pinout
The pinout for the boards can be found on the [JustBoom website](https://www.justboom.co/technical-guides/boards-pinout/) or on [Pinout.xyz](https://pinout.xyz/boards#manufacturer=JustBoom)

This list shows the various chips used and the I2C address where applicable:
* Amp HAT - [TAS5756M](http://www.ti.com/product/TAS5756M) - 0x4D
* DAC HAT - [PCM5122](http://www.ti.com/product/PCM5122) - 0x4D
* Digi HAT - [WM8804G](http://www.alldatasheet.net/view.jsp?Searchword=WM8804G&sField=2) - 0x3B
* Amp Zero - [TAS5756M](http://www.ti.com/product/TAS5756M) - 0x4D
* DAC Zero - [PCM5121](http://www.ti.com/product/PCM5121) - 0x4D
* Digi Zero - [WM8804G](http://www.alldatasheet.net/view.jsp?Searchword=WM8804G&sField=2) - 0x3B
* Amp - [TPA3118D2](http://www.ti.com/product/TPA3118D2)
* DAC - [PCM5102A](http://www.ti.com/product/PCM5102A)
