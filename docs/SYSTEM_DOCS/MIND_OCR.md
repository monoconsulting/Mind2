# MIND OCR System Documentation

This document provides a technical overview of the Optical Character Recognition (OCR) service within the MIND project. It details the software used, its installation, configuration, data flows, and storage mechanisms.

## 1. Installation

The OCR service is a core function and requires the `paddleocr` library. This dependency is not included in the base `requirements.txt` file and must be added for the OCR service to function.

To enable OCR, add the following packages to `requirements.txt`:

```
paddlepaddle
paddleocr
```

*Note: For better performance in a compatible environment, consider using the GPU version: `paddlepaddle-gpu`.*

## 2. Core OCR Software

The system uses **PaddleOCR**, a versatile OCR toolkit. It is integrated into the Python backend via the `paddleocr` library.

- **Library:** `paddleocr`
- **Code Reference:** `backend/src/services/ocr.py`

## 3. Configuration

The OCR service is configured entirely through environment variables, which are typically set in a `.env` file.

- **`ENABLE_REAL_OCR`**: This is the master switch for the OCR service. The `process_ocr` task only performs OCR if this variable is set to a true-like value (e.g., `"true"`, `"1"`, `"yes"`). If set to a false value or is not present, the task logs the job status as "skipped_disabled" and stops processing.
- **`OCR_LANG`**: Defines the languages for the OCR engine. The default value is `sv+en`, which prioritizes **Swedish** and uses **English** as a secondary language.
- **`OCR_USE_ANGLE_CLS`**: Controls whether the engine attempts to detect and correct text orientation. Defaults to `true`.
- **`OCR_SHOW_LOG`**: ⚠️ **DEPRECATED** - This parameter has been removed in newer versions of PaddleOCR and should not be used. The parameter is ignored in the current implementation.
- **`STORAGE_DIR`**: Defines the absolute path to the file storage volume where receipt images are read from. In the Docker environment, this is set to `/data/storage`.

## 4. Modifying OCR Settings

All OCR settings are controlled via the environment variables listed above. To change any setting (e.g., to switch the language to only English), modify the corresponding variable in your `.env` file:

```
# Example: Change language to only English
OCR_LANG=en
```

## 5. Key Service Files

- **`docker-compose.yml`**: Defines and configures the `celery-worker` service, which is responsible for executing asynchronous tasks, including OCR.
- **`backend/src/services/tasks.py`**: Contains the definition of the main Celery task, `process_ocr`. This task is the entrypoint for an OCR job.
- **`backend/src/services/ocr.py`**: Contains the core OCR logic. It initializes the PaddleOCR engine based on environment variables and processes the images.
- **`backend/src/services/queue_manager.py`**: Sets up the Celery application.
- **`backend/src/api/ingest.py` & `backend/src/api/fetcher.py`**: These API modules trigger OCR processing by dispatching the `process_ocr` task.

## 6. Execution Flow & Triggering

The OCR process is asynchronous and queue-based with **automatic triggering** for all file ingestion methods.

### Automatic OCR Triggering (Updated 2025-09-27)

The system now automatically triggers OCR processing for **all** file ingestion paths:

1.  **FTP Import** (`backend/src/services/fetch_ftp.py`):
    - Files downloaded from FTP server automatically trigger OCR
    - Status flow: `"new"` → `"queued"` → OCR processing starts
    - Applies to both local inbox and remote FTP paths

2.  **Mobile Capture** (`backend/src/api/ingest.py`):
    - Files uploaded via mobile app automatically trigger OCR
    - OCR queued immediately after successful file save

3.  **Manual Endpoints** (for troubleshooting):
    - `/ingest/fetch-ftp` - FTP fetch with OCR triggering
    - `/ingest/queue-new` - Process all unprocessed files
    - `/ingest/process/{file_id}/ocr` - Process specific file

### Processing Flow

