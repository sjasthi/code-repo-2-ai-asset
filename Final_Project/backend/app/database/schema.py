SCHEMA_QUERIES = [

    """
    CREATE CONSTRAINT file_path_unique IF NOT EXISTS
    FOR (f:File)
    REQUIRE f.path IS UNIQUE
    """,

    """
    CREATE CONSTRAINT class_unique IF NOT EXISTS
    FOR (c:Class)
    REQUIRE (c.name, c.file_path, c.line) IS UNIQUE
    """,

    """
    CREATE CONSTRAINT function_unique IF NOT EXISTS
    FOR (f:Function)
    REQUIRE (f.name, f.file_path, f.line) IS UNIQUE
    """,

    """
    CREATE CONSTRAINT method_unique IF NOT EXISTS
    FOR (m:Method)
    REQUIRE (m.name, m.file_path, m.line) IS UNIQUE
    """,

    """
    CREATE CONSTRAINT variable_unique IF NOT EXISTS
    FOR (v:Variable)
    REQUIRE (v.name, v.file_path, v.line) IS UNIQUE
    """,

    # FP6 search indexes.

    # Full-text (Lucene) index on symbol names, used by /search for
    # ranked, fuzzy and partial matching.
    """
    CREATE FULLTEXT INDEX symbol_name_fulltext IF NOT EXISTS
    FOR (n:Class|Function|Method|Variable)
    ON EACH [n.name]
    """,

    # Text index so file path CONTAINS / STARTS WITH lookups use an index.
    """
    CREATE TEXT INDEX file_path_text IF NOT EXISTS
    FOR (f:File)
    ON (f.path)
    """,

    # Range indexes for exact name lookups, e.g. MERGE (:Function {name})
    # in DependencyGraphBuilder.store_call and the class-imported-by query.
    """
    CREATE INDEX class_name IF NOT EXISTS
    FOR (c:Class)
    ON (c.name)
    """,

    """
    CREATE INDEX function_name IF NOT EXISTS
    FOR (f:Function)
    ON (f.name)
    """,

    """
    CREATE INDEX method_name IF NOT EXISTS
    FOR (m:Method)
    ON (m.name)
    """,

    """
    CREATE INDEX variable_name IF NOT EXISTS
    FOR (v:Variable)
    ON (v.name)
    """
]
