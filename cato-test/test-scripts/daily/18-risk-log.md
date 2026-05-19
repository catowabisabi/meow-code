# Task DL-18: Create Risk Log

## Task
Create `risks.md` in `docs-site`:
```markdown
# Risk Log

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Budget overrun | High | Medium | Monitor weekly |
| Timeline delay | Medium | High | Add buffer |
```

Location: `C:\Users\enoma\Desktop\cato-test\projects\docs-site\risks.md`

## Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\risks.md"
```