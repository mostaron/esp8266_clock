from machine import Pin, SPI
from micropython import const
import framebuf, utime
from font import big

_DIGIT_0 = const(0x1)

_DECODE_MODE = const(0x9)
_NO_DECODE = const(0x0)

_INTENSITY = const(0xa)
_INTENSITY_MIN = const(0x0)

_SCAN_LIMIT = const(0xb)
_DISPLAY_ALL_DIGITS = const(0x7)

_SHUTDOWN = const(0xc)
_SHUTDOWN_MODE = const(0x0)
_NORMAL_OPERATION = const(0x1)

_DISPLAY_TEST = const(0xf)
_DISPLAY_TEST_NORMAL_OPERATION = const(0x0)

_MATRIX_SIZE = const(8)

# _SCROLL_SPEED_NORMAL is ms to delay (slow) scrolling text.
_SCROLL_SPEED_NORMAL = 25

class Max7219(framebuf.FrameBuffer):
    """
    Driver for MAX7219 8x8 LED matrices
    https://github.com/vrialland/micropython-max7219
    Example for ESP8266 with 2x4 matrices (one on top, one on bottom),
    so we have a 32x16 display area:
    >>> from machine import Pin, SPI
    >>> from max7219 import Max7219
    >>> spi = SPI(1, baudrate=10000000)
    >>> screen = Max7219(32, 16, spi, Pin(15))
    >>> screen.rect(0, 0, 32, 16, 1)  # Draws a frame
    >>> screen.text('Hi!', 4, 4, 1)
    >>> screen.show()
    On some matrices, the display is inverted (rotated 180°), in this case
     you can use `rotate_180=True` in the class constructor.
    """

    def __init__(self, width, height, spi, cs, rotate_180=False):
        # Pins setup
        self.spi = spi
        self.cs = cs
        self.cs.init(Pin.OUT, True)

        # Dimensions
        self.width = width
        self.height = height
        # Guess matrices disposition
        self.cols = width // _MATRIX_SIZE
        self.rows = height // _MATRIX_SIZE
        self.nb_matrices = self.cols * self.rows
        self.rotate_180 = rotate_180
        # 1 bit per pixel (on / off) -> 8 bytes per matrix
        self.buffer = bytearray(width * height // 8)
        format = framebuf.MONO_HLSB if not self.rotate_180 else framebuf.MONO_HMSB
        super().__init__(self.buffer, width, height, format)

        # Init display
        self.init_display()

    def _write_command(self, command, data):
        """Write command on SPI"""
        cmd = bytearray([command, data])
        self.cs(0)
        for matrix in range(self.nb_matrices):
            self.spi.write(cmd)
        self.cs(1)

    def init_display(self):
        """Init hardware"""
        for command, data in (
                (_SHUTDOWN, _SHUTDOWN_MODE),  # Prevent flash during init
                (_DECODE_MODE, _NO_DECODE),
                (_DISPLAY_TEST, _DISPLAY_TEST_NORMAL_OPERATION),
                (_INTENSITY, _INTENSITY_MIN),
                (_SCAN_LIMIT, _DISPLAY_ALL_DIGITS),
                (_SHUTDOWN, _NORMAL_OPERATION),  # Let's go
        ):
            self._write_command(command, data)

        self.fill(0)
        self.show()

    def print_time(self, hour: int, minute: int, second: int):
        #print(hour, minute, second)
        if hour >= 22 or hour <= 7:
            self.brightness(1)
        else:
            self.brightness(15)
        hour_str = '{:0>2d}'.format(hour)
        self.print_letter(hour_str[0], 0, 0)
        self.print_letter(hour_str[1], 5, 0)
        self.print_colon(10)
        minute_str = '{:0>2d}'.format(minute)
        self.print_letter(minute_str[0], 12, 0)
        self.print_letter(minute_str[1], 17, 0)
        # self.print_colon(21)
        second_str = '{:0>2d}'.format(second)
        self.print_letter(second_str[0], 23, 0)
        self.print_letter(second_str[1], 28, 0)
        self.show()

    def print_letter(self, letter, x, y):
        mod = 0b0001
        for y1 in range(8):
            row = big[letter][y1]
            # print(row)
            for x1 in range(1, 5):
                data = row & mod
                if data != 0:
                    self.pixel(x + 4 - x1, y1 + y, 1)
                    # print(x1, y1)
                else:
                    self.pixel(x + 4 - x1, y1 + y, 0)
                x1 += 1
                row = row >> 1
            y1 += 1

    def print_colon(self, x):
        self.pixel(x, 3, 1)
        self.pixel(x, 6, 1)

    def brightness(self, value):
        # Set display brightness (0 to 15)
        if not 0 <= value < 16:
            raise ValueError('Brightness must be between 0 and 15')
        self._write_command(_INTENSITY, value)

    def marquee(self, message):
        start = 33
        extent = 0 - (len(message) * 8) - 32
        for i in range(start, extent, -1):
            self.fill(0)
            self.text(message, i, 0, 1)
            self.show()
            utime.sleep_ms(_SCROLL_SPEED_NORMAL)

    def show(self):
        """Update display"""
        # Write line per line on the matrices
        for line in range(8):
            self.cs(0)

            for matrix in range(self.nb_matrices):
                # Guess where the matrix is placed
                row, col = divmod(matrix, self.cols)
                # Compute where the data starts
                if not self.rotate_180:
                    offset = row * 8 * self.cols
                    index = col + line * self.cols + offset
                else:
                    offset = 8 * self.cols - row * (8 - line) * self.cols
                    index = (7 - line) * self.cols + col - offset

                self.spi.write(bytearray([_DIGIT_0 + line, self.buffer[index]]))

            self.cs(1)