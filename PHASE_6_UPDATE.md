# Phase 6 Update: Frontend Deployment Fixed

## Issue
The initial Static Web App was created without GitHub integration, so automated deployments weren't triggering.

## Solution
Created a new Static Web App with proper Azure configuration. It now uses deployment tokens that can be triggered via GitHub Actions.

## Action Required - UPDATE GITHUB SECRET

1. **Go to:** https://github.com/rinkutek/secure-ai-audit-assistant/settings/secrets/actions

2. **Edit:** `AZURE_STATIC_WEBAPPS_API_TOKEN`

3. **Replace the value with:**
   ```
   73a53f5a97f5cf414631c3408ece9e89173658823e2827fd3976ba2161ffffd4d01-111263b0-5bf3-4563-ae79-fd56b47b338600f200508b79210f
   ```

4. **Click "Update secret"**

## New Frontend URL
After the workflow runs (following the secret update), your frontend will be live at:
```
https://happy-coast-08b79210f.1.azurestaticapps.net
```

## Build Fixes Applied
- ✅ Upgraded Node.js to v20 (Vite 5 requires v18+, v20 is more stable)
- ✅ Updated GitHub Actions workflow to use `node-version: 20`
- ✅ Created `.nvmrc` file for version consistency
- ✅ Verified frontend builds successfully locally

## Next Steps
1. Update the GitHub secret (manual UI step required)
2. Push an empty commit to trigger workflow: `git commit --allow-empty -m "chore: trigger deployment with new SWA token"`
3. Watch workflow at: https://github.com/rinkutek/secure-ai-audit-assistant/actions
4. Frontend will deploy to: https://happy-coast-08b79210f.1.azurestaticapps.net

## Technical Details

### Why This Happened
- Initial Static Web App creation didn't include GitHub repository integration
- The deployment token from the unlinked SWA couldn't trigger automatic builds
- Solution: Created new SWA instance with proper Azure configuration for token-based deployments

### Why Node.js v20 Matters
- Vite 5.x requires Node.js 18.0.0 or higher
- Node.js v16 is missing modern crypto APIs that Vite needs during build
- v20 provides full compatibility with Vite 5.4+ and better performance
