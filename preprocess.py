#!/usr/local/bin/python3

'''
preprocess: Ensures that metadata are readable, deletes undesired noisy metadata, and creates easily-streamable downmixed AAC alternative audio tracks
'''

import os
import sys
import shutil
import subprocess
from clean_metadata import *
from add_aac_to_file import filters
from add_aac_to_file import convert_to_stereo
from add_aac_to_file import run_mkvinfo
from add_aac_to_file import convert as normal_convert
from add_aac_workaround import convert as workaround_convert
from check_valid_default import *
from fix_subs_audio import *
from fix_subs_audio import inspect_mkv as subfix

# The output paths
goal_path = "/Users/Carlitos/Movies/premiumize_downloads/out/originale_out"
goal_4k = "/Users/Carlitos/Movies/premiumize_downloads/out/4K_out" # I am not sure anymore if I ended up using this

def check_metadata(mkvinfo, file):
	'''
	Usually, in MKV files, metadata come first in the bytestream and are thus readable by libraries like mkvinfo.
 	In rare cases, there are other things at the beginning of the bytestream, rendering the metadata unreadable.
  	mkvinfo was at the time of writing not great at noticing incomplete metadata, so this function checks for us.
 	'''
	print("Checking metadata...")
	lines = iter(mkvinfo.split('\n'))
	found = False
	while found == False:
		try:
			current = next(lines)
		except:
			print("Metadata are illegible in", file)
			return False
		if "Track number: " in current:
			print("Metadata legible.")
			print("Cleaning Metadata...")
			clean_metadata(file)
			print("Done cleaning metadata.")
			return True

def preprocess(file, goal_path, root="/Users/Carlitos/Movies/premiumize_downloads/out/originale_in"):
	if check_metadata(run_mkvinfo(file), file):
		print("Fixing the subtitles:")
		subfix(file, root)
		print("Normal audio conversion:")
		conv = normal_convert(file, sys.stdout) # this launches a conversion process and is 0 when successful
		if conv != 0 and conv != 'leave as is': # when not successful, a different workaround script often did the trick -- though I forgot what the workaround does differently
			print("Workaraound was necessary:")
			conv = workaround_convert(file, sys.stdout)
			if conv != 0:
				print("Both conversion attempts failed.") # never had this happen, thankfully
				raise Exception
		# Some files already satisfy my goal profile because they only contain Stereo audio tracks, for example
		elif conv == 'leave as is':
			new_name = file
		elif conv == 0:
			new_name = file[:-4] + "-new.mkv"
		print("Done, moving new file to the goal path, deleting the old.")
		audio_check(new_name) # this function is in check_valid_default.py
		filename = file.split('/')[-1]
		shutil.move(new_name, os.path.join(goal_path, filename))
		if os.path.isfile(file):
			os.remove(file)

def main():
	global goal_path
	if len(sys.argv) == 1: # defaults to this path if no other is defined in the calling of the script
		arg = "/Users/Carlitos/Movies/premiumize_downloads/out/originale_in"
	else:
		arg = sys.argv[1]
	if os.path.isdir(arg):
		for root, dirs, files in os.walk(arg):
			for file in files:
				if "4K" in root: # probably not necessary
					goal_path = goal_4k
				if not os.path.isdir(goal_path): # create path if it doesn't exist yet
					subprocess.call(['mkdir', '-p', goal_path])
				goal_file = os.path.join(goal_path, file)
				file = os.path.join(root, file)
				if not os.path.isfile(goal_file) and file.endswith(".mkv") and not file.endswith("-new.mkv") and not file.endswith("-temp.mkv"): # don't accidentally process files that were created by my own script
					print("\n\n\nStarting", file)
					preprocess(file, goal_path, root)
				else:
					print("Skipping", file)
			
	elif os.path.isfile(arg):
		preprocess(arg, goal_path)

if __name__ == "__main__":
	# I used some file for most of the logs in case the output was unexpected. The script runs fine nowadays so I haven't used this in a long while. You may skip this.
	sys.stdout=open("/Users/Carlitos/Library/CloudStorage/Dropbox/05 – Technisches/Data Storage/software_filmsammlung/log_preprocess_hotfolder.txt", "a")
	main()
