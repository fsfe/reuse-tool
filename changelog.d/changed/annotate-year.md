- The behaviour of the `--year` option to `reuse annotate`is now different.
  Previously, you could define `--year <year>` multiple times. Now you can only
  do so once, but the value may be a string containing multiple years or a range
  of years. (#1145)
- `reuse annotate --merge-copyrights` works more efficiently now, capable of
  better heuristics to detect years and year ranges. (#1145)
- `reuse annotate --merge-copyrights` no longer adds spacing around the merged
  year ranges. i.e. `2017-2025`, not `2017 - 2025`. (#1145)
