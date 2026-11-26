"""Discord #prefab-share feed for the native asset browser.

Network work runs on a thread pool. Results are put on a queue and applied on
Blender's main thread by a bpy.app.timers poller, so no bpy calls happen off
the main thread. Message metadata and thumbnails are cached on disk under
~/NoMansSkyBaseBuilder/prefab-share, the folder earlier versions used.
"""

import json
import os
import queue
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import bpy

from .catalog_data import PREFAB_SHARE_PATH

API_URL = "https://api.djmonkey.uk"
MESSAGE_CACHE_PATH = os.path.join(PREFAB_SHARE_PATH, "messages")
THUMBNAIL_CACHE_PATH = os.path.join(PREFAB_SHARE_PATH, "thumbnails")
PREFAB_EXTENSIONS = (".json", ".txt", ".nmsprefab", ".nmsbase")
DISCORD_INVITE_URL = "https://discord.gg/kpGVRKPn5W"
DISCORD_GUILD_ID = "844499346450939904"
DISCORD_CHANNEL_ID = "1107768757482442842"
PAGE_SIZE = 20
TIMEOUT = 20

SORT_OPTIONS = (
    ("default", "Discord Order", ""),
    ("newest", "Newest", ""),
    ("oldest", "Oldest", ""),
    ("title_asc", "A-Z", ""),
    ("title_desc", "Z-A", ""),
    ("activity", "Most Comments", ""),
)

