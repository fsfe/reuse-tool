# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2020 Tuomas Siipola <tuomas@zpl.fi>
# SPDX-FileCopyrightText: 2022 Carmen Bianca Bakker <carmenbianca@fsfe.org>
# SPDX-FileCopyrightText: 2022 Florian Snow <florian@familysnow.net>
# SPDX-FileCopyrightText: 2022 Nico Rikken <nico.rikken@fsfe.org>
# SPDX-FileCopyrightText: 2022 Pietro Albini <pietro.albini@ferrous-systems.com>
# SPDX-FileCopyrightText: 2023 DB Systel GmbH
# SPDX-FileCopyrightText: 2023 Johannes Zarl-Zierl <johannes@zarl-zierl.at>
# SPDX-FileCopyrightText: 2024 Rivos Inc.
# SPDX-FileCopyrightText: 2024 Skyler Grey <sky@a.starrysky.fyi>
# SPDX-FileCopyrightText: © 2020 Liferay, Inc. <https://liferay.com>
# SPDX-FileCopyrightText: 2025 Simon Barth <simon.barth@gmx.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Utilities related to the extraction of REUSE information out of files."""

import codecs
import contextlib
import importlib
import logging
import os
import platform
import re
import sys
from encodings import aliases, normalize_encoding
from itertools import chain
from types import ModuleType
from typing import BinaryIO, Generator, Literal, NamedTuple, cast

from .comment import _all_style_classes
from .copyright import (
    COPYRIGHT_NOTICE_PATTERN,
    CopyrightNotice,
    ReuseInfo,
    SpdxExpression,
)
from .exceptions import NoEncodingModuleError
from .i18n import _

_LOGGER = logging.getLogger(__name__)

_ENCODING_MODULES = {  # pylint: disable=invalid-name
    "python-magic": "magic",
    "file-magic": "magic",
    "charset_normalizer": "charset_normalizer",
    "chardet": "chardet",
}
if _env_encoding_module := os.environ.get("REUSE_ENCODING_MODULE"):
    # Backwards compatibility. In v6.1.2, 'magic' used to mean 'python-magic'.
    if _env_encoding_module == "magic":
        _env_encoding_module = "python-magic"
    if _env_encoding_module not in _ENCODING_MODULES:
        print(
            # TRANSLATORS: Do not translate REUSE_ENCODING_MODULE.
            _(
                "REUSE_ENCODING_MODULE must have a value in {modules}; it has"
                " '{env_module}'. Aborting."
            ).format(
                modules=list(_ENCODING_MODULES.keys()),
                env_module=_env_encoding_module,
            )
        )
        sys.exit(1)
    _ENCODING_MODULES = {  # pylint: disable=invalid-name
        _env_encoding_module: (
            "magic" if "magic" in _env_encoding_module else _env_encoding_module
        )
    }

_ENCODING_MODULE: ModuleType | None = None
_MAGIC = None
for _module in _ENCODING_MODULES.values():
    if _module == "magic" and platform.system() == "Windows":
        continue
    try:
        _ENCODING_MODULE = importlib.import_module(_module)
        break
    except ImportError:
        continue
else:
    raise NoEncodingModuleError(
        _(
            "No supported module that can detect the encoding of files could be"
            " successfully imported. Re-read the installation instructions for"
            " the reuse package, or try the following:"
        )
        + "\n\n"
        + _(
            "- If you are running a Linux distribution, try your equivalent of"
            " `apt install file` or `dnf install file`."
        )
        + "\n"
        + _(
            "- Run ` pipx install reuse[charset-normalizer]`. Replace 'pipx'"
            " with 'pip' if you are not using pipx."
        )
    )


def _detect_magic(module: ModuleType) -> Literal["python-magic", "file-magic"]:
    if hasattr(module, "from_buffer"):
        return "python-magic"
    return "file-magic"


