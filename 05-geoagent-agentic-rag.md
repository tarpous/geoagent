# Plan 05 — `geoagent`: a complete production swarm over geospatial data, with an automated eval factory

**Targets:** the entire general AI-engineering market (EU/US), Palantir FDSE, Z.ai (agentic engineering), Anthropic-shaped eval/red-teaming signal, local/sovereign-LLM shops (+ ties the whole portfolio together). Cloud API vendors (Mistral etc.) are hiring targets only if useful — **not** runtime dependencies.
**Effort:** ~5–7 weekends (vision tools are in-repo, not borrowed). **Compute:** **RTX 4080 Super (16 GB VRAM)** + local open-weight LLMs via a **custom llama.cpp server** (default) and **vLLM** (serving / ablation profile); ONNX Runtime for imagery models (CPU or GPU); no cloud LLM bills; no training required for the default path.

## Completeness contract (non-negotiable)
`geoagent` is a **standalone, shippable project**. Definition of done:

- Every tool in the tools layer has a **real implementation** in this repo (no `NotImplementedError`, no fixture-only “stub models,” no “wait for Plan-00/03”).
- Default demo path answers multi-tool geospatial questions with **live or cached-but-real** tool outputs via **all three product clients**: custom **TUI**, **web UI**, and **MCP** (PostGIS, STAC/NDVI, land-cover, detections, RAG citations, maps).
- **Default LLM path is fully local** on the 4080 Super — no Mistral/OpenAI/Anthropic API keys required to run the swarm, eval factory, or judge.
- **Only two inference backends are supported:** custom **llama.cpp** server and **vLLM**. No Ollama, no SGLang, no other wrappers in-tree.
- CI runs offline using **committed fixtures** (small OSM extract, cached Sentinel-2 tiles, PDFs, model weights or a download script with checksums) — fixtures speed CI; they do not replace models. CI may use smaller GGUF / HF IDs (e.g. Gemma 4 E4B / Qwen3.5-4B) than the demo profile.
- Eval factory + golden set (`golden@v1`) + swarm-vs-single ablation + REPORT.md + CI eval badge are published.
- **Contracts shipped:** `FinalAnswer`, structured-output policy, geo CRS/units tests, `NOTICE`/manifests, reproducibility pins, `make demo`.
- **M0 locks applied:** Pi SDK factory; demo roster Qwen3.5-9B / Gemma 4 E4B / Diffusion drafts; Attica + Thessaloniki.
- Plan-00 / Plan-03 are **optional later backends** behind the same tool schemas, never blockers.

## Why
The 2026 AI-engineer checklist is explicit: RAG + vector DBs, **multi-agent orchestration** (swarm / handoff patterns are now a production norm), MCP, structured outputs, guardrails, **eval literacy**, observability, FastAPI/Docker deployment — plus the sovereignty story: **agentic systems that run on open weights**. `geoagent` is the public, inspectable version: a **swarm of specialist analysts** over **maps, satellite imagery, and documents** — a Palantir-shaped product demo that also tells a coherent portfolio story (other plans can plug in later as upgraded weights).

## Product definition
"**A geospatial analyst swarm in a chat box**": ask *"How much tree cover was lost within 2 km of the new ring road since 2023?"* or *"Which municipalities in Attica have the most flood-prone agricultural land?"* → agents hand off across the team (data, imagery, documents, cartography), a critic checks the assembled evidence, and the user gets an answer with citations, numbers, and a generated map — with the full swarm trace visible.

### How people interact (all three required)
Same swarm core; three first-class clients. All call a shared **swarm session API** (ask question → stream events → `FinalAnswer` + trace + map artifact).

| Client | What it is | How you run it | Notes |
|---|---|---|---|
| **1. Custom TUI** | CLI-style chat in the terminal: type a question, see handoffs stream, get answer + citations + map path | `uv run geoagent tui` (or `geoagent-tui`) | Built in-repo (Textual / prompt_toolkit / rich). Optional mode: **custom Pi-embedded chat** (`@earendil-works/pi-coding-agent` `createAgentSession`) whose only “tools” are `ask_swarm` / `show_trace` hitting the same API — OpenClaw-style embed, not stock Pi coding agent |
| **2. Web UI** | Browser chat with SSE streaming + swarm trace panel + map preview | `docker compose up` → open UI; or FastAPI static/SPA under `api/ui/` | Primary demo GIF path for non-terminal reviewers |
| **3. MCP** | MCP server exposing **tools** and a **`ask_swarm` (or equivalent) tool** so external agents can either call tools directly or run the full swarm | `uv run geoagent mcp` / stdio or SSE transport | Cursor / Claude Desktop / other MCP hosts are clients — not design dependencies |

