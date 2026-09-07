# Embedding strategy: text embedders alongside ColQwen2

Researched 2026-09-07 against the locked D05/D09/D33/D34 retrieval design.
MTEB numbers below are self-reported by model authors on different task subsets and dates.
The leaderboard moves monthly, so treat every score as a snapshot, not a ranking that holds next quarter.

## 1. Is a text embedder a substitute for ColQwen2 here

No, and not by degree, by category.
A text embedder takes text as input.
It never sees a pixel, so it cannot produce the patch-level similarity map the heatmap renders from, regardless of how good its retrieval is.
ColPali's own benchmark, ViDoRe, was built to demonstrate exactly this gap and shows a late-interaction visual retriever at nDCG@5 0.81 against a traditional OCR-plus-text pipeline at 0.66 on the same visually-rich document set ([ColPali paper](https://arxiv.org/abs/2407.01449)).

**Screenshot whose only text is drawn inside the image.**
A text embedder needs OCR to run first, then embeds whatever OCR extracted.
If OCR mangles the dialog text, or the app's own OCR coverage log shows a miss (a designed possibility per D-risk "Apple Vision OCR misses on dense screenshots"), the text embedder has nothing correct to embed.
ColQwen2 embeds the rendered image directly, independent of whether OCR ran at all.

**Slide found by its chart shape, no matching words.**
This is the structural failure, not a quality gap.
If the page carries no relevant text, there is no text for any text embedder to encode; the query and the page share zero vocabulary in either direction.
ColQwen2's vision tower matches on layout and shape because it was trained on rendered document images, not word co-occurrence.

