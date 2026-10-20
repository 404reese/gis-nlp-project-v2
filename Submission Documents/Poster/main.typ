#set page(height: 90cm, width: 63.6cm)
#set page(margin: (top:8.3cm,left:2.55cm, bottom: 2.55cm, right: 2.55cm))

#let power-red = rgb("#B7202E")

#import "@preview/fletcher:0.5.8" as fletcher: node, edge

#set page(header: [
  #table(
    stroke:none,
    columns: (1.4fr,auto,1fr),
    align: (left+horizon,center+horizon,center+horizon),
    [#image("kjsit.svg",height: 3.8cm)],[#text(size: 60pt, fill: power-red, font: "Times New Roman")[K.J. SOMAIYA INSTITUTE OF\ TECHNOLOGY]\ #text(size:40pt, fill: power-red, font: "Times New Roman")[Department of Artificial Intelligence and Data Science]],[#image("trust.svg",height: 3.8cm)]
  )

  #align(center+bottom)[#line(length: 63.6cm, stroke: 6pt+ power-red)]
])

#set page(footer: [
  #place(
  bottom + right,
  dx: 2.55cm,
  rect(width: 25cm, height: 2.55cm, fill: power-red)
),
#place(
  bottom + right,
  dx: 2.55cm,
  rect(width: 2.50cm, height: 12cm, fill: power-red)
),
#place(
  bottom + right,
  dx: -22.44cm,
  rect(width: 3.25cm, height: 2.55cm, fill: rgb("#ED1C24"))
)])

#align(center)[#text(size: 34pt, font: "Times New Roman")[= *Geospatial Query System with Natural Language Processing and GIS Integration*]
#text(size: 32pt, font: "Times New Roman")[Riddhesh Chaudhary, Arpit Balmiki, Chirayu Vyas\
Guide: Dr. Vaishali Wadhe]]
#line(length: 100%, stroke: 5pt + power-red)
#place(
 // Place it on the page background
  left + top,      // Align to the top-left corner
  dx: 50%,         // Move 50% of the PAGE width to the right
  dy: 160pt,
  // Draw the line, 100% of the PAGE height
  line(length: 73.35cm, stroke: 5pt+ power-red, angle: 90deg)
)

#set text(size: 28pt, font: "Times New Roman")
#set par(justify: true)

#show heading.where(level: 1): set text(
  fill: power-red,
  size: 40pt,
  font: "Times New Roman"
)

