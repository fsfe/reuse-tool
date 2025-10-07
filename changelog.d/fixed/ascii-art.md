- ASCII frames around comments were broken in v6.0.0. They now work again. The
  sole condition is that the 'suffix' of a comment is identical to its 'prefix'.
  For example:

  ```
  /*******************************************\
  |*  SPDX-License-Identifier: CC-BY-SA-4.0  *|
  \*******************************************/
  ```
