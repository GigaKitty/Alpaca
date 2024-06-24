import json
import os
import time
import asyncio
import redis.asyncio as aioredis
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Redis connection details
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))


def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run


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
        instructions = """
        You add a sentiment score scaled from -100 (negative) to 100 (positive).
        You are a brilliant investor that consumes headlines in the form of JSON data.
        You follow the links to these headlines and consume the  content and add that information to your overall sentiment score.
        You return only JSON with this added sentiment score.
        You take this JSON and analyze it to perform a sentiment score for each ticker of buy or sell of the asset and add that to the existing data json object as a new field.
        You also produce a summary or reason for sentiment on each ticker>
        You will remember previous messages in this thread and cross-examine that information in an efficient but accurate manner.
        """
        assistant = client.beta.assistants.create(
            name=assistant_name,
            instructions=instructions.strip().replace("\n", ""),
            model="gpt-4-turbo-preview",
        )

        print(f"Assistant '{assistant.name}' created.")
        print(f"Assistant ID: {assistant.id}")
        print(f"Assistant Instructions: {assistant.instructions}")
        thread = client.beta.threads.create()
        print(f"Thread ID: {thread.id}")

        return assistant, thread


async def prompt_gpt(assistant, thread, data):
    print("============================================================")
    print("Prompting GPT-4 with the following data:")
    print(f"Data: {data}")
    print(f"Thread ID: {thread.id}")
    print(f"Assistant ID: {assistant.id}")
    print("============================================================")

    # message = client.beta.threads.messages.create(
    #    thread_id=thread.id, role="user", content=json.dumps(data)
    # )

    # run = client.beta.threads.runs.create(
    #    thread_id=thread.id, assistant_id=assistant.id
    # )

    ## Wait for completion
    # run = wait_on_run(run, thread)

    ## Retrieve all the messages added after our last user message
    # messages = client.beta.threads.messages.list(
    #    thread_id=thread.id, order="asc", after=message.id
    # )

    # for msg in messages.data:
    #    if msg.role == "assistant":
    #        content = msg.content
    #        print(f"Assistant response content: {content}")
    #        if isinstance(content, str):
    #            try:
    #                return json.loads(content)
    #            except json.JSONDecodeError as e:
    #                print(f"Error decoding JSON: {e}")
    #                return None
    #        elif isinstance(content, list):
    #            try:
    #                return [
    #                    json.loads(item) for item in content if isinstance(item, str)
    #                ]
    #            except json.JSONDecodeError as e:
    #                print(f"Error decoding JSON list item: {e}")
    #                return None

    # return None


async def redis_listener(assistant, thread):
    redis = aioredis.from_url(
        f"redis://{redis_host}:{redis_port}",
        encoding="utf-8",
        decode_responses=True,
    )
    pubsub = redis.pubsub()
    await pubsub.subscribe("news_channel")

    async for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"]
            await prompt_gpt(assistant, thread, data)


async def main():
    assistant_name = "{}-{}".format(
        os.getenv("SERVICE_NAME", "sentimentsheperd"),
        os.getenv("ENVIRONMENT", "dev"),
    )
    assistant, thread = init_assistant(assistant_name)
    await asyncio.gather(redis_listener(assistant, thread))


if __name__ == "__main__":
    asyncio.run(main())