def get_encoding_module() -> ModuleType:
    """Get the module used to detect the encodings of files."""
    return cast(ModuleType, _ENCODING_MODULE)


def _get_encoding_module_name() -> str | None:
    module = get_encoding_module()
    result = getattr(module, "__name__", None)
    if result == "magic":
        return _detect_magic(module)
    return result


def set_encoding_module(name: str) -> ModuleType:
    """Set the module used to detect the encodings of files, and return the
    module.
    """
    if name not in _ENCODING_MODULES:
        raise NoEncodingModuleError(f"'{name}' is not a valid encoding module.")
    try:
        # pylint: disable=global-statement
        global _ENCODING_MODULE
        _ENCODING_MODULE = importlib.import_module(name)
        return _ENCODING_MODULE
    except ImportError as err:
        raise NoEncodingModuleError(f"'{name}' could not be imported.") from err


if _get_encoding_module_name() == "python-magic":
    _MAGIC = get_encoding_module().Magic(mime_encoding=True)


REUSE_IGNORE_START = "REUSE-IgnoreStart"
REUSE_IGNORE_END = "REUSE-IgnoreEnd"

# REUSE-IgnoreStart

SPDX_SNIPPET_INDICATOR = b"SPDX-SnippetBegin"

_START_PATTERN = r"(?:^.*?)"
_END_PATTERN = r"\s*(?:{})*\s*$".format(
    "|".join(
        set(
            chain(
                (
                    re.escape(style.MULTI_LINE.end)
                    for style in _all_style_classes()
                    if style.MULTI_LINE.end
                ),
                # These are special endings which do not belong to specific
                # comment styles, but which we want to nonetheless strip away
                # while parsing.
                (
                    # ex: <tag value="Copyright Jane Doe">
                    r'"\s*/*>',
                    r"'\s*/*>",
                    # ex: [SPDX-License-Identifier: GPL-3.0-or-later] ::
                    r"\]\s*::",
                ),
            )
        )
    )
)
_ALL_MATCH_PATTERN = re.compile(
    r"^(?P<prefix>.*?)(?:SPDX-\S+:|Copyright|©).*$",
    re.MULTILINE,
)
_COPYRIGHT_NOTICE_PATTERN = re.compile(
    _START_PATTERN + COPYRIGHT_NOTICE_PATTERN.pattern + _END_PATTERN,
)
_LICENSE_IDENTIFIER_PATTERN = re.compile(
    _START_PATTERN
    + r"SPDX-License-Identifier:\s*(?P<value>.*?)"
    + _END_PATTERN,
)
_CONTRIBUTOR_PATTERN = re.compile(
    _START_PATTERN + r"SPDX-FileContributor:\s*(?P<value>.*?)" + _END_PATTERN,
)
# The keys match the relevant attributes of ReuseInfo.
_SPDX_TAGS: dict[str, re.Pattern] = {
    "spdx_expressions": _LICENSE_IDENTIFIER_PATTERN,
    "contributor_lines": _CONTRIBUTOR_PATTERN,
}
_LICENSEREF_PATTERN = re.compile(r"LicenseRef-[a-zA-Z0-9-.]+$")
_NEWLINE_PATTERN = re.compile(r"\r\n?")

_LINE_ENDINGS = ("\r\n", "\r", "\n")
_LINE_ENDINGS_ASCII = tuple(ending.encode("ascii") for ending in _LINE_ENDINGS)
_LINE_ENDINGS_UTF_16_LE = tuple(
    ending.encode("utf_16_le") for ending in _LINE_ENDINGS
)
_LINE_ENDINGS_UTF_32_LE = tuple(
    ending.encode("utf_32_le") for ending in _LINE_ENDINGS
)
_LINE_ENDING_ENCODINGS_ASCII = set()
for _name in set(chain.from_iterable(aliases.aliases.items())):
    with contextlib.suppress(Exception):
        if codecs.encode("\r\n", _name) == b"\r\n":
            _LINE_ENDING_ENCODINGS_ASCII.add(_name)
