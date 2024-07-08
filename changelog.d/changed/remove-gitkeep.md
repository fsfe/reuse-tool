- `.gitkeep` is no longer ignored, because this is not defined in the
  specification. However, if `.gitkeep` is a 0-size file, it will remain ignored
  (because 0-size files are ignored). (#1043)
