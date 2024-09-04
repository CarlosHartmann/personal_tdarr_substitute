'''
fix_subs: Geht rekursiv durch eine Directory, um bei allen MKV-Dateien die integrierten SRTs zu UTF-8-SIG zu machen. Ausserdem diverse UT-Reparaturen, die automatisierbar sind.
	+ AAC-Versionen für Surround und non-AAC/AC3-Spuren
'''

import os
import re
import sys
import pprint
import subprocess
import pymediainfo
from add_aac_to_file import *

url_regex = "(http)?s?(://)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"

pp = pp = pprint.PrettyPrinter(indent=4).pprint

done_files_path = "/Users/Carlitos/Library/CloudStorage/Dropbox/05 – Technisches/Data Storage/fix_subs_done-files.txt"
with open(done_files_path) as infile:
	done_files = infile.read().split('\n')
	
finished_dirs = ['Carnival']

def remux(file, sub_ids):
	mkvmerge_command = ["/usr/local/bin/mkvmerge", "-o", file[:-4]+'-temp.mkv', '--no-subtitles', file]
	mkvpropedit_command = ["/usr/local/bin/mkvpropedit", file[:-4]+'-temp.mkv']
	counter = 0
	for elem in sub_ids:
		counter += 1
		elem_id = elem[0]
		lang = elem[1]
		if lang == None:
			lang = 'und'
		srt_filename = file[:-4]+'-'+str(elem_id)+'.srt'
		mkvmerge_command.append("--language")
		mkvmerge_command.append('0:'+lang)
		mkvmerge_command.append(srt_filename)
		
		title = elem[2]
		flags = elem[3]
		if title  != None:
			mkvpropedit_command.append('--edit')
			mkvpropedit_command.append('track:s'+str(counter))
			mkvpropedit_command.append('--set')
			mkvpropedit_command.append("name="+title)
		for key, value in list(flags.items()):
			mkvpropedit_command.append('--edit')
			mkvpropedit_command.append('track:s'+str(counter))
			mkvpropedit_command.append('--set')
			mkvpropedit_command.append(key+"="+value)
	subprocess.call(mkvmerge_command, stdout=subprocess.PIPE)
	subprocess.call(mkvpropedit_command, stdout=subprocess.PIPE)

def remove_formatting(text):
	text = re.sub('<[^>]+>', '', text)
	text = re.sub('\{[^}]+\}', '', text)
	return text

def remove_false_positives(url_list):
	return [elem for elem in url_list if elem != "L.A." and not re.search("\.{3}\w", elem)]

def test_sub_content(file):
	result = False
	with open(file) as infile:
		content = infile.read()
	
	if len(re.findall('\n<', content)) > 1: # formatting
		print("Found formatting.")
		content = remove_formatting(content)
		result = True
	possible_urls = re.findall(url_regex, content)
	remove_false_positives(possible_urls)
	if len(possible_urls) > 0:
		print("Possible URLs detected:")
		for elem in possible_urls:
			print(elem)
		result = True
	if re.search('@', content):
		print("@ detected in", file)
	if re.search("sub[sz] by", content):
		print("Possible author note detected in", file)
	if re.search(" \.", content):
		print("Fullstop with leading space found in", file)
	with open(file, "w", encoding="utf-8") as outfile:
		outfile.write(content)
	return result

def fix_charset(subfile, charset):
	try:
		with open(subfile, encoding=charset) as infile:
			content = infile.read()
	except:
		print("The chardetect-output for", subfile, "was not correct. Used utf-8 instead, check manually for problems.")
		with open(subfile, encoding="utf-8") as infile:
			content = infile.read()
	content = remove_formatting(content)
	with open(subfile, "w", encoding="utf-8") as outfile:
		outfile.write(content)

def cleanup(file, sub_ids, updated):
	if updated:
		subprocess.call(["rm", file])
		subprocess.call(["mv", file[:-4]+'-temp.mkv', file])
	for elem in sub_ids:
		subprocess.call(["rm", file[:-4]+'-'+str(elem[0])+'.srt'])

