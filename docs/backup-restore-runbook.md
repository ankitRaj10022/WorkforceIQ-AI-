# Backup And Restore Runbook

Use the JSON backup script for redacted audits only. Use database-native backups for disaster recovery.

## MySQL Backup

```powershell
mysqldump --single-transaction --routines --triggers --events `
  -h <mysql-host> -u <backup-user> -p workforceiq `
  > backups\workforceiq-YYYYMMDD-HHMMSS.sql
```

Store the dump in encrypted object storage with retention, immutability, and access logs.

## Restore Drill

Run this against a staging database, never directly against production:

```powershell
mysql -h <staging-host> -u <restore-user> -p -e "CREATE DATABASE workforceiq_restore;"
mysql -h <staging-host> -u <restore-user> -p workforceiq_restore `
  < backups\workforceiq-YYYYMMDD-HHMMSS.sql
```

After restore:
- Run `flask db current` and confirm the expected Alembic revision.
- Run `python scripts\smoke_test.py --base-url <staging-api> --require-auth`.
- Validate one employee profile, one audit-log query, and one compliance export.
- Record restore duration and compare it to the target RTO.

## Redacted Audit Export

```powershell
python scripts\backup_database.py
```

This export redacts password hashes and MFA secrets, so it is safe for internal audit review but not sufficient for full disaster recovery.
