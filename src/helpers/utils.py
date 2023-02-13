import re
from typing import List

from common.models import Hashtag


async def fix_hashtag_text(text: str) -> str:
    text = str(text).lower()
    text = text.replace('_', '')  # '_' breaks inline keys

    if not text.startswith('#'):
        text = f'#{text}'

    return text


async def get_hashtags_from_text(text: str) -> List[Hashtag]:
    hashtags = [str(Hashtag(text=await fix_hashtag_text(h))) for h in re.findall(r'#[^ \n]+', text)]
    hashtags.sort()
    return hashtags


async def get_hashtags_from_text_with_rate(text: str) -> List[Hashtag]:
    hashtags = []

    for h in re.findall(r'#[^ ]+ - [0-9]+[K,M]*', text):
        word, rate = h.split(' - ')
        hashtags.append(
            Hashtag(
                text=await fix_hashtag_text(word),
                rate=await unhumanize_rate(rate),
            )
        )
    return hashtags


async def unhumanize_rate(rate: str) -> int:
    rate = rate\
        .replace('T', '000000000000')\
        .replace('B', '000000000')\
        .replace('M', '000000')\
        .replace('K', '000')
    return int(rate)
