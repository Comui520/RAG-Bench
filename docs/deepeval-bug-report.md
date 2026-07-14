# deepeval Bug Report: `DeepEvalBaseLLM` Subclass Incompatible with Synthesizer

> **Version:** deepeval v4.0.7
> **Status:** Unresolved upstream
> **Discovered:** 2026-07-14 during RAG Evaluation Platform v2 development

## Summary

Custom `DeepEvalBaseLLM` subclasses cannot be used as `critic_model` in `ContextConstructionConfig` — the Synthesizer silently returns 0 goldens.

## Reproduction

```python
from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import ContextConstructionConfig
from deepeval.models import DeepEvalBaseLLM
from deepeval.models import DeepEvalBaseEmbeddingModel

# A correctly implemented custom LLM
class MyModel(DeepEvalBaseLLM):
    def get_model_name(self): return "my-model"
    def load_model(self, async_mode=False): return None
    def generate(self, prompt, schema=None): return "{}", 0.0
    async def a_generate(self, prompt, schema=None): return "{}", 0.0

# A correctly implemented custom embedder
class MyEmbedder(DeepEvalBaseEmbeddingModel):
    def get_model_name(self): return "my-embedder"
    def load_model(self): return None
    def embed_text(self, text): return [0.0] * 768
    def embed_texts(self, texts): return [[0.0] * 768] * len(texts)
    async def a_embed_text(self, text): return [0.0] * 768
    async def a_embed_texts(self, texts): return [[0.0] * 768] * len(texts)

# Should work but doesn't
model = MyModel()
embedder = MyEmbedder()
cfg = ContextConstructionConfig(embedder=embedder, critic_model=model, chunk_size=200)
s = Synthesizer(model=model)
goldens = s.generate_goldens_from_docs(
    document_paths=["test_doc.txt"],
    context_construction_config=cfg,
    max_goldens_per_context=2,
)

print(len(goldens))  # Expected: >0  Actual: 0
```

### Console Output

```
[Confident AI Synthesizer Log] SUCCESS: Context Construction: Utilizing 0 out of N chunks.
```

Note: `DeepSeekModel` (native deepeval model) works correctly with identical parameters.

## Root Cause Analysis

1. **`DeepEvalBaseLLM.generate()` abstract signature** declares return type as `str`:
   ```python
   @abstractmethod
   def generate(self, *args, **kwargs) -> str:
   ```

2. **Native models** (`DeepSeekModel`, `OpenAIModel`, etc.) actually return `Tuple[Union[str, BaseModel], float]` — a `(content, cost)` 2-tuple.

3. **Synthesizer's chunk evaluation** (`context_generator.py`, `_generate_schema()` and related methods) internally assumes the `(parsed_model, cost)` tuple return format. It does NOT use the public `generate_with_schema()` path.

4. When a custom `DeepEvalBaseLLM` subclass returns `str` (per the documented abstract signature), the Synthesizer fails to parse the return value and **silently discards all chunks** — no error, no warning, just 0 goldens.

## Impact

| Model Type | `generate()` Return | Synthesizer |
|-----------|-------------------|-------------|
| `DeepSeekModel` (native) | `(content, cost)` tuple | Works |
| `OpenAIModel` (native) | `(content, cost)` tuple | Works |
| Custom `DeepEvalBaseLLM` subclass | `str` or `(str, float)` | Returns 0 goldens |

Any developer creating custom deepeval models by following the documented `DeepEvalBaseLLM` interface will hit this bug.

## Suggested Fixes (for upstream)

### Option A: Fix the abstract signature
Update `DeepEvalBaseLLM.generate()` and `a_generate()` return type to match all native implementations:
```python
@abstractmethod
def generate(self, *args, **kwargs) -> Tuple[Union[str, BaseModel], float]:
```
Impact: High — all downstream implementations need updating.

### Option B: Fix the Synthesizer
In `context_generator.py`, add return value format detection:
```python
result = self.critic_model.generate(prompt, schema=schema)
if isinstance(result, tuple) and len(result) == 2:
    parsed, cost = result
else:
    parsed, cost = result, 0.0
```
Impact: Low — backward compatible, minimal changes.

### Option C: Add internal adapter
Add a `_generate_for_eval()` method to `DeepEvalBaseLLM` that normalizes return format regardless of subclass implementation.

## Workaround Used in This Project

`app/pipeline.py:build_evaluation_model()` routes to native `DeepSeekModel` when provider is `"deepseek"`, and uses `CustomOpenAIModel` for all other providers. This avoids the bug for the DeepSeek path while preserving custom model support for other providers.
