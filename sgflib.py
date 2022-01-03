#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# sgflib.py (Smart Game Format parser & utility library)
# Copyright © 2000-2021 David John Goodger (goodger@python.org)
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# (lgpl.txt) along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# The license is currently available on the Internet at:
#     http://www.gnu.org/copyleft/lesser.html

"""
====================================================
 Smart Game Format Parser & Utility Library: sgflib
====================================================

version 2.0a (2021-01-13~)

Homepage: http://gotools.sourceforge.net

Copyright © 2000-2021 David Goodger (goodger@python.org; "goodger" on KGS,
"davidg" on IGS). sgflib.py comes with ABSOLUTELY NO WARRANTY. This is free
software, and you are welcome to redistribute it and/or modify it under the
terms of the GNU Lesser General Public License; see the source code for
details.


Description
===========

This library contains a parser and classes for SGF, the Smart Game Format, file
format 4 (FF[4]). SGF is a text only, tree based file format designed to store
game records of board games for two players, most commonly for the game of Go.
(See `the official SGF specification <https://www.red-bean.com/sgf/>`_.)

Given a bytestring containing a complete SGF data instance (the contents of a
.sgf file), the `Parser` class will create a `Collection` object consisting of
one or more `GameTree` instances (one per game in the SGF file), each
containing a sequence of `Node` instances and (optionally) two or more branch
`GameTree` objects (variations). Branches begin immediately following the last
`Node` in the main `GameTree` sequence. Each `Node` contains a mapping of
properties, ID-value pairs. All property values are lists, and can have
multiple entries.

Tree traversal methods are provided through the `Cursor` class.

The default representation (using ``str()``/``bytes()`` or ``print()``) of
each class of SGF objects is the Smart Game Format itself.

The parser does not require valid SGF, nor does it validate the SGF data
supplied. The construction classes do not validate the resulting SGF.

In addition, this library contains several utility classes:

* SummaryCLI: Summarize one or more SGF files.

* NormalizerCLI: Put an SGF collection into a normalized form.

* MergerCLI: Merge two or more SGF game trees into one.

.. * LabelerCLI: Label variations in an SGF file (collection of games).
"""


# Revision History:
#
# * 2.0a (2021-01-13~): Rewrite for Python 3.0. Modernized.
#
# * 1.0 (2000-03-27): First public release. Ready for prime time.
#
# * 0.1 (2000-01-16): Initial idea & started coding.


import sys
import os
import os.path
import warnings
import argparse
import datetime
import re
import textwrap
import collections
import itertools
import math
from copy import deepcopy


TEXT_ENCODING = 'UTF-8'
"""Encoding used for all text output."""

NAME_ENCODING = 'ASCII'
"""Encoding used for all property names and non-text values."""

PRETTY_INDENT_SPACES = 2
"""Per-level indent for pretty-formatted output."""


class Error(Exception):
    """Base class for sgflib exceptions."""
    pass

# Parsing Exceptions

class ParseError(Error):
    """Base class for parsing exceptions."""
    pass

class EndOfDataParseError(ParseError):
    """Raised by `Parser.parse_branches()`, `Parser.parse_node()`."""
    pass

class TreeParseError(ParseError):
    """Raised by `Parser.parse_game_tree()`."""
    pass

class NodePropertyParseError(ParseError):
    """Raised by `Parser.parse_node()`."""
    pass

class PropertyValueParseError(ParseError):
    """Raised by `Parser.parsePropertyValue()`."""
    pass

# Tree Construction Exceptions

class TreeConstructionError(Error):
    """Base class for game tree construction exceptions."""
    pass

class NodeConstructionError(TreeConstructionError):
    """Raised by `Node.update()`."""
    pass

class DuplicatePropertyError(TreeConstructionError):
    """Raised by `Node.add_property()`."""
    pass

class MergeError(TreeConstructionError):
    """Raised by `Collection.merge()` & `GameTree.merge()`."""
    pass

# Tree Navigation Exceptions

class TreeNavigationError(Error):
    """Base class for game tree navigation, and raised by `Cursor.next()`."""
    pass

class TreeEndError(TreeNavigationError):
    """Raised by `Cursor.next()`, `Cursor.previous()`."""
    pass

# Miscellaneous Exceptions

class PropertyError(Error):
    """Raised by `Node` methods."""
    pass


class Collection(list):

    """
    A `Collection` is a `list` of one or more `GameTree` objects.
    """

    path = None

    def __str__(self):
        """
        SGF text representation, accessed via `str(collection)`.
        Separates game trees with a blank line.
        """
        return '\n\n'.join(str(item) for item in self)

    def pretty(self):
        """
        Pretty-formatted SGF text representation, accessed via
        `str(collection)`. Separates game trees with a blank line.
        """
        return '\n\n'.join(item.pretty() for item in self) + '\n'

    def __bytes__(self):
        """
        SGF bytes representation, accessed via `bytes(collection)`.
        Separates game trees with a blank line.
        """
        return b'\n\n'.join(bytes(item) for item in self)

    def __repr__(self):
        """
        The canonical string representation of the `Collection`.
        """
        return '{}({}, ...)'.format(self.__class__.__name__, repr(self[0]))

    def cursor(self, gamenum=0):
        """Returns a `Cursor` object for navigation of the given `GameTree`."""
        return Cursor(self[gamenum])

    @classmethod
    def load(cls, path=None, data=None, parser_class=None):
        """
        Return a `Collection` loaded a filesystem `path` (`None` or "-" reads
        from <stdin>) or from `data`.

        The default `parser_class` is `Parser`. `RootNodeParser` may be passed
        in instead.
        """
        if data is None:
            if path == '-':
                path = None
            if path:
                with open(path, 'rb') as src:
                    data = src.read()
            else:
                # read bytestring from <stdin>:
                data = sys.stdin.buffer.read()
        if parser_class is None:
            parser_class = Parser
        parser = parser_class(data)
        collection = parser.parse()
        collection.path = path
        return collection

    def save(self, file_or_path=None, pretty=False):
        """
        Output as a bytestring to `file_or_path` (`None` or "-" writes to
        <stdout>), optionally `pretty`-formatted.
        """
        if pretty:
            output = bytes(self.pretty(), encoding=TEXT_ENCODING)
        else:
            output = bytes(self)
        if file_or_path == '-':
            file_or_path = None
        if hasattr(file_or_path, 'write'):
            file_or_path.write(output)
        elif file_or_path:
            with open(file_or_path, 'wb') as dest:
                dest.write(output)
        else:
            sys.stdout.buffer.write(output)

    def normalize(self):
        """Normalize `self`."""
        for gametree in self:
            gametree.normalize()

    def merge(self, other, comment=None, comments_everywhere=True,
              ignore_property_values=None):
        """
        Merge `other` into `self`. Identify variant branches & sources of
        comments with prefix `comment`.
        """
        if len(self) != 1:
            path = self.path if self.path else '<data:self>'
            raise MergeError(
                f'"{path}" is a collection of {len(self)} games. '
                'A multi-game collection cannot be merged. '
                'Only one game can be merged at a time.')
        if len(other) != 1:
            path = other.path if other.path else '<data:other>'
            raise MergeError(
                f'"{path}" is a collection of {len(other)} games. '
                'A multi-game collection cannot be merged. '
                'Only one game can be merged at a time.')
        self[0].merge(
            other[0], comment, comments_everywhere, ignore_property_values)
        self.normalize()


