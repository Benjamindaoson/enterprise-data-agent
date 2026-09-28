# Third-Party Notices

This repository temporarily integrates upstream open-source projects to accelerate the BA Agent product bootstrap.
The long-term plan is to replace upstream implementation details behind stable internal interfaces while preserving
required copyright and license notices for any code that remains derived from those projects.

## Pinned upstreams

| Component | Upstream | Pinned commit | License | Temporary role |
| --- | --- | --- | --- | --- |
| DeepAnalyze | https://github.com/ruc-datalab/DeepAnalyze | `f04a1c3b9ed3ae6c6efbb70e0cdcce4552c04ba4` | MIT | Code-analysis worker, multi-round code/execute runtime, optional 8B model/training reference |
| Data Formulator | https://github.com/microsoft/data-formulator | `5477f0e236426dc8f74a498ec400414fba7fbc0f` | MIT | Data Thread UX, visualization workflow, chart restyle/repair patterns, DuckDB/sandbox reference |
| WrenAI | https://github.com/Canner/WrenAI | `d26ab6af5e7e641f3e67f3ea9125486f5425fd30` | Mixed; core/sdk/skills Apache-2.0 | Semantic-layer and governed query reference; only Apache-2.0 code paths may be copied into first-party code |

The upstream repositories remain separate Git submodules. Their original license files and copyright notices remain
inside each submodule. Do not copy code from a path whose license is incompatible with the intended distribution.
