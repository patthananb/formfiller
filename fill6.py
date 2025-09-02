# pip install requests
import re, time, random, requests
from pathlib import Path
from typing import Dict, List, Tuple

FORM_ID = "1FAIpQLSclacqDbfy4PFIYBATKqWVJsWnpUe9WH_U15P92fjpTl_KDWg"
VIEW_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/viewform"
POST_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"

# -------------------- CONFIG: entries per page --------------------
# Put each page’s entries here. The code will accumulate answers across pages.
PAGES: List[Dict[str, List[str]]] = [
    # Page 0
    {
        "entry.1212729351": ["ปี 4 ขึ้นไป"],
        "entry.2139451852": ["วิศวกรรมศาสตร์"],
    },
    # Page 1
    {
        "entry.233448731": ["ไม่มีปัญหา"],
        "entry.663819695": ["แว่นสายตา"],
    },
    # Page 2
    {
        "entry.850765298": ["น้อยกว่า 1 ชั่วโมง"],
        "entry.961423934": ["น้อยกว่า 1 ชั่วโมง"],
        "entry.1127393595": ["ดูหนัง/เล่นเกม/โซเชียลมีเดีย"],
    },
    # Page 3 (final)
    {
        "entry.2121588": ["ไม่พักเลย"],
    },
]

OTHER_PAT = re.compile(r"^\s*(?:__other_option__|other|others|อื่น|อื่นๆ|อื่น ๆ|その他)\s*$", re.IGNORECASE)

def filter_other(options: List[str]) -> List[str]:
    return [o for o in options if not OTHER_PAT.match(o or "")]

def parse_hidden(html: str) -> Dict[str, str]:
    # Collect hidden inputs we should carry
    hidden = {}
    for name, value in re.findall(r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]*value="([^"]*)"', html):
        hidden[name] = value
    return hidden

def fetch_first_page(sess: requests.Session) -> Tuple[str, Dict[str,str]]:
    r = sess.get(VIEW_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    if r.status_code != 200:
        Path("last_view.html").write_text(r.text, encoding="utf-8")
        raise RuntimeError(f"Failed to GET viewform: {r.status_code}")
    hidden = parse_hidden(r.text)
    fbzx = hidden.get("fbzx")
    if not fbzx:
        Path("last_view.html").write_text(r.text, encoding="utf-8")
        raise RuntimeError("fbzx not found (is the form restricted?)")
    return fbzx, hidden

def answers_to_tuples(answers: Dict[str, List[str]]) -> List[Tuple[str,str]]:
    """Turn {'entry.X': ['A','B']} into repeated key tuples."""
    tuples: List[Tuple[str,str]] = []
    for qid, opts in answers.items():
        vals = filter_other(opts or [])
        for v in vals:
            tuples.append((qid, v))
    return tuples

def build_payload(page_index: int,
                  fbzx: str,
                  carry_hidden: Dict[str,str],
                  cumulative_answers: Dict[str, List[str]],
                  final_submit: bool) -> List[Tuple[str,str]]:
    data: List[Tuple[str,str]] = []

    # Hidden tokens/state
    data.append(("fbzx", fbzx))
    data.append(("fvv", carry_hidden.get("fvv", "1")))
    if "hl" in carry_hidden:                # language hint if present
        data.append(("hl", carry_hidden["hl"]))
    if "draftResponse" in carry_hidden:      # very important across pages
        data.append(("draftResponse", carry_hidden["draftResponse"]))
    if "partialResponse" in carry_hidden:    # present on some forms
        data.append(("partialResponse", carry_hidden["partialResponse"]))

    # Page history like "0", "0,1", ...
    data.append(("pageHistory", ",".join(str(i) for i in range(page_index + 1))))

    # Continue on intermediate pages; omit on final
    if not final_submit:
        data.append(("continue", "1"))

    # >>> KEY FIX: include ALL answers so far (cumulative) <<<
    data.extend(answers_to_tuples(cumulative_answers))

    return data

def submit_multipage_once() -> bool:
    with requests.Session() as sess:
        fbzx, hidden = fetch_first_page(sess)

        # Cumulative answers we’ll keep appending to
        cumulative: Dict[str, List[str]] = {}

        for page_idx, page_answers in enumerate(PAGES):
            # merge current page answers into cumulative
            for qid, opts in page_answers.items():
                if qid not in cumulative:
                    cumulative[qid] = []
                # extend without duplicates
                for v in opts:
                    if v not in cumulative[qid]:
                        cumulative[qid].append(v)

            final = (page_idx == len(PAGES) - 1)
            payload = build_payload(page_idx, fbzx, hidden, cumulative, final_submit=final)

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": VIEW_URL,
                "Origin": "https://docs.google.com",
            }
            r = sess.post(POST_URL, data=payload, headers=headers, timeout=30, allow_redirects=True)

            # Parse next page’s hidden fields (fresh draftResponse/partialResponse tokens, etc.)
            hidden = parse_hidden(r.text)

            ok_status = r.status_code in (200, 302)
            looks_thanks = (
                "formResponse" in r.url
                or "Your response has been recorded." in r.text
                or "ตอบของคุณได้ถูกบันทึกแล้ว" in r.text
            )

            print(f"[page {page_idx}{' final' if final else ''}] POST {r.status_code} → {r.url}")

            if final:
                ok = ok_status and looks_thanks
                if not ok:
                    Path("last_form_response.html").write_text(r.text, encoding="utf-8")
                    print("Saved response HTML to last_form_response.html")
                return ok
            else:
                if r.status_code != 200:
                    Path("last_intermediate.html").write_text(r.text, encoding="utf-8")
                    print("Saved intermediate HTML to last_intermediate.html")
                    return False

def submit_many(n=3, delay=(0.7, 1.6), seed=None):
    if seed is not None:
        random.seed(seed)
    ok = 0
    for _ in range(n):
        if submit_multipage_once():
            ok += 1
        time.sleep(random.uniform(*delay))
    print(f"Done: {ok}/{n} OK")

if __name__ == "__main__":
    submit_many(n=3)

