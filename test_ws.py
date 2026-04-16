import asyncio
import websockets

async def main():
    uri = 'ws://localhost:8000/ws/detect'
    async with websockets.connect(uri) as websocket:
        print('Connected')
        await websocket.send('calibrate')
        for i in range(3):
            msg = await websocket.recv()
            print('Received:', msg[:50])
        print('Closing')

asyncio.run(main())
