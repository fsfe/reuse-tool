- The `--source` option of `reuse download` now also works for non-custom
  licenses (i.e. licenses that do not start with `LicenseRef-`). (#1276)
- Previously when a directory was passed to the `--source` option of
  `reuse download`, the files within had to equal `<identifier>.txt`. Now, the
  files may also be named `<identifier>`. (#1276)
