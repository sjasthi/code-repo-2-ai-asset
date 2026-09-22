After researching all of the existing code dependency tools availiable, here is a summary of a few popular tools and what they do well.

Github's Dependency Graph:
    Pros:
        Built directly into Github, security focused, transitive dependency tracking, wide package ecosystem support, free for public repos, auto updates, vulnerabliity itelligence, and pull request integration.

    Cons: 
        Package-level only, cannot show code-level dependencies. Only works if project has package.json, requirments.txt, etc. No code symbol indexing, limited to external dependencies, GitHub only (no Gitlab, Git, etc.).


GitLab Dependency Scanning:
    Pros:
        CI/CD integrated, good security, comprehensive dependency analysis, immediate feedback, supports multiple ecosystems (Python, Java, Ruby, etc), can scan outside of CI/CD pipelines.

    Cons: 
        Enterprise-only feature (requires tier subscription), GitLab only (does not work with Github or other platforms), Requires gitlab-ci.yml file setup, only focuses on security, no code symbol indexing, and no interactive visualization.



VScode Maps:
    Pros:
        Works locally in ediotr, file-level structure (can show classes, functions and methods), quick naviagation, interactive UI, supports multiple languages, no API calls required, free options avialable, and quick and easy to setup.

    Cons: 
        Single file view only, limited cross-file dependencies, no security scanning, no codebase-wide search, limited scalability, requires manual naviagation, IDE-dependent (meaning only works in VSCode), no presistent graph storage.



Possible ideas for our project:

Since the GitHub Dependency Graph only shows package dependencies and not code relationships, we can provide file imports, function calls, and class hierarchies. 

Most of these solutions only work on single-file or single-project and has no searcable index, so we can use Neo4j to enable fast gloybal symbol search accross the entire codebase. 

There is no good solution for cross-file dependency navigation, but our graphs will be able to show these relationships as well as an impact analysis.

Exisisting tools are built mainly for humans. LLMs will be able to query our Neo4j graphs which will help then understand the code structure better.