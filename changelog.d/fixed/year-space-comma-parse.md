- Fixed two corner cases of parsing year ranges in copyright notices that could
  cause unintended errors. These errors occurred when there was too much spacing
  inside of a year range (e.g. `© 2017  -  2020 Jane Doe`, with more than one
  space preceding and/or succeeding the separator) or when there wasn't spacing
  following the comma after a year range (e.g. `© 2017-2020,Jane Doe`).