def fix_subs(file, sub_ids):
	update_needed = False
	for elem in sub_ids:
		sub_filename = file[:-4]+'-'+str(elem[0])+'.srt'
		proc = subprocess.Popen(["/usr/local/bin/chardetect", sub_filename], stdout=subprocess.PIPE)
		output = proc.stdout.read().decode()
		charset = re.search("(\S+) with confidence", output).group(1)
		confidence = re.search("with confidence (\S+)", output).group(1)
		print("Sub file", str(elem[0]), "has", charset, "with confidence", confidence)
		good_charsets = ["UTF-8-SIG", "utf-8", "ascii"]
		if charset not in good_charsets:
			fix_charset(sub_filename, charset)
			update_needed = True
		else:
			if update_needed == False: # if it is still(!) by this subs-file
				update_needed = test_sub_content(sub_filename)
			else:
				test_sub_content(sub_filename)
			
	return update_needed

def extract_subs(file, sub_ids):
	for id in range(len(sub_ids)):
		sub_filename = file[:-4]+'-'+str(sub_ids[id][0])+'.srt'
		subprocess.call(["/usr/local/bin/ffmpeg", "-n", "-i", file, "-map", "0:s:"+str(id), "-c:s", "copy", "-nostats", sub_filename]) #, stdout=subprocess.PIPE, stderr=subprocess.PIPE

def fix_mkv(file, ids, root):
	extract_subs(file, ids)
	update_needed = fix_subs(file, ids)
	if update_needed:
		print("Update of file", file, "was needed, remuxing, then deleting the old file.")
		remux(file, ids)
		cleanup(file, ids, updated=True)
	else:
		print("No update of file", file, "was needed. Cleaning up and leaving file intact.")
		cleanup(file, ids, updated=False)

def get_flags(mkvinfo, id):
	id = str(id)
	lines = iter(mkvinfo.split('\n'))
	found = False
	while found == False:
		try:
			current = next(lines)
			if current.endswith("(track ID for mkvmerge & mkvextract: "+id+")"):
				found = True
		except:
			return None
	end = False
	flags = dict()
	while current.startswith("|  "):
		current = next(lines)
		if '"Commentary" flag' in current:
			flags['flag-commentary'] = current[-1]
		elif '"Forced display" flag' in current:
			flags['flag-forced'] = current[-1]
		elif '"Hearing impaired" flag' in current:
			flags['flag-hearing-impaired'] = current[-1]
		elif current.endswith("+ Track"):
			end = True
	return flags
	

def inspect_mkv(file, root):
	'''
	Runs an mkvmerge analysis on the mkv
	'''
	proc = subprocess.Popen(["/usr/local/bin/mkvmerge", "-i", file], stdout=subprocess.PIPE)
	output = proc.stdout.read().decode()
	sub_ids = [int(elem) for elem in re.findall('Track ID (\d): subtitles', output)]
	proc = subprocess.Popen(["/usr/local/bin/mkvinfo", file], stdout=subprocess.PIPE)
	output = proc.stdout.read().decode()
	sub_ids = [(elem,
				pymediainfo.MediaInfo.parse(file).tracks[elem+1].language,
				pymediainfo.MediaInfo.parse(file).tracks[elem+1].title,
				get_flags(output, elem)) for elem in sub_ids]
	flags = [elem[3] for elem in sub_ids]
	if None in flags:
		print(file, "has not fully legible metadata.")
	elif len(sub_ids) > 0:
 		fix_mkv(file, sub_ids, root)
	else:
		print(file, "does not have any subtitles.")

def fix_all_mkv_subs_in(dir, max_files):
	global done_files
	counter = 0
	for root, dirs, files in os.walk(dir):
		for file in files:
			if file.endswith(".mkv") and '-new.mkv' not in file:
				if len([elem for elem in finished_dirs if elem in root]) == 0:
					filepath = os.path.join(root, file)
					if filepath not in done_files:
						print(file + ":")
						inspect_mkv(filepath, root)
						add_stereo(filepath)
						with open(done_files_path, "a") as infile:
							infile.write(filepath + '\n')
						print(str(counter)+'/'+str(max_files), "files processed.")
					counter += 1

def get_total_files(dir):
	counter = 0
	for root, dirs, files in os.walk(dir):
		for file in files:
			if not file.startswith("_") and file.endswith(".mkv"):
				if len([elem for elem in finished_dirs if elem in root]) == 0:
					counter += 1
	return counter

def main():
	rootfolder = sys.argv[1]
	max_files = get_total_files(rootfolder)
	fix_all_mkv_subs_in(rootfolder, max_files)

if __name__ == "__main__":
	main()