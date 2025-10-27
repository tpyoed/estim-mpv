#!/usr/bin/python3

from mpv import ShutdownError
from PIL import Image, ImageDraw, ImageFont
from time import sleep, time_ns
import argparse
import json
import os
from os.path import exists
import io
import sys
from datetime import datetime

import mpv
import requests

TIMEOUT = 10 * 1000 # 10 seconds

parser = argparse.ArgumentParser(description='Handy MPV sync Utility')
parser.add_argument('file', metavar='file', type=str,
                   help='The file to play')
parser.add_argument("--double", action="store_true", help='enable 2x speed conversion')

def find_script(video_path):
    video_name = video_path.replace('.' + str.split(video_path, '.')[-1:][0], '')
    script_path = f'{video_name}.funscript'
    if (os.path.exists(script_path)):
        print(f'script found for video: {video_name}')
    return script_path

def script_2x(script_file):
    with open(script_file) as f:
        script = json.loads(f.read())

    edited = []
    for action in script['actions']:
        action['pos'] = 0
        edited.append(action)

    final = []
    for x in range(len(edited)):
        if edited[x]['pos'] == 95:
            edited[x]['pos'] = 100
        final.append(edited[x])

        if x == len(edited) - 1:
            break

        new_pos = {}
        new_pos['at'] = int((edited[x + 1]['at'] + edited[x]['at']) / 2)
        new_pos['pos'] = 100
        final.append(new_pos)

    script['actions'] = final
    return (script_file, json.dumps(script))

args = parser.parse_args()
print(args)
script = find_script(args.file)

saved_time = get_saved_time()

if  time_ns() - saved_time['last_saved'] < 3600000000000:
    time_sync_average_offset = saved_time['time_sync_average_offset']
    time_sync_initial_offset = saved_time['time_sync_initial_offset']
else :
    update_server_time()
    save_server_time()

player = mpv.MPV(input_default_bindings=True, input_vo_keyboard=True, osc=True)
player.play(args.file)
# font = ImageFont.truetype('DejaVuSans.ttf', 40)


# overlay = player.create_image_overlay()
# img = Image.new('RGBA', (400, 150),  (255, 255, 255, 0))
# d = ImageDraw.Draw(img)

sync = 0

# @player.on_key_press('up')
def my_up_binding(key_state, key_name, key_char):
    value = player._get_property('playback-time')
    time_ms = int(value * 1000)
    print(time_ms)
    # sync_play(time_ms, 'false')

# @player.on_key_press('q')
def my_q_binding(key_state, key_name, key_char):
    global player
    # sync_play(0, 'false')
    player.command("quit")
    del player
    os._exit(-1)

# @player.on_key_press('down')
def my_down_binding(key_state, key_name, key_char):
    value = player._get_property('playback-time')
    time_ms = int(value * 1000)
    print(time_ms)
    # sync_play(time_ms, 'true')


player.register_key_binding("up", my_up_binding)
player.register_key_binding("q", my_q_binding)
player.register_key_binding("down", my_down_binding)

# @player.event_callback('playback-restart')
def file_restart(event):
    value = player._get_property('playback-time')
    time_ms = int(value * 1000)
    print(time_ms)
    # sync_play(time_ms)
    print(f'Now playing at {time_ms}s')

# @player.event_callback('shutdown')
def callback_shutdown(event):
    # sync_play(0, 'false')
    player.command("quit")
    sys.exit()

#@player.event_callback('pause')
def video_pause(event):
    # sync_play(0, 'false')
    print('pause')

def video_pause_unpause(property_name, new_value):
    paused = new_value
    if paused:
        # sync_play(0, 'false')
        print('pause')
    else:
        value = player._get_property('playback-time')
        if value is not None:
            time_ms = int(value * 1000)
            print(f'Unpause: t={time_ms}')

player.observe_property('pause', video_pause_unpause)

#@player.event_callback('unpause')
def video_unpause(event):
    value = player._get_property('playback-time')
    time_ms = int(value * 1000)
    print('unpause')

def on_event(event):
    e = event.as_dict(decoder=mpv.lazy_decoder)["event"]
    match e:
        case "playback-restart":
            file_restart(event)
        case "shutdown":
            callback_shutdown(event)
        # case "pause":
        #     video_pause(event)
        # case "unpause":
        #     video_unpause(event)

player.register_event_callback(on_event)

@player.property_observer('time-pos')
def time_observer(_name, value):
    # Here, _value is either None if nothing is playing or a float containing
    # fractional seconds since the beginning of the file.
    print('Now playing at {:.2f}s'.format(value))


try:
    player.wait_for_playback()
except ShutdownError as e:
    # sync_play(0, 'false')
    del player
    exit()
