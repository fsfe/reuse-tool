- `ReuseTOML.from_toml` no longer exposes tomlkit's style-preserving objects.
  The values parsed from a `REUSE.toml` file are now plain Python objects. This
  raises the minimum required version of tomlkit to 0.11.7.
