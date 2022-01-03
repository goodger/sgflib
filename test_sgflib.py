#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io

import pytest

import sgflib


class TestNode:

    @staticmethod
    def node1():
        n = sgflib.Node()
        n['B'] = 'aa'
        n['BL'] = '123.45'
        n['C'] = 'text /\\[]()'
        n['LB'] = ['bb:A', 'cc:B']
        return n

    node1_str = r';B[aa]BL[123.45]C[text /\\[\]()]LB[bb:A][cc:B]'
    node1_repr = r"Node(B='aa', BL='123.45', C='text /\\[]()', LB=['bb:A', 'cc:B'])"

    @staticmethod
    def node2():
        n = sgflib.Node()
        n.B = 'aa'
        n.BL = '123.45'
        n.C = 'text /\\[]()'
        n.LB = ['bb:A', 'cc:B']
        return n

    @staticmethod
    def node3():
        n = sgflib.Node()
        n.black = 'aa'
        n.black_time_left = '123.45'
        n.comment = 'text /\\[]()'
        n.label = ['bb:A', 'cc:B']
        return n

    def test_node(self):
        n1 = self.node1()
        assert str(n1) == self.node1_str
        assert repr(n1) == self.node1_repr
        n2 = self.node2()
        assert str(n2) == self.node1_str
        assert repr(n2) == self.node1_repr
        n3 = self.node3()
        assert str(n3) == self.node1_str
        assert repr(n3) == self.node1_repr

    def test_escape_text(self):
        n1 = self.node1()
        assert n1.escape_text(r'abc\def]ghi') == r'abc\\def\]ghi'


class TestGameTree:

    def test_game_tree(self):
        g = sgflib.GameTree()
        assert str(g) == '(\n)'
        n = TestNode.node1()
        g = sgflib.GameTree(n)
        assert str(g) == '(\n{}\n)'.format(TestNode.node1_str)


