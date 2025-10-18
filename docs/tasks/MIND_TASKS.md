# MIND - TASK LIST

Notes to agent:
This must be used to keep track of tasks. As soon as you finished a task you MUST mark it done in this document.
Add the tasks in english using the following standard:

#### **TEMPLATE PHASE X- Description of the phase**

- [ ] **Task 1.1 - Task title**

  **System prompt for agent:** A specific clear and very descriptive system prompt for the agent.

  **Description:** Description of the task

  **How to verify:** Description of how this should be verified and presented to the user

- [ ] **Task 1.2 - Task title**

  **System prompt:**

  **Description:** 

  **How to verify:**
  
  
  
  
  
  #### Phase 5 - Missing fields
  
  - [ ] **Task 5.1 - Fixes in preview modal**
  
    **Description:** Follow the instructions in @docs/tasks/Preview modal - field population and item name fix.md
  
    
  
  - [ ] **Task 5.2. VAT corrections**
  
    **Description:** Read instructions in @docs/MIND_VAT_CORRECTIONS.md
  
  - [x] **Task 5.3. - Missing card details**
  
    **Description:** Follow instructions in @docs/MIND_MISSING_CARD_DETAILS.md
  
    Task 5.4. - Felaktigheter i gula fält
  
    
  
    
  
  
  
  #### **Phase 6 - Process bugs**
  
  - [ ] **Task 6.1 - Redesign the workflow badges**
  
    **Description:** The workflow badges is not in sync with the design of the page. I want them to have a better design with rounded corners and the sam colors as the rest of the product. 
  
    Move the column status so it's the second line after the preview of the picture
  
    Change the icon so it has the same color scheme as the rest of the site
  
    Use the same kind of icons as the buttons - rounded corners and icons
  
    In the status column - only the active ongoing process should show with the new design
  
    When clicking on the workflow badge - it should open up the process steps under that has the same length as the row with the new design of all badges in one long row. Every badge should have a unique icon that matches the tasks. It should be clearly visible what task it is working on, what is done and what is left. 
  
    When clicking on an executing badge a full log should appear as it is today
  
  - [ ] **Task 6.2 - Merge lines**
  
    **System prompt:**
  
    **Description:** When importing a pdf it is splitted into one ore many png-files, and the pdf is still there also which create a lot of rows.
  
    If a pdf is converted to png - remove the pdf and just keep the png:s
  
    If the ocr-merge is done - just keep one preview picture in the table - but when you click on the preview modal you should see all. Put the png-files on top of each other so we get a long document in the middle. Make sure to keep the same design so we can scroll all columns individually.
  
    
  
    **How to verify:**
  
  - [ ] **Task 6.4 - Preview modal - next receipt**
  
    **System prompt for agent:** A specific clear and very descriptive system prompt for the agent.
  
    **Description:** On the most left and right side it should be an arrow that opens up to the next receipt. Click on right arrow opens up the next down in the list. Click on left open up the one above.
  
    **How to verify:** Description of how this should be verified and presented to the user
  
  - [ ] **Task 6.5 - Task title**
  
    **System prompt:**
  
    **Description:** 
  
    **How to verify:**
  
    
  
    
  
    
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  _______

#### **Phase 1 - Issues with the Credit Card workflow

-------

- [ ] **Task. 1.4. Update the process-page** and remove the flickering that occurs when the page is updated. No need to reload the pictures - just the specific workflow badges and the text fields

-------

- [ ] **Task 1.5. Automatically update Kortmatchning-page**  

  Update Kortmatchning-page in the vite-interval set in the .env file. Should work in the same way as the process page - but remove the flickering that occurs in process

-------

- [ ] **Task 1.6. Errors in import of pdf-receipts with multiple pages**

Any pdf file no matter of content should use the same import strategy for pdfs 
 	1. Convert pdf with 1 png for each page. Store in unified_files with file_type png_page (not pdf_page) 
 	2. OCR of the png-pages - store the OCR-data for the individual files in ocr_raw for the png
 	3. Merge of the OCR to store in the original pdf_page ocr_raw. If its only one page it should still be stored in the original pdf.
 	4. Start the AI-pipeline for receipts with the text from ocr_raw from the original pdf.

Analyze the existing workflow for multiple receipt pages and correct this so it follows the standards above

-------

**Task 1.7 - Wrong filetype set** 

1.6.1. If after the OCR is done, this is analyzed as "other" or "invoice" - the file_type should change to other and the ai-workflow should stop. Right now it continues and keeps the same file_type.

-------

- [ ] **Task 1.8 - All card fields empty**

**Description: In the preview modal - all fields on the left column in the section "BETALNINGSTYP" are emtpy. Both in 	**How to verify:** By a new import.

-------