class GameTree(list):

    """
    An SGF game tree: a sequence of `Node` objects (game plays) and optional
    branches (game variations).

    Instance attributes:

    self : list of `Node`
       Game tree 'trunk' (main line of game or branch), all plays prior to any
       branches.

    self.branches : list of `GameTree`
       Variations of a game. `self.branches[0]` is the main line of the game
       (trunk of the tree).
    """

    def __init__(self, nodelist=None, branches=None, comment=None):
        """
        Arguments:

        - nodelist : `GameTree` or list of `Node` or `Node` -- Stored in `self`.
        - branches : list of `GameTree` -- Stored in `self.branches`.
        - comment : added to the first node.
        """
        if isinstance(nodelist, GameTree):
            self.extend(nodelist)
            self.branches = nodelist.branches
        elif isinstance(nodelist, list):
            self.extend(nodelist)
        elif isinstance(nodelist, Node):
            self.append(nodelist)
        elif nodelist is not None:
            raise TreeConstructionError(
                f'Unable to construct a GameTree from supplied nodelist '
                f'(type {type(nodelist)}.')
        self.branches = [] if branches is None else branches
        self.prefix_comment(comment)

    def deepcopy(self):
        copy = self.__class__(
            [node.deepcopy() for node in self],
            [branch.deepcopy() for branch in self.branches])
        return copy

    def __eq__(self, other):
        return super().__eq__(other) and self.branches == other.branches

    def __str__(self):
        """Return an SGF representation of this `GameTree`."""
        parts = ['(']
        parts.extend(str(item) for item in self)
        parts.extend(str(branch) for branch in self.branches)
        parts.append(')')
        return '\n'.join(parts)

    def pretty(self, indent=0):
        """Return a pretty-formatted SGF representation of this `GameTree`."""
        indent += 1
        parts = ['(']
        parts.extend(item.pretty(indent) for item in self)
        parts.extend(branch.pretty(indent) for branch in self.branches)
        spaces = ' ' * indent * PRETTY_INDENT_SPACES
        return (
            f'\n{spaces}'.join(parts)
            + f'\n{" "*(indent-1)*PRETTY_INDENT_SPACES})')

    def __bytes__(self):
        """Return an SGF bytes representation of this `GameTree`."""
        parts = [b'(']
        parts.extend(bytes(item) for item in self)
        parts.extend(bytes(branch) for branch in self.branches)
        parts.append(b')')
        return b'\n'.join(parts)

    def __repr__(self):
        nodelist = branches = ''
        if self:
            nodelist = 'nodelist=[{}, ...], '.format(repr(self[0]))
        if self.branches:
            branches = 'branches=[{}, ...]'.format(repr(self.branches[0]))
        return '{}({}{})'.format(self.__class__.__name__, nodelist, branches)

    def trunk(self):
        """
        Return the main line of the game (nodes and variation A) as a new
        `GameTree`.
        """
        if self.branches:
            return GameTree(self + self.branches[0].trunk())
        else:
            return self

    # def cursor(self):
    #     """Return a `Cursor` object for navigation of this `GameTree`."""
    #     return Cursor(self)

    def property_search(self, pid, getall=0):
        """
        Search this `GameTree` for nodes containing matching properties.
        Return a `GameTree` containing the matched node(s).

        Arguments:

        - pid : string -- ID of properties to search for.
        - getall : boolean -- Set to true (1) to return all `Node`'s that
          match, or to false (0) to return only the first match.
        """
        matches = []
        for n in self:
            if n.has_key(pid):
                matches.append(n)
                if not getall:
                    break
        else:    # getall or not matches:
            for v in self.branches:
                matches = matches + v.property_search(pid, getall)
                if not getall and matches:
                    break
        return GameTree(matches)

    def normalize(self):
        while self.branches:
            if len(self.branches) == 1:
                self.extend(self.branches[0])
                self.branches = self.branches[0].branches
            else:
                for index, branch in enumerate(self.branches):
                    branch.normalize()
                break

    def merge(self, other, comment=None, comments_everywhere=True,
              ignore_property_values=None):
        """
        Merge the `other` GameTree into `self`. Identify variant branches &
        plays with prefix `comment` (once, at point of deviation).
        """
        # TODO: add labels to branches
        # In case either `self` or `other` are empty:
        i = -1
        other = other.deepcopy()
        for (i, my_node, other_node) in zip(itertools.count(), self, other):
            if my_node.equivalent(other_node):
                my_node.merge(
                    other_node, comment, comments_everywhere,
                    ignore_property_values)
            else:
                # Make the rest of self & other into branches:
                self_branch = GameTree(self[i:], self.branches)
                del self[i:]
                other_branch = GameTree(other[i:], other.branches, comment)
                self.branches = [self_branch, other_branch]
                break
        else:
            if i == -1:
                # Either `self` or `other` is empty, prior to branches.
                if self:
                    if not other.branches:
                        # `other` is empty; leave `self` alone:
                        return
                elif not self.branches:
                    # `self` is empty; copy data from `other`:
                    if other:
                        other[0].prefix_comment(comment)
                    self[:] = other
                    self.branches = other.branches
                    return
                # Else branches exist in both; merge them.
            # Check for leftover nodes. If unequal lengths, make self & other
            # equal-length by converting any remainder into a branch:
            if len(self) > len(other):
                if other.branches:
                    self_branch = GameTree(self[i+1:], self.branches)
                    del self[i+1:]
                    self.branches = [self_branch]
                # Else no need to convert, as there's nothing left to merge.
            elif len(other) > len(self):
                other_branch = GameTree(other[i+1:], other.branches, comment)
                del other[i+1:]
                other.branches = [other_branch]
            if not other.branches:
                return
            if not self.branches:
                self.branches.append(GameTree([Node(C='')]))
            # Merge branches:
            for self_branch in self.branches[:]:
                for (i, other_branch) in enumerate(other.branches[:]):
                    if self_branch[0].equivalent(other_branch[0]):
                        self_branch.merge(
                            other_branch, comment, comments_everywhere,
                            ignore_property_values)
                        del other.branches[i]
                        break
            for other_branch in other.branches:
                other_branch.prefix_comment(comment)
            self.branches.extend(other.branches)

    def prefix_comment(self, comment):
        if not comment:
            return
        if self:
                self[0].prefix_comment(comment)
        else:
            for branch in self.branches:
                branch.prefix_comment(comment)


