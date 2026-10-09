"""Compile locale/*/LC_MESSAGES/django.po into django.mo without GNU gettext.

Django's own `compilemessages` needs the gettext tools (msgfmt). This command uses only
the standard library, so translations can be rebuilt on any machine with Python.
"""

import ast
import struct
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def parse_po(text):
    """Return {msgid: msgstr} where plural entries use "\\0"-joined forms, as .mo files expect."""
    entries, entry, key = {}, {}, None

    def flush():
        if "msgid" in entry and not entry.get("fuzzy"):
            msgid = entry["msgid"]
            if "msgid_plural" in entry:
                msgid += "\0" + entry["msgid_plural"]
                forms = [entry[k] for k in sorted(k for k in entry if k.startswith("msgstr["))]
                msgstr = "\0".join(forms)
            else:
                msgstr = entry.get("msgstr", "")
            if msgstr.replace("\0", ""):
                entries[msgid] = msgstr
        entry.clear()

    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            flush()
            key = None
        elif line.startswith("#,") and "fuzzy" in line:
            entry["fuzzy"] = True
        elif line.startswith("#"):
            continue
        elif line.startswith('"'):
            if key is None:
                raise CommandError(f"Line {number}: continuation without a keyword")
            entry[key] += ast.literal_eval(line)
        else:
            keyword, _, value = line.partition(" ")
            if keyword == "msgid" and "msgid" in entry:
                flush()
            key = keyword
            entry[key] = ast.literal_eval(value)
    flush()
    return entries


def write_mo(entries, path):
    keys = sorted(entries)
    ids = b"".join(k.encode() + b"\0" for k in keys)
    strs = b"".join(entries[k].encode() + b"\0" for k in keys)
    header_size = 7 * 4
    table_size = len(keys) * 8
    ids_start = header_size + 2 * table_size
    strs_start = ids_start + len(ids)
    id_table, str_table, id_offset, str_offset = [], [], 0, 0
    for k in keys:
        encoded_id, encoded_str = k.encode(), entries[k].encode()
        id_table += [len(encoded_id), ids_start + id_offset]
        str_table += [len(encoded_str), strs_start + str_offset]
        id_offset += len(encoded_id) + 1
        str_offset += len(encoded_str) + 1
    output = struct.pack("Iiiiiii", 0x950412DE, 0, len(keys), header_size, header_size + table_size, 0, 0)
    output += struct.pack(f"{len(id_table)}i", *id_table) + struct.pack(f"{len(str_table)}i", *str_table)
    path.write_bytes(output + ids + strs)


class Command(BaseCommand):
    help = "Compile .po translation files into .mo files (no gettext tools needed)."

    def handle(self, *args, **options):
        for locale_dir in settings.LOCALE_PATHS:
            for po_path in sorted(Path(locale_dir).glob("*/LC_MESSAGES/*.po")):
                entries = parse_po(po_path.read_text(encoding="utf-8"))
                write_mo(entries, po_path.with_suffix(".mo"))
                self.stdout.write(f"Compiled {po_path} ({len(entries) - 1} messages)")
