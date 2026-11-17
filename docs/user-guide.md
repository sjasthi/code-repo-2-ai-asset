# User Guide

Code Dependency Graph shows how the files, classes and functions in a codebase
depend on each other. This guide walks through the app from loading code to
exploring the graph.

> The app runs at `http://localhost:5173` in local development. If someone
> deployed it for you, use the address they gave you.

## The header

Every page shows two status badges:

- **API**: the backend is reachable.
- **Neo4j**: the graph database is reachable. Hover it to see the error when it's red.

If either badge is red, uploads, search and the graph won't work until it's green
again. It rechecks every 15 seconds.

## 1. Add code (Upload page)

Open **Upload** and choose a tab.

### Files

1. Drag files onto the drop zone, or click **Choose files**.
   - Accepted: Python (`.py`, `.pyi`), JavaScript (`.js`, `.jsx`, `.mjs`,
     `.cjs`), TypeScript (`.ts`, `.mts`, `.cts`), up to 1 MB each.
   - **To add a whole folder,** ZIP it and drop the `.zip`. It's unpacked in
     your browser and the supported files are queued. Others are skipped, and
     the app tells you how many.
2. Check the list. Unsupported or oversized files are marked as errors.
   Remove a file with its × button.
3. Click **Analyze N files**. Each file shows its result when it's done.

Uploaded files appear in the graph under **Uploaded files**.

> **Tip:** Imports *between* uploaded files are not linked yet (see
> [Known limitations](#known-limitations)). To see a project's full import
> graph, use the GitHub tab.

### GitHub repository

1. Paste a public repository URL, e.g. `https://github.com/psf/requests`.
   A `/tree/<branch>` URL works too.
2. Optionally enter a **branch**. Leave it empty for the default branch.
3. Click **Import repository**. A 50,000-line project takes about a minute and a half, so
   keep the page open.

When it finishes you'll see how many files, symbols and relationships were
stored, how many files were skipped, and how many had syntax errors.

Importing the same repository again **replaces** its previous data. Use that
to refresh after the code changes.

Repository import supports more languages than file upload: Python,
JavaScript, TypeScript, Go, Rust, Java, C, C++ and Ruby. Go through Ruby get
symbols (search and graph nodes) but no import or call links yet.

Limits: public repos only, up to 5,000 source files and 30 MB download.
Files over 2 MB are skipped.

## 2. Find code (Search page)

1. Choose **Symbols** or **Files**.
2. Type a name or part of one, and press **Search**.

**Symbols** finds classes, functions, methods and variables.

- Tick the type filters (**class**, **function**, **method**, **variable**) to narrow results.
- **Match typos** (on by default) finds `UserService` when you type `UserServce`.
- Several words must all match: `order manager` finds `OrderManager`.
- Results are ordered: exact name → starts with → contains → typo match.

**Files** matches any part of the path, e.g. `utils/helpers` or `main`.

Each result has a **Graph** link that opens the graph centered on that file,
with the symbol highlighted.

## 3. Trace dependencies (Dependencies page)

1. Search for a file, e.g. `main.py` or `backend/app`.
2. Click **Show dependencies** on a result.
3. You'll see three lists:
   - **Imports**: project files this file imports.
   - **Imported by**: project files that import this file. These are what
     might break if you change it.
   - **Functions called**: function names called from this file, with line numbers.
4. **Open this file in the dependency graph** jumps to the graph with two hops,
   symbols and calls turned on.

Only files stored in the graph are listed. Imports of external packages
(`react`, `os`) are not shown.

## 4. Explore the graph (Graph page)

### Choose what to show

- **Project**: an imported repository, **Uploaded files**, or **All files**.
- **Center on file**: type a path to show just that file and its neighbors,
  then choose **1–3 import hops**. This is the best way to explore big projects.
- **Include › Classes, functions & variables** adds the symbols inside each file.
- **Include › Function calls** adds function-call links.

Symbols and calls add many nodes, so start with files only on large repos.

### Read it

| Edge | Meaning |
|---|---|
| imports | file A imports file B |
| contains | file defines this class or function |
| calls | file calls a function with this name |

### Interact

- **Click a node.** What it imports turns teal, what imports it turns orange,
  and everything else fades. The side panel lists the neighbors as buttons, so
  you can walk the graph by keyboard.
- **Highlight** box: type a name or path and matching nodes light up as you type.
- **Show types** checkboxes hide or show each kind of node.
- Canvas buttons: **+ / −** zoom, **Fit**, **Re-layout**, **PNG** (download an image).
- Scroll to zoom, drag the background to pan, drag a node to move it.

Large graphs (over 400 nodes) switch to a **grouped by file** layout, where each
file's symbols circle around it. Over 1,500 nodes, labels appear only when you
zoom in. If a graph is cut off at the file limit, the page tells you.

### Share a view

The URL holds the view, e.g.
`/graph?file=app/main.py&depth=2&symbols=1&calls=1&q=get_database`. Copy it to
share exactly what you're looking at.

## Known limitations

- Imports between **uploaded** files don't create links. Use GitHub import for full import graphs.
- **GitLab** and **private** GitHub repositories aren't supported yet.
- **Calls** are matched by function name. If two files both define `save()`, a
  call to `save` links to the name, not to a particular definition, so
  "called by" can include false matches.
- `.tsx` files with JSX may show syntax errors and miss some symbols.
- `.tsx` files don't show in the **Choose files** picker. Drag them onto the drop zone, put them in a ZIP, or use GitHub import.

For the full list and plans, see the [Roadmap](roadmap.md).