```
Human ──► TUI (CLI or Pi-custom) ──┐
Human ──► Web UI (SSE)           ──┼──► Swarm session API ──► LangGraph swarm ──► tools
Agent  ──► MCP (tools + ask_swarm)─┘
```

**Shared contract:** one `FinalAnswer` schema + event stream (`handoff`, `tool_call`, `tool_result`, `critic`, `done`) consumed by TUI, UI, and MCP alike. Do not fork business logic per client.

## Contracts & engineering standards (locked)

### FinalAnswer schema (single Pydantic contract)
Every successful or refused run ends as one validated `FinalAnswer` (module: `src/geoagent/schemas/answer.py`). Critic, TUI, web UI, MCP `ask_swarm`, and eval judges all consume **this type only** — no free-form “final message” bypass.

| Field | Type | Rules |
|---|---|---|
| `trace_id` | `str` (ULID/UUID) | Stable across SSE events; Langfuse root id may alias it |
| `status` | `answered \| refused \| degraded` | `degraded` = partial evidence / specialist failure still produced a best-effort answer |
| `answer_md` | `str` | User-facing markdown; empty iff `refused` |
| `numbers` | `list[Quantity]` | Each: `name`, `value: float`, `unit` (UCUM-ish: `m`, `km`, `m2`, `ha`, `percent`, `count`), `source_tool`, optional `ci` |
| `citations` | `list[Citation]` | `doc_id`, `chunk_id`, `span_start/end` or quote ≤300 chars, `uri`/`page` when known |
| `geometries` | `list[GeoRef]` | WGS84 lon/lat GeoJSON; optional `epsg_computed` noting projection used for meters |
| `map_artifact` | `Path \| None` | Repo-relative path to PNG/HTML from `make_map`; required when cartographer ran |
| `refusal` | `Refusal \| None` | `reason_code` (`unanswerable`, `out_of_aoi`, `unsafe`, `budget`, `tool_failure`) + `message` |
| `warnings` | `list[str]` | Unit mismatches fixed, low NDVI confidence, etc. |
| `model_roster` | `dict[str, str]` | role → model id@quant actually used |

Validation fails the turn (retry once via critic path, else `degraded`/`refused`) — clients never invent fields.

### Tool-calling & structured-output policy
Local ≤15B models fail open JSON often; treat structure as infrastructure.

- **Request shape:** every tool and every agent structured emit uses a **JSON Schema** (Pydantic → schema). Prefer backend native constraints: llama.cpp **grammar / JSON schema** mode; vLLM **guided decoding / structured outputs** when available for that model.
- **Parse path:** schema-validate → on failure, **one repair retry** with the validator error echoed; second failure → tool result `{ok: false, error: "schema_violation", detail}` (never crash the swarm).
- **Malformed / unknown tool names:** specialist sees error payload; after 2 consecutive schema violations on the same tool, hand off to `critic` or `intake` with `degraded` warning — do not infinite-loop.
- **Max tool calls per specialist:** pinned in `budget.py` (default 8); global step cap separate.
- **Handoffs:** typed `Handoff(to, reason, state_delta)` — not free text “please call geodata.”
- **Evals:** golden items assert schema-valid traces; “tool_call_parse_rate” is a published metric (target ≥95% on demo profile).

### Geo correctness rules (executable, not critic-only)
Documented in `docs/geo.md`; enforced in `tests/geo/` and tool wrappers:

| Rule | Implementation |
|---|---|
| **Storage CRS** | Persist/exchange geometries as **EPSG:4326 (WGS84)** lon/lat |
| **Metric work** | Buffers, lengths, areas computed in a suitable projected CRS (default **EPSG:2100** for Greece demo AOIs, or local UTM); results converted back to WGS84 for storage/maps |
| **Units** | Tools return explicit units; `Quantity.unit` must match tool contract; critic + unit tests reject silent meter/degree mixups |
| **Geometry sane** | Reject empty, NaN, non-finite coords; max AOI area pin; self-intersection check where cheap; bbox must intersect demo regions unless user opts out |
| **Time** | Imagery/stats declare timezone (UTC) and date range inclusive bounds |

