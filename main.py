import os
import yt_dlp
import webvtt
import sys
import glob
import openai
import tiktoken
import subprocess as s
from urllib.parse import urlparse, parse_qs
from collections import deque
import http.client


openai.api_key_path= "/home/mat/Documents/ProgramExperiments/openAIapiKey"
CURR_DIR = '/home/mat/Documents/ProgramExperiments/ytSum/'
GRAVEYARD = "/home/mat/Documents/ProgramExperiments/ytSum/vtt_graveyard/"
OBS_ZK = '/home/mat/Obsidian/ZettleKasten/'
MODEL = "gpt-3.5-turbo-16k-0613"
ENCODING = tiktoken.encoding_for_model(MODEL)


# this is just here for easy testing.
short_video = 'https://www.youtube.com/watch?v=jjb77v3LX_s'


def get_sub(your_video):
    global video_title, transcript, video_id

    # This is for vtt ID'ing and moving around basically
    query = urlparse(your_video).query
    video_id = parse_qs(query)["v"][0]


    vtt_already_downloaded = glob.glob(os.path.join(CURR_DIR + "vtt_graveyard/", f"*{video_id}*"))

    ytdl_opts = {
            'retries': 5,
            'quiet': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'get-title': True
            }

    if vtt_already_downloaded:
        print("yo found it")
        sub_filename = vtt_already_downloaded[0]
    
    else:
        print("new video")
        print("downloading video....")

        # dl vtt
        ytdl = yt_dlp.YoutubeDL(ytdl_opts)
        ytdl.download([your_video])

        # putting the vtt in the graveyard
        vtt_filename = glob.glob(f"*{video_id}*")

        vtt_current = os.getcwd() + "/" + vtt_filename[0]
        sub_filename = GRAVEYARD +  vtt_filename[0]
        os.rename(vtt_current, sub_filename)


    # This is just getting video title, to name the obsidian note later
    ytdl = yt_dlp.YoutubeDL(ytdl_opts)
    info = ytdl.extract_info(your_video, download=False, extra_info=None)
    video_title = info['title']




    ### formatting text to be human readable (and without timestamps)
    # credit: https://stackoverflow.com/questions/51784232/how-do-i-convert-the-webvtt-format-to-plain-text

    lines = []
    transcript = ""
    vtt = webvtt.read(sub_filename)


    for line in vtt:
        # Strip the newlines from the end of the text.
        # Split the string if it has a newline in the middle
        # Add the lines to an array
        lines.extend(line.text.strip().splitlines())

    # Remove repeated lines
    previous = None
    for line in lines:
        if line == previous:
            continue
        transcript += " " + line
        previous = line
    print("got video")
    return
    


def token_and_write():
    ## this function calls the OpenAI call and writing to text.

    global transcript

    TOKEN_LEN = (len(ENCODING.encode(transcript)))
    if TOKEN_LEN > 16000:
        print('oh my god becky')
        
        listStuff = []
        mid = len(transcript) // 2
        first_half = transcript[:mid]
        second_half = transcript[mid:]
        listStuff = listStuff + [first_half, second_half]


        # takes summaries, and then summarizes them
        summary_list = ""
        for i in listStuff:
            print("summarizing part")
            summary_list += text_from_AI(i)

        write_to_file(text_from_AI(summary_list))

    else:
        print("Small enough for single summary")
        write_to_file(text_from_AI(transcript))

    return




### AI Stuff inbound
def text_from_AI(text):
    print("sending to AI")

    # for chunk in chunks:
    prompt = """
    Take the following text and write out a very lengthy summary (700 words) of the technical aspects.
    Provide multiple headings that give quick overviews of what each section talks about, and also explains what the entire text is about.
    Finish with typing out the key points of the text. 
    Format this all in Markdown please.
    \n- 
    """
    
    # try:
    send = openai.ChatCompletion.create(
        model = MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
    ])

    res = send["choices"][0]["message"]["content"]

    return str(res)


def get_unique_filename(file_name):
    # global file_name
    base_name, ext = os.path.splitext(file_name)
    counter = 0
    while os.path.exists(OBS_ZK + file_name):
        file_name = f"{base_name}{counter}{ext}"
        counter += 1
    
    # Create the file with the unique name
    with open(OBS_ZK + file_name, 'w') as f:
        f.write('')  # Write an empty string, just to create the file
    
    return file_name


def write_to_file(text_to_write):
    global video_title

    # this is because Obsidian doesn't like certain chars, won't create file if includes.
    replace_list = ["/", "\\",  ":", "[", "]", "#", "^", "|"]
    for i in replace_list:
        video_title = video_title.replace(i, "'")

    NOTE_NAME = video_title + ' (AI Summary).md'

    if os.path.exists(OBS_ZK + NOTE_NAME):
        user_choice = input("The file already exists. Do you want to overwrite it? (yes/no/cancel): ").strip().lower()
        
        if user_choice == "yes":
            with open(OBS_ZK + NOTE_NAME, 'w+') as f:  
                f.write(text_to_write + f"\n\nSource: {video_url}")
            print("done! Check Obsidian for the note named " + NOTE_NAME)

        elif user_choice == "no":
            unique_name = get_unique_filename(NOTE_NAME)
            with open(OBS_ZK + unique_name, 'w+') as f:
                f.write(text_to_write + f"\n\nSource: {video_url}")
            print("done! Check Obsidian for the note named " + unique_name)

        elif user_choice == "cancel":
            print("Operation cancelled.")

        else:
            print("Try again, cancel if you need")
            

    else:
        with open(OBS_ZK + NOTE_NAME, 'w+') as f:  
            f.write(text_to_write + f"\n\nSource: {video_url}")

    


#------- Execution Time --------#

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg1 = sys.argv[1]
        video_url = sys.argv[1]
        print(f"Working on your video: {video_url}")
    else:
        print("No argument passed.")


    get_sub(video_url)
    token_and_write()

