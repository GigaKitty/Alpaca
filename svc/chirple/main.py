from gtts import gTTS
import subprocess
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import io

# Create a sample TTS and pipe it directly to paplay
def create_sample_tts():
    current_time = datetime.now().strftime("%H:%M:%S")
    text = f"The current time is {current_time}"
    tts = gTTS(text=text, lang="en")

    # Save the TTS output to a memory buffer instead of a file
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)

    # Use ffmpeg to pipe the MP3 audio to paplay
    try:
        ffmpeg_process = subprocess.Popen(
            ["ffmpeg", "-i", "pipe:0", "-f", "wav", "pipe:1"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        paplay_process = subprocess.Popen(
            ["paplay"],
            stdin=ffmpeg_process.stdout,
            stderr=subprocess.DEVNULL,
        )

        # Send the MP3 data to ffmpeg for conversion to WAV
        ffmpeg_process.stdin.write(mp3_fp.read())
        ffmpeg_process.stdin.close()

        # Wait for both processes to complete
        paplay_process.communicate()
        ffmpeg_process.communicate()

        print(f"Played TTS for time: {current_time}")
    except Exception as e:
        print(f"Exception occurred while playing TTS: {e}")

# Set up APScheduler and start monitoring
if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(create_sample_tts, 'interval', minutes=1, seconds=0)

    try:
        print("Starting scheduler...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Exiting ...")
        scheduler.shutdown()
