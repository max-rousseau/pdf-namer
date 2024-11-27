First - In a few words, summarize the key identifiers for the PDF file below, based on its contents.
This will be used as the filename. If you are able to tell, also include "Maxime" or "Amanda" when the document is intended specifically for one or the other.

Second - You need to identify if the PDF is dated, for example invoice date. If the document is dated provide the date in the format YYYY.MM.DD. Otherwise, return None for date.

Here are some examples to help you:

2023.07.23 - Verizon MyBill.pdf
2024.01.08 - Fidelity Amanda Dependent Care FSA.pdf
2024.01.08 - HealthEquity Maxime Preschool Claim.pdf
2024.02.29 - Fidelity Amanda Statement.pdf
2024.03.25 - One Medical Receipt 14843256.pdf
2024.03.26 - MorganStanley MSFT Sale - StockPlan Connect.pdf
2024.03.29 - Service Champions Invoice #2503621.pdf
2024.03.31 - Vanguard Evelyn Statement.pdf
2024.04.09 - Maxime Vision Script Optique.pdf
2024.04.20 - Premera Amanda EoB.pdf
2024.04.25 - Bay Area Moisture Control - Service Record.pdf
2024.04.26 - Amanda Macan Purchase Contract Carlsen.pdf
2024.04.26 - Bay Area Moisture Control Invoice 15657.pdf
2024.04.26 - Carmax Sale Amanda Macan.pdf

Respond only using JSON format, conforming to this schema: 
{{"filename": "Carmax Sale Amanda Macan.pdf", "date": "2024.04.26"\\}}
{{"filename": "Some reference document.pdf", "date": None\\}}

Now here is the file:

```pdf{text}```
