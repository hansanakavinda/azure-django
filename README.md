# Authentication API

## Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/auth/register/` | No | Create new user account |
| POST | `/api/auth/login/` | No | Get JWT tokens |
| POST | `/api/auth/logout/` | Yes | Blacklist refresh token |
| POST | `/api/auth/token/refresh/` | No | Get new access token |

---

## POST /api/auth/register/

**Request Body:**
```json
{
  "username": "string (unique, max 150 chars)",
  "password": "string (min 8 chars)",
  "email": "string (optional)"
}
```

**Returns:** `user_id`, `username`, `access` token, `refresh` token

---

## POST /api/auth/login/

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Returns:** `user_id`, `username`, `access` token, `refresh` token

---

## POST /api/auth/logout/

**Request Body:**
```json
{
  "refresh": "string"
}
```

**Returns:** Success message

---

## POST /api/auth/token/refresh/

**Request Body:**
```json
{
  "refresh": "string"
}
```

**Returns:** New `access` token, `refresh` token

---

## Authentication

Use the `access` token in header:
```
Authorization: Bearer <access_token>
```

# Documents API

## Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/pdfs/` | Yes | List user's documents |
| GET | `/api/pdfs/{id}/` | Yes | Get document details |
| POST | `/api/pdfs/upload/` | Yes | Upload PDF files |
| GET | `/api/pdfs/{id}/download/` | Yes | Get temporary download URL |

---

## GET /api/pdfs/

List all user documents with optional filtering and searching.

**Query Parameters:**
```
?filename=<string>          # Search in filename (case insensitive)
?date_from=<YYYY-MM-DD>     # Uploaded after this date
?date_to=<YYYY-MM-DD>       # Uploaded before this date
?size_min=<bytes>           # Minimum file size
?size_max=<bytes>           # Maximum file size
?search=<string>            # Search in filename or description
?ordering=<field>           # Sort by: uploaded_at, file_size, original_filename
```

**Returns:** `documents[]`, `count`, pagination info

---

## GET /api/pdfs/{id}/

Get details of a specific document.

**Returns:** `id`, `original_filename`, `file_size`, `file_size_kb`, `file_size_mb`, `uploaded_at`, `updated_at`, `owner`

---

## POST /api/pdfs/upload/

Upload one or more PDF files.

**Request Body (multipart/form-data):**
```
files: File[] (max 20 files, must be valid PDFs)
job_description: string (optional, max 5000 chars)
search_all: boolean (optional, default: true)
```

**Returns:** `uploaded`, `failed`, `total`, `results[]` with status and details for each file

**Validations:**
- Max 20 files per request
- Max file size: configured in settings
- Must be valid PDF files (checked by file header)
- Filename max 255 characters

---

## GET /api/pdfs/{id}/download/

Get a temporary signed URL to download a PDF file.

**Returns:** `download_url`, `expires_at`, `expires_in_hours`, `filename`

**Note:** URL expires after 1 hour

# Search API

## Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/search/results/` | Yes | List search results |
| GET | `/api/search/results/{id}/` | Yes | Get search result detail |
| GET | `/api/search/candidates/{candidate_id}/` | Yes | Get candidate profile |
| GET | `/api/search/test-candidates/` | Yes | List all candidates |
| GET | `/api/search/test-candidates/{candidate_id}/` | Yes | Get candidate details (test) |
| POST | `/api/search/webhook/` | No | Receive ranking results from Azure |

---

## GET /api/search/results/

List search results for the authenticated user.

**Query Parameters:**
```
?batch_id=<uuid>    # Filter by specific upload batch
?limit=<int>        # Results per page
?offset=<int>       # Pagination offset
```

**Returns:** `results[]` with `id`, `batch_id`, `candidate_id`, `score`, `rank`, `received_at`

---

## GET /api/search/results/{id}/

Get details of a specific search result including batch information.

**Returns:** `id`, `batch_id`, `job_description`, `search_all`, `candidate_id`, `score`, `rank`, `received_at`

---

## GET /api/search/candidates/{candidate_id}/

Fetch full candidate profile from database.

**Security:** User must have a search result with this candidate_id in their results

**Returns:** Full candidate profile data from Cosmos DB

---

## GET /api/search/test-candidates/

List all candidates in database (paginated).

**Query Parameters:**
```
?limit=<int>            # Results per page (default: 10)
?page_token=<string>    # Token for next page
```

**Returns:** `candidates[]`, `next_page_token`

---

## GET /api/search/test-candidates/{candidate_id}/

Get candidate details by ID (test endpoint).

**Returns:** Full candidate profile data from Cosmos DB

---

## POST /api/search/webhook/

Webhook endpoint called by Azure after ranking is complete.

**Authentication:** Signature verified using shared secret

**Request Body:**
```json
{
  "batch_id": "uuid",
  "status": "complete|failed",
  "error_message": "string (if failed)",
  "results": [
    {
      "candidate_id": "string",
      "score": "0.0 to 1.0"
    }
  ]
}
```

**Returns:** Results saved count and batch info

**Note:** Automatically ranks results by score (highest first) and saves to database


