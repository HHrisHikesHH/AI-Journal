# Security Guidelines

## ✅ Security Measures Implemented

### API Keys & Secrets
- **config.json** is excluded from Git (in `.gitignore`)
- **config.json.example** contains only placeholders
- API keys are read from `config.json` or environment variables
- No API keys are hardcoded in source code

### Data Privacy
- All journal entries stored locally
- No data sent to external services except Gemini API (for AI features)
- Only entry content sent to Gemini (no personal identifiers)
- Git sync is optional and user-controlled

### File Security
- Sensitive files excluded via `.gitignore`:
  - `config.json` (contains API keys)
  - `local/` directory (embeddings, models, summaries)
  - `logs/` directory (may contain sensitive info)
  - `venv/` directory (Python virtual environment)
  - `node_modules/` (dependencies)

### Best Practices
1. **Never commit config.json** - Always use `config.json.example` as template
2. **Review commits** - Check `git diff` before committing
3. **Use environment variables** - Can set `GEMINI_API_KEY` in environment instead
4. **Regular security audits** - Review `.gitignore` periodically

## 🔒 Security Checklist

Before committing code:
- [ ] Verify `config.json` is in `.gitignore`
- [ ] Check that no API keys are in committed files
- [ ] Ensure `config.json.example` has placeholders only
- [ ] Review `git status` to see what will be committed
- [ ] Use `git diff` to review changes

## 🚨 If API Key is Exposed

If you accidentally commit an API key:

1. **Immediately revoke the key** at https://aistudio.google.com/
2. **Generate a new API key**
3. **Update local config.json** with new key
4. **Remove from Git history** (if needed):
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch config.json" \
     --prune-empty --tag-name-filter cat -- --all
   ```
5. **Force push** (if already pushed):
   ```bash
   git push origin --force --all
   ```

## 📝 Current Security Status

✅ **Secure**: API keys are properly excluded
✅ **Secure**: Sensitive data not in repository
✅ **Secure**: Example files use placeholders
✅ **Secure**: Proper `.gitignore` configuration