class Node(dict):

    """
    An SGF node (one move or play, or initial setup), consisting of properties
    (name:value pairs). Property values may be scalars or lists; see
    `self.list_properties`.

    Example: Let ``node`` be a `Node` parsed from ';B[aa]BL[250]C[comment]':

    * node['BL'] =>  '250'
    * node['B']  =>  'aa'
    """

    def resolve_property_id(self, name):
        if name in self.property_ids:
            return name
        elif name in self.property_names:
            return self.property_names[name]
        else:
            raise PropertyError(
                "Unknown SGF property name or ID: '{}'".format(name))

    def __getattr__(self, name):
        key = self.resolve_property_id(name)
        try:
            return self[key]
        except KeyError as error:
            if name == key:
                raise PropertyError(
                    "No '{}' property ID in Node".format(name)) from None
            else:
                raise (PropertyError(
                    "No '{}' property (SGF ID '{}') in Node".format(name, key))
                    ) from None

    def __setattr__(self, name, value):
        key = self.resolve_property_id(name)
        self[key] = value

    def __delattr__(self, name):
        key = self.resolve_property_id(name)
        try:
            del self[key]
        except KeyError as error:
            if name == key:
                raise PropertyError(
                    "No '{}' property ID in Node".format(name)) from None
            else:
                raise (PropertyError(
                    "No '{}' property (SGF ID '{}') in Node".format(name, key))
                    ) from None

    def __str__(self):
        """Return an SGF text representation of this `Node`."""
        parts = [';']
        for (name, value) in self.items():
            parts.append(name)
            parts.append('[')
            if name in self.list_properties:
                parts.append(']['.join(
                    self.escape_text(str(item)) for item in value))
            else:
                parts.append(self.escape_text(str(value)))
            parts.append(']')
        return ''.join(parts)

    def pretty(self, indent=0):
        return str(self)

    def __bytes__(self):
        """SGF bytes representation."""
        parts = [b';']
        for (name, value) in self.items():
            encoding = (
                TEXT_ENCODING if name in self.text_properties
                else NAME_ENCODING)
            parts.append(bytes(name, NAME_ENCODING))
            parts.append(b'[')
            if name in self.list_properties:
                parts.append(b']['.join(
                    bytes(self.escape_text(str(item)), encoding)
                    for item in value))
            else:
                parts.append(bytes(self.escape_text(str(value)), encoding))
            parts.append(b']')
        return b''.join(parts)

    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            ', '.join('{}={!r}'.format(name, value)
                      for name, value in self.items()))

    def deepcopy(self):
        copy = self.__class__()
        dict.update(copy, deepcopy(dict(self.items())))
        return copy

    chars_to_escape = ['\\', ']']
    """List of characters that need to be backslash-escaped."""

    chars_to_escape_pattern = None
    """Regexp pattern for isolating characters for backslash escaping.
    Initialized when `Node.escape_text` is first executed."""

    def compile_chars_to_escape_pattern(self):
        return re.compile(
            '(' + '|'.join(re.escape(char) for char in self.chars_to_escape)
            + ')')

    def escape_text(self, text):
        """Add backslash-escapes to property value characters that need them."""
        if self.chars_to_escape_pattern is None:
            object.__setattr__(
                self, 'chars_to_escape_pattern',
                self.compile_chars_to_escape_pattern())
        return ''.join(
            # escapable characters are at all odd indexes:
            ('\\' if index % 2 else '') + part
            for (index, part) in enumerate(
                self.chars_to_escape_pattern.split(text)))

    def set_encoding(self, encoding):
        object.__setattr__(self, 'encoding', encoding)

    def equivalent(self, other):
        """
        Return True iff `self` and `other` are equivalent: both the same type
        of node (setup or move), same player & coordinates if a move, etc.
        """
        my_type = self.node_type()
        other_type = other.node_type()
        if my_type is None or other_type is None:
            return True
        if my_type != other_type:
            return False
        if my_type == 'move':
            # Check that the same player played, and the coordinates match:
            self_props = set(self.keys())
            self_player = self_props & self.move_required_properties
            if (num_players := len(self_player)) != 1:
                raise PropertyError(
                    f'Expected 1 player move in `self` node, {num_players} '
                    f'found.')
            other_props = set(other.keys())
            other_player = other_props & self.move_required_properties
            if (num_players := len(other_player)) != 1:
                raise PropertyError(
                    f'Expected 1 player move in `other` node, {num_players} '
                    f'found.')
            if self_player != other_player:
                return False
            player = self_player.pop()
            if self[player] != other[player]:
                # different coordinates
                return False
        return True

    def node_type(self):
        props = set(self.keys())
        if not props or 'C' in props and not self.C:
            return None
        for (node_type, node_type_properties) in self.node_types.items():
            if props & node_type_properties:
                return node_type
        else:
            raise PropertyError(
                f'Unknown node type for node with properties {props}')

    def merge(self, other, comment=None, comments_everywhere=True,
              ignore_property_values=None):
        """
        Merge the `other` Node with `self`. Any differing comment in `other`
        will be prefixed with `comment` before merging into `self`.

        Assumes the equivalence/compatibility of `self` and `other`; this
        should be tested prior to calling.
        """
        other = other.deepcopy()
        if comment is None:
            comment = ''
        else:
            comment = f'{comment}\n'
        if ignore_property_values is None:
            ignore_property_values = dict()
        for (property_id, other_value) in other.items():
            ignore_values = (
                self.ignore_property_values.get(property_id, set())
                | ignore_property_values.get(property_id, set()))
            if (  property_id in self.scalar_properties
                  and ((any in ignore_values)
                       or (other_value in ignore_values))):
                continue
            elif property_id == 'C':
                if 'C' in self and self['C']:
                    if self['C'].strip() != other_value.strip():
                        if comments_everywhere:
                            self['C'] = (
                                f'{self["C"].strip()}\n\n'
                                f'{comment}{other_value.strip()}')
                        else:
                            self['C'] = (
                                f'{self["C"].strip()}\n\n'
                                f'{other_value.strip()}')
                else:
                    if comments_everywhere:
                        self['C'] = f'{comment}{other_value.strip()}'
                    else:
                        self['C'] = f'{other_value.strip()}'
            elif property_id in self:
                if property_id in self.scalar_properties:
                    if other_value != self[property_id]:
                        self.merge_differing_scalar_property_values(
                            property_id, other_value, ignore_values)
                    # Else equal values, so nothing to do.
                else:
                    self_values = set(self[property_id])
                    other_values = set(other_value)
                    if extras := (other_values - self_values):
                        self[property_id].extend(extras)
            else:
                if property_id in self.scalar_properties:
                    self[property_id] = other_value
                else:
                    self[property_id] = other_value[:]

    def merge_differing_scalar_property_values(
            self, property_id, other_value, ignore_values):
        self_value = self[property_id]
        if self_value in ignore_values:
            # Clear value so the value from other is used instead:
            del self[property_id]
            self_value = None
        if not other_value:
            # Empty other value, nothing to do:
            return
        if not self_value:
            # Empty self value, use value from other:
            self[property_id] = other_value
            return
        if (  property_id in self.real_properties and
              math.isclose(float(self_value), float(other_value))):
            # Ignore equivalent real-number values:
            return
        if (property_id in self.text_properties and
              self_value.lower() == other_value.lower()):
            # Ignore differences in text case:
            return
        raise MergeError(f"""\
Game nodes cannot be merged because the values for shared property \
"{property_id}" differ: "{self_value}" vs "{other_value}". \
Maybe use an option:

* "--ignore-property '{property_id}={other_value}'"
* "--ignore-property '{property_id}={self_value}'"
* "--ignore-property {property_id}" (ignores all values)""")

    def update(self, other):
        """
        `Dictionary` method not applicable to `Node`

        Raise `NodeConstructionError`.
        """
        raise NodeConstructionError(
            'The update() method is not supported by Node; add properties '
            'individually or use `merge(other)` instead.')

    def prefix_comment(self, comment):
        if not comment:
            return
        if 'C' in self and self['C'].strip():
            self['C'] = f'{comment}\n{self["C"]}'
        else:
            self['C'] = f'{comment}'

    property_ids = {
        'AB': 'add_black',
        'AE': 'add_empty',
        'AN': 'annotation',
        'AP': 'application',
        'AR': 'arrow',
        'AS': 'who_adds_stones',
        'AW': 'add_white',
        'B':  'black',
        'BL': 'black_time_left',
        'BM': 'bad_move',
        'BR': 'black_rank',
        'BT': 'black_team',
        'C':  'comment',
        'CA': 'charset',
        'CP': 'copyright',
        'CR': 'circle',
        'DD': 'dim_points',
        'DM': 'even_position',
        'DO': 'doubtful',
        'DT': 'date',
        'EV': 'event',
        'FF': 'file_format',
        'FG': 'figure',
        'GB': 'good_for_black',
        'GC': 'game_comment',
        'GM': 'game',
        'GN': 'game_name',
        'GW': 'good_for_white',
        'HA': 'handicap',
        'HO': 'hotspot',
        'IP': 'initial_position',
        'IT': 'interesting',
        'IY': 'invert_y_axis',
        'KM': 'komi',
        'KO': 'ko',
        'LB': 'label',
        'LN': 'line',
        'MA': 'mark',
        'MN': 'set_move_number',
        'N':  'node_name',
        'OB': 'overtime_stones_black',
        'ON': 'opening',
        'OT': 'overtime',
        'OW': 'overtime_stones_white',
        'PB': 'player_black',
        'PC': 'place',
        'PL': 'player_to_play',
        'PM': 'print_move_mode',
        'PW': 'player_white',
        'RE': 'result',
        'RO': 'round',
        'RU': 'rules',
        'SE': 'markup',
        'SL': 'selected',
        'SO': 'source',
        'SQ': 'square',
        'ST': 'style',
        'SU': 'setup_type',
        'SZ': 'size',
        'TB': 'territory_black',
        'TE': 'tesuji',
        'TM': 'time_limit',
        'TR': 'triangle',
        'TW': 'territory_white',
        'UC': 'unclear_position',
        'US': 'user',
        'V':  'value',
        'VW': 'view',
        'W':  'white',
        'WL': 'white_time_left',
        'WR': 'white_rank',
        'WT': 'white_team',
        }
    """Mapping of SGF property ID to property name."""

    property_names = {value: key for (key, value) in property_ids.items()}
    """Mapping of property name to SGF property ID."""

    list_properties = {
        'AB', 'AE', 'AR', 'AW', 'CR', 'DD', 'LB', 'LN', 'MA', 'SL', 'SQ',
        'TB', 'TR', 'TW', 'VW',}
    """IDs of properties with multiple values, stored in lists. Other
    properties are scalars (single values; see `Node.scalar_properties`)."""

    scalar_properties = {
        'AN', 'AP', 'AS', 'B', 'BL', 'BM', 'BR', 'BT', 'C', 'CA', 'CP', 'DM',
        'DO', 'DT', 'EV', 'FF', 'FG', 'GB', 'GC', 'GM', 'GN', 'GW', 'HA',
        'HO', 'IP', 'IT', 'IY', 'KM', 'KO', 'MN', 'N', 'OB', 'ON', 'OT', 'OW',
        'PB', 'PC', 'PL', 'PM', 'PW', 'RE', 'RO', 'RU', 'SE', 'SO', 'ST',
        'SU', 'SZ', 'TE', 'TM', 'UC', 'US', 'V', 'W', 'WL', 'WR', 'WT',}
    """IDs of properties with single values. Other properties have multiple
    values (see `Node.list_properties`)."""

    text_properties = {
        'AN', 'AP', 'AS', 'BR', 'BT', 'C', 'CA', 'CP', 'DT', 'EV', 'FG', 'GC',
        'GN', 'IP', 'IY', 'LB', 'N', 'ON', 'OT', 'PB', 'PC', 'PW', 'RE', 'RO',
        'RU', 'SO', 'SU', 'US', 'WR', 'WT',}
    """IDs of properties with values of type text & simpletext, encoded per
    the CA/charset property. Other properties are ASCII-encoded."""

    real_properties = {'KM', 'BL', 'TM', 'V', 'WL',}
    """IDs of properties with real-number values."""

    root_only_properties = {
        'AP', 'CA', 'FF', 'GM', 'ST', 'SZ', 'AN', 'BR', 'BT', 'CP', 'DT',
        'EV', 'GN', 'GC', 'ON', 'OT', 'PB', 'PW', 'PC', 'RE', 'RO', 'RU',
        'SO', 'TM', 'US', 'WR', 'WT',}
    """IDs of properties that only appear in the root node (which is also a
    setup node)."""

    setup_properties = {'AB', 'AW', 'AE', 'PL',}
    """IDs of properties that appear in setup nodes (incl. the root node)."""

    root_properties = root_only_properties | setup_properties
    """IDs of properties that appear in root nodes."""

    move_properties = {
        'B', 'W', 'KO', 'MN', 'BM', 'DO', 'IT', 'TE', 'BL', 'OB', 'OW', 'WL',}
    """IDs of properties that appear in move nodes."""

    move_required_properties = {'B', 'W',}
    """IDs of properties that must appear in move nodes."""

    ignore_property_values = {
        'RE': {'?'},
        'AP': {any},}
    """Property IDs & sets of values to ignore when merging game trees.
    `any` may be used to signify any value (value kept from primary game)."""

    node_types = {
        'root': root_properties,
        'setup': setup_properties,
        'move': move_properties,
        }

    game_types = {
        1: 'Go',
        2: 'Othello',
        3: 'chess',
        4: 'Gomoku+Renju',
        5: "Nine Men's Morris",
        6: 'Backgammon',
        7: 'Chinese chess',
        8: 'Shogi',
        9: 'Lines of Action',
        10: 'Ataxx',
        11: 'Hex',
        12: 'Jungle',
        13: 'Neutron',
        14: "Philosopher's Football",
        15: 'Quadrature',
        16: 'Trax',
        17: 'Tantrix',
        18: 'Amazons',
        19: 'Octi',
        20: 'Gess',
        21: 'Twixt',
        22: 'Zertz',
        23: 'Plateau',
        24: 'Yinsh',
        25: 'Punct',
        26: 'Gobblet',
        27: 'hive',
        28: 'Exxit',
        29: 'Hnefatal',
        30: 'Kuba',
        31: 'Tripples',
        32: 'Chase',
        33: 'Tumbling Down',
        34: 'Sahara',
        35: 'Byte',
        36: 'Focus',
        37: 'Dvonn',
        38: 'Tamsk',
        39: 'Gipf',
        40: 'Kropki',
        }
    """Mapping of game type numbers to names."""


