import environ
import logging
import pathlib


# set types for env variables
env = environ.FileAwareEnv(
    API_ID=(int),
    API_HASH=(str),
    BOT_NAME=(str, ''),  # TODO eliminate this, use pwd
    BOT_TOKEN=(str),
    BOT_VERSION=(str, ''),  # TODO eliminate this, use pwd

    LOG_LEVEL=(str, 'WARNING'),

    # DB
    DB_NAME=(str, 'postgres'),
    DB_USER=(str, 'postgres'),
    DB_PASSWORD=(str),
    DB_HOST=(str, 'db'),
    DB_PORT=(int, 5432),
    REDIS_HOST=(str, 'redis'),
    REDIS_PORT=(int, 6379),

    SEND_PLATFORM_METRICS_DATA=(bool, True),
    SEND_USER_STATS_INTERVAL_S=(int, 1800),

    # SMP
    SMP_PLATFORM_METRICS_EVENTS_URL=(str, 'platform-metrics/v1/events/'),
    SMP_PLATFORM_METRICS_MEASUREMENTS_URL=(str, 'platform-metrics/v1/measurements/'),

    SMP_APP_ID=(str),
    SMP_APP_SECRET=(str),
    SMP_BASE_URL=(str, 'https://api.smp.io'),

    # ThirdParty API
    RAPIDAPI_URL=(str, 'https://instagram-data1.p.rapidapi.com'),
    RAPIDAPI_EDGE=(str, 'instagram-data1.p.rapidapi.com'),
    RAPIDAPI_KEY=(str, ''),

    DISCORD_WEBHOOK=(str, ''),
    SUPPORT_CHAT_URL=(str),

    TELEGRAM_FLOOD_CONTROL_PAUSE_S=(int, 10),  # TODO parse this from error msg

    TROTTLING_WAIT_BETWEEN_PAID_REQUESTS_S=(int, 10),
    TROTTLING_WAIT_BETWEEN_REQUESTS_S=(float, 0.5),

    PENDING_DELAY=(int, 3)
)

# read .env file
environ.Env.read_env(pathlib.Path().resolve() / '.env')


API_ID = env('API_ID')
API_HASH = env('API_HASH')
BOT_NAME = env('BOT_NAME')
BOT_TOKEN = env('BOT_TOKEN')
BOT_VERSION = env('BOT_VERSION')

# DB
DB_NAME = env('DB_NAME')
DB_USER = env('DB_USER')
DB_PASSWORD = env('DB_PASSWORD')
DB_HOST = env('DB_HOST')
DB_PORT = env('DB_PORT')

REDIS_HOST = env('REDIS_HOST')
REDIS_PORT = env('REDIS_PORT')

# SMP
SMP_PLATFORM_METRICS_EVENTS_URL = env('SMP_PLATFORM_METRICS_EVENTS_URL')
SMP_PLATFORM_METRICS_MEASUREMENTS_URL = env('SMP_PLATFORM_METRICS_MEASUREMENTS_URL')

SMP_APP_ID = env('SMP_APP_ID')
SMP_APP_SECRET = env('SMP_APP_SECRET')
SMP_BASE_URL = env('SMP_BASE_URL')

if env('LOG_LEVEL') == 'DEBUG':
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO

# ThirdParty API
RAPIDAPI_URL = env('RAPIDAPI_URL')
RAPIDAPI_EDGE = env('RAPIDAPI_EDGE')
RAPIDAPI_KEY = env('RAPIDAPI_KEY')

DISCORD_WEBHOOK = env('DISCORD_WEBHOOK')
SUPPORT_CHAT_URL = env('SUPPORT_CHAT_URL')

TELEGRAM_MAX_INLINE_BUTTON_ROWS = 30
TELEGRAM_FLOOD_CONTROL_PAUSE_S = env('TELEGRAM_FLOOD_CONTROL_PAUSE_S')

TROTTLING_WAIT_BETWEEN_PAID_REQUESTS_S = env('TROTTLING_WAIT_BETWEEN_PAID_REQUESTS_S')
TROTTLING_WAIT_BETWEEN_REQUESTS_S = env('TROTTLING_WAIT_BETWEEN_REQUESTS_S')

PENDING_DELAY = env('PENDING_DELAY')

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

SECONDS_BETWEEN_ADMIN_NOTIFICATIONS = 60 * 10  # 10 minutes
DAY_BORDER_HOUR = 14

ANNOUNCE_PACK_LENGTH = 20

CONFIG_PATH = 'configs/creoscan.yaml'
PLUGINS = [
    'Introduction.core',
    'Instagram.core',
    'Support.core',
    'Common.core',
]
