# Alsaloop

This package is responsible for detecting audio input in the HifiBerryOS system.

## Requirements
The `pyalsaaudio` package is used to read from and write to audio devices. This package does not work on Windows.

## How it works

1. The input device is opened. It is read continuously.
2. When a certain number of samples have been read, the audio volume is calculated
3. If the audio was not playing, but one of the samples exceed the threshold volume, audio will start playing
4. If the audio was playing, but none of the samples exceed the threshold volume, audio will stop playing



