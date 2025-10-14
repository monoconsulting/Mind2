





@.prompts\start.prompt.md

jag tänkte nu börja arbeta på matchning av kreditkortsfaktura mot kvitton. Jag skulle vilja att du analyserar kodbasen och undersöker vad som är implementerat av denna funktionalitet. Först ska en faktura laddas upp, och det är enklast att vi gör det i menyn för kortmatchning. Denna processas med pdfkonvertering om det krävs, och därefter ocr. Då detta är klart ska alla poster på fakturan läsas in i databasen. Slutligen ska matchning ske med hjälp av AI5 där alla kvitton ska gås igenom. Om kvittot har samma inköpsdatum, samma försäljningsställe och samma belopp så matchas dessa och det ska flaggas i creditcard_receipt_matches. På sidan kortmatchning så ska man kunna välja mellan de olika månadsfakturorna under kontoutdrag, och klickar man på ett i rutan "Företagskort" så ska samtliga poster på den kreditkortsfakturan visas med de kolumner som finns på fakturan, samt med en ruta som säger att den är matchad (grön bock) eller inte. Man ska kunna klicka på företagsnamnet och få upp previewmodalen för kvitton för att kunna granska. Om kvittot är matchat så ska det också finnas en grön bock längst uppe till höger i modalen som det står Matchad under. Läs igenom 