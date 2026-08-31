---

layout: single
title: "RAG 学习笔记：Phase 3 reranker.py + engine.py 带读"
date: 2026-08-31 17:03:00 +0800
categories:

- 学习笔记
tags:
- RAG
- Python
- Reranker
- Cross-Encoder
- 个人博客

## toc: true
toc_sticky: true

> **对照阅读：Phase 3 检索（第四篇）**
>
>
> |            |                                                                                                                                                                                                                                                                              |
> | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
> | 仓库内路径      | `rag-backend/app/retrieval/reranker.py`、`engine.py`                                                                                                                                                                                                                          |
> | GitHub 原文  | [reranker.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/reranker.py) · [engine.py](https://github.com/123XH-sudo/123xh-sudo.github.io/blob/main/rag-backend/app/retrieval/engine.py)                                            |
> | 上一篇        | [hybrid.py]({% post_url 2026-08-31-rag-retrieval-hybrid-walkthrough %})                                                                                                                                                                                                      |
> | Phase 3 系列 | [types + vector]({% post_url 2026-08-30-rag-retrieval-types-vector-walkthrough %}) → [corpus + bm25]({% post_url 2026-08-30-rag-retrieval-corpus-bm25-walkthrough %}) → [hybrid]({% post_url 2026-08-31-rag-retrieval-hybrid-walkthrough %}) → **rerank + engine**（本文）→ eval |
> | CLI        | `python -m app.retrieval.search "..."`（默认 `hybrid_rerank`）                                                                                                                                                                                                                   |
>
>
> reranker 80 行 + engine 54 行。**先逐行读码、自己思考，再整理成博客。** 这篇记录 Cross-Encoder 精排、四种检索模式怎么串、以及读码时把模式搞混的纠错。

