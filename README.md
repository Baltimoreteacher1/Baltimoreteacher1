# Neft Hub

**Mr. Neft** — Grade 6 Math Teacher | BCPS | Building interactive learning tools with code + AI

---

## Live Sites

| Site                     | URL                                                                                                     | Purpose                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| **Neft Hub**             | [neft-teacher-app-library.pages.dev](https://neft-teacher-app-library.pages.dev)                        | Central student app library and landing page             |
| **Classroom Activities** | [neft-classroom-html-activities.pages.dev](https://neft-classroom-html-activities.pages.dev)            | All math, ESOL, and classroom activities in one place    |
| **Neft Teacher**         | [eduwonderlab.vercel.app](https://eduwonderlab.vercel.app)                                              | Lesson plan and notebook generation                      |
| **Data Studio**          | [data-studio-3cb.pages.dev](https://data-studio-3cb.pages.dev)                                          | Classroom data analysis and visualization                |
| **Lesson Forms**         | [baltimoreteacher1.github.io/Baltimoreteacher1](https://baltimoreteacher1.github.io/Baltimoreteacher1/) | Notes, Practice, and Quiz Google Forms for all 74 lessons |

---

## Open-Source Repos

| Repo                                                                                                  | Purpose                                                    |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [neft-classroom-html-activities](https://github.com/Baltimoreteacher1/neft-classroom-html-activities) | All math, ESOL, and classroom HTML activities consolidated |
| [neft-quiz-warmup-engine](https://github.com/Baltimoreteacher1/neft-quiz-warmup-engine)               | Quiz and warmup generation engine                          |
| [neft-esol-reading](https://github.com/Baltimoreteacher1/neft-esol-reading)                           | ESOL reading comprehension activities                      |
| [neft-correlation-playground](https://github.com/Baltimoreteacher1/neft-correlation-playground)       | Interactive scatter plot and correlation activity          |
| [google-forms/](google-forms/)                                                                        | Generator for the lesson Google Forms (in this repo)       |

Older standalone activity repos are archived — their content now lives in
[neft-classroom-html-activities](https://github.com/Baltimoreteacher1/neft-classroom-html-activities).

---

## Quick Deploy

**Add to Classroom Activities:** Clone `neft-classroom-html-activities` → add HTML in the right folder (e.g. `math/unit-5/my-activity/index.html`) → push to `main` → Cloudflare auto-deploys.

**New standalone activity:** Create repo → add `index.html` → Settings → Pages → deploy from `main` → live at `baltimoreteacher1.github.io/repo-name/`

**Cloudflare Pages:** [dash.cloudflare.com](https://dash.cloudflare.com) → Pages → Connect repo → set build output to `.` → auto-deploys on push.

**Rebuild lesson forms:** see [google-forms/README.md](google-forms/README.md).
