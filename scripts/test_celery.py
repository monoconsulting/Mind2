from celery import Celery

# Ensure this matches the configuration in your application
CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/0"

# The app name must match the worker's app name
celery_app = Celery('mind', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

print("Sending 'hello' task to the queue...")

# Send the task
celery_app.send_task('services.tasks.hello', args=['world'])

print("Task 'hello' sent.")
