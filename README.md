# HPC Log Analytics

End-to-end analytics pipeline for the **Thunderbird** HPC supercomputer log dataset.  
Ingests 211 M log lines via **PySpark → HDFS → MongoDB** and serves an interactive **Streamlit** dashboard.

## Note

Running this project end to end requires the Thunderbird HPC log dataset, a separately running MongoDB Docker container, and a configured HDFS and Spark environment. Processing over 211 million log lines involves significant data processing, storage, and setup time. The dashboard can be run independently only if the required MongoDB collections and supporting data have already been populated (the steps for which will be provided later).

---

## Project Structure

```
HPC-log-analytics/
│
├── app/                        # Streamlit dashboard
│   ├── main.py                 # Entry-point: streamlit run app/main.py
│   └── pages/
│       ├── 1_Research_Findings.py
│       └── 1_Template_Decoder.py
│
├── pipeline/                   # PySpark ETL & analysis jobs
│   ├── process_full.py         # Stage 1 – parse raw logs → Parquet (HDFS)
│   ├── export_for_mongo.py     # Stage 2 – export Parquet → JSON for Mongo
│   ├── research_analyses.py    # Stage 3 – research aggregations → MongoDB
│   └── tail_analysis.py        # Diagnostic: inspect parse quality / tails
│
├── database/                   # MongoDB setup & management
│   ├── load_mongo.py           # Bulk-load JSON exports into MongoDB
│   ├── add_indexes.py          # Create compound indexes; benchmarks before/after
│   └── build_mongo_exports.py  # Build node_daily & template sample collections
│
├── glossary/                   # Plain-English log vocabulary
│   ├── data.py                 # Canonical label / program / template definitions
│   ├── template_glossary.py    # Pure-Python template decoder (used by dashboard)
│   ├── load_glossary.py        # Load glossary into MongoDB & tag templates
│   ├── verify_glossary.py      # Self-tests for glossary consistency
│   ├── discovery.py            # MongoDB queries for exploring new patterns
│   └── discovery.txt           # Saved discovery output
│
├── utils/                      # Shared utilities
│   └── masking.py              # PySpark UDF – mask IPs, MACs, hex values, etc.
│
├── scripts/                    # One-off maintenance & patch scripts
│   ├── apply_patches.py        # Apply named text patches to source files
│   ├── apply_patch2.py         # Secondary patch for research_analyses.py
│   ├── apply_rename.py         # Rename a page file with content substitution
│   ├── parse_test.py           # Quick single-week parse smoke-test
│   ├── program_level_gaps.py   # Report templates with only program-level coverage
│   └── verify_env.py           # Check Python deps + Mongo + Spark connectivity
│
├── docker/
│   └── docker-compose.yml      # MongoDB container definition
│
└── README.md
```

---

## Quick Start

### 1. Verify environment
```bash
python scripts/verify_env.py
```

### 2. Run the ETL pipeline
```bash
# Parse raw logs → Parquet
spark-submit pipeline/process_full.py

# Build extra Mongo-export collections
spark-submit pipeline/research_analyses.py

# Export to JSON
spark-submit pipeline/export_for_mongo.py
```

### 3. Load into MongoDB
```bash
python database/load_mongo.py
python database/add_indexes.py
python glossary/load_glossary.py
```

### 4. Launch the dashboard
```bash
streamlit run app/main.py
```

---

## Dataset

**Thunderbird** — 211,212,192 log lines from a Sandia National Laboratories HPC system.  
Source: [Loghub](https://github.com/logpai/loghub)

## Tech Stack

| Layer | Technology |
|---|---|
| Ingestion / ETL | Apache Spark (PySpark) |
| Storage | HDFS (Parquet) → MongoDB |
| Analysis | PySpark, Pandas |
| Dashboard | Streamlit, Plotly |
