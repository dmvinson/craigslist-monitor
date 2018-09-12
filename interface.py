import asyncio
import os
import slacker
import websockets
import json
from dispatch import Command
from util import find_url, validate_url

slack_token = os.environ['CRAIGSLIST_SLACK_TOKEN']
slack_client = slacker.Slacker(slack_token)

class SlackBot(object):

    def __init__(self, command_queue):
        slack_token = os.environ['CRAIGSLIST_SLACK_TOKEN']
        self.client = slacker.Slacker(slack_token) 
        self.command_queue = command_queue

    async def listen(self):
        resp = self.client.rtm.connect()
        if not resp.successful:
            print('Error connecting to RTM:', resp.error)
            return
        ws_url = resp.body['url']
        async with websockets.connect(ws_url, ssl=True) as ws:
            async for event in ws:
                msg = await self.handle(event)
                if msg is None:
                    continue
                await ws.send(msg)

    async def handle(self, event):
        data = json.loads(event)
        if 'add monitor' in data['text']:
            url = find_url(data['text'])
            if validate_url(url):
                self.command_queue.put((Command.ADD, url)) # sync queue fine as long as infinite capacity
                return 'Added monitor for listings at {}'.format(url)
        elif 'remove monitor' in data['text']:
            url = find_url(data['text'])
            if validate_url(url):
                self.command_queue.put((Command.REMOVE, url))
                return 'Removed monitor for listings at {}'.format(url)
    

    
    