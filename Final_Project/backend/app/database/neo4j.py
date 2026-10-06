import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

from app.database.schema import SCHEMA_QUERIES


load_dotenv()


class Neo4jConnection:

    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")

        self.database = os.getenv(
            "NEO4J_DATABASE",
            "neo4j"
        )

        self.driver = GraphDatabase.driver(
            uri,
            auth=(username, password)
        )

    def close(self):
        self.driver.close()

    def verify_connection(self):
        self.driver.verify_connectivity()

    def initialize_schema(self):

        with self.driver.session(
            database=self.database
        ) as session:

            for query in SCHEMA_QUERIES:
                session.run(query)

    def execute_query(
        self,
        query,
        parameters=None
    ):
        with self.driver.session(
            database=self.database
        ) as session:

            result = session.run(
                query,
                parameters or {}
            )

            return result.data()
    
    def create_file(self, path, language):

        query = """
        MERGE (f:File {path: $path})
        SET f.language = $language
        RETURN f
        """

        return self.execute_query(
            query,
            {
                "path": path,
                "language": language
            }
        )

    def create_symbol(
        self,
        symbol
    ):

        symbol_type = symbol["type"]

        labels = {
            "class": "Class",
            "function": "Function",
            "method": "Method",
            "variable": "Variable"
        }

        label = labels.get(symbol_type)

        if not label:
            raise ValueError(
                f"Unknown symbol type: {symbol_type}"
            )

        query = f"""
        MERGE (s:{label} {{
            name: $name,
            file_path: $file_path,
            line: $line
        }})
        RETURN s
        """

        return self.execute_query(
            query,
            {
                "name": symbol["name"],
                "file_path": symbol["file_path"],
                "line": symbol["line"]
            }
        )

    def create_file_symbol_relationship(
        self,
        symbol
    ):

        relationship = "CONTAINS"

        label = {
            "class": "Class",
            "function": "Function",
            "method": "Method",
            "variable": "Variable"
        }.get(symbol["type"])

        if not label:
            raise ValueError(
                f"Unknown symbol type: {symbol['type']}"
            )

        query = f"""
        MATCH (f:File {{path: $file_path}})
        MATCH (s:{label} {{
            name: $name,
            file_path: $file_path,
            line: $line
        }})

        MERGE (f)-[:{relationship}]->(s)
        """

        return self.execute_query(
            query,
            {
                "file_path": symbol["file_path"],
                "name": symbol["name"],
                "line": symbol["line"]
            }
        )