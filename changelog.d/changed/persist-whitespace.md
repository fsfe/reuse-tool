- Reuse previously would insert a newline after a header, which is not always a
  desirable behavior. Instead of inserting a newline, Reuse will now respect the
  existing whitespace of the file where the header is being placed. When the
  license header is being added to a file for the first time, a space will be
  added after the license, but subsequent updates to the header will leave the
  whitespace alone. (#1136)
