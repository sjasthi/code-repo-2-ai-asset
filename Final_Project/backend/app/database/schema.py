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
    """
]