**Invoice line item in a table.**
Tables encode meaning through the alignment of a number to its row label, information that lives in the 2D layout, not the token stream.
OCR or PDF-text extraction typically flattens a table into a sequence of tokens and loses that alignment, so a text embedder can retrieve the right page by keyword luck ("Q2", "hosting") but cannot reconstruct which number belongs to which line, which is exactly what the heatmap is for.
A newer, more careful study finds vision-based retrieval actually generalizes worse than OCR pipelines on documents unlike its fine-tuning set ([Lost in OCR Translation, arXiv 2505.05666](https://arxiv.org/abs/2505.05666)), which is a real caveat for the general corpus, but it does not change the three hero cases above: those are cases OCR structurally cannot serve, not cases it serves worse.

## 2. Is there a place for a second, text-only semantic stage

Plausibly yes, for a specific reason: BM25 is lexical, and it gates everything downstream.
If a query and a page share no stems, the page never enters the top-300 candidate pool, so it never reaches ColQwen2's MaxSim rerank no matter how good that rerank is.
A dense text embedding stage between BM25 and the visual rerank would catch exactly this class of miss: a markdown note or a PDF text page found by paraphrase ("outbound data transfer" against a query for "egress") rather than shared words.

FR-7's existing fallback, "run a multivector search over every embedded page" when stage 1 returns fewer than five hits, does not cover this.
It is visual, not textual, so it only searches pages ColQwen2 has already embedded, and it only fires below a five-hit floor, not when BM25 returns five-plus hits that simply omit the right one.
A text-embedding stage could also be run eagerly over the whole text-bearing corpus at ingest time, because a 33-600M parameter text encoder on CPU is orders of magnitude cheaper than ColQwen2 on MPS, so it does not need the lazy 30-page cap that visual embedding needs.

**Whether this is worth shipping is unresolved and should stay unresolved until measured.**
The risk of skipping the experiment is shipping a stage that duplicates what BM25 plus filename and recency boosts already solve for a corpus of the user's own words, since personal-file search often reuses the vocabulary the user typed themselves, unlike enterprise search over documents written by strangers.

**What would settle it, using the existing 30-query golden set and `/eval/golden/run`:**
1. Tag each golden query by whether its expected page is text-native (markdown, or a PDF page with a real text layer) or visual-hero (screenshot, chart page, scanned image).
2. Run the golden set through the current pipeline and record recall@5 and recall@10 split by that tag, not pooled, since a 30-query set pooled together hides a small subset's failure.
3. Add a BM25 plus text-embedding candidate stage (reciprocal rank fusion into the same up-to-300 pool, still capped to 30 for ColQwen2) and re-run the same split.
4. A measurable win on the text-native subset, not the pooled score, is the evidence to keep the stage; no change there, keep it off.
5. Because 30 queries gives thin statistical power on a text-native subset that might be 10-15 queries, extend the golden set with a few deliberately paraphrased queries against known text-native targets, phrased so they share no stems with the target page, and check whether stage 1 alone ever surfaces that page at all; a hard zero there is the strongest single signal that a text-embedding stage adds real recall rather than reordering results that already made the cut.

## 3. If a text stage is worth it, which local model

All figures below are measured directly from Hugging Face repo file listings (safetensors byte size) and from each model's own README or paper, checked 2026-09-07.

| Model | Params | Download | Dims | MTEB Retrieval | License | Matryoshka |
| --- | --- | --- | --- | --- | --- | --- |
| [EmbeddingGemma-300m](https://huggingface.co/google/embeddinggemma-300m) | 308M | 1.21 GB ([file size](https://huggingface.co/api/models/google/embeddinggemma-300m/tree/main)) | 768 | 62.49 Multi-v2 / 55.7 Eng-v2 ([paper Table 5/7](https://arxiv.org/abs/2509.20354)) | Gemma ToU (not OSI, use-restricted) | Yes, to 512/256/128 |
| [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | 595.8M | 1.19 GB ([file size](https://huggingface.co/api/models/Qwen/Qwen3-Embedding-0.6B/tree/main)) | 1024 | 64.65 Multi-v2 / 61.83 Eng-v2 ([model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)) | Apache 2.0 | Yes, 32-1024 |
| [pplx-embed-v1-0.6b](https://huggingface.co/perplexity-ai/pplx-embed-v1-0.6b) | 596M | 2.38 GB, fp32 only ([file size](https://huggingface.co/api/models/perplexity-ai/pplx-embed-v1-0.6b/tree/main)) | 1024 | 65.41 Multi-v2, 18-task nDCG@10 ([paper Table 1](https://arxiv.org/abs/2602.11151)) | MIT | Yes, unspecified floor |
| [bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) | 33.4M | 0.13 GB | 384 | 53.9 MTEB-v2 ([Granite R2 card, IBM's own eval](https://huggingface.co/ibm-granite/granite-embedding-small-english-r2)) | MIT | No |
| [e5-small-v2](https://huggingface.co/intfloat/e5-small-v2) | 33.4M | 0.13 GB | 384 | 48.5 MTEB-v2 (same Granite table) | MIT | No |
| [granite-embedding-small-english-r2](https://huggingface.co/ibm-granite/granite-embedding-small-english-r2) | 47M | 0.10 GB | 384 | 53.9 MTEB-v2 ([own card](https://huggingface.co/ibm-granite/granite-embedding-small-english-r2)) | Apache 2.0 | Not stated |
| [nomic-embed-text-v2-moe](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe) | 475M total / 305M active | 1.90 GB | 768 | 52.86 BEIR, not the same task set ([own card](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe)) | Apache 2.0 | Yes, to 256 |

Two findings change the shape of the owner's original question.

First, `pplx-embed-v1-0.6b` is not purely hosted: the same MIT-licensed weights load through `sentence_transformers.SentenceTransformer(..., trust_remote_code=True)` and run entirely offline, and on Perplexity's own comparison table they edge out both Qwen3-Embedding-0.6B and EmbeddingGemma on this retrieval slice.
That local path costs twice the download of the alternatives (no bf16 checkpoint is published), requires `trust_remote_code=True` (arbitrary code execution from the repo, a supply-chain question none of the other candidates raise), and the model card's primary usage example is the hosted `api.perplexity.ai` endpoint, which is the part that would break the privacy spec.

Second, EmbeddingGemma's Gemma license is not Apache/MIT-equivalent.
It requires redistributors to bind downstream users to Google's Prohibited Use Policy, and Google reserves a right to remotely restrict usage it judges violates that policy ([TechCrunch, March 2026](https://techcrunch.com/2025/03/14/open-ai-model-licenses-often-carry-concerning-restrictions/), [Gemma Terms of Use](https://ai.google.dev/gemma/terms)).
Every weight already in the stack is Apache-2.0 or MIT (D05, D10, D20), so shipping EmbeddingGemma would be the first license exception in the project, not a drop-in.

Qwen3-Embedding-0.6B is the only candidate that is simultaneously top-of-table on retrieval, fully Apache-2.0, Matryoshka-truncatable, and loads through standard `transformers`/`sentence-transformers` with no custom code and no `peft`-style surprise like D31 hit for ColQwen2.

## 4. What would make the choice switchable later

A `TextEmbedder` port, sized like the ones in `sidecar/src/sidecar/application/ports.py`:

```python
class TextEmbedder(Protocol):
    """Embeds short text into a single dense vector for semantic candidate generation.

    Optional: the composition root may leave this port unbound, in which case
    the query pipeline runs BM25 candidate generation alone, exactly as it does today.
    """

    def embed_query(self, text: str) -> Sequence[float]:
        """Embed a search query. Never raises on an empty string; returns a zero vector."""
        ...

    def embed_passage(self, text: str) -> Sequence[float]:
        """Embed a page or chunk of document text for indexing.

        Same dimensionality as `embed_query`, so the two are directly comparable by cosine.
        """
        ...

    @property
    def dimensions(self) -> int:
        """Length of every vector this embedder returns, fixed for the life of an index."""
        ...


class TextVectorStore(Protocol):
    """Stores and searches single-vector text embeddings, independent of the visual `page_vectors` table."""

    def upsert(self, page_id: str, vector: Sequence[float]) -> None:
        """Insert or replace by `page_id`. Idempotent."""
        ...

    def search(self, query_vector: Sequence[float], limit: int) -> list[PageHit]:
        """Nearest pages by cosine similarity, best first. Empty list if the store is empty."""
        ...
```

`IndexFolder` and the search use case take `TextEmbedder | None` and `TextVectorStore | None`.
Turning the stage off is deleting the composition-root binding, not touching a use case, matching D08's existing pattern of keeping vector storage in a separate table so the core `pages` row never carries a nullable vector column.
Swapping models later is changing one adapter and one `dimensions` value; nothing upstream of the port cares which model produced the vector.

A hosted embedder fits the same `Protocol` unchanged, the method signatures do not know or care where the vector came from.
What would actually have to change is the privacy contract around it, not the port: a hosted call needs the same explicit-and-labeled treatment the Anthropic call gets (PRD Principle 1), a setting disabled by default and force-disabled in offline mode (mirroring FR-14), and a new `DECISIONS.md` entry, since D21's "no telemetry, ever" and the PRD's "no network traffic except the explicit download and the Anthropic call" are specifications, not defaults, and a second silent network call would falsify both.
It would also change the economics from pay-once-in-local-compute to pay-per-page-embedded, which has to stay strictly additive: FR-16's "search works without an API key" must keep holding with the port unbound.

## 5. Recommendation

Add a `TextEmbedder` stage using Qwen3-Embedding-0.6B between BM25 and visual rerank, gated behind the golden-set experiment in section 2, not shipped speculatively.
The reason: it is the only small local candidate that leads on retrieval, carries no license exception, and slots behind a port that costs nothing to remove.
The cost of being wrong is small and reversible: if the golden-set split shows no measurable gain on the text-native subset, the loss is a 1.19 GB download and one more idle adapter behind an unbound port, not a rewrite, a privacy exception, or a lost capability.
