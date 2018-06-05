#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# converts a "font" image to to .asm code
# ----------------------------------------------------------------------------
"""
Tool to convert a font-file to .asm code
"""
import argparse
import sys
import queue
from PIL import Image


__docformat__ = 'restructuredtext'


PIXELS_PER_BYTE = 4
GFX_PAGES = 2
GFX_SEG = 0x1800

class Parser:

    def __init__(self, image_file, output_fd):
        self._visited = {}
        self._image_file = image_file
        self._output_fd = output_fd
        self._width = 0
        self._height = 0
        self._array = []
        self._segments = {}

    def run(self):
        """Execute the conversor."""
        im = Image.open(self._image_file)
        self._array = im.tobytes()
        self._width = im.width
        self._height = im.height

        segment = 0
        for x in range(self._width):
            for y in range(self._height):
                if not self.is_visited(x, y):
                    color = self.get_color(x, y)
                    self.start_segment(segment, x, y, color, 0)
                    #print(self._segments[segment])
                    segment += 1

        print('Total segments: %d' % segment)
        self.process_segments()

        self.generate_output()

    def is_visited(self, x, y):
        key = '%d,%d' % (x, y)
        return key in self._visited

    def is_valid(self, segment, x, y, color):
        # safety check
        if x < 0 or x >= self._width:
            return False
        if y < 0 or y >= self._height:
            return False

        # ignore if already visited
        if self.is_visited(x, y):
            return False

        # ignore if not the same color
        if self.get_color(x, y) != color:
            return False

        return True

    def start_segment(self, segment, x, y, color, depth):
        # non recursive "visit" algorithm since to avoid recursion exception

        print('Starting segment: %d - color: %d (%d,%d)' % (segment, color, x, y))
        q = queue.Queue()
        q.put((x, y))
        while not q.empty():
            x, y = q.get()

            if not self.is_valid(segment, x, y, color):
                # skip already processed nodes
                continue

            # tagged as visited
            key = '%d,%d' % (x, y)
            self._visited[key] = True

            if segment not in self._segments:
                self._segments[segment] = {}

            if y not in self._segments[segment]:
                self._segments[segment][y] = []

            # update dictionary with values for segment
            self._segments[segment][y].append(x)

            # visit the rest of the nodes
            if self.is_valid(segment, x-1, y, color):
                q.put((x-1, y))
            if self.is_valid(segment, x+1, y, color):
                q.put((x+1, y))
            if self.is_valid(segment, x, y-1, color):
                q.put((x, y-1))
            if self.is_valid(segment, x, y+1, color):
                q.put((x, y+1))

    def get_color(self, x, y):
        return self._array[self._width * y + x]

    def process_segments(self):
        for segment_k, segment_v in self._segments.items():
            for col, values in segment_v.items():
                values.sort()
                # non contiguos regions not supported yet (not needed for 55-segment)
                assert(len(values)-1 == values[-1] - values[0])
                # replace strings with range: coordinate, lenght
                self._segments[segment_k][col] = (
                        values[0],                  # starting x position
                        1 + values[-1] - values[0]) # lenght

    def generate_output(self):
        # Graphics mode 4: 320 x 200 x 4 colors: 2 bits per pixel
        # TODO: support 640 x 200 x 2 colors: 1 bit per pixel

        for seg_key, seg_data in self._segments.items():
            self.generate_on(seg_key, seg_data)
            self.generate_off(seg_key, seg_data)

    def generate_on(self, seg_key, seg_data):
        out = """
;=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-;
segment_%d_on:
        mov     ax,0b01010101_01010101
""" % seg_key
        self._output_fd.write(out)

        # offset used in X since the graphics might not be 320x200
        x_offset = (320 - self._width) // 2

        for row, values in seg_data.items():
            x_start, x_len = values
            x_start += x_offset

            while x_len > 0:

                consumed_pixels = 0
                offset = self.calculate_offset(row, x_start)

                # use full byte ?
                if x_start % PIXELS_PER_BYTE == 0:
                    # bytes available: pixels_left / pixels_per_word
                    bytes_used = x_len // PIXELS_PER_BYTE

                    if bytes_used // 2 > 0:
                        # at least one word
                        self.do_rep_stosw(offset, bytes_used // 2)
                        consumed_pixels = bytes_used * PIXELS_PER_BYTE
                    elif bytes_used > 0:
                        # one byte
                        assert(bytes_used == 1)
                        self.do_stosb(offset)
                        consumed_pixels = bytes_used * PIXELS_PER_BYTE
                    else:
                        # remaining part, less than one byte
                        mask = self.calculate_mask(x_start, x_len)
                        self.do_or(offset, mask)

                        # consumes all the remaining pixels
                        consumed_pixels = x_len

                else:
                    remaining = PIXELS_PER_BYTE - x_start % PIXELS_PER_BYTE
                    consumed_pixels = min(remaining, x_len)
                    mask = self.calculate_mask(x_start, consumed_pixels)
                    self.do_or(offset, mask)

                x_len -= consumed_pixels
                x_start += consumed_pixels

    def generate_off(self, seg_key, seg_data):
        pass

    def calculate_offset(self, y, x):

        # There are 2 'pages'
        # Even lines use page 0
        # Odd lines use page 1
        page = y % GFX_PAGES
        offset = page * 8192

        # each line is 320 pixels wide
        offset += (y // GFX_PAGES) * 320 // PIXELS_PER_BYTE

        # add x pixels, in bytes
        offset += x // PIXELS_PER_BYTE

        return offset

    def calculate_mask(self, x, pixels):
        # starting pixel from the left (msb bit)
        msb = PIXELS_PER_BYTE - x % PIXELS_PER_BYTE
        return 0xff

    def do_rep_stosw(self, offset, times):
        out = '        mov     di,0x%04x\n' % offset
        if times > 1:
            out += '        mov     cx,%d\n' % times
            out += '        rep stosw\n'
        else:
            out += '        stosw\n'
        self._output_fd.write(out)

    def do_stosb(self, offset):
        out = '        mov     di,0x%04x\n' % offset
        out += '        stosb\n'
        self._output_fd.write(out)

    def do_and(self, offset, mask):
        out = '        and     [0x%04x], %s\n' % (offset, bin(mask))
        self._output_fd.write(out)

    def do_or(self, offset, mask):
        out = '        or      [0x%04x], %s\n' % (offset, bin(mask))
        self._output_fd.write(out)


def parse_args():
    """Parse the arguments."""
    parser = argparse.ArgumentParser(
        description='Converts font-file to asm', epilog="""Example:

$ %(prog)s 55-segment.png -o font.asm
""")
    parser.add_argument('filename', metavar='<filename>',
            help='file to convert')
    parser.add_argument('-o', '--output-file', metavar='<filename>',
            help='output file. Default: stdout')

    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    if args.output_file is not None:
        with open(args.output_file, 'w+') as fd:
            Parser(args.filename, fd).run()
    else:
        Parser(args.filename, sys.stdout).run()

if __name__ == "__main__":
    main()