# class Cursor:

#     """
#     `GameTree` navigation tool.

#     Instance attributes:

#     - self.game : `GameTree` -- The root `GameTree`.
#     - self.gametree : `GameTree` -- The current `GameTree`.
#     - self.node : `Node` -- The current Node.
#     - self.nodenum : integer -- The offset of `self.node` from the root of
#       `self.game`. The nodenum of the root node is 0.
#     - self.index : integer -- The offset of `self.node` within `self.gametree`.
#     - self.stack : list of `GameTree` -- A record of `GameTree` objects traversed.
#     - self.children : list of `Node` -- All child nodes of the current node.
#     - self.at_end : boolean -- Flags if we are at the end of a branch.
#     - self.at_start : boolean -- Flags if we are at the start of the game.
#     """

#     def __init__(self, gametree):
#         self.game = gametree                    # root GameTree
#         self.reset()

#     def reset(self):
#         """Set `Cursor` to point to the start of the root `GameTree`, `self.game`."""
#         self.gametree = self.game
#         self.nodenum = 0
#         self.index = 0
#         self.stack = []
#         self.node = self.gametree[self.index]
#         self._set_children()
#         self._set_flags()

#     def next(self, branch=0):
#         """
#         Move the `Cursor` to & return the next `Node`.

#         Argument:

