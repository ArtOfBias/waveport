import mutagen
from mutagen import id3, flac, mp4, wave, oggopus, oggvorbis

import os
import pickle
import subprocess
import shutil
import re
from typing import List, Dict

UNICODE_LIMIT = 319
FILENAME_ILLEGAL_SYMBOLS = r"""[<>:"/\\\|\?\*]"""

# TODO add comments
# TODO better variable names


def main():
    overwrite : bool = False

    playlist_folder : str = input("playlists path:\n    ")
    main_playlist_file_name : str = input("main playlist filename:\n    ")
    output_dest : str = input("output destination:\n    ")

    try:
        old_filename_dict : Dict[str, str] = load_data("data.pickle")
    except FileNotFoundError:
        old_filename_dict = {}

    add_filename_dict : Dict[str, str] = convert_tracks(playlist_folder + "\\" + main_playlist_file_name, output_dest, overwrite_files=overwrite, existing_files=old_filename_dict)

    filename_dict = old_filename_dict | add_filename_dict

    create_new_playlists(playlist_folder, output_dest, filename_dict)

    dump_data(filename_dict, "data.pickle")


# TODO use a separate file for creating playlists


def str_to_cmd_args(args : str) -> List[str]:
    """returns list of arguments found in the args string

    Args:
        args (str): string of command

    Returns:
        List[str]: list of arguments parsed from args
    """

    out : List[str] = []

    args = args.strip()

    last_space : int = -1
    last_quote : int = 0
    in_quote : bool = False

    for i in range(len(args)):
        if not in_quote:
            if args[i] == " " and i != last_space:
                out.append(args[last_space + 1 : i])
                last_space = i
            elif args[i] == "\"":
                last_quote = i
                in_quote = True

        else:
            if args[i] == "\"":
                out.append(args[last_quote + 1 : i])
                last_space = i + 1
                in_quote = False

    if last_space != len(args):
        out.append(args[last_space + 1 :])

    return out


