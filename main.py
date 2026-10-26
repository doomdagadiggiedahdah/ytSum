import os
import sys
import yt_dlp
import webvtt
import glob
import anthropic
import tiktoken
import argparse
import subprocess as s
import shlex
import shutil
import tempfile
import tomllib
from urllib.parse import urlparse, parse_qs


CURR_DIR = '/home/mat/Documents/ProgramExperiments/ytSum/'
GRAVEYARD = "/home/mat/Documents/ProgramExperiments/ytSum/vtt_graveyard/"
OBS_ZK = '/home/mat/Obsidian/ZettleKasten/'


# defaults, overridden by config.toml (see config.example.toml)
DEFAULT_CONFIG = {
    "llm": {"model": "claude-sonnet-5-5"},
    "transcribe": {
        "enabled": True,
        "language": "en",
        "model": "small",
        "backend": "local",
        "device": "auto",
        "compute_type": "default",
        "command": "",
    },
}


def load_config():
    config = {section: dict(values) for section, values in DEFAULT_CONFIG.items()}
    path = os.environ.get("YTSUM_CONFIG", CURR_DIR + "config.toml")
    if os.path.exists(path):
        with open(path, "rb") as f:
            for section, values in tomllib.load(f).items():
                config.setdefault(section, {}).update(values)
    return config


CONFIG = load_config()
MODEL = CONFIG["llm"]["model"]
#ENCODING = tiktoken.encoding_for_model("gpt-4") # this is out for now


# this is just here for easy testing.
short_video = 'https://www.youtube.com/watch?v=jjb77v3LX_s'


def transcribe_audio(your_video, video_id):
    ## fallback for when captions are missing/blocked: download the audio and run whisper on it
    cfg = CONFIG["transcribe"]
    print(f"transcribing audio with whisper ({cfg['backend']} backend), this can take a while...")

    with tempfile.TemporaryDirectory() as tmp:
        audio_opts = {
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'format': 'ba[abr<=80]/ba',  # speech doesn't need more, keeps the transfer small
            'outtmpl': os.path.join(tmp, '%(id)s.%(ext)s'),
        }
        yt_dlp.YoutubeDL(audio_opts).download([your_video])
        audio = glob.glob(os.path.join(tmp, f"{video_id}.*"))[0]
        out = os.path.join(tmp, f"{video_id}.whisper.vtt")

        if cfg["backend"] == "command":
            placeholders = {"audio": audio, "out": out, "model": cfg["model"], "language": cfg["language"]}
            cmd = cfg["command"]
            for key, value in placeholders.items():
                cmd = cmd.replace("{" + key + "}", shlex.quote(value))
            s.run(cmd, shell=True, check=True, cwd=CURR_DIR)
        elif cfg["backend"] == "local":
            try:
                from whisper_vtt import transcribe
                transcribe(audio, out, cfg["model"], cfg["device"], cfg["compute_type"], cfg["language"])
            except ImportError:
                sys.exit("faster-whisper isn't installed. Run `uv pip install faster-whisper`, or set a different backend in config.toml.")
        else:
            sys.exit(f"Unknown transcribe backend '{cfg['backend']}' in config.toml (use 'local' or 'command').")

        if not os.path.exists(out):
            raise Exception(f"Transcriber finished but didn't write {out}")

        # only lands in the graveyard once it's complete, so a failed run never gets cached
        sub_filename = GRAVEYARD + os.path.basename(out)
        shutil.move(out, sub_filename)

    return sub_filename


def get_sub(your_video, force_whisper=False):
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
        sub_filename = None

        # dl vtt
        if not force_whisper:
            print("downloading captions....")
            try:
                ytdl = yt_dlp.YoutubeDL(ytdl_opts)
                ytdl.download([your_video])

                # putting the vtt in the graveyard
                vtt_filename = glob.glob(f"*{video_id}*.vtt")
                if vtt_filename:
                    vtt_current = os.getcwd() + "/" + vtt_filename[0]
                    sub_filename = GRAVEYARD +  vtt_filename[0]
                    os.rename(vtt_current, sub_filename)
                else:
                    print("No captions found for this video")
            except Exception as e:
                print(f"Couldn't download captions: {e}")

        if sub_filename is None:
            if not CONFIG["transcribe"]["enabled"]:
                raise Exception("No captions, and whisper transcription is disabled in config.toml")
            sub_filename = transcribe_audio(your_video, video_id)


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
    Format this all in Markdown please. (Wrap latex and math terms in `$` to render in line in obsidian)
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

    # read the key from the environment, personal key first, bail out early if neither is set
    api_key = os.environ.get("PERSONAL_ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Neither PERSONAL_ANTHROPIC_API_KEY nor ANTHROPIC_API_KEY is set. Export one and run again.")

    client = anthropic.Anthropic(api_key=api_key)

    # streaming so long transcripts / long summaries don't hit HTTP timeouts
    try:
        with client.messages.stream(model = MODEL,
        max_tokens=64000,
        system=prompt,
        messages=[
            {"role": "user", "content": text}
            ]) as stream:
            send = stream.get_final_message()
    except anthropic.AuthenticationError:
        sys.exit("Anthropic rejected the API key (check PERSONAL_ANTHROPIC_API_KEY / ANTHROPIC_API_KEY).")
    except anthropic.RateLimitError as e:
        sys.exit(f"Anthropic rate limit / quota error: {e.message}")
    except anthropic.APIStatusError as e:
        sys.exit(f"Anthropic API error ({e.status_code}): {e.message}")
    except anthropic.APIConnectionError:
        sys.exit("Network error talking to the Anthropic API.")

    if send.stop_reason == "refusal":
        sys.exit("The model declined to respond to this transcript.")
    if send.stop_reason == "max_tokens":
        print("warning: response hit max_tokens and may be cut off")

    res = "".join(block.text for block in send.content if block.type == "text")

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
        get_sub(URL, force_whisper=args.whisper)
        #token_and_write()
        summary = text_from_AI(transcript)
        if args.save_obs:
            write_to_file(summary)
        else:
            # default: just print it, nothing goes to Obsidian
            print(summary + f"\n\nSource: {args.URL}")
    else:
        print("No argument passed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some video URLs.')
    parser.add_argument('URL', type=str, nargs='?', help='The URL of the video to process')
    parser.add_argument('--question', type=str, default=None,  help='The URL of the video to process')
    parser.add_argument('--save-obs', action='store_true', help='Save the summary as a note in Obsidian (default: only print it)')
    parser.add_argument('--whisper', action='store_true', help='Skip YouTube captions and transcribe the audio with whisper (see config.toml)')

    args = parser.parse_args()
    main(args.URL, args.question)
