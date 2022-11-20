from datetime import datetime

from cytubebot.common.socket_extensions import send_chat_msg


def content_handler(content_finder, tag, db, sio, sio_data) -> None:
    send_chat_msg(sio, 'Searching for content...')

    content, count = content_finder.find_content(tag)

    if count == 0:
        send_chat_msg(sio, 'No content to add.')
        return

    send_chat_msg(sio, f'Adding {count} videos.')

    for content_tuple in content:
        channel_id = content_tuple.channel_id
        new_dt = content_tuple.datetime
        video_id = content_tuple.video_id

        sio.emit(
            'queue',
            {'id': video_id, 'type': 'yt', 'pos': 'end', 'temp': True},
        )
        while not sio_data.queue_resp:
            sio.sleep(0.3)
        sio_data.queue_resp = None

        db.update_datetime(channel_id, str(new_dt))

    send_chat_msg(sio, 'Finished adding content.')


def add_christmas_videos(sio) -> None:
    now = datetime.now()
    if now.day != 25 and now.month != 12:
        send_chat_msg(sio, "It's not Christmas :(")
        return

    xmas_vids = ['3KvWwJ6sh5s']
    for video_id in xmas_vids:
        sio.emit(
            'queue',
            {'id': video_id, 'type': 'yt', 'pos': 'end', 'temp': True},
        )
