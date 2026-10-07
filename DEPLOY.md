# Deploying Cloud Stock Manager (Railway)

- Railway builds the `Dockerfile` (copies `legacy/` to `/app`) and deploys from `main`.
- The service start command runs migrations and collects static files before starting gunicorn:

  ```
  sh -c "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn core.wsgi --bind 0.0.0.0:${PORT:-8080} --log-file -"
  ```

- After a deploy, check the logs for `Applying inventory.00XX_... OK` (when there are new migrations), the collectstatic line, and `Starting gunicorn`.
- Rollback: redeploy the previous good deployment in Railway. New migrations that only add tables can stay in place.
