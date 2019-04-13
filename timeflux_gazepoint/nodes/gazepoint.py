"""timeflux.nodes.gazepoint: Gazepoint driver"""

from timeflux.core.node import Node
from timeflux.helpers.clock import now
from threading import Thread, Lock
from time import sleep, perf_counter
import logging
import socket
import re

class Gazepoint(Node):

    """Gazepoint eye tracker driver.

    Attributes:
        o (Port): Default output, provides DataFrame.
    """

    def __init__(self, host='127.0.0.1', port=4242, enable=None):
        """
        Args:
            host (string): IP address or hostname to listen to. Default: `127.0.0.1`.
            port (int): TCP port to listen to. Default: `4242`.
            enable (list): Channels to enable. Default: `None`.
        """

        if enable is None:
            enable = [
                'POG_FIX',
                'POG_LEFT',
                'POG_RIGHT',
                'POG_BEST',
                'PUPIL_LEFT',
                'PUPIL_RIGHT',
                'EYE_LEFT',
                'EYE_RIGHT',
                'CURSOR',
                'BLINK',
            ]
        always_enable = [
            'COUNTER',
            'TIME',
            'TIME_TICK',
            'DATA'
        ]
        enable = enable + always_enable
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((host, port))
        for key in enable:
            self._socket.send(str.encode('<SET ID="ENABLE_SEND_' + key + '" STATE="1" />\r\n'))
        self._reset()
        self._regex = re.compile(r'( ([A-Z]+)="(.*?)")')
        self._lock = Lock()
        Thread(target=self._loop).start()

    def _reset(self):
        self._rows = []
        self._timestamps = []

    def _loop(self):
        while True:
            with self._lock:
                data = self._socket.recv(1024)
                data = bytes.decode(data)
                data = data.split('\r\n')
                for line in data:
                    if line.startswith('<REC'):
                        row = {}
                        values = self._regex.findall(line)
                        for value in values:
                            row[value[1]] = float(value[2])
                        if len(row) > 0:
                            self._timestamps.append(now())
                            self._rows.append(row)
                sleep(.001) # be nice

    def update(self):
        with self._lock:
            if self._rows:
                self.o.set(self._rows, self._timestamps)
            self._reset()