_LINE_ENDING_ENCODINGS_ASCII.add("utf_8_sig")
_LINE_ENDING_ENCODINGS_UTF_16_LE = {
    "u16",
    "utf16",
    "utf_16",
    "unicodelittleunmarked",
    "utf_16le",
    "utf_16_le",
}
_LINE_ENDING_ENCODINGS_UTF_32_LE = {
    "u32",
    "utf32",
    "utf_32",
    "utf_32le",
    "utf_32_le",
}


#: Default chunk size for reading files.
CHUNK_SIZE = 1024 * 64
#: Default line size for reading files.
LINE_SIZE = 1024
#: Default chunk size used to heuristically detect file type, encoding, et
#: cetera.
HEURISTICS_CHUNK_SIZE = 1024 * 2


class FilterBlock(NamedTuple):
    """A simple tuple that holds a block of text, and whether that block of text
    is in an ignore block.
    """

    text: str
    in_ignore_block: bool


def filter_ignore_block(
    text: str, in_ignore_block: bool = False
) -> FilterBlock:
    """Filter out blocks beginning with REUSE_IGNORE_START and ending with
    REUSE_IGNORE_END to remove lines that should not be treated as copyright and
    licensing information.

    Args:
        text: The text out of which the ignore blocks must be filtered.
        in_ignore_block: Whether the text is already in an ignore block. This is
            useful when you parse subsequent chunks of text, and one chunk does
            not close the ignore block.

    Returns:
        A :class:`FilterBlock` tuple that contains the filtered text and a
        boolean that signals whether the ignore block is still open.
    """
    ignore_start: int | None = None if not in_ignore_block else 0
    ignore_end: int | None = None
    if REUSE_IGNORE_START in text:
        ignore_start = text.index(REUSE_IGNORE_START)
    if REUSE_IGNORE_END in text:
        ignore_end = text.index(REUSE_IGNORE_END) + len(REUSE_IGNORE_END)
    if ignore_start is None:
        return FilterBlock(text, False)
    if ignore_end is None:
        return FilterBlock(text[:ignore_start], True)
    if ignore_start < ignore_end:
        text_before_block = text[:ignore_start]
        text_after_block, in_ignore_block = filter_ignore_block(
            text[ignore_end:], False
        )
        return FilterBlock(
            text_before_block + text_after_block, in_ignore_block
        )
    rest = text[ignore_start + len(REUSE_IGNORE_START) :]
    if REUSE_IGNORE_END in rest:
        ignore_end = rest.index(REUSE_IGNORE_END) + len(REUSE_IGNORE_END)
        text_before_block = text[:ignore_start]
        text_after_block, in_ignore_block = filter_ignore_block(
            rest[ignore_end:]
        )
        return FilterBlock(
            text_before_block + text_after_block, in_ignore_block
        )
    return FilterBlock(text[:ignore_start], True)


def extract_reuse_info(text: str) -> ReuseInfo:
    """Extract REUSE information from a multi-line text block.

    Raises:
        ExpressionError: if an SPDX expression could not be parsed.
        ParseError: if an SPDX expression could not be parsed.
    """
    notices: set[CopyrightNotice] = set()
    expressions: set[SpdxExpression] = set()
    contributors: set[str] = set()

    for possible in _ALL_MATCH_PATTERN.finditer(text):
        possible_text = possible.group()
        prefix = possible.group("prefix").strip()
        reversed_prefix = prefix[::-1]
        possible_text = possible_text.removesuffix(reversed_prefix)
        if match := _COPYRIGHT_NOTICE_PATTERN.match(possible_text):
            notices.add(CopyrightNotice.from_match(match))
        elif match := _LICENSE_IDENTIFIER_PATTERN.match(possible_text):
            expressions.add(SpdxExpression(match.group("value")))
        elif match := _CONTRIBUTOR_PATTERN.match(possible_text):
            contributors.add(match.group("value"))

    return ReuseInfo(
        spdx_expressions=expressions,
        copyright_notices=notices,
        contributor_lines=contributors,
    )


