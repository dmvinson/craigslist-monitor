import asyncio
import json
import os
import threading

import slacker
import websocket

import config
from dispatch import Command
from util import find_url, validate_url


class SlackBot(threading.Thread):

    def __init__(self, command_queue):
        threading.Thread.__init__(self)
        slack_token = config.CRAIGSLIST_SLACK_TOKEN
        self.client = slacker.Slacker(slack_token)
        self.command_queue = command_queue

    def run(self):
        self.listen()

    def listen(self):
        print('Connecting RTM')
        resp = self.client.rtm.connect()
        if not resp.successful:
            print('Error connecting to RTM:', resp.error)
            return
        print(resp.body['url'])
        ws_url = resp.body['url']
        print('Connecting websocket')
        ws = websocket.WebSocketApp(
            ws_url, on_message=self.on_msg,
            on_error=self.on_error,
            on_close=self.on_close
        )
        ws.run_forever()

    def on_msg(self, ws, msg):
        data = json.loads(msg)
        print(msg)
        if 'add monitor' in data['text']:
            print('add command')
            url = find_url(data['text'])
            if validate_url(url):
                # sync queue fine as long as infinite capacity
                print('Added monitor for listings at {}'.format(url))
                self.command_queue.put((Command.ADD, url))
        elif 'remove monitor' in data['text']:
            print('remove command')
            url = find_url(data['text'])
            if validate_url(url):
                print('Removed monitor for listings at {}'.format(url))
                self.command_queue.put((Command.REMOVE, url))

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws):
        print('Socket closed')