“Geometry sane?” in the critic is a **call to these validators**, not prose vibes.

### Licensing & provenance (`NOTICE` + manifests)
Ship `NOTICE` and machine-readable manifests so the portfolio is redistribute-safe:

- **OSM:** ODbL — attribution in UI/TUI footer + README; `data/osm/ATTRIBUTION`
- **Corpus PDFs:** each row in `data/corpus_manifest.csv` has `license`, `source_url`, `retrieval_date`
- **LLMs / GGUF / HF:** `models/llm/LICENSE-MAP.md` (Gemma / Qwen / Diffusion terms)
- **Vision ONNX:** `models/landcover|detect/LICENSE`
- **Third-party code:** root `NOTICE` aggregates

CI fails if a new corpus file lacks manifest license fields.

### Reproducibility pins
| Pin | Where | Default |
|---|---|---|
| Per-role `temperature`, `seed`, `top_p` | `configs/models.yaml` | `temperature: 0.1` agents; `0.0` judge; fixed `seed` for CI |
| `n_ctx` / `max_model_len` | same | demo 16k–32k as VRAM allows; CI smaller |
| Golden set version | `evals/golden/VERSION` | `golden@v1` semver-ish; factory bumps on taxonomy change |
| Eval artifact hashes | `evals/results/*.sha256` | CI compares subset scores + hash of frozen fixtures |
| Prompt versions | `prompts/*.md` + git SHA in `FinalAnswer.model_roster` / Langfuse metadata | Prompt edit without version bump fails review checklist |

Offline CI uses recorded fixtures + seeds so flaky GPU variance doesn’t false-fail the gate (full GPU job is nightly/manual).

### Hero demo command
Reviewers must not hand-compose the stack:

```bash
make demo
# alias: uv run geoagent demo
```

**Does:** ensure compose deps (Postgres) up → hit local llama.cpp → run hero question  
*“How much tree cover was lost within 2 km of the new ring road since 2023?”* (Attica AOI fixtures) → print `FinalAnswer` summary + write `artifacts/demo/{trace_id}/` (map PNG, trace JSON, answer.md) → exit nonzero on schema/tool failure.

Documented in README as the 60-second path; GIF recorded from `make demo` + TUI/web.

### M0 decisions (locked — no “pick later”)
| Decision | Lock |
|---|---|
| Eval factory harness | **Pi SDK** (`@earendil-works/pi-coding-agent`) only — OpenCode not in scope |
| Product terminal chat | **Custom Python TUI** required; **Pi-custom chat client** (`clients/pi_chat`) also required as second terminal entry (both call swarm API) |
| Default role map (demo profile) | see table below — single roster, not a menu |
| Inference backends | llama.cpp default; vLLM serving/ablation only |
| Demo AOIs | **Attica + Thessaloniki** |

**Locked default role map (`configs/models.yaml` → `profile: demo`):**

| Role | Model | Quant (llama.cpp / vLLM) |
|---|---|---|
| `intake`, `critic`, single-agent baseline | **Qwen3.5-9B** | Q4_K_M / AWQ-4 |
| Specialists (shared) | **Gemma 4 E4B** | Q5_K_M / AWQ-4 or FP16 |
| Eval-factory author | **Qwen3.5-9B** | Q4_K_M / AWQ-4 |
| Eval-factory verifier + LLM judge | **Gemma 4 E4B** (cross-family vs Qwen swarm/author) | Q5_K_M / AWQ-4 |
| Factory draft stems / captions | **Gemma Diffusion** (≤15B-class) | Q4_K_M via llama.cpp; skip if unavailable → Gemma 4 E4B |
| Embeddings / rerank | BGE-M3 + bge-reranker-v2-m3 | FP16/INT8 (CPU OK) |

Ablations may swap Qwen↔Gemma for specialists in REPORT; **demo and CI default roster stays as above.**

## Local LLM strategy (4080 Super — primary)
**No cloud chat APIs in the default stack.** All agents, the eval factory, and the LLM judge talk to a local OpenAI-compatible endpoint served by **exactly one** of:

