# Architecture

## True swarm model (locked)

Geoagent implements a **peer handoff swarm** in the OpenAI Swarm / langgraph-swarm sense:

1. Each specialist owns domain tools **and** `transfer_to_<peer>` handoff tools.
2. Control moves only when a specialist **invokes** one or more transfer tools.
3. Invoking multiple transfer tools spawns a **parallel wave**; peers run concurrently, results merge, then a **join** activates the next specialist.
4. There is **no supervisor / commander** that dispatches work.

CPU-only mode uses a deterministic per-peer chooser over the same transfer-tool catalog. With local LLMs later, specialists keep the catalog and choose tools via structured outputs.

## Not Kimi Agent Swarm

| Pattern | Geoagent |
| --- | --- |
| Kimi commander + mass anonymous sub-agent spawn | **Out of scope** (hierarchical / supervisor-like) |
| Fixed `A→B→C` pipeline | Rejected |
| Peer `transfer_to_*` + optional parallel join | **This project** |

## Graph engineering

Compile-time topology (`topology.py`) defines allowed transfer destinations. Runtime peers may only invoke tools for those edges. After `geodata`, independent peers (`earth-obs`, `librarian`) are a parallel join phase when both are required.

```text
intake --transfer_to_geodata--> geodata
geodata --transfer_to_earth_obs + transfer_to_librarian--> (parallel wave)
        --swarm_join--> cartographer --transfer_to_critic--> critic
```

## Runtimes

- `GEOAGENT_SWARM_RUNTIME=loop` (default): swarm loop with `ThreadPoolExecutor` waves
- `GEOAGENT_SWARM_RUNTIME=langgraph`: same specialists/tools, LangGraph routing on `active_agent`

## Bounded reflection

The critic may invoke `transfer_to_*` **once** (`budgets.max_reflections`) when evidence gaps remain (missing citations, quantities, geometry, or map/draft). After that budget is spent it must emit `FinalAnswer`.

## When swarm vs single-agent

See `REPORT.md` and `evals/results/ablation_swarm_vs_single.json`.
