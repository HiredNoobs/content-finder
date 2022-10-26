import requests
from collections import namedtuple
from operator import attrgetter
from datetime import datetime
from bs4 import BeautifulSoup as bs
from cytubebot.contentfinder.database import DBHandler


class ContentFinder:
    def __init__(self) -> None:
        self.db = DBHandler()

    def find_content(self) -> tuple[list, int]:
        """
        returns:
            A tuple containing the content dict and a count of the amount of
            new content found. Content dict comes in the form:
            {
                'channel_id': (datetime, [video_id_1, video_id_2])
            }
        """
        con, cur = self.db.init_db()
        ContentDetails = namedtuple('ContentDetails',
                                    'channel_id datetime video_id')
        content = []

        cur.execute('SELECT * FROM content')
        for row in cur:
            channel_id = row[0]
            name = row[1]
            dt = datetime.fromisoformat(row[2])
            print(f'Getting content for: {name}')

            channel = ('https://www.youtube.com/feeds/videos.xml?channel_id='
                       f'{channel_id}')
            resp = requests.get(channel)
            page = resp.text
            soup = bs(page, 'lxml')

            for item in soup.find_all('entry'):
                if '#shorts' in item.find_all('title')[0].text.casefold():
                    print('Skipping #short.')
                    continue

                published = item.find_all('published')[0].text
                published = datetime.fromisoformat(published)

                if published < dt or published == dt:
                    print(f'No more new videos for {name}')
                    break

                video_id = item.find_all('yt:videoid')[0].text

                c = ContentDetails(channel_id, published, video_id)
                content.append(c)

        cur.close()
        con.close()

        content = sorted(content, key=attrgetter('datetime'))

        return content, len(content)
