# File-Level Evaluation Report

Evaluating **aakash-73/reposcope-ai** | 33 questions across 10 files

> **Judge:** `qwen2.5-coder:7b-instruct` | **Embeddings:** `nomic-embed-text`

> **Questions file:** `file_questions.json`

> **What this measures:** Faithfulness and relevancy of the file-level chat pipeline (`chat_with_component`). Context is pre-analyzed node summary + raw file code. No retrieval or Query Router involved.

---

## 📄 `main.py`
> `backend/main.py`

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `0.7292` |
| **Answer Relevancy** | `0.9795` |

| Question | Faithfulness | Answer Relevancy |
|:---------|-------------:|-----------------:|
| What two HTTP headers can be used to authenticate API requests in this | `1.0000` | `1.0000` |
| Which URL path is always exempt from API key authentication, and what  | `1.0000` | `0.9344` |
| What tasks does the FastAPI lifespan startup routine perform? | `0.9167` | `0.9835` |
| What HTTP methods are permitted by the CORS middleware? | `0.0000` | `1.0000` |

### DeepEval

| Question | Faith | Rel | Correct | Reason |
|:---------|------:|----:|--------:|:-------|
| What two HTTP headers can be used to authenticate API reques... | `0.0000` | `1.0000` | `1.0000` | The score is 0.00 because the actual output contradicts the retrieval context by |
| Which URL path is always exempt from API key authentication,... | `0.0000` | `1.0000` | `1.0000` | The score is 0.00 because the actual output contradicts the retrieval context by |
| What tasks does the FastAPI lifespan startup routine perform... | `0.5455` | `0.0909` | `1.0000` | The score is 0.55 because the actual output contradicts the retrieval context in |
| What HTTP methods are permitted by the CORS middleware? | `0.0000` | `1.0000` | `0.8000` | The score is 0.00 because the actual output contradicts the retrieval context by |

---

## 📄 `config.py`
> `backend/config.py`

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `0.8333` |
| **Answer Relevancy** | `0.9552` |

| Question | Faithfulness | Answer Relevancy |
|:---------|-------------:|-----------------:|
| What is the default Ollama model used for both analysis and chat tasks | `1.0000` | `0.9626` |
| What does leaving API_KEY as an empty string (the default) mean for th | `0.5000` | `0.9029` |
| What are the four file-processing character-limit settings and their d | `1.0000` | `1.0000` |

### DeepEval

| Question | Faith | Rel | Correct | Reason |
|:---------|------:|----:|--------:|:-------|
| What is the default Ollama model used for both analysis and ... | `1.0000` | `1.0000` | `0.8000` | The score is 1.00 because there are no contradictions. |
| What does leaving API_KEY as an empty string (the default) m... | `1.0000` | `0.2500` | `0.8000` | The score is 1.00 because there are no contradictions. |
| What are the four file-processing character-limit settings a... | `0.2000` | `1.0000` | `0.0000` | The score is 0.20 because the actual output contradicts the retrieval context by |

---

## 📄 `database.py`
> `backend/database.py`

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `0.8750` |
| **Answer Relevancy** | `0.5822` |

| Question | Faithfulness | Answer Relevancy |
|:---------|-------------:|-----------------:|
| What unique constraint is enforced on the files collection? | `0.7500` | `0.9666` |
| Which collections store Knowledge Graph data and what indexes are defi | `1.0000` | `0.7799` |
| What text search index is created on the files collection and what is  | `0.8750` | `0.0000` |

### DeepEval

