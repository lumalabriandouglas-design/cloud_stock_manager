# Deploying Cloud Stock Manager (Railway)

- Railway builds the `Dockerfile` (copies `legacy/` to `/app`) and deploys from `main`.
- The service start command runs migrations and collects static files before starting gunicorn:

  ```
  sh -c "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn core.wsgi --bind 0.0.0.0:${PORT:-8080} --log-file -"
  ```

- After a deploy, check the logs for `Applying inventory.00XX_... OK` (when there are new migrations), the collectstatic line, and `Starting gunicorn`.
- Rollback: redeploy the previous good deployment in Railway. New migrations that only add tables can stay in place.

## Subscription reminder emails

Shop owners are emailed when a free trial or paid subscription is about to end. Mail uses the SMTP settings already used for low-stock alerts:

`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`.

If `EMAIL_HOST` is missing, the command does not send and does not mark a reminder as sent.

- One email when the due date is 1, 2, or 3 calendar days away in Africa/Kampala.
- One email on the due date.
- Each of those is sent at most once for that due moment. Extending or renewing changes the due moment, so the next period can be reminded again.
- Only owner email addresses already on the shop are used. Shops with no owner email are skipped. Staff are not emailed. Suspended shops are not emailed.

Do not add this to the web service start command. After the migration is deployed, add a separate Railway cron service from this repo with start command:

```
python manage.py send_subscription_reminders
```

Run it once a day at 08:00 Africa/Kampala, which is 05:00 UTC (Uganda does not use daylight saving):

```
0 5 * * *
```

`python manage.py send_subscription_reminders --dry-run` prints who would be emailed without sending. The web service start command still runs `migrate`, which applies `0013_subscription_reminders` (two nullable columns that remember which reminder was already sent).
