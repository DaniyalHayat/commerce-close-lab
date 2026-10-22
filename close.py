"""Order-to-cash close laboratory; synthetic data, USD integer cents throughout."""
from __future__ import annotations
import csv, json, random, sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CUTOFF='2026-10-31'
ACCOUNTS={'1000':'Cash','1100':'Processor clearing','1200':'Inventory','2000':'Accounts payable','2100':'Customer advances','2200':'Sales tax payable','3000':'Opening equity','4000':'Revenue','4100':'Sales returns','5000':'Cost of goods sold','5100':'Processing fees'}

def write_csv(path,rows):
    path.parent.mkdir(exist_ok=True,parents=True)
    with path.open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def generate():
    rng=random.Random(71);orders=[];events=[];settlements=[];banks=[]
    for i in range(600):
        oid=f'O{i+1:05}';day=date(2026,10,1)+timedelta(days=i%31)
        ship=day+timedelta(days=1+i%5);net=rng.randint(1500,22000);tax=round(net*.08);gross=net+tax;cost=round(net*.52)
        orders.append(dict(order_id=oid,order_date=str(day),ship_date=str(ship),net_cents=net,tax_cents=tax,cost_cents=cost))
        events.append(dict(event_id=f'C{i+1:05}',order_id=oid,event_date=str(day),kind='capture',amount_cents=gross))
        if i%19==0 and ship<=date(2026,10,27):
            events.append(dict(event_id=f'R{i+1:05}',order_id=oid,event_date=str(ship+timedelta(days=3)),kind='refund',amount_cents=gross))
    # Same immutable event id replayed; duplicate is rejected, never posted twice.
    events.append(dict(events[0])); events.append(dict(events[1]))
    events.append(dict(event_id='R_ORPHAN',order_id='UNKNOWN',event_date='2026-10-20',kind='refund',amount_cents=10000))
    events.append(dict(event_id='C_INVALID',order_id=orders[2]['order_id'],event_date='2026-10-10',kind='capture',amount_cents=-100))
    # Missing COGS is an unresolved accounting input, not a zero-cost assumption.
    orders[12]['cost_cents']=''
    for day in range(1,32):
        activity=[e for e in events if e['event_date']==f'2026-10-{day:02}' and e['event_id'] not in ('R_ORPHAN','C_INVALID')]
        unique={e['event_id']:e for e in activity}
        gross=sum(e['amount_cents']*(1 if e['kind']=='capture' else -1) for e in unique.values())
        fee=sum(round(e['amount_cents']*.029)+30 for e in unique.values() if e['kind']=='capture')
        if day==8:fee+=25000 # deliberate noncontractual fee
        sid=f'S{day:02}'; paid=date(2026,10,day)+timedelta(days=2)
        if day!=11:
            settlements.append(dict(settlement_id=sid,activity_date=f'2026-10-{day:02}',paid_date=str(paid),gross_cents=gross,fee_cents=fee,net_cents=gross-fee))
            banks.append(dict(bank_id='B'+sid,settlement_id=sid,bank_date=str(paid),amount_cents=gross-fee-(15000 if day==16 else 0)))
    # Duplicate bank rows have distinct identifiers, so flag duplicate settlement keys.
    duplicate=dict(banks[3]);duplicate['bank_id']='B_DUP';banks.append(duplicate)
    purchases=[dict(po_id=f'P{i:03}',receipt_date=f'2026-10-{1+i%25:02}',quantity=10+i,unit_cost_cents=1000+i*50,invoice_cents=(10+i)*(1000+i*50),invoice_date=f'2026-10-{1+i%25:02}',paid_date='2026-11-15') for i in range(30)]
    purchases[4]['invoice_cents']+=10000
    purchases[7]['receipt_date']='2026-11-02' # invoice precedes goods receipt
    purchases[10]['paid_date']='2026-10-25'
    data=dict(orders=orders,events=events,settlements=settlements,banks=banks,purchases=purchases)
    for key,rows in data.items():write_csv(ROOT/'data'/f'{key}.csv',rows)
    return data

