import json
import os
import time
import asyncio
import redis.asyncio as aioredis
from rich.console import Console
from rich.table import Table
from transformers import pipeline
from concurrent.futures import ThreadPoolExecutor

console = Console()

# Redis connection details
redis_host = os.getenv("REDIS_HOST", "redis-stack")
redis_port = 6379

# Initialize multiple sentiment analysis pipelines
models = [
    "distilbert-base-uncased-finetuned-sst-2-english",
    "nlptown/bert-base-multilingual-uncased-sentiment",
    "cardiffnlp/twitter-roberta-base-sentiment",
]

def analyze_sentiment(text):
    scores = []
    for analyzer in sentiment_analyzers:
        result = analyzer(text)[0]
        score = (
            result["score"]
            if result["label"] in ["POSITIVE", "5 stars", "LABEL_2"]
            else -result["score"]
        )
        scores.append(score)
    aggregated_score = sum(scores) / len(scores)
    return aggregated_score


async def process_message(message):
    if message["type"] == "message":
        article = json.loads(message["data"])
        sentiment = analyze_sentiment(article["content"])
        article["sentiment"] = sentiment
        display_in_cli(article)


async def redis_listener():
    redis = aioredis.from_url(
        f"redis://{redis_host}:{redis_port}",
        encoding="utf-8",
        decode_responses=True,
    )
    pubsub = redis.pubsub()
    await pubsub.subscribe("news_channel")

    async for message in pubsub.listen():
        print(message)
        if message["type"] == "message":
            data = message["data"]
            print(data)
            #display_in_cli(data)


def display_in_cli(article):
    table = Table(title="News Article")
    table.add_column("Title", style="bold")
    table.add_column("Content")
    table.add_column("Timestamp")
    table.add_row(article["title"], article["content"], article["timestamp"])
    console.print(table)


async def main():
    await asyncio.gather(redis_listener())


if __name__ == "__main__":
    asyncio.run(main())
