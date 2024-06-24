from aiohttp import web
import aiohttp
import asyncio
import json
import logging
import os
import redis.asyncio as aioredis

# Configure logging
logging.basicConfig(level=logging.INFO)

connected_clients = set()

# Connect to Redis
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
# redis_client = aioredis.StrictRedis(host=redis_host, port=redis_port, db=0)

redis_client = aioredis.from_url(
    f"redis://{redis_host}:{redis_port}",
    encoding="utf-8",
    db=0,
    decode_responses=True,
    socket_timeout=60,
    socket_connect_timeout=60,
    socket_keepalive=True,
)


async def get_earnings_list():
    """
    List is published via another service and is part of earnyearn service
    This grabs the list from Redis returns the list of tickers and closes redis connection
    """
    try:
        earnings_list = await redis_client.lindex("dev_earnings_list", 0)
        return json.loads(earnings_list)

    except Exception as e:
        logging.error(f"Error fetching latest message from Redis: {e}")
        return None


async def handle_connection(request):
    websocket = web.WebSocketResponse()
    await websocket.prepare(request)

    connected_clients.add(websocket)
    logging.info("New client connected")
    try:
        async for msg in websocket:
            if msg.type == aiohttp.WSMsgType.TEXT:
                logging.info(f"Received message from client: {msg.data}")
                # Broadcast message to all connected clients
                await broadcast(msg.data, "general")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logging.error(f"WebSocket error: {msg.data}")
                break
    finally:
        connected_clients.remove(websocket)
        logging.info("Client disconnected")

    return websocket


async def broadcast(message, channel):
    if connected_clients:  # Check if there are any connected clients
        await asyncio.wait([client.send_str(message) for client in connected_clients])
    # Publish message to Redis
    await redis_client.publish(channel, message)


async def news_socket():
    """
    @SEE: https://docs.alpaca.markets/docs/streaming-real-time-news
    """
    wss_news_url = "wss://stream.data.alpaca.markets/v1beta1/news"
    api_key = os.getenv("APCA_API_KEY_ID")
    api_sec = os.getenv("APCA_API_SECRET_KEY")
    auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(wss_news_url) as websocket:
            await websocket.send_str(auth_message)

            response = await websocket.receive_str()
            logging.info(f"News authentication response: {response}")

            try:
                response_data = json.loads(response)
            except json.JSONDecodeError:
                logging.error("Invalid JSON received in the authentication response.")
                return

            if (
                isinstance(response_data, list)
                and response_data[0].get("T") == "success"
            ):
                subscription_message = json.dumps(
                    {"action": "subscribe", "news": ["*"]}
                )
                logging.info(
                    "News authentication successful. Connected to the WebSocket."
                )
                await websocket.send_str(subscription_message)

                async for msg in websocket:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = msg.data
                        logging.info(f"News data: {data}")
                        await broadcast(data, "news_channel")
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logging.info("News WebSocket connection closed")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logging.error(f"WebSocket error: {msg.data}")
                        break
            else:
                logging.error("News authentication failed.")


async def stocks_socket():
    """
    @SEE: https://docs.alpaca.markets/docs/real-time-stock-pricing-data#schema-2
    """
    wss_stocks_url = "wss://stream.data.alpaca.markets/v2/sip"
    api_key = os.getenv("APCA_API_KEY_ID")
    api_sec = os.getenv("APCA_API_SECRET_KEY")
    auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(wss_stocks_url) as websocket:
            await websocket.send_str(auth_message)

            response = await websocket.receive_str()
            logging.info(f"Stocks authentication response: {response}")

            try:
                response_data = json.loads(response)
            except json.JSONDecodeError:
                logging.error("Invalid JSON received in the authentication response.")
                return

            if (
                isinstance(response_data, list)
                and response_data[0].get("T") == "success"
            ):
                earnings_list = await get_earnings_list()
                logging.info(f"Subscribing to the following tickers: {earnings_list}")
                subscription_message = json.dumps(
                    {
                        "action": "subscribe",
                        "trades": earnings_list,
                        "quotes": earnings_list,
                        "bars": ["*"],
                        "statuses": ["*"],
                    }
                )
                await websocket.send_str(subscription_message)

                async for msg in websocket:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = msg.data
                        logging.info(f"Stocks data: {data}")
                        await broadcast(data, "stocks_channel")
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logging.info("Stocks WebSocket connection closed")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logging.error(f"WebSocket error: {msg.data}")
                        break
            else:
                logging.error("Stocks authentication failed.")


async def crypto_socket():
    """
    @SEE: https://docs.alpaca.markets/docs/real-time-crypto-pr!
    """
    wss_crypto_url = "wss://stream.data.alpaca.markets/v1beta3/crypto/us"
    api_key = os.getenv("APCA_API_KEY_ID")
    api_sec = os.getenv("APCA_API_SECRET_KEY")
    auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(wss_crypto_url) as websocket:
            await websocket.send_str(auth_message)

            response = await websocket.receive_str()
            logging.info(f"Crypto authentication response: {response}")

            try:
                response_data = json.loads(response)
            except json.JSONDecodeError:
                logging.error("Invalid JSON received in the authentication response.")
                return

            if (
                isinstance(response_data, list)
                and response_data[0].get("T") == "success"
            ):
                subscription_message = json.dumps(
                    {
                        "action": "subscribe",
                        "trades": ["*"],
                        "quotes": ["*"],
                        "bars": ["*"],
                        "updatedBars": ["*"],
                        "dailyBars": ["*"],
                        "orderbooks": ["*"],
                    }
                )
                logging.info(
                    "Crypto authentication successful. Connected to the WebSocket."
                )
                await websocket.send_str(subscription_message)

                async for msg in websocket:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = msg.data
                        logging.info(f"Crypto data: {data}")
                        await broadcast(data, "crypto_channel")
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logging.info("Crypto WebSocket connection closed")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logging.error("WebSocket error: {msg.data}")
                        break
            else:
                logging.error("Crypto authentication failed.")


async def main():
    # commented out until I can get the premium again or have a crypto strategy
    # crypto_task = crypto_socket()
    news_task = news_socket()
    stocks_task = stocks_socket()

    await asyncio.gather(news_task, stocks_task)


if __name__ == "__main__":
    asyncio.run(main())