def convert_tracks(
    playlist_filename : str,
    output_folder : str,
    library_folder : str = "library\\",
    new_folder : bool = True,
    overwrite_files : bool = False,
    existing_files : Dict[str, str] = {},
    use_existing_files : bool = True
) -> Dict[str, str]:
    """converts tracks in a playlist to mp3 and sends them to a set destination folder, keeps old tracks

    Args:
        playlist_filename (str):absolute path to playlist file
        output_folder (str): destination folder for library
        library_folder (str, optional): library folder where converted tracks will be stored. Defaults to "library".
        new_folder (bool, optional): determines if a library folder is used or not. Defaults to True.
        overwrite (bool, optional): -y or -n argument for ffmpeg. Defaults to False.
        existing_files (Dict[str, str], optional): uses known existing files to skip conversions
        use_existing_files : (bool, optional): whether to use or overwrite existing files

    Returns:
        Dict[str, str]: dict mapping old filenames to new ones
    """

    if overwrite_files:
        overwrite_str = "-y"
    else:
        overwrite_str = "-n"

    if new_folder:
        true_output_folder = output_folder + "\\" + library_folder
        if library_folder[-1] not in "\\/":  # append backslash if not found
            library_folder = library_folder + "\\"
    else:
        library_folder = ""

    if not os.path.isdir(true_output_folder):
        os.mkdir(true_output_folder)

    filename_dict : Dict[str, str] = {}

    old_track_paths : List[str] = []

    with open(playlist_filename, 'r', encoding="utf-8-sig") as playlist_filename:
        old_track_paths = [line.strip() for line in playlist_filename.readlines()[1:]]

    user_rename : List[str] = []

    for track_path_old in old_track_paths:
        if (track_path_old in existing_files.keys() and use_existing_files):
            print("already exists, skipping file operations")
        else:
            if ".mp3" in track_path_old:
                # gets metadata from file
                audio_old = id3.ID3(track_path_old)
                artist = audio_old.get("TPE2")[0]
                album = audio_old.get("TALB")[0]
                title = audio_old.get("TIT2")[0]

                track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{artist} - {album} - {title}.mp3")

                flag : bool = True
                for char in track_file_new[max(track_file_new.rfind("/"), track_file_new.rfind("\\")) + 1:]:
                    if ord(char) > UNICODE_LIMIT:
                        flag = False
                        break

                if flag:
                    track_path_new : str = true_output_folder + "\\" + track_file_new
                    shutil.copy(track_path_old, track_path_new)
                    filename_dict[track_path_old] = library_folder + track_file_new  # note this is an relative path
                    audio_new = id3.ID3(track_path_new)

                    audio_new.add(id3.TPE1(encoding=3, text=artist))

                    audio_new.save()

                else:
                    user_rename.append(track_path_old)

            elif ".flac" in track_path_old:
                audio_old = flac.FLAC(track_path_old)
                artist = audio_old["albumartist"][0]
                album = audio_old["album"][0]
                title = audio_old["title"][0]

                track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{artist} - {album} - {title}.mp3")

                flag : bool = True
                for char in track_file_new[max(track_file_new.rfind("/"), track_file_new.rfind("\\")) + 1:]:
                    if ord(char) > UNICODE_LIMIT:
                        flag = False
                        break

                if flag:
                    track_path_new : str = true_output_folder + "\\" + track_file_new
                    args = str_to_cmd_args(f"ffmpeg {overwrite_str} -i \"{track_path_old}\" -q 0 \"{track_path_new}\"")
                    subprocess.run(args)
                    filename_dict[track_path_old] = library_folder + track_file_new
                    audio_new = id3.ID3(track_path_new)

                    track = audio_new.get("TRCK")
                    disc = audio_new.get("TPOS")
                    totaltracks = audio_new.get("TXXX:TRACKTOTAL")
                    totaldiscs = audio_new.get("TXXX:DISCTOTAL")
                    audio_new.add(id3.TRCK(encoding=0, text=f"{track}/{totaltracks}"))
                    audio_new.add(id3.TPOS(encoding=0, text=f"{disc}/{totaldiscs}"))
                    audio_new.delall("TXXX:TRACKTOTAL")
                    audio_new.delall("TXXX:DISCTOTAL")

                    audio_new.add(id3.TPE1(encoding=3, text=artist))

                    audio_new.save()

                else:
                    user_rename.append(track_path_old)

            elif ".m4a" in track_path_old:
                audio_old = mp4.MP4(track_path_old)
                artist = audio_old["aART"][0]
                album = audio_old["\xa9alb"][0]
                title = audio_old["\xa9nam"][0]

                track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{artist} - {album} - {title}.mp3")

                flag : bool = True
                for char in track_file_new[max(track_file_new.rfind("/"), track_file_new.rfind("\\")) + 1:]:
                    if ord(char) > UNICODE_LIMIT:
                        flag = False
                        break

                if flag:
                    track_path_new : str = true_output_folder + "\\" + track_file_new
                    subprocess.run(str_to_cmd_args(f"ffmpeg {overwrite_str} -i \"{track_path_old}\" -q 0 \"{track_path_new}\""))
                    filename_dict[track_path_old] = library_folder + track_file_new
                    audio_new = id3.ID3(track_path_new)

                    audio_new.add(id3.TPE1(encoding=3, text=artist))

                    audio_new.save()

                else:
                    user_rename.append(track_path_old)

            elif ".wav" in track_path_old:
                audio_old = wave.WAVE(track_path_old)
                artist = audio_old.get("TPE2")[0]
                album = audio_old.get("TALB")[0]
                title = audio_old.get("TIT2")[0]
                track = audio_old.get("TRCK")[0].split("/")[0]
                disc = audio_old.get("TPOS")[0].split("/")[0]
                totaltracks = audio_old.get("TRCK")[0].split("/")[1]
                totaldiscs = audio_old.get("TPOS")[0].split("/")[1]

                track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{artist} - {album} - {title}.mp3")

                flag : bool = True
                for char in track_file_new[max(track_file_new.rfind("/"), track_file_new.rfind("\\")) + 1:]:
                    if ord(char) > UNICODE_LIMIT:
                        flag = False
                        break

                if flag:
                    track_path_new : str = true_output_folder + "\\" + track_file_new
                    subprocess.run(str_to_cmd_args(f"ffmpeg {overwrite_str} -i \"{track_path_old}\" -q 0 \"{track_path_new}\""))
                    filename_dict[track_path_old] = library_folder + track_file_new
                    audio_new = id3.ID3(track_path_new)

                    audio_new.add(id3.TRCK(encoding=0, text=f"{track}/{totaltracks}"))
                    audio_new.add(id3.TPOS(encoding=0, text=f"{disc}/{totaldiscs}"))

                    audio_new.add(id3.TPE1(encoding=3, text=artist))

                    audio_new.save()

                else:
                    user_rename.append(track_path_old)

            elif ".opus" in track_path_old:
                audio_old = oggopus.OggOpus(track_path_old)
                artist = audio_old["albumartist"][0]
                album = audio_old["album"][0]
                title = audio_old["title"][0]
                track = audio_old["tracknumber"][0]
                disc = audio_old["discnumber"][0]
                totaltracks = audio_old["tracktotal"][0]
                totaldiscs = audio_old["disctotal"][0]

                track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{artist} - {album} - {title}.mp3")

                flag : bool = True
                for char in track_file_new[max(track_file_new.rfind("/"), track_file_new.rfind("\\")) + 1:]:
                    if ord(char) > UNICODE_LIMIT:
                        flag = False
                        break

                if flag:
                    track_path_new : str = true_output_folder + "\\" + track_file_new
                    subprocess.run(str_to_cmd_args(f"ffmpeg {overwrite_str} -i \"{track_path_old}\" -q 0 -map_metadata 0:s:a:0 \"{track_path_new}\""))
                    filename_dict[track_path_old] = library_folder + track_file_new
                    audio_new = id3.ID3(track_path_new)

                    audio_new.add(id3.TRCK(encoding=0, text=f"{track}/{totaltracks}"))
                    audio_new.add(id3.TPOS(encoding=0, text=f"{disc}/{totaldiscs}"))

                    audio_new.add(id3.TPE1(encoding=3, text=artist))

                    audio_new.save()

                else:
                    user_rename.append(track_path_old)

            elif ".ogg" in track_path_old:
                audio_old = oggvorbis.OggVorbis(track_path_old)
                artist = audio_old["albumartist"][0]
                album = audio_old["album"][0]
                title = audio_old["title"][0]
                track = audio_old["tracknumber"][0]
                disc = audio_old["discnumber"][0]
                totaltracks = audio_old["tracktotal"][0]
                totaldiscs = audio_old["disctotal"][0]

                track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{artist} - {album} - {title}.mp3")

                flag : bool = True
                for char in track_file_new[max(track_file_new.rfind("/"), track_file_new.rfind("\\")) + 1:]:
                    if ord(char) > UNICODE_LIMIT:
                        flag = False
                        break

                if flag:
                    track_path_new : str = true_output_folder + "\\" + track_file_new
                    subprocess.run(str_to_cmd_args(f"ffmpeg {overwrite_str} -i \"{track_path_old}\" -q 0 -map_metadata 0:s:a:0 \"{track_path_new}\""))
                    filename_dict[track_path_old] = library_folder + track_file_new
                    audio_new = id3.ID3(track_path_new)

                    audio_new.add(id3.TRCK(encoding=0, text=f"{track}/{totaltracks}"))
                    audio_new.add(id3.TPOS(encoding=0, text=f"{disc}/{totaldiscs}"))

                    audio_new.add(id3.TPE1(encoding=3, text=artist))

                    audio_new.save()

                else:
                    user_rename.append(track_path_old)

    for track_path_old in user_rename:
        if ".mp3" in track_path_old:
            audio_old = id3.ID3(track_path_old)
            artist = audio_old.get("TPE2")[0]
            album = audio_old.get("TALB")[0]
            title = audio_old.get("TIT2")[0]

            print(f"{artist} - {album} - {title}")

            fn_artist = input("artist: ")
            fn_album = input("album: ")
            fn_title = input("title: ")

            track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{fn_artist} - {fn_album} - {fn_title}.mp3")

            track_path_new : str = true_output_folder + "\\" + track_file_new
            shutil.copy(track_path_old, track_path_new)
            filename_dict[track_path_old] = library_folder + track_file_new
            audio_new = id3.ID3(track_path_new)

            audio_new.add(id3.TPE1(encoding=3, text=artist))

            audio_new.save()

        elif ".flac" in track_path_old:
            audio_old = flac.FLAC(track_path_old)
            artist = audio_old["albumartist"][0]
            album = audio_old["album"][0]
            title = audio_old["title"][0]

            print(f"{artist} - {album} - {title}")

            fn_artist = input("artist: ")
            fn_album = input("album: ")
            fn_title = input("title: ")

            track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{fn_artist} - {fn_album} - {fn_title}.mp3")

            track_path_new : str = true_output_folder + "\\" + track_file_new
            args = str_to_cmd_args(f"ffmpeg {overwrite_str} -i \"{track_path_old}\" -q 0 \"{track_path_new}\"")
            subprocess.run(args)
            filename_dict[track_path_old] = library_folder + track_file_new
            audio_new = id3.ID3(track_path_new)

            track = audio_new.get("TRCK")
            disc = audio_new.get("TPOS")
            totaltracks = audio_new.get("TXXX:TRACKTOTAL")
            totaldiscs = audio_new.get("TXXX:DISCTOTAL")
            audio_new.add(id3.TRCK(encoding=0, text=f"{track}/{totaltracks}"))
            audio_new.add(id3.TPOS(encoding=0, text=f"{disc}/{totaldiscs}"))
            audio_new.delall("TXXX:TRACKTOTAL")
            audio_new.delall("TXXX:DISCTOTAL")

            audio_new.add(id3.TPE1(encoding=3, text=artist))

            audio_new.save()

        elif ".m4a" in track_path_old:
            audio_old = mp4.MP4(track_path_old)
            artist = audio_old["aART"][0]
            album = audio_old["\xa9alb"][0]
            title = audio_old["\xa9nam"][0]

            print(f"{artist} - {album} - {title}")

            fn_artist = input("artist: ")
            fn_album = input("album: ")
            fn_title = input("title: ")

            track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{fn_artist} - {fn_album} - {fn_title}.mp3")

            track_path_new : str = true_output_folder + "\\" + track_file_new
            subprocess.run(str_to_cmd_args(f"ffmpeg {overwrite_str} -i \"{track_path_old}\" -q 0 \"{track_path_new}\""))
            filename_dict[track_path_old] = library_folder + track_file_new
            audio_new = id3.ID3(track_path_new)

            audio_new.add(id3.TPE1(encoding=3, text=artist))

            audio_new.save()

        elif ".wav" in track_path_old:
            audio_old = wave.WAVE(track_path_old)
            artist = audio_old.get("TPE2")[0]
            album = audio_old.get("TALB")[0]
            title = audio_old.get("TIT2")[0]
            track = audio_old.get("TRCK")[0].split("/")[0]
            disc = audio_old.get("TPOS")[0].split("/")[0]
            totaltracks = audio_old.get("TRCK")[0].split("/")[1]
            totaldiscs = audio_old.get("TPOS")[0].split("/")[1]

            print(f"{artist} - {album} - {title}")

            fn_artist = input("artist: ")
            fn_album = input("album: ")
            fn_title = input("title: ")

            track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{fn_artist} - {fn_album} - {fn_title}.mp3")

            track_path_new : str = true_output_folder + "\\" + track_file_new
            subprocess.run(str_to_cmd_args(f"ffmpeg {overwrite_str} -i \"{track_path_old}\" -q 0 \"{track_path_new}\""))
            filename_dict[track_path_old] = library_folder + track_file_new
            audio_new = id3.ID3(track_path_new)

            audio_new.add(id3.TRCK(encoding=0, text=f"{track}/{totaltracks}"))
            audio_new.add(id3.TPOS(encoding=0, text=f"{disc}/{totaldiscs}"))

            audio_new.add(id3.TPE1(encoding=3, text=artist))

            audio_new.save()

        elif ".opus" in track_path_old:
            audio_old = mutagen.oggopus.OggOpus(track_path_old)
            artist = audio_old["albumartist"][0]
            album = audio_old["album"][0]
            title = audio_old["title"][0]
            track = audio_old["tracknumber"][0]
            disc = audio_old["discnumber"][0]
            totaltracks = audio_old["tracktotal"][0]
            totaldiscs = audio_old["disctotal"][0]

            print(f"{artist} - {album} - {title}")

            fn_artist = input("artist: ")
            fn_album = input("album: ")
            fn_title = input("title: ")

            track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{fn_artist} - {fn_album} - {fn_title}.mp3")

            track_path_new : str = true_output_folder + "\\" + track_file_new
            subprocess.run(str_to_cmd_args(f"ffmpeg {overwrite_str} -i \"{track_path_old}\" -q 0 -map_metadata 0:s:a:0 \"{track_path_new}\""))
            filename_dict[track_path_old] = library_folder + track_file_new
            audio_new = id3.ID3(track_path_new)

            audio_new.add(id3.TRCK(encoding=0, text=f"{track}/{totaltracks}"))
            audio_new.add(id3.TPOS(encoding=0, text=f"{disc}/{totaldiscs}"))

            audio_new.add(id3.TPE1(encoding=3, text=artist))

            audio_new.save()

        elif ".ogg" in track_path_old:
            audio_old = oggvorbis.OggVorbis(track_path_old)
            artist = audio_old["albumartist"][0]
            album = audio_old["album"][0]
            title = audio_old["title"][0]
            track = audio_old["tracknumber"][0]
            disc = audio_old["discnumber"][0]
            totaltracks = audio_old["tracktotal"][0]
            totaldiscs = audio_old["disctotal"][0]

            print(f"{artist} - {album} - {title}")

            fn_artist = input("artist: ")
            fn_album = input("album: ")
            fn_title = input("title: ")

            track_file_new : str = re.sub(FILENAME_ILLEGAL_SYMBOLS, "-", f"{fn_artist} - {fn_album} - {fn_title}.mp3")

            track_path_new : str = true_output_folder + "\\" + track_file_new
            subprocess.run(str_to_cmd_args(f"ffmpeg {overwrite_str} -i \"{track_path_old}\" -q 0 -map_metadata 0:s:a:0 \"{track_path_new}\""))
            filename_dict[track_path_old] = library_folder + track_file_new
            audio_new = id3.ID3(track_path_new)

            audio_new.add(id3.TRCK(encoding=0, text=f"{track}/{totaltracks}"))
            audio_new.add(id3.TPOS(encoding=0, text=f"{disc}/{totaldiscs}"))

            audio_new.add(id3.TPE1(encoding=3, text=artist))

            audio_new.save()

    return filename_dict


