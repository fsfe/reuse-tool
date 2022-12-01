..
  SPDX-FileCopyrightText: 2022 Nico Rikken <nico.rikken@fsfe.org>

  SPDX-License-Identifier: CC-BY-SA-4.0

==============
Helper scripts
==============

This section contains scripts and snippets to help with the usage of REUSE.
REUSE already has a lot of functionality builtin, but there are still cases where REUSE could use support from some external scripts.
A typical example is adding SPDX headers based on the information in the version control system.
This collection of scripts and snippets offers help for such situations.

.. warning::
  These scripts help you run REUSE against your codebase.
  Automatically extracted information might not resemble the truth.
  The correctness of these scripts is not guaranteed.
  Use with caution and at your own risk.

******************************
Starting point of the codebase
******************************

The first code contribution can be a worthwhile date to include in the copyright annotation.

First commit
============

Git log can show summaries of all commits.
At the moment of writing git does not allow selecting just one commit, so ``head`` is used to restrict the output.

.. SPDX-SnippetBegin
.. SPDX-Snippet-License-Identifier: CC0-1.0

.. code-block:: console

  $ git log --reverse --all | head -n 3
  commit cdcea0887e0a85149f93e734b647301a16dd893e
  Author: Carmen Bianca Bakker <carmenbianca@fsfe.org>
  Date:   Tue Oct 10 18:27:11 2017 +0200

.. SPDX-SnippetEnd

Year of first commit
====================

With a custom format just the year of the first commit can be displayed.
This output is convenient for use in larger scripts.

.. SPDX-SnippetBegin
.. SPDX-Snippet-License-Identifier: CC0-1.0

.. code-block:: console

  $ git log --reverse --date="format:%Y" --format="format:%cd" | head -n 1
  2017

.. SPDX-SnippetEnd

*******
Authors
*******

Unless the authors have signed away their copyright to a company or the project, the authors are also the copyright holders of their contributions.
So in a lot of cases it is valuable to know the original authors in order to explicitly state these copyright holders.

Commit authors
==============

Some examples on how to get information about the authors from the codebase.

Based on commit order
---------------------

Print out the authors known to git in chronological order.
Awk is used to filter out subsequent duplicate entries so each entry is shown only for the first appearance.

.. SPDX-SnippetBegin
.. SPDX-Snippet-License-Identifier: CC0-1.0

.. code-block:: console

  $ git log --reverse --all --format="%aN <%aE>" | awk '!seen[$0]++'
  Carmen Bianca Bakker <carmenbianca@fsfe.org>
  carmenbianca <carmenbianca@fsfe.org>
  Carmen Bianca Bakker <carmen@carmenbianca.eu>
  ...

.. SPDX-SnippetEnd

The same command, but now without the email addresses.

.. SPDX-SnippetBegin
.. SPDX-Snippet-License-Identifier: CC0-1.0

.. code-block:: console

  $ git log --reverse --all --format="%aN" | awk '!seen[$0]++'
  Carmen Bianca Bakker
  carmenbianca
  Sebastian Schuberth
  ...

.. SPDX-SnippetEnd

Sorted by name
--------------

All authors as known to the version control system, simply sorted by name.

.. SPDX-SnippetBegin
.. SPDX-Snippet-License-Identifier: CC0-1.0

.. code-block:: console

  $ git log --all --format="%aN <%aE>" | sort | uniq
  Adam Spiers <reuse-tool@adamspiers.org>
  Ajinkya Patil <ajinkyarangnathpatil@gmail.com>
  Alvar <8402811+oxzi@users.noreply.github.com>
  ...

.. SPDX-SnippetEnd

The same command, but now without the email addresses.

.. SPDX-SnippetBegin
.. SPDX-Snippet-License-Identifier: CC0-1.0

.. code-block:: console

  $ git log --all --format="%aN" | sort | uniq
  Adam Spiers
  Ajinkya Patil
  Alvar
  ...

.. SPDX-SnippetEnd

Authors in commit trailers like sign-off
========================================

A sign-off annotation in a commit also contains author details that can be as valuable.

.. TODO: improve this oneliner based on built-in Git options as documented in https://stackoverflow.com/a/41361273/12013233

.. SPDX-SnippetBegin
.. SPDX-Snippet-License-Identifier: CC0-1.0

.. code-block:: console

  $ git log --all | grep -i 'Signed-off-by\|Co-authored-by' | sort | uniq
      Co-authored-by: Ethel Morgan <eth@ethulhu.co.uk>
      Co-authored-by: max.mehl <max.mehl@fsfe.org>
      Co-authored-by: Max Mehl <max.mehl@fsfe.org>
      Signed-off-by: Carmen Bianca Bakker <carmenbianca.bakker@liferay.com>
      ...

.. SPDX-SnippetEnd


***********
Add headers
***********

A common use-case is to add headers to existing, modified or newly written code.

Add headers to staged files based on git settings
=================================================

This script helps you add your copyright headers right before committing the code you wrote.

The list of files staged in git can be retrieved using ``git diff --name-only --cached``, which is the basis to apply the ``reuse annotate`` command to.

Git user and email address are available through ``git config --get user.name`` and ``git config --get user.email``.

REUSE already sets the current year, so there is no need to set that explicitly.

These elements can be combined into a single command:

.. SPDX-SnippetBegin
.. SPDX-Snippet-License-Identifier: CC0-1.0

.. code-block:: console

  $ git diff --name-only --cached | xargs -I {} reuse annotate -c "$(git config --get user.name) <$(git config --get user.email)>" "{}"

.. SPDX-SnippetEnd

.. rubric:: Copyright

This page is licensed under the `Creative Commons Attribution-ShareAlike 4.0 International license <https://creativecommons.org/licenses/by-sa/4.0/>`_.
Examples, recipes, and other code in the documentation are additionally licensed under the `Creative Commons Zero v1.0 Universal License <https://creativecommons.org/choose/zero/>`_.

