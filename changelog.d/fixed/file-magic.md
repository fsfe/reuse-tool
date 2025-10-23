- When `file-magic` is installed simultaneously with `python-magic`, the tool
  used to misbehave (read: crash), because either one of them could be imported
  on `import magic`. This misbehaviour no longer happens. (#1264)
