#!/usr/bin/env python3
"""
Build Google Forms specs from Neft lesson configs.

Reads every lessons/<id>/config.json from the neft-classroom-html-activities
repo and emits, per lesson, three form specifications:

  - notes     : guided-notes form (objectives, vocabulary cloze, turn & talk,
                explore, connect)  -- not a quiz
  - practice  : every practice problem in its natural form              -- not a quiz
  - quiz      : an autograded quiz (multiple-choice + matching/drag-sort/
                balance-scale converted to multiple-choice + exit ticket)

Outputs:
  forms-data.json   -> consumed by the Apps Script generator (create-forms.gs)
  question-bank.csv -> flat human-readable export of every question

Usage:
  python3 build.py /path/to/neft-classroom-html-activities/lessons
"""
import json, glob, os, sys, csv, random

random.seed(42)  # stable distractor ordering between runs


# ---------- form-item helpers -------------------------------------------------

def section(title, description=""):
    return {"kind": "section", "title": title, "description": description}

def paragraph(title, help=""):
    return {"kind": "paragraph", "title": title, "help": help, "required": False}

def short(title, help=""):
    return {"kind": "short", "title": title, "help": help, "required": False}

def mc(title, choices, correct_index=None, points=0, explanation="", required=False):
    """A multiple-choice item. If correct_index is set and points>0 it is graded."""
    return {
        "kind": "mc",
        "title": title,
        "choices": list(choices),
        "correctIndex": correct_index,
        "points": points,
        "explanation": explanation or "",
        "required": required,
    }


# ---------- converters: non-MC practice types -> graded MC --------------------

def pair_prompt_answer(pair):
    """Return (prompt, answer) for a matching/matching-game pair, key-name agnostic."""
    prompt = pair.get("term") or pair.get("situation") or pair.get("left")
    answer = pair.get("match") or pair.get("equation") or pair.get("right")
    if prompt is None or answer is None:               # fall back to value order
        vals = list(pair.values())
        prompt = prompt or (vals[0] if vals else "")
        answer = answer or (vals[1] if len(vals) > 1 else "")
    return str(prompt), str(answer)


def matching_to_mc(item, points):
    """One graded MC per pair: 'Match X -> ?' with all answers as choices."""
    pairs = item.get("pairs", [])
    parsed = [pair_prompt_answer(p) for p in pairs]
    answers = [a for _, a in parsed]
    out = []
    if len(answers) < 2:
        return out
    label = item.get("label", "Match each item to its partner.")
    for prompt, answer in parsed:
        choices = answers[:]
        random.shuffle(choices)
        out.append(mc(f"{label}\n\n{prompt}", choices,
                      correct_index=choices.index(answer), points=points))
    return out


def dragsort_to_mc(item, points):
    """One graded MC per item: 'Which category does X belong to?'."""
    cats = item.get("categories", [])
    labels = [c.get("label", c.get("id", "")) for c in cats]
    id_to_label = {c.get("id"): c.get("label", c.get("id", "")) for c in cats}
    if len(labels) < 2:
        return []                                      # degenerate single bucket
    instr = item.get("instructions", "Sort into the correct category.")
    out = []
    for it in item.get("items", []):
        if not isinstance(it, dict):
            continue
        correct = id_to_label.get(it.get("category"))
        if correct not in labels:
            continue
        out.append(mc(f"{instr}\n\nWhere does this belong?  {it.get('text','')}",
                      labels, correct_index=labels.index(correct), points=points))
    return out


def balance_to_mc(item, points):
    """One graded MC per row: 'Is this balanced?'."""
    instr = item.get("instructions", "Is each equation balanced?")
    choices = ["Balanced ⚖️", "Not balanced"]
    out = []
    for it in item.get("items", []):
        correct = 0 if it.get("balanced") else 1
        expl = it.get("correction", "")
        out.append(mc(f"{instr}\n\n{it.get('left','')}   ↔   {it.get('right','')}",
                      choices, correct_index=correct, points=points, explanation=expl))
    return out


# ---------- practice form: every item in natural (ungraded) form --------------

def _text(x):
    """Display text for a drag-sort/list item that may be a str or a dict."""
    if isinstance(x, dict):
        return x.get("text") or x.get("label") or str(next(iter(x.values()), ""))
    return str(x)


