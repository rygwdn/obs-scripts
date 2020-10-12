import obspython as obs
import datetime

def script_description():
    return '''Countdown to a specified time.'''

class Settings:
    countdown_time = None
    source_name = ""
    stop_text = ""

def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_int(props, "hour", "Hour (0-24)", 0, 24, 1)
    obs.obs_properties_add_int(props, "minute", "Minute (0-59)", 0, 59, 1)
    obs.obs_properties_add_int(props, "second", "Second (0-59)", 0, 59, 1)

    p = obs.obs_properties_add_list(props, "source_name", "Text source", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    sources = obs.obs_enum_sources()
    for source in sources:
        source_id = obs.obs_source_get_id(source)
        if source_id == "text_gdiplus" or source_id == "text_ft2_source" or source_id == "text_gdiplus_v2" or source_id == "text_ft2_source_v2":
            name = obs.obs_source_get_name(source)
            obs.obs_property_list_add_string(p, name, name)
    obs.source_list_release(sources)

    obs.obs_properties_add_text(props, "stop_text", "Countdown final text", obs.OBS_TEXT_DEFAULT)

    return props

def script_defaults(settings):
    obs.obs_data_set_default_int(settings, "hour", 11)
    obs.obs_data_set_default_int(settings, "minute", 0)
    obs.obs_data_set_default_int(settings, "second", 0)
    obs.obs_data_set_default_string(settings, "source_name", "")
    obs.obs_data_set_default_string(settings, "stop_text", "Starting soon")

def script_load(settings):
    pass

def script_update(settings):
    Settings.countdown_time = datetime.time(
        obs.obs_data_get_int(settings, "hour"),
        obs.obs_data_get_int(settings, "minute"),
        obs.obs_data_get_int(settings, "second")
    )

    Settings.source_name = obs.obs_data_get_string(settings, "source_name")
    Settings.stop_text = obs.obs_data_get_string(settings, "stop_text")

    start_timer()

def script_unload():
    obs.timer_remove(timer_callback)

def start_timer():
    obs.timer_remove(timer_callback)
    obs.timer_add(timer_callback, 500)

def format_time():
    now = datetime.datetime.now()
    end_date = datetime.datetime.combine(now.date(), Settings.countdown_time)

    if now > end_date:
        return Settings.stop_text

    difference_seconds = (end_date - now).total_seconds()
    difference_time = datetime.time(
        int(difference_seconds // (60 * 60)),
        int((difference_seconds // 60) % 60),
        int(difference_seconds % 60)
    )

    if difference_time.hour > 0:
        return difference_time.strftime(r"%H:%M:%S")
    return difference_time.strftime(r"%M:%S")

def timer_callback():
    if not Settings.source_name or not Settings.countdown_time:
        return

    text = format_time()

    source = obs.obs_get_source_by_name(Settings.source_name)
    if source:
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", text)
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source)
