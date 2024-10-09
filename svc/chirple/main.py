import asyncio
from datetime import datetime
from gtts import gTTS
import io
import redis.asyncio as aioredis
import subprocess

CHRIPLE_CHANNEL = "account_channel"

async def speakoutloud(message):
    current_time = datetime.now().strftime("%H:%M:%S")
    print(message)
    text = message.decode("utf-8")
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

        #print(f"Played TTS for time: {current_time}")
    except Exception as e:
        print(f"Exception occurred while playing TTS: {e}")

# Function to handle messages from Redis channel
async def handle_redis_message(message):
    print(f"Received message from Redis: {message.decode('utf-8')}")
    await speakoutloud(message)

# Function to listen to Redis channel
async def listen_to_redis_channel():
    redis = aioredis.from_url('redis://redis-stack-core:6379')
    pubsub = redis.pubsub()
    await pubsub.subscribe(CHIRPLE_CHANNEL)

    async for message in pubsub.listen():
        if message['type'] == 'message':
            await handle_redis_message(message['data'])

    await redis.close()

# Set up the event loop and start monitoring
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(listen_to_redis_channel())

    # Keep the main thread alive
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()