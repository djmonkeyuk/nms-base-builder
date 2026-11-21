"""Xbox Game Pass (Microsoft Store) save files.

Game Pass keeps saves in the Xbox "wgs" layout:

    %LOCALAPPDATA%/Packages/HelloGames.NoMansSky_*/SystemAppData/wgs/<account>/
        containers.index            one entry per save, e.g. Slot1Auto, Slot1Manual
        <directory guid>/
            container.<n>           names the "data" and "meta" blobs of that save
            <data guid>             the save itself, same compressed format as a Steam save.hg
            <meta guid>             small header, holds the decompressed size of the data

A save is written like the game does it, as new blob files with new names plus a new
container.<n+1>, and containers.index is updated last. Because the file names change on
every write, the rest of the save editor refers to a Game Pass save by a link,
"gamepass:<account folder>|<save identifier>", which is resolved to the current files
whenever they are needed.
"""

import os
import re
import shutil
import struct
import time
import uuid
from datetime import datetime
from pathlib import Path

LINK_PREFIX = "gamepass:"
INDEX_FILE = "containers.index"
INDEX_VERSION = 14
SLOT_PATTERN = re.compile(r"Slot(\d+)(Auto|Manual)")

# sync states of a containers.index entry
SYNC_STATE_SYNCED = 1
SYNC_STATE_MODIFIED = 2

# chunk header of the compressed save data, shared with Steam saves
DATA_MAGIC = 0xFEEDA1E5
# the meta blob stores the decompressed size of the data at this offset
META_SIZE_OFFSET = 16

BLOB_NAME_BYTES = 128


# Finding saves ---
def get_packages_folder():
    local_app_data = os.environ.get("LOCALAPPDATA")
    return Path(local_app_data) / "Packages" if local_app_data else None


def find_account_folders():
    """Every Game Pass account folder on this machine, [] when Game Pass isn't installed."""
    packages = get_packages_folder()
    if packages is None or not packages.is_dir():
        return []

    folders = []
    for package in packages.glob("HelloGames.NoMansSky_*"):
        wgs = package / "SystemAppData" / "wgs"
        if not wgs.is_dir():
            continue
        for folder in wgs.iterdir():
            if (folder / INDEX_FILE).is_file():
                folders.append(folder)
    return folders


def is_account_folder(folder):
    return (Path(folder) / INDEX_FILE).is_file()


def get_account_label(folder):
    return f"Game Pass ( {Path(folder).name[-3:]} )"


def get_save_slots(folder):
    """{slot number: [links]} for every save slot listed in the account's containers.index."""
    index = ContainersIndex(folder)
    slots = {}
    for entry in index.entries:
        match = SLOT_PATTERN.fullmatch(entry.identifier)
        if match is None:
            continue
        slots.setdefault(int(match.group(1)), []).append(make_link(folder, entry.identifier))
    return slots


# Links ---
def make_link(folder, identifier):
    return f"{LINK_PREFIX}{folder}|{identifier}"


def is_link(link):
    return str(link).startswith(LINK_PREFIX)


def parse_link(link):
    folder, identifier = str(link)[len(LINK_PREFIX):].rsplit("|", 1)
    return Path(folder), identifier


def get_link_name(link):
    return parse_link(link)[1]


def resolve_data_path(link):
    """Path of the file currently holding the save data."""
    return SaveBlobs(link).data_path


def get_modified_time(link):
    folder, identifier = parse_link(link)
    return ContainersIndex(folder).find(identifier).last_modified


# Binary helpers ---
class _Reader:
    def __init__(self, data, name):
        self.data = data
        self.name = name
        self.offset = 0

    def read(self, size):
        if self.offset + size > len(self.data):
            raise ValueError(f"{self.name} is shorter than expected")
        chunk = self.data[self.offset:self.offset + size]
        self.offset += size
        return chunk

    def unpack(self, fmt):
        return struct.unpack(fmt, self.read(struct.calcsize(fmt)))[0]

    # a utf-16 string prefixed by its length in characters
    def string(self):
        return self.read(self.unpack("<i") * 2).decode("utf-16-le")


