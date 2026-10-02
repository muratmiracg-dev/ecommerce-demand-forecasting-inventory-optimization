import unittest

import numpy as np

from ecom_opt.inventory import _round_to_pack


class PackRoundingTests(unittest.TestCase):
    def test_orders_round_up_to_complete_packs(self):
        for quantity, pack, expected in (
            (0, 6, 0),
            (6, 6, 6),
            (6.1, 6, 12),
            (1, np.int64(4), 4),
        ):
            with self.subTest(quantity=quantity, pack=pack):
                self.assertEqual(_round_to_pack(quantity, pack), expected)

    def test_rejects_invalid_pack_sizes(self):
        for pack in (0, -2, 1.5, True, np.bool_(True), np.nan, np.inf):
            with self.subTest(pack=pack):
                with self.assertRaisesRegex(
                    ValueError, "case_pack must be a positive integer"
                ):
                    _round_to_pack(10, pack)

    def test_rejects_invalid_order_quantities(self):
        for quantity in (-1, np.nan, np.inf, -np.inf):
            with self.subTest(quantity=quantity):
                with self.assertRaisesRegex(
                    ValueError, "order quantity must be finite and non-negative"
                ):
                    _round_to_pack(quantity, 6)