def first_cell(row):
    """The 'given'/prompt cell of a fill-table row (answers stay hidden)."""
    if isinstance(row, dict):
        for k in ("given", "problem", "expression", "situation", "question",
                  "inequality", "equation", "scenario", "dataSet", "shape",
                  "feature", "preference"):
            if row.get(k):
                return str(row[k])
        return str(next(iter(row.values()), ""))
    if isinstance(row, list):
        return str(row[0]) if row else ""
    return str(row)


def practice_item_to_natural(item):
    t = item.get("type")
    if t == "multiple-choice":
        return [mc(item.get("stem", ""), item.get("choices", []))]
    if t in ("matching", "matching-game"):
        label = item.get("label", "Match each item to its partner.")
        lines = [f"  • {p}   →   ?" for p, _ in
                 (pair_prompt_answer(x) for x in item.get("pairs", []))]
        return [paragraph(label, "Write each match:\n" + "\n".join(lines))]
    if t == "drag-sort":
        cats = ", ".join(c.get("label", "") for c in item.get("categories", []))
        items = "\n".join(f"  • {_text(x)}" for x in item.get("items", []))
        return [paragraph(item.get("instructions", "Sort each item."),
                          f"Categories: {cats}\n\n{items}")]
    if t == "fill-table":
        cols = item.get("columns", [])
        prompts = [first_cell(r) for r in item.get("rows", [])]
        prompts = [p for p in prompts if p]
        body = "Columns: " + " | ".join(cols) + "\n\nComplete each row:\n" + \
               "\n".join(f"  • {p}" for p in prompts)
        return [paragraph(item.get("label", "Complete the table."), body)]
    if t == "error-analysis":
        steps = "\n".join(f"  {i+1}. {s.get('label','')}: {s.get('work','')}"
                          for i, s in enumerate(item.get("workedExample", [])))
        return [paragraph(item.get("title", "Find and fix the error."),
                          steps + "\n\nFind the mistake and write the correct work.")]
    if t == "open-response":
        return [paragraph(item.get("prompt") or item.get("stem") or "Explain your reasoning.",
                          item.get("sentenceFrame", ""))]
    if t == "number-line":
        return [paragraph(item.get("label", item.get("instructions", "Use the number line.")),
                          item.get("instructions", ""))]
    if t == "coordinate-grid":
        return [paragraph("Coordinate grid: " + item.get("instructions", ""),
                          f"x: {item.get('xLabel','')}  |  y: {item.get('yLabel','')}")]
    if t == "bar-model":
        return [short(item.get("label", "") + "  " + item.get("questionText", ""))]
    if t == "balance-scale":
        lines = "\n".join(f"  • {x.get('left','')}   ↔   {x.get('right','')}"
                          for x in item.get("items", []))
        return [paragraph(item.get("instructions", "Is each side balanced?"),
                          lines + "\n\nFor each: balanced or not? If not, correct it.")]
    # unknown -> best effort
    return [paragraph(item.get("stem") or item.get("label") or item.get("prompt")
                      or item.get("instructions") or f"Problem ({t})",
                      item.get("instructions", ""))]


def _ensure_titles(items):
    """Guarantee no item has an empty title (Google Forms rejects empty titles)."""
    for it in items:
        if not str(it.get("title", "")).strip():
            it["title"] = "Question"
    return items


# ---------- per-lesson builder ------------------------------------------------

PRACTICE_LEVELS = ["optional", "approaching", "onLevel", "extending"]
LEVEL_TITLE = {"optional": "Warm-up", "approaching": "Building Up",
               "onLevel": "On Level", "extending": "Challenge"}


def iter_practice(cfg):
    """Yield (level, item) over all practice items in a stable order."""
    p = cfg.get("practice", {})
    if not isinstance(p, dict):
        return
    for lvl in PRACTICE_LEVELS:
        for it in p.get(lvl, []) or []:
            if isinstance(it, dict):
                yield lvl, it


