import logging
import re

import psycopg
import requests
from bs4 import BeautifulSoup as bs

logger = logging.getLogger(__name__)


def add_user(args, db, sio) -> None:
    if not args:
        return

    channel_name = ''.join(args)
    channel_name = channel_name.strip().lower()

    # Remove <a> tags if necessary
    if '</a>' in channel_name:
        channel_name = re.search(r'.*>(.*?)</a>', channel_name).group(1)

    if 'https://www.youtube.com/c/' not in channel_name:
        channel = f'https://www.youtube.com/c/{channel_name}'
    else:
        channel = channel_name

    resp = requests.get(channel, cookies={'CONSENT': 'YES+1'})
    page = resp.text
    soup = bs(page, 'lxml')
    yt_initial_data = soup.find('script', string=re.compile('ytInitialData'))
    try:
        results = re.search('.*"browse_id","value":"(.*?)"', yt_initial_data.text)
    except AttributeError:
        msg = f"Couldn't find channel ID for {channel}"
        logger.error(msg)
        sio.emit('chatMsg', {'msg': msg})
        return

    channel_id = results.group(1)
    msg = f'Found channel ID: {channel_id} for {channel_name}, adding to DB.'
    sio.emit('chatMsg', {'msg': msg})

    try:
        db.add_channel(channel_id, channel_name)
    except psycopg.errors.UniqueViolation:
        msg = f'{channel_name} already in Database.'
        sio.emit('chatMsg', {'msg': msg})


def remove_user(args, db, sio) -> None:
    if not args:
        return

    channel_name = ''.join(args)
    channel_name = channel_name.strip().lower()

    # Remove <a> tags if necessary
    if '</a>' in channel_name:
        channel_name = re.search(r'.*>(.*?)</a>', channel_name).group(1)

    msg = f'Deleting {channel_name} from DB.'
    sio.emit('chatMsg', {'msg': msg})

    db.remove_channel(channel_name)
