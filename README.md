# Resume Scoring API

This project exposes a versioned API under `/api/v1/`.

## Common Response Format

All endpoints use the same envelope:

```json
{
  "success": true,
  "message": "...",
  "data": {},
  "errors": null
}
```

On failures, `success` is `false` and `errors` contains the validation or runtime details.

## Authentication

JWT authentication is used throughout the API.

```
Authorization: Bearer <access_token>
```

## API Docs

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/schema/` | OpenAPI schema |
| GET | `/api/v1/docs/` | Swagger UI |

# Authentication API

## Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/v1/auth/register/` | No | Create a new user account |
| POST | `/api/v1/auth/login/` | No | Get JWT tokens |
| POST | `/api/v1/auth/logout/` | Yes | Blacklist a refresh token |
| POST | `/api/v1/auth/token/refresh/` | No | Refresh JWT tokens |

## POST /api/v1/auth/register/

Request body:

```json
{
  "username": "string",
  "email": "string (optional)",
  "password": "string",
  "confirm_password": "string"
}
```

Notes:

- `username` must start with a letter and can contain letters, numbers, underscores, and hyphens.
- `password` must be at least 8 characters and include uppercase, lowercase, a number, and a special character.
- `confirm_password` must match `password`.

Returns `user_id`, `username`, `access`, and `refresh` in `data`.

## POST /api/v1/auth/login/

Request body:

```json
{
  "username": "string",
  "password": "string"
}
```

Returns `user_id`, `username`, `access`, and `refresh` in `data`.

## POST /api/v1/auth/logout/

Request body:

```json
{
  "refresh": "string"
}
```

Blacklists the refresh token and returns a success message.

## POST /api/v1/auth/token/refresh/

Request body:

```json
{
  "refresh": "string"
}
```

Returns refreshed JWT data in `data`. Because refresh rotation is enabled, the response may include a new `refresh` token as well as a new `access` token.

# Documents API

## Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/v1/pdfs/` | Yes | List the current user's documents |
| GET | `/api/v1/pdfs/{id}/` | Yes | Get document details |
| POST | `/api/v1/pdfs/upload/` | Yes | Upload PDF files |
| GET | `/api/v1/pdfs/{id}/download/` | Yes | Get a temporary download URL |

## GET /api/v1/pdfs/

Lists the authenticated user's active documents.

Query parameters:

```
?filename=<string>          # Case-insensitive filename match
?date_from=<YYYY-MM-DD>     # Uploaded on or after this date
?date_to=<YYYY-MM-DD>       # Uploaded on or before this date
?size_min=<bytes>           # Minimum file size
?size_max=<bytes>           # Maximum file size
?search=<string>            # Search filename and description
?ordering=<field>           # uploaded_at, file_size, original_filename
?page=<int>                 # DRF page number pagination
```

Response `data` includes `count`, `next`, `previous`, and `documents`.

Each document includes:

- `id`
- `original_filename`
- `file_size`
- `file_size_kb`
- `file_size_mb`
- `uploaded_at`
- `updated_at`
- `owner`

## GET /api/v1/pdfs/{id}/

Returns a single document for the authenticated user. The payload uses the same document fields listed above.

## POST /api/v1/pdfs/upload/

Uploads one or more PDF files as `multipart/form-data`.

Request fields:

```text
files: File[]             # Required, max 20 files
job_description: string   # Optional, max 5000 chars
search_all: boolean       # Optional, default true
```

Validations enforced by the API:

- Maximum of 20 files per request.
- Maximum file size is configured in settings.
- Files must be valid PDFs, checked by file header and MIME type.
- Filenames must be 255 characters or fewer.

Response `data` includes `uploaded`, `failed`, `total`, and `results`.

If `job_description` is provided, an upload batch is created and the backend sends a processing signal with a callback URL to `/api/v1/search/webhook/`.

## GET /api/v1/pdfs/{id}/download/

Returns a temporary signed download URL for the file.

Response fields:

- `download_url`
- `expires_at`
- `expires_in_hours`
- `filename`

The URL expires after 1 hour.

# Search API

## Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/v1/search/results/` | Yes | List the current user's search results |
| GET | `/api/v1/search/results/{id}/` | Yes | Get search result details |
| GET | `/api/v1/search/candidates/{candidate_id}/` | Yes | Get a candidate profile if it appears in the user's results |
| GET | `/api/v1/search/test-candidates/` | Yes | List all candidates in Cosmos DB |
| GET | `/api/v1/search/test-candidates/{candidate_id}/` | Yes | Get a candidate profile by ID |
| POST | `/api/v1/search/webhook/` | No | Receive ranking results from Azure |

## GET /api/v1/search/results/

Lists the authenticated user's search results.

Query parameters:

```
?batch_id=<uuid>    # Filter by upload batch
?page=<int>         # DRF page number pagination
```

Response `data` includes `count`, `next`, `previous`, and `results`.

Each result includes:

- `id`
- `batch_id`
- `candidate_id`
- `score`
- `rank`
- `received_at`

## GET /api/v1/search/results/{id}/

Returns a single search result with batch context.

The detail payload adds:

- `job_description`
- `search_all`

## GET /api/v1/search/candidates/{candidate_id}/

Returns a full candidate profile from Cosmos DB.

Access is restricted to users who already have that `candidate_id` in one of their search results.

## GET /api/v1/search/test-candidates/

Returns a paginated list of candidates from Cosmos DB for testing.

Query parameters:

```
?limit=<int>         # Optional page size, default 10
?page_token=<string> # Optional continuation token
```

Response `data` includes `candidates` and `next_page_token`.

## GET /api/v1/search/test-candidates/{candidate_id}/

Returns a single candidate profile from Cosmos DB using a direct point read.

## POST /api/v1/search/webhook/

Webhook endpoint called by Azure when ranking completes.

Authentication is based on the `X-Webhook-Signature` header and the shared webhook secret.

Request body:

```json
{
  "batch_id": "uuid",
  "status": "complete",
  "error_message": "string",
  "results": [
    {
      "candidate_id": "string",
      "score": 0.95
    }
  ]
}
```

Notes:

- `status` must be `complete` or `failed`.
- `score` must be a number between 0 and 1.
- Results are sorted by score descending before being saved.

The response reports how many results were saved and which batch was processed.


