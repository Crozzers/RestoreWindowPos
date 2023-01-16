import logging
import threading
import time
from abc import ABC, abstractmethod


class Service(ABC):
    def __init__(self, callback, lock=None):
        self.log = logging.getLogger(__name__).getChild(
            self.__class__.__name__).getChild(str(id(self)))
        self._callback = callback
        self._lock = lock or threading.RLock()
        self._kill_signal = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._runner, daemon=True)

        self._thread.start()
        self.log.info('started thread')

    def stop(self, timeout=10):
        self.log.info('send kill signal')
        self._kill_signal.set()

        start = time.time()
        while self._thread.is_alive():
            time.sleep(0.5)
            if timeout is None:
                continue

            if (duration := time.time() - start) > timeout:
                self.log.info(f'kill signal timeout after {duration}s')
                return False

        self.log.info('thread exited')
        return True

    @abstractmethod
    def _runner(self):
        pass

    def pre_callback(self, *args, **kwargs):
        self.log.debug('run pre_callback')

    def callback(self, *args, **kwargs):
        with self._lock:
            self.pre_callback(*args, **kwargs)
            try:
                self.log.debug('run callback')
                self._callback()
            except Exception:
                self.log.exception('callback failed')
                return False
            else:
                self.post_callback(*args, **kwargs)

        return True

    def post_callback(self, *args, **kwargs):
        self.log.debug('run post_callback')
