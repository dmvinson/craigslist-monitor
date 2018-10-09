import queue
import threading
import time
import traceback

import redis
import requests
from lxml import html

# TODO: Find better solution for getting types than eval


class QueryMonitor(threading.Thread):

    def __init__(self, feed_url: str, notify_queue: queue.Queue, delay: int = 60, redis_cli=None):
        threading.Thread.__init__(self)
        self.feed_url = feed_url
        self.delay = delay
        if redis_cli:
            self.redis_cli = redis_cli
        else:
            self.redis_cli = redis.StrictRedis()
        self.notify_queue = notify_queue
        self.saved_ids = None
        self.stopped = False

    def run(self):
        print('Starting monitor for:', self.feed_url)
        saved_ids = self.redis_cli.get(self.feed_url)
        if not saved_ids:
            self.initialize_set()
            saved_ids = self.redis_cli.get(self.feed_url)
            time.sleep(self.delay)
        saved_ids = set(eval(saved_ids))
        while not self.stopped:
            current_listings = self.get_listings()
            if current_listings is None:
                time.sleep(self.delay/5)
                continue
            current_listing_ids = self.get_listing_ids(current_listings)
            new_ids = [
                listing for listing in current_listing_ids if listing not in saved_ids
            ]
            if new_ids:
                for i in new_ids:
                    self.notify_queue.put((i, self.feed_url))
            else:
                print('No new listings added')
            self.redis_cli.set(self.feed_url, current_listing_ids)
            self.saved_ids = current_listing_ids
            time.sleep(self.delay)
        print('Ending monitor for', self.feed_url)

    def initialize_set(self):
        print('Initializing DB')
        listing_ids = None
        while listing_ids is None:
            listing_ids = self.get_listing_ids(self.get_listings())
        self.redis_cli.set(self.feed_url, listing_ids)
        print('Starting with IDs')
        print(listing_ids)

    def get_listings(self):
        page = self.get_listings_page()
        if page is None:
            return None
        listings = page.cssselect('li.result-row')
        return listings

    def get_listing_ids(self, listings):
        listing_ids = set()
        for l in listings:
            try:
                listing_ids.add(l.attrib['data-pid'])
            except KeyError:
                continue
        print(listings[0].attrib['data-pid'])
        return listing_ids

    def get_listings_page(self):
        try:
            r = requests.get(self.feed_url)
        except requests.exceptions.RequestException:
            traceback.print_exc()
            return None
        return html.fromstring(r.content)
    
    def stop(self):
        self.stopped = True
