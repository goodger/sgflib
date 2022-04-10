======================================================
 sgflib: Smart Game Format Parser Library & Utilities
======================================================

Description
===========

For Python programmers, sgflib.py is a module containing a parser and classes
for SGF, the Smart Game Format, specifically for the game of Go.

For Go players, several utilities are included:

* sgfmerge: Merge two or more game record files into one. Works best
  when the game record files are for the same game, and contain
  variations.

* sgfnorm: Normalize an SGF file. Usful for comparing two files
  representing the same game.

* sgfsummary: Read, analyze, and summarize one or more SGF files.


Installation
============

You'll need the Python language itself, version 3.8 or higher, freely
available from http://www.python.org.

The sgflib.tgz archive contains the following:

- sgflib.py -- SGF Parser Library. Put this in a folder on Python's path.

- sgfsummary, sgfnorm, sgfmerge -- Utility tools. Put these on your PATH.

- README.txt -- Installation instructions (the file you're reading now).

- test_sgflib.py & test_data/ -- Test suite. Requires pytest to run.


Bugs & Other Issues
===================

If you have any trouble running this code, if you find (maybe fix?)
any bugs, or add any features, please contact_ the author.


To Do
=====

* Reimplement the GameTree as a data structure that's convenient for
  the user of sgflib, rather than following the file format.

* Reimplement the Cursor class? Or remove it altogether if unnecessary.

* Reimplement the parser?

  * Simplify. It works, but it seems clunky. Written early in my
    Python career.

  * Reimplement as a generator?

  * Support earlier versions of SGF?

* Titler: Populate the title (GN/game_name property) inside the SGF
  file itself, e.g.:

      player1 (2 dan, white) vs player2 (4 kyu, black +h5); W+18½; KGS; 2020-12-04

* Renamer: Rename SGF files, e.g.:

      2020-12-04 player1 · player2 +h5 W+18.sgf

* Query SGF data: Extract game & node properties & comments from .sgf
  files. Queries could be Python expressions for maximum flexibility.

* Handicap convertor? Lizzie (Leela Zero?) can't handle handicap
  stones, so this program would convert the HA[n] & AB[xx] tags to
  B[xx] moves & W[] passes. Katago via KaTrain doesn't have this
  problem though.

* Auto-label variations.

Have any suggestions? Want to help? Please contact_ the author.


Contact
=======

Project author: `David Goodger <mailto:goodger@python.org>`_.

Go Tools Project website: http://gotools.sourceforge.net.
