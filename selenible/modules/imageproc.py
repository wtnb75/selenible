import os
import time
import math
from PIL import Image, ImageChops, ImageFilter, ImageEnhance, ImageFont, ImageDraw, ImageColor


def inout_fname(param):
    input_filename = param.get("input")
    output_filename = param.get("output", input_filename)
    if input_filename is None or output_filename is None:
        raise Exception("please set input and output: %s" % (param))
    return input_filename, output_filename


def Base_image_crop(self, param):
    input_filename, filename = inout_fname(param)
    if filename is None:
        # generate filename
        ts = time.time()
        msec = math.modf(ts)[0] * 1000
        filename = param.get("prefix", "")
        filename += time.strftime("%Y%m%d_%H%M%S", time.localtime(ts))
        filename += "_%03d.png" % (msec)
        self.log.debug("filename generated %s", filename)
    size = param.get("size", "auto")
    if size == "auto":
        img = Image.open(input_filename)
        bg = Image.new(img.mode, img.size, img.getpixel((0, 0)))
        diff = ImageChops.difference(img, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        box = diff.getbbox()
        self.log.info("auto crop: %s", box)
        crop = img.crop(box)
        crop.save(filename)
    elif isinstance(size, (tuple, list)):
        img = Image.open(input_filename)
        self.log.info("manual crop: %s", size)
        crop = img.crop(size)
        crop.save(filename)
    else:
        raise Exception("not implemented yet: crop %s %s" % (filename, size))


def Base_image_optimize(self, param):
    input_filename, filename = inout_fname(param)
    command = param.get("command", "optipng")
    self.log.info("optimize image: %s -> %s", input_filename, filename)
    before = os.stat(input_filename)
    if before.st_size == 0:
        raise Exception("image size is zero: %s" % (input_filename))
    if filename != input_filename:
        cmd = [command, "-o9", "-out", filename, input_filename]
    else:
        cmd = [command, "-o9", filename]
    sout = self.runcmd(cmd)
    self.log.debug("result: %s", sout)
    after = os.stat(filename)
    self.log.info("%s: before=%d, after=%d, reduce %d bytes (%.1f %%)", filename,
                  before.st_size, after.st_size, before.st_size - after.st_size,
                  100.0 * (before.st_size - after.st_size) / before.st_size)


def Base_image_resize(self, param):
    input_filename, filename = inout_fname(param)
    base, ext = os.path.splitext(filename)
    if ext not in (".png", ".PNG"):
        self.log.info("non-png: %s ...pass", filename)
        return
    self.log.info("resize image: %s %s -> %s", input_filename, param, filename)
    img = Image.open(input_filename)
    size = param.get("size")
    if size is None:
        raise Exception("missing size: [x, y, width, height]")
    rst = img.resize(tuple(size))
    rst.save(filename)


def Base_image_writetext(self, param):
    text = self.getvalue(param)
    input_filename, filename = inout_fname(param)
    pos = param.get("position", (0, 0))
    fontname = param.get("font")
    fontsize = param.get("size", 10)
    color = param.get("color", "red")
    if fontname is None:
        font = ImageFont.load_default()
    else:
        font = ImageFont.truetype(fontname, size=fontsize)
    img = Image.open(input_filename)
    draw = ImageDraw.Draw(img)
    fillcolor = ImageColor.getcolor(color)
    draw.text(tuple(pos), text, fill=fillcolor, font=font)
    del draw
    img.save(filename)


def Base_image_filter(self, param):
    """
    - name: image filter
      image_filter:
        input: input.png
        output: output.png
        filter:
          - ModeFilter: 12
          - GaussianBlur: 5
          - ModeFilter: 12
          - GaussianBlur: 1
    """
    input_filename, filename = inout_fname(param)
    img = Image.open(input_filename)
    for f in param.get("filter", []):
        if not isinstance(f, dict):
            raise Exception("invalid parameter: %s" % (f))
        for k, v in f.items():
            fn = getattr(ImageFilter, k)
            if not callable(fn):
                raise Exception("filter %s(%s) not found" % (k, v))
            self.log.debug("filter %s %s", k, v)
            if v is None:
                img = img.filter(fn)
            elif isinstance(v, (tuple, list)):
                img = img.filter(fn(*v))
            elif isinstance(v, dict):
                img = img.filter(fn(**v))
            else:
                img = img.filter(fn(v))
    img.save(filename)


def Base_image_convert(self, param):
    input_filename, filename = inout_fname(param)
    img = Image.open(input_filename)
    mode = param.get("mode")
    if mode is None:
        raise Exception("invalid parameter: %s" % (param))
    img = img.convert(mode)
    img.save(filename)


def Base_image_chops(self, param):
    input_filename, filename = inout_fname(param)
    img = Image.open(input_filename)
    for f in param.get("filter"):
        if not isinstance(f, dict):
            raise Exception("invalid parameter: %s" % (param))
        for k, v in f.items():
            fn = getattr(ImageChops, k)
            if not callable(fn):
                raise Exception("chop %s(%s) not found" % (k, v))
            self.log.debug("chop %s %s", k, v)
            if isinstance(v, (list, tuple)):
                fname = v[0]
                args = v[1:]
            else:
                fname = v
                args = []
            img2 = Image.open(fname)
            img = fn(img, img2, *args)
    img.save(filename)


def Base_image_enhance(self, param):
    input_filename, filename = inout_fname(param)
    img = Image.open(input_filename)
    for f in param.get("filter"):
        if not isinstance(f, dict):
            raise Exception("invalid parameter: %s" % (param))
        for k, v in f.items():
            fn = getattr(ImageEnhance, k)
            if not callable(fn):
                raise Exception("enhance %s(%s) not found" % (k, v))
            self.log.debug("enhance %s %s", k, v)
            enhancer = fn(img)
            img = enhancer.enhance(v)
    img.save(filename)
