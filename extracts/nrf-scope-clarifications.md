# Scope

  - NRF Service with two operations: RegisterNFInstance, NFDeregister, NFDiscover
  - MVP HTTP Service
  - Listen to PORT from environment or default 8080
  - Healthcheck endpoint: GET `/health` → HTTP 200
  - Stateless process, MongoDB storage (connection string from environment)


# Clarifications:
  - validityPeriod: from environment, default 3600
  - RegisterNFInstance: nfInstanceId in the NFProfile must always be the same as in path
  - RegisterNFInstance: PUT is both registration (NF is not in store, HTTP 201) and update (NF was in store, HTTP 200)
  - SearchNFInstances: target-nf-type selects nfType. requester-nf-type must be a valid NFType and does not select nfType.
  - SearchNFInstances: SearchResult contains full NFProfile objects
  - No fqdn length check

