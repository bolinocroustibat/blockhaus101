# Blockhaus 101

## To run as async with ASGI with Uvicorn

gunicorn blockhaus101.asgi:application -k uvicorn.workers.UvicornWorker
