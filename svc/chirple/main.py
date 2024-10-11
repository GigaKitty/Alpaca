from datetime import datetime
from gtts import gTTS
import asyncio
import io
import json
import redis.asyncio as aioredis
import subprocess

CHIRPLE_CHANNEL = "account_channel"


async def speakoutloud(message):
    # Decode the message and parse the JSON
    text = message.decode("utf-8")
    try:
        message_data = json.loads(text)
    except json.JSONDecodeError:
        print("Invalid JSON received.")
        return

    # Qualify the message to ensure it is a fill event
    event = message_data.get("data", {}).get("event")
    filled_at = message_data.get("data", {}).get("order", {}).get("filled_at")
    if event != "fill" and filled_at is None or filled_at == "":
        print("Order not filled.")
        return

    # Extract the required fields for tts message
    order_data = message_data.get("data", {}).get("order", {})
    ticker = order_data.get("symbol", "Unknown Ticker")
    price = round(float(order_data.get("filled_avg_price", "Unknown Price")), 2)
    filled_qty = order_data.get("filled_qty", "Unknown Quantity")
    order_type = order_data.get("type", "Unknown Type")
    side = order_data.get("side", "Unknown Side")
    position_qty = float(message_data.get("data", {}).get("position_qty", 0))

    position_value = f"${round(position_qty * price, 2)}"

    # Prepare the text for TTS
    tts_text = f"{side} side {order_type} order on {ticker} for {filled_qty} shares @ ${price} holding {position_qty} shares of {ticker} with a market value of {position_value}."
    print(f"Filled order: {tts_text}")
    tts = gTTS(
        text=tts_text, lang="en-uk", slow=False
    )  # @NOTE: can use other lang like en-au, en-uk, etc.

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
        paplay_process.communicate()
        ffmpeg_process.communicate()

        # print(f"Played TTS for time: {current_time}")
    except Exception as e:
        print(f"Exception occurred while playing TTS: {e}")
    finally:
        # Ensure all subprocesses are properly closed
        if ffmpeg_process.stdin and not ffmpeg_process.stdin.closed:
            ffmpeg_process.stdin.close()
        if ffmpeg_process.stdout and not ffmpeg_process.stdout.closed:
            ffmpeg_process.stdout.close()
        if paplay_process.stdin and not paplay_process.stdin.closed:
            paplay_process.stdin.close()


# Function to handle messages from Redis channel
async def handle_redis_message(message):
    print(f"Received message from Redis: {message.decode('utf-8')}")
    await speakoutloud(message)


# Function to listen to Redis channel
async def listen_to_redis_channel():
    redis = aioredis.from_url("redis://redis-stack-core:6379")
    pubsub = redis.pubsub()
    await pubsub.subscribe(CHIRPLE_CHANNEL)

    async for message in pubsub.listen():
        if message["type"] == "message":
            await handle_redis_message(message["data"])

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
