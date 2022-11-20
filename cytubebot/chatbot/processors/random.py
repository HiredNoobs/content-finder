from cytubebot.common.socket_extensions import send_chat_msg


def random_handler(command, args, random_finder, sio, sio_data) -> None:
    rand_id = None

    if command == 'random_word':
        rand_id, search_str = random_finder.find_random(use_dict=True)
    elif command == 'random':
        try:
            size = int(args[0]) if args else 3
        except ValueError:
            size = 3

        rand_id, search_str = random_finder.find_random(size)

    if rand_id:
        sio.emit(
            'queue',
            {'id': rand_id, 'type': 'yt', 'pos': 'end', 'temp': True},
        )
        while not sio_data.queue_resp:
            sio.sleep(0.3)
        sio_data.queue_resp = None

        msg = f'Searched: {search_str}, added: {rand_id}'
        send_chat_msg(sio, msg)
    else:
        msg = 'Found no random videos.. Try again. If giving arg over 5, try reducing.'
        send_chat_msg(sio, msg)
