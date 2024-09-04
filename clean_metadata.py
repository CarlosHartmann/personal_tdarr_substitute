'''
clean_metadata: It cleans the MKV metadata to my liking.
Most titles are deleted, but if valuable info is found in them, the info is transferred to its proper place in the MKV metadata.
'''

import os
import sys
import subprocess
from pymediainfo import MediaInfo as MI

def clean_metadata(file):
	inf = MI.parse(file)
	subprocess.call(['/usr/local/bin/mkvpropedit', file, '--delete', 'title'])
	video = inf.video_tracks[0]
	print("Setting video track language to 'undetermined':")
	subprocess.call(['/usr/local/bin/mkvpropedit', file, '--edit', 'track:v1', '--set', 'language=und'])
	
	if video.title is not None:
		if 'intertitles' not in video.title.lower() and 'hard' not in video.title.lower(): # some video tracks can have valuable info in the title, such as "intertitles" for silent films or "hard-coded english subtitles"
			print("Deleting video title.")
			subprocess.call(['/usr/local/bin/mkvpropedit', file, '--edit', 'track:v1', '--delete', 'name'])
		else:
			print("Video track name judged appropriate, leaving it.")
			
	for i in range(len(inf.audio_tracks)):
		track = inf.audio_tracks[i]
		if track.title is not None:
			if 'commentary' not in track.title.lower():
				print(str(i), "Deleting audio track name")
				subprocess.call(['/usr/local/bin/mkvpropedit', file, '--edit', 'track:a'+str(i+1), '--delete', 'name'])
			else:
				print(str(i), "Leaving commentary track name as is, setting commentary flag")
				subprocess.call(['/usr/local/bin/mkvpropedit', file, '--edit', 'track:a'+str(i+1), '--set', 'flag-commentary=1'])
	
	print("Editing subtitle metadata:")
	for i in range(len(inf.text_tracks)):
		track = inf.text_tracks[i]
		if track.title is not None:
			if 'commentary' not in track.title.lower() and 'forced' not in track.title.lower() and 'sdh' not in track.title.lower():
				print(str(i), "Deleteing subtitle track name")
				subprocess.call(['/usr/local/bin/mkvpropedit', file, '--edit', 'track:s'+str(i+1), '--delete', 'name'])
			elif 'commentary' in track.title.lower():
				print(str(i),"Setting commentary flag")
				subprocess.call(['/usr/local/bin/mkvpropedit', file, '--edit', 'track:s'+str(i+1), '--set', 'flag-commentary=1'])
			elif 'sdh' in track.title.lower():
				print(str(i),"Setting HI flag")
				subprocess.call(['/usr/local/bin/mkvpropedit', file, '--edit', 'track:s'+str(i+1), '--set', 'flag-hearing-impaired=1'])
			elif 'forced' in track.title.lower():
				print(str(i),"Setting forced flag")
				subprocess.call(['/usr/local/bin/mkvpropedit', file, '--edit', 'track:s'+str(i+1), '--set', 'flag-forced=1'])

def main():
	if os.path.isdir(sys.argv[1]):
		for file in os.listdir(sys.argv[1]):
			file = os.path.join(sys.argv[1], file)
			if os.path.isfile(file) and file.endswith(".mkv") and not file.endswith("-new.mkv") and not file.endswith("-temp.mkv"):
				clean_metadata(file)
			
	elif os.path.isfile(sys.argv[1]):
		clean_metadata(sys.argv[1])

if __name__ == "__main__":
	main()
