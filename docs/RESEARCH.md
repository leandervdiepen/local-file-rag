# Research log

Researched on 2026-09-07.
Each finding names what it changed in the plan.

## Retrieval models

colpali-engine is deprecated in favor of Sentence Transformers v6, which ships `MultiVectorEncoder` with `encode_query`, `encode_document`, MaxSim `similarity`, and built-in `HierarchicalTokenPooling`.
Confirmed loading: `vidore/colqwen2-v1.0`, `vidore/colqwen2.5-v0.2`, `vidore/colpali-v1.3`, `vidore/colqwen-omni-v0.1`.
Changed: D04, the sidecar depends on `sentence-transformers` rather than `colpali-engine`.

`vidore/colqwen2-v1.0` is Qwen2-VL-2B with LoRA adapters, 128-dim vectors, at most 768 patches per page, about 755 document vectors per page and about 25 query vectors.
Backbone Apache 2.0, adapters MIT.
Changed: D05.

ColModernVBERT is a 250M encoder from Illuin under MIT that matches models ten times larger on ViDoRe and is fast on CPU.
Its model card says interpretability functions raise `NotImplementedError` because the Idefics3-style split-image token grid is not rectangular.
Changed: rejected for v1 because the heatmap is the hero. Parked as a fast mode.

Token pooling at factor 3 keeps about 97.8 percent of retrieval quality with a third of the vectors.
Changed: D09.

No maintained MLX port of ColQwen or ColPali was found.
colpali-engine notes torch 2.6.0 errors on MPS fixed by 2.5.1, so pin torch carefully and test on day 0.
Changed: D06, and the day 0 spike.

The Visual RAG Toolkit paper (SIGIR 2026 demo) describes training-free spatial pooling to dozens of vectors per page plus exact MaxSim reranking as a second stage, at roughly four times the throughput with recall held.
Changed: confirms the two-stage design. Their code is a reference if pooled candidate generation is needed later.

ViDoRe V3 is the current benchmark, about 26,000 pages across ten domains and six languages.
Top late-interaction models sit below 65 percent nDCG@10 on it.
Changed: the golden set uses a small public subset if one is easy to fetch, otherwise the demo corpus. Publish the corpus with the number.

## Storage

LanceDB stores multivectors as `list<list<float32 or float16, dim>>`, indexes them with `create_index(metric="cosine")`, and searches with a matrix of query vectors using MaxSim.
Cosine is the only supported metric for multivector.
Full-text search and hybrid search with an RRF reranker exist for single-vector columns.
Whether hybrid search accepts multivector columns is undocumented.
Changed: D07, D08, and stage 2 scores MaxSim in numpy over candidates so nothing depends on the undocumented combination.

## PDF, OCR, metadata

PyMuPDF is AGPL with a paid commercial license.
pypdfium2 5.13 is BSD-3 plus Apache-2.0, renders with `page.render(scale=...)`, extracts text, and has a macOS arm64 wheel.
Changed: D10.

Apple Vision `VNRecognizeTextRequest` is reachable from Python through `pyobjc-framework-Vision`.
`ocrmac` is a thin wrapper that shows the calls.
Changed: D11.

Spotlight metadata such as last-used date is available through `mdls` or the CoreServices `MDItem` API through pyobjc.
Changed: FR-2 records last-used for the recency boost and idle pre-embedding.

## Competitors

Spotlight in macOS 26 got a new indexer with semantic search, quick keys, clipboard, actions and inline Apple Intelligence.
It does not explain matches and does not answer questions.

Fenn: local, 50 plus file types, chat with citations, 9 USD per month or 249 USD lifetime, closed source.

omni-macos by Han Xiao: Apache 2.0 code, `jina-embeddings-v5-omni` ported to MLX Swift, text, images, audio, video and Photos in one vector space, embeddings in SQLite, no question answering, no explanation of matches, weights CC-BY-NC.

Dhito, LocalSpider, Index: closed, search or basic Q&A, no explanation.

