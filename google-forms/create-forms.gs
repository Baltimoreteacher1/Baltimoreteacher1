/**
 * Neft Math — Google Forms generator
 * ----------------------------------------------------------------------------
 * Creates, for every Grade 6 math lesson, three Google Forms:
 *   1. Notes     — guided notes (vocabulary, turn & talk, explore, connect)
 *   2. Practice  — every practice problem (not graded)
 *   3. Quiz      — an AUTOGRADED quiz (answer keys + per-question feedback)
 *
 * The question content is read from forms-data.json (built by build.py).
 *
 * ============================  HOW TO USE  ==================================
 * 1. Go to https://script.google.com  ->  New project.
 * 2. Delete the sample code, paste THIS file in, and Save.
 * 3. Run  createAllForms  once. Approve the permissions prompt
 *    (it needs to create Forms, Sheets, and Drive folders in YOUR account).
 * 4. Google stops scripts after ~6 minutes. This script is RESUMABLE:
 *    just keep clicking Run on createAllForms until the log says
 *    "ALL DONE". It picks up exactly where it left off.
 * 5. Open the spreadsheet "Neft Math — Forms Index" (created in your Drive)
 *    for clickable links to every form and its answer key.
 *
 * Other functions you can run:
 *   createFormsForLesson("6-3")  - build just one lesson's three forms
 *   resetProgress()              - start over (does NOT delete existing forms)
 * ===========================================================================
 */

// URL of the generated data file (public raw GitHub link).
var DATA_URL = "https://raw.githubusercontent.com/Baltimoreteacher1/baltimoreteacher1/claude/upbeat-shannon-n6fSc/google-forms/forms-data.json";

var ROOT_FOLDER_NAME = "Neft Math — Google Forms";
var INDEX_SHEET_NAME = "Neft Math — Forms Index";
var TIME_BUDGET_MS  = 4.5 * 60 * 1000;   // stop before Google's ~6 min cap

// ---------------------------------------------------------------------------

function createAllForms() {
  var start = Date.now();
  var data = loadData_();
  var lessons = data.lessons;
  var props = PropertiesService.getScriptProperties();
  var next = parseInt(props.getProperty("nextIndex") || "0", 10);

  if (next >= lessons.length) {
    Logger.log("ALL DONE — nothing left to build. Run resetProgress() to start over.");
    return;
  }

  var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
  var sheet = getIndexSheet_();

  for (var i = next; i < lessons.length; i++) {
    buildLesson_(lessons[i], root, sheet);
    props.setProperty("nextIndex", String(i + 1));
    Logger.log("Built %s/%s : lesson %s", i + 1, lessons.length, lessons[i].id);
    if (Date.now() - start > TIME_BUDGET_MS) {
      Logger.log("Time budget reached. Run createAllForms() again to continue (%s of %s done).",
                 i + 1, lessons.length);
      return;
    }
  }
  Logger.log("ALL DONE — built all %s lessons. See \"%s\" in your Drive.",
             lessons.length, INDEX_SHEET_NAME);
}

function createFormsForLesson(lessonId) {
  var data = loadData_();
  var lesson = null;
  for (var i = 0; i < data.lessons.length; i++) {
    if (data.lessons[i].id === lessonId) { lesson = data.lessons[i]; break; }
  }
  if (!lesson) { Logger.log("No lesson with id %s", lessonId); return; }
  var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
  buildLesson_(lesson, root, getIndexSheet_());
  Logger.log("Built lesson %s", lessonId);
}

function resetProgress() {
  PropertiesService.getScriptProperties().deleteProperty("nextIndex");
  Logger.log("Progress reset. createAllForms() will start from the first lesson.");
}

// ---------------------------------------------------------------------------

