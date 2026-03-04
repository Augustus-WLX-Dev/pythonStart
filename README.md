# Python Learning Journey 🚀

Welcome to my Python learning repository. This space currently documents my deep dive into and practical summaries of `asyncio` asynchronous programming. It rebuilds the underlying mechanisms of Asyncio using three-dimensional physical thinking.

欢迎来到我的 Python 学习仓库。这里目前主要记录了我对 `asyncio` 异步编程的深度探索与实践总结。用物理世界立体的思维来重新构建 Asyncio 的底层机制。

---

## 📂 Repository Resources | 仓库资源

### 📚 Core Principles Deep Dive | 核心原理精讲 ([docs/](docs/))

This directory contains all deep learning notes, covering the most core theoretical models in asynchronous programming.
这里存放了所有深度学习笔记，涵盖了异步编程中最核心的理论模型。

#### 🇬🇧 English Edition

- [**Semaphore Master Guide (Deep Dive)**](docs/asyncio_semaphore_guide.md): **[Under the Hood]** A bilingual, line-by-line low-level concurrent analysis of `asyncio.Semaphore`.

- [**The Director-Camera Model (Asyncio Meta-Theory)**](docs/asyncio_meta_theory.md): **[Macro Architecture]** Rebuilding Asyncio's internal mechanisms using the film set metaphor.

- [**The Future Object Decoded**](docs/future_concept.md): **[Meta-Theory]** Deep dive into the "Status Machine, Mailbox, and Pager" model.

- [**blocking_fix Deep Dive**](docs/blocking_fix_deep_dive.md): **[Micro Details]** A line-by-line breakdown of the code; please read this in conjunction with [**The Director-Camera Model (Asyncio Meta-Theory)**](docs/asyncio_meta_theory.md).

- [**Asyncio Queue Explained**](docs/ASYNCIO_QUEUE_EXPLAINED.md): A practical guide to the Producer-Consumer model.

- [**Asyncio TaskGroups (Structured Concurrency)**](docs/asy_taskgroups_walkthrough.md): **[Modern Pattern]** Using the "Safety Escape Pod" metaphor to master Python 3.11's TaskGroups and ExceptionGroups.

- [**Asyncio Chronicles**](docs/asyncio_chronicles.md): **[Universal Evolution]** Recording the first major breakthroughs during the learning process.
 - Source Code: [asy_practice.py](src/asy_practice.py) (Events & Signals) & [asy_queue_simple.py](src/asy_queue_simple.py) (Queues & Sync)

---

#### 🇨🇳 中文版 (Chinese Edition)

- [**Semaphore 核心逻辑通俗解析 (Master Guide)**](docs/asyncio_semaphore_guide.md): **[底层揭秘]** 中英双语，逐行级拆解 `asyncio.Semaphore` 的极客指南。

- [**Asyncio TaskGroups (结构化并发)**](docs/asyncio_taskgroups.md): **[现代模式]** 用“安全逃生舱”的隐喻掌握 Python 3.11 的 TaskGroups 与 ExceptionGroups。
    - 对应源码：[asy_taskgroups.py](src/asy_taskgroups.py)

- [**导演与摄像机模型 (Asyncio Meta-Theory)**](docs/asyncio_meta_theory.md): **[宏观架构]** 用电影片场的隐喻重新构建 Asyncio 底层机制。
- [**Future 对象深度解码**](docs/future_concept.md): **[元理论]** 深度剖析“状态机、信箱与呼叫机”模型。

- [**blocking_fix 深度剖析 (Deep Dive)**](docs/blocking_fix_deep_dive.md): **[微观细节]** 针对代码逐行拆解，请结合 [**导演与摄像机模型 (Asyncio Meta-Theory)**](docs/asyncio_meta_theory.md) 食用。

- [**Asyncio Queue 详解**](docs/ASYNCIO_QUEUE_EXPLAINED.md): 生产者-消费者模型的实战指南。

- [**Asyncio 编年史 (Chronicles)**](docs/asyncio_chronicles.md): **[宇宙演化论]** 记录学习过程中的首次重大突破。
  - 对应源码：[asy_practice.py](src/asy_practice.py) (事件与信号) & [asy_queue_simple.py](src/asy_queue_simple.py) (队列与同步)

---

## 🛠️ Getting Started | 如何开始

1. **Read the Docs**: Start by reading the explanations in the `docs/` directory.  
   **阅读文档**：首先阅读 `docs/` 目录下的解读文章。

2. **Explore the Code**: Review the corresponding source code in the `src/` directory to deepen your understanding.  
   **查看源码**：结合 `src/` 目录下的相关代码进行对照学习，加深理解。

---
*Look, this is my universe. Enjoy it or leave it.*  
*这是我的宇宙。喜欢就来，不喜欢随意。*