def _read_chunks(
    fp: BinaryIO,
    chunk_size: int = CHUNK_SIZE,
    line_size: int = LINE_SIZE,
    newline: bytes = b"\n",
) -> Generator[bytes, None, None]:
    """Read and yield somewhat equal-sized chunks from (realistically) a file.
    The chunks always split at a newline where possible.

    An amount of bytes equal to *chunk_size* is always read into the chunk if
    *fp* contains that many bytes. An additional *line_size* or lesser amount of
    bytes is also read into the chunk, up to the next newline character.

    *newline* is the line separator that is (expected to be) used in the input.
    """
    newline_len = len(newline)
    while True:
        chunk = fp.read(chunk_size)
        if not chunk:
            break
        end_chunk_pos = fp.tell()
        remainder = fp.read(line_size)
        newline_idx = remainder.find(newline)
        if newline_idx != -1:
            remainder = remainder[: newline_idx + newline_len]
            fp.seek(end_chunk_pos + newline_idx + newline_len)
        chunk += remainder
        yield chunk


def _detect_encoding_magic(mime_encoding: str, chunk: bytes) -> str | None:
    if mime_encoding == "binary":
        return None
    if mime_encoding == "utf-8" and chunk[:3] == b"\xef\xbb\xbf":
        mime_encoding += "-sig"
    # Python and magic disagree on what 'le' means. For magic, it means a UTF-16
    # block prefixed with a BOM. For Python, that's what 'utf-16' is, and
    # 'utf_16_le' is a little endian block _without_ BOM prefix.
    elif mime_encoding == "utf-16le" and chunk[:2] == b"\xff\xfe":
        mime_encoding = "utf-16"
    elif mime_encoding == "utf-32le" and chunk[:4] == b"\xff\xfe\x00\x00":
        mime_encoding = "utf-32"
    else:
        # This nifty function gets the (in Python) standardised name for an
        # encoding. 'iso-8859-1' becomes 'iso8859-1'.
        try:
            codec_info = codecs.lookup(mime_encoding)
            mime_encoding = codec_info.name
        except LookupError:
            # Fallback.
            mime_encoding = "utf-8"
    return normalize_encoding(mime_encoding)


def _detect_encoding_python_magic(chunk: bytes) -> str | None:
    result: str = _MAGIC.from_buffer(chunk)  # type: ignore[union-attr]
    return _detect_encoding_magic(result, chunk)


def _detect_encoding_file_magic(chunk: bytes) -> str | None:
    result: str = get_encoding_module().detect_from_content(chunk).encoding
    return _detect_encoding_magic(result, chunk)


def _detect_encoding_charset_normalizer(chunk: bytes) -> str | None:
    matches = get_encoding_module().from_bytes(  # type: ignore[union-attr]
        chunk,
    )
    best = matches.best()
    if best is not None:
        result: str = best.encoding
        if result == "utf_8" and best.bom:
            result += "_sig"
        return result
    return None


def _detect_encoding_chardet(chunk: bytes) -> str | None:
    dict_ = get_encoding_module().detect(chunk)  # type: ignore[union-attr]
    result: str | None = dict_.get("encoding")
    if result is None:
        return None
    try:
        codec_info = codecs.lookup(result)
        result = codec_info.name
    except LookupError:
        # Fallback.
        result = "utf-8"
    return normalize_encoding(result)


