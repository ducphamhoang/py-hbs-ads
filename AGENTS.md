## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Use graphify as the first research tool when you need fast codebase understanding, architecture context, dependency/coupling insight, or cross-file/community discovery
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, rebuild graphify with `scripts/rebuild-graphify.sh`

Notes:
- Graphify is here to make codebase research easier: use it to understand major abstractions, bridges between features, and where logic should probably live before making broader changes
- Graphify is installed for the interpreter recorded in `.graphify_python` and may not be importable from the default `python3`
- In this repo, `.graphify_python` currently points to `/usr/bin/python3`
- `scripts/rebuild-graphify.sh` validates the interpreter can import `graphify` before running the rebuild
