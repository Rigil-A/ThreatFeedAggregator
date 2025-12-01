from utils.config import config
from models.feed_config import FeedConfigModel, FeedSettings
import json

def load_feeds():
    feeds_raw = config.get("feeds", default=[]) or []
    feeds = []

    for entry in feeds_raw:
        feed_data = entry.get("Feed", {})
        tag_data = entry.get("Tag", {})

        if not feed_data.get("enabled", False):
            continue

        raw_settings = feed_data.get("settings", "{}").strip('"')
        try:
            settings_obj = json.loads(raw_settings)
        except:
            settings_obj = {}

        csv_conf = settings_obj.get("csv", {})
        common_conf = settings_obj.get("common", {})

        csv_value = csv_conf.get("value", "")
        indexes = [int(x) for x in csv_value.split(",") if x.isdigit()]

        feed_settings = FeedSettings(
            csv_indexes=indexes,
            csv_delimiter=csv_conf.get("delimiter", ","),
            exclude_regex=common_conf.get("excluderegex")
        )

        feeds.append(
            FeedConfigModel(
                name=feed_data.get("name"),
                provider=feed_data.get("provider"),
                url=feed_data["url"],
                enabled=True,
                source_format=feed_data.get("source_format", "freetext"),
                input_source=feed_data.get("input_source", "network"),
                settings=feed_settings,
                tag_name=tag_data.get("name")
            )
        )

    return feeds
