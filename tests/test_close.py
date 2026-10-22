import copy, sqlite3, unittest
import close as c

class CloseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=c.generate();cls.r=c.reconcile(cls.data)
    def test_order_count(self):self.assertEqual(self.r['summary']['orders'],600)
    def test_trial_balance(self):self.assertEqual(self.r['checks']['trial_balance'],0)
    def test_every_journal_balances(self):
        from collections import defaultdict
        totals=defaultdict(int)
        for x in self.r['journals']:totals[x['journal_id']]+=x['debit_cents']-x['credit_cents']
        self.assertTrue(all(x==0 for x in totals.values()))
    def test_cutoff(self):self.assertTrue(all(x['date']<=c.CUTOFF for x in self.r['journals']))
    def test_advances_reconcile(self):self.assertEqual(self.r['checks']['customer_advances'],0)
    def test_clearing_reconciles(self):self.assertEqual(self.r['checks']['processor_clearing'],0)
    def test_ap_reconciles(self):self.assertEqual(self.r['checks']['accounts_payable'],0)
    def test_incomplete_close(self):self.assertFalse(self.r['summary']['close_ready'])
    def test_bank_difference_exposed(self):self.assertNotEqual(self.r['checks']['bank_reconciliation'],0)
    def test_duplicate_events(self):self.assertEqual(sum(x['rule']=='DUPLICATE_EVENT' for x in self.r['exceptions']),2)
    def test_orphan_event(self):self.assertIn('ORPHAN_EVENT',{x['rule'] for x in self.r['exceptions']})
    def test_fee_exception(self):self.assertIn('FEE_VARIANCE',{x['rule'] for x in self.r['exceptions']})
    def test_missing_cost(self):self.assertIn('MISSING_COST',{x['rule'] for x in self.r['exceptions']})
    def test_three_way_mismatch(self):self.assertIn('THREE_WAY_MISMATCH',{x['rule'] for x in self.r['exceptions']})
    def test_unreceived_invoice(self):self.assertIn('UNRECEIVED_INVOICE',{x['rule'] for x in self.r['exceptions']})
    def test_missing_settlement(self):self.assertIn('MISSING_SETTLEMENT',{x['rule'] for x in self.r['exceptions']})
    def test_duplicate_bank(self):self.assertIn('DUPLICATE_BANK_MATCH',{x['rule'] for x in self.r['exceptions']})
    def test_money_integer(self):self.assertTrue(all(isinstance(x['debit_cents'],int) and isinstance(x['credit_cents'],int) for x in self.r['journals']))
    def test_replay_idempotent(self):
        d=copy.deepcopy(self.data);d['events']+=copy.deepcopy(self.data['events'][:50]);r=c.reconcile(d)
        self.assertEqual(r['trial_balance'],self.r['trial_balance'])
    def test_unshipped_not_revenue(self):
        unshipped={x['order_id'] for x in self.data['orders'] if x['ship_date']>c.CUTOFF}
        self.assertFalse(any(x['journal_id'].removeprefix('SHIP_') in unshipped for x in self.r['journals'] if x['journal_id'].startswith('SHIP_')))
    def test_original_inputs_immutable(self):
        d=copy.deepcopy(self.data);c.reconcile(d);self.assertEqual(d,self.data)
    def test_payment_mismatch_quarantined(self):
        d=copy.deepcopy(self.data);d['events'][5]['amount_cents']+=1;r=c.reconcile(d)
        self.assertIn('PAYMENT_AMOUNT_MISMATCH',{x['rule'] for x in r['exceptions']})
    def test_bad_date(self):
        with self.assertRaises(ValueError):c.reconcile(self.data,'bad')
    def test_sql_journal_check(self):
        db=sqlite3.connect(':memory:');db.executescript((c.ROOT/'sql/model.sql').read_text())
        db.executemany('INSERT INTO journal_lines VALUES(:journal_id,:date,:account,:account_name,:debit_cents,:credit_cents)',self.r['journals'])
        self.assertEqual(db.execute('SELECT COUNT(*) FROM unbalanced_journals').fetchone()[0],0);db.close()

if __name__=='__main__':unittest.main()
