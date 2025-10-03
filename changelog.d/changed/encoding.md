- The encodings of files are now detected before they are read or altered.
  (#1235, #1218)
- The dependency `python-magic` has been added, alongside the optional
  dependencies `charset-normalizer` and `chardet`. So long as at least one of
  these is installed, the program will work. (#1235)
- The dependency `binaryornot` has been removed. (#1235)
