import unittest

import numpy as np
from scipy.ndimage import binary_dilation

from rm_bg.converter import _flood_fill_edges


def _legacy_flood_fill_edges(mask: np.ndarray) -> np.ndarray:
    """Previous iterative implementation kept for regression checks."""
    edge_seed = np.zeros_like(mask, dtype=bool)
    edge_seed[0, :] = True
    edge_seed[-1, :] = True
    edge_seed[:, 0] = True
    edge_seed[:, -1] = True

    filled = edge_seed & mask
    while True:
        expanded = binary_dilation(filled) & mask
        if np.array_equal(expanded, filled):
            break
        filled = expanded
    return filled


class TestFloodFillEdges(unittest.TestCase):
    def test_preserves_island_not_connected_to_edges(self) -> None:
        mask = np.zeros((7, 7), dtype=bool)
        mask[0, 1:4] = True
        mask[1, 1] = True
        mask[3:5, 3:5] = True  # interior island

        got = _flood_fill_edges(mask)

        expected = np.zeros_like(mask, dtype=bool)
        expected[0, 1:4] = True
        expected[1, 1] = True
        self.assertTrue(np.array_equal(got, expected))

    def test_all_true_mask_stays_true(self) -> None:
        mask = np.ones((16, 16), dtype=bool)
        got = _flood_fill_edges(mask)
        self.assertTrue(np.array_equal(got, mask))

    def test_all_false_mask_stays_false(self) -> None:
        mask = np.zeros((16, 16), dtype=bool)
        got = _flood_fill_edges(mask)
        self.assertTrue(np.array_equal(got, mask))

    def test_diagonal_is_not_connected_in_4_connectivity(self) -> None:
        mask = np.zeros((3, 3), dtype=bool)
        mask[0, 0] = True  # touches edge
        mask[1, 1] = True  # only diagonal neighbor

        got = _flood_fill_edges(mask)
        expected = np.zeros_like(mask, dtype=bool)
        expected[0, 0] = True

        self.assertTrue(np.array_equal(got, expected))

    def test_regression_matches_legacy_on_random_masks(self) -> None:
        rng = np.random.default_rng(42)
        for shape in ((8, 8), (16, 24), (32, 32), (64, 40)):
            for _ in range(10):
                mask = rng.random(shape) > 0.6
                got = _flood_fill_edges(mask)
                legacy = _legacy_flood_fill_edges(mask)
                self.assertTrue(np.array_equal(got, legacy))


if __name__ == "__main__":
    unittest.main()
