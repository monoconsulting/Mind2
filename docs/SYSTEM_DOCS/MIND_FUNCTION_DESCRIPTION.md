Excellent. Thank you for that detailed clarification. Based on your answers and the original technical document, I have now created a complete functional plan for the "Mind" system. This plan is written in plain English and describes the entire workflow from a user's perspective, including the necessary pages and features in the user interface.

------



## **Mind System: Functional Plan**

### **1. Overview**

The **Mind system** is designed to streamline expense management by digitizing and automating the entire lifecycle of a receipt. A user captures a photo of a receipt, and the system uses Artificial Intelligence (AI) to read, understand, and prepare it for accounting. An administrator can then review, manage, and finally export the data for their accountant in a standard format.

The system is divided into two main parts: a simple public-facing interface for capturing documents and a comprehensive admin area for management and processing.

------



### **2. Part 1: Capturing a Document (The User Experience)**

This is the process a regular user follows to submit a receipt or invoice. This happens on the public website, `mind.mono.se`, which is designed for quick and easy use on mobile devices.



#### **The Main Screen**

When a user visits the site, they are presented with a clean interface with three primary options:

- **"Take Photo":** A large, prominent button to immediately open the device's camera.
- **"Gallery":** A secondary button to select an existing image or PDF from the device's storage.
- **"Tags":** A button that likely leads to a view where the user can see or manage the tags they frequently use (this functionality can be defined further).



#### **The Capture and Submission Flow**

1. **Capture:** The user either takes a new photo or selects one from their gallery.
   - If taking a new photo, the system will ask **"Use this photo?"** and provide three choices: **"Re-take"** or **"Add another page"** or "**Finished**" . This allows for multi-page receipts to be submitted as a single entry. The user continues adding pages until they are finished.
2. **Tagging:** After the image(s) are confirmed, the user is shown a list of available **tags** (e.g., "Project X," "Sales Trip," "Client Lunch"). These tags are predefined in the admin area. The user can select one or more tags to categorize the expense.
3. **Geolocation:** The system then asks a simple question: **"Add location data?"** with **"Yes"** and **"No"** options. This allows the system to optionally store where the receipt was captured. Nothing else than yes or no needs to be shown
4. **Submission:** The user confirms the submission. The system uploads the image file(s) and a small data file (containing the selected tags and geolocation choice) to the server for processing. The user's task is now complete.

------



### **3. Part 2: Automated AI Processing (The Backend Workflow)**

Once a document is submitted, the system's automated AI pipeline begins its work. The user does not see these steps directly, but their results are visible in the admin area.

1. **Step A: Reading the Text:** The system analyzes the image and reads all visible text, converting the picture of the receipt into a plain text document. If it is two or more photos assigned to the same receipts (some have more than one page) this must be handled.
2. **Step B: Classifying the Document:** The AI reads the text to determine what kind of document it is. It classifies it as a **"Receipt,"** **"Invoice,"** or **"Other."** If it's "Other," or "Invoice" the process may stop for now. Further functionality later. For receipts, it continues.
3. **Step C: Extracting Key Information:** For receipts, the AI carefully extracts important details, such as:
   - Merchant Name (e.g., "Pressbyrån")
   - Organization Number (`orgnr`)
   - Date and Time of Purchase
   - Total Amount, Net Amount, and VAT Amount (broken down by VAT rate: 25%, 12%, 6%, 0%)
   - Individual line items (e.g., "Kaffe," "Bulle")
   - Document type - The AI should decide if this is something that is bought using a company credit card (there is a set of rules to identify that) or if it is expenses - the user paid himself - and should get money back. The rules on how to identify this must be set in the ai-setup
