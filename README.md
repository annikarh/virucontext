# ViruContext

Summarize **open-access virology papers** into a field packet for **writing, teaching, and tool development**.

This repository is the source code. It is **not** a public website that is already running. Until someone hosts it with an API key, the working product is still the chat where this tool was designed.

Target reader: someone with virology training who is not necessarily an expert in the paper's subfield (student, postdoc, PI). Not a lay explainer.

---

## For the virologist (no coding)

You do **not** need to install this to use ViruContext today. Paste a paper title, DOI, or open-access link in the chat that built this tool.

Give this repository to a student, collaborator, or IT person if you want a page on your own computer or lab server.

**Scope**

- Open-access papers with full text in [Europe PMC](https://europepmc.org/) / PMC.
- Paywalled PDFs are refused, not guessed.
- Output is the locked packet: paper identity, field background, what was shown, related viruses to keep separate, inferred vs shown, then writing / teaching / tools.

---

## For a helper (run it)

Needs: Python 3.11+, and an [OpenAI API key](https://platform.openai.com/api-keys) (billed to whoever owns the key).

```bash
git clone https://github.com/annikarh/virucontext.git
cd virucontext
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste OPENAI_API_KEY=
uvicorn app:app --reload --port 8000
```

Open http://127.0.0.1:8000

Paste a title, DOI, PMID, PMCID, or Europe PMC / PMC link. Optional: name a virus of interest. Summarize.

Do not commit `.env`. The API key never belongs in GitHub.

### Docker

```bash
docker build -t virucontext .
docker run --rm -p 8000:8000 --env-file .env virucontext
```

### Hosting later

Any host that runs a Python web process works (Render, Railway, Fly, a lab VM). Set `OPENAI_API_KEY` as a secret. This repo does not include a live deployment.

---

## Packet contract

Every successful run returns these sections, in this order:

1. Paper
2. Background (field context for virologists; prior knowledge vs this paper's contribution)
3. What this paper is about
4. Shown in this paper
5. Related viruses / not the same thing
6. Inferred, not shown
7. For writing / For teaching / For tools

Accuracy rules: isolate, temperature, pH, maturation state, and antibody clone stay distinct. No fake citations. Scope claims to the virus actually studied.

Prompt text lives in `virucontext/prompt.py`.