- [ ] **Task 1.9 - Error in OpenAI api call - **

**Description:** celery-worker-1 shows this error message for AI

```
`0-16 16:09:58`

​    `raise RuntimeError(f"OpenAI API call failed: {exc}")`

`2025-10-16 16:09:58`

`RuntimeError: OpenAI API call failed: HTTPSConnectionPool(host='api.openai.com', port=443): Read timed out. (read timeout=300)`

`2025-10-16 16:09:58`

`[2025-10-16 14:09:58,850: ERROR/ForkPoolWorker-2] Task wf3.firstcard_invoice[edb419e3-9418-4f34-80ac-33f69b9f9eaf] raised unexpected: RuntimeError('Failed to persist credit card invoice header')`

`2025-10-16 16:09:58`

`Traceback (most recent call last):`

`2025-10-16 16:09:58`

  `File "/usr/local/lib/python3.10/dist-packages/celery/app/trace.py", line 453, in trace_task`

`2025-10-16 16:09:58`

​    `R = retval = fun(*args, **kwargs)`

`2025-10-16 16:09:58`

  `File "/usr/local/lib/python3.10/dist-packages/celery/app/trace.py", line 736, in __protected_call__`

`2025-10-16 16:09:58`

​    `return self.run(*args, **kwargs)`

`2025-10-16 16:09:58`

  `File "/app/services/tasks.py", line 2158, in wf3_firstcard_invoice`

`2025-10-16 16:09:58`

​    `raise RuntimeError("Failed to persist credit card invoice header")`

`2025-10-16 16:09:58`

`RuntimeError: Failed to persist credit card invoice header`
```

**This is most likely a wrong api-address.** The following should be used:
(`POST https://api.openai.com/v1/responses`) with**GPT-5** as model and `response_format` to either`"json_object"` (enkel JSON-mode) or`"json_schema"` (Structured Outputs with strict validation).

**This is already set in the database - which means that there are most likely a hardcoded value somewhere**

**How to verify:** Check logs after new import







-------











#### **Phase 2 - Rendering OCR Overlays**

- [x] **Task 2.1 - Render OCR Bounding Boxes on Image**

  **System prompt for agent:** Modify the `PreviewModal` component in `main-system/app-frontend/src/ui/pages/Receipts.jsx`. In the JSX where the `<img>` tag for the preview is rendered, wrap it in a `div` with `position: relative`. Immediately after the `<img>` tag, map over the `ocrBoxes` state array. For each `box` object in the array, render a `div`. This `div` must have `position: absolute` and its `left`, `top`, `width`, and `height` CSS properties must be set using the percentage-based `x`, `y`, `w`, and `h` values from the box object (e.g., `left: '{box.x * 100}%'`). Style the box with a semi-transparent background and a border (e.g., `background: rgba(0, 100, 255, 0.2); border: 1px solid blue;`).

  **Description:** This task involves rendering the fetched OCR coordinate data as visible, positioned overlay boxes on top of the receipt image within the preview modal.

  **How to verify:** Open a receipt preview in the application. The OCR bounding boxes should now be visible as blue, semi-transparent rectangles overlaid on the receipt image, corresponding to the locations of the recognized text.

#### **Phase 3 - Interactivity and User Experience**

- [ ] **Task 3.1 - Add Toggle to Show/Hide OCR Overlays**

  **System prompt for agent:** In the `PreviewModal` component in `main-system/app-frontend/src/ui/pages/Receipts.jsx`, add a new state variable, `showOcrBoxes`, defaulting to `true`. In the modal's footer or header, add a checkbox or button (e.g., `<button>Show/Hide OCR</button>`) that toggles this state. Use the `showOcrBoxes` state to conditionally render the container of the OCR box overlays you created in the previous task.

  **Description:** Add a user control to the preview modal that allows the user to toggle the visibility of the OCR bounding boxes. This provides a cleaner viewing experience when needed.

  **How to verify:** In the receipt preview modal, a new button or checkbox is visible. Clicking this control toggles the visibility of all the blue bounding boxes on the image. The boxes should be visible by default.

- [ ] **Task 3.2 - Display Text on Hover**

  **System prompt for agent:** In the `PreviewModal` component in `main-system/app-frontend/src/ui/pages/Receipts.jsx`, enhance the mapped OCR box `div`s. Add `onMouseEnter` and `onMouseLeave` event handlers to each box. On hover, display the `box.field` (the recognized text) in a simple tooltip. You can achieve this by adding another state for the active tooltip and rendering a positioned `div` when it's set. The box `div` should also have a `title` attribute set to `box.field`.

  **Description:** Improve user experience by showing the recognized text for a bounding box when the user hovers their mouse over it.

  **How to verify:** In the receipt preview modal, hover the mouse over any of the blue bounding boxes. A tooltip should appear showing the text that was recognized within that box. The browser's native tooltip should also show the text.

