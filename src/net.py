"""Network helper: a sequential reader of a large remote file that survives dropped connections."""
from __future__ import annotations

import io
import time
import urllib.request


class ResumingStream(io.RawIOBase):
    """Sequential reader of a remote file that reconnects with an HTTP Range request when the
    connection drops (it did, often, on the machine used here), so the stream has no gap.
    Wrap it in io.BufferedReader and give it to tarfile in stream mode ("r|gz", "r|*")."""

    def __init__(self, url: str, retries: int = 200):
        self.url, self.pos, self.retries, self.resp = url, 0, retries, None
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as r:
            self.size = int(r.headers["Content-Length"])

    def _open(self):
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-"})
        self.resp = urllib.request.urlopen(req, timeout=120)

    def readable(self):
        return True

    def readinto(self, b):
        if self.pos >= self.size:
            return 0
        for attempt in range(self.retries):
            try:
                if self.resp is None:
                    self._open()
                n = self.resp.readinto(b)
                if n:
                    self.pos += n
                    return n
                raise ConnectionError("empty read before the end of the file")
            except Exception as e:  # noqa: BLE001 - any network error: reconnect at self.pos
                print(f"  connection lost at byte {self.pos:,} ({e!r}); reconnecting", flush=True)
                self.resp = None
                time.sleep(min(60, 2 ** attempt))
        raise ConnectionError(f"gave up after {self.retries} reconnects at byte {self.pos}")
