# -*- coding: utf-8 -*-

# Copyright 2020 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://www.subscribestar.com/"""

from .common import Extractor, Message
from .. import text
import datetime
import json


BASE_PATTERN = r"(?:https?://)?(?:www\.)?subscribestar\.(com|adult)"


class SubscribestarExtractor(Extractor):
    """Base class for subscribestar extractors"""
    category = "subscribestar"
    root = "https://www.subscribestar.com"
    directory_fmt = ("{category}", "{author_name}")
    filename_fmt = "{post_id}_{id}.{extension}"
    archive_fmt = "{id}"

    def __init__(self, match):
        tld, self.item = match.groups()
        if tld == "adult":
            self.root = "https://subscribestar.adult"
            self.subcategory += "-adult"
        Extractor.__init__(self, match)
        self.metadata = self.config("metadata", False)
        self._year = " " + str(datetime.date.today().year)

    def items(self):
        for post_html in self.posts():
            media = self._media_from_post(post_html)
            if not media:
                continue
            data = self._data_from_post(post_html)
            yield Message.Directory, data
            for item in media:
                item.update(data)
                url = item["url"]
                yield Message.Url, url, text.nameext_from_url(url, item)

    def posts(self):
        """Yield HTML content of all relevant posts"""

    @staticmethod
    def _media_from_post(html):
        gallery = text.extract(html, 'data-gallery="', '"')[0]
        if gallery:
            return [
                item for item in json.loads(text.unescape(gallery))
                if "/previews/" not in item["url"]
            ]
        return ()

    def _data_from_post(self, html):
        extr = text.extract_from(html)
        data = {
            "post_id"    : text.parse_int(extr('data-id="', '"')),
            "author_id"  : text.parse_int(extr('data-user-id="', '"')),
            "author_name": text.unescape(extr('href="/', '"')),
            "author_nick": text.unescape(extr('>', '<')),
            "content"    : (extr(
                '<div class="post-content', '<div class="post-uploads')
                .partition(">")[2]),
        }

        if self.metadata:
            url = "{}/posts/{}".format(self.root, data["post_id"])
            page = self.request(url).text
            data["date"] = self._parse_datetime(text.extract(
                page, 'class="section-subtitle">', '<')[0])

        return data

    def _parse_datetime(self, dt):
        date = text.parse_datetime(dt, "%B %d, %Y %H:%M")
        if date is dt:
            date = text.parse_datetime(dt + self._year, "%d %b %H:%M %Y")
        return date


class SubscribestarUserExtractor(SubscribestarExtractor):
    """Extractor for media from a subscribestar user"""
    subcategory = "user"
    pattern = BASE_PATTERN + r"/(?!posts/)([^/?&#]+)"
    test = (
        ("https://www.subscribestar.com/subscribestar", {
            "count": ">= 20",
            "pattern": r"https://star-uploads.s\d+-us-west-\d+.amazonaws.com"
                       r"/uploads/users/11/",
            "keyword": {
                "author_id": 11,
                "author_name": "subscribestar",
                "author_nick": "SubscribeStar",
                "content": str,
                "height" : int,
                "id"     : int,
                "pinned" : bool,
                "post_id": int,
                "type"   : "re:image|video",
                "url"    : str,
                "width"  : int,
            },
        }),
        ("https://www.subscribestar.com/subscribestar", {
            "options": (("metadata", True),),
            "keyword": {"date": "type:datetime"},
            "range": "1",
        }),
        ("https://subscribestar.adult/kanashiipanda", {
            "range": "21-40",
            "count": 20,
        }),
    )

    def posts(self):
        needle_next_page = 'data-role="infinite_scroll-next_page" href="'
        page = self.request("{}/{}".format(self.root, self.item)).text

        while True:
            posts = page.split('<div class="post ')[1:]
            if not posts:
                return
            yield from posts

            url = text.extract(posts[-1], needle_next_page, '"')[0]
            if not url:
                return
            page = self.request(self.root + text.unescape(url)).json()["html"]


class SubscribestarPostExtractor(SubscribestarExtractor):
    """Extractor for media from a single subscribestar post"""
    subcategory = "post"
    pattern = BASE_PATTERN + r"/posts/(\d+)"
    test = (
        ("https://www.subscribestar.com/posts/102468", {
            "url": "612da5a98af056dd78dc846fbcfa705e721f6675",
            "keyword": {
                "author_id": 11,
                "author_name": "subscribestar",
                "author_nick": "SubscribeStar",
                "content": "re:<h1>Brand Guidelines and Assets</h1>",
                "date": "dt:2020-05-07 12:33:00",
                "extension": "jpg",
                "filename": "8ff61299-b249-47dc-880a-cdacc9081c62",
                "group": "imgs_and_videos",
                "height": 291,
                "id": 203885,
                "pinned": False,
                "post_id": 102468,
                "type": "image",
                "width": 700,
            },
        }),
        ("https://subscribestar.adult/posts/22950", {
            "url": "440d745a368e6b3e218415f593a5045f384afa0d",
            "keyword": {"date": "dt:2019-04-28 07:32:00"},
        }),
    )

    def posts(self):
        url = "{}/posts/{}".format(self.root, self.item)
        self._page = self.request(url).text
        return (self._page,)

    def _data_from_post(self, html):
        extr = text.extract_from(html)
        return {
            "post_id"    : text.parse_int(extr('data-id="', '"')),
            "author_name": text.unescape(extr('href="/', '"')),
            "author_id"  : text.parse_int(extr('data-user-id="', '"')),
            "author_nick": text.unescape(extr('alt="', '"')),
            "date"       : self._parse_datetime(extr(
                'class="section-subtitle">', '<')),
            "content"    : (extr(
                '<div class="post-content', '<div class="post-uploads')
                .partition(">")[2]),
        }
