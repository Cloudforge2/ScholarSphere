# 🧠 Author Profile System

A comprehensive research profiling and summarization system that aggregates data from multiple scholarly APIs, deduplicates abstracts and full texts, extracts content from PDFs, and generates detailed summaries using **GroqCloud (LLaMA 3.3)** (Primary LLM) ,  **OpenAI GPT-4o-mini**( Fallback Option) ,  **Rule-based summarization**  (last fallback Option)

This tool allows you to search for an author by **name or ORCID**, fetch all their works from OpenAlex and related sources, and generate:
- Cleaned, deduplicated paper metadata
- Co-author networks
- Research statistics (citations, years active, collaborators)
- Full paper and author-level summaries (via LLMs)
- PDF-based content extraction (PyPDF2 / pdfplumber)

---

## ✨ Features

- 🔍 Fetches author & paper data from:
  - **OpenAlex**
  - **arXiv**
  - **Semantic Scholar**
  - **Unpaywall**
  - **Crossref**
- 📑 Extracts full text from PDFs (if available)
- 🧹 Deduplicates overlapping abstracts from multiple sources
- 🧠 Summarizes research using:
  - **GroqCloud** (LLaMA 3.3 70B) — primary LLM
  - **OpenAI GPT-4o-mini** — fallback
  - **Rule-based summarization** — last fallback
- 🧍 Displays co-authors, affiliations, and top collaborators
- 📈 Computes statistics:
  - Publication velocity
  - Citations and h-index
  - Collaboration frequency
  - 💾 Interactive or non-interactive execution modes

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 API Keys Setup

This system uses both **GroqCloud** and **OpenAI** APIs.

### 1. Groq API Key (Recommended)

Get your API key from [https://console.groq.com](https://console.groq.com).

Then either:

- **Option A:** Set it as an environment variable:
  ```bash
  export GROQ_API_KEY="your_groq_api_key_here"
  ```
- **Option B:** Save it in `~/.groq_api_key`  
  (the program can do this for you interactively on first run).

### 2. OpenAI API Key (Optional Fallback)

Get your OpenAI key from [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)

Then:
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
```

---

## 🧰 Usage

Run the system:

```bash
python kc_core.py
```

You’ll be prompted to search for an author:

```
Search by (1) Name or (2) ORCID? Enter 1 or 2:
```

Then follow interactive steps to:
- Select author (if multiple found)
- Choose how many papers to fetch
- View publication statistics and summaries



## ⚡ Example Workflow

1. Run the script.
2. Search author by **name** (e.g., *"Yogesh Simmhan"*).
3. Select the correct OpenAlex profile.
4. The system:
   - Fetches metadata from 5 APIs.
   - Downloads open-access PDFs when available.
   - Deduplicates content.
   - Generates author and paper summaries.
   - Prints publication stats and collaboration graphs.

---

## 📦 Outputs

- Output of:
  - Author profile
  - Research summary
  - Top collaborators
  - Summarized paper list


---

## 🧩 Additional Features 

| Feature | How to Enable |
|----------|----------------|
| **PDF text extraction** | Install `PyPDF2` and `pdfplumber` (already in `requirements.txt`) |
| **Full author merging via ORCID** | Automatically enabled if multiple profiles share same ORCID |
| **Non-interactive mode** | Pipe default answers or run via cron/script |

---


---

## 🧰 Tech Stack

- **Python 3.8+**
- **aiohttp / asyncio** — parallel I/O
- **requests** — API calls
- **PyPDF2 / pdfplumber** — PDF parsing
- **GroqCloud / OpenAI API** — LLM summarization
- **OpenAlex, Crossref, Semantic Scholar, arXiv, Unpaywall APIs**



## 📜 License

MIT License © 2025  
