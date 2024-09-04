# personal_tdarr_substitute
This is the script I run on all my movie files to get them uniform for streaming.

Input:
* This will only handle MKV files

Output:
The same file edited so that:
* all 5+-channel audio tracks are copied onto a new track and downmixed to stereo AAC using recommended presets using libfdk_aac
* video channels do not have language metadata
* audio channels have no noisy titles
* subtitles are all in the SRT file format with UTF-8 character encoding, and are superficially cleaned

How to use this script:

### This repo is NOT an installable application. It is uploaded for you to copy the code and adjust it to your environment and goals

The code as it is uploaded will NOT run first-try. There are things like absolute paths in it that require you to read and edit the code before using it yourself. Perhaps an LLM can assist you if you're new to Python.

### Instructions

1. Download the repo
2. Write down somewhere in what path you want to put the input files, the output files, and the log files
3. Start reading preprocess.py -- this is the main script.
4. Input your own paths where necessary
5. Open and edit other files mentioned in preprocess.py as needed.