Changed: positioning table in PRD.md. The wedge is explainable page-level retrieval, lazy indexing with a visible index, cited answers, and built-in eval, all open source.

## Cloud embedding alternatives

Cohere embed v4 and Voyage multimodal-3.5 embed page images into a single vector through an API.
Neither produces patch-level maps.
Changed: not used in v1. Documented as the hosted fallback for a team version.

## Answer generation

Anthropic Python SDK: images go in as base64 `image` blocks before the text block.
Stream with `client.messages.stream` and read `text_stream`.
Default model per the Claude API skill is `claude-opus-5` with adaptive thinking and the server-side fallback option for Opus 5.
Verify the beta header string against the skill at implementation time.
Changed: D14 and the answer pipeline in ARCHITECTURE.md.

## Packaging

PyInstaller onedir plus electron-builder `extraResources` remains the working pattern for a Python sidecar.
Notarization uses `xcrun notarytool` with an App Store Connect API key and requires every bundled binary signed and hardened runtime entitlements.
Changed: D18. Notarization is optional for v1.

electron-vite v3 with React 19, Tailwind v4 and shadcn/ui is the current template stack, several maintained starters exist.
Changed: D01.

## Sources

- [colpali-engine on GitHub](https://github.com/illuin-tech/colpali)
- [Multi-vector encoders in Sentence Transformers](https://huggingface.co/blog/multi-vector-encoder)
- [vidore/colqwen2-v1.0](https://huggingface.co/vidore/colqwen2-v1.0)
- [ModernVBERT/colmodernvbert](https://huggingface.co/ModernVBERT/colmodernvbert)
- [ModernVBERT paper](https://arxiv.org/pdf/2510.01149)
- [Visual RAG Toolkit](https://arxiv.org/pdf/2602.12510)
- [ViDoRe V3](https://arxiv.org/abs/2601.08620)
- [ViDoRe V3 leaderboard](https://mteb-leaderboard.hf.space/benchmark/ViDoRe(v3))
- [Token pooling in colpali-engine](https://pypi.org/project/colpali-engine/0.3.9/)
- [Hierarchical patch compression for ColPali](https://arxiv.org/abs/2506.21601)
- [LanceDB multivector search](https://docs.lancedb.com/search/multivector-search)
- [LanceDB hybrid search](https://docs.lancedb.com/search/hybrid-search)
- [LanceDB on late interaction](https://www.lancedb.com/blog/late-interaction-efficient-multi-modal-retrievers-need-more-than-just-a-vector-index)
- [pypdfium2](https://pypi.org/project/pypdfium2/)
- [Python PDF library comparison](https://www.nutrient.io/blog/best-python-pdf-libraries/)
- [ocrmac](https://github.com/straussmaximilian/ocrmac)
- [Vision framework via PyObjC](https://yasoob.me/posts/how-to-use-vision-framework-via-pyobjc/)
- [Spotlight in macOS Tahoe](https://www.macrumors.com/how-to/do-more-with-spotlight-in-macos-tahoe/)
- [Fenn](https://www.usefenn.com/)
- [omni-macos](https://github.com/hanxiao/omni-macos)
- [Dhito](https://dhito.io/)
- [LocalSpider](https://localspider.com/)
- [Cohere embed v4](https://bestofai.io/models/cohere-embed-v4/)
- [Embedding model comparison 2026](https://www.buildmvpfast.com/blog/best-embedding-model-comparison-voyage-openai-cohere-2026)
- [Bundling Python inside Electron](https://til.simonwillison.net/electron/python-inside-electron)
- [electron-builder notarization](https://www.electron.build/docs/features/code-signing/notarization/)
- [Notarizing Electron apps in 2026](https://www.forasoft.com/blog/article/the-pain-of-publishing-electron-apps-on-macos-303)
- [Vite Electron template](https://github.com/GeorgiMY/Vite-Electron-Template)
- [MLX developer guide 2026](https://www.digitalapplied.com/blog/apple-mlx-framework-local-ai-developers-2026-guide)