- [x] 

- [ ] **Task 5.3 - Task title**

  **System prompt for agent:** A specific clear and very descriptive system prompt for the agent.

  **Description:** Description of the task

  **How to verify:** Description of how this should be verified and presented to the user

- [ ] **Task 5.3 - Task title**

  **System prompt:**

  **Description:** 

  **How to verify:**

#### **Phase 6 - Workflow Stabilization**

- [ ] **Task 6.1 - Fix WF1 AI provider fallback**

  **System prompt for agent:** Review `backend/src/services/ai_service.py` and related configuration so that WF1 receipt workflows never call the Ollama endpoint when it is not configured. Ensure the AI pipeline selects an available provider/model (e.g., OpenAI) or degrades gracefully without raising `Ollama API call failed` errors.

  **Description:** WF1 receipts currently fail during `wf1.run_ai_pipeline` because the worker still targets the Ollama gateway that is not running. Update provider resolution and/or environment handling so the workflow completes the AI stages with a supported model.

  **How to verify:** Upload a sample receipt via `/ingest/upload`. Confirm in the Celery logs that `wf1.run_ai_pipeline` succeeds without Ollama exceptions and that the workflow reaches `wf1.finalize`. Check `workflow_stage_runs` for `ai_pipeline` marked `succeeded`.

- [ ] **Task 6.2 - Restore WF2 chord orchestration**

  **System prompt for agent:** Update the WF2 pipeline in `backend/src/services/tasks.py` so that `wf2_prepare_pdf_pages` schedules the page OCR chord (group of `wf2.run_page_ocr` tasks followed by `wf2.merge_ocr_results`) and the remaining stages (`wf2.run_invoice_analysis`, `wf2.finalize`). Ensure each task calls `mark_stage` with the correct stage keys and status transitions.

  **Description:** Currently only `wf2.prepare_pdf_pages` runs; the downstream OCR/merge/analysis/finalize steps never start. Implement the documented workflow so PDF uploads progress through every stage.

  **How to verify:** Upload a multi-page PDF through the Process menu. Inspect Celery logs to verify execution order `prepare_pdf_pages` → `run_page_ocr` (per page) → `merge_ocr_results` → `run_invoice_analysis` → `finalize`. Confirm corresponding entries in `workflow_stage_runs` with statuses `running/succeeded`.

- [ ] **Task 6.3 - Implement WF3 FirstCard processing**

  **System prompt for agent:** Extend `wf3.firstcard_invoice` in `backend/src/services/tasks.py` (and supporting modules) to perform the FirstCard invoice parsing/matching pipeline: aggregate OCR text, call AI6 parsing, persist to `creditcard_invoices_main/creditcard_invoice_items`, and transition workflow/document statuses per design.

  **Description:** WF3 currently marks success without doing any work. Implement the full processing chain so FirstCard uploads trigger AI parsing and populate the matching tables.

  **How to verify:** Upload a FirstCard invoice via the Kortmatchning menu. Confirm `wf3.firstcard_invoice` logs meaningful stage information, the workflow run reaches `succeeded`, and new rows appear in `creditcard_invoices_main`/`creditcard_invoice_items`. Validate entries in `workflow_stage_runs` for WF3.

- [ ] **Task 6.4 - Audit workflow_stage_runs coverage**

  **System prompt for agent:** Review every workflow task (`wf1.*`, `wf2.*`, `wf3.*`) to ensure each significant step calls `mark_stage` with distinct stage keys, including start/end transitions and failure paths. Backfill missing stage writes where needed so `workflow_stage_runs` always reflects the full lifecycle.

  **Description:** We rely on `workflow_stage_runs` as the canonical progress log. Some tasks still skip stage logging; this task standardises the calls so observability matches the redesign spec.

  **How to verify:** Trigger WF1, WF2 and WF3 via their respective upload paths. Query `workflow_stage_runs` for each new `workflow_run_id` and verify all expected stage keys (dispatch, ocr, ai_pipeline, finalize, etc.) are present with appropriate status values (`running`, `succeeded`, `failed`, `skipped`). Cross-check with Celery logs for consistency.

  

#### **

- [x] **Task 1.1 - Unified files has wrong file_type and workflow_type**

​	**System prompt for agent:** Update this specific task using information in the MIND_WORKFLOW_REDESIGN.md. For history 	read the worklogs and claude.md.

​	**Description:** For a First Card - faktura uploaded from "Kortmatchning" the field unified_fields.file_type should be set to  	cc_pdf (if it is the pdf-file that is stored) and cc-image for png-files. It should on all the files have the 	unified_files.workflow_type 	set to 'creditcard_invoice'. This should be shown in the celery-logs for that workflow. 