def _pack_string(text):
    encoded = text.encode("utf-16-le")
    return struct.pack("<i", len(encoded) // 2) + encoded


def guid_file_name(guid_bytes):
    # guids are stored in .NET byte order, files are named by the guid's uppercase hex
    return uuid.UUID(bytes_le=bytes(guid_bytes)).hex.upper()


def _now_filetime():
    return int((time.time() + 11644473600) * 10_000_000)


def get_decompressed_size(packed):
    """Total decompressed size of chunked save data, read from its chunk headers."""
    size = 0
    offset = 0
    while offset + 16 <= len(packed):
        magic, compressed_size, decompressed_size, _ = struct.unpack_from("<IIII", packed, offset)
        if magic != DATA_MAGIC:
            raise ValueError("Save data is not in the expected compressed format")
        size += decompressed_size
        offset += 16 + compressed_size
    return size


def _write_file(path, data):
    with open(path, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


# containers.index ---
class ContainerEntry:
    def __init__(self, reader):
        self.identifier = reader.string()
        self.identifier_2 = reader.string()
        self.sync_hex = reader.string()
        self.extension = reader.unpack("<B")
        self.sync_state = reader.unpack("<i")
        self.directory_guid = reader.read(16)
        self.last_modified = reader.unpack("<q")
        self.unknown = reader.read(8)
        self.total_size = reader.unpack("<q")

    def pack(self):
        return b"".join((
            _pack_string(self.identifier),
            _pack_string(self.identifier_2),
            _pack_string(self.sync_hex),
            struct.pack("<B", self.extension),
            struct.pack("<i", self.sync_state),
            self.directory_guid,
            struct.pack("<q", self.last_modified),
            self.unknown,
            struct.pack("<q", self.total_size),
        ))


class ContainersIndex:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.path = self.folder / INDEX_FILE
        reader = _Reader(self.path.read_bytes(), INDEX_FILE)

        self.version = reader.unpack("<i")
        if self.version != INDEX_VERSION:
            raise ValueError(f"Unsupported {INDEX_FILE} version {self.version}")
        count = reader.unpack("<q")
        self.process_identifier = reader.string()
        self.last_modified = reader.unpack("<q")
        self.sync_state = reader.unpack("<i")
        self.account_guid = reader.string()
        self.footer = reader.read(8)
        self.entries = [ContainerEntry(reader) for _ in range(count)]
        # anything after the entries is kept as is
        self.trailing = reader.data[reader.offset:]

    def find(self, identifier):
        for entry in self.entries:
            if entry.identifier == identifier:
                return entry
        raise ValueError(f"{identifier} not found in {INDEX_FILE}")

    def get_directory(self, entry):
        return self.folder / guid_file_name(entry.directory_guid)

    def pack(self):
        return b"".join((
            struct.pack("<i", self.version),
            struct.pack("<q", len(self.entries)),
            _pack_string(self.process_identifier),
            struct.pack("<q", self.last_modified),
            struct.pack("<i", self.sync_state),
            _pack_string(self.account_guid),
            self.footer,
            *(entry.pack() for entry in self.entries),
            self.trailing,
        ))


# container.<n> ---
class BlobContainer:
    def __init__(self, directory, extension):
        self.directory = Path(directory)
        self.path = self.directory / f"container.{extension}"
        reader = _Reader(self.path.read_bytes(), self.path.name)

        self.header = reader.unpack("<i")
        count = reader.unpack("<i")
        # name: (cloud guid, local guid), in file order
        self.blobs = {}
        for _ in range(count):
            name = reader.read(BLOB_NAME_BYTES).decode("utf-16-le").split("\x00", 1)[0]
            cloud_guid = reader.read(16)
            local_guid = reader.read(16)
            self.blobs[name] = (cloud_guid, local_guid)

    def get_blob_path(self, name):
        if name not in self.blobs:
            return None
        return self.directory / guid_file_name(self.blobs[name][1])

    def pack(self):
        parts = [struct.pack("<i", self.header), struct.pack("<i", len(self.blobs))]
        for name, (cloud_guid, local_guid) in self.blobs.items():
            encoded = name.encode("utf-16-le")
            if len(encoded) > BLOB_NAME_BYTES:
                raise ValueError(f"Blob name {name} is too long")
            parts += [encoded.ljust(BLOB_NAME_BYTES, b"\x00"), cloud_guid, local_guid]
        return b"".join(parts)


class SaveBlobs:
    """The index entry, container and data/meta files of one save."""

    def __init__(self, link):
        self.folder, self.identifier = parse_link(link)
        self.index = ContainersIndex(self.folder)
        self.entry = self.index.find(self.identifier)
        self.directory = self.index.get_directory(self.entry)
        self.container = BlobContainer(self.directory, self.entry.extension)
        self.data_path = self.container.get_blob_path("data")
        self.meta_path = self.container.get_blob_path("meta")
        if self.data_path is None or not self.data_path.is_file():
            raise ValueError(f"Save data of {self.identifier} is missing")


# Writing ---
def patch_meta(meta, old_data, new_data):
    """Meta with its decompressed size updated for new_data.

    The size is only changed when the meta holds the old data's size where it's expected,
    so a meta laid out differently is left untouched.
    """
    if meta is None or len(meta) < META_SIZE_OFFSET + 4:
        return meta
    stored_size = struct.unpack_from("<I", meta, META_SIZE_OFFSET)[0]
    if stored_size != get_decompressed_size(old_data):
        return meta
    patched = bytearray(meta)
    struct.pack_into("<I", patched, META_SIZE_OFFSET, get_decompressed_size(new_data))
    return bytes(patched)


def write_save(link, data, meta=None):
    """Replace a save's data, and its meta when given, else the current meta is updated to match.

    New files are written first and containers.index is written last, so if anything fails
    before that the game still sees the old save. Old files are removed at the end.
    """
    blobs = SaveBlobs(link)
    old_data = blobs.data_path.read_bytes()
    if meta is None and blobs.meta_path is not None:
        meta = patch_meta(blobs.meta_path.read_bytes(), old_data, data)

    new_contents = {"data": data}
    if meta is not None:
        new_contents["meta"] = meta

    # new blob files, other blobs of the container are kept as they are
    container = blobs.container
    old_container_path = container.path
    old_files = [blobs.container.get_blob_path(name) for name in new_contents]
    new_files = []
    try:
        for name, content in new_contents.items():
            guid = uuid.uuid4()
            path = blobs.directory / guid.hex.upper()
            _write_file(path, content)
            new_files.append(path)
            # a zero cloud guid marks the blob as not uploaded yet
            container.blobs[name] = (bytes(16), guid.bytes_le)

        entry = blobs.entry
        entry.extension = 1 if entry.extension >= 255 else entry.extension + 1
        container.path = blobs.directory / f"container.{entry.extension}"
        _write_file(container.path, container.pack())
        new_files.append(container.path)

        now = _now_filetime()
        if entry.sync_state == SYNC_STATE_SYNCED:
            entry.sync_state = SYNC_STATE_MODIFIED
        entry.last_modified = now
        entry.total_size = sum(
            path.stat().st_size
            for name in container.blobs
            if (path := container.get_blob_path(name)) is not None and path.is_file()
        )
        blobs.index.last_modified = now

        # the index is swapped in with one rename, this is the moment the new save takes over
        temp_index = blobs.index.path.with_name(INDEX_FILE + ".tmp")
        _write_file(temp_index, blobs.index.pack())
        os.replace(temp_index, blobs.index.path)
    except Exception:
        for path in new_files:
            try:
                os.remove(path)
            except OSError:
                pass
        raise

    for path in [old_container_path] + old_files:
        try:
            if path is not None:
                os.remove(path)
        except OSError:
            pass


# Backups ---
def get_backup_folder(link):
    """Backups live outside the Packages folder so the Xbox app never sees them."""
    folder, _ = parse_link(link)
    local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home())
    backup_folder = Path(local_app_data) / "NMS Base Builder" / "gamepass_backups" / folder.name
    backup_folder.mkdir(parents=True, exist_ok=True)
    return backup_folder


def make_backup(link, suffix=None):
    """Copy a save's data and meta into the backup folder, returns (data backup, meta backup)."""
    blobs = SaveBlobs(link)
    backup_folder = get_backup_folder(link)
    suffix = suffix or datetime.now().strftime("d-%Y-%m-%d_t-%H-%M-%S-%f")[:-3]

    data_backup = backup_folder / f"{blobs.identifier}.data.{suffix}.blender.bak"
    shutil.copy2(blobs.data_path, data_backup)

    meta_backup = None
    if blobs.meta_path is not None and blobs.meta_path.is_file():
        meta_backup = backup_folder / f"{blobs.identifier}.meta.{suffix}.blender.bak"
        shutil.copy2(blobs.meta_path, meta_backup)
    return data_backup, meta_backup


def restore_backup(link, backup):
    data_backup, meta_backup = backup
    meta = Path(meta_backup).read_bytes() if meta_backup is not None else None
    write_save(link, Path(data_backup).read_bytes(), meta)
