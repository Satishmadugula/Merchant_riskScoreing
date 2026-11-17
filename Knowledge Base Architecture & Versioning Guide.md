# On-Premises Agent Knowledge Base: RBAC & Dataset Versioning Architecture

## 1. Core Architectural Decisions

### A. User-Propagated Roles vs. Static Agent Roles
* **Decision:** Use **User-Propagated Roles (On-Behalf-Of RBAC/ABAC)** rather than binding static roles to individual agents.
* **Why:** Binding permissions to agents leads to role explosion as data sources grow (e.g., `Finance_HR_Agent`, `Finance_Only_Agent`). Treating the agent as a stateless runtime that inherits caller permissions keeps the codebase unified.
* **Enforcement:** Always enforce access control at the **retrieval/database layer** via mandatory metadata filters (`WHERE data_source IN user.allowed_sources`), never via system prompts alone (which are vulnerable to prompt injection).

### B. Storage Layer vs. Retrieval Layer
* **Object Storage (MinIO / RustFS / Ceph):** Acts as the **System of Record** for raw and processed artifacts, partitioned by source prefix (`s3://kb-bucket/<source>/...`).
* **Search / Vector / Graph Index:** Acts as the **Low-Latency Retrieval Layer**. Storage-level permissions must be mirrored as metadata tags (`source`, `allowed_roles`, `commit_id`, `valid_from`, `valid_to`) on every indexed chunk or node.

---

## 2. Dataset-Level Versioning for Deterministic Evaluations

Because knowledge base data updates continuously, offline evaluations require point-in-time reproducibility so agents see the exact same data state that existed when a production response was generated.

### Why Raw Object Versioning Isn't Enough
* **MinIO / S3 Object Versioning** tracks individual files (`doc1.pdf -> v1, v2`), making point-in-time reconstruction across thousands of files slow and complex.
* **DVC + Object Storage** provides Git-style dataset commits and content-addressable deduplication, ideal for scheduled/batch updates.
* **lakeFS + Object Storage** provides native Git-like operations (`branch`, `commit`, `merge`, `tag`, `revert`) and curated **Datasets** directly on top of S3-compatible storage without duplicating data—ideal for continuous or frequent ingestion.

### Two Patterns for Index-Level Point-in-Time Replay
1. **Temporal Validity Windows (Append-Only Index):**
   * Tag indexed chunks with `valid_from` and `valid_to` timestamps.
   * **Production:** Queries `WHERE valid_to IS NULL`.
   * **Evaluation:** Replays with logged `eval_timestamp` using `WHERE valid_from <= eval_timestamp AND (valid_to > eval_timestamp OR valid_to IS NULL)`.
2. **Commit-Tagged Snapshots (lakeFS Integration):**
   * Tag indexed chunks with the immutable lakeFS `commit_id` generated on branch merge.
   * Log `(trace_id, user_roles, lakefs_commit_id, retrieved_chunk_ids)` in production traces so evaluations can deterministically replay any historical commit.

---

## 3. Storage Engine Comparison (On-Premises)

| Dimension | MinIO | Rust Object Stores (e.g., RustFS) | Ceph (via RADOS Gateway / RGW) |
| :--- | :--- | :--- | :--- |
| **Deployment Model** | Single binary/container; scales from 1 node to multi-node erasure coding. | Single lightweight binary/container; low memory footprint, Apache 2.0 license. | Heavy distributed cluster (min. 3 nodes, 16+ GB RAM/node, dedicated storage ops). |
| **S3 & IAM Support** | Mature S3 API and granular IAM policies (AGPLv3 / commercial). | S3-compatible with built-in web console; zero GC tail latency. | Full S3 compatibility, IAM, and object versioning alongside block/POSIX storage. |
| **Dataset Versioning** | Object-level only (pair with lakeFS or DVC). | Object-level only (pair with lakeFS or DVC). | Object-level only (pair with lakeFS or DVC). |

### Why Choose MinIO Over Ceph for an On-Prem Knowledge Base
* **Operational Simplicity:** Single binary/container vs. managing `MON`, `OSD`, `MGR`, and `RGW` daemons and CRUSH maps.
* **S3 Performance:** Purpose-built for S3 without gateway translation overhead.
* **Built-in Data Protection:** Inline erasure coding and HighwayHash bitrot protection out of the box.
* *(Choose Ceph only if your infrastructure team already operates an existing Ceph cluster.)*

