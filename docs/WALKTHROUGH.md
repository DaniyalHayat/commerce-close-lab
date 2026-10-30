# Five minute accounting demonstration

## Business question
Can the accounting team support the October close from order and payment evidence, and which issues prevent completion?

1. Start on Summary: close is incomplete even though the trial balance balances.
2. Search `C00001` in the journal explorer. A capture debits processor clearing and credits customer advances; it does not create revenue.
3. Search `SHIP_O00001`. Shipment releases the advance into revenue and sales tax payable. Merchandise cost is booked separately to COGS and inventory.
4. Filter the exception register to MISSING_SETTLEMENT, then DUPLICATE_BANK_MATCH. Explain timing differences versus errors; a missing expected T+2 settlement is not treated as cash received.
5. Open the Excel VLOOKUP mapping, SUMIFS trial balance and native PivotTable. End with the close memo's review responsibilities and unresolved missing cost.

## Questions 

- Can a journal balance and still be wrong? Yes. Incorrect account, amount, cutoff, or source evidence can still produce equal debits and credits.
- Why is captured cash not necessarily revenue? The simplified retailer has not yet satisfied its shipment-based obligation. The project states that policy assumption explicitly.
- Why not report payment processor net deposits as sales? Fees, returns, timing, and sales tax must be separated from recognized first-party revenue.
- Why is COGS provisional? One shipped order has no validated cost. The model flags the missing evidence instead of inserting a false zero.
- Why doesn't the exception amount sum equal a loss? Some rows show affected gross amounts and some show reconciliation differences; they are not an additive loss measure.
- How is replay handled? Immutable event IDs prevent duplicate posting. Replaying a batch leaves the trial balance unchanged while adding duplicate warnings.
- What would production require? Actual contractual revenue policy, partial events, FX, inventory reserves, subledger and bank interfaces, restricted approvals, correction/reversal history, and accounting-owner review.
