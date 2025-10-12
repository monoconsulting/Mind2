# Instructions and rules for agents
```
Version: 1.1
Date: 2025-10-12
```

## Rules

* Mock data in the system are **not allowed.** This can not be used without a specific order to implement it
* **SQLLite can never be used.** You have no permissions to use this.
* Test **must** be performed exactly as stated in @docs/TEST_RULES.md
* You are **never allowed to change port** or assign a new port to something that is not working.  You MUST ask permission
* You have **NO PERMISSIONS to use taskkill** to kill a port that someone else is using. This can cause serious damage
* You **ARE NOT ALLOWED TO EDIT playwright.config.ts** (except playwright.dev.config.ts for development testing)

## Development & Testing Environment

### Frontend Development Modes

The system supports both production and development frontend modes:

**Production Mode (Port 8008):**
- Built frontend served via Docker + Nginx
- Used for final testing and deployment
- Requires rebuild after code changes

**Development Mode (Port 5169) - HOT-RELOAD ENABLED:**
- Vite dev server with instant hot-reload
- **Automatically starts with `mind_docker_compose_up.bat`**
- No rebuild needed - changes appear instantly
- Two ways to run:
  1. **Docker mode (Recommended)**: Part of `mind-web-main-frontend-dev` service
  2. **Local mode**: Using `mind_frontend_dev.bat`

### Testing Workflows

**For Development Testing (with hot-reload):**
1. Start services: `mind_docker_compose_up.bat`
2. Dev frontend automatically available at: `http://localhost:5169`
3. Edit code → instant hot-reload
4. Test: `npx playwright test --config=playwright.dev.config.ts --headed`

**For Production Testing:**
1. Build: `mind_docker_build_nocache.bat`
2. Start: `mind_docker_compose_up.bat`
3. Test: `npx playwright test --headed`

**Important:** When reporting work done, ensure rebuilds are performed if testing requires the production build. For development testing, use the dev server on port 5169.

### Port Assignments (DO NOT CHANGE)
- **8008** - Production frontend + API (via nginx)
- **5169** - Dev frontend with hot-reload
- **5000** - Backend API (internal, not exposed)
- **3310** - MySQL
- **6380** - Redis
- **8087** - phpMyAdmin

### Documentation References
See `@docs/SYSTEM_DOCS/MIND_TASK_IMPLEMENTATION_REVIEW.md` for complete details on frontend testing and hot-reload setup.

