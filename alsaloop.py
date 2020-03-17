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

#!/usr/bin/env python

import sys
import logging
from math import sqrt, log
from struct import unpack_from
import os

import alsaaudio

stopped = True
threshold = 20

SAMPLE_MAXVAL = 32768


def open_sound(output=False):
    
    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK, device=device)
    inp.setchannels(2)
    inp.setrate(48000)
    inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    inp.setperiodsize(1024)
    
    if output:
        out = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, alsaaudio.PCM_NONBLOCK, device=device)
        out.setchannels(2)
        out.setrate(48000)
        out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        return(inp, out)
    
    else:
        return inp
    
def decibel(value):
    return 20*log(value/SAMPLE_MAXVAL)
        
def stop_playback(_signalNumber, _frame):
    logging.info("received USR1, stopping music playback")
    stopped = True

if __name__ == '__main__':
    
    dbthreshold = 0
    try: 
        dbthreshold = float(sys.argv[1])
        if dbthreshold > 0:
            dbthreshold = -dbthreshold
        print("using alsaloop witht input level detection {:.1f}".format(dbthreshold))
    except:
        print("using alsaloop without input level detection")
        
    device = 'default'
    
    inp = open_sound(output=False)
    
    finished = False
    
    rmssamples = 11050
    samples = 0
    samplesum = 0
    max_sample = 0
    status = "-"
    rms = 0
    playing = False

    while not(finished):
        # Read data from device
        l, data = inp.read()
        if l<0:
            logging.error("?")
            continue
        
        #logging.error("%s %s %s",l,len(data),samples)
        
        if (len(data) % 4) != 0:
                print("oops %s".format(len(data)))
                continue
            
        offset = 0
        while offset < l: 
            try:
                (sample_l,sample_r) = unpack_from('<hh', data, offset=offset)
            except:
                # logging.error("%s %s %s",l,len(data), offset)
                pass
            offset += 4
            samples += 2
            samplesum += sample_l*sample_l + sample_r*sample_r
            max_sample = max(max_sample, abs(sample_l), abs(sample_r))
    
        if samples >= rmssamples:        
            # Calculate RMS
            rms = sqrt(samplesum/samples)
        
            if dbthreshold == 0 or decibel(max_sample) > dbthreshold:
                playing = True
                status="P"
            else:
                playing = False
                status="-"

            print("{} {:.1f} {:.1f}".format(status, decibel(rms), decibel(max_sample)))
                  
            samplesum = 0
            samples = 0
            max_sample = 0 

            
            if stopped==True and playing:

                inp = None
                logging.info("Input signal detected, pausing other players")
                os.system("/opt/hifiberry/bin/pause-all alsaloop")
                (inp, outp) = open_sound(output=True)
                stopped = False
                continue
                
            elif stopped == False and not(playing):
                outp = None
                logging.info("Input signal lost, stopping playback")
                del outp
                del inp
                inp = open_sound(output=False)
                stopped = True
                continue
            
        if not(stopped):
            outp.write(data)