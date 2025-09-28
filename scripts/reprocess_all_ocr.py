
import os
import sys
import mysql.connector
from celery import Celery

# --- Configuration ---
# These are read from environment variables.
# Ensure you have a .env file or have set these in your shell.
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3310))
DB_NAME = os.getenv("DB_NAME", "mono_se_db_9")
DB_USER = os.getenv("DB_USER", "mind")
DB_PASS = os.getenv("DB_PASS")

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# --- Main Script ---

def enqueue_ocr_for_all_receipts():
    """
    Connects to the database, fetches all receipt IDs, and enqueues a Celery
    task to process OCR for each one.
    """
    if not DB_PASS:
        print("ERROR: The DB_PASS environment variable is not set.", file=sys.stderr)
        print("Please set the database password before running this script.", file=sys.stderr)
        sys.exit(1)

    if os.getenv("ENABLE_REAL_OCR", "false").lower() not in {"1", "true", "yes"}:
        print("WARNING: ENABLE_REAL_OCR is not set to 'true'.", file=sys.stderr)
        print("The tasks will be enqueued, but the OCR worker will skip them.", file=sys.stderr)
        print("Consider setting ENABLE_REAL_OCR=true in your .env file.", file=sys.stderr)


    receipt_ids = []
    try:
        # 1. Connect to the database
        print(f"Connecting to database '{DB_NAME}' on {DB_HOST}:{DB_PORT}...")
        db_connection = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        cursor = db_connection.cursor()
        print("Database connection successful.")

        # 2. Fetch all receipt IDs
        print("Fetching all receipt IDs from 'unified_files' table...")
        cursor.execute("SELECT id FROM unified_files WHERE ai_status != 'completed' OR ai_status IS NULL")
        receipt_ids = [item[0] for item in cursor.fetchall()]
        print(f"Found {len(receipt_ids)} receipts to process.")

    except mysql.connector.Error as err:
        print(f"Database Error: {err}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'db_connection' in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()
            print("Database connection closed.")

    if not receipt_ids:
        print("No receipts found to process.")
        return

    # 3. Connect to Celery and enqueue tasks
    print(f"Connecting to Celery broker at {CELERY_BROKER_URL}...")
    try:
        celery_app = Celery('mind', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)
        print("Celery connection successful.")

        enqueued_count = 0
        print(f"Enqueuing {len(receipt_ids)} tasks...")
        for rid in receipt_ids:
            try:
                # The task name must match how Celery knows it.
                # Usually 'path.to.module.task_function_name'
                celery_app.send_task('services.tasks.process_ocr', args=[rid])
                enqueued_count += 1
            except Exception as e:
                print(f"Failed to enqueue task for receipt ID {rid}: {e}", file=sys.stderr)

        print(f"\nSuccessfully enqueued {enqueued_count} OCR tasks.")
        print("You can now monitor the 'celery-worker' container logs to see the processing progress.")

    except Exception as e:
        print(f"Celery Error: {e}", file=sys.stderr)
        print("Please ensure Redis is running and accessible.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    enqueue_ocr_for_all_receipts()
