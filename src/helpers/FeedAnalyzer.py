import datetime
import logging
import random
from dataclasses import dataclass
from typing import Optional, Tuple

from common.models import Post

from .base import BaseHelper


DAY_BORDER_HOUR = 14
EVEN_MINUTES = (0, 30)
RANDOM_ADDITIONAL_MINUTES_RANGE = (1, 7)
log = logging.getLogger(__name__)


@dataclass
class FeedStats:
    average_likes_count: int
    average_comments_count: int
    posts_count: int

    best_first_publication_time: datetime.datetime
    best_second_publication_time: datetime.datetime
    oldest_post_date: datetime.datetime
    newest_post_date: datetime.datetime

    post_with_best_activity: str
    post_with_worst_activity: str


class FeedAnalyzerHelper(BaseHelper):
    """
    Base class for obtaining user feed and extracting useful data from it.
    """
    # TODO make slots
    _posts = []
    _search_method = 'get_posts_from_feed'

    @property
    async def search_results(self) -> Tuple[datetime.datetime]:
        search_results = await super().search_results
        first_half_posts = [p for p in search_results if p.created_at.hour < DAY_BORDER_HOUR]
        second_half_posts = [p for p in search_results if p.created_at.hour >= DAY_BORDER_HOUR]

        # find posts with the best activity in both halves of the day
        best_post_in_first_half = max(first_half_posts, key=lambda p: p.likes_count) if first_half_posts else None
        best_post_in_second_half = max(second_half_posts, key=lambda p: p.likes_count) if second_half_posts else None

        average_likes_count = round(sum([p.likes_count for p in search_results]) / len(search_results), 1)

        best_first_publication_time = await self._get_best_publication_time(average_likes_count, best_post_in_first_half)
        best_second_publication_time = await self._get_best_publication_time(average_likes_count, best_post_in_second_half)

        # check that best publication time is not even
        best_first_publication_time = await self._get_adjusted_even_time(best_first_publication_time)
        best_second_publication_time = await self._get_adjusted_even_time(best_second_publication_time)

        return FeedStats(
            average_comments_count=round(sum([p.comments_count for p in search_results]) / len(search_results), 1),
            average_likes_count=round(sum([p.likes_count for p in search_results]) / len(search_results), 1),
            best_first_publication_time=best_first_publication_time,
            best_second_publication_time=best_second_publication_time,
            post_with_best_activity=max(posts, key=lambda p: p.activity_count) if (posts := search_results) else None,
            post_with_worst_activity=min(posts, key=lambda p: p.activity_count) if (posts := search_results) else None,
            newest_post_date=max(search_results, key=lambda p: p.created_at).created_at,
            oldest_post_date=min(search_results, key=lambda p: p.created_at).created_at,
            posts_count=len(search_results),
        )

    @property
    def keyword(self):
        """
        account can be in forms of:
            https://www.instagram.com/basni.krylova/
            https://www.instagram.com/basni.krylova
            https://instagram.com/basni.krylova?utm_medium=copy_link
            basni.krylova
            @basni.krylova
        """
        if not (text := self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        # cut last part if account is in form of url (and drop last /)
        text = text.split('/')[-1] or text.split('/')[-2]
        # cut utm
        text = text.split('?')[0]
        # cut '@'
        return text.replace('@', '')

    async def _get_best_publication_time(self, average_likes_count: int, best_post: Post) -> Optional[datetime.datetime]:
        if not best_post:
            return

        # skip if best post is below average activity
        if best_post.likes_count < average_likes_count:
            return

        return datetime.datetime.now().replace(
            hour=best_post.created_at.hour,
            minute=best_post.created_at.minute,
        )

    @staticmethod
    async def _get_adjusted_even_time(best_time: datetime.datetime) -> Optional[datetime.datetime]:
        if not best_time:
            return

        if best_time.minute in EVEN_MINUTES:
            minutes_shift = random.randrange(*RANDOM_ADDITIONAL_MINUTES_RANGE)
            if best_time.minute + minutes_shift > 59:
                minutes_shift *= -1

            new_minute = best_time.minute + minutes_shift

            best_time.replace(minute=new_minute)

        return best_time
