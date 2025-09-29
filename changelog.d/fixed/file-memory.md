- There used to be a specific scenario where `reuse lint` would read the
  contents of an entire file into memory. This no longer happens.
  `reuse annotate` will still read the entire file into memory. (#1229)