function buildLesson_(lesson, root, sheet) {
  var unitFolder = getOrCreateFolder_(root, "Unit " + (lesson.unit || "?"));
  var urls = {};
  for (var f = 0; f < lesson.forms.length; f++) {
    var spec = lesson.forms[f];
    var form = buildForm_(spec);
    DriveApp.getFileById(form.getId()).moveTo(unitFolder);
    urls[spec.key] = form.getPublishedUrl();
    sheet.appendRow([
      lesson.id, lesson.unit, lesson.lesson, lesson.standard,
      spec.key, spec.isQuiz ? "yes" : "no",
      form.getPublishedUrl(), form.getEditUrl()
    ]);
  }
  updateIndexJson_(root, lesson.id, urls);   // power the forms-index.html page
}

/**
 * Maintains forms-index.json in the root folder: { "<lessonId>": {notes,practice,quiz} }.
 * Download this file and drop it next to forms-index.html to activate the links.
 */
function updateIndexJson_(root, lessonId, urls) {
  var map = {};
  var it = root.getFilesByName("forms-index.json");
  var file = null;
  if (it.hasNext()) {
    file = it.next();
    try { map = JSON.parse(file.getBlob().getDataAsString()); } catch (e) { map = {}; }
  }
  map[lessonId] = urls;
  var json = JSON.stringify(map, null, 1);
  if (file) file.setContent(json);
  else root.createFile("forms-index.json", json, "application/json");
}

function buildForm_(spec) {
  var form = FormApp.create(spec.title);
  form.setDescription(spec.description || "");
  if (spec.isQuiz) form.setIsQuiz(true);
  try { form.setCollectEmail(true); } catch (e) {}  // identify students; ignore if account blocks it

  var items = spec.items || [];
  for (var i = 0; i < items.length; i++) {
    var it = items[i];
    switch (it.kind) {
      case "section":
        form.addSectionHeaderItem()
            .setTitle(it.title || "")
            .setHelpText(it.description || "");
        break;
      case "short":
        form.addTextItem()
            .setTitle(it.title || "")
            .setHelpText(it.help || "")
            .setRequired(!!it.required);
        break;
      case "paragraph":
        form.addParagraphTextItem()
            .setTitle(it.title || "")
            .setHelpText(it.help || "")
            .setRequired(!!it.required);
        break;
      case "mc":
        addMultipleChoice_(form, it, spec.isQuiz);
        break;
    }
  }
  return form;
}

function addMultipleChoice_(form, it, isQuiz) {
  var item = form.addMultipleChoiceItem();
  item.setTitle(it.title || "");
  item.setRequired(!!it.required);

  var graded = isQuiz && it.correctIndex !== null &&
               it.correctIndex !== undefined && (it.points || 0) > 0;

  if (graded) {
    var choices = [];
    for (var i = 0; i < it.choices.length; i++) {
      choices.push(item.createChoice(String(it.choices[i]), i === it.correctIndex));
    }
    item.setChoices(choices);
    item.setPoints(it.points);
    if (it.explanation) {
      var fb = FormApp.createFeedback().setText(it.explanation).build();
      item.setFeedbackForIncorrect(fb);
      item.setFeedbackForCorrect(fb);
    }
  } else {
    var vals = [];
    for (var j = 0; j < it.choices.length; j++) vals.push(String(it.choices[j]));
    item.setChoiceValues(vals);
  }
}

// ---------------------------------------------------------------------------

function loadData_() {
  var resp = UrlFetchApp.fetch(DATA_URL, { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) {
    throw new Error("Could not fetch data (" + resp.getResponseCode() +
                    "). Check DATA_URL at the top of the script.");
  }
  return JSON.parse(resp.getContentText());
}

function getOrCreateFolder_(parent, name) {
  var it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}

function getIndexSheet_() {
  var props = PropertiesService.getScriptProperties();
  var id = props.getProperty("indexSheetId");
  var ss;
  if (id) {
    try { ss = SpreadsheetApp.openById(id); } catch (e) { ss = null; }
  }
  if (!ss) {
    ss = SpreadsheetApp.create(INDEX_SHEET_NAME);
    var sh = ss.getSheets()[0];
    sh.appendRow(["lesson_id", "unit", "lesson", "standard",
                  "form", "graded", "live_url", "edit_url"]);
    sh.setFrozenRows(1);
    props.setProperty("indexSheetId", ss.getId());
  }
  return ss.getSheets()[0];
}
