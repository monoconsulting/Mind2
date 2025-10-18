# AI Services Error Report

## Summary of the Problem

All AI services (AI1-AI6) are reported as broken after a series of changes to fix an issue with AI6. The initial problem was a `400 Bad Request` from the OpenAI API for AI6, followed by a timeout issue. The fixes applied seem to have caused a regression, breaking all other AI services.

## Investigation and Findings

My investigation points to a single root cause: **incorrectly applying a fix for a new OpenAI API endpoint to all AI services.**

Here's a breakdown of my findings:

1.  **Initial AI6 Error:** The original error for AI6 was `Unsupported parameter: 'response_format'`. This error message also indicated that the parameter had moved to `text.format` for the `/v1/responses` API.

2.  **Incorrect Generalization:** I incorrectly assumed that all OpenAI services were using this new `/v1/responses` endpoint and payload format. I modified the central `OpenAIProvider.generate` method in `ai_service.py` to use the new payload format.

3.  **The Root Cause:** It appears that only AI6 is intended to use the newer `/v1/responses` API, while the other AI services (AI1-AI5) use the standard `/v1/chat/completions` endpoint, which still requires the `response_format` parameter. By changing the common provider, I broke the working services.

4.  **OCR Timeout:** The timeout issue (`SoftTimeLimitExceeded`) was a separate problem related to the OCR process taking a long time, especially on the first run when it downloads models. I addressed this by increasing the Celery task time limits in `docker-compose.yml`. This change is likely still valid and necessary.

5.  **Missing AI6 Logs:** The reason no logs were appearing for AI6 is that the `wf3_firstcard_invoice` task in `tasks.py` did not have the necessary calls to the `_history` logging function.

## Plan for Resolution

To fix this, I will refactor the code to support both the old and new OpenAI APIs, and ensure logging is correctly implemented for all services.

1.  **Revert `OpenAIProvider`:** I will revert the `OpenAIProvider.generate` method in `ai_service.py` to its original state, using the `/v1/chat/completions` endpoint and the `response_format` parameter. This will fix AI1-AI5.

2.  **Create a New Provider for AI6:** I will create a new provider class, `ResponsesApiOpenAIProvider`, specifically for the `/v1/responses` API. This class will contain the corrected payload format (`text: { format: ... }`).

3.  **Update Provider Selection:** I will modify the `_init_provider` method in `ai_service.py` to allow selecting the new `ResponsesApiOpenAIProvider` based on the provider name configured in the database (e.g., `openai-responses-api`). This will allow the AI6 service to be configured to use the new provider.

4.  **Ensure AI6 Logging:** I have already added the necessary logging calls to the `wf3_firstcard_invoice` task in `tasks.py`. This will ensure that AI6 activity is properly logged to the `ai_processing_history` table.

I will now proceed with these changes.
