import atexit
import logging
import os
import typing

import requests
from bs4 import BeautifulSoup as bs
from psycopg_pool import ConnectionPool


class DBHandler:
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

        conn_info = (
            'postgres://'
            f'{os.getenv("POSTGRES_USER")}:{os.getenv("POSTGRES_PASSWORD")}'
            '@postgres.content-finder:5432/content?connect_timeout=30'
        )
        self._pool = ConnectionPool(conn_info)

        # When the module exits this should force close the pool of conns
        atexit.register(self._close_pool)

    def _execute(self, query: str, params: typing.Tuple = None) -> list | None:
        """
        Extremely generic method for executing any single query against the DB.
        Method will take a connection from the pool, create a cursor, execute
        the given query - while supplying any params, if a SELECT is given the
        method will call .fetchall() and return the results, and commit any
        changes to the DB then return None.
        """
        self._logger.info(f'Executing {query} with {params}.')
        query_type = query.split()[0]
        result = None
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                self._logger.info(cur.statusmessage)
                if query_type == 'SELECT':
                    result = cur.fetchall()
            conn.commit()
        return result

    def _close_pool(self) -> None:
        self._logger.info('Closing Postgres connnection pool.')
        self._pool.close()

    def update_datetime(self, channel_id: str, new_dt: str) -> None:
        query = 'UPDATE content SET datetime = %s WHERE channelId = %s'
        self._execute(query, (new_dt, channel_id))

    def add_channel(self, channel_id: str, channel_name: str) -> None:
        channel = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
        resp = requests.get(channel)
        page = resp.text
        soup = bs(page, 'lxml')
        entry = soup.find_all('entry')[0]
        published = entry.find_all('published')[0].text

        query = 'INSERT INTO content(channelId, name, datetime) VALUES (%s,%s,%s)'
        self._execute(query, (channel_id, channel_name, published))

    def remove_channel(self, channel_name) -> None:
        query = 'DELETE FROM content WHERE ctid IN (SELECT ctid FROM content WHERE name = %s LIMIT 1)'
        self._execute(query, (channel_name,))

    @property
    def pool(self) -> ConnectionPool:
        return self._pool
