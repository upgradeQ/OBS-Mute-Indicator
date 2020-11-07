#
# Project     OBS Mute Indicator Script
# @author     David Madison
# @link       github.com/dmadison/OBS-Mute-Indicator
# @license    GPLv3 - Copyright (c) 2020 David Madison
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import obspython as obs


# ------------------------------------------------------------

# Script Properties

debug = True  # default to "True" until overwritten by properties
source_name = ""  # source name to monitor, stored from properties


sources_loaded = False  # set to 'True' when sources are presumed loaded
callback_name = None  # source name for the current callback
# ------------------------------------------------------------

# Mute Indicator Functions


def dprint(*input):
    if debug == True:
        print(*input)


def send_to_private_data(data_type, field, result):
    settings = obs.obs_data_create()
    set = getattr(obs, f"obs_data_set_{data_type}")
    set(settings, field, result)
    obs.obs_apply_private_data(settings)
    obs.obs_data_release(settings)


def write_output(muted):
    output = "muted" if muted else "unmuted"
    result = f"{source_name} is " + output
    send_to_private_data("string", "__muted__",result)


def get_muted(sn):
    source = obs.obs_get_source_by_name(sn)

    if source is None:
        return None

    muted = obs.obs_source_muted(source)
    obs.obs_source_release(source)

    return muted


def mute_callback(calldata):
    muted = obs.calldata_bool(calldata, "muted")  # true if muted, false if not
    write_output(muted)


def create_muted_callback(sn):
    global callback_name

    if sn is None or sn == callback_name:
        return False  # source hasn't changed or callback is already set

    if callback_name is not None:
        remove_muted_callback(callback_name)

    source = obs.obs_get_source_by_name(sn)

    if source is None:
        if sources_loaded:  # don't print if sources are still loading
            dprint("ERROR: Could not create callback for", sn)
        return False

    handler = obs.obs_source_get_signal_handler(source)
    obs.signal_handler_connect(handler, "mute", mute_callback)
    callback_name = sn  # save name for future reference
    dprint('Added callback for "{:s}"'.format(obs.obs_source_get_name(source)))

    obs.obs_source_release(source)

    return True


def remove_muted_callback(sn):
    if sn is None:
        return False  # no callback is set

    source = obs.obs_get_source_by_name(sn)

    if source is None:
        dprint("ERROR: Could not remove callback for", sn)
        return False

    handler = obs.obs_source_get_signal_handler(source)
    obs.signal_handler_disconnect(handler, "mute", mute_callback)
    dprint('Removed callback for "{:s}"'.format(obs.obs_source_get_name(source)))

    obs.obs_source_release(source)

    return True


def list_audio_sources():
    audio_sources = []
    sources = obs.obs_enum_sources()

    for source in sources:
        if obs.obs_source_get_type(source) == obs.OBS_SOURCE_TYPE_INPUT:
            # output flag bit field: https://obsproject.com/docs/reference-sources.html?highlight=sources#c.obs_source_info.output_flags
            capabilities = obs.obs_source_get_output_flags(source)

            has_audio = capabilities & obs.OBS_SOURCE_AUDIO
            # has_video = capabilities & obs.OBS_SOURCE_VIDEO
            # composite = capabilities & obs.OBS_SOURCE_COMPOSITE

            if has_audio:
                audio_sources.append(obs.obs_source_get_name(source))

    obs.source_list_release(sources)

    return audio_sources


def source_loading():
    global sources_loaded

    source = obs.obs_get_source_by_name(source_name)

    if source and create_muted_callback(source_name):
        sources_loaded = True  # sources loaded, no need for this anymore
        obs.remove_current_callback()  # delete this timer
    else:
        dprint("Waiting to load sources...")

    obs.obs_source_release(source)


# ------------------------------------------------------------

# OBS Script Functions


def script_description():
    return (
        "<b>OBS Mute Indicator Script</b>"
        + "<hr>"
        + 'Python script for sending the "mute" state of an audio source to a serial device.'
        + "<br/><br/>"
        + "Made by David Madison, © 2020"
        + "<br/><br/>"
        + "partsnotincluded.com"
        + "<br/>"
        + "github.com/dmadison/OBS-Mute-Indicator"
    )


def script_update(settings):
    global debug, source_name

    debug = obs.obs_data_get_bool(settings, "debug")  # for printing debug messages

    source_name = obs.obs_data_get_string(settings, "source")

    if sources_loaded:
        create_muted_callback(source_name)  # create 'muted' callback for source


def script_properties():
    props = obs.obs_properties_create()

    # Create list of audio sources and add them to properties list
    audio_sources = list_audio_sources()

    source_list = obs.obs_properties_add_list(
        props,
        "source",
        "Audio Source",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )

    for name in audio_sources:
        obs.obs_property_list_add_string(source_list, name, name)

    obs.obs_properties_add_bool(props, "debug", "Print Debug Messages")

    return props


def script_load(settings):
    obs.timer_add(
        source_loading, 10
    )  # brute force - try to load sources every 10 ms until the callback is created


def script_unload():
    obs.timer_remove(source_loading)
    remove_muted_callback(callback_name)  # remove the callback if it exists
    dprint("OBS Mute Indicator Script Unloaded. Goodbye! <3")
