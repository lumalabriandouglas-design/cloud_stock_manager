# Cloud Stock Manager

New shop app (Inventory + Sell). The previous Django project is kept in `legacy/`.

## Railway

Point this service at the **same Postgres** the live shop already uses. Do not create an empty database.

Start command after build:

```
npm run build && npm run preview -- --host 0.0.0.0 --port $PORT
```

Or use the existing `startup.sh` if you run the preview server.

Existing usernames, emails, passwords, shops, and stock are imported on first boot. Old Django tables are not deleted.