| Backend | Role in geoagent | Weights | When |
|---|---|---|---|
| **Custom llama.cpp server** (`llama-server` / in-repo launch scripts) | **Default demo + day-to-day** | GGUF on disk (`models/llm/*.gguf` or download script + SHA256) | Interactive swarm, single-user latency, easy quant swaps, Gemma Diffusion if GGUF/runtime supports it |
| **vLLM** | **Serving / throughput profile** | HF safetensors IDs pinned in config | Concurrent evals, OpenAI-compatible production-shaped serving, latency/tok-s ablation vs llama.cpp |

Both expose OpenAI-compatible HTTP. `src/geoagent/llm/provider.py` is a thin client; `LLM_BACKEND=llamacpp|vllm` + `LLM_BASE_URL` switch profiles. **Out of scope:** Ollama, SGLang, cloud gateways.

### In-repo serving glue (required)
```
deploy/llm/
  llamacpp/   # scripts to build/run llama-server with CUDA on the 4080 Super
  vllm/       # scripts to launch vLLM OpenAI API server with pinned HF IDs
configs/
  models.yaml # per-role ids, **quant**, ctx, temp; profiles: llamacpp-demo | vllm-serving | ci
```

### Hardware budget (16 GB VRAM) — hard caps
- **Max ~15B parameters** for any chat / agent / judge / factory model. **No 26B/27B+ pins** — too tight on a 4080 Super once context, KV cache, and ONNX vision share the card.
- Prefer **one resident LLM** (or one heavy + one tiny) at a time; specialists share the mid-tier checkpoint.
- Leave headroom for embeddings/rerank and ONNX landcover/detect (or run those on CPU if VRAM is tight).
- Document exact GGUF/HF paths, **quantization**, `n_ctx` / `max_model_len` in `configs/models.yaml`.

### Quantization (required pins — not optional footnotes)
Every role in `configs/models.yaml` must declare backend + quant. Defaults for the 4080 Super:

| Backend | Format | Default quant | When to use something else |
|---|---|---|---|
| **llama.cpp** | GGUF | **Q4_K_M** for 9–15B; **Q5_K_M** for ≤8B if VRAM allows; **Q4_0 / Q3_K_M** only for CI tiny tags | Q5/Q6 for quality sweeps in REPORT; Q8 only for ≤4B smoke tests |
| **vLLM** | HF safetensors | **AWQ 4-bit** (preferred) or **weight-only INT4** where AWQ weights exist; else **FP8** if card/stack supports it cleanly | BF16/FP16 only for ≤4B CI; never default BF16 for 12–15B on 16 GB |
| **Embeddings / rerank** | ONNX or sentence-transformers | FP16 or INT8 | Keep small; prefer CPU if LLM is occupying GPU |
| **Vision ONNX** (`landcover`, `detect`) | ONNX | FP32 or FP16 | CPU default; GPU optional — must not silently OOM the LLM |

Checksum scripts verify both the weight file and the declared quant tag (e.g. `*-Q4_K_M.gguf`, `*-AWQ`). README quickstart lists the exact filenames.

### Role → model map
**Defaults are locked in “M0 decisions” above.** Ablation-only swaps go under `profile: ablation-*` in `configs/models.yaml`, never silently replace `demo`. Hard cap remains **≤15B** and pinned quants (Q4_K_M / Q5_K_M / AWQ-4).

**Policy:** only **2026 open models ≤ ~15B**. Reject 26B MoE / 27B dense pins. No cloud chat APIs. Backend swap is config-only (`llamacpp` \| `vllm`).

### Swarm concurrency note
Serialize LLM calls through one GPU server so VRAM stays predictable; optional dual-load only after measurement. Budgets = **token + wall-clock + VRAM**, not €. REPORT.md includes a **llama.cpp vs vLLM** latency/tok-s table on the same model pair where both backends support it.