def reconcile(data,cutoff=CUTOFF):
    date.fromisoformat(cutoff)
    orders={o['order_id']:o for o in data['orders']}; lines=[];issues=[];seen=set();valid=[]
    def issue(rule,key,amount,detail,severity='High'):
        issues.append(dict(rule=rule,source_id=key,amount_cents=amount,detail=detail,severity=severity,owner='Accounting review',status='Open'))
    def post(key,dt,entries):
        if dt>cutoff:return
        if sum(v for a,v in entries)!=0:raise ValueError('Unbalanced journal '+key)
        for account,signed in entries:
            lines.append(dict(journal_id=key,date=dt,account=account,account_name=ACCOUNTS[account],debit_cents=max(signed,0),credit_cents=max(-signed,0)))
    post('OPEN','2026-10-01',[('1000',2000000),('1200',5000000),('3000',-7000000)])
    for e in data['events']:
        if e['event_date']>cutoff:continue
        if e['event_id'] in seen:
            issue('DUPLICATE_EVENT',e['event_id'],e['amount_cents'],'Repeated immutable event id; excluded');continue
        seen.add(e['event_id'])
        if e['kind'] not in ('capture','refund'):
            issue('UNKNOWN_EVENT_KIND',e['event_id'],e['amount_cents'],'Event kind excluded');continue
        if e['amount_cents']<=0:
            issue('INVALID_AMOUNT',e['event_id'],e['amount_cents'],'Nonpositive payment; excluded');continue
        o=orders.get(e['order_id'])
        if o is None:
            issue('ORPHAN_EVENT',e['event_id'],e['amount_cents'],'No matching order; excluded');continue
        if e['amount_cents']!=o['net_cents']+o['tax_cents']:
            issue('PAYMENT_AMOUNT_MISMATCH',e['event_id'],e['amount_cents'],'Only full-order events supported; excluded');continue
        if e['kind']=='refund' and (o['ship_date']>e['event_date'] or not any(v['order_id']==o['order_id'] and v['kind']=='capture' for v in valid)):
            issue('REFUND_WITHOUT_SALE',e['event_id'],e['amount_cents'],'Refund lacks prior shipped captured sale; excluded');continue
        # One capture and one full refund per order in this scope.
        if any(v['order_id']==e['order_id'] and v['kind']==e['kind'] for v in valid):
            issue('DUPLICATE_ORDER_EVENT',e['event_id'],e['amount_cents'],'Additional same-kind order event excluded');continue
        valid.append(e)
        if e['kind']=='capture':post(e['event_id'],e['event_date'],[('1100',e['amount_cents']),('2100',-e['amount_cents'])])
        else:
            post(e['event_id'],e['event_date'],[('4100',o['net_cents']),('2200',o['tax_cents']),('1100',-e['amount_cents'])])
            if o['cost_cents']!='':post('RET_'+e['event_id'],e['event_date'],[('1200',o['cost_cents']),('5000',-o['cost_cents'])])
    captured={e['order_id'] for e in valid if e['kind']=='capture'}
    for oid in sorted(captured):
        o=orders[oid]
        if o['ship_date']>cutoff:continue
        post('SHIP_'+oid,o['ship_date'],[('2100',o['net_cents']+o['tax_cents']),('4000',-o['net_cents']),('2200',-o['tax_cents'])])
        if o['cost_cents']=='':issue('MISSING_COST',oid,o['net_cents'],'Revenue recognized; COGS unresolved and not silently zeroed')
        else:post('COGS_'+oid,o['ship_date'],[('5000',o['cost_cents']),('1200',-o['cost_cents'])])
    included_settlements=[];settlement_ids=set();bank_by=defaultdict(list)
    for b in data['banks']:
        if b['bank_date']<=cutoff:bank_by[b['settlement_id']].append(b)
    for s in data['settlements']:
        if s['paid_date']>cutoff:continue
        if s['settlement_id'] in settlement_ids:
            issue('DUPLICATE_SETTLEMENT',s['settlement_id'],s['gross_cents'],'Duplicate settlement excluded');continue
        settlement_ids.add(s['settlement_id'])
        activity=[e for e in valid if e['event_date']==s['activity_date']]
        expected_gross=sum(e['amount_cents']*(1 if e['kind']=='capture' else -1) for e in activity)
        expected_fee=sum(round(e['amount_cents']*.029)+30 for e in activity if e['kind']=='capture')
        if s['gross_cents']!=expected_gross:issue('SETTLEMENT_GROSS',s['settlement_id'],s['gross_cents']-expected_gross,'Processor gross differs from event subledger')
        if s['gross_cents']-s['fee_cents']!=s['net_cents']:
            issue('SETTLEMENT_ARITHMETIC',s['settlement_id'],s['gross_cents']-s['fee_cents']-s['net_cents'],'Settlement excluded');continue
        if s['fee_cents']!=expected_fee:issue('FEE_VARIANCE',s['settlement_id'],s['fee_cents']-expected_fee,'Fee differs from illustrative 2.9% plus $0.30 per capture')
        matches=bank_by.get(s['settlement_id'],[])
        if len(matches)>1:issue('DUPLICATE_BANK_MATCH',s['settlement_id'],sum(x['amount_cents'] for x in matches)-s['net_cents'],'Multiple bank rows; investigate before close')
        if len(matches)==0:issue('MISSING_BANK',s['settlement_id'],s['net_cents'],'No bank receipt at cutoff')
        elif len(matches)==1 and matches[0]['amount_cents']!=s['net_cents']:issue('BANK_VARIANCE',s['settlement_id'],matches[0]['amount_cents']-s['net_cents'],'Actual bank receipt differs from expected net settlement')
        post('SET_'+s['settlement_id'],s['paid_date'],[('1000',s['net_cents']),('5100',s['fee_cents']),('1100',-s['gross_cents'])])
        included_settlements.append(s)
    for b in data['banks']:
        if b['bank_date']<=cutoff and b['settlement_id'] not in settlement_ids:issue('ORPHAN_BANK',b['bank_id'],b['amount_cents'],'Bank deposit has no posted settlement')
    dates={e['event_date'] for e in valid}
    for dt in sorted(dates):
        if str(date.fromisoformat(dt)+timedelta(days=2))<=cutoff and not any(s['activity_date']==dt for s in included_settlements):
            due=sum(e['amount_cents']*(1 if e['kind']=='capture' else -1) for e in valid if e['event_date']==dt)
            issue('MISSING_SETTLEMENT',dt,due,'Expected T+2 settlement absent; remains in processor clearing')
    purchase_total=0;paid_total=0
    for p in data['purchases']:
        if p['invoice_date']>cutoff:continue
        expected=p['quantity']*p['unit_cost_cents']
        if p['receipt_date']>cutoff:
            issue('UNRECEIVED_INVOICE',p['po_id'],p['invoice_cents'],'Unreceived goods; invoice held outside posted inventory/AP');continue
        if p['invoice_cents']!=expected:
            issue('THREE_WAY_MISMATCH',p['po_id'],p['invoice_cents']-expected,'PO quantity-times-price differs from invoice; invoice held');continue
        post('AP_'+p['po_id'],max(p['invoice_date'],p['receipt_date']),[('1200',expected),('2000',-expected)]);purchase_total+=expected
        if p['paid_date']<=cutoff:
            post('PAY_'+p['po_id'],p['paid_date'],[('2000',expected),('1000',-expected)]);paid_total+=expected
    balances=defaultdict(int)
    for x in lines:balances[x['account']]+=x['debit_cents']-x['credit_cents']
    tb=[dict(account=k,name=ACCOUNTS[k],debit_cents=max(balances[k],0),credit_cents=max(-balances[k],0)) for k in ACCOUNTS]
    cap=sum(e['amount_cents'] for e in valid if e['kind']=='capture');ref=sum(e['amount_cents'] for e in valid if e['kind']=='refund')
    clearing_expected=cap-ref-sum(s['gross_cents'] for s in included_settlements)
    advances_expected=sum(orders[oid]['net_cents']+orders[oid]['tax_cents'] for oid in captured if orders[oid]['ship_date']>cutoff)
    bank_total=sum(b['amount_cents'] for b in data['banks'] if b['bank_date']<=cutoff)
    checks=dict(trial_balance=sum(balances.values()),processor_clearing=balances['1100']-clearing_expected,customer_advances=balances['2100']+advances_expected,accounts_payable=balances['2000']+purchase_total-paid_total,bank_reconciliation=(balances['1000']-2000000+paid_total)-bank_total)
    summary=dict(cutoff=cutoff,source='Synthetic seed 71; illustrative accounting policies',orders=len(orders),raw_events=len(data['events']),accepted_events=len(valid),journal_lines=len(lines),exceptions=len(issues),revenue_cents=-balances['4000'],returns_cents=balances['4100'],net_revenue_cents=-balances['4000']-balances['4100'],cogs_cents=balances['5000'],fees_cents=balances['5100'],inventory_cents=balances['1200'],processor_clearing_cents=balances['1100'],customer_advances_cents=-balances['2100'],ap_cents=-balances['2000'],cash_cents=balances['1000'],close_ready=not issues and all(v==0 for v in checks.values()))
    return dict(summary=summary,checks=checks,journals=lines,trial_balance=tb,exceptions=issues,orders=list(orders.values()),settlements=included_settlements)

