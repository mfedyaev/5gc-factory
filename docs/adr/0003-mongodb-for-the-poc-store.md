# 3. MongoDB for the PoC store

Status: Accepted

Date: 2026-09-25

## Context

The PoC store is either an in-memory map or MongoDB. The map is invisible while the process runs. MongoDB leaves the documents readable during debugging, and for this PoC it adds no real operational cost.

## Decision

The store is MongoDB.

[free5GC](https://github.com/free5gc/free5gc) is the role model. Its NRF stores NF profiles in MongoDB (`MongoDBUrl`, collection `NfProfile`). Its UDR uses the same database for subscriber data. Documents match the JSON bodies on the wire, and queries are document queries.

## Consequences

Tests and debugging need a running MongoDB instance. Starting one is easy, and we accept that.
