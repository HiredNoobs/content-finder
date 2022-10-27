def content_handler(content_finder, db, sio, sio_data) -> None:
    sio.emit('chatMsg', {'msg': 'Searching for content...'})

    content, count = content_finder.find_content()

    if count == 0:
        sio.emit('chatMsg', {'msg': 'No content to add.'})
        return

    sio.emit('chatMsg', {'msg': f'Adding {count} videos.'})

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

    sio.emit('chatMsg', {'msg': 'Finished adding content.'})
