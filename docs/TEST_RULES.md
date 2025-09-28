# Test Execution Rules for AI Agents

## Important info

You MUST report back every step to me as defined below:

Tests are available at /web/tests

If you create a new test this must be stored in web/tests

Save test report to: web/test-reports/

Playwright-test must include video 1900x120 and snapshot 1900x1200

Save test report to: web/test-reports/ with working links to both video and snapshot



## Before you start

- Is there a test already? Check /web/testsProve the problem with **one failing** Playwright test.

  **Report**: "Test available" or "Test not available"

- Fix only the responsible layer.

  **Report**: Explain short name of test and function

- Prove the fix with the **same passing** test.

  **Report**: "Name of test - test try ##" add number

- You are not allowed to modify the test if it fail just to pass

- Remember: The **FUNCTION** must be tested. A visible button that is possible to test - but nothing happens at all is FAIL. 

- Always verify and confirm that the database get updated

  **Report**: Table XXX updated with data yyy



## How to Run (Chromium headless only) - example
- Full run: `npm run test:e2e:report`
- Single file: `npm run test:e2e:report -- web/tests/meetings.spec.ts`
- Tagged tests: `npm run test:e2e:report -- -g @formX`
- Combined: `npm run test:e2e:report -- tests/e2e/project/meetings.spec.ts -g @formX`
- Print latest report path: `npm run test:e2e:open-latest`

## Rules
- Do **not** change `playwright.config.ts`.
- Do **not** create new spec files if an area already exists — expand the existing one.
- The PR **must** link to `tests/reports/<timestamp>/index.html`.
- Success = 100%. Everything under 100% is fail.
- To skip steps in this guide is fail. To not report your steps is fail.
