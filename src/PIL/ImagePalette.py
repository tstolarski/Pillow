#
# The Python Imaging Library.
# $Id$
#
# image palette object
#
# History:
# 1996-03-11 fl   Rewritten.
# 1997-01-03 fl   Up and running.
# 1997-08-23 fl   Added load hack
# 2001-04-16 fl   Fixed randint shadow bug in random()
#
# Copyright (c) 1997-2001 by Secret Labs AB
# Copyright (c) 1996-1997 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

import array

from . import GimpGradientFile, GimpPaletteFile, ImageColor, PaletteFile


class ImagePalette:
    """
    Color palette for palette mapped images

    :param mode: The mode to use for the Palette. See:
        :ref:`concept-modes`. Defaults to "RGB"
    :param palette: An optional palette. If given, it must be a bytearray,
        an array or a list of ints between 0-255 and of length ``size``
        times the number of colors in ``mode``. The list must be aligned
        by channel (All R values must be contiguous in the list before G
        and B values.) Defaults to 0 through 255 per channel.
    :param size: An optional palette size. If given, it cannot be equal to
        or greater than 256. Defaults to 0.
    """

    def __init__(self, mode="RGB", palette=None, size=0):
        self.mode = mode
        self.rawmode = None  # if set, palette contains raw data
        self.palette = palette or bytearray(range(256)) * len(self.mode)
        self.dirty = None
        if (size == 0 and len(self.mode) * 256 != len(self.palette)) or (
            size != 0 and size != len(self.palette)
        ):
            raise ValueError("wrong palette size")

    @property
    def palette(self):
        return self._palette

    @palette.setter
    def palette(self, palette):
        self._palette = palette

        mode_len = len(self.mode)
        self.colors = {
            tuple(self.palette[i : i + mode_len]): i // mode_len
            for i in range(0, len(self.palette), mode_len)
        }

    def copy(self):
        new = ImagePalette()

        new.mode = self.mode
        new.rawmode = self.rawmode
        if self.palette is not None:
            new.palette = self.palette[:]
        new.dirty = self.dirty

        return new

    def getdata(self):
        """
        Get palette contents in format suitable for the low-level
        ``im.putpalette`` primitive.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            return self.rawmode, self.palette
        return self.mode + ";L", self.tobytes()

    def tobytes(self):
        """Convert palette to bytes.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            raise ValueError("palette contains raw palette data")
        if isinstance(self.palette, bytes):
            return self.palette
        arr = array.array("B", self.palette)
        if hasattr(arr, "tobytes"):
            return arr.tobytes()
        return arr.tostring()

    # Declare tostring as an alias for tobytes
    tostring = tobytes

    def getcolor(self, color):
        """Given an rgb tuple, allocate palette entry.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            raise ValueError("palette contains raw palette data")
        if isinstance(color, tuple):
            try:
                return self.colors[color]
            except KeyError as e:
                # allocate new color slot
                if isinstance(self.palette, bytes):
                    self._palette = bytearray(self.palette)
                index = len(self.colors)
                if index >= 256:
                    raise ValueError("cannot allocate more than 256 colors") from e
                self.colors[color] = index
                self._palette[index] = color[0]
                self._palette[index + 256] = color[1]
                self._palette[index + 512] = color[2]
                self.dirty = 1
                return index
        else:
            raise ValueError(f"unknown color specifier: {repr(color)}")

    def save(self, fp):
        """Save palette to text file.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            raise ValueError("palette contains raw palette data")
        if isinstance(fp, str):
            fp = open(fp, "w")
        fp.write("# Palette\n")
        fp.write(f"# Mode: {self.mode}\n")
        for i in range(256):
            fp.write(f"{i}")
            for j in range(i * len(self.mode), (i + 1) * len(self.mode)):
                try:
                    fp.write(f" {self.palette[j]}")
                except IndexError:
                    fp.write(" 0")
            fp.write("\n")
        fp.close()


# --------------------------------------------------------------------
# Internal


def raw(rawmode, data):
    palette = ImagePalette()
    palette.rawmode = rawmode
    palette.palette = data
    palette.dirty = 1
    return palette


# --------------------------------------------------------------------
# Factories


def make_linear_lut(black, white):
    lut = []
    if black == 0:
        for i in range(256):
            lut.append(white * i // 255)
    else:
        raise NotImplementedError  # FIXME
    return lut


def make_gamma_lut(exp):
    lut = []
    for i in range(256):
        lut.append(int(((i / 255.0) ** exp) * 255.0 + 0.5))
    return lut


def negative(mode="RGB"):
    palette = list(range(256))
    palette.reverse()
    return ImagePalette(mode, palette * len(mode))


def random(mode="RGB"):
    from random import randint

    palette = []
    for i in range(256 * len(mode)):
        palette.append(randint(0, 255))
    return ImagePalette(mode, palette)


def sepia(white="#fff0c0"):
    r, g, b = ImageColor.getrgb(white)
    r = make_linear_lut(0, r)
    g = make_linear_lut(0, g)
    b = make_linear_lut(0, b)
    return ImagePalette("RGB", r + g + b)


def wedge(mode="RGB"):
    return ImagePalette(mode, list(range(256)) * len(mode))


def load(filename):

    # FIXME: supports GIMP gradients only

    with open(filename, "rb") as fp:

        for paletteHandler in [
            GimpPaletteFile.GimpPaletteFile,
            GimpGradientFile.GimpGradientFile,
            PaletteFile.PaletteFile,
        ]:
            try:
                fp.seek(0)
                lut = paletteHandler(fp).getpalette()
                if lut:
                    break
            except (SyntaxError, ValueError):
                # import traceback
                # traceback.print_exc()
                pass
        else:
            raise OSError("cannot load palette")

    return lut  # data, rawmode
