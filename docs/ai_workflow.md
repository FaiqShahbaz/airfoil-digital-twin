# AI Workflow

This project uses multiple AI tools with strict edit authority.

- GPT-5.5/OpenCode Build edits files as the lead-coder.
- Qwen/OpenCode Review inspects local files with tool access and does not edit files.
- DeepSeek/Ollama reviews generated text bundles from `scripts/make_review_bundle.py` for reasoning-heavy review without tool access.
- Gemini CLI verifies literature, external references, and benchmark protocol claims before any comparison is documented.
- Continue.dev is autocomplete only.
- Only the lead-coder edits files; review agents must report findings without modifying the workspace.

Generate a CFD review bundle:

```bash
python scripts/make_review_bundle.py --kind cfd
```

Review the generated bundle with a non-tool Ollama model such as DeepSeek:

```bash
ollama run deepseek-r1:14b-32k < review_bundles/cfd_review_bundle.txt
```

Bundles for `gnn`, `benchmark`, and `dashboard` are placeholders until those phases are implemented.