| Question | Faith | Rel | Correct | Reason |
|:---------|------:|----:|--------:|:-------|
| What unique constraint is enforced on the files collection? | `1.0000` | `1.0000` | `0.8000` | The score is 1.00 because there are no contradictions. |
| Which collections store Knowledge Graph data and what indexe... | `0.1667` | `1.0000` | `1.0000` | The score is 0.17 because the actual output mentions specific collections (`kg_n |
| What text search index is created on the files collection an... | `0.0000` | `0.7500` | `0.5000` | The score is 0.00 because the actual output contradicts the retrieval context by |

---

## 📄 `node_analyzer_service.py`
> `backend/services/node_analyzer_service.py`

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `0.2262` |
| **Answer Relevancy** | `0.6599` |

| Question | Faithfulness | Answer Relevancy |
|:---------|-------------:|-----------------:|
| How does analyze_all_nodes treat leaf files differently from files tha | `0.3333` | `0.8115` |
| What JSON fields does STRUCTURED_PROMPT require the LLM to return for  | `0.0000` | `0.9578` |
| What four Knowledge Graph edge relation types are created in _update_k | `0.0000` | `0.0000` |
| Which topological sort algorithm is used in _sort_by_dependency_order  | `0.5714` | `0.8701` |

### DeepEval

| Question | Faith | Rel | Correct | Reason |
|:---------|------:|----:|--------:|:-------|
| How does analyze_all_nodes treat leaf files differently from... | `0.7500` | `0.1667` | `1.0000` | The score is 0.75 because the actual output contradicts the retrieval context by |
| What JSON fields does STRUCTURED_PROMPT require the LLM to r... | `0.0000` | `1.0000` | `1.0000` | The score is 0.00 because the actual output contradicts the retrieval context by |
| What four Knowledge Graph edge relation types are created in... | `0.0000` | `0.0000` | `0.0000` | The score is 0.00 because the actual output contradicts the retrieval context by |
| Which topological sort algorithm is used in _sort_by_depende... | `0.4286` | `1.0000` | `0.8000` | The score is 0.43 because the actual output incorrectly attributes Kahn's Algori |

---

## 📄 `query_router_service.py`
> `backend/services/query_router_service.py`

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `0.2500` |
| **Answer Relevancy** | `0.8993` |

| Question | Faithfulness | Answer Relevancy |
|:---------|-------------:|-----------------:|
| What are the six query strategy types the router can classify a query  | `1.0000` | `0.9899` |
| How does query_hive_search fall back when no matching category nodes a | `0.0000` | `0.8893` |
| What MongoDB operator does query_graph use and what is its maxDepth se | `0.0000` | `0.8041` |
| How does execute_router_search limit and rank the final file context a | `0.0000` | `0.9140` |

### DeepEval

| Question | Faith | Rel | Correct | Reason |
|:---------|------:|----:|--------:|:-------|
| What are the six query strategy types the router can classif... | `0.2857` | `0.1667` | `1.0000` | The score is 0.29 because the actual output contradicts the retrieval context by |
| How does query_hive_search fall back when no matching catego... | `1.0000` | `0.2000` | `0.0000` | The score is 1.00 because there are no contradictions. |
| What MongoDB operator does query_graph use and what is its m... | `0.0000` | `0.4000` | `1.0000` | The score is 0.00 because the actual output refers to '$graphLookup' and 'maxDep |
| How does execute_router_search limit and rank the final file... | `0.1667` | `0.1111` | `0.8000` | The score is 0.17 because the retrieval context does not provide any information |

---

## 📄 `repo_chat_service.py`
> `backend/services/repo_chat_service.py`

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `0.2593` |
| **Answer Relevancy** | `0.8504` |

| Question | Faithfulness | Answer Relevancy |
|:---------|-------------:|-----------------:|
| What two LLM clients are initialized in repo_chat_service.py and what  | `0.7778` | `0.8684` |
| What exact response must the model return when the user asks something | `0.0000` | `0.8803` |
| How does stream_chat_with_repo strip <think> blocks without buffering  | `0.0000` | `0.8026` |

### DeepEval

| Question | Faith | Rel | Correct | Reason |
|:---------|------:|----:|--------:|:-------|
| What two LLM clients are initialized in repo_chat_service.py... | `0.5000` | `0.1111` | `1.0000` | The score is 0.50 because the contradictions indicate a mismatch between the com |
| What exact response must the model return when the user asks... | `0.0000` | `0.5000` | `0.0000` | The score is 0.00 because the retrieval context does not mention anything about  |
| How does stream_chat_with_repo strip <think> blocks without ... | `0.7500` | `1.0000` | `0.8000` | The score is 0.75 because the `stream_chat_with_repo` function is described as s |

---

## 📄 `guardrail_service.py`
> `backend/services/guardrail_service.py`

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `0.2667` |
| **Answer Relevancy** | `0.8846` |

| Question | Faithfulness | Answer Relevancy |
|:---------|-------------:|-----------------:|
| How many prompt injection patterns are defined in guardrail_service.py | `0.8000` | `0.9401` |
| What is the minimum query word count before off-topic pattern matching | `0.0000` | `0.9287` |
| What overrides off-topic detection even when an off-topic pattern matc | `0.0000` | `0.7850` |

### DeepEval

| Question | Faith | Rel | Correct | Reason |
|:---------|------:|----:|--------:|:-------|
| How many prompt injection patterns are defined in guardrail_... | `nan` | `0.4000` | `1.0000` | Skipped — judge contamination on security content. Use RAGAS faithfulness for th |
| What is the minimum query word count before off-topic patter... | `0.5000` | `1.0000` | `0.8000` | The score is 0.50 because the contradiction indicates that _OFFTOPIC_PATTERNS co |
| What overrides off-topic detection even when an off-topic pa... | `0.0000` | `0.6667` | `1.0000` | The score is 0.00 because the retrieval context states that off-topic queries ar |

---

## 📄 `repo_controller.py`
> `backend/controllers/repo_controller.py`

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `0.6667` |
| **Answer Relevancy** | `0.7926` |

| Question | Faithfulness | Answer Relevancy |
|:---------|-------------:|-----------------:|
| How does import_repository detect that a repository has already been i | `1.0000` | `0.7114` |
| What cleanup steps run before a failed repository import is retried? | `0.0000` | `0.9729` |
| What hashing function generates repo_id versus unique_key? | `1.0000` | `0.6936` |

### DeepEval

| Question | Faith | Rel | Correct | Reason |
|:---------|------:|----:|--------:|:-------|
| How does import_repository detect that a repository has alre... | `0.8333` | `0.8889` | `0.8000` | The score is 0.83 because the actual output implies a retry mechanism for import |
| What cleanup steps run before a failed repository import is ... | `0.2500` | `1.0000` | `0.8000` | The score is 0.25 because the actual output contradicts the retrieval context by |
| What hashing function generates repo_id versus unique_key? | `1.0000` | `0.5000` | `1.0000` | The score is 1.00 because there are no contradictions. |

---

## 📄 `sync_service.py`
> `backend/services/sync_service.py`

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `1.0000` |
| **Answer Relevancy** | `0.8844` |

| Question | Faithfulness | Answer Relevancy |
|:---------|-------------:|-----------------:|
| What is the first check sync_repository performs to avoid unnecessary  | `1.0000` | `0.8355` |
| What hashing algorithm does sync_service use for file content change d | `1.0000` | `0.9873` |
| What repository status is required before sync_repository is allowed t | `1.0000` | `0.8304` |

### DeepEval

| Question | Faith | Rel | Correct | Reason |
|:---------|------:|----:|--------:|:-------|
| What is the first check sync_repository performs to avoid un... | `0.5000` | `1.0000` | `1.0000` | The score is 0.50 because the actual output contradicts the retrieval context by |
| What hashing algorithm does sync_service use for file conten... | `1.0000` | `0.5000` | `0.7000` | The score is 1.00 because there are no contradictions. |
| What repository status is required before sync_repository is... | `1.0000` | `1.0000` | `1.0000` | The score is 1.00 because there are no contradictions. |

---

## 📄 `auto_sync_service.py`
> `backend/services/auto_sync_service.py`

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `1.0000` |
| **Answer Relevancy** | `0.8731` |

| Question | Faithfulness | Answer Relevancy |
|:---------|-------------:|-----------------:|
| How frequently does the auto-sync polling loop wake up to check for du | `1.0000` | `0.9120` |
| What three conditions must all be true for a repo to be picked up by t | `1.0000` | `0.9024` |
| How does start_background_polling prevent duplicate background tasks? | `1.0000` | `0.8049` |

### DeepEval

| Question | Faith | Rel | Correct | Reason |
|:---------|------:|----:|--------:|:-------|
| How frequently does the auto-sync polling loop wake up to ch... | `0.0000` | `1.0000` | `1.0000` | The score is 0.00 because the actual output contradicts the retrieval context by |
| What three conditions must all be true for a repo to be pick... | `1.0000` | `1.0000` | `1.0000` | The score is 1.00 because there are no contradictions. |
| How does start_background_polling prevent duplicate backgrou... | `1.0000` | `0.2500` | `1.0000` | The score is 1.00 because there are no contradictions. |

---

## 📊 Overall Scores

### RAGAS

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `0.5916` |
| **Answer Relevancy** | `0.8370` |

### DeepEval

| Metric | Score |
|:-------|------:|
| **Faithfulness** | `0.4649` |
| **Answer Relevancy** | `0.6652` |
| **Correctness (GEval)** | `0.7939` |

### Framework Comparison

| Metric | RAGAS | DeepEval | Agreement |
|:-------|------:|---------:|:---------:|
| Faithfulness     | `0.5916` | `0.4649` | ✅ |
| Answer Relevancy | `0.8370`   | `0.6652`   | ⚠️ |

> ✅ = agree within 0.15 | ⚠️ = diverge, check per-query reasons

---

## 📖 Score Guide

| Range | Meaning |
|:------|:--------|
| 0.90–1.00 | Excellent |
| 0.80–0.89 | Good |
| 0.70–0.79 | Acceptable |
| < 0.70 | Needs work |
| `nan` | Judge failed or skipped |

> Faithfulness/Correctness marked `nan` for security-content queries (guardrail service) due to local judge contamination. Use RAGAS faithfulness as the authoritative score for those.
