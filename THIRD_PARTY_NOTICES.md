# Third-Party References and Notices

The BA Agent runtime and Retail Intelligence product in the current tree are
first-party implementations. No source tree from DeepAnalyze, Microsoft Data
Formulator, or WrenAI is vendored or imported by the product runtime.

During the bootstrap phase, the project evaluated these public repositories as
implementation references:

| Project | Repository | Evaluated commit | License at evaluation | What was studied |
| --- | --- | --- | --- | --- |
| DeepAnalyze | https://github.com/ruc-datalab/DeepAnalyze | `f04a1c3b9ed3ae6c6efbb70e0cdcce4552c04ba4` | MIT | autonomous code-analysis loop, training recipes |
| Microsoft Data Formulator | https://github.com/microsoft/data-formulator | `5477f0e236426dc8f74a498ec400414fba7fbc0f` | MIT | data-thread UX, visualization interaction, sandbox patterns |
| WrenAI | https://github.com/Canner/WrenAI | `d26ab6af5e7e641f3e67f3ea9125486f5425fd30` | mixed; core/sdk/skills Apache-2.0 at evaluation | semantic-model and governed-query concepts |

The current product code was reimplemented behind first-party contracts:

- versioned retail semantic package and business semantic resolver;
- LangGraph Supervisor + specialist workstreams;
- deterministic analytical skills and insight mining;
- first-party ECharts product UI, chart planner/restyler and executive report;
- first-party OpenAI-compatible AI-Coding worker and Docker isolation sandbox;
- independent RetailAnalystBench and real-data CI product proof.

An external DeepAnalyze API can still be configured as a compatibility fallback,
but its source is not part of this repository and the first-party code worker
takes precedence when configured.

The public Complete Journey data distribution used by the Retail Intelligence
benchmark is pinned separately and declared CC0 by the `completejourney`
package; its provenance and hashes are captured by the ingestion manifest.
