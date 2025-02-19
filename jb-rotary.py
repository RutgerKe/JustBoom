#!/usr/bin/python3
# Author: Francesco Vannini
# Company: Pi Supply

import logging
import json
import alsaaudio
import RPi.GPIO as GPIO
from time import sleep
import getopt
import paho.mqtt.client as mqtt
import sys

ROTARY_TYPES = ["standard", "keyes"]

MQTT_HOST = "10.80.30.10"
MQTT_PORT = 1883

MQTT_COMMAND_TOPICS = 'magicmirror/justboom/set/'


class Rotary:
    CLOCKWISE = 0
    ANTICLOCKWISE = 1

    def __init__(self, clockPin, dataPin, buttonPin,
                 rotaryCallback, buttonCallback, rotaryType):
        # persist values
        self.clockPin = clockPin
        self.dataPin = dataPin
        self.buttonPin = buttonPin
        self.rotaryCallback = rotaryCallback
        self.buttonCallback = buttonCallback
        self.rotaryType = rotaryType

        # setup pins
        if self.rotaryType == "standard":
            GPIO.setup(clockPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # All pins are pull up because both
            GPIO.setup(dataPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # the encoder and the button
        elif self.rotaryType == "keyes":
            GPIO.setup(clockPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # All pins are pull up because both
            GPIO.setup(dataPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # the encoder and the button

        GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # will be connected to Ground

    def start(self):
        GPIO.add_event_detect(self.clockPin,
                              GPIO.FALLING,
                              callback=self._clockCallback,
                              bouncetime=50)
        GPIO.add_event_detect(self.buttonPin,
                              GPIO.FALLING,
                              callback=self._switchCallback,
                              bouncetime=300)

    def stop(self):
        GPIO.remove_event_detect(self.clockPin)
        GPIO.remove_event_detect(self.buttonPin)

    def _clockCallback(self, pin):
        if GPIO.input(self.clockPin) == 0:
            data = GPIO.input(self.dataPin)
            if data == 1:
                self.rotaryCallback(self.ANTICLOCKWISE)
            else:
                self.rotaryCallback(self.CLOCKWISE)

    def _switchCallback(self, pin):
        if GPIO.input(self.buttonPin) == 0:
            self.buttonCallback()

class EasyMixer(mqtt.Client):
    def __init__(self, start_vol, vol_inc, clk, dt, btn, rot_type):
        cardId = 0

        self.startvol = start_vol
        self.volinc = vol_inc
        self.hasMute = True # Are we using the Digital control or the SoftMaster
        self.isMute = False
        self.clk = clk # First rotary pin
        self.dt = dt # Second rotary pin
        self.btn = btn # Button pin
        self.rotary = None

        # Is the rotary encoder keyes like i.e. pull down or standard i.e. pull up
        if rot_type in ROTARY_TYPES:
            self.rot_type = rot_type
            print("Configuring rotary encoder as ", self.rot_type)
        else:
            print(rot_type, " is not a valid rotary encoder type")
            exit()

        # Finds the JustBoom card
        for i in range(len(alsaaudio.cards())):
            print(alsaaudio.cards()[i])
            if (alsaaudio.cards()[i]=='sndrpiboomberry' or alsaaudio.cards()[i]=='sndrpijustboomd'):
                cardId=i
                if 'Digital' in alsaaudio.mixers(cardId):
                    self.mixer = alsaaudio.Mixer(control='Digital', cardindex=cardId)
                    self.hasMute = True
                elif 'SoftMaster' in alsaaudio.mixers(cardId):
                    self.mixer = alsaaudio.Mixer(control='SoftMaster', cardindex=cardId)
                    self.hasMute = False
                else:
                    print("There are no suitable mixers")
                    exit()
                self.rotary = Rotary(self.clk, self.dt, self.btn, self.rotarychange, self.buttonpressed, self.rot_type)
        if self.rotary == None:
            print("There are no suitable cards")
            exit()

        # Init the mqtt stuff
        super().__init__()
        self.connect(MQTT_HOST, MQTT_PORT, 60)
        # With the # suffix we subscribe to all subtopics
        self.subscribe(MQTT_COMMAND_TOPICS + "#")


    def getmute(self):
        self.isMute = self.mixer.getmute()[0]
        return self.isMute

    def setmute(self, mute):
        self.mixer.setmute(mute)

    def getvolume(self):
        return self.mixer.getvolume()[0]

    def setvolume(self, volume):
        self.mixer.setvolume(volume)
        self.publish("magicmirror/justboom/state", str(volume))

    def upvolume(self):
        if (self.getvolume() + self.volinc) <= 100:
            self.setvolume(self.getvolume() + self.volinc)

    def downvolume(self):
        if (self.getvolume() - self.volinc) >= 0:
            self.setvolume(self.getvolume() - self.volinc)

    def rotarychange(self, direction):
        if self.hasMute:
            if not self.getmute():  # Is the audio muted?
                if direction:
                    self.upvolume() # Increase the volume
                else:
                    self.downvolume() # Decrease the volume
                print("Volume: " + str(self.getvolume()))
        else:
            if direction:
                self.upvolume() # Increase the volume
            else:
                self.downvolume() # Decrease the volume
            print("Volume: " + str(self.getvolume()))

    def buttonpressed(self):
        self.publish("magicmirror/screen/set", '{"state": "TOGGLE"}')

    def toggle_mute(self):
        # Toggle and the unmute/mute logic could be merged. This function is just what was already available
        if self.hasMute:
            if (self.getmute()):  # Is the audio muted?
                self.setvolume(self.getvolume())  # Applies the last known value of volume (before entering mute)
                self.setmute(0)  # Unmute the sound
                print("Unmuted")
            else:
                self.setmute(1)  # Mute the audio
                print("Muted")
        else:
            self.setvolume(0)   # Since the control hasn't got a mute we simply set the volume to 0
            print("Volume: " + str(self.getvolume()))

    def start(self):
        self.mixer.setvolume(self.startvol) # Set mixer volume to start volume
        self.rotary.start()

    def stop(self):
        self.rotary.stop()

    def on_connect(self, client, userdata, flags, rc):
        logging.info("Connected with result code " + str(rc))

    def on_disconnect(self, client, userdata, rc=0):
        logging.info("Disconnected with result code " + str(rc))
        # Do nothing, just do the default and try to reconnect

    def on_message(self, client, userdata, msg):
        logging.info(msg.topic + " " + str(msg.payload))

        command = msg.topic.split(MQTT_COMMAND_TOPICS)[1]
        if command == "MUTE":
            if msg.payload.decode() == "MUTE":
                if self.hasMute:
                    self.setmute(1)
                else:
                    self.setvolume(0)   # Since the control hasn't got a mute we simply set the volume to 0
            elif msg.payload.decode() == "UNMUTE":
                if self.hasMute:
                    self.setvolume(self.getvolume())  # Applies the last known value of volume (before entering mute)
                    self.setmute(0)  # Unmute the sound
                else:
                    logging.info("Unmuting not supported, just increase the volume")
            elif msg.payload.decode() == "TOGGLE":
                self.toggle_mute()

        elif command == "VOLUME":
            payload = json.loads(msg.payload)
            if payload['COMMAND'] == "SET":
                if payload['VALUE'] <= 100 and payload['VALUE'] >= 0:
                    self.setvolume(payload['VALUE'])
            elif payload['COMMAND'] == "CHANGE":
                if 'VALUE' in payload:
                    if payload['VALUE'] + self.getvolume() <= 100 and payload['VALUE'] + self.getvolume() >= 0:
                        self.setvolume(self.getvolume() + payload['VALUE'])
                elif 'DIRECTION' in payload:
                    if payload['DIRECTION'] == "DOWN":
                        self.downvolume()
                    elif payload['DIRECTION'] == "UP":
                        self.upvolume()


def usage():
    print('Usage: \tjb_rotary [-sirtbv]\n' + \
          '\tjb_rotary {-h|--help}         Script usage information\n' +\
          '\n' +\
          '\t-s --startvol    start volume level\n' +\
          '\t-i --volinc      volume increments/decrements\n' +\
          '\t-r --rotary      rotary encoder pins\n' + \
          '\t-t --type        rotary encoder type ' + str(ROTARY_TYPES) + '\n' + \
          '\t-b --button      button pin')

# main

# Defaults
start_volume = 0 # Starting volume
volume_increments = 1 # Step for volume increments
rotary_pins = [16,18] # Rotary encoder pin
button_pin = 10  # Button pin
rotary_type = "standard"

# Script arguments
try:
    options, remainder  = getopt.getopt(sys.argv[1:], "h:s:i:r:b:t:", ['help', 'startvol=', 'volinc=', 'rotary=', 'button=', 'type='])
except getopt.GetoptError as err:
    print(str(err))
    usage()
    sys.exit(2)

for opt, arg in options:
    if opt in ('-s', '--startvol'):
        start_volume = int(arg)
    elif opt in ('-i', '--volinc'):
        volume_increments = int(arg)
    elif opt in ('-r', '--rotary'):
        rotary_pins = arg.split(',')
    elif opt in ('-b', '--button'):
        button_pin = int(arg)
    elif opt in ('-t', '--type'):
        rotary_type = arg
    elif opt in ('-h', '--help'):
        usage()
        sys.exit()
    else:
        assert False, "unhandled option"

GPIO.setmode(GPIO.BOARD) # Set the GPIO with pin numbering

easy_mixer = EasyMixer(start_volume,volume_increments, int(rotary_pins[0]), int(rotary_pins[1]), button_pin, rotary_type) # New mixer instantiation

easy_mixer.start() # Start mixer and rotary encoder
easy_mixer.loop_start() # Start mqtt non-blocking loop

# Wait for something to happen
try:
    while True:
        sleep(0.1)
finally:
    easy_mixer.stop()
    easy_mixer.loop_stop()
    GPIO.cleanup()
