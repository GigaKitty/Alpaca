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
        print(f"Assistant Instructions: {assistant.instructions}")
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

    # print("Simulating some processing time...")
    # await asyncio.sleep(42)  # sleep for 5 seconds
    # print("Processing complete!")

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


async def redis_listener():
    redis = aioredis.from_url(
        f"redis://{redis_host}:{redis_port}",
        encoding="utf-8",
        decode_responses=True,
    )
    pubsub = redis.pubsub()
    await pubsub.subscribe("news_channel")

    async for message in pubsub.listen():
        if message["type"] == "message":
            print(message["data"])


async def main():
    """
    Main function to start the scheduler and run the event loop
    """
    await asyncio.gather(redis_listener())


if __name__ == "__main__":
    """
    Entry point for the application
    """
    asyncio.run(main())
    # Create an assistant specific to this service and environment i.e. 'sentimentsheperd-dev'
    # assistant = init_assistant(
    #    "{}-{}".format(
    #        os.getenv("COPILOT_SERVICE_NAME", "sentimentsheperd"),
    #        os.getenv("COPILOT_ENVIRONMENT", "dev"),
    #    )
    # )
