import queue
import enum
import redis
import threading

from monitor import QueryMonitor

# TODO: Find better solution for getting types than eval


REDIS_DB_NUMBER = 10

ALL_QUERIES_KEY = 'craigslist query urls'

class Command(enum.Enum):
    ADD = enum.auto()
    REMOVE = enum.auto()

class Dispatch(threading.Thread):

    def __init__(self, notify_queue: queue.Queue):
        threading.Thread.__init__(self)
        self.redis_cli = redis.StrictRedis(db=10)
        self.command_queue = queue.Queue()
        self.notify_queue = notify_queue


        query_urls = self.redis_cli.get(ALL_QUERIES_KEY)
        if query_urls is None:
            self.query_urls = set()
            self.redis_cli.set(ALL_QUERIES_KEY, self.query_urls)
        else:
            self.query_urls = set(eval(query_urls))
        self.active_monitors = []
        self.make_monitors()

    def make_monitors(self):
        for url in self.query_urls:
            qm = QueryMonitor(url, self.notify_queue)
            qm.start()
            self.active_monitors.append(qm)
    
    def run(self):
        while 1:
            command, url = self.command_queue.get()
            if command == Command.ADD:
                self.add_monitor(url)
            elif command == Command.REMOVE:
                print('Removing', url)
                self.remove_monitor(url)

    def add_monitor(self, url):
        monitor = QueryMonitor(url, self.notify_queue)
        monitor.start()
        self.query_urls.add(url)
        self.redis_cli.set(ALL_QUERIES_KEY, self.query_urls)
        self.active_monitors.append(monitor)

    def remove_monitor(self, url):
        for i in range(len(self.active_monitors)):
            if self.active_monitors[i].feed_url == url:
                self.active_monitors[i].stop()
                del self.active_monitors[i]
                break
        else:
            print('No monitor found for', url)
        self.query_urls.remove(url)
        self.redis_cli.set(ALL_QUERIES_KEY, self.query_urls)
        

    
    
    