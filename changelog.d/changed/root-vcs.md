- Previously when using `reuse --root PATH` where `PATH` was nested inside of a
  VCS repository, the behaviour differed per VCS, and was effectively undefined.
  Now, if `PATH` is not also the root of the repository, reuse will pretend that
  the directory is not in a VCS repository. (#1294)
