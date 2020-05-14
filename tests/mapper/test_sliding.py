# -*- coding: utf-8 -*-
#
# Copyright 2020 Data61, CSIRO
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
import pytest

from stellargraph import StellarGraph
from stellargraph.mapper import (
    SlidingFeaturesNodeGenerator,
    SlidingFeaturesNodeSequence,
)
from ..test_utils.graphs import example_graph, example_hin_1


def test_sliding_generator_invalid():
    with pytest.raises(ValueError, match="window_size: expected .* found -123"):
        SlidingFeaturesNodeGenerator(example_graph(), window_size=-123)

    with pytest.raises(TypeError, match="window_size: expected int, found NoneType"):
        SlidingFeaturesNodeGenerator(example_graph(), window_size=None)

    with pytest.raises(ValueError, match="G: expected a graph .* node types: 'A', 'B'"):
        SlidingFeaturesNodeGenerator(example_hin_1(), window_size=1)


def _graph(shape):
    nodes = np.arange(np.product(shape)).reshape(shape)
    return StellarGraph(nodes=nodes)


def test_sliding_generator_flow_invalid():
    g = _graph(2, 10, 4)
    gen = SlidingFeaturesNodeGenerator(g, window_size=2)

    gen.flow(None)
    gen.flow(range(100))
    gen.flow(range(4, 10, 2))  # should be an error?


def _feat_getters(graph):
    def single(idx):
        return graph.node_features()[:, start, ...]

    def several(start, end):
        return graph.node_features()[:, start:end, ...]

    return single, several


def test_feat_getter():
    # 3 nodes with features like [[0, 1], [2, 3], [4, 5], [6, 7]]
    g = _graph((3, 4, 2))
    single, several = _feat_getters(g)

    np.testing.assert_array_equal(single(1), [[2, 3], [10, 11], [18, 19]])
    np.testing.assert_array_equal(several(1, 2), [[[2, 3]], [[10, 11]], [[18, 19]]])
    np.testing.assert_array_equal(
        several(1, 3), [[[2, 3], [4, 5]], [[10, 11], [12, 13]], [[18, 19], [20, 21]]]
    )


def _check_sequence(seq, expected):
    assert len(seq) == len(expected)
    for (feats, targets), (exp_feats, exp_targets) in zip(seq, expected):
        assert len(feats) == 1
        np.testing.assert_array_equal(feats[0], exp_feats)
        if exp_targets is None:
            assert targets is None
        else:
            np.testing.assert_array_equal(targets, exp_targets)


@pytest.mark.parametrize("variates", ["uni", "multi"])
def test_sliding_sequence(variates):
    if variates == "uni":
        # 2 nodes with features: [0, 1, 2, 3], [4, 5, 6, 7]
        shape = (2, 4)
    else:
        # 2 nodes with features: [[[0, 1]], [[2, 3]], [[4, 5]], [[6, 7]]], [[[8, 9]], ...]
        shape = (2, 4, 1, 2)

    g = _graph(shape)

    single, several = _feat_getters(g)

    # extreme case: window_size = 1
    gen1 = SlidingFeaturesNodeGenerator(g, window_size=1)
    seq = gen1.flow(range(0, 4), batch_size=3)
    _check_sequence(
        seq,
        [
            ([several(0, 1), several(1, 2), several(2, 3)], None),
            ([several(3, 4)], None),
        ],
    )

    seq = gen1.flow(range(0, 4), batch_size=2, target_distance=1)
    _check_sequence(
        seq,
        [
            ([several(0, 1), several(1, 2)], [single(1), single(2)]),
            ([several(2, 3)], [single(3)]),
        ],
    )

    gen2 = SlidingFeaturesNodeGenerator(g, window_size=2)
    seq = gen2.flow(range(0, 4), batch_size=2)
    _check_sequence(
        seq, [([several(0, 2), several(1, 3)], None), ([several(2, 4)], None)]
    )

    seq = gen2.flow(range(0, 4), batch_size=2, target_distance=1)
    _check_sequence(seq, [([several(0, 2), several(1, 3)], [single(2), single(3)])])
