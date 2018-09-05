import enum
import queue
import traceback
import threading
from lxml import html
import util

SEARCH_ENDPOINT = '/search/sss'


class NotificationMethod(enum.Enum):
    PRINT = enum.auto()
    SLACK = enum.auto()
    FB_MSG = enum.auto()


class QueryNotifier(threading.Thread):

    def __init__(self, pid_queue: queue.Queue, notify_method: NotificationMethod = NotificationMethod.PRINT):
        threading.Thread.__init__(self)
        self.pid_queue = pid_queue
        self.notify_method = notify_method

    def run(self):
        print('Listening for IDs')
        while 1:
            listing_id, feed_url = self.pid_queue.get()
            base_url = util.get_base_url(feed_url)
            details = self.get_listing_info(listing_id, base_url)
            self.notify(details)

    def get_listing_info(listing_id, base_url):
        search_url = base_url + SEARCH_ENDPOINT
        resp = requests.get(params={'query': listing_id})
        page = html.fromstring(resp.content)
        try:
            listing_el = page.cssselect('li.result-row > a[href]')[0]
        except IndexError:
            print('No listings found for pid:', listing_id)
            return None
        listing_url = listing_el.attrib['href']
        listing_resp = requests.get(listing_url)
        listing_page = html.fromstring(listing_resp.content)
        listing_info = self.extract_product_details(listing_page)
        listing_info['url'] = listing_url
        return listing_info

    def extract_product_details(listing_page):
        title = listing_page.get_element_by_id(
            'titletextonly', default='Title Not Found'
        )
        price_elements = listing_page.find_class('price')
        if not price_elements:
            price = 'Price Not Found'
        else:
            price = price_elements[0].text_content()
        try:
            img_url = page.cssselect('[data-imgid] > img')[0].attrib['src']
        except (IndexError, KeyError) as e:
            img_url = 'Images not found'
            traceback.print_exc()
        try:
            location = page.cssselect('.mapaddress')[0].text_content()
        except IndexError:
            location = 'Location not found'
        return {
            'title': title,
            'price': price,
            'img_url': img_url,
            'location': location
        }

    def notify(self, listing_info):
        if self.notify_method == NotificationMethod.PRINT:
            self.notify_print(listing_info)

    def notify_print(self, listing_info):
        msg = """New Listing!
        Title: {title}
        URL: {url}
        Price: {price}
        Location: {location}
        Images: {img_url}
        """
        print(msg)
