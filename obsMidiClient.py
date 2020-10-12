# MIDI !
import rtmidi
from rtmidi.midiutil import open_midiinput

import obspython as obs

def testInput(cmdType, channel, value):
    global midiParams
    
    if transitionControlType == cmdType and channel >= transitionFirst:
        print("do transition")
        transition(channel - transitionFirst)
    if logMidiInput:
        print(cmdType+"\t"+str(channel)+"\t"+str(value))
    

def noteOn(channel, velocity):
    testInput("Note", channel, velocity)

def controlChange(channel, value):
    testInput("CC", channel, value)

currentMidiPort = "";
midiin = None
logMidiInput = False
transitionControlType = ""
transitionFirst = 0
transitionTime = 0

class MidiInputHandler(object):
    def __init__(self, port):
        self.port = port

    def __call__(self, event, data=None):
        message, deltatime = event
        if message[0] == 144 :
            noteOn(message[1], message[2])
        elif message[0] == 176 :
            controlChange(message[1], message[2])


# defines script description 
def script_description():
    return '''Select preview scenes and trigger transition with a midi controller. '''

# defines user properties
def script_properties():
    props = obs.obs_properties_create()
    devicesList = obs.obs_properties_add_list(props, "midiDevice", "MIDI Device", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    midiIn = rtmidi.MidiIn()
    availablePorts = midiIn.get_ports()
    obs.obs_property_list_add_string(devicesList, "", "")
    for port in availablePorts:
        obs.obs_property_list_add_string(devicesList, port, port)
    
    transitionsMidiType = obs.obs_properties_add_list(props, "transitionToSceneMidiType", "Transition to Scene midi type", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(transitionsMidiType, "Control Change", "CC")
    obs.obs_property_list_add_string(transitionsMidiType, "Note On", "Note")

    obs.obs_properties_add_int(props, "transitionToSceneMidiAddress", "First Transition to Scene Midi Address", 0, 127, 1)
    obs.obs_properties_add_int(props, "transitionTime", "Transition time (MS)", 0, 5000, 1)
    
    obs.obs_properties_add_bool(props, "logMidiInput", "Log MIDI input")
    
    return props

# def script_defaults(settings):

# def script_load(settings):

def script_update(settings):
    global currentMidiPort
    global midiin
    global logMidiInput
    global transitionControlType
    global transitionFirst
    global transitionTime

    askedPort = obs.obs_data_get_string(settings, "midiDevice")
    if currentMidiPort != askedPort:
        if currentMidiPort != "":
            midiin.close_port();
            currentMidiPort = ""
        ok = True
        if askedPort != "":
            try:
                midiin, port_name = open_midiinput(askedPort, use_virtual=True)
                midiin.set_callback(MidiInputHandler(port_name))
                print("connected to " + port_name)
            except (EOFError, KeyboardInterrupt):
                print("Meh :/")
                ok = False
            if ok:
                currentMidiPort = askedPort

    transitionControlType = obs.obs_data_get_string(settings, "transitionToSceneMidiType")
    transitionFirst = obs.obs_data_get_int(settings, "transitionToSceneMidiAddress")
    logMidiInput = obs.obs_data_get_bool(settings, "logMidiInput")
    transitionTime = obs.obs_data_get_int(settings, "transitionTime")
    

def script_unload():
    global currentMidiPort
    global midiin
    if currentMidiPort != "":
        midiin.close_port();

def transition(num):
    trans = obs.obs_frontend_get_current_transition()

    duration = transitionTime #obs.obs_frontend_get_transition_duration()
    scenes = obs.obs_frontend_get_scenes()
    if num > len(scenes):
        print(f"Invalid scene number: {num}")
        return
    print(f"want to transition to: {num}")
    dest = scenes[num]
    
    obs.obs_transition_start(trans, obs.OBS_TRANSITION_MODE_AUTO, duration, dest)
