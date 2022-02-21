from machine import Pin, SPI
import max7219
import time
import wifiManager
import ntptime
from machine import RTC

spi = SPI(1, baudrate=10000000)
display = max7219.Max7219(32, 8, spi, Pin(15))


def init_wifi():
    wlan = wifiManager.get_connection(display)
    if wlan is None:
        display.text("WIER")


def init_time():
    ntptime.NTP_DELTA = 3155644800
    ntptime.host = 'ntp1.aliyun.com'
    ntptime.settime()


def init():
    init_wifi()
    init_time()
    rtc = RTC()
    synced = False
    while True:
        try:
            datetime = rtc.datetime()

            display.print_time(int(datetime[4]), int(datetime[5]), int(datetime[6]))
            # if int(datetime[4]) % 5 == 0 and int(datetime[5]) == 0 and int(datetime[6]) == 0:
            if int(datetime[6]) == 0 and not synced:
                init_time()
                synced = True
            else:
                synced = False
            time.sleep(0.01)
        except Exception:
            pass


if __name__ == '__main__':
    init()