## Scope
1. **Agent core — a LangGraph swarm**, with a single-agent baseline for an honest ablation:
   - **Specialist agents**, each with a narrow system prompt, its own tool subset, and scoped context:
     - `intake` (thin) — classifies the question, seeds `TeamState`, hands off to the first specialist;
     - `geodata` — spatial SQL over PostGIS/OSM, geocoding;
     - `earth-obs` — STAC imagery search/compositing, `landcover_classify`, `detect_objects`, raster stats;
     - `librarian` — hybrid RAG over the document corpus, returns citation-grounded evidence packets;
     - `cartographer` — turns team outputs into maps/figures (`make_map`);
     - `critic` — verifies the draft answer against collected evidence (numbers match sources? citations resolve? geometry sane? units correct?) and can send work back **once** (bounded reflection).
   - **Primary — swarm** (langgraph-swarm): no manager; agents hand off directly with handoff tools. Guards: recursion/step limits, per-request token & latency budgets, timeout per specialist, structured `TeamState` (Pydantic).
   - **Baseline — single agent with all tools** — ablation + CI latency check only; not the default product path.
   - **Out of scope:** supervisor architecture (swarm vs single-agent is the thesis).
   - `docs/architecture.md` explains when swarm beats single-agent vs when it doesn't — backed by *measured numbers* on **local** models.

