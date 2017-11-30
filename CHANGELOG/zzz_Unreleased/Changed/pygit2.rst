- ``pygit2`` added as soft dependency.  reuse remains usable without it, but the
  performance with ``pygit2`` is significantly better.  Because ``pygit2``
  has a non-Python dependency (``libgit2``), it must be installed independently
  by the user.  In the future, when reuse is packaged natively, this will not be
  an issue.
