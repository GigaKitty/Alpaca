import asyncio
import json
import os
import websockets

# Global variables to track WebSocket connection status
news_websocket_connected = False
stocks_websocket_connected = False
crypto_websocket_connected = False
connected = set()  # a set of websockets for all connected clients


async def news_socket():
    global news_websocket_connected
    wss_news_url = "wss://stream.data.alpaca.markets/v1beta1/news"
    async with websockets.connect(wss_news_url) as websocket:
        api_key = os.getenv("APCA_API_KEY_ID")
        api_sec = os.getenv("APCA_API_SECRET_KEY")
        auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

        await websocket.send(auth_message)

        response = await websocket.recv()
        print(f"News authentication response: {response}")

        try:
            response_data = json.loads(response)
        except json.JSONDecodeError:
            print("Invalid JSON received in the authentication response.")
            return

        if isinstance(response_data, list) and response_data[0].get("T") == "success":
            subscription_message = json.dumps({"action": "subscribe", "news": ["*"]})
            print("News authentication successful. Connected to the WebSocket.")
            news_websocket_connected = True
            await websocket.send(subscription_message)

            while True:
                try:
                    data = await websocket.recv()
                    print(f"News data: {data}")
                    await broadcast(data)
                    print("--------------------------------------------")
                except websockets.ConnectionClosed:
                    print("News WebSocket connection closed")
                    news_websocket_connected = False
                    break
        else:
            print("News authentication failed.")
            news_websocket_connected = False


async def stocks_socket():
    global stocks_websocket_connected
    wss_stocks_url = "wss://stream.data.alpaca.markets/v2/sip"
    async with websockets.connect(wss_stocks_url) as websocket:
        api_key = os.getenv("APCA_API_KEY_ID")
        api_sec = os.getenv("APCA_API_SECRET_KEY")
        auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

        await websocket.send(auth_message)

        response = await websocket.recv()
        print(f"Stocks authentication response: {response}")

        try:
            response_data = json.loads(response)
        except json.JSONDecodeError:
            print("Invalid JSON received in the authentication response.")
            return

        if isinstance(response_data, list) and response_data[0].get("T") == "success":
            subscription_message = json.dumps(
                {
                    "action": "subscribe",
                    "trades": ["*"],
                    "quotes": ["*"],
                    "bars": ["*"],
                    "statuses": ["*"],
                }
            )
            print("Stocks authentication successful. Connected to the WebSocket.")
            stocks_websocket_connected = True
            await websocket.send(subscription_message)

            while True:
                try:
                    data = await websocket.recv()
                    print(f"Stocks data: {data}")
                    await broadcast(data)
                    print("--------------------------------------------")
                except websockets.ConnectionClosed:
                    print("Stocks WebSocket connection closed")
                    stocks_websocket_connected = False
                    break
        else:
            print("Stocks authentication failed.")
            stocks_websocket_connected = False


async def crypto_socket():
    global crypto_websocket_connected
    wss_crypto_url = "wss://stream.data.alpaca.markets/v1beta3/crypto/us"
    async with websockets.connect(wss_crypto_url) as websocket:
        api_key = os.getenv("APCA_API_KEY_ID")
        api_sec = os.getenv("APCA_API_SECRET_KEY")
        auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

        await websocket.send(auth_message)

        response = await websocket.recv()
        print(f"Crypto authentication response: {response}")

        try:
            response_data = json.loads(response)
        except json.JSONDecodeError:
            print("Invalid JSON received in the authentication response.")
            return

        if isinstance(response_data, list) and response_data[0].get("T") == "success":
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

            print("Crypto authentication successful. Connected to the WebSocket.")
            crypto_websocket_connected = True
            await websocket.send(subscription_message)

            while True:
                try:
                    data = await websocket.recv()
                    print(f"Crypto data: {data}")
                    await broadcast(data)
                    print("--------------------------------------------")
                except websockets.ConnectionClosed:
                    print("Crypto WebSocket connection closed")
                    crypto_websocket_connected = False
                    break
        else:
            print("Crypto authentication failed.")
            crypto_websocket_connected = False


async def server(websocket, path):
    # Register websocket connection
    connected.add(websocket)
    try:
        while True:
            message = (
                await websocket.recv()
            )  # server also needs to receive to maintain connection
            print("Received by server from a client:", message)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Unregister
        connected.remove(websocket)

        connected_clients = set()


async def handle_connection(websocket, path):
    logging.info("New client connected")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            logging.info(f"Received message from client: {message}")
            # Broadcast message to all connected clients
            await broadcast(message)
    except websockets.ConnectionClosed:
        logging.info("Client disconnected")
    finally:
        connected_clients.remove(websocket)


async def broadcast(message):
    if connected:  # Check if there are any connected clients
        await asyncio.wait([client.send(message) for client in connected])


async def main():
    server_task = websockets.serve(server, "0.0.0.0", 8765)
    news_task = news_socket()
    stocks_task = stocks_socket()
    crypto_task = crypto_socket()

    await asyncio.gather(server_task, news_task, stocks_task, crypto_task)


# Run the asyncio event loop
asyncio.run(main())
