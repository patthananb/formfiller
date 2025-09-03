# pip install requests
import re
import time
import random
import requests
from pathlib import Path
from typing import Dict, List, Tuple

# ==================== FORM CONFIG ====================
FORM_ID = "1FAIpQLSclacqDbfy4PFIYBATKqWVJsWnpUe9WH_U15P92fjpTl_KDWg"
VIEW_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/viewform"
POST_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"

# Question entry IDs (from your mapping)
ENTRY_FACULTY        = "entry.2139451852"   # คณะ (Faculty)
ENTRY_YEAR           = "entry.1212729351"   # ชั้นปี
ENTRY_VISION_STATUS  = "entry.233448731"    # ท่านมีปัญหาสายตาหรือไม่
ENTRY_AIDS           = "entry.663819695"    # ท่านใช้เครื่องช่วยในการมองเห็นหรือไม่ (checkbox)
ENTRY_PHONE_USE      = "entry.850765298"    # ระยะเวลาเฉลี่ยที่ใช้สมาร์ทโฟนต่อวัน
ENTRY_PC_USE         = "entry.961423934"    # ระยะเวลาเฉลี่ยที่ใช้คอมพิวเตอร์/โน้ตบุ๊กต่อวัน
ENTRY_ACTIVITIES     = "entry.1127393595"   # กิจกรรมหลักในการใช้งานสมาร์ทโฟน/คอมพิวเตอร์ (multi)
ENTRY_BREAK_HABIT    = "entry.2121588"      # ท่านพักสายตาเป็นระยะหรือไม่ (เสริม)

# ==================== OPTIONS ====================
FACULTIES = [
    "วิศวกรรมศาสตร์",
    "ครุศาสตร์อุตสาหกรรม",
    "วิทยาลัยเทคโนโลยีอุตสาหกรรม",
    "วิทยาศาสตร์ประยุกต์",
    "สถาปัตยกรรมและการออกแบบ",
    "บริหารธุรกิจ",
    "วิทยาลัยนานาชาติ",
    "คณะพัฒนาธุรกิจและอุตสาหกรรม",
    "Other:",
]
YEARS = ["ปี 1", "ปี 2", "ปี 3", "ปี 4", "ปี 4 ขึ้นไป"]

VISION_STATUS = ["ไม่มีปัญหา", "สายตาสั้น", "สายตายาว", "สายตาเอียง", "Other:"]

AIDS = ["แว่นสายตา", "คอนแทคเลนส์", "ไม่ใช้"]  # checkbox list

PHONE_USE = ["น้อยกว่า 1 ชั่วโมง", "1–3 ชั่วโมง", "3–5 ชั่วโมง", "5–8 ชั่วโมง", "มากกว่า 8 ชั่วโมง"]
PC_USE    = ["น้อยกว่า 1 ชั่วโมง", "1–3 ชั่วโมง", "3–5 ชั่วโมง", "5–8 ชั่วโมง", "มากกว่า 8 ชั่วโมง"]

ACTIVITIES = [
    "เรียนออนไลน์/ทำงานที่เกี่ยวกับการเรียน",
    "ทำงานพิเศษ/โปรเจกต์",
    "ดูหนัง/เล่นเกม/โซเชียลมีเดีย",
    "Other:",
]

BREAK_HABIT = ["พักสม่ำเสมอ", "พักบ้างเป็นบางครั้ง", "ไม่พักเลย"]

# Matches “Other/อื่นๆ/その他” variants to exclude by default
OTHER_PAT = re.compile(
    r"^\s*(?:__other_option__|other|others|อื่น|อื่นๆ|อื่น ๆ|その他)\s*$",
    re.IGNORECASE
)

# ==================== HELPERS ====================
def filter_other(options: List[str]) -> List[str]:
    """Remove any 'Other/อื่นๆ/...' placeholders unless you intend to fill text fields."""
    return [o for o in options if not OTHER_PAT.match(o or "")]

def parse_hidden(html: str) -> Dict[str, str]:
    """Collect tokens and hidden inputs required for multi-page submissions."""
    hidden = {}
    for name, value in re.findall(
        r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]*value="([^"]*)"', html
    ):
        hidden[name] = value
    return hidden

def fetch_first_page(sess: requests.Session) -> Tuple[str, Dict[str, str]]:
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

def answers_to_tuples(answers: Dict[str, List[str]]) -> List[Tuple[str, str]]:
    """Turn {'entry.X': ['A','B']} into repeated (key, value) tuples."""
    tuples: List[Tuple[str, str]] = []
    for qid, opts in answers.items():
        vals = filter_other(opts or [])
        for v in vals:
            tuples.append((qid, v))
    return tuples

