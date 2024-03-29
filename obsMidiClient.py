# https://spotlightkid.github.io/python-rtmidi/rtmidi.html
import rtmidi
from rtmidi.midiutil import open_midiinput
from rtmidi.midiconstants import NOTE_ON, CONTROL_CHANGE

# https://obsproject.com/docs/reference-frontend-api.html
import obspython as obs


# defines script description 
def script_description():
    return '''Select preview scenes and trigger transition with a midi controller. '''

# defines user properties
def script_properties():
    props = obs.obs_properties_create()

    Midi.addConfig(props)
    TransitionHandler.addConfig(props)
    RecordingHandler.addConfig(props)

    return props

# def script_defaults(settings):

# def script_load(settings):

def script_update(settings):
    Midi.initializeFromSettings(settings)

def script_unload():
    Midi.shutdown()


class Midi(object):
    _instance = None

    class Keys(object):
        port = "midiDevice"

    @classmethod
    def addConfig(cls, props):
        devicesList = obs.obs_properties_add_list(props, cls.Keys.port, "MIDI Device", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)

        availablePorts = rtmidi.MidiIn().get_ports()
        obs.obs_property_list_add_string(devicesList, "None", "")
        for port in availablePorts:
            obs.obs_property_list_add_string(devicesList, port, port)

    @classmethod
    def initializeFromSettings(cls, settings):
        cls.shutdown()

        # Port names contain the port number by default, but this changes based on insertion
        # order. So we'll try to find the closest match by removing the last character (the number)
        availablePorts = rtmidi.MidiIn().get_ports()
        port = obs.obs_data_get_string(settings, cls.Keys.port)
        if port not in availablePorts:
            print("port " + port + " not found")
            possibleMatches = list(filter(lambda prt: prt[:-1] == port[:-1], availablePorts))
            if len(possibleMatches) == 1:
                port = possibleMatches[0]
                obs.obs_data_set_string(settings, cls.Keys.port, port)
                print("using port " + port + " instead")

        cls._instance = Midi(
            port=port,
            handlers = [
                TransitionHandler.fromSettings(settings),
                RecordingHandler.fromSettings(settings)
            ]
        )

    @classmethod
    def shutdown(cls):
        if not cls._instance:
            return
        if cls._instance.midiin:
            cls._instance.midiin.close_port();
        cls._instance = None

    def __init__(self, port, handlers):
        self.midiin = None
        self.currentMidiPort = ""
        self.handlers = handlers
        self.openPort(port)

    def openPort(self, askedPort):
        if self.currentMidiPort == askedPort:
            return

        if self.midiin:
            self.midiin.close_port();
            self.currentMidiPort = ""

        if askedPort == "":
            return

        try:
            self.midiin, port_name = open_midiinput(askedPort, use_virtual=True)
            self.midiin.set_callback(self.onMidi)
            print("connected to " + port_name)
            self.currentMidiPort = askedPort
        except (EOFError, KeyboardInterrupt):
            print("Failed to open port")

    def testInput(self, cmdType, channel, value):
        print(cmdType+"\t"+str(channel)+"\t"+str(value))
        for handler in self.handlers:
            handler.handleMidi(cmdType, channel, value)

    def onMidi(self, event, data=None):
        message, deltatime = event

        # Strip off the channel
        message_type = message[0] & 0xf0

        if message_type == NOTE_ON:
            self.testInput("Note", message[1], message[2])
        elif message_type == CONTROL_CHANGE:
            self.testInput("CC", message[1], message[2])


