#### 5.2.2.2 NFRegister

The NF Service Consumer shall send a PUT request to the resource URI representing the NF Instance. URI variable {nfInstanceID} is UUID.

The UUIDs should be lower-case, upper-case should be converted to lower-case.

On success, "201 Created" shall be returned, response content shall contain the representation of the created resource 

On failure due to errors in URI or NFProfile JSON object, the NRF shall return "400 Bad Request" status code with the ProblemDetails IE providing details of the error.

#### 5.2.2.4 NFDeregister

Removes the profile of a NF previously registered in the NRF by DELETE request on the URI of specific NF Instance.

NF Service Consumer shall send a DELETE request to the resource URI representing the NF Instance. The request body shall be empty.

On success, 204, response body empty.

On failure if is not found - 404 with the ProblemDetails IE providing details of the error.

#### 5.3.2.2 NFDiscover

Discovers the set of NF Instances represented by their NF Profile, that are currently registered in NRF and satisfy a number of input query parameters.

The NF Service Consumer shall send an HTTP GET request to the resource URI "nf-instances" with query parameters. 

On success, "200 OK" shall be returned. The response body shall contain an array of NF Profile objects that satisfy filter criteria and in REGISTERED status, or empty array

On failure due to errors in the URI query parameters, return 400 with the ProblemDetails IE providing details of the error.