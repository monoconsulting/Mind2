# MIND - TASK LIST

Notes to agent:
This must be used to keep track of tasks. As soon as you finished a task you MUST mark it done in this document.
Add the tasks in english using the following standard:

#### **Phase 1 - Description of the phase**

- [ ] **Task 1.1 - Task title**

  **System prompt for agent:** A specific clear and very descriptive system prompt for the agent.

  **Description:** Description of the task

  **How to verify:** Description of how this should be verified and presented to the user

- [ ] **Task 1.2 - Task title**

  **System prompt:**

  **Description:** 

  **How to verify:**

_______________________

#### **Phase 1 - Data Fetching for OCR Visualization**

- [x] **Task 1.1 - Fetch OCR Bounding Box Data**

  **System prompt for agent:** Modify the `main-system/app-frontend/src/ui/pages/Receipts.jsx` file. Create a new state within the `PreviewModal` component to store OCR box data, e.g., `const [ocrBoxes, setOcrBoxes] = React.useState([])`. When the modal is opened and an image is being loaded for a receipt, make an additional asynchronous API call to `/ai/api/receipts/<receipt_id>/ocr/boxes`. Once the data is fetched, update the `ocrBoxes` state with the resulting array. Ensure this is done concurrently with the image fetch.

  **Description:** The backend provides an endpoint with OCR data containing text and coordinates. This task is to fetch this data when a user opens the receipt image preview modal and store it in the component's state.

  **How to verify:** Use the browser's developer tools to inspect network requests when opening a receipt preview. Confirm that a request is made to `/ai/api/receipts/<receipt_id>/ocr/boxes`. Use React Developer Tools to inspect the `PreviewModal` component and verify that its `ocrBoxes` state contains an array of box data.

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

  

Databas: 
