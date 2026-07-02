#!/bin/sh
set -e

echo "[tfpc-server] collectstatic..."
python manage.py collectstatic --noinput

echo "[tfpc-server] migrate..."
python manage.py migrate --noinput

# 可选：首次启动创建超级管理员（通过环境变量）
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "[tfpc-server] ensuring superuser: $DJANGO_SUPERUSER_USERNAME"
  python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
U = get_user_model()
uname = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL') or (uname + '@example.com')
pwd  = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
if not U.objects.filter(username=uname).exists():
    U.objects.create_superuser(username=uname, email=email, password=pwd)
    print('superuser created:', uname)
else:
    print('superuser exists:', uname)
" 2>/dev/null || true
fi

echo "[tfpc-server] starting: $@"
exec "$@"