IMAGE_SIGNATURES = (
    (b"\x89PNG", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF8", ".gif"),
)


# Helpers ---
def online_access():
    return getattr(bpy.app, "online_access", True)


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "NMS-Base-Builder"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def thread_url(thread_id):
    return "https://discord.com/channels/{}/{}/threads/{}".format(
        DISCORD_GUILD_ID, DISCORD_CHANNEL_ID, thread_id
    )


def _image_extension(data):
    for signature, extension in IMAGE_SIGNATURES:
        if data.startswith(signature):
            return extension
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def _message_cache_path(thread_id):
    return os.path.join(MESSAGE_CACHE_PATH, "{}.json".format(thread_id))


def _load_cached_message(thread_id):
    try:
        with open(_message_cache_path(thread_id), "r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, ValueError):
        return None


def _save_cached_message(thread_id, message):
    try:
        os.makedirs(MESSAGE_CACHE_PATH, exist_ok=True)
        with open(_message_cache_path(thread_id), "w", encoding="utf-8") as stream:
            json.dump(message, stream)
    except OSError:
        pass


def _cached_thumbnail_path(thread_id):
    """Path of a cached thumbnail with a real image extension, or None.

    The Qt browser cached thumbnails as <id>.bin. Blender's previews need the
    right extension, so those are copied once to <id>.<ext>.
    """
    for _, extension in IMAGE_SIGNATURES + ((None, ".webp"),):
        path = os.path.join(THUMBNAIL_CACHE_PATH, thread_id + extension)
        if os.path.isfile(path):
            return path
    legacy_path = os.path.join(THUMBNAIL_CACHE_PATH, thread_id + ".bin")
    if os.path.isfile(legacy_path):
        try:
            with open(legacy_path, "rb") as stream:
                return _save_thumbnail(thread_id, stream.read())
        except OSError:
            return None
    return None


def _save_thumbnail(thread_id, data):
    extension = _image_extension(data)
    if not extension:
        return None
    os.makedirs(THUMBNAIL_CACHE_PATH, exist_ok=True)
    path = os.path.join(THUMBNAIL_CACHE_PATH, thread_id + extension)
    with open(path, "wb") as stream:
        stream.write(data)
    return path


def _match_attachments(message):
    return [
        attachment
        for attachment in (message.get("attachments") or [])
        if os.path.splitext(attachment.get("filename", ""))[1].lower() in PREFAB_EXTENSIONS
    ]


def _fetch_message(thread_id):
    url = API_URL + "/post?" + urllib.parse.urlencode({"threadId": thread_id})
    payload = json.loads(download(url).decode("utf-8"))
    return payload.get("message") or {}


def prefab_id_for(record):
    name = "{}_{}".format(record["author"], record["name"])
    return "".join(
        character if character.isalnum() or character in " -_" else "_" for character in name
    ).strip(" ._") or "shared_prefab"


class Feed:
    """State of the #prefab-share feed. One instance, shared by every view."""

    def __init__(self):
        self._executor = None
        self._results = queue.Queue()
        self._pending = 0
        self._token = 0
        self.revision = 0
        self.records = []
        self.by_id = {}
        self.next_cursor = None
        self.status = ""
        self.loading = False
        self.loaded_once = False
        self.selected_id = ""
        self.sort = "default"
        self.search = ""

    # Lifetime ---
    def shutdown(self):
        self._token += 1
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None
        if bpy.app.timers.is_registered(self._poll):
            bpy.app.timers.unregister(self._poll)

    def _submit(self, kind, function, *args):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nms_prefab_share")
        token = self._token
        self._pending += 1

        def work():
            try:
                result = (kind, token, args, function(*args), None)
            except Exception as error:
                result = (kind, token, args, None, error)
            self._results.put(result)

        self._executor.submit(work)
        if not bpy.app.timers.is_registered(self._poll):
            bpy.app.timers.register(self._poll, first_interval=0.1)

    def _poll(self):
        changed = False
        while True:
            try:
                kind, token, args, value, error = self._results.get_nowait()
            except queue.Empty:
                break
            self._pending -= 1
            if token != self._token:
                continue
            changed = True
            try:
                getattr(self, "_on_" + kind)(args, value, error)
            except Exception as handler_error:
                self.status = "Prefab share error: {}".format(handler_error)
        if changed:
            self.touch()
        return 0.1 if self._pending > 0 else None

    def touch(self):
        self.revision += 1
        _redraw_browsers()

    # Queries ---
    def visible_records(self):
        """Records with a downloadable prefab, in feed order."""
        return [record for record in self.records if record["resolved"] and record["attachments"]]

    def selected(self):
        return self.by_id.get(self.selected_id)

    def unresolved_count(self):
        return sum(1 for record in self.records if not record["resolved"])

    # Actions ---
    def refresh(self, sort=None, search=None):
        if sort is not None:
            self.sort = sort
        if search is not None:
            self.search = search
        self._token += 1
        self.records = []
        self.by_id = {}
        self.next_cursor = None
        self.selected_id = ""
        self.loaded_once = True
        if not online_access():
            self.status = "Allow Online Access in Preferences > System to browse #prefab-share."
            self.touch()
            return
        self._load_page(None)

    def ensure_loaded(self):
        if not self.loaded_once:
            self.refresh()

    def load_more(self):
        if self.next_cursor and not self.loading and online_access():
            self._load_page(self.next_cursor)

    def _load_page(self, cursor):
        query = {"limit": str(PAGE_SIZE), "sort": self.sort, "search": self.search.strip()}
        if cursor:
            query["cursor"] = cursor
        self.loading = True
        self.status = "Loading shared prefabs..."
        self._submit("threads", self._fetch_threads, query)
        self.touch()

    @staticmethod
    def _fetch_threads(query):
        url = API_URL + "/threads?" + urllib.parse.urlencode(query)
        return json.loads(download(url).decode("utf-8"))

    def _on_threads(self, args, payload, error):
        self.loading = False
        if error is not None:
            self.status = "Unable to load #prefab-share: {}".format(error)
            return
        for thread in payload.get("threads", []):
            thread_id = thread.get("id")
            if not thread_id or thread_id in self.by_id:
                continue
            creator = thread.get("creator") or {}
            record = {
                "id": thread_id,
                "name": thread.get("name") or "Untitled Prefab",
                "author": creator.get("displayName") or creator.get("username") or "Unknown author",
                "content": "",
                "attachments": [],
                "attachment_index": 0,
                "thumbnail_url": "",
                "thumbnail_path": None,
                "resolved": False,
            }
            self.records.append(record)
            self.by_id[thread_id] = record
            message = _load_cached_message(thread_id)
            if message is not None:
                self._apply_message(record, message)
            else:
                self._submit("post", self._fetch_and_cache_message, thread_id)
        self.next_cursor = payload.get("nextCursor")
        self._update_status()

    @staticmethod
    def _fetch_and_cache_message(thread_id):
        message = _fetch_message(thread_id)
        _save_cached_message(thread_id, message)
        return message

    def _on_post(self, args, message, error):
        record = self.by_id.get(args[0])
        if record is None:
            return
        if error is not None:
            record["resolved"] = True
            self.status = "Unable to load {}: {}".format(record["name"], error)
            return
        self._apply_message(record, message)
        self._update_status()

    def _apply_message(self, record, message):
        record["attachments"] = _match_attachments(message)
        record["attachment_index"] = 0
        record["content"] = message.get("content") or ""
        author = message.get("author") or {}
        record["author"] = author.get("displayName") or author.get("username") or record["author"]
        image = next(
            (
                attachment
                for attachment in (message.get("attachments") or [])
                if (attachment.get("contentType") or "").lower().startswith("image/")
            ),
            None,
        )
        record["thumbnail_url"] = image.get("url", "") if image else ""
        record["resolved"] = True
        if record["attachments"] and record["thumbnail_url"]:
            record["thumbnail_path"] = _cached_thumbnail_path(record["id"])
            if record["thumbnail_path"] is None:
                self._submit("thumbnail", self._fetch_thumbnail, record["id"], record["thumbnail_url"])

    @staticmethod
    def _fetch_thumbnail(thread_id, url):
        return _save_thumbnail(thread_id, download(url))

    def _on_thumbnail(self, args, path, error):
        record = self.by_id.get(args[0])
        if record is not None and path:
            record["thumbnail_path"] = path

    def _update_status(self):
        waiting = self.unresolved_count()
        count = len(self.visible_records())
        if waiting:
            self.status = "Checking {} shared threads...".format(waiting)
        elif count:
            self.status = "{} shared prefabs".format(count)
        else:
            self.status = "No shared prefabs found."

    def select(self, thread_id):
        self.selected_id = thread_id
        self.touch()

    def import_selected(self):
        record = self.selected()
        if record is None or not record["attachments"]:
            self.status = "Select a shared prefab with a prefab attachment."
            self.touch()
            return
        if not online_access():
            self.status = "Allow Online Access in Preferences > System to import."
            self.touch()
            return
        attachment = record["attachments"][record["attachment_index"]]
        self.status = "Downloading {}...".format(record["name"])
        self._submit("attachment", self._download_attachment, record["id"], dict(attachment))
        self.touch()

    @staticmethod
    def _download_attachment(thread_id, attachment):
        """Download an attachment, refreshing its signed URL once on a 404.

        Discord's CDN URLs expire after about a day but the cached message is
        kept forever, so a 404 means the URL went stale.
        """
        try:
            return download(attachment["url"]), None
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        message = _fetch_message(thread_id)
        _save_cached_message(thread_id, message)
        attachments = _match_attachments(message)
        fresh = next(
            (item for item in attachments if item.get("filename") == attachment.get("filename")),
            attachments[0] if attachments else None,
        )
        if fresh is None:
            raise RuntimeError("the shared prefab no longer has a matching attachment")
        return download(fresh["url"]), message

    def _on_attachment(self, args, value, error):
        record = self.by_id.get(args[0])
        if record is None:
            return
        if error is not None:
            self.status = "Unable to download {}: {}".format(record["name"], error)
            return
        data, fresh_message = value
        if fresh_message is not None:
            self._apply_message(record, fresh_message)
        try:
            prefab_id = self._write_prefab(record, data)
        except Exception as write_error:
            self.status = "Unable to import {}: {}".format(record["name"], write_error)
            return
        from .operators import place_item

        if place_item(prefab_id):
            self.status = "Imported {}".format(record["name"])
        else:
            self.status = "Saved {} to prefab-share, open a 3D View to place it.".format(record["name"])

    @staticmethod
    def _write_prefab(record, data):
        prefab_data = json.loads(data.decode("utf-8-sig"))
        if isinstance(prefab_data, list):
            prefab_data = {"Objects": prefab_data}
        if not isinstance(prefab_data, dict) or not (
            prefab_data.get("Objects") or prefab_data.get("Prefab")
        ):
            raise ValueError("the attachment does not contain a supported prefab object list")
        os.makedirs(PREFAB_SHARE_PATH, exist_ok=True)
        prefab_id = prefab_id_for(record)
        path = os.path.join(PREFAB_SHARE_PATH, prefab_id + ".nmsprefab")
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(prefab_data, stream)
        return prefab_id


def _redraw_browsers():
    from .space import redraw

    redraw()


_FEED = None


def get_feed():
    global _FEED
    if _FEED is None:
        _FEED = Feed()
    return _FEED


def shutdown():
    global _FEED
    if _FEED is not None:
        _FEED.shutdown()
        _FEED = None
