#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ -f /home/ubuntu/Consulting_Platform/venv/bin/activate ]; then
  source /home/ubuntu/Consulting_Platform/venv/bin/activate
elif [ -f venv/bin/activate ]; then
  source venv/bin/activate
fi

python manage.py collectstatic --noinput

mkdir -p media/diagnostics/templates
mkdir -p media/diagnostics/student
mkdir -p media/diagnostics/admin
mkdir -p media/academic/transcripts
mkdir -p media/academic/cv
mkdir -p media/academic/personal_statements

# Allow nginx (www-data) to traverse /home/ubuntu and read uploaded files
chmod o+x /home/ubuntu
chmod o+x /home/ubuntu/Consulting_Platform
chmod o+x /home/ubuntu/Consulting_Platform/platform_edu
chmod -R a+rX staticfiles
chmod -R u+rwX,go+rX media

echo "Static files collected and media directories ready."
echo "Reload nginx if needed: sudo systemctl reload nginx"
