# How to Connect to Loopia FTP

This document describes how the Mind2 system connects to Loopia's FTP server to fetch files for processing.

## Overview

The system uses a standard FTP connection to Loopia's FTP cluster to download documents (PDFs, images) which are then processed through the AI workflows.

## Configuration

### Environment Variables

Add these variables to your `.env` file:

```bash
# FTP Connection Settings
FTP_HOST=ftpcluster.loopia.se
FTP_PORT=21
FTP_USER=<your-ftp-username>
FTP_PASS=<your-ftp-password>
FTP_REMOTE_DIR=/
FTP_LOCAL_DIR=./inbox
FTP_LOCAL_MOVE_DIR=/data/inbox/imported

# Connection Options
FTP_TLS=false
FTP_PASSIVE=true

# File Handling
FTP_ALLOWED_EXT=pdf,jpg,jpeg,png,txt,mp3,mp4,json
FTP_DELETE_AFTER=false
```

### Variable Descriptions

| Variable | Description | Default |
|----------|-------------|---------|
| `FTP_HOST` | Loopia FTP server hostname | **Required** |
| `FTP_PORT` | FTP port | 21 |
| `FTP_USER` | FTP username from Loopia | "anonymous" |
| `FTP_PASS` | FTP password from Loopia | "anonymous@" |
| `FTP_REMOTE_DIR` | Directory on FTP server to fetch from | "/" |
| `FTP_LOCAL_DIR` | Local fallback directory if FTP unavailable | "./inbox" |
| `FTP_LOCAL_MOVE_DIR` | Where to move files after local processing | "/data/inbox/imported" |
| `FTP_TLS` | Use FTPS/TLS encryption | false |
| `FTP_PASSIVE` | Use passive mode (recommended) | true |
| `FTP_ALLOWED_EXT` | Comma-separated list of allowed file extensions | "pdf,jpg,jpeg,png" |
| `FTP_DELETE_AFTER` | Delete files from FTP after successful download | false |

## Setting Up Loopia FTP Account

### 1. Create FTP Account in Loopia

1. Log in to Loopia Customer Zone: https://www.loopia.se/loopia-customer-zone/
2. Go to **Webbhotell** > **FTP-konton**
3. Click **Skapa FTP-konto**
4. Set username and password
5. Define the home directory for the FTP account

### 2. Note the Connection Details

- **Server**: `ftpcluster.loopia.se` (Loopia's standard FTP cluster)
- **Port**: 21 (standard FTP)
- **Username**: The username you created (e.g., `ftpuploadsmind`)
- **Password**: The password you set

### 3. Test Connection

Test the connection using any FTP client (FileZilla, WinSCP, etc.) before configuring Mind2.

## How It Works

### Architecture

```
Loopia FTP Server                    Mind2 System
+------------------+                 +------------------+
|                  |     FTP         |                  |
| /documents/      | <-------------> | ftp_service.py   |
| - receipt1.pdf   |                 |       |          |
| - receipt1.json  |                 |       v          |
| - image.jpg      |                 | fetch_ftp.py     |
|                  |                 |       |          |
+------------------+                 |       v          |
                                     | unified_files DB |
                                     |       |          |
                                     |       v          |
                                     | AI Workflows     |
                                     +------------------+
```

### Fetch Process

1. **Connection**: System connects to `ftpcluster.loopia.se` using configured credentials
2. **List Files**: Lists all files in `FTP_REMOTE_DIR` matching `FTP_ALLOWED_EXT`
3. **Download**: For each file:
   - Downloads the file binary content
   - Attempts to download accompanying `.json` metadata file (optional)
   - Calculates SHA256 hash for duplicate detection
4. **Storage**: Saves file to internal storage system
5. **Database**: Creates record in `unified_files` table with metadata
6. **Workflow**: Dispatches to appropriate AI workflow:
   - WF1 (images) - Receipt processing
   - WF2 (PDFs) - PDF split and processing
7. **Cleanup**: Optionally deletes file from FTP if `FTP_DELETE_AFTER=true`

### Optional Metadata Files

You can include a `.json` file alongside each document with additional metadata:

```json
{
  "file_id": "original_id_from_source",
  "original_name": "kvitto_2025-01-12.pdf",
  "timestamp": "2025-01-12T10:30:00+02:00",
  "file_size": 12345,
  "file_type": "application/pdf",
  "location": {
    "latitude": 59.3293,
    "longitude": 18.0686,
    "acc": 5.0
  },
  "tags": ["fuel", "company_car"]
}
```

The metadata file should have the same name as the document with `.json` extension:
- `receipt.pdf` -> `receipt.json`

## API Usage

### Trigger FTP Fetch

```bash
curl -X POST http://localhost:8008/ai/api/ingest/fetch-ftp \
  -H "Authorization: Bearer <token>"
```

### Response

```json
{
  "downloaded": [
    ["abc123-uuid", "receipt1.pdf"],
    ["def456-uuid", "receipt2.jpg"]
  ],
  "skipped": ["duplicate.pdf"],
  "errors": []
}
```

## Code Files

| File | Purpose |
|------|---------|
| `backend/src/services/ftp_service.py` | FTP connection and operations |
| `backend/src/services/fetch_ftp.py` | File fetching and processing logic |
| `backend/src/api/fetcher.py` | REST API endpoint |

## Fallback Mode

If `FTP_HOST` is not configured or connection fails, the system falls back to reading from `FTP_LOCAL_DIR` (local filesystem). This is useful for:
- Development without FTP access
- Manual file imports
- Testing

## Troubleshooting

### Connection Refused

1. Verify `FTP_HOST` and `FTP_PORT` are correct
2. Ensure `FTP_PASSIVE=true` (required for most firewall configurations)
3. Check if Loopia account is active

### Authentication Failed

1. Verify `FTP_USER` and `FTP_PASS` in `.env`
2. Test credentials with external FTP client
3. Check Loopia Customer Zone for correct username

### Files Not Appearing

1. Check `FTP_REMOTE_DIR` is correct
2. Verify file extensions are in `FTP_ALLOWED_EXT`
3. Check `ai_processing_history` table for errors

### Timeout Errors

The FTP connection has a 20-second timeout. If you experience timeouts:
1. Check network connectivity to Loopia
2. Verify Loopia service status
3. Consider if files are too large

## Security Notes

- Store credentials only in `.env` file (not in version control)
- Consider enabling `FTP_TLS=true` if Loopia supports FTPS
- Use `FTP_DELETE_AFTER=true` in production to avoid reprocessing
- Loopia FTP cluster uses standard FTP (port 21) - data is not encrypted in transit

## Docker Configuration

The FTP variables are exposed to the `ai-api` container in `docker-compose.yml`:

```yaml
ai-api:
  environment:
    - FTP_HOST=${FTP_HOST}
    - FTP_PORT=${FTP_PORT}
    - FTP_USER=${FTP_USER}
    - FTP_PASS=${FTP_PASS}
    - FTP_REMOTE_DIR=${FTP_REMOTE_DIR}
    - FTP_TLS=${FTP_TLS}
    - FTP_PASSIVE=${FTP_PASSIVE}
    - FTP_ALLOWED_EXT=${FTP_ALLOWED_EXT}
    - FTP_DELETE_AFTER=${FTP_DELETE_AFTER}
```
