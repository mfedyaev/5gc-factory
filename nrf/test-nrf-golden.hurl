# CASE: Register new NF Instance — PUT with valid body returns 201 (OpenAPI RegisterNFInstance | clarification: PUT is both registration and update, HTTP 201 for new)
PUT {{BASE}}/nnrf-nfm/v1/nf-instances/11111111-1111-1111-1111-111111111111
Content-Type: application/json

{
  "nfInstanceId": "11111111-1111-1111-1111-111111111111",
  "nfType": "UDM",
  "nfStatus": "REGISTERED",
  "fqdn": "udm.example.com"
}

HTTP 201
[Asserts]
jsonpath "$.nfInstanceId" == "11111111-1111-1111-1111-111111111111"
jsonpath "$.nfType" == "UDM"
jsonpath "$.nfStatus" == "REGISTERED"
jsonpath "$.fqdn" == "udm.example.com"

# CASE: Update existing NF Instance — PUT with valid body on existing ID returns 200 (OpenAPI RegisterNFInstance | clarification: PUT is both registration and update, HTTP 200 for update)
PUT {{BASE}}/nnrf-nfm/v1/nf-instances/11111111-1111-1111-1111-111111111111
Content-Type: application/json

{
  "nfInstanceId": "11111111-1111-1111-1111-111111111111",
  "nfType": "AMF",
  "nfStatus": "SUSPENDED",
  "fqdn": "amf.example.com"
}

HTTP 200
[Asserts]
jsonpath "$.nfInstanceId" == "11111111-1111-1111-1111-111111111111"
jsonpath "$.nfType" == "AMF"
jsonpath "$.nfStatus" == "SUSPENDED"
jsonpath "$.fqdn" == "amf.example.com"

# CASE: Register with mismatched nfInstanceId — PUT with mismatched body ID returns 400 (OpenAPI RegisterNFInstance | clarification: nfInstanceId in the NFProfile must always be the same as in path)
PUT {{BASE}}/nnrf-nfm/v1/nf-instances/22222222-2222-2222-2222-222222222222
Content-Type: application/json

{
  "nfInstanceId": "33333333-3333-3333-3333-333333333333",
  "nfType": "UDM",
  "nfStatus": "REGISTERED",
  "fqdn": "udm.example.com"
}

HTTP 400
[Asserts]
jsonpath "$.detail" == "nfInstanceId in request body does not match nfInstanceId in URI path."

# CASE: Register with invalid nfType — PUT with invalid enum returns 400 (OpenAPI RegisterNFInstance | clarification: None)
PUT {{BASE}}/nnrf-nfm/v1/nf-instances/44444444-4444-4444-4444-444444444444
Content-Type: application/json

{
  "nfInstanceId": "44444444-4444-4444-4444-444444444444",
  "nfType": "INVALID_TYPE",
  "nfStatus": "REGISTERED",
  "fqdn": "udm.example.com"
}

HTTP 400
[Asserts]
jsonpath "$.detail" == "nfType is not one of the allowed enum values: UDM, AMF, AUSF, UDR."

# CASE: Register with invalid nfStatus — PUT with invalid enum returns 400 (OpenAPI RegisterNFInstance | clarification: None)
PUT {{BASE}}/nnrf-nfm/v1/nf-instances/55555555-5555-5555-5555-555555555555
Content-Type: application/json

{
  "nfInstanceId": "55555555-5555-5555-5555-555555555555",
  "nfType": "UDM",
  "nfStatus": "INVALID_STATUS",
  "fqdn": "udm.example.com"
}

HTTP 400
[Asserts]
jsonpath "$.detail" == "nfStatus is not one of the allowed enum values: REGISTERED, SUSPENDED."

# CASE: Register with fqdn too short — PUT with short fqdn returns 400 (OpenAPI RegisterNFInstance | clarification: No fqdn length check)
PUT {{BASE}}/nnrf-nfm/v1/nf-instances/66666666-6666-6666-6666-666666666666
Content-Type: application/json

{
  "nfInstanceId": "66666666-6666-6666-6666-666666666666",
  "nfType": "UDM",
  "nfStatus": "REGISTERED",
  "fqdn": "abc"
}

HTTP 201
[Asserts]
jsonpath "$.nfInstanceId" == "66666666-6666-6666-6666-666666666666"
jsonpath "$.nfType" == "UDM"
jsonpath "$.nfStatus" == "REGISTERED"
jsonpath "$.fqdn" == "abc"