def build_notes_form(cfg):
    title = cfg["title"]
    lid = cfg["lessonId"]
    emoji = cfg.get("themeEmoji", "")
    desc = (f"Guided notes for Lesson {lid}: {title}  (Standard {cfg.get('standard','')})\n\n"
            f"Content objective: {cfg.get('contentObjective','')}\n"
            f"Language objective: {cfg.get('languageObjective','')}")
    items = []

    vocab = cfg.get("vocabulary", []) or []
    if vocab:
        items.append(section("\U0001F4D8 Vocabulary",
                             "Fill in each blank using what you learn this lesson."))
        for v in vocab:
            cloze = v.get("cloze") or f"{v.get('term','')}: ___"
            items.append(short(cloze, "Term: " + v.get("term", "")))

    tat = cfg.get("turnAndTalk", []) or []
    if tat:
        items.append(section("\U0001F5E3️ Turn & Talk", ""))
        for t in tat:
            help = ""
            stems = t.get("stems") or []
            if stems:
                help = "Sentence starters:\n" + "\n".join(f"  • {s}" for s in stems)
            items.append(paragraph(t.get("question", ""), help))

    explore = cfg.get("explore", {})
    if isinstance(explore, dict) and explore.get("discourse"):
        d = explore["discourse"]
        items.append(section("\U0001F50D Explore", explore.get("instructions", "")))
        items.append(paragraph(d.get("prompt", "Explain your thinking."),
                               d.get("sentenceFrame", "")))

    connect = cfg.get("connect", {})
    if isinstance(connect, dict) and (connect.get("promptQuestion") or connect.get("scenario")):
        items.append(section("\U0001F517 Connect", connect.get("scenario", "")))
        items.append(paragraph(connect.get("promptQuestion", "Apply what you learned."),
                               connect.get("prompt", "")))

    return {"key": "notes", "title": f"{emoji} {lid} Notes — {title}".strip(),
            "description": desc, "isQuiz": False, "items": items}


def build_practice_form(cfg):
    title = cfg["title"]
    lid = cfg["lessonId"]
    emoji = cfg.get("themeEmoji", "")
    items = []
    last_level = None
    for lvl, it in iter_practice(cfg):
        if lvl != last_level:
            items.append(section(LEVEL_TITLE.get(lvl, lvl.title()), ""))
            last_level = lvl
        items.extend(practice_item_to_natural(it))
    return {"key": "practice",
            "title": f"{emoji} {lid} Practice — {title}".strip(),
            "description": f"Practice problems for Lesson {lid}: {title}. "
                           f"Work through each one — this form is not graded.",
            "isQuiz": False, "items": items}


def build_quiz_form(cfg):
    title = cfg["title"]
    lid = cfg["lessonId"]
    emoji = cfg.get("themeEmoji", "")
    PTS = 1
    items = []

    # direct multiple-choice practice problems
    for lvl, it in iter_practice(cfg):
        if it.get("type") == "multiple-choice" and "correctIndex" in it:
            items.append(mc(it.get("stem", ""), it.get("choices", []),
                            correct_index=it["correctIndex"], points=PTS,
                            explanation=it.get("explanation", ""), required=True))

    # converted types
    for lvl, it in iter_practice(cfg):
        t = it.get("type")
        if t in ("matching", "matching-game"):
            items.extend(matching_to_mc(it, PTS))
        elif t == "drag-sort":
            items.extend(dragsort_to_mc(it, PTS))
        elif t == "balance-scale":
            items.extend(balance_to_mc(it, PTS))

    # exit ticket
    et = cfg.get("reflect", {}).get("exitTicket")
    if isinstance(et, dict) and "correctIndex" in et:
        items.append(mc("Exit Ticket: " + et.get("stem", ""), et.get("choices", []),
                        correct_index=et["correctIndex"], points=PTS,
                        explanation=et.get("explanation", ""), required=True))

    for it in items:                                   # all quiz items required
        it["required"] = True

    total = sum(i.get("points", 0) for i in items)
    return {"key": "quiz",
            "title": f"{emoji} {lid} Quiz — {title}".strip(),
            "description": f"Autograded quiz for Lesson {lid}: {title} "
                           f"(Standard {cfg.get('standard','')}). "
                           f"{len(items)} questions, {total} points.",
            "isQuiz": True, "items": items}


# ---------- index page --------------------------------------------------------

INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Google Forms — Index</title>
<style>
body{margin:0;background:#f7f4ec;color:#21313f;font-family:Calibri,"Segoe UI",system-ui,sans-serif;}
.wrap{max-width:920px;margin:0 auto;padding:32px 20px;}
h1{font-family:Outfit,system-ui,sans-serif;color:#12355b;margin:0 0 6px;}
.sub{color:#5f6f80;margin:0 0 18px;}
.banner{border-radius:12px;padding:12px 16px;margin:0 0 20px;font-size:14px;}
.banner.warn{background:#fef0d8;border:1px solid #f2c15b;color:#7a5410;}
.banner.ok{background:#dff2ee;border:1px solid #1fa6a2;color:#0f6f6b;}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 18px;}
input[type=search]{flex:1;min-width:200px;padding:9px 12px;border:1px solid #d7e2ed;border-radius:8px;font-size:15px;}
.unit-group{background:#fff;border:1px solid #d7e2ed;border-radius:12px;padding:16px 20px;margin:0 0 16px;}
.unit-group h2{color:#1fa6a2;margin:0 0 10px;font-family:Outfit,system-ui,sans-serif;}
.row{display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #eef3f8;flex-wrap:wrap;}
.row:last-child{border-bottom:0;}
.name{flex:1;min-width:220px;font-weight:600;color:#12355b;}
.std{color:#5f6f80;font-weight:400;font-size:13px;margin-left:6px;}
.tag{display:inline-block;font-size:11px;font-weight:700;border-radius:999px;padding:1px 8px;margin-left:6px;}
.tag-core{background:#dff2ee;color:#1fa6a2;border:1px solid #1fa6a2;}
.tag-flagship{background:#fef0d8;color:#9a6b12;border:1px solid #f2c15b;}
.btns{display:flex;gap:6px;}
.btn{font-size:13px;font-weight:700;border-radius:8px;padding:5px 12px;text-decoration:none;border:1px solid;white-space:nowrap;}
.btn-notes{color:#1fa6a2;border-color:#1fa6a2;background:#f1faf8;}
.btn-practice{color:#12355b;border-color:#9bb6d2;background:#f1f6fb;}
.btn-quiz{color:#9a6b12;border-color:#f2c15b;background:#fef7e8;}
.btn:hover{filter:brightness(0.96);}
.btn.off{color:#aab4bf;border-color:#dde5ec;background:#f4f7fa;cursor:not-allowed;}
.legend{color:#5f6f80;font-size:14px;margin:0 0 16px;}
code{background:#eef3f8;padding:1px 5px;border-radius:4px;}
</style>
</head>
<body>
<div class="wrap">
  <h1>Google Forms</h1>
  <p class="sub">Notes, Practice, and autograded Quiz forms for all __COUNT__ Grade 6 math lessons.</p>
  <div id="banner" class="banner warn">
    Buttons are inactive until you generate the forms. Run <code>create-forms.gs</code>
    in Google Apps Script, download the <code>forms-index.json</code> it writes to your Drive,
    and place it next to this page. The buttons will then link straight to each form.
  </div>
  <p class="legend"><span class="tag tag-core">Core</span> standard lesson &nbsp;
     <span class="tag tag-flagship">Flagship</span> mission-based lesson</p>
  <div class="controls"><input id="q" type="search" placeholder="Filter by lesson name, number, or standard…" /></div>
  <div id="list"></div>
</div>
<script>
const LESSONS = __LESSONS__;
let URLS = {};
function render(filter){
  filter = (filter||"").toLowerCase();
  const byUnit = {};
  LESSONS.forEach(L => {
    const hay = (L.id+" "+L.title+" "+L.standard).toLowerCase();
    if(filter && hay.indexOf(filter)<0) return;
    (byUnit[L.unit] = byUnit[L.unit] || []).push(L);
  });
  const list = document.getElementById("list");
  list.innerHTML = "";
  Object.keys(byUnit).map(Number).sort((a,b)=>a-b).forEach(u => {
    const sec = document.createElement("section");
    sec.className = "unit-group";
    sec.innerHTML = "<h2>Unit "+u+"</h2>";
    byUnit[u].forEach(L => {
      const u3 = URLS[L.id] || {};
      const btn = (key,label,cls) => u3[key]
        ? '<a class="btn '+cls+'" target="_blank" rel="noopener" href="'+u3[key]+'">'+label+'</a>'
        : '<span class="btn '+cls+' off" title="Run the generator to activate">'+label+'</span>';
      const tag = L.flagship
        ? '<span class="tag tag-flagship">Flagship</span>'
        : '<span class="tag tag-core">Core</span>';
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML = '<span class="name">'+L.id+' — '+L.title+' '+tag+
        '<span class="std">'+L.standard+'</span></span>'+
        '<span class="btns">'+btn("notes","Notes","btn-notes")+
        btn("practice","Practice","btn-practice")+
        btn("quiz","Quiz","btn-quiz")+'</span>';
      sec.appendChild(row);
    });
    list.appendChild(sec);
  });
}
fetch("./forms-index.json").then(r => r.ok ? r.json() : null).then(j => {
  if(j){ URLS = j;
    const b = document.getElementById("banner");
    const n = Object.keys(URLS).length;
    b.className = "banner ok";
    b.innerHTML = "Linked to your forms — "+n+" lessons connected. Click any button to open the form.";
  }
  render("");
}).catch(() => render(""));
document.getElementById("q").addEventListener("input", e => render(e.target.value));
</script>
</body>
</html>
"""


def write_index_html(lessons, out_dir):
    meta = [{"id": L["id"], "unit": L["unit"], "lesson": L["lesson"],
             "title": L["title"], "standard": L["standard"],
             "flagship": "flagship" in L["id"]} for L in lessons]
    html = (INDEX_TEMPLATE
            .replace("__COUNT__", str(len(lessons)))
            .replace("__LESSONS__", json.dumps(meta, ensure_ascii=False)))
    for name in ("forms-index.html", "index.html"):   # index.html = Pages root
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(html)


# ---------- driver ------------------------------------------------------------

def main():
    lessons_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/nca/lessons"
    out_dir = os.path.dirname(os.path.abspath(__file__))
    lessons = []
    for cfgpath in sorted(glob.glob(os.path.join(lessons_dir, "*", "config.json"))):
        cfg = json.load(open(cfgpath, encoding="utf-8"))
        if "lessonId" not in cfg:
            continue
        forms = [build_notes_form(cfg), build_practice_form(cfg), build_quiz_form(cfg)]
        for fm in forms:
            _ensure_titles(fm["items"])
        lessons.append({
            "id": cfg["lessonId"],
            "unit": cfg.get("unit"),
            "lesson": cfg.get("lesson"),
            "standard": cfg.get("standard", ""),
            "title": cfg.get("title", ""),
            "forms": forms,
        })

    # sort by unit then lesson, flagships after their base lesson
    def sortkey(L):
        return (L["unit"] or 0, L["lesson"] or 0, "flagship" in L["id"])
    lessons.sort(key=sortkey)

    data = {"meta": {"generator": "neft google-forms/build.py",
                     "lessonCount": len(lessons)},
            "lessons": lessons}
    with open(os.path.join(out_dir, "forms-data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    # flat CSV question bank
    with open(os.path.join(out_dir, "question-bank.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lesson_id", "form", "graded", "kind", "question",
                    "choices", "correct_answer", "points", "explanation"])
        for L in lessons:
            for form in L["forms"]:
                for it in form["items"]:
                    if it["kind"] == "section":
                        continue
                    choices = it.get("choices", [])
                    ci = it.get("correctIndex")
                    correct = choices[ci] if (ci is not None and choices and ci < len(choices)) else ""
                    w.writerow([L["id"], form["key"], "yes" if form["isQuiz"] else "no",
                                it["kind"], it.get("title", "").replace("\n", " / "),
                                " | ".join(choices), correct,
                                it.get("points", 0), it.get("explanation", "").replace("\n", " ")])

    write_index_html(lessons, out_dir)

    # summary
    nf = sum(len(L["forms"]) for L in lessons)
    nq = sum(len(f["items"]) for L in lessons for f in L["forms"] if f["isQuiz"])
    graded = sum(1 for L in lessons for f in L["forms"] if f["isQuiz"]
                 for it in f["items"] if it.get("points", 0) > 0)
    print(f"lessons: {len(lessons)}")
    print(f"forms:   {nf}  (notes + practice + quiz per lesson)")
    print(f"quiz questions: {nq}  (autograded MC: {graded})")
    print(f"wrote: forms-data.json, question-bank.csv, forms-index.html")


if __name__ == "__main__":
    main()
