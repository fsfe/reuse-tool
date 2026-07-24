- `AnnotationsItem` now preserves keys of a `REUSE.toml` `[[annotations]]` table
  that reuse does not recognise, exposing them through the new
  `custom_properties` attribute instead of discarding them.
