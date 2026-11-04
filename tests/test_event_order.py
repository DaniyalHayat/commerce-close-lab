import copy
import random
import unittest
import close


class EventOrderTests(unittest.TestCase):
    def test_reordering_preserves_balances_and_accepted_events(self):
        data=close.generate()
        original=close.reconcile(data)
        shuffled=copy.deepcopy(data)
        random.Random(31).shuffle(shuffled['events'])
        result=close.reconcile(shuffled)
        self.assertEqual(original['trial_balance'], result['trial_balance'])
        self.assertEqual(original['summary'], result['summary'])

    def test_duplicate_order_cannot_silently_replace_source(self):
        data=close.generate()
        data['orders'].append(copy.deepcopy(data['orders'][0]))
        with self.assertRaises(ValueError):close.reconcile(data)
