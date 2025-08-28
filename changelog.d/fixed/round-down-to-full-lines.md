- Text extraction is limited to a certain number of bytes, which could happen to
  cut a text line in between a license identifier, triggering bogus "Bad
  licenses" errors. This is now avoided by "rounding down" extracted text to
  full lines of text.