#         * branch : integer, default 0 -- Branch number. A non-zero value is
#           only valid at a branching, where branches exist.

#         Raise `TreeEndError` if the end of a branch is exceeded.
#         Raise `TreeNavigationError` if a non-existent branch is accessed.
#         """
#         if self.index + 1 < len(self.gametree):    # more main line?
#             if branch != 0:
#                 raise TreeNavigationError("Nonexistent branch.")
#             self.index = self.index + 1
#         elif self.gametree.branches:            # branches exist?
#             if branch < len(self.gametree.branches):
#                 self.stack.append(self.gametree)
#                 self.gametree = self.gametree.branches[branch]
#                 self.index = 0
#             else:
#                 raise TreeNavigationError("Nonexistent branch.")
#         else:
#             raise TreeEndError
#         self.node = self.gametree[self.index]
#         self.nodenum = self.nodenum + 1
#         self._set_children()
#         self._set_flags()
#         return self.node

#     def previous(self):
#         """
#         Move the `Cursor` to & return the previous `Node`.

#         Raise `TreeEndError` if the start of a branch is exceeded.
#         """
#         if self.index - 1 >= 0:                    # more main line?
#             self.index = self.index - 1
#         elif self.stack:                        # were we in a branch?
#             self.gametree = self.stack.pop()
#             self.index = len(self.gametree) - 1
#         else:
#             raise TreeEndError
#         self.node = self.gametree[self.index]
#         self.nodenum = self.nodenum - 1
#         self._set_children()
#         self._set_flags()
#         return self.node

#     def _set_children(self):
#         """Set up `self.children`."""
#         if self.index + 1 < len(self.gametree):
#             self.children = [self.gametree[self.index+1]]
#         else:
#             self.children = map(lambda list: list[0], self.gametree.branches)

#     def _set_flags(self):
#         """Set up the flags `self.at_end` and `self.at_start`."""
#         self.at_end = (
#             not self.gametree.branches
#             and (self.index + 1 == len(self.gametree)))
#         self.at_start = not self.stack and (self.index == 0)


