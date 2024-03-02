import logging
from collections import namedtuple
from datetime import datetime
from operator import attrgetter

import requests
from bs4 import BeautifulSoup as bs

from cytubebot.contentfinder.database import DBHandler


class ContentFinder:
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._db = DBHandler()

    def find_content(self, tag: str = None) -> list[namedtuple]:
        """
        returns:
            A tuple containing the content dict and a count of the amount of
            new content found. Content dict comes in the form:
            {
                'channel_id': (datetime, [video_id_1, video_id_2])
            }
        """
        ContentDetails = namedtuple('ContentDetails', 'channel_id datetime video_id')

        content = []
        channels = self._db.get_channels(tag)

        for row in channels:
            channel_id = row[0]
            name = row[1]
            dt = datetime.fromisoformat(row[2])
            self._logger.info(f'Getting content for: {name}')

            channel = (
                f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
            )
            resp = requests.get(channel, timeout=60)
            page = resp.text
            soup = bs(page, 'lxml')

            for item in soup.find_all('entry'):
                published = item.find_all('published')[0].text
                published = datetime.fromisoformat(published)

                if published < dt or published == dt:
                    self._logger.info(f'No more new videos for {name}')
                    break

                title = item.find_all('title')[0].text.casefold()
                video_id = item.find_all('yt:videoid')[0].text

                if not self._is_short(title, video_id):
                    c = ContentDetails(channel_id, published, video_id)
                    content.append(c)

        content = sorted(content, key=attrgetter('datetime'))

        return content, len(content)

    def _is_short(self, title: str, id: str) -> bool:
        """
        Returns True if video id is a YT Shorts video.
        """
        if '#shorts' in title:
            return True

        shorts_url = f'https://www.youtube.com/shorts/{id}'
        resp = requests.head(
            shorts_url, cookies={'CONSENT': 'YES+1'}, timeout=60, allow_redirects=False
        )
        if resp.status_code == 303 or resp.status_code == 302:
            return False
        # Assume any 2XX successfully reached a shorts page
        elif 200 <= resp.status_code <= 299:
            return True
        else:
            self._logger.info(f'Received {resp.status_code=} from {shorts_url}')
            return True
