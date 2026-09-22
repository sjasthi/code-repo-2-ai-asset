Overview

This plan breaks the project into 10 focused iterations, each with clear deliverables. Each iteration builds on the previous, with time allocated for learning, testing, optimization, and refinement (Note. iterations are not set in stone).

FP1: Project Understanding
Project scope, goals, and vision defined
Users and stakeholders identified
Primary goals documented
FP2: Research, Design & Planning (NEXT)


Goals:

Quick competitive research (focused, not exhaustive)
Validate technology stack choices
Create basic architecture diagram
Document key risks
Set up dev environment

Deliverables:

RESEARCH.md — 1-page competitive analysis (3-5 key tools, what's missing)
TECH_STACK.md — Tech choices and quick rationale
ARCHITECTURE.md — Basic system diagram (ASCII or simple sketch)
RISKS.md — Top 5 risks with quick mitigation
Local dev environment working (Python + Neo4j running)
GitHub repo initialized with README

Key Tasks:

Spend 2 hours researching 3-5 competing tools (what do they do well?)
Quick tree-sitter test on 1 Python file (prove it works)
Spin up Neo4j locally (verify it runs)
Sketch basic architecture (can be simple)
Set up FastAPI + React skeleton repos

Success Criteria:

Team agrees on tech stack
Dev environment runs on all machines
No blocking unknowns identified
Ready to start coding FP3

Notes:

Skip exhaustive research; make quick decisions
Focus on "does it work?" not "is it perfect?"
Can course-correct in FP9
FP3: Backend Foundation & Python Parser

Duration: 1 week

Goals:

Set up FastAPI backend scaffold
Integrate tree-sitter for Python
Extract top-level symbols (classes, functions)

Deliverables:

FastAPI server with 1 basic endpoint
tree-sitter Python parser working
Symbol extractor (classes + functions only)
Basic tests (5-10 test cases)

Key Tasks:

Set up FastAPI project (main.py, requirements.txt)
Install tree-sitter and Python grammar
Implement simple symbol extractor (walk AST, extract class/function names)
Create /parse endpoint that accepts Python code (string)
Write 5-10 unit tests
Document endpoint in README

Success Criteria:

/parse endpoint works on sample Python files
Extracts class and function names correctly
Tests pass
No external dependencies blocked

Notes:

Focus only on top-level symbols (skip nested for now)
Methods extracted in FP5 (keep scope tight)
Tests don't need to be perfect, just basic coverage
FP4: Neo4j Schema & Database Integration

Duration: 1 week

Goals:

Design and implement Neo4j data model
Store parsed symbols in Neo4j
Create basic queries

Deliverables:

Neo4j schema (File, Class, Function nodes)
Neo4j driver integration in FastAPI
/store endpoint that saves symbols to Neo4j
3-5 basic queries (find class, find function, list all symbols)
Connection pooling + error handling

Key Tasks:

Design minimal Neo4j schema (just the essentials)
Set up Neo4j driver in FastAPI
Implement store_symbol() function
Create /store endpoint
Build simple queries for retrieval
Test Neo4j connection and basic CRUD

Success Criteria:

Can insert symbols into Neo4j
Can retrieve symbols by name
Basic queries work correctly
No connection pooling issues
Tests passing

Notes:

Keep schema minimal (add relationship types in FP5-6)
Don't optimize queries yet (do that in FP5)
Test with small dataset (10-20 symbols)
FP5: Import Extraction & File Dependencies

Duration: 1 week

Goals:

Extract import statements from Python files
Build file-to-file relationships in Neo4j
Create /analyze endpoint that processes a folder

Deliverables:

Import extractor (parse Python import/from statements)
File node creation (one node per .py file)
IMPORTS relationship builder
/analyze endpoint (takes folder, parses all .py files)
Basic import dependency queries

Key Tasks:

Implement import statement parser (regex + AST)
Create File nodes for each Python file
Extract and store IMPORTS relationships
Implement /analyze endpoint
Write tests for import extraction
Test on sample Python project (100-200 files)

Success Criteria:

Correctly identifies all top-level imports
File nodes created in Neo4j
IMPORTS relationships accurate
/analyze endpoint works on sample project
Tests passing

Notes:

Python imports only (JS/TS in v2)
Skip edge cases for now (circular, dynamic) - handle in FP9
Don't optimize performance yet (FP9)
FP6: Symbol Search

Duration: 1 week

Goals:

Implement basic symbol search
Create search API endpoint

Deliverables:

/search endpoint (search by symbol name)
Neo4j indexes for fast lookup
Search returns classes and functions
Tests for search functionality

Key Tasks:

Create Neo4j indexes on symbol names
Implement search endpoint (exact match)
Return results: symbol name, file, line number
Add basic error handling
Write tests (10 test cases)
Document /search endpoint

Success Criteria:

Search endpoint works
Returns correct results
Tests passing
No performance optimization needed yet

Notes:

Exact match only (fuzzy in v2)
No pagination yet (simple list)
No ranking (all results same priority)
FP7: Frontend Setup & Upload UI

Duration: 1 week

Goals:

Create React/TypeScript project
Build file upload component
Wire up to backend /analyze endpoint

Deliverables:

React app with TypeScript
Upload folder component
API client (basic fetch wrapper)
Loading/error states
Basic layout

Key Tasks:

Set up Vite project
Create upload component (file input)
Build API client service
Create /analyze endpoint call
Add loading/error messages
Test component manually

Success Criteria:

Can upload a folder
Backend receives files
Loading state shows
Error handling works
No TypeScript errors

Notes:

No graph visualization yet (FP8)
No search UI yet (FP8)
Simple layout only
Manual testing is fine
FP8: Graph Visualization

Duration: 1 week

Goals:

Render dependency graph with Cytoscape.js
Add basic interactions (zoom, pan)
Connect to backend graph API

Deliverables:

Cytoscape.js integration
/graph endpoint that returns JSON graph data
Render nodes (files, classes)
Render edges (imports)
Zoom/pan controls
Basic styling

Key Tasks:

Integrate Cytoscape.js library
Create /graph endpoint (returns graph as JSON)
Fetch graph from backend
Render nodes and edges
Add zoom/pan
Add basic node colors
Test with sample graph (50-100 nodes)

Success Criteria:

Graph renders
Zoom/pan works
Nodes are clickable
No major performance issues on small graphs
Manual testing passes

Notes:

Don't worry about large graphs yet (FP9)
No filtering/searching on graph (FP9)
Simple styling only
Performance optimization in FP9
FP9: GitHub Integration & Performance Optimization

Duration: 1 week

Goals:

Add GitHub repo import
Optimize performance for larger codebases
Test on real open-source projects
Fix bugs found during testing

Deliverables:

GitHub API integration (token-based)
cloneRepo() function
Real-world testing (3-5 open-source repos)
Performance improvements (optimize queries/parsing)
Bug fixes from testing
Known issues documented

Key Tasks:

Implement GitHub API client (token auth)
Clone repo and process all .py files
Build repo picker UI
Test on Flask, Django, Requests (50K-100K lines each)
Profile and optimize slow queries
Fix parsing edge cases
Benchmark end-to-end time
Document known limitations

Success Criteria:

GitHub import works
Can analyze real repo in <2 minutes
Graph renders with 1K+ nodes without lag
At least 3 open-source projects analyzed successfully
Major bugs fixed

Notes:

GitLab in v2 (keep scope tight)
Focus on MVP target (50K lines in 2 min)
Skip edge cases, document them instead
FP10: Documentation, Deployment & Feedback

Duration: 1 week

Goals:

Complete documentation
Create deployment guide
Gather user feedback
Plan v2 roadmap

Deliverables:

Complete README (with demo)
API documentation
Deployment guide (Docker + quick start)
User guide / tutorial
v2 roadmap document
Known issues/limitations list

Key Tasks:

Write comprehensive README
Document all API endpoints
Create Docker setup
Write quick start guide
Get feedback from 3-5 developers
Create v2 feature list
Document tech debt
Clean up code (basic refactoring)
Remove debug code/comments

Success Criteria:

README is clear and complete
Can deploy with docker-compose up
User feedback collected
v2 roadmap defined
Known issues documented
Code is clean and ready for handoff

Notes:

Focus on clarity over perfection
User feedback from team/classmates is fine
v2 roadmap for future development
No code refactoring beyond cleanup