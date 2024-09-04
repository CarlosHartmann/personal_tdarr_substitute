#!/usr/local/bin/python3

import os
import sys
import subprocess
from pymediainfo import MediaInfo as MI

filters = {	'5.1': 'pan=stereo|FL<FL+0.707*FC+0.707*BL+0.5*LFE|FR<FR+0.707*FC+0.707*BR+0.5*LFE',
			'7.1': 'pan=stereo|FL = 0.274804*FC + 0.388631*FL + 0.336565*SL + 0.194316*SR + 0.336565*BL + 0.194316*BR + 0.274804*LFE | FR = 0.274804*FC + 0.388631*FR + 0.336565*SR + 0.194316*SL + 0.336565*BR + 0.194316*BL + 0.274804*LFE',
			'6.1': 'pan=stereo|FL = 0.321953*FC + 0.455310*FL + 0.394310*SL + 0.227655*SR + 278819*BC + 0.321953*LFE | FR = 0.321953*FC + 0.455310*FR + 0.394310*SR + 0.227655*SL + 278819*BC + 0.321953*LFE',
			'5.0': 'pan=stereo|FL = 0.460186*FC + 0.650802*FL + 0.563611*BL + 0.325401*BR | FR = 0.460186*FC + 0.650802*FR + 0.563611*BR + 0.325401*BL'
			}

def convert_to_stereo(file, ids_list, num_a_tracks, stderr):
	# frequently used command chunks
	comm_in = ['/usr/local/bin/ffmpeg', '-y', '-i', 'file:'+file]
	comm_out = ['file:' + file[:-4]+'-new.mkv']
	comm_vid = ['-map', '0:0', '-c:0', 'copy']
	
	# vars to keep track
	c = 1
	created_files = list()
	
	for id_tuple in ids_list:
		metadata = dict()
		filter_dict = dict()
		id = id_tuple[0]-1
		channel_layout = id_tuple[1]
		if channel_layout == '1' or channel_layout == '2' or channel_layout == '3' or channel_layout == 'Object Based':
			new_file = file[:-4]+'-'+str(c)+'.aac'
			lang = MI.parse(file).audio_tracks[id-1].language
			stream_title = MI.parse(file).audio_tracks[id-1].title
			#lang = pycountry.languages.get(iso639_1_code=lang).iso639_2T_code # ffmpeg requires the ISO-639-2 code, but MediaInfo provides the -1 code
			comm = comm_in + ['-map', '0:'+str(id), '-c:a', 'libfdk_aac', 'file:' + new_file]
			subprocess.call(comm, stdout=subprocess.PIPE)
			created_files.append(new_file)
			metadata[new_file] = (lang, stream_title)
			c += 1
		elif channel_layout in list(filters.keys()):
			pan = filters[channel_layout]
			new_file = file[:-4]+'-'+str(c)+'.aac'
			lang = MI.parse(file).audio_tracks[id-1].language
			stream_title = MI.parse(file).audio_tracks[id-1].title
			stream_title = stream_title if stream_title is not None else ''
			#lang = pycountry.languages.get(iso639_1_code=lang).iso639_2T_code # ffmpeg requires the ISO-639-2 code, but MediaInfo provides the -1 code.
			comm = comm_in + ['-map', '0:'+str(id), '-c:a', 'libfdk_aac', 'file:' + new_file]
			print(' '.join(comm))
			subprocess.call(comm, stdout=subprocess.PIPE)
			created_files.append(new_file)
			filter_dict[new_file] = pan
			metadata[new_file] = (lang, stream_title)
			c += 1
		else:
			print("Unexcpected channel layout:", channel_layout)
			return 1
	
	merge_comm = comm_in
	for elem in created_files:
		merge_comm = merge_comm + ['-i', elem]
	
	merge_comm = merge_comm + comm_vid
	
	for elem in created_files:
		counter = elem[-5]
		merge_comm = merge_comm + ['-map', counter+':a', '-filter:'+counter, filter_dict[elem], '-c:'+counter, 'libfdk_aac']
	
	print("Merging", str(c), "workaround-files, check their metadata in the new file!")
	
	for i in range(1, num_a_tracks+1):
		merge_comm = merge_comm + ['-map', '0:'+str(i), '-c:'+str(c), 'copy']
		c += 1
		
	comm_subs = ['-map', '0:s?', '-c:s', 'copy', '-map_metadata', '0']
	options = ['-nostats']
	
	merge_comm = merge_comm + comm_subs + options + comm_out
	print(' '.join(merge_comm))
	
	proc = subprocess.call(merge_comm, stdout=subprocess.PIPE)
	if proc != 0:
		with open("log.txt", "a") as outfile:
			outfile.write('Error detected, repeating with -ss flag.')
		comm = ['/usr/local/bin/ffmpeg', '-fflags', '+genpts'] + comm[2:]
		proc = subprocess.call(comm, stdout=subprocess.PIPE, stderr=stderr)	
	
	for i in range(1, len(created_files) + 1):
		new_file = file[:-4]+'-new.mkv'
		elem = created_files[i-1]
		lang = metadata[elem][0]
		title = metadata[elem][1]
		subprocess.call(['/usr/local/bin/mkvpropedit', new_file, '--edit', 'track:a'+str(i), '--set', 'language='+lang])
		subprocess.call(['/usr/local/bin/mkvpropedit', new_file, '--edit', 'track:a'+str(i), '--set', 'name='+title])
		subprocess.call(['/usr/local/bin/mkvpropedit', new_file, '--edit', 'track:a'+str(i), '--set', 'flag-default=1'])
		os.remove(elem)
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
	a_tracks = MI.parse(file).audio_tracks
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
		print("No tracks to convert.")
		return 0
		pass
	else:
		chosen = possible_tracks[0]
		print("No 7.1 tracks found, choosing the first possible track to convert")
		proc = convert_to_stereo(file, [(chosen[0], chosen[1])], num_a_tracks, stderr)
		if proc != 0:
			return None
		else:
			return proc

