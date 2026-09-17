# Discovery Test DSDs

These files are synthetic benchmark fixtures. They are not official agency DSDs and must not be presented as authoritative standards.

| Local DSD | Expected discovery result | What it demonstrates |
| --- | --- | --- |
| `local-employment.xml` | Employment reference first, Strong | Exact component, label, code-label, representation, and labour-domain evidence |
| `local-tourism.xml` | Tourism reference first, Strong | Domain-specific concepts and tourism code labels |
| `local-prices.xml` | Consumer price reference first, Strong | Price concepts and consumption-classification code labels |
| `local-mixed-domain.xml` | Three Plausible candidates | Generic dimensions are insufficient to identify one authoritative standard |
| `local-no-match.xml` | No suitable reference standard identified | A valid no-match outcome; the application must not force a candidate |

## How to Test

1. Open the Streamlit application.
2. Upload one XML file using **Local DSD**.
3. Select **Discover standards**.
4. Compare the displayed candidates and evidence with the table above.
5. For a domain-specific fixture, select the expected reference to inspect the detailed alignment findings.

The three domain-specific samples intentionally share some generic concepts such as `REF_AREA` and `FREQ`. This allows the application to show weaker alternatives while keeping the domain-relevant reference first.