#columns(2)[
  #grid(
    columns: 1,
    rows: auto,
    gutter: 40pt,

    [
      = Abstract
      Choosing where to open a business usually means weeks of manual surveys and scattered research across maps, listings and reports. This project presents a natural-language spatial intelligence platform for real estate and business site selection in Mumbai. A user asks a question in plain English, such as "safest area near a metro for a cafe", and an LLM pipeline translates it into verified spatial SQL over a live PostGIS database of roads, points of interest, real estate listings, crime zones and transit stops. The answer is returned as an interactive map with a short explanation, the generated SQL and a data-grounded budget estimate, turning a multi-week survey into a single instant query.
    ],

    [
      = Background
      Traditional GIS tools demand expertise in spatial data, SQL and specialised software, which keeps location intelligence out of reach for most businesses. Recent work on LLM-based GIS and spatial Text-to-SQL (LLM-Geo, NALSpatial, GS-SQL, GeoLLM) is promising, but still lacks query testing and logging, depends on predefined mapping rules, and struggles with multi-entity spatial reasoning and distance errors. Our system addresses these gaps with schema-grounded intent parsing, multi-step query planning, metre-accurate distance handling and a validation loop before execution, all grounded in real city data.

      #figure(
        image("fig_competition.jpg", width: 100%),
        caption: [GeoQuery workspace: competition and catchment analysis for a cafe at Vikhroli],
      )
    ],

    [
      = Objectives
      - Simplify site selection so businesses can find and evaluate new locations without manual survey work.
      - Generate automatic, data-grounded cost estimates (rent, setup, licenses) for any chosen spot.
      - Compare locations side by side on nearby comparables, footfall, amenity density, safety and transit access.
      - Replace scattered research across sources with a single natural-language query.
      - Save time and cost with instant, grounded answers instead of weeks of on-ground survey.
    ],

    [
      = Acknowledgement
      This research work is supported by K. J. Somaiya Institute of Technology.
    ],
  )
  #colbreak()
  #grid(
    columns: 1,
    rows: auto,
    gutter: 40pt,

    [
      = Methodology
      A FastAPI backend receives the plain-English query and passes it to an LLM pipeline that classifies intent, grounds it in the database schema, plans the query and generates spatial SQL. The SQL runs on a PostGIS database, and a validation and correction loop re-plans any query that fails or returns empty results. Validated results are converted to GeoJSON and rendered on an interactive MapLibre map.

      #figure(
        {
          set text(size: 26pt)
          let sub(t) = text(size: 22pt, fill: luma(90), emph(t))
          fletcher.diagram(
            spacing: (14mm, 14mm),
            node-stroke: 1.5pt + rgb("#2c3e50"),
            node-fill: rgb("#f8f9fa"),
            node-inset: 12pt,
            node-corner-radius: 4pt,
            edge-stroke: 2.5pt + rgb("#2c3e50"),

            node((0, 0), align(center)[*User Input*\ #sub[(Natural Language)]]),
            edge((0, 0), (1, 0), "->"),
            node((1, 0), align(center)[*FastAPI*\ *Backend*]),
            edge((1, 0), (2, 0), "->"),
            node((2, 0), align(center)[*LLM Pipeline*\ #sub[(Intent, Schema, SQL)]]),
            edge((2, 0), (2, 1), "->"),

            node((2, 1), align(center)[*PostGIS Database*\ *Execution*]),
            edge((2, 1), (1, 1), "->"),
            node((1, 1), align(center)[*Validation*\ *Correction Loop*]),
            edge((1, 1), (0, 1), "->"),
            node((0, 1), align(center)[*GeoJSON*\ *Generation*]),
            edge((0, 1), (0, 2), "->"),

            node((0, 2), align(center)[*MapLibre Rendering*\ #sub[(Answer Layer)]], fill: rgb("#e8f5e9"), stroke: 1.5pt + rgb("#2e7d32")),
          )
        },
        caption: [Proposed Methodology],
      )
    ],

    [
      = Results and Discussion
      The platform runs on live Mumbai data: 48 administrative boundaries, 16,800+ road segments, 10,800+ points of interest, 55,600+ real estate listings, 2,200+ transit stops and 40 crime-safety zones. Answers arrive in seconds with a map, an explanation and the SQL behind them. In evaluation, it estimated about ₹62 lakh to open a café in Bandra and about ₹1.3 crore for a premium restaurant in Lower Parel.

      #figure(
        grid(
          columns: 2,
          column-gutter: 1cm,
          align: top,
          image("fig_compare.jpg", width: 15.5cm),
          image("fig_plan_1.jpg", height: 12cm),
        ),
        caption: [Location comparison (Kanjurmarg vs Vikhroli) and cost-to-open report for a cafe],
      )
    ],

    [
      = Conclusion
      Natural-language spatial intelligence makes location decisions accessible to businesses without GIS or data teams. One verifiable query interface replaces weeks of scattered research, and the city-agnostic design allows extension well beyond Mumbai.
    ],

    [
      = References
      #set text(size: 24pt)
      #set par(justify: false)
      #pad(right: 1.5cm)[
      [1] A. K. Kazazi, Z. Li, M. N. Lessani, and G. Cervone, "From Questions to Queries: An AI-powered Multi-Agent Framework for Spatial Text-to-SQL," arXiv, 2025.

      [2] X. Zhang, F. Xiao, L. Yan, and Z. Zhang, "GS-SQL: Modeling Spatial Semantics in Spatial Text-to-SQL," IJCNN, 2024.

      [3] J. Malczewski, "GIS-based multicriteria decision analysis: a survey of the literature," Int. J. Geographical Information Science, vol. 20, no. 7, pp. 703–726, 2006.

      [4] Felt, "Felt AI: AI-powered GIS and mapping platform," Felt Help Center, 2025. [Online]. Available: https://help.felt.com/felt-ai
      ]
    ],
  )
]