def detect_encoding(chunk: bytes) -> str | None:
    """Find the encoding of the bytes chunk, and return it as normalised name.
    See :func:`encodings.normalize_encoding`. If no encoding could be found,
    return :const:`None`.

    If the chunk is empty or the encoding of the chunk is ASCII, ``'utf_8'`` is
    returned.
    """
    # If the file is empty, assume UTF-8.
    if not chunk:
        return "utf_8"

    result: str | None = None
    if _get_encoding_module_name() == "python-magic":
        result = _detect_encoding_python_magic(chunk)
    elif _get_encoding_module_name() == "file-magic":
        result = _detect_encoding_file_magic(chunk)
    elif _get_encoding_module_name() == "charset_normalizer":
        result = _detect_encoding_charset_normalizer(chunk)
    elif _get_encoding_module_name() == "chardet":
        result = _detect_encoding_chardet(chunk)
    else:
        # This code should technically never be reached.
        raise NoEncodingModuleError()

    if result in ["ascii", "us_ascii"]:
        result = "utf_8"
    return result


def detect_newline(chunk: bytes, encoding: str = "ascii") -> str:
    """Return one of ``'\\n'``, ``'\\r'`` or ``'\\r\\n'`` depending on the line
    endings used in *chunk*. Return :const:`os.linesep` if there are no line
    endings.
    """
    line_endings: tuple[bytes, ...] | None = None
    encoding = normalize_encoding(encoding.lower())
    # This step is part optimalisation, part dealing with BOMs.
    if encoding in _LINE_ENDING_ENCODINGS_ASCII:
        line_endings = _LINE_ENDINGS_ASCII
    elif encoding in _LINE_ENDING_ENCODINGS_UTF_16_LE:
        line_endings = _LINE_ENDINGS_UTF_16_LE
    elif encoding in _LINE_ENDING_ENCODINGS_UTF_32_LE:
        line_endings = _LINE_ENDINGS_UTF_32_LE

    if line_endings is not None:
        for line_ending_bytes in line_endings:
            if line_ending_bytes in chunk:
                return line_ending_bytes.decode(encoding)
    else:
        for line_ending_str in _LINE_ENDINGS:
            if line_ending_str.encode(encoding) in chunk:
                return line_ending_str
    return os.linesep


def reuse_info_of_file(
    fp: BinaryIO,
    chunk_size: int = CHUNK_SIZE,
    line_size: int = LINE_SIZE,
) -> ReuseInfo:
    """Read from *fp* to extract REUSE information. It is read in chunks of
    *chunk_size*, additionally reading up to *line_size* until the next newline.

    This function decodes the binary data into UTF-8 and removes REUSE ignore
    blocks before attempting to extract the REUSE information.
    """
    position = fp.tell()
    heuristics_chunk = fp.read(HEURISTICS_CHUNK_SIZE)
    fp.seek(position)  # Reset position.
    encoding = detect_encoding(heuristics_chunk)
    filename = getattr(fp, "name", None)
    if encoding is None:
        if filename:
            _LOGGER.info(
                _(
                    "'{path}' was detected as a binary file; not searching its"
                    " contents for REUSE information."
                ).format(path=filename)
            )
        return ReuseInfo()

    newline = detect_newline(heuristics_chunk, encoding=encoding)

    if filename:
        _LOGGER.debug(
            _(
                "extracting REUSE information from '{path}'"
                " (encoding {encoding}, encoding module {module},"
                " newline {newline})"
            ).format(
                path=filename,
                encoding=repr(encoding),
                module=repr(_get_encoding_module_name()),
                newline=repr(newline),
            )
        )
    in_ignore_block = False
    reuse_infos: list[ReuseInfo] = []
    for chunk in _read_chunks(
        fp,
        chunk_size=chunk_size,
        line_size=line_size,
        newline=newline.encode(encoding),
    ):
        text = chunk.decode(encoding, errors="replace")
        text = _NEWLINE_PATTERN.sub("\n", text)
        text, in_ignore_block = filter_ignore_block(text, in_ignore_block)
        reuse_infos.append(extract_reuse_info(text))
    return ReuseInfo().union(*reuse_infos)


def contains_reuse_info(text: str) -> bool:
    """The text contains REUSE info."""
    return bool(extract_reuse_info(filter_ignore_block(text).text))


# REUSE-IgnoreEnd
