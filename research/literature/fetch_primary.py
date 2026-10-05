"""Download public primary papers for local scholarly inspection; no learner data."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, requests, fitz

BASE = Path(__file__).resolve().parent
PAPERS = {
    "code_dkt_2022": "https://educationaldatamining.org/edm2022/proceedings/2022.EDM-long-papers.5/2022.EDM-long-papers.5.pdf",
    "code_edit_aied_2025": "https://people.umass.edu/~andrewlan/papers/25aied-codeedit.pdf",
    "code_edit_arxiv_2025": "https://arxiv.org/pdf/2502.19407v2",
    "reliability_pkt_2026": "https://arxiv.org/pdf/2605.04727v1",
    "code_insight_2026": "https://arxiv.org/pdf/2609.00940v1",
    "exrec_2025": "https://proceedings.neurips.cc/paper_files/paper/2025/file/13707aad517ddd6c09ea02e0f55e1e7a-Paper-Conference.pdf",
    "rem_2017": "https://www.cs.cmu.edu/~shayand/papers/L@S2017.pdf",
    "unier_2026": "https://arxiv.org/pdf/2605.16750v1",
}

def fetch(item):
    key, url = item
    try:
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            raise ValueError("Response was not a PDF")
        pdf_path = BASE / "papers" / f"{key}.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(r.content)
        doc = fitz.open(stream=r.content, filetype="pdf")
        text_path = BASE / "papers" / f"{key}.txt"
        text_path.write_text("\n".join(f"\n=== PDF PAGE {i+1} ===\n{page.get_text()}" for i, page in enumerate(doc)), encoding="utf-8")
        return {"id": key, "requested_url": url, "resolved_url": r.url, "local_pdf": str(pdf_path.relative_to(BASE)), "sha256": hashlib.sha256(r.content).hexdigest(), "bytes": len(r.content), "pages": len(doc), "retrieved_on": "2026-09-26"}
    except Exception as exc:
        return {"id": key, "requested_url": url, "error": str(exc)}

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=8) as pool:
        result = list(pool.map(fetch, PAPERS.items()))
    (BASE / "download_manifest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
