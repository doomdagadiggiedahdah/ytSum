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
OBS_ZK = '/home/mat/Obsidian/ZettleKasten/'
MODEL = "gpt-3.5-turbo-16k-0613"
ENCODING = tiktoken.encoding_for_model(MODEL)


# this is just here for easy testing.
short_video = 'https://www.youtube.com/watch?v=jjb77v3LX_s'


def get_sub(your_video):
    global video_title, transcript, video_id

    query = urlparse(your_video).query
    video_id = parse_qs(query)["v"][0]

    # Download subtitles using yt-dlp    # ^^ is not finding the vtt file for some reason...
    # and just to make sure, I was able to run the webvtt.read() command just fine by entering in the file name directly.

    ## I think the above two comments aren't needed anymore, not sure.
    ytdl_opts = {
        'retries': 5,
        'quiet': True,
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'get-title': True
    }

    print("downloading video....")
    ytdl = yt_dlp.YoutubeDL(ytdl_opts)
    ytdl.download([your_video])
    info = ytdl.extract_info(your_video, download=False, extra_info=None)
    video_title = info['title']
    sub_filename = glob.glob(f"*{video_id}*")



    ### formatting text to be human readable (and without timestamps)
    # credit: https://stackoverflow.com/questions/51784232/how-do-i-convert-the-webvtt-format-to-plain-text

    lines = []
    transcript = ""
    vtt = webvtt.read(sub_filename[0])

    # putting the vtt in the graveyard
    vtt_current = os.getcwd() + "/" + sub_filename[0]
    vtt_destination = "/home/mat/Documents/ProgramExperiments/ytSum/vtt_graveyard/" + sub_filename[0]
    os.rename(vtt_current, vtt_destination)

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


    # beginning of token stuff, prob could go to another function.

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
            print("\n\nsummarizing part\n\n")
            summary_list += text_from_AI(i)

        write_to_file(text_from_AI(summary_list))

    else:
        print("shit nah, no splittin here")
        write_to_file(text_from_AI(transcript))

    return
    


def write_to_file(text_to_write):
    global video_title

    # this is because Obsidian doesn't like certain chars, won't create file if includes.
    replace_list = ["/", "\\",  ":", "[", "]", "#", "^", "|"]
    for i in replace_list:
        video_title = video_title.replace(i, "'")

    NOTE_NAME = video_title + ' (AI Summary).md'

    with open(OBS_ZK + NOTE_NAME, 'a+') as f:  
        f.write(text_to_write + f"\n\nSource: {video_url}")
    print("done! Check Obsidian for the note named " + NOTE_NAME)



### AI Stuff inbound
def text_from_AI(text):
    print("sending to AI")

    # for chunk in chunks:
    prompt = """
    Take the following text and write out a very lengthy summary of the technical aspects talked about, ((including side notes for more complicated concepts you see in double quotes like this)).
    Finish with typing out the key points of the text. 
    Provide multiple headings that give quick overviews of what each section talks about, and also explains what the entire text is about.
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


#------- Execution Time --------#

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg1 = sys.argv[1]
        video_url = sys.argv[1]
        print(f"Working on your video: {video_url}")
    else:
        print("No argument passed.")


    get_sub(video_url)


    ## (((I can uncomment these when I want the AI send again.)))
    ## "a+" is indeed append boi




    # NOTE_NAME = video_title + ' (AI Summary).md'
    # with open(OBS_ZK + NOTE_NAME, 'w+') as f:
    #     f.write(text_from_AI() + f"\n\nSource: {video_url}")

    # sys.stdout.write(str(NOTE_NAME))