class Parser:

    """
    Parser for SGF data. Creates a tree structure based on the SGF standard
    itself. `Parser.parse()` will return a `Collection` object for the
    entire data.
    """

    encoding = 'latin-1'

    class patterns:
        """Regular expression text matching patterns."""
        game_tree_start = re.compile(rb'\s*\(')
        game_tree_end   = re.compile(rb'\s*\)')
        game_tree_next  = re.compile(rb'\s*(;|\(|\))')
        node_contents   = re.compile(rb'\s*([A-Za-z]+(?=\s*\[))')
        property_start  = re.compile(rb'\s*\[')
        property_end    = re.compile(rb'\]')
        escape          = re.compile(rb'\\')
        line_break      = re.compile(rb'\r\n?|\n\r?')    # CR, LF, CR/LF, LF/CR

    # character translation tables
    # for control characters (except LF \012 & CR \015): convert to spaces
    ctrltrans = bytes.maketrans(
        (b"\000\001\002\003\004\005\006\007\010\011\013\014\016\017\020\021\022\023\024\025\026\027"
         b"\030\031\032\033\034\035\036\037"),
        b" "*30)
    """Control character translation table for `bytes.translate()``, used to
    remove all control characters from Property values. May be overridden
    (preferably in instances)."""

    def __init__(self, data):
        self.data = data
        """The complete SGF data instance (`bytes`)."""

        self.datalen = len(data)
        """Length of `self.data`."""

        self.index = 0
        """Current parsing position in `self.data`."""

    def parse(self):
        """
        Parse the SGF data stored in `self.data`, and return a `Collection`.
        """
        collection = Collection()
        while self.index < self.datalen:
            game = self.parse_one_game()
            if game:
                collection.append(game)
            else:
                break
        return collection

    def parse_one_game(self):
        """
        Parse one game from `self.data`. Return a `GameTree` containing one
        game, or `None` if the end of `self.data` has been reached.
        """
        if self.index < self.datalen:
            match = self.patterns.game_tree_start.match(self.data, self.index)
            if match:
                self.index = match.end()
                return self.parse_game_tree()
        return None

    def parse_game_tree(self):
        """
        Parse and return one `GameTree` from `self.data`.

        Called when "(" encountered, ends when a matching ")" encountered.

        Raise `TreeParseError` if a problem is encountered.
        """
        g = GameTree()
        while self.index < self.datalen:
            match = self.patterns.game_tree_next.match(self.data, self.index)
            if match:
                self.index = match.end()
                if match.group(1) == b';':
                    # found start of node
                    if g.branches:
                        raise TreeParseError(
                            "A node was encountered after a branch.")
                    g.append(self.parse_node())
                elif match.group(1) == b'(':
                    # found start of branch
                    g.branches = self.parse_branches()
                else:
                    # found end of GameTree ")"
                    return g
            else:
                raise TreeParseError('Past end of SGF.')
        g.encoding = self.encoding
        return g

    def parse_branches(self):
        """
        Return a list of branch `GameTree` objects.

        Called when "(" encountered inside a `GameTree`, ends when a
        non-matching ")" encountered.

        Raise `EndOfDataParseError` if the end of `self.data` is reached
        before the end of the enclosing `GameTree`.
        """
        v = []
        while self.index < self.datalen:
            # check for ")" at end of GameTree, but don't consume it
            match = self.patterns.game_tree_end.match(self.data, self.index)
            if match:
                return v
            g = self.parse_game_tree()
            if g:
                v.append(g)
            # check for next branch, and consume "("
            match = self.patterns.game_tree_start.match(self.data, self.index)
            if match:
                self.index = match.end()
        raise EndOfDataParseError

    def parse_node(self):
        """
        Parse and return one `Node`, which can be empty.

        Called when ";" encountered (& is consumed).

        Per the SGF standard,

            Only one of each property is allowed per node, e.g. one cannot
            have two comments in one node

        However, at least one online server (OGS) produces SGF files with
        multiple comments per node.

        Raise `NodePropertyParseError` if no property values are extracted.
        Raise `EndOfDataParseError` if the end of `self.data` is reached
        before the end of the node (i.e., the start of the next node, the
        start of a branch, or the end of the enclosing game tree).
        """
        node = Node()
        while self.index < self.datalen:
            match = self.patterns.node_contents.match(self.data, self.index)
            if not match:
                # reached end of Node
                return node
            property_id = match.group(1).decode(NAME_ENCODING)
            self.index = match.end()
            pvlist = self.parse_property_value()
            if not pvlist:
                raise NodePropertyParseError
            encoding = (self.encoding if property_id in node.text_properties
                        else NAME_ENCODING)
            pvlist = [item.decode(encoding) for item in pvlist]
            if property_id in node.list_properties:
                value = pvlist
            elif len(pvlist) == 1:
                value = pvlist[0]
            else:
                raise NodePropertyParseError(
                    'Expected a scalar value, got a list: {}[{}]'
                    .format(property_id, ']['.join(pvlist)))
            if property_id in node:
                warnings.warn(
                    f'Duplicate property ID "{property_id}" in node '
                    f'(existing value: "{node[property_id]}"; '
                    f'new value: "{value}"). Appending new value.')
                if property_id in node.list_properties:
                    node[property_id].extend(value)
                else:
                    node[property_id] = f'{node[property_id]}\n\n{value}'
            else:
                node[property_id] = value
            # CA == charset
            if property_id == 'CA':
                self.encoding = pvlist[0]
                # detect encoding on input, force UTF-8 on output:
                node['CA'] = TEXT_ENCODING
        raise EndOfDataParseError

    def parse_property_value(self):
        """
        Parse and return a list of property values.

        Called when "[" encountered (but not consumed), ends when the next
        property, node, or branch encountered.

        Raise `PropertyValueParseError` if there is a problem.
        """
        pvlist = []
        while self.index < self.datalen:
            match = self.patterns.property_start.match(self.data, self.index)
            if match:
                self.index = match.end()
                value_parts = []
                # scan for escaped characters (using '\'), unescape them
                # (remove linebreaks)
                mend = self.patterns.property_end.search(self.data, self.index)
                mesc = self.patterns.escape.search(self.data, self.index)
                while mesc and mend and (mesc.end() < mend.end()):
                    # copy up to '\' escape, but remove '\'
                    value_parts.append(self.data[self.index:mesc.start()])
                    mbreak = self.patterns.line_break.match(
                        self.data, mesc.end())
                    if mbreak:
                        # remove linebreak:
                        self.index = mbreak.end()
                    else:
                        # copy escaped character (slice to prevent
                        # int-conversion):
                        value_parts.append(self.data[mesc.end():mesc.end()+1])
                        # move to point after escaped char:
                        self.index = mesc.end() + 1
                    mend = self.patterns.property_end.search(
                        self.data, self.index)
                    mesc = self.patterns.escape.search(self.data, self.index)
                if mend:
                    value_parts.append(self.data[self.index:mend.start()])
                    self.index = mend.end()
                    pvlist.append(
                        self._convert_control_chars(b''.join(value_parts)))
                else:
                    raise PropertyValueParseError
            else:
                # reached end of Property
                break
        if len(pvlist) >= 1:
            return pvlist
        else:
            raise PropertyValueParseError

    def _convert_control_chars(self, text):
        """
        Convert control characters in `text` to spaces, using the
        `self.ctrltrans` translation table. Override for variant behaviour.
        """
        #???return string.translate(text, self.ctrltrans)
        return text


class RootNodeParser(Parser):

    """
    For parsing only the first `GameTree` object's root `Node` of an SGF file.
    """

    def parse_node(self):
        """
        Parse and return the root `Node` only.
        """
        # Process one `Node` as usual:
        n = Parser.parse_node(self)
        # Point to the end of the data, effectively ending the `GameTree` and
        # `Collection`:
        self.index = self.datalen
        return n


class Summary:

    """
    Read, analyze, and summarize one or more SGF files.

    Command-line interface provided by `SummaryCLI` class.
    """

    summary_format = (
        '{DT}\t{RE}\t{PW}\t{WR}\t{PB}\t{BR}\t{KM}\t{HA}\t'
        '{SZ}\t{TM}\t{OT}\t{GN}\t{PC}\t{EV}\t{filename}')

    summary_fields = {
        'DT' : 'Date',
        'RE' : 'Result',
        'PW' : 'White',
        'WR' : 'W Rank',
        'PB' : 'Black',
        'BR' : 'B Rank',
        'KM' : 'Komi',
        'HA' : 'Handicap',
        'SZ' : 'Board Size',
        'TM' : 'Main Time',
        'OT' : 'Overtime',
        'GN' : 'Game Name',
        'PC' : 'Place',
        'EV' : 'Event',
        'filename' : 'Filename',
        }

    summary_header = summary_format.format(**summary_fields)

    #ctrltrans = string.maketrans(
    #    ("\000\001\002\003\004\005\006\007\010\011\012\013"
    #     "\014\015\016\017\020\021\022\023\024\025\026\027"
    #     "\030\031\032\033\034\035\036\037"), " "*32)

    def __init__(self, path, game_collections=True):
        """
        Read and store (in `self.data`) one SGF file's contents, and
        initialize an SGF parser (as `self.parser`).

        Arguments:

        - path : string -- Path to the source SGF file.
        - game_collections : boolean -- Flags whether to consider SGF
          collections. ``False`` (no) is faster, but only the first game of an
          SGF file will be processed.
        """

        self.filename = os.path.basename(path)
        """Name of file being summarized."""

        self.is_sgf = False
        """File validity flag."""

        with open(path, 'rb') as src:
            data = src.read()

        self.data = data
        """Raw SGF file contents."""

        parser_class = Parser if game_collections else RootNodeParser

        self.parser = parser_class(self.data)
        """Instance of `Parser` or `RootNodeParser`."""

        self.properties = {}
        """Property/value pairs."""

        # # override parser's ctrl chars -> spaces translation table to include
        # # LF & CR:
        # self.parser.ctrltrans = self.ctrltrans

    def __str__(self):
        """
        Return a string representation (summary) of the current game from the
        object's SGF file. Return an empty string if the file was not valid
        SGF.
        """
        if self.is_sgf:
            return self.summary_format.format(**self.properties)
        else:
            return ''

    def summarize(self):
        """
        Summarize one game from the SGF file. Return ``True`` for success,
        ``False`` for failure (no more games, or not an SGF file).
        """
        game = self.parser.parse_one_game()
        if not game:
            # no more games:
            return False
        self.reset_properties()
        self.is_sgf = False
        root = game[0]
        for property in root:
            if property in self.properties:
                self.is_sgf = True
                self.properties[property] = root[property].strip()
        #self._timeFromFilename()
        # success:
        return True

    #def _timeFromFilename(self):
    #    """
    #    Extract time when game played from filename, appends time to date field.
    #    """
    #    if (self.properties['DT'] != ''):            # only if date exists
    #        timeMatch = self.timepat.search(self.properties['filename'])
    #        if timeMatch:
    #            self.properties['DT'] = (self.properties['DT'] + " " +
    #                                timeMatch.group(1) + ":" + timeMatch.group(2))

    def reset_properties(self):
        for key in self.summary_fields:
            self.properties[key] = ''
        self.properties['filename'] = self.filename


