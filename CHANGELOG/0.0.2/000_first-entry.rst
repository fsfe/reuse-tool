This is a very early development release aimed at distributing the program as
soon as possible.  Because this is the first release, the changelog is a little
empty beyond "created the program".

The program can do roughly the following:

- Detect the license of a given file through one of three methods (in order of
  precedence):

  - Information embedded in the .license file.

  - Information embedded in its header.

  - Information from the global debian/copyright file.

- Find and report all files in a project tree of which the license could not be
  found.

- Ignore files ignored by Git.

- Do some logging into STDERR.
