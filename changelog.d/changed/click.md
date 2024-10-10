- Switched from `argparse` to `click` for handling the CLI. The CLI should still
  handle the same, with identical options and arguments, but some stuff changed
  under the hood. (#1084)

  Find here a small list of differences:

  - `-h` is no longer shorthand for `--help`.
  - `--version` now outputs "reuse, version X.Y.Z", followed by a licensing
    blurb on different paragraphs.
  - Some options are made explicitly mutually exclusive, such as `annotate`'s
    `--skip-unrecognised` and `--style`, and `download`'s `--output` and
    `--all`.
  - Subcommands which take a list of things (files, license) as arguments, such
    as `annotate`, `lint-file`, or `download`, now also allow zero arguments.
    This will do nothing, but can be useful in scripting.
  - `annotate` and `lint-file` now also take directories as arguments. This will
    do nothing, but can be useful in scripting.