class RecordingHandler(object):
    class Keys(object):
        cmdType = "recordingMidiType"
        endChannel = "endRecordingMidiChannel"
        startChannel = "startRecordingMidiChannel"
        pauseChannel = "pauseRecordingMidiChannel"
        unpauseChannel = "unpauseRecordingMidiChannel"

    @classmethod
    def addConfig(cls, props):
        addMidiTypeProp(props, cls.Keys.cmdType, "Recording midi type")
        addNoteProp(props, cls.Keys.startChannel, "Start Recording Midi Note/Address")
        addNoteProp(props, cls.Keys.endChannel, "End Recording Midi Note/Address")
        addNoteProp(props, cls.Keys.pauseChannel, "Pause Recording Midi Note/Address")
        addNoteProp(props, cls.Keys.unpauseChannel, "Unpause Recording Midi Note/Address")

    @classmethod
    def fromSettings(cls, settings):
        return RecordingHandler(
            cmdType=obs.obs_data_get_string(settings, cls.Keys.cmdType),
            startChannel=obs.obs_data_get_int(settings, cls.Keys.startChannel),
            endChannel=obs.obs_data_get_int(settings, cls.Keys.endChannel),
            pauseChannel=obs.obs_data_get_int(settings, cls.Keys.pauseChannel),
            unpauseChannel=obs.obs_data_get_int(settings, cls.Keys.unpauseChannel)
        )

    def __init__(self, cmdType, startChannel, endChannel, pauseChannel, unpauseChannel):
        self.cmdType = cmdType
        self.startChannel = startChannel
        self.endChannel = endChannel
        self.pauseChannel = pauseChannel
        self.unpauseChannel = unpauseChannel

    def handleMidi(self, cmdType, channel, value):
        if self.cmdType != cmdType:
            return

        if channel == self.startChannel:
            print("Start Recording")
            #obs.obs_frontend_recording_active
            #obs.obs_frontend_streaming_active
            #obs.obs_frontend_streaming_start
            obs.obs_frontend_recording_start()
        elif channel == self.endChannel:
            print("Stop Recording")
            #obs.obs_frontend_streaming_stop
            obs.obs_frontend_recording_stop()
        elif channel == self.pauseChannel:
            if obs.obs_frontend_recording_paused():
                print("Already paused")
            else:
                print("Pause Recording")
                obs.obs_frontend_recording_pause(True)
        elif channel == self.unpauseChannel:
            if obs.obs_frontend_recording_paused():
                print("Unpause Recording")
                obs.obs_frontend_recording_pause(False)
            else:
                print("Not paused")


class TransitionHandler(object):
    class Keys(object):
        cmdType = "transitionToSceneMidiType"
        transitionFirst = "transitionToSceneMidiAddress"
        duration = "transitionTime"

    @classmethod
    def addConfig(cls, props):
        addMidiTypeProp(props, cls.Keys.cmdType, "Transition to Scene midi type")
        addNoteProp(props, cls.Keys.transitionFirst, "First Transition to Scene Midi Note/Address")
        transition_prop = obs.obs_properties_add_int(props, cls.Keys.duration, "Base transition time (MS) -- multiplied by Midi Value/100", 0, 5000, 1)
        obs.obs_property_set_long_description(transition_prop, """This value will be multiplied by the MIDI value/100.
e.g. if the MIDI note comes with a value/velocity of 100, then the base transition time will be used.
If the note comes with a value/velocity of 50, then then the transition will take half the base transition time.
If the note comes with a value/velocity of 0, then then there will be no transition time.""")

    @classmethod
    def fromSettings(cls, settings):
        return TransitionHandler(
            cmdType=obs.obs_data_get_string(settings, cls.Keys.cmdType),
            transitionFirst=obs.obs_data_get_int(settings, cls.Keys.transitionFirst),
            duration=obs.obs_data_get_int(settings, cls.Keys.duration)
        )

    def __init__(self, cmdType, transitionFirst, duration):
        self.cmdType = cmdType
        self.transitionFirst = transitionFirst
        self.duration = duration

    def handleMidi(self, cmdType, channel, value):
        if cmdType != self.cmdType:
            return

        sceneNumber = channel - self.transitionFirst
        if sceneNumber >= 0:
            self.transition(sceneNumber, value)

    def transition(self, num, value):
        trans = obs.obs_frontend_get_current_transition()

        scenes = obs.obs_frontend_get_scenes()
        if num > len(scenes):
            print(f"Invalid scene number: {num}")
            return

        print(f"start transition to scene #{num}")
        duration = int(self.duration * (value / 100))
        obs.obs_transition_start(trans, obs.OBS_TRANSITION_MODE_AUTO, duration, scenes[num])
        # obs_frontend_set_current_preview_scene
        # obs_frontend_get_current_preview_scene


def addMidiTypeProp(props, key, description):
    listProp = obs.obs_properties_add_list(props, key, description, obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_property_list_add_string(listProp, "Control Change", "CC")
    obs.obs_property_list_add_string(listProp, "Note On", "Note")


def addNoteProp(props, key, description):
    obs.obs_properties_add_int(props, key, description, 0, 127, 1)
