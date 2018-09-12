import redis
import asyncio
import queue
from notify import QueryNotifier, NotificationMethod
from monitor import QueryMonitor
from dispatch import Dispatch
from interface import SlackBot




def main():
    notify_queue = queue.Queue()
    notifier = QueryNotifier(notify_queue, NotificationMethod.SLACK)
    notifier.start()
    dispatch = Dispatch(notifier.pid_queue)
    dispatch.run()
    bot = SlackBot()


if __name__ == "__main__":
    main()