1.  **File Ingestion**: A new file is added to the system via FTP, mobile capture, or direct upload.
2.  **Automatic Task Dispatch**: The ingestion process automatically calls `process_ocr.delay(file_id)`, creating a message in the Redis queue.
3.  **Status Update**: File status updated from `"new"` to `"queued"`.
4.  **Worker Execution**: The `celery-worker` container picks up the job and executes the `process_ocr` task.
5.  **OCR Processing**: The worker calls the `run_ocr` function, which loads the image file(s) from the `STORAGE_DIR`.
6.  **Data Extraction**: The `run_ocr` function uses the PaddleOCR engine to extract text and coordinate data.
7.  **Result Persistence**: The `process_ocr` task saves the extracted data to the `unified_files` table and records the event in the `ai_processing_history` table.
8.  **Final Status**: File status updated to `"completed"` upon successful processing.

## 7. Data Storage and Structure

### Input Files
Receipt images are stored in subdirectories under the `STORAGE_DIR` path:
- Location: `{STORAGE_DIR}/{receipt_id}/`
- Example: `/data/storage/3bcb72bb-27a9-4209-996a-06ff052c8d0c/page-1.jpg`

### OCR Output Storage
The OCR results are stored in multiple locations:

#### 1. JSON Files on Disk
- **Bounding Boxes**: `{STORAGE_DIR}/{receipt_id}/boxes.json`
  - Contains array of text regions with coordinates and recognized text
  - Format: `[{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05, "field": "text content"}, ...]`

- **Line Items**: `{STORAGE_DIR}/line_items/{receipt_id}.json`
  - Contains extracted line items from the receipt
  - Format: `[{"description": "Item", "quantity": 1, "amount": 10.00, "vat_rate": 25}, ...]`

#### 2. Database Storage
- **Table**: `unified_files`
- **Fields Updated by OCR**:
  - `merchant_name`: Extracted merchant/vendor name
  - `gross_amount`: Total amount including VAT
  - `net_amount`: Amount excluding VAT
  - `purchase_datetime`: Extracted date/time of purchase
  - `ai_status`: Set to "ocr_done" after processing
  - `ai_confidence`: OCR confidence score (0.0 to 1.0)
  - **`ocr_raw`** ✅ **NEW**: Complete raw text extracted from the receipt image(s)

#### 3. Processing History
- **Table**: `ai_processing_history`
- Records each OCR job with timestamp and status

### File Structure Example
```
/data/storage/
├── 3bcb72bb-27a9-4209-996a-06ff052c8d0c/
│   ├── page-1.jpg           # Original receipt image
│   └── boxes.json           # OCR bounding boxes and text
├── line_items/
│   └── 3bcb72bb-27a9-4209-996a-06ff052c8d0c.json  # Extracted line items
└── ... (other receipts)
```

## 8. Manual OCR Processing

### Triggering OCR for Existing Receipts

The system provides tools to manually trigger OCR processing for receipts that have already been imported:

#### Method 1: Batch File (Windows)
Run the batch file from the project root:
```cmd
trigger_ocr.bat
```

This batch file will:
- Check that Python and required packages are installed
- Verify that the backend services are running
- Authenticate with the API using the ADMIN_PASSWORD from .env
- Fetch all receipts and trigger OCR processing for those not yet processed
- Provide a summary of the processing results

#### Method 2: Python Script
Alternatively, run the Python script directly:
```bash
python scripts/trigger_ocr_all.py
```

The script requires:
- Backend services running (docker-compose up)
- ADMIN_PASSWORD set in the .env file
- Network access to http://localhost:8008

### Complete System Reset (Updated 2025-09-27)

For development and testing purposes, the system includes a complete cleanup script:

```cmd
clean_all.bat
```

This script performs a **complete system reset**:
- Cleans local inbox folder (`/inbox/*`)
- Cleans Docker container inbox
- **Removes ALL files from storage folder** (`/storage/*`)
- Recreates empty storage structure
- Truncates all database tables

