# Licence log

Every data source must be recorded here before ingestion (URL, terms, date accessed, what we may store and serve).

| Source | URL | Terms summary | Accessed | Store? | Serve? |
|---|---|---|---|---|---|
| The Constitution of India [As on 1st May, 2024], Legislative Department, Ministry of Law and Justice (diglot edition; English pages used) | https://cdnbbsr.s3waas.gov.in/s380537a945c7aaa788ccfcdf1b99b5d8f/uploads/2024/07/20240716890312078.pdf | Official Government of India publication of an enactment. Text is quoted with a link to the exact page. Not an authenticated copy for court use. | 2026-10-25 | Yes (downloaded on demand, not committed) | Yes, with source + page link |
| Indian Supreme Court Judgments (AWS Open Data, maintained by Dattam Labs; judgments as published by the Supreme Court in e-SCR, sourced from eCourts) | https://registry.opendata.aws/indian-supreme-court-judgments/ | **CC-BY-4.0**. Attribute: "Indian Supreme Court Judgments, Dattam Labs, registry.opendata.aws/indian-supreme-court-judgments, accessed 2026-10-25". | 2026-10-25 | Yes (PDFs cached in `data/raw/`, not committed) | Yes, with attribution |
| Music: Edvard Grieg, Peer Gynt Suite No. 1, Op. 46 - I. Morning Mood and II. The Death of Aase, Musopen Symphony (used in docs/trailer.mp4 and docs/product_video.mp4) | https://commons.wikimedia.org/wiki/File:Grieg_-_Peer_Gynt_Suite_No._1,_Op._46_-_I._Morning_Mood_(Musopen_Symphony).flac and https://commons.wikimedia.org/wiki/File:Grieg_-_Peer_Gynt_Suite_No._1,_Op._46_-_II._The_Death_of_Aase_(Musopen_Symphony).flac | Composition and recording both **Public domain** (Commons metadata: License pd, Copyrighted: False). No attribution required. | 2026-10-26 | Yes (`data/music/`, not committed) | Yes |
| Sample corpus (`data/sample/`) | n/a | Fictional judgments written for testing. Parties, citations (`FSR`, `FSC`) and facts are invented. Used by tests only. | 2026-10-25 | Yes | Tests only |

Judgment text may contain personal data of parties. Do not attempt to de-anonymise anonymised judgments (see README, Data section).