2. **Tools layer** (each independently unit-tested, JSON-schema'd, **complete in-repo**):
   - `spatial_sql`: parameterized PostGIS queries over OSM data (pinned ingestion: Geofabrik Greece extract → clip to the two demo regions → `osm2pgsql` flex output, scripted in `data/osm/`; safety: query allowlist templates, not raw SQL from the model).
   - `stac_imagery`: search/fetch Sentinel-2 COGs (Element84 Earth Search API), compute NDVI/cloud-masked composites via `stackstac`/`rasterio`; demo AOIs cache composited tiles for latency, with a live-fetch path for non-cached AOIs.
   - `landcover_classify` (**real, in-repo**): ONNX land-cover inference over fetched/cached tiles (CPU default; GPU optional).
     - Default backend: small pretrained land-cover ONNX (or export script + pinned weights with SHA256 in `models/landcover/`) → per-pixel class maps + area stats (tree/crop/urban/water/bare — label set documented in README).
     - Implementation: `src/geoagent/tools/landcover.py` + `models/landcover/`; tests assert non-empty class histogram on fixture tiles.
     - Optional later: Plan-00 TerraTorch/GFM weights behind the same schema — **not required to ship**.
   - `detect_objects` (**real, in-repo**): ONNX object detector on imagery tiles.
     - Default backend: small YOLO-class ONNX in `models/detect/` with pinned checksum; boxes + labels + counts (building, vehicle, … — documented allowlist).
     - Implementation: `src/geoagent/tools/detect.py`; tests assert detections on a fixture tile with known positives.
     - Optional later: Plan-03 overwatch weights — **not required to ship**.
   - `geocode` (Nominatim, with rate-limit + cache), `make_map` (folium + static PNG for answers).
   - `docs_search`: the RAG pipeline (below).

3. **RAG pipeline**: corpus = EU/Greek environmental & planning documents (public PDFs; pinned starter set with `data/corpus_manifest.csv`) → parsing (`docling`) → **hybrid retrieval in Postgres: FTS + `pgvector`, RRF, then local cross-encoder rerank**. One database for documents, vectors, and PostGIS. Span-level citations. Chunking ablation: fixed vs structural.

4. **Product clients — TUI + Web UI + MCP (all required)**:
   - **Swarm session API** (FastAPI): `POST /v1/chat` (SSE) and/or in-process Python API used by TUI; returns streamed events + final structured answer.
   - **Custom TUI (required):** CLI chat — prompt loop, streaming handoff trace, render citations/map path, slash commands (`/trace`, `/map`, `/backend`). Implementation: Python TUI library **and/or** custom **Pi SDK** session that wraps `ask_swarm` (not a generic coding agent). Smoke-tested in CI with a scripted question.
   - **Web UI (required):** minimal SPA/htmx page — chat, live trace, map image/iframe. Served by FastAPI.
   - **MCP server (required):** expose all geospatial tools **plus** `ask_swarm` so hosts can run the full team or bypass it for single-tool calls. Document Cursor + one other host; Desktop GIF optional.
   - **A2A:** out of scope.

5. **Eval harness + eval factory** — `geoagent-evals` + `evals/factory/`:
   - **Golden dataset is machine-authored** by an independent factory (not the runtime swarm), using **local** author/verifier models (cross-family) via llama.cpp or vLLM.
   - Verifier rejects bad items → `evals/golden/*.jsonl`. Imagery items must expect **real** vision-tool traces.
   - Human role: ~20–30 audited items for κ.
   - Retrieval + swarm metrics + swarm-vs-single ablation; report tok/s, latency, VRAM — not API €. Include **backend ablation** (llama.cpp vs vLLM) on a fixed model pair.
   - CI: small GGUF via llama.cpp (or skipped GPU profile documented); fail-on-regression for prompt changes.
   - **Factory runtime:** **Pi SDK locked** (see M0). Separate from product Pi chat — factory authors evals; product Pi only calls `ask_swarm`.
   - Golden set tagged **`golden@v1`** (+ VERSION file); CI checks fixture hashes and `tool_call_parse_rate`.

6. **Safety/robustness**: injection tests (PDFs/OSM names), inter-agent propagation tests, PII redaction, per-specialist tool allowlists, chaos tests. Factory-generated injection cases.

7. **Serving & ops**: FastAPI (SSE API + web UI) + TUI entrypoint + MCP entrypoint; **`llm/provider.py` = OpenAI-compatible client only** (`LLM_BACKEND=llamacpp|vllm`); `configs/models.yaml` per-role pins; Langfuse self-hosted; Docker Compose (app + Postgres/PostGIS/pgvector + Langfuse). **llama.cpp server and vLLM run on the host GPU** (compose → `host.docker.internal:<port>`). Launch scripts under `deploy/llm/`. GitHub Actions: tests + eval gate + weight checksums + client smoke (TUI scripted, UI HTTP, MCP tool list).

8. **Writeup** `REPORT.md`: why swarm; retrieval ablation; eval-factory methodology; judge calibration; red-team; **≤15B roster + quants + seeds**; **llama.cpp vs vLLM**; **FinalAnswer / tool_call_parse_rate / geo rules**; **TUI + web UI + MCP**; licensing/NOTICE notes; vision limits.

**Non-goals:** Ollama, SGLang, cloud LLM APIs as default, fine-tuning custom GFMs, multi-tenant auth, mobile app, supervisor architecture, A2A, hand-authoring the full golden set, stubbing any production tool. (Custom TUI + web UI + MCP are **in** scope — not non-goals.)

## Repo structure
```
geoagent/
├── src/geoagent/
│   ├── swarm/ (graph.py, state.py, handoffs.py, budget.py, intake.py,
│   │          specialists/ (geodata.py, earth_obs.py, librarian.py, cartographer.py, critic.py))
│   ├── baseline/ (single_agent.py)
│   ├── tools/ (spatial_sql.py, stac_imagery.py, landcover.py, detect.py, geocode.py, mapping.py)
│   ├── rag/ (ingest.py, chunkers.py, hybrid_retriever.py, reranker.py, citations.py)
│   ├── schemas/ (answer.py, handoff.py, events.py, quantity.py)  # FinalAnswer + stream events
│   ├── geo/ (crs.py, units.py, validate.py)       # WGS84 store, metric project, sane geometry
│   ├── llm/ (provider.py, structured.py)          # OpenAI-compat + schema/grammar retries
│   ├── mcp_server/ (server.py, tool_schemas.py)   # tools + ask_swarm
│   ├── tui/ (app.py, render.py)                   # CLI chat
│   ├── clients/pi_chat/                           # custom Pi SDK → ask_swarm only
│   └── api/ (app.py, ui/)                         # SSE API + web UI
├── configs/
│   └── models.yaml                        # locked demo roster + quants + seeds/temps
├── models/
│   ├── llm/          # GGUF + LICENSE-MAP.md + checksums
│   ├── landcover/    # *.onnx + LICENSE + checksums
│   └── detect/       # *.onnx + LICENSE + checksums
├── deploy/
│   ├── llm/
│   │   ├── llamacpp/
│   │   └── vllm/
│   ├── docker-compose.yml
│   └── .github/workflows/
├── evals/
│   ├── factory/
│   ├── golden/ (VERSION → golden@v1, *.jsonl)
│   ├── judge.py, calibrate.py, retrieval_evals.py, agent_evals.py, run.py, results/
├── data/ (corpus_manifest.csv, osm/ATTRIBUTION, download scripts, fixtures/)
├── artifacts/demo/    # make demo outputs (gitignored except .gitkeep)
├── tests/ (incl. tests/geo/)
├── Makefile           # demo, tui, mcp, evals, checksums
├── NOTICE             # aggregated third-party + data licenses
├── AGENTS.md          # short coding-agent entrypoint → points at this plan’s locks
├── REPORT.md  README.md  docs/architecture.md  docs/geo.md
├── prompts/*.md
```

## Milestones
| M | Deliverable | Done when |
|---|---|---|
| 0 | Contracts + factory + backends | `FinalAnswer` + structured-output path green; **Pi SDK** factory emits 10 items; llama.cpp + vLLM scripts run; **locked demo roster** in `models.yaml`; `NOTICE` stub + corpus license columns; `make demo` dry-run against fixtures |
| 1 | RAG pipeline + retrieval evals | hybrid+rerank beats dense-only on recall@5; table published |
| 2 | **Complete tools** + PostGIS/OSM + geo tests | every tool real; `tests/geo` CRS/units/sane geometry green; single-tool Qs answerable |
| 3 | Swarm + handoff eval (local) | multi-tool incl. imagery; handoff correctness; schema-valid traces; `tool_call_parse_rate` logged |
| 4 | Golden set + judge calibration | `golden@v1` ~80–120 Qs; audit ~20–30; κ; artifact hashes in CI |
| 5 | Single-agent + ablations | swarm-vs-single frontier; llama.cpp vs vLLM table |
| 6 | **TUI + Web UI + MCP** + deploy | both terminal clients + web UI + MCP; **`make demo`** hero path green; CI client smokes |
| 7 | Red-team + report | suites passing; REPORT includes contracts, quant, licenses, clients; badge green |

## Tech stack (pinned)
Python 3.12, **LangGraph + langgraph-swarm**, Pydantic v2, **PostgreSQL 16 + PostGIS + pgvector + FTS**, BGE-M3 + bge-reranker-v2 (Qwen3-Reranker-0.6B ablation), docling, osm2pgsql, pystac-client + stackstac + rasterio, **onnxruntime**, folium, FastAPI (+ SSE web UI), **custom TUI** (Textual/prompt_toolkit/rich; optional **Pi SDK** chat client), **MCP Python SDK**, Langfuse, Docker, pytest, uv, ruff. **LLMs: local only, ≤15B** — **llama.cpp (CUDA, default; GGUF Q4_K_M / Q5_K_M)** and **vLLM (AWQ-4 / FP8)** with Gemma 4 / Qwen3.5 / Gemma Diffusion. **Eval factory:** Pi SDK → local endpoint (separate from product Pi chat).

## Risks & mitigations
- **16 GB VRAM contention** → hard **≤15B** cap; Q4_K_M / AWQ-4 defaults; serialize roles; specialists on E4B/4B; CI uses tiny GGUFs (Q3/Q4).
- **Local tool-calling quality** → JSON-schema/grammar + one repair retry; publish `tool_call_parse_rate`; golden traces must be schema-valid.
- **Pi churn** → factory and product Pi-chat only speak stable APIs (`golden/*.jsonl` schema; `ask_swarm` / `FinalAnswer`).
- **Dual weight formats + quants** → GGUF Q4_K_M (llama.cpp) + HF AWQ-4 (vLLM) documented together; checksums fail if quant tag drifts.
- **vLLM model-support lag for brand-new 2026 tags** → llama.cpp/GGUF is the compatibility fallback; vLLM ablation uses the newest mutually supported **≤15B** pair at the pinned quant.
- **Gemma Diffusion** → preferred for high-throughput factory drafting; llama.cpp-only if vLLM lacks support; never substitute a 26B+ autoregressive model — do not block M0–M6 if diffusion GGUF is late (fall back to Gemma 4 E4B/12B Q4).
- **Eval dataset quality** → factory + verifier (cross-family) + human audit slice.
- **Swarm loses to single-agent** → report frontier honestly.
- **STAC latency** → cache Attica/Thessaloniki composites.
- **Vision model ceiling** → document classes/failures; Plan-00/03 optional later.
- **Pi / OpenCode churn** → `golden/*.jsonl` schema is the contract.

## User actions needed
- Build/run **llama.cpp server** (CUDA) via `deploy/llm/llamacpp`; optionally **vLLM** for serving ablation.
- Download pinned GGUF/HF weights for the **locked demo roster** (Qwen3.5-9B, Gemma 4 E4B, optional Gemma Diffusion).
- Langfuse via compose.
- Confirm demo AOIs **Attica + Thessaloniki** (already locked; override only if you must).
- **~1–2 hours** spot-checking the audit slice for κ.
- Run `make demo` before recording GIFs.

## Build notes for coding agents
*(Cursor, Codex, OpenCode, Claude Code, Pi, or a custom agent — same rules. Prefer reading this section + `AGENTS.md` / repo root before coding.)*

### Non-negotiables
- **Local-first backends only:** `LLM_BACKEND=llamacpp` (default) or `vllm`; `LLM_BASE_URL` → host GPU server (e.g. `http://127.0.0.1:8080/v1` for llama-server). Do **not** add Ollama, SGLang, or cloud chat API keys to quickstart.
- **Standalone vision tools:** implement `landcover_classify` and `detect_objects` fully in-repo; never block on Plan-00/03; no stub tools in the default path.
- **Clients are all required:** custom TUI + web UI + MCP (`ask_swarm` + tools) share one swarm session API and `FinalAnswer` — do not fork business logic per client.
- **M0 locks are closed:** Pi SDK for eval factory; demo roster Qwen3.5-9B / Gemma 4 E4B / Diffusion drafts; AOIs Attica + Thessaloniki. Document deviations in REPORT only.
- **≤15B + pinned quants:** do not introduce 26B/27B+ models; declare quant in `configs/models.yaml` (Q4_K_M / Q5_K_M / AWQ-4).

### Implementation order
1. Schemas + structured-output retries (`FinalAnswer`, tool JSON schema/grammar) **before** multi-agent demos.
2. RAG + retrieval evals (M1) before swarm polish.
3. Real tools + `tests/geo` (CRS/units) before claiming M2 done.
4. Swarm + evals, then TUI / web UI / MCP, then `make demo` green.
5. M2 = **zero stub tools**. `make demo` is the reviewer entrypoint — keep it one command.

### Environment
- Windows 11 + Docker Desktop (WSL2): Postgres/PostGIS/pgvector/Langfuse/osm2pgsql via compose.
- **GPU:** llama.cpp and vLLM run on the **host** 4080 Super; compose uses `host.docker.internal`. Do not trap the LLM in a CPU-only container by default.
- Python 3.12 + `uv`; Node/TS only where needed (Pi factory / Pi chat client).
- **Fixtures ≠ stubs:** committed tiles/PDFs/OSM extracts for offline CI; models still run real ONNX / GGUF inference on those fixtures.

### Repo conventions for agents
- Put durable agent instructions in **`AGENTS.md`** (and optional `.cursor/rules` / OpenCode `AGENTS.md` / Codex guidance) — keep them short; this plan is source of truth for scope.
- Prompts live in `prompts/*.md` only; no buried system strings in random files.
- Eval factory must **not** import `src/geoagent/swarm`. Product TUI / Pi-chat **may** call the swarm session API.
- Prefer small diffs; do not expand scope (no supervisor, A2A, K8s, cloud LLMs, OpenCode-as-factory).
- Before finishing a milestone: run the relevant tests / `make demo` dry path; update NOTICE/manifests if adding data or weights.

### Demo & proof
- Hero path: Attica ring-road tree-cover question → map + trace under `artifacts/demo/{trace_id}/`.
- GIF: `make demo` + TUI + web UI (+ MCP clip) on the **same** question.
- Critic does not re-implement geo math — it calls `geo` validators.

## CV bullet draft
> Built and deployed a complete open-source geospatial analyst **swarm** running **fully locally on consumer GPU** (LangGraph handoffs, PostGIS/pgvector, STAC imagery, in-repo ONNX land-cover + object detection; **custom CLI TUI**, **web UI**, and **MCP** — including `ask_swarm` — over one session API; **≤15B Gemma 4 / Qwen3.5 / Gemma Diffusion** with pinned **Q4_K_M / AWQ-4** via **llama.cpp** and **vLLM** on RTX 4080 Super): hybrid RAG with local reranking and span-level citations; **automated eval factory** (Pi SDK author/verifier, cross-family judge) producing an 80–120 question golden set with a human audit slice (κ reported); handoff-correctness metrics plus swarm-vs-single and **llama.cpp-vs-vLLM** ablations gating CI; prompt-injection and inter-agent propagation red-teaming; Langfuse tracing; Docker + host-GPU deployment with zero cloud LLM dependency.
