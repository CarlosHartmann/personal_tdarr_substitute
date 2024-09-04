#!/usr/local/bin/python3

'''
preprocess: Für neue MKVs für Filmsammlung; stellt sicher, dass Metadaten lesbar sind löscht unerwünschten Filmtitel, erstellt plexfreundliche Tonspuren.
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

goal_path = "/Users/Carlitos/Movies/premiumize_downloads/out/originale_out"
goal_4k = "/Users/Carlitos/Movies/premiumize_downloads/out/4K_out"

def check_metadata(mkvinfo, file):
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
		conv = normal_convert(file, sys.stdout)
		if conv != 0 and conv != 'leave as is':
			print("Workaraound was necessary:")
			conv = workaround_convert(file, sys.stdout)
			if conv != 0:
				print("Both conversion attempts failed.")
				raise Exception
		elif conv == 'leave as is':
			new_name = file
		elif conv == 0:
			new_name = file[:-4] + "-new.mkv"
		print("Done, moving new file to the goal path, deleting the old.")
		audio_check(new_name)
		filename = file.split('/')[-1]
		shutil.move(new_name, os.path.join(goal_path, filename))
		if os.path.isfile(file):
			os.remove(file)

def main():
	global goal_path
	if len(sys.argv) == 1:
		arg = "/Users/Carlitos/Movies/premiumize_downloads/out/originale_in"
	else:
		arg = sys.argv[1]
	if os.path.isdir(arg):
		for root, dirs, files in os.walk(arg):
			for file in files:
				if "4K" in root:
					goal_path = goal_4k
				if not os.path.isdir(goal_path):
					subprocess.call(['mkdir', '-p', goal_path])
				goal_file = os.path.join(goal_path, file)
				file = os.path.join(root, file)
				if not os.path.isfile(goal_file) and file.endswith(".mkv") and not file.endswith("-new.mkv") and not file.endswith("-temp.mkv"):
					print("\n\n\nStarting", file)
					preprocess(file, goal_path, root)
				else:
					print("Skipping", file)
			
	elif os.path.isfile(arg):
		preprocess(arg, goal_path)

if __name__ == "__main__":
	sys.stdout=open("/Users/Carlitos/Library/CloudStorage/Dropbox/05 – Technisches/Data Storage/software_filmsammlung/log_preprocess_hotfolder.txt", "a")
	main()