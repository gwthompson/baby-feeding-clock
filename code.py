import board
import displayio
import digitalio
import busio
import adafruit_touchscreen
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_requests as requests
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import neopixel
from adafruit_io.adafruit_io import RESTClient
import time
import rtc
import gc

TIME_SERVICE = "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s"
TIME_SERVICE_STRFTIME = '&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z'

DIM_DOWN_DELAY_SEC = 30

from secrets import secrets

def connect_wifi():
    print('Connecting wifi...')
    esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
    esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
    esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
    status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
    wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)
    print('Done.')
    gc.collect()
    return wifi

# from: https://github.com/adafruit/Adafruit_CircuitPython_PyPortal/blob/master/adafruit_pyportal.py
# simplified for use
def set_local_time():
    api_url = None
    aio_username = secrets['aio_username']
    aio_key = secrets['aio_key']
    location = secrets['timezone']
    print("Getting time for timezone", location)
    api_url = (TIME_SERVICE + "&tz=%s") % (aio_username, aio_key, location)
    api_url += TIME_SERVICE_STRFTIME
    response = requests.get(api_url)
    #print("Time request: ", api_url)
    print("Time reply: ", response.text)
    times = response.text.split(' ')
    the_date = times[0]
    the_time = times[1]
    year_day = int(times[2])
    week_day = int(times[3])
    is_dst = None  # no way to know yet
    year, month, mday = [int(x) for x in the_date.split('-')]
    the_time = the_time.split('.')[0]
    hours, minutes, seconds = [int(x) for x in the_time.split(':')]
    now = time.struct_time((year, month, mday, hours, minutes, seconds, week_day, year_day,
                            is_dst))
    rtc.RTC().datetime = now
    # now clean up
    response.close()
    response = None
    gc.collect()

def time_to_str(t):
    return '{}-{}-{} {}:{}:{}'.format(t.tm_year, t.tm_mon,
                                      t.tm_mday, t.tm_hour,
                                      t.tm_min, t.tm_sec)

def str_to_time(s):
    a = s.split(' ')
    data_ymd = a[0].split('-')
    data_hms = a[1].split(':')
    str_time = time.struct_time((int(data_ymd[0]), int(data_ymd[1]), int(data_ymd[2]),
                                 int(data_hms[0]), int(data_hms[1]), int(data_hms[2]),
                                   -1, -1, False))  # we dont know day of week/year or DST
    return str_time