def create_new_playlists(playlist_folder : str, output_folder : str, filename_dict : Dict[str, str]) -> None:
    """creats new .m3u8 playlists from a folder of old ones by replacing filenames, keeps old playlists

    Args:
        playlist_folder (str): folder containing old playlists
        output_folder (str): destination folder for new playlists
        filename_dict (Dict[str, str]): dictionary mapping of old track filenames to new ones
    """

    playlists : List[str] = [f for f in os.listdir(playlist_folder) if ".m3u8" in f]

    for playlist in playlists:
        with open(playlist_folder + "\\" + playlist, "r", encoding="utf-8-sig") as f:
            content = f.read()

            for key in filename_dict:
                content = content.replace(key, filename_dict[key])
                content = content.replace("#\n", "")

            new_playlist_path = output_folder + "\\" + playlist

            new_playlist = open(new_playlist_path, "w", encoding="utf-8-sig")
            new_playlist.write(content)
            new_playlist.close()


def dump_data(filename_data : Dict[str, str], pickle_filename : str, data_location : str = ".\\data\\") -> None:
    try:
        with open(data_location + pickle_filename, "wb") as f:
            pickle.dump(filename_data, f)
    except FileNotFoundError:
        os.mkdir(data_location)
        f = open(data_location + pickle_filename, "x")
        with open(data_location + pickle_filename, "wb") as f:
            pickle.dump(filename_data, f)


def load_data(pickle_filename : str, data_location : str = ".\\data\\") -> Dict[str, str]:
    try:
        with open(data_location + pickle_filename, "rb") as f:
            data_dict : Dict[str, str] = pickle.load(f)
            for key in data_dict.keys():
                assert type(key) == str
                assert type(data_dict[key]) == str
    except FileNotFoundError:
        data_dict = {}

    return data_dict


if __name__ == "__main__":
    main()
