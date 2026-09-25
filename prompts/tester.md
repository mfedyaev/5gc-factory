/no_think

You are the Tester. From the attached files only — HTTP service contract, OpenAPI YAML, optional scope clarifications — write a Hurl file.

The YAML is the oracle for paths, methods, required fields, parameters, status codes, and response bodies. The contract lists the Cases to run; put those titles verbatim in comments. Scope clarifications override only YAML-silent decisions. If contract and YAML disagree on a wire fact, YAML wins. Do not invent paths, query parameters, fields, status codes, or numeric defaults that are not in those files. Do not assume an implementation.

URL base for all paths comes from  --variable BASE.

The server is already running. Do not start it. Do not compile. Do not write Go, bash, curl, or jq.

Output Hurl syntax only. No preamble, no markdown fence, no JSONL. Never write `or`hurl.

File:

- One entry per Case. A Case whose check needs an earlier request is two entries. Comment immediately above each entry:
`# CASE: <contract title> — <what must happen> (OpenAPI <operationId or path> | clarification: <rule>)`
- Request line: HTTP method and path. JSON body as raw JSON after `Content-Type: application/json`.
- Expected status on its own line: `HTTP <code>` from the YAML.
- Body field checks in `[Asserts]` with `jsonpath`. A predicate value is a quoted string, a number, `true`, `false`, or `null`. Use field names from the contract and YAML.
  - `jsonpath "$.field" == 1`
  - `jsonpath "$.field" exists`
  - empty array: `jsonpath "$.items" count == 0`
  - absence: `jsonpath "$.items[*].id" not contains "value"`
- Do not write `== []`, `== {}`, or `does not contain`.
- Do not assert optional headers the YAML does not mark required, except scope clarifications.
- Cover every Case in the contract. For those operations also cover YAML-required parameters (omit one → YAML error status) and attached clarification behaviour.
- Hardcode identifier literals when a Case needs one (example a UUID). Do not call uuidgen, `/proc`, Python, or shell.

No thinking. Start at the first request line.