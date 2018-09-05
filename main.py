import redis
import queue
from notify import QueryNotifier, NotificationMethod
from monitor import QueryMonitor

REDIS_DB_NUMBER = 10


def main():
    redis_cli = redis.StrictRedis(db=10)
    notify_queue = queue.Queue()
    notifier = QueryNotifier(notify_queue, NotificationMethod.PRINT)
    notifier.start()
    monitor = QueryMonitor(
        'https://newyork.craigslist.org/search/sss', notify_queue, redis_cli=redis_cli)
    monitor.start()
    monitor.join()


if __name__ == "__main__":
    main()