class TestParser:

    sgfdata1 = rb"""       (;GM [1]FF[4]CA[UTF-8]US[someone]CP[\
  Permission to reproduce this game is given.]GN[a-b]EV[None]RE[B+Resign]
PW[a]WR[2k*]PB[b]BR[4k*]PC[somewhere]DT[2000-01-16]SZ[19]TM[300]KM[4.5]
HA[3]AB[pd][dp][dd];W[pp];B[nq];W[oq]C[ x started observation.
](;B[qc]C[ [b\]: \\ hi x! ;-) \\];W[kc])(;B[hc];W[oe]))   """

    sgfdata1_str = r"""(
;GM[1]FF[4]CA[UTF-8]US[someone]CP[  Permission to reproduce this game is given.]GN[a-b]EV[None]RE[B+Resign]PW[a]WR[2k*]PB[b]BR[4k*]PC[somewhere]DT[2000-01-16]SZ[19]TM[300]KM[4.5]HA[3]AB[pd][dp][dd]
;W[pp]
;B[nq]
;W[oq]C[ x started observation.
]
(
;B[qc]C[ [b\]: \\ hi x! ;-) \\]
;W[kc]
)
(
;B[hc]
;W[oe]
)
)"""

    sgfdata1_repr = r"Collection(GameTree(nodelist=[Node(GM='1', FF='4', CA='UTF-8', US='someone', CP='  Permission to reproduce this game is given.', GN='a-b', EV='None', RE='B+Resign', PW='a', WR='2k*', PB='b', BR='4k*', PC='somewhere', DT='2000-01-16', SZ='19', TM='300', KM='4.5', HA='3', AB=['pd', 'dp', 'dd']), ...], branches=[GameTree(nodelist=[Node(B='qc', C=' [b]: \\ hi x! ;-) \\'), ...], ), ...]), ...)"

    sgfdata1_mainline_str = r"""(
;GM[1]FF[4]CA[UTF-8]US[someone]CP[  Permission to reproduce this game is given.]GN[a-b]EV[None]RE[B+Resign]PW[a]WR[2k*]PB[b]BR[4k*]PC[somewhere]DT[2000-01-16]SZ[19]TM[300]KM[4.5]HA[3]AB[pd][dp][dd]
;W[pp]
;B[nq]
;W[oq]C[ x started observation.
]
;B[qc]C[ [b\]: \\ hi x! ;-) \\]
;W[kc]
)"""

    def test_sgfdata1(self):
        parser = sgflib.Parser(self.sgfdata1)
        assert parser.encoding == 'latin-1'
        collection = parser.parse()
        assert len(collection) == 1
        assert parser.encoding == 'UTF-8'
        assert repr(collection) == self.sgfdata1_repr
        assert str(collection) == self.sgfdata1_str
        assert bytes(collection) == self.sgfdata1_str.encode('UTF-8')
        mainline = collection[0].trunk()
        assert str(mainline) == self.sgfdata1_mainline_str
        parser2 = sgflib.Parser(bytes(collection))
        collection2 = parser2.parse()
        assert str(collection2) == str(collection)

    sgfdata2_unicode = r"""(;GM[1]FF[4]CA[UTF-8]US[高橋]CP[©２０２１ Üñìṿé₹šâł ℂøđəδ ÇħÅŗ∀ćτεя §∊⊤…]GN[面白いゲーム]RE[B+Resign]PW[しろちゃん]WR[2k*]PB[くろくん]BR[4k*]PC[インターネット]DT[2021-01-01]SZ[19]TM[300]KM[4.5]HA[3]AB[pd][dp][dd];W[pp];B[nq];W[oq]C[誰が勝っている？](;B[qc]C[[しろちゃん\]: いい手だね];W[kc])(;B[hc];W[oe]))"""

    sgfdata2 = sgfdata2_unicode.encode('utf-8')

    sgfdata2_str = r"""(
;GM[1]FF[4]CA[UTF-8]US[高橋]CP[©２０２１ Üñìṿé₹šâł ℂøđəδ ÇħÅŗ∀ćτεя §∊⊤…]GN[面白いゲーム]RE[B+Resign]PW[しろちゃん]WR[2k*]PB[くろくん]BR[4k*]PC[インターネット]DT[2021-01-01]SZ[19]TM[300]KM[4.5]HA[3]AB[pd][dp][dd]
;W[pp]
;B[nq]
;W[oq]C[誰が勝っている？]
(
;B[qc]C[[しろちゃん\]: いい手だね]
;W[kc]
)
(
;B[hc]
;W[oe]
)
)"""

    sgfdata2_repr = "Collection(GameTree(nodelist=[Node(GM='1', FF='4', CA='UTF-8', US='高橋', CP='©２０２１ Üñìṿé₹šâł ℂøđəδ ÇħÅŗ∀ćτεя §∊⊤…', GN='面白いゲーム', RE='B+Resign', PW='しろちゃん', WR='2k*', PB='くろくん', BR='4k*', PC='インターネット', DT='2021-01-01', SZ='19', TM='300', KM='4.5', HA='3', AB=['pd', 'dp', 'dd']), ...], branches=[GameTree(nodelist=[Node(B='qc', C='[しろちゃん]: いい手だね'), ...], ), ...]), ...)"

    sgfdata2_mainline_str = r"""(
;GM[1]FF[4]CA[UTF-8]US[高橋]CP[©２０２１ Üñìṿé₹šâł ℂøđəδ ÇħÅŗ∀ćτεя §∊⊤…]GN[面白いゲーム]RE[B+Resign]PW[しろちゃん]WR[2k*]PB[くろくん]BR[4k*]PC[インターネット]DT[2021-01-01]SZ[19]TM[300]KM[4.5]HA[3]AB[pd][dp][dd]
;W[pp]
;B[nq]
;W[oq]C[誰が勝っている？]
;B[qc]C[[しろちゃん\]: いい手だね]
;W[kc]
)"""

    def test_sgfdata2(self):
        parser = sgflib.Parser(self.sgfdata2)
        assert parser.encoding == 'latin-1'
        collection = parser.parse()
        assert len(collection) == 1
        assert parser.encoding == 'UTF-8'
        assert repr(collection) == self.sgfdata2_repr
        assert str(collection) == self.sgfdata2_str
        assert bytes(collection) == self.sgfdata2_str.encode('UTF-8')
        mainline = collection[0].trunk()
        assert str(mainline) == self.sgfdata2_mainline_str
        parser2 = sgflib.Parser(bytes(collection))
        collection2 = parser2.parse()
        assert str(collection2) == str(collection)


