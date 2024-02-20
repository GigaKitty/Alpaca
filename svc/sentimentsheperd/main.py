import asyncio
import json
import sys
import time
import os
import websockets

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Global variable to track WebSocket connection status
websocket_connected = False


def wait_on_run(run, thread):

    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run


# RULES:
#   - Streaming news categories or tickers to specific agent
#   - Return sentiment score and recommended action
async def news(assistant, thread):
    global websocket_connected
    wss_news_url = "wss://stream.data.alpaca.markets/v1beta1/news"
    async with websockets.connect(wss_news_url) as websocket:
        api_key = os.getenv("APCA_API_KEY_ID")
        api_sec = os.getenv("APCA_API_SECRET_KEY")
        auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

        await websocket.send(auth_message)

        response = await websocket.recv()

        print(f"Authentication response: {response}")

        try:
            response_data = json.loads(response)
        except json.JSONDecodeError:
            print("Invalid JSON received in the authentication response.")
            return

        if isinstance(response_data, list) and response_data[0].get("T") == "success":
            subscription_message = json.dumps({"action": "subscribe", "news": ["*"]})
            print("Authentication successful. Connected to the WebSocket.")
            websocket_connected = True
            await websocket.send(subscription_message)

            while True:
                try:
                    data = await websocket.recv()
                    asyncio.create_task(prompt_gpt(assistant, thread, data))
                    print("--------------------------------------------")
                except websockets.ConnectionClosed:
                    print("WebSocket connection closed")
                    websocket_connected = False
                    break
        else:
            print("Authentication failed.")
            websocket_connected = False


def init_assistant(assistant_name):
    # List all existing assistants
    assistants = client.beta.assistants.list()

    # Check if the assistant already exists
    if assistants.data:
        for assistant in assistants.data:
            if assistant.name == assistant_name:
                print(f"Assistant '{assistant_name}' already exists.")
                thread = client.beta.threads.create()

                return assistant, thread
    else:
        name = assistant_name
        instructions = """
        You add a sentiment score to scaled from -100 (negative) to 100 (positive).
        You are a brilliant investor that consumes headlines in the form of JSON data.
        You return only JSON with this added sentiment score.
        You take this JSON and analyze it to perform a sentiment score of buy or sell of the asset.
        You will remember previous messages in this thread and cross examine that information in an efficient but accurate manner.
        """
        assistant = client.beta.assistants.create(
            name=name,
            instructions=instructions.strip().replace("\n", ""),
            model="gpt-4-turbo-preview",
        )

        print(f"Assistant '{assistant.name}' created.")
        print(f"Assistant ID: {assistant.id}")

        thread = client.beta.threads.create()
        print(f"Thread ID: {thread.id}")

        return assistant, thread


async def prompt_gpt(assistant, thread, data):
    print("============================================================")
    print("Prompting GPT-4 with the following data:")
    print(data)
    print(assistant)
    print(thread)
    print("============================================================")

    print("Simulating some processing time...")
    await asyncio.sleep(42)  # sleep for 5 seconds
    print("Processing complete!")

    return

    message = client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=data
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id, assistant_id=assistant.id
    )

    # Wait for completion
    # wait_on_run(run, thread)

    # Retrieve all the messages added after our last user message
    # messages = client.beta.threads.messages.list(
    #     thread_id=thread.id, order="asc", after=message.id
    # )

    print(run)


if __name__ == "__main__":
    # Create an assistant specific to this service and environment i.e. 'sentimentsheperd-dev'
    assistant = init_assistant(
        "{}-{}".format(
            os.getenv("COPILOT_SERVICE_NAME", "sentimentsheperd"),
            os.getenv("COPILOT_ENVIRONMENT", "dev"),
        )
    )

    print("Starting news websocket")
    asyncio.get_event_loop().run_until_complete(news(assistant[0], assistant[1]))
