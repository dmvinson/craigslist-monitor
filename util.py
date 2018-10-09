import re
import urllib.parse


def find_url(text):
    text = text.replace('\\/', '/')
    split = text.split(' ')
    for word in split:
        word = word.strip('<>')
        if word.startswith('http') or word.startswith('https'):
            return word
    return ''

def validate_url(url):
    parsed = urllib.parse.urlparse(url)
    if 'search' not in url:
        return False
    return all([parsed.scheme, parsed.netloc, parsed.path])


def get_base_url(url):
    parsed = urllib.parse.urlparse(url)
    base = '{uri.scheme}://{uri.netloc}'.format(uri=parsed)
    return base
