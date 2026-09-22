# Competitive Analysis

After researching all of the existing code dependency tools available, here is a summary of a few popular tools and what they do well.

## GitHub's Dependency Graph

**Pros:**
- Built directly into Github
- Security focused
- Transitive dependency tracking
- Wide package ecosystem support
- Free for public repos
- Auto updates
- Vulnerability intelligence
- Pull request integration

**Cons:**
- Package-level only, cannot show code-level dependencies
- Only works if project has package.json, requirements.txt, etc.
- No code symbol indexing
- Limited to external dependencies
- GitHub only (no GitLab, Git, etc.)

---

## GitLab Dependency Scanning

**Pros:**
- CI/CD integrated
- Good security
- Comprehensive dependency analysis
- Immediate feedback
- Supports multiple ecosystems (Python, Java, Ruby, etc)
- Can scan outside of CI/CD pipelines

**Cons:**
- Enterprise-only feature (requires tier subscription)
- GitLab only (does not work with Github or other platforms)
- Requires gitlab-ci.yml file setup
- Only focuses on security
- No code symbol indexing
- No interactive visualization

---

## VSCode Maps

**Pros:**
- Works locally in editor
- File-level structure (can show classes, functions and methods)
- Quick navigation
- Interactive UI
- Supports multiple languages
- No API calls required
- Free options available
- Quick and easy to setup

**Cons:**
- Single file view only
- Limited cross-file dependencies
- No security scanning
- No codebase-wide search
- Limited scalability
- Requires manual navigation
- IDE-dependent (only works in VSCode)
- No persistent graph storage