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
                'https://www.youtube.com/feeds/videos.xml?channel_id=' f'{channel_id}'
            )
            resp = requests.get(channel, timeout=60)
            page = resp.text
            soup = bs(page, 'lxml')

            for item in soup.find_all('entry'):
                if '#shorts' in item.find_all('title')[0].text.casefold():
                    self._logger.info('Skipping #short.')
                    continue

                published = item.find_all('published')[0].text
                published = datetime.fromisoformat(published)

                if published < dt or published == dt:
                    self._logger.info(f'No more new videos for {name}')
                    break

                video_id = item.find_all('yt:videoid')[0].text

                c = ContentDetails(channel_id, published, video_id)
                content.append(c)

        content = sorted(content, key=attrgetter('datetime'))

        return content, len(content)
