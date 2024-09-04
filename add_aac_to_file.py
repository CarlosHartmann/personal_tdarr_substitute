#!/usr/local/bin/python3

'''
add_aac_to_file: The seemingly simple name hides a monumental task once you get down to all the exceptions and complications.
I do not remember most of my work here as it took me 18 hours and I did it in one go without breaks.
I recommend testing this as a stand-alone and observing what it does to your files. If you want something to be done differently,
an LLM could perhaps try to find where to edit the code.
'''


import os
import sys
import subprocess
import pymediainfo

# Taken from: https://superuser.com/a/1410620
filters = {	'5.1': 'pan=stereo|FL<FL+0.707*FC+0.707*BL+0.5*LFE|FR<FR+0.707*FC+0.707*BR+0.5*LFE',
			'7.1': 'pan=stereo|FL = 0.274804*FC + 0.388631*FL + 0.336565*SL + 0.194316*SR + 0.336565*BL + 0.194316*BR + 0.274804*LFE | FR = 0.274804*FC + 0.388631*FR + 0.336565*SR + 0.194316*SL + 0.336565*BR + 0.194316*BL + 0.274804*LFE',
			'6.1': 'pan=stereo|FL = 0.321953*FC + 0.455310*FL + 0.394310*SL + 0.227655*SR + 278819*BC + 0.321953*LFE | FR = 0.321953*FC + 0.455310*FR + 0.394310*SR + 0.227655*SL + 278819*BC + 0.321953*LFE',
			'5.0': 'pan=stereo|FL = 0.460186*FC + 0.650802*FL + 0.563611*BL + 0.325401*BR | FR = 0.460186*FC + 0.650802*FR + 0.563611*BR + 0.325401*BL'
			}

def convert_to_stereo(file, ids_list, num_a_tracks, stderr):
	c = 1
	comm = ['/usr/local/bin/ffmpeg', '-y', '-i']
	comm = comm + ['file:'+file]
	comm = comm + ['-map', '0:0', '-c:0', 'copy']
	for id_tuple in ids_list:
		id = id_tuple[0]-1
		channel_layout = id_tuple[1]
		if channel_layout == '1' or channel_layout == '2' or channel_layout == '3' or channel_layout == 'Object Based':
			comm = comm + ['-map', '0:'+str(id), '-c:'+str(c), 'libfdk_aac', '-ac', '2']
			c += 1
		elif channel_layout in list(filters.keys()):
			pan = filters[channel_layout]
			comm = comm + ['-map', '0:'+str(id), '-filter:'+str(id), pan, '-c:'+str(c), 'libfdk_aac']
			c += 1
		else:
			print("Unexcpected channel layout:", channel_layout)
			return 1
	for i in range(1, num_a_tracks+1):
		comm = comm + ['-map', '0:'+str(i), '-c:'+str(c), 'copy']
		c += 1
	comm = comm + ['-map', '0:s?', '-c:s', 'copy', '-map_metadata', '0']
	comm = comm + ['-strict', '2', 'file:' + file[:-4]+'-new.mkv']
	comm = comm + ['-nostats']
	#print(' '.join(comm))
	proc = subprocess.call(comm, stdout=subprocess.PIPE, stderr=open("log.txt", "a"))
	if proc != 0:
		with open("log.txt", "a") as outfile:
			outfile.write('Error detected, repeating with -ss flag.')
		comm = ['/usr/local/bin/ffmpeg', '-fflags', '+genpts'] + comm[2:]
		proc = subprocess.call(comm, stdout=subprocess.PIPE, stderr=stderr)	
	return proc
		

def is_commentary(mkvinfo, id, path):
	global counter
	id = str(id)
	lines = iter(mkvinfo.split('\n'))
	found = False
	while found == False:
		try:
			current = next(lines)
		except:
			print("Metadata are illegible in", path)
			return 'metadata_issue'
		if "Track number: "+id in current:
			found = True
	end = False
	while current.startswith("|  "):
		current = next(lines)
		if '"Commentary" flag: 1' in current:
			return 'is_commentary'
		elif current.endswith("+ Track") or current.endswith("+ Chapters"):
			end = True
	return 'not_commentary'

def run_mkvinfo(file):
	proc = subprocess.Popen(["/usr/local/bin/mkvinfo", file], stdout=subprocess.PIPE)
	return proc.stdout.read().decode()

def convert(file, stderr):
	possible_tracks = list()
	a_tracks = pymediainfo.MediaInfo.parse(file).audio_tracks
	num_a_tracks = len(a_tracks)
	for track in a_tracks:
		id = track.track_id
		codec = track.codec_id
		
		if track.channellayout_original:
			layout = track.channellayout_original
		else:
			layout = track.channel_layout
			
		if track.channel_s__original:
			chans = str(track.channel_s__original)
		else:
			chans = str(track.channel_s)
			
		if layout != None:
			if 'LFE' in layout.split():
				chans = str(int(chans)-1) + '.1'
			if chans == '5':
				chans = chans + '.0'
			elif chans == '6':
				chans = '5.1'
				
		commentary_check = is_commentary(run_mkvinfo(file), id, file)
		
		if commentary_check == 'metadata_issue':
			return None
		elif '.1' in chans and commentary_check == 'not_commentary':
			possible_tracks.append((id, chans))
		elif commentary_check == 'is_commentary':
			pass	
		elif 'AAC' not in codec and 'AC3' not in codec and 'E-AC-3' not in codec and 'MPEG/L3' not in codec:
			possible_tracks.append((id, chans))
	layouts = [elem[1] for elem in possible_tracks]
	if '7.1' in layouts:
		for elem in possible_tracks:
			if elem[1] ==  '7.1':
				print("Found 7.1 track, converting it to stereo...")
				proc = convert_to_stereo(file, [(elem[0], elem[1])], num_a_tracks, stderr)
				if proc != 0:
					return None
				else:
					return proc
				break
	elif possible_tracks == []:
		print("No tracks to convert in", file)
		return 'leave as is'
		pass
	else:
		chosen = possible_tracks[0]
		print("No 7.1 in file, choosing the first audio track that must be converted.")
		# This could probably be changed to a system where it asks the user which track to convert
		# Sometimes there are two equal audio tracks that are simply different languages => both should be converted
		proc = convert_to_stereo(file, [(chosen[0], chosen[1])], num_a_tracks, stderr)
		if proc != 0:
			return None
		else:
			return proc

 
def main(): # this is just for running the script as stand-alone
    file = sys.argv[1]
    convert(file, stderr=open("log.txt", "a")))

if __name__ == "__main__":
	main()
