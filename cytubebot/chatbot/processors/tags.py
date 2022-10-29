from cytubebot.common.exceptions import InvalidTagError

VALID_TAGS = ['ASMR']


def add_tags(args, db) -> None:
    channel_id = args[0]
    tags = args[1:]
    tags = [x.upper() for x in tags]
    if not all(tag in VALID_TAGS for tag in tags):
        raise InvalidTagError('Invalid tag supplied.')
    db.add_tags(channel_id, tags)


def remove_tags(args, db) -> None:
    channel_id = args[0]
    tags = args[1:]
    tags = [x.upper() for x in tags]
    if not all(tag in VALID_TAGS for tag in tags):
        raise InvalidTagError('Invalid tag supplied.')
    db.remove_tags(channel_id, tags)
