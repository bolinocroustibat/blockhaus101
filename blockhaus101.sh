#!/bin/bash
git -C /home/www/blockhaus101/ pull origin master
source /home/virtualenvs/blockhaus101/bin/activate
pip install -r /home/www/blockhaus101/requirements.txt
python /home/www/blockhaus101/manage.py migrate
python /home/www/blockhaus101/manage.py collectstatic --noinput
chown -R www-data:www-data /home/www/blockhaus101
systemctl reload nginx 
