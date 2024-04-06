# ytSum

Get summaries of your favorite YouTube videos and import them directly to your Obsidian vault!

## Usage
1. Simply open your terminal (Ctrl + Alt + T)
2. Activate the `venv`
3. Run the command `python main.py your_youtube_link`
- Ex. `python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ`

### New and improved; ask your own questions to the video.
- Use `python main.py {your video link} --question "put question in quotations"` to query the video data in a specific way.

## Setup before usage
- You'll need to update the following variables in `main.py` before running the script:
  - `openai.api_key_path`: provide your own key ;)
  - `GRAVEYARD`: if you want to keep the vtt files from your videos, this is where they'll be saved
  - `OBS_ZK`: This is the location that you'll deposit your summaries in Obsidian
