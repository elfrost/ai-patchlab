Review the code changes and provide feedback.

## Instructions

1. Read CLAUDE.md to understand project standards
2. Review all modified files in the current git diff: `git diff`
3. If no diff, review the files specified: $ARGUMENTS

## Review Checklist

For each file, check:

### Code Quality
- [ ] Type hints on all functions
- [ ] Docstrings on public functions
- [ ] No files over 300 lines
- [ ] No hardcoded secrets or config values
- [ ] Proper error handling (no silent failures)
- [ ] Logging with loguru (no print statements)

### Patterns
- [ ] Follows patterns from examples/
- [ ] Consistent with existing codebase style
- [ ] Async/await used for I/O operations
- [ ] Pydantic models for data validation

### Database (if applicable)
- [ ] Parameterized queries (no string concat)
- [ ] Proper indexes
- [ ] created_at/updated_at timestamps

### Testing
- [ ] Critical functions have tests
- [ ] External calls are mocked
- [ ] Tests actually test behavior (not just existence)

## Output Format

Provide:
1. **Summary** — Overall assessment (1-2 sentences)
2. **Issues** — List of problems found (with file:line references)
3. **Suggestions** — Improvements that aren't bugs but would help
4. **Good stuff** — Things done well (positive reinforcement)

Run validation:
```bash
ruff check src/
black --check src/
pytest tests/ -v
```

Report results.