class TestMerge:

    sgfdata_singles = [
        rb"""
(
  ;GM[1]FF[4]CA[UTF-8]
  ;W[pp]
  ;B[nq]
  ;W[oq]C[comment 1]
  (
    ;B[qc]C[comment 2]
    ;W[kc]
  )
  (
    ;B[hc]
    ;W[oe]
  )
)""",
#         rb"""       (;GM [1]FF[4]CA[UTF-8]US[someone]CP[\
#   Permission to reproduce this game is given.]GN[a-b]EV[None]RE[B+Resign]
# PW[a]WR[2k*]PB[b]BR[4k*]PC[somewhere]DT[2000-01-16]SZ[19]TM[300]KM[4.5]
# HA[3]AB[pd][dp][dd];W[pp];B[nq];W[oq]C[ x started observation.
# ](;B[qc]C[ [b\]: \\ hi x! ;-) \\];W[kc])(;B[hc];W[oe]))   """
    ]

    expected_single_with_one_comment = [
        rb"""
(
  ;GM[1]FF[4]CA[UTF-8]
  ;W[pp]
  ;B[nq]
  ;W[oq]C[comment 1]
  (
    ;B[qc]C[comment 2]
    ;W[kc]
  )
  (
    ;B[hc]
    ;W[oe]
  )
)""",
    ]

    expected_single_with_two_comments = [
        rb"""
(
  ;GM[1]FF[4]CA[UTF-8]C[[[first\]\]]
  ;W[pp]
  ;B[nq]
  ;W[oq]C[comment 1]
  (
    ;B[qc]C[comment 2]
    ;W[kc]
  )
  (
    ;B[hc]
    ;W[oe]
  )
)""",
    ]

    def test_merge_once(self):
        """Merge single game once."""
        for sgfdata in self.sgfdata_singles:
            result = sgflib.Collection([sgflib.GameTree()])
            parser = sgflib.Parser(sgfdata)
            game = parser.parse()
            game.normalize()
            game_before = game.pretty()
            result.merge(game)
            game_after = game.pretty()
            assert game_before == game_after
            assert result.pretty() == game.pretty()
            assert result == game

    def test_merge_twice(self):
        """Merge single game twice."""
        for sgfdata in self.sgfdata_singles:
            result = sgflib.Collection([sgflib.GameTree()])
            parser = sgflib.Parser(sgfdata)
            game = parser.parse()
            game.normalize()
            game_before = game.pretty()
            result.merge(game)
            result.merge(game)
            game_after = game.pretty()
            assert game_before == game_after
            assert result.pretty() == game.pretty()
            assert result == game

    def test_merge_self(self):
        """Merge single game with itself."""
        for sgfdata in self.sgfdata_singles:
            result = sgflib.Collection([sgflib.GameTree()])
            parser = sgflib.Parser(sgfdata)
            game = parser.parse()
            game.normalize()
            result.merge(game)
            game.merge(game)
            assert result.pretty() == game.pretty()
            assert result == game

    def test_merge_with_one_comment(self):
        """Merge single game twice, with a comment on the second merge."""
        for (i, sgfdata) in enumerate(self.sgfdata_singles):
            result = sgflib.Collection([sgflib.GameTree()])
            parser = sgflib.Parser(sgfdata)
            game = parser.parse()
            game.normalize()
            game_before = game.pretty()
            result.merge(game)
            result.merge(game, '[[second]]')
            game_after = game.pretty()
            assert game_before == game_after
            expected = sgflib.Parser(
                self.expected_single_with_one_comment[i]).parse()
            expected.normalize()
            assert result.pretty() == expected.pretty()
            assert result == expected

    def test_merge_with_two_comments(self):
        for (i, sgfdata) in enumerate(self.sgfdata_singles):
            result = sgflib.Collection([sgflib.GameTree()])
            parser = sgflib.Parser(sgfdata)
            game = parser.parse()
            game.normalize()
            game_before = game.pretty()
            result.merge(game, '[[first]]')
            result.merge(game, '[[second]]')
            game_after = game.pretty()
            assert game_before == game_after
            expected = sgflib.Parser(
                self.expected_single_with_two_comments[i]).parse()
            expected.normalize()
            assert result.pretty() == expected.pretty()
            assert result == expected

    merger_CLI_configs = (
        # ((argv,), path_to_expected_output, load_expected_as_game),
        (('--no-filename-comments',
          'test_data/game1.sgf',
          'test_data/game1copy.sgf'),
         'test_data/game1.sgf',
         True),
        (('--filename-comments',
          'test_data/game1.sgf',
          'test_data/game1copy.sgf'),
         'test_data/expected_self_merge_filename_comments.sgf',
         True),
        (('test_data/game1.sgf',
          'test_data/game1copy.sgf',
          '[[secondary 1]]'),
         'test_data/expected_self_merge_secondary_comment.sgf',
         True),
        (('test_data/game2.sgf',
          'test_data/game2a.sgf',
          '[[secondary 2]]'),
         'test_data/expected_merge_game_2_2a_with_comments.sgf',
         True),
        (('--pretty-format',
          'test_data/game2.sgf',
          '[[primary]]',
          'test_data/game3.sgf',
          '[[secondary 3]]'),
         'test_data/expected_merge_game_2_3_with_comments.sgf',
         False),
        (('test_data/game4a.sgf',
          'test_data/game4b.sgf'),
         'test_data/expected_merge_game_4a_4b.sgf',
         True),
        # test for a completed game & its scratchpad with a prefix comment:
        (('--comments-on-branches-only',
          'test_data/game5_server.sgf',
          'test_data/game5_scratchpad.sgf',
          '[[scratchpad]]'),
         'test_data/expected_game_5_merged.sgf',
         True),
    )

    @pytest.mark.parametrize(
        "argv, expected_path, load_expected_as_game", merger_CLI_configs)
    def test_MergerCLI(self, argv, expected_path, load_expected_as_game):
        cli = sgflib.MergerCLI(argv=argv)
        with io.BytesIO() as cli.settings.output:
            cli.run()
            merged = cli.settings.output.getvalue()
        with open(expected_path, 'rb') as expected_file:
            expected = expected_file.read()
        if load_expected_as_game:
            game = sgflib.Collection.load(data=expected)
            game.normalize()
            expected = bytes(game)
        assert merged == expected

    ## old version:
    # def test_MergerCLI(self):
    #     for (i, config) in enumerate(self.merger_CLI_configs):
    #         argv, expected_path, normalize = config
    #         print(i, (argv, expected_path, normalize))
    #         cli = sgflib.MergerCLI(argv=argv)
    #         with io.BytesIO() as cli.settings.output:
    #             cli.run()
    #             merged = cli.settings.output.getvalue()
    #         if normalize:
    #             expected = sgflib.Collection.load(expected_path)
    #             expected.normalize()
    #         else:
    #             expected = open(expected_path, encoding='utf-8').read()
    #         assert merged.decode('utf-8') == str(expected)
    #         print(i, 'OK')
            

