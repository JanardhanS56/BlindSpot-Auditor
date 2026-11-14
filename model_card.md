# Nemotron-3.5-Embed-8B-BF16 — Model Card Summary

## Overview
- **What it is:** An 8B-parameter multimodal embedding model by NVIDIA, optimized for text and document-image retrieval in RAG (Retrieval-Augmented Generation) applications.
- **Key capability:** Embeds document pages as images, text, or combined image–text inputs. Supports dense retrieval, semantic search, and agentic RAG workflows.
- **License:** OpenMDW License Agreement v1.1 (commercially usable). Also references Apache 2.0 for Ministral-3-8B component.
- **Release dates:** API via Build.NVIDIA.com — 10/19/2026; Hugging Face — 10/20/2026.
- **Deployment:** Global; optimized for NVIDIA GPU-accelerated systems (CUDA/Photon Engine).

## Architecture
| Detail | Value |
|---|---|
| **Parameters** | 8.38B total |
| **Architecture** | Transformer |
| **Vision Encoder** | Initialized from `mistralai/Ministral-3-8B-Instruct-2512-BF16` |
| **LLM Component** | Initialized from `nvidia/Nemotron-3-Embed-8B-BF16` (frozen during fine-tuning) |
| **Training** | Only vision encoder & multimodal projector were trained; LLM component kept frozen |

## Input
| Detail | Value |
|---|---|
| **Modalities** | Text, Image, or combined Image + Text |
| **Query input** | Text only |
| **Document input** | Image, text, or both |
| **Image size** | Default longest edge: 1,120 px (up to 1,540 px) |
| **Max context** | 32,768 tokens |

## Output
| Detail | Value |
|---|---|
| **Embedding** | 4,096-dimensional vector (mean-pooled, L2-normalized) |
| **Dynamic truncation** | Supports smaller sizes (e.g., 1,024 or 512 dims) — L2-normalize after truncation for best results |

## Use Cases
- **Multimodal RAG:** Build Q&A applications over large corpora of documents (text + images).
- **Semantic search:** Search across mixed text and document-image collections.
- **Agentic workflows:** Embeddings feed into agent-based retrieval systems.

## How It Works (Typical Pipeline)
1. **Indexing:** Embed the entire corpus (document images or text chunks) and store vectors in a vector database alongside raw content.
2. **Query:** Embed the user's text query at inference time.
3. **Retrieve:** Use similarity search against stored embeddings to find relevant documents.

## Multilingual Support
- **Text retrieval:** 34 languages (English, Chinese, Japanese, Korean, Hindi, Arabic, Spanish, French, German, Russian, Portuguese, and more).
- **Image retrieval:** 18 languages (Arabic, Bengali, Chinese, English, Hindi, Japanese, Korean, Russian, Spanish, Thai, and more).

## Training Data
| Modality | Size |
|---|---|
| Text-only | 50M+ samples |
| Image (with/without text) | 2.3M samples |

- Datasets: Publicly available, commercially permissible, and synthetically generated (queries generated from seed documents or LLM-based QA pairs).

## Evaluation Scores (NDCG@10)
| Benchmark | Image | Text | Image + Text |
|---|---|---|---|
| **ViDoRe V3** | 60.39 | 60.65 | 61.47 |
| **MIRACL-VISION** | 70.15 | — | — |

## Integration
- **Runtime:** Native CUDA backend — Photon Engine
- **OS:** Linux
- **Framework:** `transformers==5.12.1`
- **Hardware:** NVIDIA GPU-accelerated systems (CUDA cores)

## Key Notes
- The text embeddings are **identical** to `Nemotron-3-Embed-8B-BF16` since the LLM component is frozen.
- Image inputs support text, tables, charts, and infographics.
- Ethical considerations: Users responsible for input rights/permissions; NVIDIA recommends testing with use-case-specific data before deployment.