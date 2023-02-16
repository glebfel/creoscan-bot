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
    REDIS_HOST=(str, 'redis'),
    REDIS_PORT=(int, 6379),

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

REDIS_HOST = env('REDIS_HOST')
REDIS_PORT = env('REDIS_PORT')

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
