#!/bin/bash
git -C /home/www/production/blockhaus101-django/ pull origin master
source /home/virtualenvs/blockhaus101-venv/bin/activate
pip install -r /home/www/production/blockhaus101-django/requirements.txt
python /home/www/production/blockhaus101-django/manage.py migrate
python /home/www/production/blockhaus101-django/manage.py collectstatic --noinput
/etc/init.d/apache2 reload
