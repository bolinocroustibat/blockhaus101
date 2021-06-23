#!/bin/bash
git -C /home/www/blockhaus101-django/ pull origin master
source /home/virtualenvs/blockhaus101/bin/activate
pip install -r /home/www/blockhaus101-django/requirements.txt
python /home/www/blockhaus101-django/manage.py migrate
python /home/www/blockhaus101-django/manage.py collectstatic --noinput
chown -R www-data:www-data /home/www/blockhaus101-django
systemctl reload nginx 
