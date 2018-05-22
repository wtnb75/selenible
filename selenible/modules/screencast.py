import io
import time
import threading
from logging import getLogger
from PIL import Image


class screencast(threading.Thread):
    def __init__(self, drvobj, crop, interval=1.0, thumbnail=None):
        super().__init__()
        self.drvobj = drvobj
        if crop is None:
            self.crop = crop
        else:
            self.crop = tuple(crop)
        self.thumbnail = thumbnail
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
                self.log.info("shot: %d bytes, %f sec", len(p), time.time() - t1)
            if len(p) != 0:
                img = Image.open(io.BytesIO(p))
                if self.crop is not None:
                    self.log.info("crop %s, %f sec", self.crop, time.time() - t1)
                    img = img.crop(self.crop)
                if self.thumbnail is not None:
                    img.thumbnail(self.thumbnail, Image.ANTIALIAS)
                self.frames.append(img)
            td = time.time() - t1
            if self.interval is not None and self.interval > td:
                self.log.info("sleep %f - %f", self.interval, td)
                time.sleep(self.interval - td)
        self.finished_ts = time.time()

    def savefile(self, output_fn, optimize=False, loop=0, speed=1.0):
        if len(self.frames) == 0:
            raise Exception("no image found")
        d = 1000 * (self.finished_ts - self.start_ts) / len(self.frames) / speed
        self.log.info("%d frames, %d sec. duration=%f(ms)", len(
            self.frames), self.finished_ts - self.start_ts, d)
        self.frames[0].save(output_fn, save_all=True, duration=d, optimize=optimize,
                            loop=loop, append_images=self.frames[1:])


scr_th = None


def Base_screencast(self, param):
    """
    - name: start screencast
      screencast:
        interval: 0.5
        thumbnail: [100, 100]
    - name: sleep
      sleep: 3
    - name: save screencast
      screencast: output.gif
    """
    global scr_th
    if isinstance(param, dict) and "output" not in param:
        if scr_th is not None:
            raise Exception("screencast already working")
        scr_th = screencast(self, param.get("crop"), param.get("interval"),
                            param.get("thumbnail"))
        scr_th.start()
        return "started"
    if scr_th is None:
        raise Exception("screencast is not working")
    self.log.debug("stop cast")
    scr_th.stop = True
    scr_th.join(2)
    if scr_th.is_alive():
        self.log.warn("cannot stop screencast thread.")
    else:
        self.log.debug("done join. saving")
    if isinstance(param, str):
        self.log.info("save to %s", param)
        scr_th.savefile(param)
    elif isinstance(param, dict):
        output = param.get("output")
        assert output is not None
        self.log.info("save to %s", output)
        scr_th.savefile(output,
                        optimize=param.get("optimize", False),
                        loop=param.get("loop", 0),
                        speed=param.get("speed", 1.0))
    scr_th = None
    return "finished"