# def convert(file, stderr=open("log.txt", "a")):
# 	a_tracks = MI.parse(file).audio_tracks
# 	num_a_tracks = len(a_tracks)
# 	convert_tracks = list()
# 	for track in a_tracks:
# 		id = track.track_id
# 		codec = track.codec_id
# 		
# 		if track.channellayout_original:
# 			layout = track.channellayout_original
# 		else:
# 			layout = track.channel_layout
# 			
# 		if track.channel_s__original:
# 			chans = str(track.channel_s__original)
# 		else:
# 			chans = str(track.channel_s)
# 		
# 		if layout != None:
# 			if 'LFE' in layout.split():
# 				chans = str(int(chans)-1) + '.1'
# 			if chans == '5':
# 				chans = chans + '.0'
# 			elif chans == '6':
# 				chans = chans + '.0'
# 		else:
# 			if chans == '6':
# 				chans = '5.1'
# 		commentary_check = is_commentary(run_mkvinfo(file), id, file)
# 		if commentary_check == 'metadata_issue':
# 			return None
# 		elif '.' in chans:
# 			convert_tracks.append((id, chans))
# 		elif 'AAC' not in codec and 'AC3' not in codec and 'E-AC-3' not in codec and 'MPEG/L3' not in codec:
# 			convert_tracks.append((id, chans))
# 	layouts = [elem[1] for elem in convert_tracks]
# 	if len(convert_tracks) > 0:
# 		proc = convert_to_stereo(file, convert_tracks, num_a_tracks, stderr)
# 	else:
# 		proc = 0
# 	if proc != 0:
# 		print("Process failed for", file)
# 		return None # not relevant here but for uses in other scripts
# 	else:
# 		return True

def add_stereo(file):
    path_4k = "/Volumes/Almazen/filmsammlung/4K"
    filename = file.split('/')[-1]
    if os.path.isfile(path_4k + "/" + filename): # 4K-Files to be handled differently
        convert_4k(file, stderr=open("log.txt", "a"))
    else:
        convert(file, stderr=open("log.txt", "a"))
 
def main():
    file = sys.argv[1]
    add_stereo(file)

if __name__ == "__main__":
	main()