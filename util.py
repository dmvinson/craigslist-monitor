import urllib.parse


def get_base_url(url):
    parsed = urllib.parse.urlparse(url)
    base = '{uri.scheme}://{uri.netloc}'.format(uri=parsed)
    return base