4. **Step D: Quality Control & Validation:** The system automatically double-checks the AI's work. It verifies that the math is correct (line items add up to the total), that VAT rates are valid, and that the date is reasonable. The result of this check is a status:
   - `Passed`: Everything looks correct.
   - `Failed`: A critical error was found (e.g., the numbers don't add up). This requires mandatory review.
   - `Manual Review`: The math is correct, but the AI's confidence was low. This is a recommendation for a human to double-check.
5. **Step E: Enriching Company Data:** If a Swedish organization number (`orgnr`) was found, the system automatically looks it up in the official Swedish Companies Registration Office (`Bolagsverket`) database to fetch the official company name.
6. **Step F: Generating Accounting Entries:** Based on the extracted data and pre-defined rules, the system proposes a complete set of accounting entries (`kontering`) using the Swedish BAS chart of accounts. For example, it will debit the correct expense account (e.g., 5611 for Fuel), debit the input VAT account (2641), and credit the payment account (e.g., 1930 for Bank).

------



### **4. Part 3: The Admin Interface**

This is the control center for an administrator to manage the entire process.

#### **The Receipts Dashboard**

This is the main view in the "Receipts" section. It's a list of all submitted documents with sortable columns:

- **Status:** A color-coded indicator showing the current state (`Processing`, `Passed`, `Failed`, `Needs Review`, `Completed`).
- **Date:** The purchase date from the receipt.
- **Merchant:** The name of the seller.
- **User:** The person who submitted the receipt.
- **Total Amount:** The gross total of the receipt.
- **Tags:** The tags assigned during upload.

This page includes powerful **search and filter** functions, allowing the admin to easily find receipts (e.g., show all receipts from last month that are marked as "Failed").

#### **The Receipt Detail & Review View**

Clicking on any receipt in the dashboard opens this detailed view. This is where manual review and corrections happen. The screen is split into sections:

- **Image Viewer:** A clear view of the original receipt image. All the fields on the image that is correlated to a field in the database should be higlighted in yellow, and on mouseover it should display the field name
- **Extracted Data:** All the fields the AI extracted (Merchant, Date, Totals, Line Items, etc.). **Every field here is editable.**
- **Validation Report:** The results from the Quality Control step, with clear messages for any failures or warnings (e.g., "Warning: Sum of line items differs from total by 0.10 SEK").
- **Proposed Accounting Entries:** The accounting entries generated by the AI. The admin can **edit the accounts, amounts, and add notes** before approving.

The admin's primary action here is to review the data, make any necessary corrections, and finally click an **"Approve"** button to finalize the entry.

#### **The Accounting Rules Page (New Section)**

This is a new page under "Settings" where an admin can manage the logic for automatic accounting. The interface allows an admin to **create, edit, and delete rules**. A rule could be:

- "If a receipt's **merchant name contains** `Circle K` or `OKQ8`, then use expense **account** `5611` (Vehicle Fuel)."
- "If a receipt has a **line item containing** the word `Taxi`, then use expense **account** `5820` (Travel Expenses)."

This powerful feature allows the organization to customize the AI's behavior to fit its specific needs.

### Matching to Company Card

A company invoice is receieved every month which should be matched to expense type "company" - which means it is paid by the company card.

* This should be handled from a menu that says "Företagskort" in swedish or "Company card" in english. 
* When a new invoice is uploaded AI should read and store the content of this file, and then automatically match this to the available receipts. This should be possible to edit if AI picks the wrong one. 

------



### **5. Part 4: ** **Exporting for Accounting**

This is the final step in the workflow, also located within the admin area.

#### **The Export Page**

##### Receipts

This page allows the administrator to generate an export of all approved accounting data. The interface is simple:

1. The admin selects a **Date Range** (e.g., "Last Month" or a custom range).
2. The admin clicks the **"Generate SIE File"** button.

The system then compiles all the approved accounting entries from that period into a single, standardized **SIE file**. This file can be downloaded and sent directly to the company's accountant, who can import it into their professional accounting software with a single click. This eliminates manual data entry and ensures accuracy.

##### Company card

The system exports a file which contains the Company Card Invoice together with all the receipts with complete data.