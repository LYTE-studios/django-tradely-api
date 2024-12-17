cd trade_journal

pipenv sync

pipenv run coverage erase

pipenv run coverage run --source='.' manage.py test

pipenv run coverage html
