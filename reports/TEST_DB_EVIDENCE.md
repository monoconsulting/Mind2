# TEST_DB_EVIDENCE
Date: 2025-12-21

## Accounting input gate test evidence (unified_files update)
```sql
SELECT id, gross_amount_sek, net_amount_sek, exchange_rate, updated_at
FROM unified_files
WHERE id='7d2bec12-7b9b-420e-a39b-672d605e8682';
```
Result:
```
id                                   gross_amount_sek  net_amount_sek  exchange_rate  updated_at
7d2bec12-7b9b-420e-a39b-672d605e8682  258.90            207.12          1.000000       2025-12-21 18:45:57
```

## AI4 validation nonfatal test evidence (ai_processing_history error)
```sql
SELECT file_id, status, error_message, created_at
FROM ai_processing_history
WHERE job_type='ai4' AND status='error'
ORDER BY created_at DESC
LIMIT 5;
```
Result:
```
file_id                               status  error_message                                                                                               created_at
6533b915-3449-4069-b98f-1d275d79edf9  error   AccountingProposalValidationError: Payload must include either 'items', 'proposals', 'entries', or 'accounting_entries'  2025-12-21 18:48:40
6533b915-3449-4069-b98f-1d275d79edf9  error   AccountingProposalValidationError: Payload must include either 'items', 'proposals', 'entries', or 'accounting_entries'  2025-12-21 18:48:40
1cef8a57-c78f-4d79-8b81-b4d56f060e42  error   AccountingProposalValidationError: Accounting proposals not balanced (debit=79.95, credit=399.75)                   2025-12-21 18:48:27
7d2bec12-7b9b-420e-a39b-672d605e8682  error   AccountingProposalValidationError: Payload must include either 'items', 'proposals', 'entries', or 'accounting_entries'  2025-12-21 18:45:57
```
