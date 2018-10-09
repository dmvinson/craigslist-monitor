from notify import QueryNotifier, NotificationMethod
from monitor import QueryMonitor
import queue
from dispatch import Dispatch
from interface import SlackBot




def main():
    notify_queue = queue.Queue()
    notifier = QueryNotifier(notify_queue, NotificationMethod.SLACK)
    dispatch = Dispatch(notify_queue)
    chat_bot = SlackBot(dispatch.command_queue)
    notifier.start()
    dispatch.start()
    chat_bot.start()

if __name__ == "__main__":
    main()