def self_test_1(onConsole=0):
    """Canned data test case"""
    sgfdata = r"""       (;GM [1]US[someone]CP[\
  Permission to reproduce this game is given.]GN[a-b]EV[None]RE[B+Resign]
PW[a]WR[2k*]PB[b]BR[4k*]PC[somewhere]DT[2000-01-16]SZ[19]TM[300]KM[4.5]
HA[3]AB[pd][dp][dd];W[pp];B[nq];W[oq]C[ x started observation.
](;B[qc]C[ [b\]: \\ hi x! ;-) \\];W[kc])(;B[hc];W[oe]))   """
    print("\n\n********** Self-Test 1 **********\n")
    print("Input data:\n")
    print(sgfdata)
    print("\n\nParsed data: ")
    collection = sgflib.Parser(sgfdata).parse()
    print("done\n")
    cstr = str(collection)
    print(cstr, "\n")
    print("Trunk:\n")
    m = collection[0].trunk()
    print(m, "\n")
    ##print("as GameTree:\n")
    ##print(GameTree(m), "\n")
    print("Tree traversal (forward):\n")
    cursor = collection.cursor()
    while 1:
        print("nodenum: %s; index: %s; children: %s; node: %s" % (cursor.nodenum, cursor.index, len(cursor.children), cursor.node))
        if cursor.at_end: break
        cursor.next()
    print("\nTree traversal (backward):\n")
    while 1:
        print("nodenum: %s; index: %s; children: %s; node: %s" % (cursor.nodenum, cursor.index, len(cursor.children), cursor.node))
        if cursor.at_start: break
        cursor.previous()
    print("\nSearch for property 'B':")
    print(collection[0].property_search("B", 1))
    print("\nSearch for property 'C':")
    print(collection[0].property_search("C", 1))