def build_payload(
    page_index: int,
    fbzx: str,
    carry_hidden: Dict[str, str],
    cumulative_answers: Dict[str, List[str]],
    final_submit: bool
) -> List[Tuple[str, str]]:
    """Assemble one POST payload for current page, including cumulative answers."""
    data: List[Tuple[str, str]] = []
    # Hidden state/tokens
    data.append(("fbzx", fbzx))
    data.append(("fvv", carry_hidden.get("fvv", "1")))
    if "hl" in carry_hidden:
        data.append(("hl", carry_hidden["hl"]))
    if "draftResponse" in carry_hidden:
        data.append(("draftResponse", carry_hidden["draftResponse"]))
    if "partialResponse" in carry_hidden:
        data.append(("partialResponse", carry_hidden["partialResponse"]))

    # Page history like "0", "0,1", ...
    data.append(("pageHistory", ",".join(str(i) for i in range(page_index + 1))))

    # Continue on intermediate pages; omit on final
    if not final_submit:
        data.append(("continue", "1"))

    # Include ALL answers so far (critical for multipage forms)
    data.extend(answers_to_tuples(cumulative_answers))
    return data

def choose_one(options: List[str]) -> str:
    return random.choice(options)

def make_random_pages() -> List[Dict[str, List[str]]]:
    """Create randomized answers for all pages with your constraints enforced."""
    # --- Page 0 ---
    faculty = choose_one(FACULTIES)
    year = choose_one(YEARS)
    page0 = {
        ENTRY_FACULTY: [faculty],  # คณะ
        ENTRY_YEAR: [year],        # ชั้นปี
    }

    # --- Page 1 ---
    vision = choose_one(VISION_STATUS)  # ท่านมีปัญหาสายตาหรือไม่
    aids: List[str] = []

    # Rule: If 'ไม่มีปัญหา' or 'Other', force aids to 'ไม่ใช้' only
    if vision == "ไม่มีปัญหา" or OTHER_PAT.match(vision or ""):
        aids = ["ไม่ใช้"]
    else:
        # Otherwise either no aids or some combination (but if 'ไม่ใช้' present, it's the only one)
        roll = random.random()
        if roll < 0.5:
            aids = ["ไม่ใช้"]
        elif roll < 0.8:
            aids = [choose_one(["แว่นสายตา", "คอนแทคเลนส์"])]
        else:
            aids = ["แว่นสายตา", "คอนแทคเลนส์"]

    # If 'ไม่ใช้' is present, it must be the only selected item
    if "ไม่ใช้" in aids:
        aids = ["ไม่ใช้"]

    page1 = {
        ENTRY_VISION_STATUS: [vision],
        ENTRY_AIDS: aids,
    }

    # --- Page 2 ---
    phone = choose_one(PHONE_USE)
    pc = choose_one(PC_USE)

    # Activities: choose 1–3 (but exclude Other)
    acts_pool = filter_other(ACTIVITIES)
    k = random.randint(1, min(3, len(acts_pool)))
    activities = random.sample(acts_pool, k=k)

    page2 = {
        ENTRY_PHONE_USE: [phone],
        ENTRY_PC_USE: [pc],
        ENTRY_ACTIVITIES: activities,
    }

    # --- Page 3 (final) ---
    page3 = {
        ENTRY_BREAK_HABIT: [choose_one(BREAK_HABIT)],
    }

    return [page0, page1, page2, page3]

# ==================== SUBMIT LOGIC ====================
def submit_multipage_once() -> bool:
    with requests.Session() as sess:
        fbzx, hidden = fetch_first_page(sess)

        # Fresh randomized answers for this run
        pages = make_random_pages()

        # Cumulative answers across pages
        cumulative: Dict[str, List[str]] = {}

        for page_idx, page_answers in enumerate(pages):
            # Merge current page into cumulative (no duplicates)
            for qid, opts in page_answers.items():
                if qid not in cumulative:
                    cumulative[qid] = []
                for v in opts:
                    if v not in cumulative[qid]:
                        cumulative[qid].append(v)

            final = (page_idx == len(pages) - 1)
            payload = build_payload(
                page_index=page_idx,
                fbzx=fbzx,
                carry_hidden=hidden,
                cumulative_answers=cumulative,
                final_submit=final
            )

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": VIEW_URL,
                "Origin": "https://docs.google.com",
            }
            r = sess.post(
                POST_URL, data=payload, headers=headers, timeout=30, allow_redirects=True
            )

            # Update hidden tokens from the response for the next step
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
    """Submit multiple randomized responses with a small random delay between them."""
    if seed is not None:
        random.seed(seed)
    ok = 0
    for i in range(n):
        print(f"--- Submission {i+1}/{n} ---")
        if submit_multipage_once():
            ok += 1
        time.sleep(random.uniform(*delay))
    print(f"Done: {ok}/{n} OK")

# ==================== CLI ====================
if __name__ == "__main__":
    # Example: 3 randomized submissions with 0.7–1.6s delay
    submit_many(n=3, delay=(0.7, 1.6))
