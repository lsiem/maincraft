```markdown
# maincraft Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill introduces the core development patterns and workflows for the `maincraft` Python project. It covers coding conventions, file organization, commit styles, and the main workflows for parser enhancement and feature documentation. By following these guidelines, contributors can maintain consistency and efficiency across the codebase.

## Coding Conventions

- **File Naming:**  
  Use camelCase for filenames.  
  *Example:*  
  ```
  parseBetterQuesting.py
  questUtils.py
  ```

- **Import Style:**  
  Use relative imports within the package.  
  *Example:*  
  ```python
  from .questUtils import parseQuest
  ```

- **Export Style:**  
  Mixed export styles are present. You may see both explicit `__all__` declarations and implicit exports.

- **Commit Patterns:**  
  - Freeform commit messages, often prefixed with `cursor`.
  - Average commit message length: ~48 characters.
  *Example:*  
  ```
  cursor: improve prerequisite resolution for quest parser
  ```

## Workflows

### Parser Enhancement or Bugfix
**Trigger:** When you want to improve or fix the BetterQuesting quest parsing logic.  
**Command:** `/parser-enhancement`

1. Edit `maincraft/ingestion/parse_betterquesting.py` to implement the enhancement or bugfix.
2. Update or refactor parsing functions as needed.
3. Optionally, add or update tests to cover the changes.

*Example:*
```python
# In maincraft/ingestion/parse_betterquesting.py

def strip_bbcode(text):
    # Improved BBCode stripping logic
    ...
```

---

### Feature Development with README Update
**Trigger:** When you add a new feature, CLI flag, or major change that needs to be documented for users.  
**Command:** `/feature-doc`

1. Implement the new feature or change in the codebase.
2. Edit `maincraft/README.md` to document the new feature or update instructions.
3. Ensure documentation is clear about new flags, retrieval methods, or test instructions.

*Example:*
```python
# Add a new CLI flag in your script
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--new-flag', help='Enable the new feature')
```
```markdown
# In maincraft/README.md

## New Feature: --new-flag
Use `--new-flag` to enable the new feature.
```

## Testing Patterns

- **Framework:** Unknown (not explicitly detected).
- **File Pattern:** Test files follow the `*.test.ts` pattern, suggesting some TypeScript-based tests may exist, possibly for frontend or CLI wrappers.
- **Recommendation:** If adding or updating Python tests, follow the existing conventions or introduce a standard Python testing framework (e.g., `pytest`) if not present.

## Commands

| Command              | Purpose                                                        |
|----------------------|----------------------------------------------------------------|
| /parser-enhancement  | Start a parser logic improvement or bugfix workflow            |
| /feature-doc         | Begin a new feature or major change with README documentation  |
```