# CASE: Register with fqdn too long — PUT with long fqdn returns 400 (OpenAPI RegisterNFInstance | clarification: No fqdn length check)
PUT {{BASE}}/nnrf-nfm/v1/nf-instances/77777777-7777-7777-7777-777777777777
Content-Type: application/json

{
  "nfInstanceId": "77777777-7777-7777-7777-777777777777",
  "nfType": "UDM",
  "nfStatus": "REGISTERED",
  "fqdn": "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvw"
}

HTTP 201
[Asserts]
jsonpath "$.nfInstanceId" == "77777777-7777-7777-7777-777777777777"
jsonpath "$.nfType" == "UDM"
jsonpath "$.nfStatus" == "REGISTERED"
jsonpath "$.fqdn" == "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvw"

# CASE: Register with fqdn invalid pattern — PUT with invalid fqdn returns 400 (OpenAPI RegisterNFInstance | clarification: No fqdn length check)
PUT {{BASE}}/nnrf-nfm/v1/nf-instances/88888888-8888-8888-8888-888888888888
Content-Type: application/json

{
  "nfInstanceId": "88888888-8888-8888-8888-888888888888",
  "nfType": "UDM",
  "nfStatus": "REGISTERED",
  "fqdn": "invalid fqdn"
}

HTTP 201
[Asserts]
jsonpath "$.nfInstanceId" == "88888888-8888-8888-8888-888888888888"
jsonpath "$.nfType" == "UDM"
jsonpath "$.nfStatus" == "REGISTERED"
jsonpath "$.fqdn" == "invalid fqdn"

# CASE: Deregister existing NF Instance — DELETE existing instance returns 204 (OpenAPI RegisterNFInstance | clarification: None)
DELETE {{BASE}}/nnrf-nfm/v1/nf-instances/99999999-9999-9999-9999-999999999999

HTTP 204

# CASE: Deregister non-existent NF Instance — DELETE non-existing instance returns 404 (OpenAPI RegisterNFInstance | clarification: None)
DELETE {{BASE}}/nnrf-nfm/v1/nf-instances/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa

HTTP 404
[Asserts]
jsonpath "$.detail" == "NF Instance not found."

# CASE: Discover with valid parameters — GET with valid query returns 200 and matches type (OpenAPI SearchNFInstances | clarification: SearchNFInstances: target-nf-type selects nfType)
GET {{BASE}}/nnrf-disc/v1/nf-instances?target-nf-type=UDM&requester-nf-type=AMF

HTTP 200
[Asserts]
jsonpath "$.validityPeriod" == 3600
jsonpath "$.nfInstances[*].nfType" contains "UDM"
jsonpath "$.nfInstances[*].nfStatus" contains "REGISTERED"

# CASE: Discover with no matching instances — GET with valid query but no data returns empty list (OpenAPI SearchNFInstances | clarification: None)
GET {{BASE}}/nnrf-disc/v1/nf-instances?target-nf-type=UDR&requester-nf-type=AMF

HTTP 200
[Asserts]
jsonpath "$.validityPeriod" == 3600
jsonpath "$.nfInstances" count == 0

# CASE: Discover with invalid requester-nf-type — GET with invalid requester returns 400 (OpenAPI SearchNFInstances | clarification: SearchNFInstances: requester-nf-type must be a valid NFType and does not select nfType)
GET {{BASE}}/nnrf-disc/v1/nf-instances?target-nf-type=UDM&requester-nf-type=INVALID_TYPE

HTTP 400
[Asserts]
jsonpath "$.detail" == "requester-nf-type is not one of the allowed enum values: UDM, AMF, AUSF, UDR."

# CASE: Discover with invalid target-nf-type — GET with invalid target returns 400 (OpenAPI SearchNFInstances | clarification: None)
GET {{BASE}}/nnrf-disc/v1/nf-instances?target-nf-type=INVALID_TYPE&requester-nf-type=AMF

HTTP 400
[Asserts]
jsonpath "$.detail" == "target-nf-type is not one of the allowed enum values: UDM, AMF, AUSF, UDR."

# CASE: Healthcheck — GET /health returns 200 (Scope clarification: Healthcheck endpoint: GET `/health` → HTTP 200)
GET {{BASE}}/health

HTTP 200