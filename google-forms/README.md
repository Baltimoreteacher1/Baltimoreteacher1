# Neft Math — Google Forms for every lesson

Auto-generates **3 Google Forms per lesson** for all **74** Grade 6 math lessons
(units 1–10), straight from the lesson `config.json` files in
[`neft-classroom-html-activities`](https://github.com/Baltimoreteacher1/neft-classroom-html-activities).

| Form | Graded? | What's in it |
| ---- | ------- | ------------ |
| **Notes** | No | Content/language objectives, vocabulary cloze fill-ins, Turn & Talk, Explore, Connect |
| **Practice** | No | Every practice problem in its natural form (multiple choice, sorting, matching, tables, error analysis, open response) |
| **Quiz** | **Yes — autograded** | Multiple-choice problems + matching / drag-sort / balance-scale converted to multiple choice + the exit ticket. Each question has an answer key, points, and feedback that shows the explanation |

**Totals:** 74 lessons → **222 forms**, with **1,294 autograded quiz questions**.

---

## Files

| File | Purpose |
| ---- | ------- |
| `create-forms.gs` | Google Apps Script that builds all the forms in your Google Drive |
| `forms-data.json` | The generated form content the script reads (1.3 MB) |
| `question-bank.csv` | Flat, human-readable export of every question + answer (open in Sheets/Excel) |
| `forms-index.html` | Neft-styled landing page linking every lesson's Notes / Practice / Quiz |
| `build.py` | Regenerates `forms-data.json`, `question-bank.csv`, and `forms-index.html` |

---

## Create the forms (the Apps Script way — recommended)

This is the only way to get **true quiz autograding** (answer keys + feedback),
and it builds all 222 forms automatically into your own Drive.

1. Open **https://script.google.com** → **New project**.
2. Delete the sample code, paste in the contents of **`create-forms.gs`**, **Save**.
3. Run the **`createAllForms`** function. Approve the permission prompt
   (it creates Forms, a Sheet, and Drive folders in *your* account).
4. Google stops a script after ~6 minutes. **This script is resumable** —
   just keep clicking **Run** on `createAllForms` until the log says
   **"ALL DONE"**. It continues exactly where it left off each time
   (expect to run it a handful of times for all 74 lessons).
5. Open the spreadsheet **"Neft Math — Forms Index"** that appears in your
   Drive for clickable links (live URL + edit URL) to every form.

The forms are organized in Drive as:
`Neft Math — Google Forms / Unit N / <lesson> <Notes|Practice|Quiz>`.

### Handy functions
- `createFormsForLesson("6-3")` — build just one lesson's three forms.
- `resetProgress()` — start the batch over (does **not** delete forms already made).

> **Note:** `forms-data.json` is fetched from this repo's raw URL, set in the
> `DATA_URL` variable at the top of `create-forms.gs`. If you move the file or
> branch, update that one line.

---

## Landing page (`forms-index.html`)

A searchable, Neft-styled page that lists all 74 lessons (grouped by unit) with
**Notes / Practice / Quiz** buttons for each. It already has every lesson's
title and standard baked in, so it renders immediately — the buttons just
need URLs to point at.

To activate the links:
1. Run `createAllForms` (above). As it builds, the script writes a file named
   **`forms-index.json`** into the `Neft Math — Google Forms` folder in your Drive.
2. Download that `forms-index.json` and place it **next to `forms-index.html`**.
3. Open the page (or deploy the folder to Cloudflare Pages / GitHub Pages).
   The banner turns green and every button links straight to its live form.

Until the JSON is present the buttons stay greyed out — the page is still a
useful, printable map of the whole course.

---

## Just want the questions? (the data way)

`question-bank.csv` has every question, choices, correct answer, points, and
explanation in plain columns — import it into Sheets, a quiz tool, or a Forms
add-on of your choice. `forms-data.json` is the same content structured by form.

---

## Regenerating after lessons change

```bash
# clone the lessons repo, then:
python3 build.py /path/to/neft-classroom-html-activities/lessons
```

This rewrites `forms-data.json` and `question-bank.csv`. Re-running
`createAllForms` (after `resetProgress`) rebuilds the forms from the new data.