**After running clean_all.bat**: Re-import files via FTP or mobile capture, and OCR will automatically trigger for all new files.

### OCR Results Visualization

Once OCR processing is complete, the extracted text regions can be visualized in the web interface:

1. Navigate to the Receipts page
2. Click on a receipt preview to open the modal
3. OCR bounding boxes will appear as blue semi-transparent overlays on the image
4. Each box represents a detected text region with its coordinates

The OCR data includes:
- **Bounding boxes**: x, y, width, and height coordinates (as percentages of image dimensions)
- **Text content**: The recognized text within each bounding box
- **Semantic fields**: Extracted merchant name, date, amounts, etc.

### API Endpoints for OCR

- **Trigger OCR for a receipt**: `POST /ai/api/ingest/process/{receipt_id}/ocr`
  - Requires authentication (Bearer token)
  - Returns task ID for tracking

- **Get receipt details with OCR data**: `GET /ai/api/receipts/{receipt_id}`
  - Returns receipt information including `ocr_raw` field with complete extracted text
  - No authentication required for reading

- **Get OCR boxes for a receipt**: `GET /ai/api/receipts/{receipt_id}/ocr/boxes`
  - Returns array of bounding box data with text content
  - Used by the frontend to display OCR overlays

## 9. Recent Fixes and Improvements (Updated 2025-09-28)

### ✅ Critical Bug Fixes Resolved

1. **PaddleOCR Initialization Error Fixed**
   - **Issue**: `ValueError: Unknown argument: show_log` preventing OCR engine initialization
   - **Fix**: Removed deprecated `show_log` parameter from PaddleOCR constructor in `backend/src/services/ocr.py:62`
   - **Impact**: OCR processing now works without errors

2. **Raw OCR Text Storage Implemented**
   - **Enhancement**: Added complete raw text storage to `unified_files.ocr_raw` column
   - **Files Modified**:
     - `backend/src/services/tasks.py:340` - Save OCR text to database
     - `backend/src/api/receipts.py:299,329` - Expose OCR text via API
   - **Impact**: Full OCR text is now preserved and accessible

3. **OCR Functionality Verification**
   - **Status**: ✅ **FULLY FUNCTIONAL**
   - **Tested**: Swedish language receipt processing with 469 characters extracted
   - **Example Extract**: "VERIFIERAD AV ENHET\nDEBIT\nPSN:00\nVisa\nVISA CONTACTLESS..."

### Current OCR System Status

- ✅ **Engine**: PaddleOCR working without errors
- ✅ **Languages**: Swedish + English support confirmed
- ✅ **Storage**: Raw text saved to `ocr_raw` column
- ✅ **API**: OCR data exposed via `/receipts/{id}` endpoint
- ✅ **JSON**: Bounding boxes and line items saved to files
- ✅ **Batch Processing**: `trigger_ocr.bat` script functional

## 10. Remaining Work for a Complete OCR Service

The current implementation is capable of performing OCR, extracting raw text, and processing that text to derive semantic data. To align with the goal of a "fullständig OCR-tjänst" as described in `MIND_TECHNICAL_PLAN_v2.0.md`, the following steps are needed:

1.  **Advanced Entity Recognition**: Implement a more robust system to reliably identify and label key entities (Vendor, Date, Total, VAT, etc.) from the raw text blocks.
2.  **Data Normalization and Validation**: Clean and normalize extracted entities into standard formats (e.g., `YYYY-MM-DD` for dates, `float` for amounts).
3.  **Confidence Scoring**: Implement a reliable confidence score for *each extracted field*.
4.  **Canonical Data Mapping**: Map the validated, structured OCR data to the canonical `invoice_lines` schema to enable unified reconciliation and analysis.
5.  **Automatic OCR on Upload**: ✅ **COMPLETED** - The system now automatically triggers OCR when new receipts are uploaded via FTP or web interface.