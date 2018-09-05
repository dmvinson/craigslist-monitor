import traceback
import requests
import time
import queue
import redis
from lxml import html


class QueryMonitor(threading.Thread):

    def __init__(self, feed_url: str, notify_queue: queue.Queue, delay: int = 60, redis_cli=None):
        self.feed_url = feed_url
        self.delay = delay
        if redis_cli:
            self.redis_cli = redis_cli

    def monitor(self):
        saved_ids = redis_cli.get(self.feed_url)
        if not saved_ids:
            self.initialize_set()
            time.sleep(self.delay)
        while True:
            current_listings = self.get_listings()
            current_listing_ids = self.get_listing_ids(current_listings)
            new_ids = [
                listing for listing in listing_ids if listing not in saved_ids]
            if new_ids:
                map(self.notify_queue.put, new_ids)
            self.redis_cli.set(self.feed_url, current_listing_ids)
            self.saved_ids = current_listing_ids
            time.sleep(self.delay)

    def initialize_set(self):
        listing_ids = None
        while listing_ids is None:
            listing_ids = self.get_listing_ids(self.get_listings())
        self.redis_cli.set(self.feed_url, listing_ids)

    def get_listings(self):
        page = get_listings_page()
        if not page:
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
        return listing_ids

    def get_listings_page(self):
        try:
            r = requests.get(self.feed_url)
        except requests.exceptions.RequestException:
            traceback.print_exc()
            return None
        return html.fromstring(r.content)