​	**How to verify:** Verify by running the workflow again and checking results in db

-------

- [x] ​	**Task 1.2 - OCR merge missing**


​	**System prompt:**

**Description:** In unified_files the ocr_raw is populated from the ocr of th png-files - but this should be merged and inserted into creditcard_invoices_main - this is not done. Also make this visibible in the logs when it happens

**How to verify:**

-------

- [x] **Task 1.3. Add complete log functionality for the cc-invoice import**

  In kortmatchning when clicking on the "visa" - button, a complete log should be shown. This should show all the steps - and all details in each steps. This should include all the reasoning made by the AI, all the conversion steps, all the workflows - everything. Make a log that is perfect for developers.

**Phase 4 - AI-menu option **

- [x] **Task 4.1. Skapa menyval AI för systemprompter och inställningar**

- [x] Skapa två tabbar som start

  - [x] Task 4.2. LLM

  * Man ska i systemet kunna addera AI-modeller för
    OpenAI
    OpenRouter
    Ollama lokalt
    Antropic
    Gemini/Google
  * Andra
  * Man ska kunna välja specifik modell hos leverantören

- [x] **Task 4.3: Systemprompter (default då man väljer ai-menyn)**

  * Alla systemprompter ska ha rutor med flera rader. Dessa ska gå att öppna i modal där man får mer plats

  * Alla ska ha en titel och en kort beskrivning av vad den ska användas till

  * LLM-modell ska kunna väljas för varje prompt
    *

  - [x] **Task 4.3. AI - Analys Kvitto/Faktura/Övrigt** Skapa där en systemprompt som heter "Dokumentanalys". Ge möjlighet att välja AI-modell beroende på vad som finns att välja på i .env.

  - [x] **Task 4.4 - AI - Utlägg eller företag :** Skapa ett fält för systemprompt som heter "Utlägg eller företag". Ge möjlighet att välja AI-modell beroende på vad som finns att välja på i .env.

  - [x] **Task 4.5 - AI - Klassificering kvittoposter:** Skapa ett fält för systemprompt som heter "Klassificering av kvittoposter" - här görs prompt för den stora sorteringen av kvittodata

  - [x] **Task 4.6. AI - Kontering:** Skapa ett fält för systemprompt  kallad kontering. Här ska all information relaterat till

  Systemprompt och övriga inställningar görs under menyval AI. Skapa där en systemprompt som heter "Eget utlägg eller företag".

  - [x] **Task 4.7 - AI - First Card**: Prompt för att hantera matchningen av firstcard-fakturan mot befintliga kvitton

  

#### **Phase 5 - Process log in frontend**

- [x] **Task 5.1 - Rebuild menu option "Process"**

  **Description:** Jag vill göra om menyn "Process" och ändra denna så att resultat från alla olika workflow-faser presenteras enligt följande från vänster till höger i varsin kolumn. 

  Process: This should be great looking badges matching the design. Every badge should be possible to click to open a modal

  Title->DateTime->Upload -> FileName -> PDFConvert -> OCR -> AI1 -> AI2 -> AI3 -> AI4 -> AI5 -> Match

  **Title**: If exists: companies.name otherwise unified_files.id: Companies.name - if exists otherwise until it arrives original file name from unified files

  **Title**: If exists: companies.name otherwise unified_files.id: YYYY-MM-DD HH:MM - when conversion was started

  **Upload**: How was the file ingested (Answer: FTP or Upload)

  **PDFConvert:** Completed or N/A depending of if a conversion from pdf to png has been done. **RIGHT NOW - NOT IMPLEMENTED WRITE N/A**

  **OCR:** Status. Links to full OCR-text or error with all other fields available

  **AI1 - AI5:** Status badge showing data from the status-field for each AI-step. Link to should open a modal with full report of everything that is included for AI one in table ai_processing_history. 

  * id
  * file_id
  * job_type
  * status
  * created_at
  * ai_stage_name
  * log_text (FULL LOG TEXT!)
  * error_message
  * confidence
  * processing_time_ms
  * provider
  * model

  **How to verify:** Test with confirmed system-file to inject: @web/test_pdf.pdf for pdf-files. @web/test/test_image.jpg and confirm all the steps are providing the correct output in the modal

  

- [x] **Task 5.2 - Convert PDF to png**

  **Description:** If a PDF is uploaded (with the correct mime-type OR the correct file ending). This should be converted to a jpg at step 0. This should create a 300dpi png-picture with dpi configurable in the settings menu option. Do a full plan on how to implement this. Step by step. Add new task in this file. DO NOT IMPLEMENT THE FUNCTION YET.

  **How to verify:**
