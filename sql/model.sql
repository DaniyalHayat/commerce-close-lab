DROP VIEW IF EXISTS trial_balance;
DROP VIEW IF EXISTS unbalanced_journals;
DROP TABLE IF EXISTS journal_lines;
DROP TABLE IF EXISTS exceptions;
CREATE TABLE journal_lines(journal_id TEXT,date TEXT,account TEXT,account_name TEXT,debit_cents INTEGER CHECK(debit_cents>=0),credit_cents INTEGER CHECK(credit_cents>=0));
CREATE TABLE exceptions(rule TEXT,source_id TEXT,amount_cents INTEGER,detail TEXT,severity TEXT,owner TEXT,status TEXT);
CREATE VIEW trial_balance AS SELECT account,account_name,SUM(debit_cents) AS debits,SUM(credit_cents) AS credits,SUM(debit_cents-credit_cents) AS balance FROM journal_lines GROUP BY account,account_name;
CREATE VIEW unbalanced_journals AS SELECT journal_id,SUM(debit_cents-credit_cents) AS difference FROM journal_lines GROUP BY journal_id HAVING SUM(debit_cents-credit_cents)<>0;
