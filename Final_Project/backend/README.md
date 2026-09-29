# Code Dependency Graph - Backend

## Overview

This is the Python backend for the Code Dependency Graph project.

The backend is responsible for analyzing source code and extracting structured information about the codebase.

## Technology Stack

- Python
- FastAPI
- Uvicorn
- Tree-sitter
- tree-sitter-python
- pytest

## Architecture

The current FP3 pipeline is:

Python source code
        |
        v
FastAPI API
        |
        v
Python Symbol Extractor
        |
        v
Tree-sitter Parser
        |
        v
Python Syntax Tree
        |
        v
Extracted Symbols
        |
        v
JSON response

## Tree-sitter

Tree-sitter is used to parse Python source code into a syntax tree.

Instead of treating source code as plain text, Tree-sitter identifies syntactic structures such as:

- Classes
- Functions
- Methods
- Assignments

The symbol extractor walks through the syntax tree and identifies these structures.

## Python Symbol Extraction

The FP3 symbol extractor currently identifies:

- Classes
- Functions
- Methods
- Variables

Each extracted symbol contains:

- Symbol type
- Symbol name
- File path
- Line number

## API Endpoints

### GET /

Checks that the backend is running.

### GET /health

Returns the backend health status.

### POST /parse/python

Parses Python source code and returns the extracted symbols.

Example request:

```json
{
    "file_path": "example.py",
    "source_code": "class User:\n    pass"
}