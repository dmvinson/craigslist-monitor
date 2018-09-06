import enum
import os
import queue
import threading
import traceback

import requests
import slacker
from lxml import html

import util

SEARCH_ENDPOINT = '/search/sss'

TEXT_MSG = """New Listing!
Title: {title}
URL: {url}
Price: {price}
Location: {location}
Images: {img_url}
"""


class NotificationMethod(enum.Enum):
    PRINT = enum.auto()
    SLACK = enum.auto()
    FB_MSG = enum.auto()


slack_token = os.environ('CRAIGSLIST_SLACK_TOKEN')
slack_client = slacker.Slacker(slack_token)


class QueryNotifier(threading.Thread):

    def __init__(self, pid_queue: queue.Queue, notify_method: NotificationMethod = NotificationMethod.PRINT):
        threading.Thread.__init__(self)
        self.pid_queue = pid_queue
        self.notify_method = notify_method

    def run(self):
        print('Listening for IDs')
        while 1:
            listing_id, feed_url = self.pid_queue.get()
            print('Notifying for', listing_id, feed_url)
            base_url = util.get_base_url(feed_url)
            details = self.get_listing_info(listing_id, base_url)
            self.notify(details)

    def get_listing_info(self, listing_id, base_url):
        search_url = base_url + SEARCH_ENDPOINT
        resp = requests.get(search_url, params={'query': listing_id})
        page = html.fromstring(resp.content)
        try:
            listing_el = page.cssselect('li.result-row > a[href]')[0]
        except IndexError:
            print('No listings found for pid:', listing_id)
            return None
        listing_url = listing_el.attrib['href']
        listing_resp = requests.get(listing_url)
        listing_page = html.fromstring(listing_resp.content)
        listing_info = extract_product_details(listing_page)
        listing_info['url'] = listing_url
        return listing_info

    def notify(self, listing_info):
        if self.notify_method == NotificationMethod.PRINT:
            self.notify_print(listing_info)
        elif self.notify_method == NotificationMethod.SLACK:
            notify_slack(listing_info)

    def notify_print(self, listing_info):
        msg = TEXT_MSG.format(**listing_info)
        print(msg)


def notify_slack(listing_info):
    buttons = make_buttons_image_urls(listing_info['img_url'])
    buttons.insert(
        0, {'type': 'button', 'text': 'View Listing',
            'url': listing_info['url']}
    )
    attachments = [
        {
            'title': listing_info['title'],
            'title_link': listing_info['url'],
            'image_url': listing_info['img_url'] if isinstance(listing_info['img_url'], str) else listing_info['img_url'][0],
            'fields': [
                {
                    'title': 'Price',
                    'value': listing_info['price'],
                    'short': True
                },
                {
                    'title': 'Location',
                    'value': listing_info['location'],
                    'short': True
                }
            ],
            'actions': buttons,
            'footer': 'Craigslist Monitor'
        }
    ]
    slack_client.chat.post_message('#general', attachments=attachments)


def make_buttons_image_urls(img_urls):
    if isinstance(img_urls, list):
        img_buttons = []
        for i in range(0, len(img_urls)):
            action_data = {
                'type': 'button',
                'text': "Image {}".format(str(i+1)),
                'url': img_urls[i]
            }
            img_buttons.append(action_data)
        return [img_buttons]
    return [{
        'type': 'button',
        'text': 'Main Image',
        'url': img_urls
    }]


def extract_product_details(listing_page):
    try:
        title_el = listing_page.get_element_by_id('titletextonly')
        title = title_el.text_content()
    except KeyError:
        title = 'Title Not Found'
    price_elements = listing_page.find_class('price')
    if not price_elements:
        price = 'N/A'
    else:
        price = price_elements[0].text_content()
    try:
        img_url = listing_page.cssselect(
            '[data-imgid] > img')[0].attrib['src']
    except (IndexError, KeyError) as e:
        img_url = 'N/A'
    try:
        location = listing_page.cssselect('div.mapaddress')[0].text_content()
    except IndexError:
        location = 'Location not found'
    return {
        'title': title,
        'price': price,
        'img_url': img_url,
        'location': location
    }
