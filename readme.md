# waveport

creates copies of audio files compressed to mp3, converts playlists as well

i made this for personal usage, works well to sync music using Syncthing

- supports `mp3`, `flac`, `m4a`, `wav`, `opus`, and `ogg`
- **only supports `.m3u8` playlist files**
- overwrites `artist` metadata tag with `albumartist` tag

## usage

python (>=3.5) and the [mutagen](https://mutagen.readthedocs.io) library are required.

[//]: # (might be a higher version of python but type hints are 3.5, i run 3.10.8)

waveport asks you for three inputs:

### playlists path

the absolute path to a single folder where `.m3u8` playlist files are stored, playlists in subfolders are not implemented

example: `c:\users\username\music\playlists` **note there isnt a slash**

### main playlist filename

a `.m3u8` file containing **all** files

example: `main.m3u8`

### output destination

the absolute path to a destination folder for the converted audio files and playlists

a `library` subfolder will be created to hold all the converted audio files, this can be changed or disabled in the source code

converted playlists will be placed in the root of the destination directory

example: `c:\users\username\phone\music`
