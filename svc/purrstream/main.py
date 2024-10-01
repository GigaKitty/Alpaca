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


async def update_list_periodically(update_interval, websocket):
    while True:
        # @IMP: add a global redis item for this list called skip list
        ticker_list = ["aristocrats_list", "earnings_list", "volatilityvulture_list"]
        logging.debug(f"skip_list: {ticker_list}")
        ticker_list = await get_list(ticker_list)

        logging.info(f"Updating subscription to the following tickers: {ticker_list}")
        subscription_message = json.dumps(
            {
                "action": "subscribe",
                "trades": ticker_list,
                "quotes": ticker_list,
                "bars": ["*"],
                "statuses": ["*"],
            }
        )
        try:
            await websocket.send_str(subscription_message)
            await asyncio.sleep(update_interval)
        except ConnectionResetError:
            # Reconnect logic here
            websocket = await connect_to_websocket()


async def get_list(ticker_list):
    combined_list = []
    ticker_list = sorted(ticker_list)
    try:
        for ticker in ticker_list:
            ticker_item = await redis_client.lindex(ticker, 0)
            if ticker_item:
                combined_list.extend(json.loads(ticker_item))
    except Exception as e:
        logging.error(f"Error fetching latest message from Redis: {e}")
        return None

    # Remove duplicates
    combined_list = list(set(combined_list))
    return combined_list


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


async def account_socket():
    wss_account_url = "wss://paper-api.alpaca.markets/stream"
    api_key = os.getenv("APCA_API_KEY_ID")
    api_sec = os.getenv("APCA_API_SECRET_KEY")
    auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(wss_account_url) as websocket:
            # Send authentication request
            await websocket.send_str(auth_message)

            # Receive authentication response
            response = await websocket.receive()
            if response.type == aiohttp.WSMsgType.TEXT:
                response_text = response.data
            elif response.type == aiohttp.WSMsgType.BINARY:
                response_text = response.data.decode("utf-8")
            else:
                logging.error(f"Unexpected message type: {response.type}")
                return

            logging.info(f"Account authentication response: {response_text}")

            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError:
                logging.error("Invalid JSON received in the authentication response.")
                return

            print(response_data)
            if (
                isinstance(response_data, list)
                and response_data[0].get("T") == "success"
            ):
                subscription_message = json.dumps(
                    {"action": "listen", "data": {"streams": ["trade_updates"]}}
                )
                logging.info(
                    "Trade authentication successful. Connected to the WebSocket."
                )
                await websocket.send_str(subscription_message)
                async for msg in websocket:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = msg.data
                        logging.info(f"Account data: {data}")
                        await broadcast(data, "account_channel")
                    elif msg.type == aiohttp.WSMsgType.BINARY:
                        data = msg.data.decode("utf-8")
                        # logging.info(f"Stocks data: {data}")
                        await broadcast(data, "account_channel")
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logging.info("Account WebSocket connection closed")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logging.error(f"WebSocket error: {msg.data}")
                        break


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
                        "quotes": ["*"],123547
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
                        # logging.info(f"Crypto data: {data}")
                        await broadcast(data, "crypto_channel")
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logging.info("Crypto WebSocket connection closed")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logging.error("WebSocket error: {msg.data}")
                        break
            else:
                logging.error("Crypto authentication failed.")


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
                asyncio.create_task(update_list_periodically(60, websocket))

                async for msg in websocket:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = msg.data
                        # logging.info(f"Stocks data: {data}")
                        await broadcast(data, "stocks_channel")
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logging.info("Stocks WebSocket connection closed")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logging.error(f"WebSocket error: {msg.data}")
                        break
            else:
                logging.error("Stocks authentication failed.")


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
                        # logging.info(f"News data: {data}")
                        await broadcast(data, "news_channel")
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        logging.info("News WebSocket connection closed")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logging.error(f"WebSocket error: {msg.data}")
                        break
            else:
                logging.error("News authentication failed.")


async def main():
    account_task = account_socket()
    crypto_task = crypto_socket()
    news_task = news_socket()
    stocks_task = stocks_socket()

    await asyncio.gather(account_task, crypto_task, news_task, stocks_task)


if __name__ == "__main__":
    asyncio.run(main())
