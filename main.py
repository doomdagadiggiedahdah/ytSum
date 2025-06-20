import os
import yt_dlp
import webvtt
import glob
from openai import OpenAI
import tiktoken
import argparse
import subprocess as s
from urllib.parse import urlparse, parse_qs


client = OpenAI()
CURR_DIR = '/home/mat/Documents/ProgramExperiments/ytSum/'
GRAVEYARD = "/home/mat/Documents/ProgramExperiments/ytSum/vtt_graveyard/"
OBS_ZK = '/home/mat/Obsidian/ZettleKasten/'
MODEL = "gpt-4.1-nano"
#ENCODING = tiktoken.encoding_for_model("gpt-4") # this is out for now


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
            'no_warnings': True,
            'skip_download': True,
            'subtitlesformat': 'vtt',
            'writesubtitles': False,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'ignoreerrors': False,
            'get-title': True
            }

    if vtt_already_downloaded:
        print("yo found it")
        sub_filename = vtt_already_downloaded[0]

    else:
        print("new video")
        print("downloading video....")

        # dl vtt
        try:
            ytdl = yt_dlp.YoutubeDL(ytdl_opts)
            ytdl.download([your_video])
        except Exception as e:
            print(f"Error downloading subtitles: {e}")
            print("Trying alternative approach...")
            
            # Fallback: try with different options
            fallback_opts = ytdl_opts.copy()
            fallback_opts['writeautomaticsub'] = True
            fallback_opts['writesubtitles'] = False
            fallback_opts['subtitleslangs'] = ['en']
            
            try:
                ytdl_fallback = yt_dlp.YoutubeDL(fallback_opts)
                ytdl_fallback.download([your_video])
            except Exception as e2:
                print(f"Fallback also failed: {e2}")
                raise Exception("Unable to download subtitles with any method")

        # putting the vtt in the graveyard
        vtt_filename = glob.glob(f"*{video_id}*")
        
        if not vtt_filename:
            raise Exception("No subtitle files found after download")

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
    if TOKEN_LEN > 1000000:

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
    Take the following text and write out a very lengthy summary (1500 words) of the main topics with a explanation of the topics.
    Provide multiple headings that give quick overviews of what each section talks about, and also explains what the entire text is about.
    Finish with typing out the key points of the text. 
    Format this all in Markdown please.
    Start this summary with the main takeaway, following these instructions: "What is the single most important thing I should take away from this information? If I were to discard everything else, what should I make sure to take away?"
    Finally, write this in the style of Paul Graham.
    \n- 
    """

    if args.question:
        print(f"Asking the model your custom question: {args.question}")
        prompt = f"""
        Take the following text and apply this instruction to it: {args.question}. 
        Aim to structure the document by: answering the question in a concise and comprehensive manner, expanding on key points 
        with relevant info from the text, suggest possible areas to look into next, and wrap up by summarizing the main points.
        Please format in Markdown with relevant headings, feel free to use emojis :)
        Finally, write this in the style of Paul Graham.
        Thank you!
        """

    # try:
    send = client.chat.completions.create(model = MODEL,
    messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": text}
        ])

    res = send.choices[0].message.content

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
    global video_title, video_url

    # this is because Obsidian doesn't like certain chars, won't create file if includes.
    replace_list = ["/", "\\",  ":", "[", "]", "#", "^", "|"]
    for i in replace_list:
        video_title = video_title.replace(i, "'")

    NOTE_NAME = video_title + ' (AI Summary).md'

    if os.path.exists(OBS_ZK + NOTE_NAME):
        user_choice = input("The file already exists. Do you want to overwrite it? (yes/no/cancel): ").strip().lower()

        if user_choice == "yes":
            with open(OBS_ZK + NOTE_NAME, 'w+') as f:  
                f.write(text_to_write + f"\n\nSource: {args.URL}")
            print("done! Check Obsidian for the note named " + NOTE_NAME)

        elif user_choice == "no":
            unique_name = get_unique_filename(NOTE_NAME)
            with open(OBS_ZK + unique_name, 'w+') as f:
                f.write(text_to_write + f"\n\nSource: {args.URL}")
            print("done! Check Obsidian for the note named " + unique_name)

        elif user_choice == "cancel":
            print("Operation cancelled.")

        else:
            print("Try again, cancel if you need")


    else:
        with open(OBS_ZK + NOTE_NAME, 'w+') as f:  
            f.write(text_to_write + f"\n\nSource: {args.URL}")
            print("done! Check Obsidian for the note named " + NOTE_NAME)




#------- Execution Time --------#

def main(URL=None, question=None):
    if URL:
        print(f"Working on your video: {URL}")
        video_url = URL
        get_sub(URL)
        #token_and_write()
        write_to_file(text_from_AI(transcript))
    else:
        print("No argument passed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some video URLs.')
    parser.add_argument('URL', type=str, nargs='?', help='The URL of the video to process')
    parser.add_argument('--question', type=str, default=None,  help='The URL of the video to process')

    args = parser.parse_args()
    main(args.URL, args.question)
