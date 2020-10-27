#!/usr/bin/env python
'''
Copyright (c) 2020 Modul 9/HiFiBerry

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

# !/usr/bin/env python

import sys
import logging
from math import sqrt, log
from struct import unpack_from
import os

import alsaaudio

output_stopped = True
threshold = 20

SAMPLE_MAXVAL = 32768


def open_sound(output=False):
    input_device = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK, device=device)
    input_device.setchannels(2)
    input_device.setrate(48000)
    input_device.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    input_device.setperiodsize(1024)

    if output:
        output_device = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, alsaaudio.PCM_NONBLOCK, device=device)
        output_device.setchannels(2)
        output_device.setrate(48000)
        output_device.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        return input_device, output_device

    else:
        return input_device


def decibel(value):
    return 20 * log(value / SAMPLE_MAXVAL, 10)


def stop_playback(_signalNumber, _frame):
    global output_stopped
    logging.info("received USR1, stopping music playback")
    output_stopped = True


if __name__ == '__main__':

    start_db_threshold = 0
    stop_db_threshold = 0
    try:
        start_db_threshold = float(sys.argv[1])
        if start_db_threshold > 0:
            start_db_threshold = -start_db_threshold

        # Define the stop threshold. This prevents hysteresis when the volume fluctuates just around the threshold.
        # 90% of the input threshold means the audio volume has to drop 10% after starting to play before playback
        # will be stopped.
        stop_db_threshold = start_db_threshold * .90

        print("using alsaloop with input level detection {:.1f} to start, {:.1f} to stop"
              .format(start_db_threshold, stop_db_threshold))
    except:
        print("using alsaloop without input level detection")

    device = 'default'
    input_device = open_sound(output=False)
    output_device = None
    finished = False

    # This is the number of samples we want before checking if audio should be turned on or off.
    target_sample_count = 11050

    samples = 0
    sample_sum = 0
    max_sample = 0
    status = "-"
    rms_volume = 0
    input_detected = False

    while not finished:
        # Read data from device
        data_length, data = input_device.read()

        if data_length < 0:
            # Something's wrong when this happens. Just try to read again.
            logging.error("?")
            continue

        if (len(data) % 4) != 0:
            # Additional sanity test: If the length isn't a multiple of 4, something's wrong
            print("oops %s".format(len(data)))
            continue

        offset = 0
        # Read through the currently captured audio data
        while offset < data_length:
            try:
                # Read the left and right channel from the data packet
                (sample_l, sample_r) = unpack_from('<hh', data, offset=offset)
            except:
                # logging.error("%s %s %s",l,len(data), offset)
                # Set a default value of zero so the program can keep running
                (sample_l, sample_r) = (0, 0)

            offset += 4
            samples += 2
            # Calculate the sum of all samples squared, used to determine rms later.
            sample_sum += sample_l * sample_l + sample_r * sample_r
            # Determine the max value of all samples
            max_sample = max(max_sample, abs(sample_l), abs(sample_r))

        if samples >= target_sample_count:
            # Calculate RMS
            rms_volume = sqrt(sample_sum / samples)

            # Determine which threshold value to use
            if output_stopped:
                threshold = start_db_threshold
            else:
                threshold = stop_db_threshold

            # Check if the threshold has been exceeded
            if start_db_threshold == 0 or decibel(max_sample) > threshold:
                input_detected = True
                status = "P"
            else:
                input_detected = False
                status = "-"

            print("{} {:.1f} {:.1f}".format(status, decibel(rms_volume), decibel(max_sample)), flush=True)

            sample_sum = 0
            samples = 0
            max_sample = 0

            if output_stopped and input_detected:
                del input_device
                logging.info("Input signal detected, pausing other players")
                os.system("/opt/hifiberry/bin/pause-all alsaloop")
                (input_device, output_device) = open_sound(output=True)
                output_stopped = False
                continue

            elif not output_stopped and not input_detected:
                del input_device
                output_device = None
                logging.info("Input signal lost, stopping playback")
                input_device = open_sound(output=False)
                output_stopped = True
                continue

        if not output_stopped:
            output_device.write(data)