"""BabyClock

- pyportal screen size is: 320x240

"""
class BabyClock:
    def __init__(self):
        self.splash = displayio.Group(max_size=5)
        self.bg_group = displayio.Group(max_size=1)

        board.DISPLAY.auto_brightness = True

        self.bg_file = None

        self.texts = []

        # touchscreen
        self.touchscreen = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                               board.TOUCH_YD, board.TOUCH_YU,
                                               calibration=((5200, 59000),(5800, 57000)),
                                               size=(320, 240))

        # connecting wifi
        self.wifi = connect_wifi()

        # connecting io
        self.connect_io()

        # setting local time
        set_local_time()

        # getting last feed time from adafruit io
        self.prev_feed_end_time, self.prev_feed_start_time, self.prev_feed_count = self.get_last_feed_time()

        board.DISPLAY.show(self.splash)

    def connect_io(self):
        print('Connecting adafruit io...')
        self.io = RESTClient(secrets['aio_username'], secrets['aio_key'], self.wifi)
        self.feed_start_time_f = self.io.get_feed('feed-start')
        self.feed_end_time_f = self.io.get_feed('feed-end')
        self.feed_count_f = self.io.get_feed('feed-count')
        print('Done.')

    """Send feed time with count of the day to adafruit io
    """
    def new_feed_time(self):
        print('Loading history...')
        received_data = self.io.receive_data(self.feed_time_f['key'])
        print('Data from temperature feed: ', received_data['value'])

    """Get from adafruit io last feed time & count
    """
    def get_last_feed_time(self):
        data = self.io.receive_data(self.feed_start_time_f['key'])
        prev_feed_start_time = str_to_time(data['value'])
        data = self.io.receive_data(self.feed_end_time_f['key'])
        prev_feed_end_time = str_to_time(data['value'])
        data = self.io.receive_data(self.feed_count_f['key'])
        prev_feed_count = int(data['value'])
        return prev_feed_end_time, prev_feed_start_time, prev_feed_count

    def clear_display(self):
        # remove all from group
        while self.bg_group:
            self.bg_group.pop()
        while self.splash:
            self.splash.pop()
        self.splash.append(self.bg_group)
        self.texts = []

    def set_background(self, image_file):
        # close if open
        if self.bg_file:
            self.bg_file.close()
        self.bck_file = open(image_file, 'rb')
        bg = displayio.OnDiskBitmap(self.bck_file)
        bg_sprite = displayio.TileGrid(bg, pixel_shader=displayio.ColorConverter(), x=0, y=0)
        self.bg_group.append(bg_sprite)
        board.DISPLAY.refresh_soon()
        board.DISPLAY.wait_for_frame()

    def set_to_info(self, max_glyphs=2):
        self.dim_down()

        self.clear_display()
        self.set_background('back_info.bmp')
        # hour since, min since, count
        positions = [(210,45),(250,45),(230,110)]
        font = bitmap_font.load_font('/fonts/Nunito-Black-17.bdf')
        #font.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
        font.load_glyphs(b'0123456789:/-_,. ')
        for x, y in positions:
            text = Label(font, text='', max_glyphs=max_glyphs)
            text.x = x
            text.y = y
            text.color = 0x000000
            self.splash.append(text)
            self.texts.append(text)

        # :
        text = Label(font, text=':')
        text.x = 238
        text.y = 43
        text.color =0x000000
        self.splash.append(text)

        self.dim_up()

    def set_to_timer(self):
        self.dim_down()
        self.feed_start_time = time.localtime()

        if self.feed_start_time.tm_mday != self.prev_feed_start_time.tm_mday:
            self.prev_feed_count = 0

        self.clear_display()
        self.set_background('back_timer.bmp')
        # hour since, min since, sec_since
        positions = [(100-50+10,120),(220-50+10,120)]
        font = bitmap_font.load_font('/fonts/Nunito-Light-75.bdf')
        #font.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
        font.load_glyphs(b'0123456789: ')
        for x, y in positions:
            text = Label(font, text='', max_glyphs=2)
            text.x = x
            text.y = y
            text.color = 0xffffff # white
            self.splash.append(text)
            self.texts.append(text)

        # add : between numbers
        text = Label(font, text=':')
        text.x = 160-7
        text.y = 120-5
        text.color = 0xffffff # white
        self.splash.append(text)

        self.dim_up()

    def set_texts(self, texts):
        for text_area, text in zip(self.texts, texts):
            text_area.text = str(text)

    def dim_down(self):
        board.DISPLAY.auto_brightness = False
        for i in range(100, -1, -1):  # dim down
            board.DISPLAY.brightness = i/100
            time.sleep(0.005)

    def dim_up(self):
        board.DISPLAY.auto_brightness = False
        for i in range(101):  # dim down
            board.DISPLAY.brightness = (i)/100
            time.sleep(0.005)
        board.DISPLAY.auto_brightness = True

    def send_to_io(self):
        # feed_start_time
        # feed_end_time
        # count

        # set previous
        self.prev_feed_end_time = time.localtime()
        self.prev_feed_start_time = self.feed_start_time
        self.prev_feed_count += 1

        # send to io
        self.io.send_data(self.feed_start_time_f['key'], time_to_str(self.feed_start_time))
        self.io.send_data(self.feed_end_time_f['key'], time_to_str(self.prev_feed_end_time))
        self.io.send_data(self.feed_count_f['key'], self.prev_feed_count)

def check_touch(touchscreen):
    touch = touchscreen.touch_point
    if touch:
        return True
    return False

def deltatime_with(t, ref):
    since = t - ref
    s = since % 60
    since //= 60
    m = since % 60
    since //= 60
    h = since % 24
    return h,m,s

baby = BabyClock()
baby.set_to_info(max_glyphs=10)

hours_since = 0
mins_since = 0
sec_since = 0
current_mode = 'info'
on_time = time.mktime(time.localtime())
while True:

    # mode:info
    if current_mode == 'info':
        now = time.mktime(time.localtime())
        touch = check_touch(baby.touchscreen)
        if on_time is None:
            # display on for number sec
            if touch:
                baby.dim_up()
                on_time = now
                continue
        else:
            h, m, s = deltatime_with(now, on_time)
            if touch and s > 5:
                print("Switching to timer mode...")
                current_mode = 'timer'
                baby.set_to_timer()
                hours_since = -1 # make sure we refresh
                continue
            elif s > DIM_DOWN_DELAY_SEC and not touch:
                baby.dim_down()
                on_time = None
            # update display
            # display time since last feeding
            # feeding count of the day
            # check touch screen to start timer mode
            else:
                h, m, s = deltatime_with(now, time.mktime(baby.prev_feed_end_time))
                if h != hours_since or m != mins_since:
                    hours_since = h
                    mins_since = m
                    baby.set_texts(["{:02d}".format(hours_since),
                                    "{:02d}".format(mins_since),
                                    "{:02d}".format(baby.prev_feed_count)
                                   ])
    # mode: timer
    else:
        now = time.localtime()
        h, m, s = deltatime_with(time.mktime(now), time.mktime(baby.feed_start_time))

        if h != hours_since or m != mins_since:
            hours_since = h
            mins_since = m
            sec_since = s
            # with leading zero
            baby.set_texts(["{:02d}".format(hours_since), "{:02d}".format(mins_since)])

        touch = check_touch(baby.touchscreen)
        if touch:
            print("Swithing to info mode...")
            current_mode = 'info'
            baby.set_to_info()
            on_time = time.mktime(time.localtime())
            baby.send_to_io()
            hours_since = -1 # make sure we refresh