class CLI:

    """
    Abstract base class that supports command-line interface tools.
    Subclasses must define:

    * An ``execute`` method as follows::

          def execute(self):
              # do everything here

    * `argument_specs`, the CLI arguments & options specifications, used as
      the arguments to `argparse.add_argument`::

          argument_specs = (
              (# Argument name or option flags (a tuple):
               ('name',),
               # Keyword arguments (a dictionary):
               {'default': None,
                'metavar': 'NAME',
                'help': ('Name that name.')}),
              # ...
              )

    * A class docstring that will be used as the description for the CLI
      --help.

    The command-line front end tool itself needs only two lines:

        import sgflib
        sgflib.SummaryCLI().run()
    """

    def __init__(self, settings=None, argv=None):
        """Instantiate to process the command-line arguments."""
        if settings is None:
            settings = self.process_command_line(argv)
        self.settings = settings

    def run(self):
        try:
            self.execute()
        except:
            print(
                '\n{}'.format(
                    datetime.datetime.now().isoformat(
                        sep=' ', timespec='seconds')),
                file=sys.stderr)
            raise

    help_option_spec = (
        ('--help', '-h',),
        {'action': 'help', 'help': 'Show this help message.'})

    @classmethod
    def process_command_line(cls, argv=None):
        """
        Return `settings`, a namespace of options & arguments to their values.

        `argv` is a list of arguments; pass `None` (the default) to use the
        command-line arguments (``sys.argv[1:]``).

        The subclass must declare `argument_specs`, the CLI arguments &
        options specifications. See the class docstring.
        """
        parser = argparse.ArgumentParser(
            description=textwrap.dedent(cls.__doc__),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            # Help option added manually (below) for consistency:
            add_help=False,)
        for names, params in cls.argument_specs:
            parser.add_argument(*names, **params)
        names, params = cls.help_option_spec
        parser.add_argument(*names, **params)
        if argv is None:
            argv = sys.argv[1:]
        settings = parser.parse_args(argv)
        return settings


class SummaryCLI(CLI):

    # Command-Line Interface implementation.

    """
    Read one or more SGF (Smart Game Format) files, specifically those
    recording Go/WeiQi/Baduk games, and summarize their game information to
    standard output. The output is a tab-delimited table with one line
    (record) for each game. The first line of the output contains the column
    headers (field names). The output is suitable for importing into a
    spreadsheet or database package for storage and manipulation.

    The output consists of the following fields::

        Date            Result          White           W Rank
        Black           B Rank          Komi            Handicap
        Board Size      Time            Game Name       Place
        Event           Filename
    """

    def execute(self):
        """
        Iterate through SGF files, outputting summaries.
        """
        print(Summary.summary_header)
        for path in self.settings.source_file_or_dir_paths:
            if os.path.isdir(path):
                srcpath = path
                srcfiles = os.listdir(path)
            else:
                srcpath, srcfile = os.path.split(path)
                srcfiles = [srcfile]
            for filename in srcfiles:
                file_path = os.path.join(srcpath, filename)
                if os.path.isdir(file_path):
                    # ignore subdirectories
                    continue
                sgfsum = Summary(file_path, self.settings.collections)
                # Summarize one game at a time from SGF file:
                while sgfsum.summarize():
                    summary = str(sgfsum)
                    if summary:
                        # print summary for valid files
                        print(summary)
                    else:
                        print(f'Not a valid SGF file: "{file_path}"')

    argument_specs = (
        (('source_file_or_dir_paths',),
         {'type': str,
          'nargs': '+',
          'help': ('Paths to SGF files or directories containing SGF files '
                   'to summarize.')}),
        (('--collections', '-c',),
         {'action': 'store_true',
          'help': ('Enable SGF collections (multiple games within each .sgf '
                   'file). The default is to analyze only the first game in '
                   'a collection.')}),
        )


class SecondaryGameOrComment(argparse.Action):

    """
    Store secondary games in the `namespace.secondary_games` list and optional
    comments in the `namespace.comments` dictionary, with key = the previous
    input file path, and value = the comment.
    """

    # This class is very specific to this one problem. It could be made more
    # general with a closure passing in the names of the namespace attributes,
    # and a lot of tricky logic. But that would be premature generalization.

    def __call__(self, parser, namespace, values, option_string=None):
        if namespace.secondary_games is None:
            # would this ever not be true?
            namespace.secondary_games = []
        comments = getattr(namespace, 'comments', None)
        if comments is None:
            comments = {}
            namespace.comments = comments
        start, end = namespace.comment_delimiters
        paths = set((namespace.primary_game,))
        for value in values:
            if not (value.startswith(start) and value.endswith(end)):
                if value in paths:
                    parser.error(
                        f'An input file path may be given only once '
                        f'("{value}")')
                namespace.secondary_games.append(value)
                paths.add(value)
                continue
            path = (namespace.secondary_games[-1] if namespace.secondary_games
                    else namespace.primary_game)
            if path in comments:
                parser.error(
                    f'Only one comment may be given per input file path '
                    f'("{path}": "{comments[path]}" & "{value}")')
            if value == f'{start}{end}':
                value = ''
            comments[path] = value


