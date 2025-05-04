import datetime
import json
import os

import click

import redis

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


@click.group()
def cli():
    """Command-line tool for managing Redis data."""
    pass


@cli.command()
@click.argument("file", type=click.Path(exists=True))
def push(file):
    """Push data from a JSON file into Redis."""
    with open(file, "r") as f:
        channels_data = json.load(f)

    for channel in channels_data:
        key = f"{channel['channel_id']}@youtube.channel.id"
        value = json.dumps(channel)
        redis_client.set(key, value)
        print(f"Inserted key: {key}")


@cli.command()
@click.argument("path", type=click.Path(exists=True), required=False)
def pull(path):
    """Pull all keys from Redis and save them into a timestamped JSON file."""
    if path is None:
        path = os.getcwd()

    keys = redis_client.keys("*")

    channels = []
    for key in keys:
        data = redis_client.get(key)
        try:
            channel = json.loads(data)
            channels.append(channel)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode data for key {key}")

    current_datetime = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"channels-{current_datetime}.json"

    with open(f"{path}/{output_file}", "w") as f:
        json.dump(channels, f, indent=4)


if __name__ == "__main__":
    cli()
