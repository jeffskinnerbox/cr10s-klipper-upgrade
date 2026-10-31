# My Prompts

---

## My 1st Prompt

Using your /skill-creator skill, create for me a skill called proof-read.

A good document proofreader performs the final quality check on a piece of writing before publication or distribution.
Focusing strictly on surface-level polish and technical presentation rather than rewriting or restructuring content.

Before making any changes, show me the improvement you wish to do and request my approval.

## What a Good Proofreader Does

- Applies a fresh perspective: Catches blind spots, typos, and repeating patterns that the original author or editor's brain naturally glosses over.
- Marks up remaining errors: Highlights mistakes directly on the final drafted or designed file (via track changes, PDF markups, or hard copy notations) for the writer to review or approve.
- Stays in their lane: Avoids heavy copy-editing or rewriting sentences unless a glaring error breaks meaning; they respect the author's voice and prior editorial choices.
- Follows guidelines: Enforces adherence to a specific style guide (such as APA, Chicago, MLA, or an in-house corporate standard).

## What a Good Proofreader Looks For

- Surface Mechanics & Typos
- Misspelled words, homophone mix-ups (e.g., their/there, effect/affect), and dropped letters.
- Punctuation errors (misplaced commas, broken quotation marks, incorrect dashes or semi-colons).
- Grammar and syntax glitches (subject-verb disagreements, tense shifts, and dangling modifiers).
- Consistency Issues
- Inconsistent spelling or hyphenation across the text (e.g., switching between email and e-mail, or British vs. American English).
- Name, title, and proper noun discrepancies (making sure a person's name or a company is spelled identically every time).
- Formatting consistency for headings, fonts, bullet points, and paragraph spacing.
- Layout, Design, and Technical Glitches
- Orphan or widow lines (isolated lines of text at the top or bottom of a page).
- Broken web or email hyperlinks in digital documents and e-books.
- Misaligned tables, missing or mismatched figure/table numbers, and incorrect image captions.
- Table of contents (TOC) or index entries that do not match the actual page numbers or headings.
- Basic Fact-Checking
- Obvious numerical, date, or data mismatches.
- Verifying that acronyms or technical terms are spelled out on first use.

At any point in the approving process, the user should have the option to accept all recommended changes.

---

## My 2nd Prompt

Use the /skill-creator skill on the proof-read skill

---

## My 3rd Prompt

Using the /proof-read skill, proof the @my-vision.md file.

---

## My 4th Prompt

I have assembled the hardware and software to begin the "## Upgrade Plan" section of the document @my-vision.md.
This plan gives a high outline of the physical build of the 3D platform, but I currently lack a well defined
future 3D printing workflow.

Research for me what are good recommendations for the workflow and answer these questions:

- How should the desktop Ubuntu system and the Sonic Pad collectively support required functionality?
- What are the recommended tools to support the step-by-step movement from
  CAD design -> STL -> G-code -> rendered object?
- Can this flow be made less manual? Can it be supported by scripts that move data and automate work?
  Can that workflow be automatically monitored and provide the user status?
- Outline the new workflow.

Place your findings in the document @new-workflow.md

---

## My 5th Prompt

The documents @input/my-vsion.md and @input/new-workflow.md describe what I wish to build.
This project is mainly the assembling and wiring of hardware parts.
It also contains loading & configuring of software packages
and writing some python scripts for automation and establishment of a workflow.

For this project to be successful:

- well orchestrated sequence of steps must be defined so the solution can be assembled and tested at each build phase
- step-by-step assembly instructions for me to follow must be written
- detail wiring instructions for me to follow must be written
- code must be written in python or bash and tested in support of the workflow process
- integration tests must be created and implemented in python or bash scripts

### 1st Step

- creation of a local git repository,
- read @input and propose a name and description for the GitHub repository for my approval,
- create a README.md file using the /readme-wizard skill,
- and then to pushed to GitHub.

### 2nd Step

- creation of a product requirements document in @docs/prd.md and implementation plan in @docs/plan.md for this project,
- use your /spec-kit skills for the creation of @docs/prd.md and @docs/plan.md documents,
- @docs/prd.md should include a full description of the workflow to be implemented.
- In in the @docs/plan.md include software libraries/packages that will be used,
  specify any prototyping or testing that should be done,
  and assure the assembly, wiring, and coding logically progresses to activate the designed functionality
  at each phase so that test can be performed.
- In the @docs/plan.md include all the sources (e.g. webpage title and URL) used to develop the plan.
- The process flow should do logging so that troubles can be analyzed by a human or Claude.
- Also, periodic log remove should be supported, for example, removal of project log after 6 months
  or remove oldest-half the log after it reached 50M bytes.

Continue to use the /spec-kit skill throughout all the subsequent phases of this project.

Make sure no secrets are written to your git repository.

Use the /grill-me skill so I can answer all question you might hav

---

claude --resume ecc1e3d8-d112-4872-b6a0-b9f6c66f86d8
