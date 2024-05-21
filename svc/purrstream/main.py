import asyncio
import json
import os
import time
import websockets

# Global variable to track WebSocket connection status
websocket_connected = False
connected = set()  # a set of websockets for all connected clients


async def alpaca_websocket():
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
                    # asyncio.create_task(prompt_gpt(assistant, thread, data))
                    print(data)
                    print("--------------------------------------------")
                except websockets.ConnectionClosed:
                    print("WebSocket connection closed")
                    websocket_connected = False
                    break
        else:
            print("Authentication failed.")
            websocket_connected = False


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


async def broadcast(message):
    if connected:  # Check if there are any connected clients
        await asyncio.wait([client.send(message) for client in connected])


async def main():
    server_task = websockets.serve(server, "localhost", 8765)
    alpaca_task = alpaca_websocket()

    await asyncio.gather(server_task, alpaca_task)


# Run the asyncio event loop
asyncio.run(main())
