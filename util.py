import re
import urllib.parse


def find_url(text):
    split = text.split('')
    for word in split:
        if word.startswith('http') or word.startswith('https'):
            return word
    return ''

def validate_url(url):
    parsed = urllib.parse.urlparse(url)
    return all([parsed.scheme, parsed.netloc, parsed.path])


def get_base_url(url):
    parsed = urllib.parse.urlparse(url)
    base = '{uri.scheme}://{uri.netloc}'.format(uri=parsed)
    return base
