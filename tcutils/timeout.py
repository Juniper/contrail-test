# From http://stackoverflow.com/questions/2281850/timeout-function-if-it-takes-too-long-to-finish
#
# Usage : 
# with timeout(seconds=3):
#    sleep(4)

from threading import Timer
import thread

from time import sleep

class TimeoutError(Exception):
    pass  

class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
        self.timer = Timer(seconds, self.handle_timeout)

    def handle_timeout(self):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        self.timer.start()

    def __exit__(self, type, value, traceback):
         self.timer.cancel()