class MergerCLI(CLI):

    # Command-Line Interface implementation.

    """
    Merge two or more SGF game record files into one. SGF files should only
    contain one game each (collections are not supported). The assumption is
    that the trunk (main game) is common between primary (first) and secondary
    (subsequent) game records.

    The primary game's structure is left unchanged: its trunk remains the
    trunk, its variations take priority (first variation remains first, etc.).
    Secondary games are either merged into the primary game's structure (if
    they match) or are added as new variations. Comments on merged nodes are
    concatenated in order. The sources of variations and merged nodes may be
    noted with merge comments as prefixes, using either the source file
    paths/names or as specified after each input in the command line.
    Specifying a merge comment of "[[]]" means "no comment" (overrides -f);
    the merge comments will be omitted for that game.

    For example, in this command:

        %(prog)s -f main-game.sgf [[]] pro-review.sgf ai-review.sgf [[AI]]

    Any existing comments and variations in main-game.sgf will not have any
    merge comments prefixed ("[[]]" means "no comment"), elements from
    pro-review.sgf will have its file name as its merge comment prefix
    ("[[pro-review.sgf]]"), and comments and variations from ai-review.sgf
    will have "[AI]" prefixes.

    One path among primary_game and secondary_game file input paths may be '-'
    for standard input (for use in a pipeline). There is no default merge
    comment for standard input.
    """

    def execute(self):
        # Accumulate merged GameTree in `result`:
        result = Collection([GameTree()])
        ignore_property_values = collections.defaultdict(set)
        if self.settings.ignore_property:
            for property_spec in self.settings.ignore_property:
                parts = property_spec.split('=', maxsplit=1)
                property_id = parts[0]
                if len(parts) == 2:
                    value = parts[1]
                else:
                    value = any
                ignore_property_values[property_id].add(value)
        for game_path in [
                self.settings.primary_game, *self.settings.secondary_games]:
            game = Collection.load(game_path)
            game.normalize()
            comment = self.settings.comments.get(game_path)
            if comment is None and self.settings.filename_comments:
                if game_path == '-':
                    comment = ''
                else:
                    start, end = self.settings.comment_delimiters
                    comment = f'{start}{game_path}{end}'
            try:
                result.merge(game, comment, self.settings.comments_everywhere,
                             ignore_property_values=ignore_property_values)
            except MergeError as error:
                print(
                    f'\nError while merging "{game_path}":\n\n{error}',
                    file=sys.stderr)
        result.save(self.settings.output, self.settings.pretty_format)

    argument_specs = (
        (('primary_game',),
         {'default': None,
          'metavar': 'primary_game [comment]',
          'help': ('Path to the primary SGF input file to merge, optionally '
                   'followed by a merge comment. Use quotes around comments '
                   'containing shell meta characters (like * ( ) etc.)')}),
        (('secondary_games',),
         {'nargs': '+',
          'metavar': 'secondary_game [comment]',
          'action': SecondaryGameOrComment,
          #'default': [],
          'help': ('One or more paths to secondary SGF input files to merge, '
                   'each optionally followed by a merge comment.')}),
        (('--output', '-o',),
         {'default': None,
          'help': ('Specify output SGF file path (default: "-", output to '
                   '<stdout>, standard output.')}),
        (('--pretty-format', '-p',),
         {'action': 'store_true',
          'default': False,
          'help': ('Pretty-format the output SGF. '
                   '(CAUTION: output can become very large.)')}),
        (('--filename-comments', '-f',),
         {'action': 'store_true',
          'default': False,
          'help': ('Use file names as default merge comments, '
                   'e.g. "[first.sgf]" (default: disabled).')}),
        (('--no-filename-comments', '-n',),
         {'dest': 'filename_comments',
          'action': 'store_false',
          'help': ('Disable filenames as merge comment; only per-input '
                   'merge comments will be used (default).')}),
        (('--comments-everywhere', '-e',),
         {'action': 'store_true',
          'default': True,
          'help': ('Apply merge comments to all differences, '
                   'including merged comments (default).')}),
        (('--comments-on-branches-only', '-b',),
         {'dest': 'comments_everywhere',
          'action': 'store_false',
          'help': ('Apply merge comments to branches only, '
                   'not to merged comments (default: everwhere).')}),
        (('--comment-delimiters', '-c',),
         {'nargs': 2,
          'metavar': 'TEXT',
          'default': ('[[', ']]'),
          'help': ('Start and end of merge comments (default "[[" & "]]"). '
                   'Must uniquely delimit & distinguish between merge '
                   'comments.')}),
        (('--ignore-property', '-i',),
         {'action': 'append',
          'help': ('Ignore the specified property name (e.g. "WR", any value) '
                   'or name:value (e.g. "WR=3k") if value to merge differs '
                   'from the existing value. Multiple properties or '
                   'property:value pairs may be specified.')}),
        # (('--label-variations', '-l',),
        #  {'action': 'store_true',
        #   'help': ('Add unique labels to each variation, '
        #            'from the parent node.')}),
        )


class NormalizerCLI(CLI):

    # Command-Line Interface implementation.

    """
    Normalize an SGF file (collection of game trees):

    * For any game tree with exactly one branch, combine the trunk of the
      branch with the trunk of the game tree itself.

    * Optionally strip out all variations (keep main game only).

    * Optionally strip out all comments.
    """

    def execute(self):
        collection = Collection.load(self.settings.source_file)
        if self.settings.main:
            collection = Collection(game.trunk() for game in collection)
        if self.uncomment:
            collection.uncomment()
        collection.normalize()
        collection.save(self.settings.output, self.settings.pretty_format)

    argument_specs = (
        (('source_file',),
         {'type': str,
          'nargs': '?',
          'default': None,
          'help': ('Path to the SGF file to normalize. '
                   'Omit or use "-" to read from the standard input.')}),
        (('--output', '-o',),
         {'default': None,
          'help': ('Specify output SGF file path (default: "-", output to '
                   '<stdout>, standard output.')}),
        (('--main', '-m',),
         {'action': 'store_true',
          'default': False,
          'help': 'Output the main game only. Strip out all variations.'}),
        (('--uncomment', '-u',),
         {'action': 'store_true',
          'default': False,
          'help': 'Strip out all comments from the output.'}),
        (('--pretty-format', '-p',),
         {'action': 'store_true',
          'default': False,
          'help': ('Pretty-format the output SGF. '
                   '(CAUTION: output can become very large.)')}),
        )


class LabelerCLI(CLI):

    # Command-Line Interface implementation.

    """
    Label variations in an SGF file (collection of games):

    *
    """

    def execute(self):
        collection = Collection.load(self.settings.source_file)
        collection.autolabel(self.settings)
        collection.save(self.settings.output, self.settings.pretty_format)

    argument_specs = (
        (('source_file',),
         {'type': str,
          'nargs': '?',
          'default': None,
          'help': ('Path to the SGF file to label. '
                   'Omit or use "-" to read from the standard input.')}),
        (('--output', '-o',),
         {'default': None,
          'help': ('Specify output SGF file path (default: "-", output to '
                   '<stdout>, standard output.')}),
        (('--pretty-format', '-p',),
         {'action': 'store_true',
          'default': False,
          'help': ('Pretty-format the output SGF. '
                   '(CAUTION: output can become very large.)')}),
        )


if __name__ == '__main__':
    print(__doc__)
