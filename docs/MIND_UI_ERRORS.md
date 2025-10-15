# Registred errors in UI





# 2025-10-15 05:59

## 1) Process

- [ ] 1.1. Remove all processing data for files related to the cc-process (Kortmatchning). This should be shown in menu option "Kortmatchning"
- [ ] 1.2. Search functionality is not working
- [ ] 1.3. Add filter for "Dokumenttyp" so it is possible to only search on "Kvitto" or "Övrigt". Add an option to show files that are soft deleted. 
- [ ] 1.4. Change the dustbin to a restore-button to restore status from soft_deleted to not soft_delted if the sorting enables the view of soft deleted files. 
- [ ] 1.5. Remove the flickering when updating page. But keep all the functionality	

## 2) Preview Modal

- [ ] 2.0. When editing fields - if a user is entering "," as separator in amount this should be converted to "." before inserting into db. 
- [ ] 2.1. Add arrows to change back and forward between items
- [ ] 2.2. Investigate why the card-detail always fails
- [ ] 2.3. In block "Belopp" automatically set "Originalbelopp ink.moms" and "Originalbelopp ex. moms" to same values as "Svenskt totalbelopp ink moms SEK" and "Svenskt totalbelopp ex moms"
- [ ] 2.4. In block "Belopp" automatically count the moms-values for "Moms 25%", "Moms 12%", "Moms 6%" if "Svenskt totalbelopp ink moms" and "Svenskt totalbelopp ex moms" is given.
- [ ] In "Varor och kontering" - "Artikel" - make sure only the description of the item is stored. Moms, amount or other details should not be stored here
- [ ] Everywhere in the Modal: 

## 3) Kortmatchning

## 4) AI

## 5) Inställningar

## 6) Användare

## 7) DB

- [ ] Add timestamps "created_at", "updated_at" for creditcard_invoice_main and creditcard_invoice_items

## 8) Workflow

- [ ] Separate workflows must be created. One for receipts that right now triggers from the process-upload/ftp-fetch. One that triggers exclusively from Kortmatchning -> Ladda upp utdrag. These 2 workflows must be handled separately. This means that they should have separate steps for conversion, separate workflow-badges, separate status updates, separate ai-handling. We must have a 100% safe definition that the code is following exactly and can never go away from. Engines should be possible to re use - like ocr  - but it should be called from the workflow. When done - it should return to its workflow. I want to have a very clear understanding of how this can be implemented and how we should update the current code to follow this new standard. I prefer to use a database where all the executions in the different workflows should be run from. 

