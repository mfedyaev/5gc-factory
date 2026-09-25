# HTTP service contract

NRF Service implementing RegisterNFInstance, NFDeregister, and NFDiscover (SearchNFInstances) with a healthcheck. The service listens on PORT from environment or 8080. It uses MongoDB. `validityPeriod` in responses is from environment or default 3600. PUT on `/nnrf-nfm/v1/nf-instances/{nfInstanceID}` creates (201) or updates (200). `nfInstanceId` in path must match `nfInstanceId` in body. Discovery filters by `target-nf-type` (selects `nfType`) and `requester-nf-type` (validates enum, does not filter). Response contains full `NFProfile` objects in REGISTERED status.

## Routes

### PUT /nnrf-nfm/v1/nf-instances/{nfInstanceID}
Register or update an NF Instance.
Path parameter:
- `nfInstanceID`: UUID string, required, non-empty.

Request body (`application/json`):
- `nfProfile`: Object.
  - `nfInstanceId`: UUID string, must equal path `nfInstanceID`.
  - `nfType`: String, enum: UDM, AMF, AUSF, UDR.
  - `nfStatus`: String, enum: REGISTERED, SUSPENDED.
  - `fqdn`: String, pattern `^([0-9A-Za-z]([-0-9A-Za-z]{0,61}[0-9A-Za-z])?\.)+[A-Za-z]{2,63}\.?$`, minLength 4, maxLength 253.

### DELETE /nnrf-nfm/v1/nf-instances/{nfInstanceID}
Deregister an NF Instance.
Path parameter:
- `nfInstanceID`: UUID string, required, non-empty.

Request body: Empty.

### GET /nnrf-disc/v1/nf-instances
Discover NF Instances.
Query parameters:
- `target-nf-type`: String, required, enum: UDM, AMF, AUSF, UDR. Selects `nfType` in results.
- `requester-nf-type`: String, required, enum: UDM, AMF, AUSF, UDR. Must be valid, but does not filter results.

### GET /health
Healthcheck.

## Cases

Case 1: Register new NF Instance
- What is sent: PUT to `/nnrf-nfm/v1/nf-instances/{nfInstanceID}` with body containing `nfInstanceId` matching the path UUID, valid `nfType`, `nfStatus`, and valid `fqdn`.
- HTTP status: 201 Created
- Response: `application/json` containing the `NFProfile` object stored.

Case 2: Update existing NF Instance
- What is sent: PUT to `/nnrf-nfm/v1/nf-instances/{nfInstanceID}` with body containing `nfInstanceId` matching the path UUID, valid `nfType`, `nfStatus`, and valid `fqdn`. The instance already exists in the store.
- HTTP status: 200 OK
- Response: `application/json` containing the updated `NFProfile` object.

Case 3: Register with mismatched nfInstanceId
- What is sent: PUT to `/nnrf-nfm/v1/nf-instances/{uuid-path}` with body where `nfInstanceId` differs from `{uuid-path}`.
- HTTP status: 400 Bad Request
- Response: `application/problem+json` with `ProblemDetails.detail`: "nfInstanceId in request body does not match nfInstanceId in URI path."

Case 4: Register with invalid nfType
- What is sent: PUT to `/nnrf-nfm/v1/nf-instances/{nfInstanceID}` with body containing `nfType` value "INVALID_TYPE".
- HTTP status: 400 Bad Request
- Response: `application/problem+json` with `ProblemDetails.detail`: "nfType is not one of the allowed enum values: UDM, AMF, AUSF, UDR."

Case 5: Register with invalid nfStatus
- What is sent: PUT to `/nnrf-nfm/v1/nf-instances/{nfInstanceID}` with body containing `nfStatus` value "INVALID_STATUS".
- HTTP status: 400 Bad Request
- Response: `application/problem+json` with `ProblemDetails.detail`: "nfStatus is not one of the allowed enum values: REGISTERED, SUSPENDED."

Case 6: Register with fqdn too short
- What is sent: PUT to `/nnrf-nfm/v1/nf-instances/{nfInstanceID}` with body containing `fqdn` with length 3.
- HTTP status: 400 Bad Request
- Response: `application/problem+json` with `ProblemDetails.detail`: "fqdn length is below the minimum of 4."

Case 7: Register with fqdn too long
- What is sent: PUT to `/nnrf-nfm/v1/nf-instances/{nfInstanceID}` with body containing `fqdn` with length 254.
- HTTP status: 400 Bad Request
- Response: `application/problem+json` with `ProblemDetails.detail`: "fqdn length exceeds the maximum of 253."

Case 8: Register with fqdn invalid pattern
- What is sent: PUT to `/nnrf-nfm/v1/nf-instances/{nfInstanceID}` with body containing `fqdn` that fails the pattern regex.
- HTTP status: 400 Bad Request
- Response: `application/problem+json` with `ProblemDetails.detail`: "fqdn does not match the required format."

Case 9: Deregister existing NF Instance
- What is sent: DELETE to `/nnrf-nfm/v1/nf-instances/{nfInstanceID}` where the instance exists.
- HTTP status: 204 No Content
- Response: Empty body.

Case 10: Deregister non-existent NF Instance
- What is sent: DELETE to `/nnrf-nfm/v1/nf-instances/{nfInstanceID}` where the instance does not exist.
- HTTP status: 404 Not Found
- Response: `application/problem+json` with `ProblemDetails.detail`: "NF Instance not found."

Case 11: Discover with valid parameters
- What is sent: GET to `/nnrf-disc/v1/nf-instances?target-nf-type=UDM&requester-nf-type=AMF`.
- HTTP status: 200 OK
- Response: `application/json` containing a `SearchResult` object with `validityPeriod` set to 3600 and `nfInstances` array containing full `NFProfile` objects where `nfType` is UDM and `nfStatus` is REGISTERED.

Case 12: Discover with no matching instances
- What is sent: GET to `/nnrf-disc/v1/nf-instances?target-nf-type=UDM&requester-nf-type=AMF` where no registered UDM instances exist.
- HTTP status: 200 OK
- Response: `application/json` containing a `SearchResult` object with `validityPeriod` set to 3600 and empty `nfInstances` array.

Case 13: Discover with invalid requester-nf-type
- What is sent: GET to `/nnrf-disc/v1/nf-instances?target-nf-type=UDM&requester-nf-type=INVALID_TYPE`.
- HTTP status: 400 Bad Request
- Response: `application/problem+json` with `ProblemDetails.detail`: "requester-nf-type is not one of the allowed enum values: UDM, AMF, AUSF, UDR."

Case 14: Discover with invalid target-nf-type
- What is sent: GET to `/nnrf-disc/v1/nf-instances?target-nf-type=INVALID_TYPE&requester-nf-type=AMF`.
- HTTP status: 400 Bad Request
- Response: `application/problem+json` with `ProblemDetails.detail`: "target-nf-type is not one of the allowed enum values: UDM, AMF, AUSF, UDR."

Case 15: Healthcheck
- What is sent: GET to `/health`.
- HTTP status: 200 OK
- Response: HTTP 200.

## Open questions

None.