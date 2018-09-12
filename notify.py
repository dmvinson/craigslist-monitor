import enum
import json
import os
import queue
import re
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

IMG_DATA_REGEXP = r"imgList = (.*?);"


class NotificationMethod(enum.Enum):
    PRINT = enum.auto()
    SLACK = enum.auto()
    FB_MSG = enum.auto()


slack_token = os.environ['CRAIGSLIST_SLACK_TOKEN']
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
    print('Notification info:', listing_info)
    buttons = make_buttons_image_urls(listing_info['img_url'])
    buttons.insert(
        0, {'type': 'button', 'text': 'View Listing',
            'url': listing_info['url']}
    )
    attachments = [
        {
            'title': listing_info['title'],
            'title_link': listing_info['url'],
            'color': '#800080',
            'pretext': 'New Listing!',
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
    if 'attribs' in listing_info:
        attachments[0]['text'] = listing_info['attribs']
    if isinstance(listing_info['img_url'], list) and listing_info['img_url']:
        attachments[0]['image_url'] = listing_info['img_url'][0]
    elif isinstance(listing_info['img_url'], str) and listing_info['img_url'] != 'N/A':
        attachments[0]['image_url'] = listing_info['img_url']
    slack_client.chat.post_message('#general', attachments=attachments)


def make_buttons_image_urls(img_urls):
    if isinstance(img_urls, list):
        img_buttons = []
        for i, val in enumerate(img_urls):
            action_data = {
                'type': 'button',
                'text': "Image {}".format(str(i+1)),
                'url': val
            }
            img_buttons.append(action_data)
        return img_buttons
    return {
        'type': 'button',
        'text': 'Main Image',
        'url': img_urls
    }


def extract_product_details(listing_page):
    info = {}
    try:
        title_el = listing_page.get_element_by_id('titletextonly')
        title = title_el.text_content()
    except KeyError:
        title = 'Title Not Found'
    info['title'] = title
    price_elements = listing_page.find_class('price')
    if not price_elements:
        price = 'N/A'
    else:
        price = price_elements[0].text_content()
    info['price'] = price
    try:
        for tag in listing_page.cssselect('script'):
            if 'imgList' in tag.text_content():
                break
        data_str = re.search(IMG_DATA_REGEXP, tag.text_content())[1]
        data = json.loads(data_str)
        img_url = [img['url'] for img in data]
    except (IndexError, KeyError) as e:
        img_url = 'N/A'
    info['img_url'] = img_url
    try:
        location = listing_page.cssselect('span.postingtitletext > small')
        if not location:
            location = listing_page.cssselect('div.mapaddress')
        location = location[0].text_content().strip(' ()')
    except IndexError:
        location = 'Location not found'
    info['location'] = location
    attribs = parse_attributes(listing_page)
    if attribs:
        info['attribs'] = attribs
    return info


def parse_attributes(listing_page):
    attr_elements = listing_page.cssselect('p.attrgroup > span')
    for a in attr_elements:
        if a.cssselect('span.otherpostings'):  # Remove 'more ads by this user' text
            attr_elements.remove(a)
    if attr_elements:
        return '\n'.join([a.text_content().strip() for a in attr_elements])
    return ''
