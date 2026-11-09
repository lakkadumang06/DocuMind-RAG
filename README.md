# DocuMind – RAG Knowledge Assistant

Ask questions about your company documents and get answers that cite the exact source
passage, or an honest "I don't know" when the documents don't contain the answer.

Work in progress, built in six phases. Phase 1 (backend skeleton, model layer, sample
documents) is complete. The full README with architecture, screenshots and eval results
arrives in Phase 6.

## Quickstart (Phase 1)

```bash
make install          # Python 3.12 venv + backend deps
make sample-docs      # generate 8 fictional documents into data/sample_docs
make qdrant           # start Qdrant via Docker
cp .env.example .env  # then set a provider and key, or keep Ollama for local use
make test
make check-embeddings
```

## License

MIT, see [LICENSE](LICENSE).
