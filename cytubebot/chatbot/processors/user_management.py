import logging
import re

import psycopg
import requests
from bs4 import BeautifulSoup as bs

logger = logging.getLogger(__name__)


def add_user(args, db, sio) -> None:
    if not args:
        return

    logger.info(f'{args=}')

    channel_name = ''.join(args)
    channel_name = cleanse_yt_crap(channel_name)

    channel = f'https://www.youtube.com/c/{channel_name}'

    resp = requests.get(channel, cookies={'CONSENT': 'YES+1'}, timeout=60)
    page = resp.text
    soup = bs(page, 'lxml')
    yt_initial_data = soup.find('script', string=re.compile('ytInitialData'))
    try:
        results = re.search('.*"browse_id","value":"(.*?)"', yt_initial_data.text)
        channel_id = results.group(1)
        msg = f'Found channel ID: {channel_id} for {channel_name}, adding to DB.'
        sio.emit('chatMsg', {'msg': msg})
    except AttributeError:
        logger.info(f'Failed to find channel_id for {channel_name}.')
        try:
            channel_id = str(channel_name)
            channel = f'https://www.youtube.com/channel/{channel_id}'
            resp = requests.get(channel, cookies={'CONSENT': 'YES+1'}, timeout=60)
            page = resp.text
            soup = bs(page, 'lxml')
            yt_initial_data = soup.find('script', string=re.compile('ytInitialData'))
            results = re.search(
                '.*"channelMetadataRenderer":{"title":"(.*?)"', yt_initial_data.text
            )
            channel_name = results.group(1)
            msg = f'Found channel name: {channel_name} for {channel_id}, adding to DB.'
            logger.info(msg)
            sio.emit('chatMsg', {'msg': msg})
        except AttributeError:
            msg = f"Couldn't find channel: {channel}"
            logger.error(msg)
            sio.emit('chatMsg', {'msg': msg})
            return

    try:
        db.add_channel(channel_id, channel_name)
    except psycopg.errors.UniqueViolation:
        msg = f'{channel_name} already in Database.'
        sio.emit('chatMsg', {'msg': msg})


def cleanse_yt_crap(channel_name_or_url: str) -> str:
    # Remove <a> tags if necessary
    if '</a>' in channel_name_or_url:
        channel_name_or_url = re.search(r'.*>(.*?)</a>', channel_name_or_url).group(1)

    channel_name_or_url = channel_name_or_url.strip()

    channel_name_or_url = channel_name_or_url.replace('/featured', '')
    channel_name_or_url = channel_name_or_url.replace('/videos', '')
    channel_name_or_url = channel_name_or_url.replace('/playlists', '')
    channel_name_or_url = channel_name_or_url.replace('/community', '')
    channel_name_or_url = channel_name_or_url.replace('/channels', '')
    channel_name_or_url = channel_name_or_url.replace('/about', '')

    if channel_name_or_url[-1:] == '/':
        channel_name_or_url = channel_name_or_url[:-1]

    channel_name_or_url = channel_name_or_url.rsplit('/', 1)[-1]

    return channel_name_or_url


def remove_user(args, db, sio) -> None:
    if not args:
        return

    channel_name = ''.join(args)
    channel_name = channel_name.strip()

    # Remove <a> tags if necessary
    if '</a>' in channel_name:
        channel_name = re.search(r'.*>(.*?)</a>', channel_name).group(1)

    msg = f'Deleting {channel_name} from DB.'
    sio.emit('chatMsg', {'msg': msg})

    db.remove_channel(channel_name)