---

## 4. Target On-Prem Stack: MinIO + lakeFS + Dagster + PostgreSQL

### Licensing & RBAC Note
* **lakeFS Open Source (OSS):** Provides full dataset-level versioning (branches, commits, tags, zero-copy snapshots, webhooks) on-premises.
* **RBAC Enforcement (OSS Tier):** Granular IAM policies inside lakeFS require lakeFS Enterprise. With OSS, enforce RBAC via **MinIO IAM policies** (isolating ingestion pipelines per source prefix) + **Retrieval Index metadata filtering** (isolating agent queries by user/agent roles).

### Hardware & Software Requirements
* **MinIO:** 4–8 vCPUs, 16–32 GB RAM, dedicated NVMe/SSD drives.
* **lakeFS Server:** 2–4 vCPUs, 4–8 GB RAM (stateless Go binary).
* **PostgreSQL 14+:** 4 vCPUs, 8–16 GB RAM (shared instance hosting separate `dagster_db` and `lakefs_db` databases).
* **Dagster (Webserver + Daemon + User Code):** 4–8 vCPUs, 16+ GB RAM.
* **Network:** 10GbE internal network if deployed across multiple physical hosts.
* **Python Dependencies:** `dagster`, `lakefs-sdk` (or `lakefs`), `boto3`, plus your parsing and vector/search client libraries.

---

## 5. End-to-End Architecture Diagram

```text
================================================================================
                        1. INGESTION & VERSIONING LAYER
================================================================================
  [Data Sources] ──► [Dagster Pipelines (Python)]
  (DBs, Docs, APIs)        │
                           ├─ 1. Create/checkout branch: `ingest-run-42`
                           ├─ 2. Write raw & parsed chunks via S3 API ──────┐
                           ├─ 3. Run Dagster Asset Checks (data quality)    │
                           └─ 4. Atomic Merge to `main` ──► Commit ID: `c9a81f`
                                                                            │
                                                                            ▼
  [Postgres (lakefs_db)] ◄──(Metadata/Commits)── [lakeFS Server (S3 Gateway)]
                                                              │
                                                 (Stores physical blobs)
                                                              ▼
                                                 [MinIO Server (On-Prem NVMe)]
                                                 Bucket: `s3://kb-storage/`

================================================================================
                        2. INDEXING & RBAC SYNC LAYER
================================================================================
  [lakeFS Post-Merge Webhook] ──► Triggers Dagster Indexing Job for Commit `c9a81f`
                                          │
                                          ▼
                             [Search / Vector / Graph Index]
                             Every indexed chunk is tagged with:
                             • `source`: "finance" | "hr" | "ops"
                             • `allowed_roles`: ["role_finance", "role_admin"]
                             • `commit_id`: "c9a81f"
                             • `valid_from` / `valid_to` (for point-in-time replay)

================================================================================
                        3. AGENT QUERY & EVALUATION LAYER
================================================================================
  [User / Calling App] ──(Passes JWT: user_roles + optional eval_commit_id)──► [Single Agent]
                                                                                   │
         ┌─────────────────────────────────────────────────────────────────────────┘
         ▼
  [Retrieval Tool / Gateway]
  • Production Query:  WHERE source IN user_roles AND valid_to IS NULL
  • Evaluation Replay: WHERE source IN logged_roles AND commit_id == logged_commit_id
```

---

## 6. Operational Workflow Summary

1. **Isolated Ingestion:** Dagster opens a temporary lakeFS branch, writes files through the lakeFS S3 gateway (`http://lakefs:8000`) which stores blobs in MinIO, and runs data quality asset checks.
2. **Atomic Commit:** Once checks pass, Dagster merges the branch into `main`, producing an immutable commit SHA (`c9a81f`) and triggering a post-merge webhook.
3. **Metadata-Tagged Indexing:** A Dagster indexing job reads the diff from commit `c9a81f`, chunks/embeds documents, and writes them to the retrieval index tagged with `source`, `allowed_roles`, `commit_id`, and `valid_from`/`valid_to`.
4. **Scoped Queries & Evaluation Replay:** Production agent calls filter by the caller's role claims against active records (`valid_to IS NULL`), while evaluation runs pass the logged `lakefs_commit_id` and `user_roles` to reproduce exact historical context.