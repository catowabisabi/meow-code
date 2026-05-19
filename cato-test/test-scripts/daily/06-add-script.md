# Task DL-6: Add npm Script

## Task
Add a new script to `hello-world/package.json`:
1. Add script: `"backup": "node backup.js"`
2. Create `backup.js` with content:
```javascript
console.log('Backup functionality');
```

Location: `C:\Users\enoma\Desktop\cato-test\projects\hello-world\`

## Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\package.json" | ConvertFrom-Json | Select-Object -ExpandProperty scripts
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\backup.js"
```