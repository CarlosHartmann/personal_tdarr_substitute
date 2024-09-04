s'''
check_valid_default: Checks MKVs to ensure the presence of only one default track and that it is not commentary and that all audio tracks meet my requirements.
Some audio codecs were incompatible with my setup. They have to be removed.
Note that at this point all audio tracks have been copied&converted to AAC, so removing an audio track does not lose anything.
'''

import os
import sys
import shutil
import pprint
import subprocess
from pymediainfo import MediaInfo as MI


def get_codec(track):
	return track.codec_id

# Depends on your setup. At the time of writing this code, the 'forbidden' codecs cause issues on Plex.
valid_codecs =		['A_AAC-2', 'A_AAC-5', 'A_AC3', 'A_DTS', 'A_EAC3', 'A_FLAC', 'A_MPEG/L2', 'A_MPEG/L3', 'A_TRUEHD']
forbidden_codecs =	['A_PCM/INT/LIT', 'A_VORBIS', 'mp4a-40-2']
default_codecs =	['A_AAC-2', 'A_AC3', 'A_EAC3', 'A_MPEG/L3']

def mux_out_unwanted(file, unwanted_tracks):
	comm = ['/usr/local/bin/ffmpeg', '-y', '-i']
	comm = comm + ['file:'+file]
	comm = comm + ['-map', '0:0', '-c:0', 'copy']
	comm = comm + ['-map', '0:a']
	for elem in unwanted_tracks:
		comm = comm + ['-map', '-0:'+str(elem)]
	comm = comm + ['-c:a', 'copy']
	comm = comm + ['-map', '0:s?', '-c:s', 'copy', '-map_metadata', '0']
	comm = comm + ['file:'+file[:-4]+'-temp.mkv']
	#print(' '.join(comm))
	proc = subprocess.call(comm, stdout=subprocess.PIPE, stderr=sys.stdout)
	if proc != 0:
		print('Error in processing', file)
		exit()
	else:
		shutil.move(file[:-4]+'-temp.mkv', file)
	
def get_a_tracks(file):
	try:
		a_tracks = MI.parse(file).audio_tracks	
	except:
		print("Metadata illegible in", file)
		raise Exception
	if a_tracks == None:
		print("No audio tracks detected in", file)
		return None
	else:
		return a_tracks

def reduce_to_one_default(file, defaults):
	to_be_fixed = defaults[1:]
	c = 1
	comm = ['/usr/local/bin/mkvpropedit', file]
	for track in to_be_fixed:
		c += 1
		comm += ['--edit', 'track:a'+str(c), '--set', 'flag-default=0']
	proc = subprocess.call(comm, stdout=subprocess.PIPE, stderr=sys.stdout)
	if proc != 0:
		print('Error in processing', file)
		exit()

def audio_check(file):
	global forbidden_codecs
	audio_tracks = get_a_tracks(file)
	unwanted_tracks = list()
	if audio_tracks == []:
		raise Exception
	
	codecs = [get_codec(elem) for elem in audio_tracks]
	for codec, track in zip(codecs, audio_tracks):
		if codec in forbidden_codecs:
			unwanted_tracks.append(track.track_id-1)
	if len(unwanted_tracks) > 0:
		mux_out_unwanted(file, unwanted_tracks)
		
	defaults = [elem for elem in audio_tracks if elem.default == "Yes"]
	non_defaults = [elem for elem in audio_tracks if elem.default == "No"]
	
	if len(defaults) + len(non_defaults) != len(audio_tracks):
		print("Something is wrong with the default flags in", file)
		raise Exception
	
	if len(defaults) == 0:
		print("No default audio tracks found in", file)
		raise Exception
	elif len(defaults) > 1:
		print("More than one default track found in", file, "fixing...")
		reduce_to_one_default(file, defaults)
	# this is basically else: just one default
	default = defaults[0]
	if default.title is not None:
		if "commentary" in default.title.lower():
			print("Default track is a commentary track in", file)
			raise Exception
	codec = get_codec(default)
	if codec not in default_codecs:
		print("Default track not ideal codec in", file)
		raise Exception

def main():
	arg = sys.argv[1]
	if os.path.isdir(arg):
		for root, dirs, files in os.walk(arg):
			for file in files:
				filepath = os.path.join(root, file)
				if not file.startswith("-") and file.endswith(".mkv"):
					audio_check(filepath)
	elif os.path.isfile(arg):
		audio_check(arg)


if __name__ == "__main__":
	main()
