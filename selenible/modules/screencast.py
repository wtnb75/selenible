import io
import time
import threading
from logging import getLogger
from PIL import Image


class screencast(threading.Thread):
    def __init__(self, drvobj, crop, interval=1.0):
        super().__init__()
        self.drvobj = drvobj
        if crop is None:
            self.crop = crop
        else:
            self.crop = tuple(crop)
        self.log = getLogger(self.name)
        self.stop = False
        self.interval = interval
        self.frames = []

    def run(self):
        self.start_ts = time.time()
        while not self.stop:
            t1 = time.time()
            with self.drvobj.lock:
                p = self.drvobj.driver.get_screenshot_as_png()
            self.log.info("shot: %d bytes", len(p))
            if len(p) != 0:
                img = Image.open(io.BytesIO(p))
                if self.crop is not None:
                    self.log.info("crop %s", self.crop)
                    img = img.crop(self.crop)
                self.frames.append(img)
            td = time.time() - t1
            if self.interval is not None and self.interval > td:
                self.log.info("sleep %f - %f", self.interval, td)
                time.sleep(self.interval - td)
        self.finished_ts = time.time()

    def savefile(self, output_fn, optimize=False, loop=0):
        if len(self.frames) == 0:
            raise Exception("no image found")
        d = 1000 * (self.finished_ts - self.start_ts) / len(self.frames)
        self.log.info("%d frames, %d sec. duration=%f(ms)", len(
            self.frames), self.finished_ts - self.start_ts, d)
        self.frames[0].save(output_fn, save_all=True, duration=d, optimize=optimize,
                            loop=loop, append_images=self.frames[1:])


scr_th = None


def Base_screencast(self, param):
    """
    - name: start screencast
      screencast:
        crop: [100, 100, 200, 200]
        interval: 0.5
    - name: sleep
      sleep: 3
    - name: save screencast
      screencast: output.gif
    """
    global scr_th
    if isinstance(param, str):
        if scr_th is None:
            raise Exception("screencast not worked")
        scr_th.stop = True
        scr_th.join()
        scr_th.savefile(param)
        del scr_th
        scr_th = None
    elif isinstance(param, dict):
        output = param.get("output")
        if output is not None:
            if scr_th is None:
                raise Exception("screencast not worked")
            scr_th.stop = True
            scr_th.join()
            scr_th.savefile(output,
                            optimize=param.get("optimize", False),
                            loop=param.get("loop", 0))
            del scr_th
            scr_th = None
        else:
            if scr_th is not None:
                raise Exception("screencast already working")
            scr_th = screencast(self, param.get("crop"), param.get("interval"))
            scr_th.start()