def build():
    data=generate();r=reconcile(data);out=ROOT/'outputs';out.mkdir(exist_ok=True)
    for key in ('journals','trial_balance','exceptions'):write_csv(out/f'{key}.csv',r[key])
    (out/'analysis.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
    con=sqlite3.connect(out/'close.sqlite');con.executescript((ROOT/'sql/model.sql').read_text())
    con.executemany('INSERT INTO journal_lines VALUES(:journal_id,:date,:account,:account_name,:debit_cents,:credit_cents)',r['journals'])
    con.executemany('INSERT INTO exceptions VALUES(:rule,:source_id,:amount_cents,:detail,:severity,:owner,:status)',r['exceptions']);con.commit();con.close()
    memo=f'''# October accounting close review\n\n## Decision\nDo not certify this synthetic close as complete. There are {r['summary']['exceptions']} open exceptions, including missing cost, settlement, bank matching, and procurement issues. A balanced trial balance alone does not establish a complete close.\n\n## Results\n- {r['summary']['orders']} orders and {r['summary']['journal_lines']} balanced journal lines.\n- Recognized net revenue: ${r['summary']['net_revenue_cents']/100:,.2f}.\n- Customer advances pending shipment: ${r['summary']['customer_advances_cents']/100:,.2f}.\n- Processor clearing: ${r['summary']['processor_clearing_cents']/100:,.2f}; includes T+2 timing and missing settlements, not revenue.\n- Bank-to-book difference: ${r['checks']['bank_reconciliation']/100:,.2f}.\n\n## Ownership and follow-up\nPayments operations: investigate processor fees and missing settlements. Treasury: resolve duplicate bank records and deposit discrepancies. Inventory accounting: obtain missing item cost and reconcile purchase invoices to receipt evidence. Controller: review unresolved items, any correcting entries, and cutoff before approval. These are proposed responsibilities in a case study.\n\n## Policies and boundaries\nAll inputs are synthetic. This is an illustrative first-party retailer, not an Amazon ledger. Capture records a processor receivable and customer advance; revenue and sales tax are recognized at shipment under the stated simplified transfer-of-control assumption. Refunds are full-order and returned goods are assumed resalable. Real policies require actual contract and delivery terms. Processing fees are expensed separately, never netted against first-party revenue. Settlement journals use processor-reported expected net cash; independent bank differences remain open, not plugged. Matched received invoices debit inventory and credit AP; disputed invoices and unreceived goods remain explicit exceptions. Opening inventory/equity are seeded balances, not current-period sales. No FX, partial shipments/refunds, intercompany, sales-tax remittances, inventory write-down reserve, chargebacks or tax provision is modeled. Missing COGS means profit is provisional.\n'''
    (out/'close_memo.md').write_text(memo,encoding='utf-8')
    print(json.dumps(dict(summary=r['summary'],checks=r['checks']),indent=2));return r

if __name__=='__main__':build()
