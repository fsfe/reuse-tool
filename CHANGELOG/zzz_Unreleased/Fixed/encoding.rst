- The tool no longer breaks when reading a file that has a non-UTF-8 encoding.
  Instead, ``chardet`` is used to detect the encoding before reading the file.
  If a file still has errors during decoding, those errors are silently ignored
  and replaced.
