#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge

#set page(width: auto, height: auto, margin: 0pt, fill: none)


#let dark-blue = rgb("#0f427c")
#let light-bg = rgb("#f2f4f7")
#let border-gray = rgb("#c0c4cc")

#let draw-node(pos, name, icon, line1, line2) = {
  node(pos, name: name, 
    block(
      width: 17em,
      stroke: 1.5pt + dark-blue,
      radius: 4pt,
      fill: white,
      clip: true,
      grid(
        columns: (3.5em, 1fr),
        align: center+horizon,
        block(width: 100%, height: 100%, inset: 0.5em, align(center+horizon)[#text(size: 1.8em)[#icon]]),
        block(inset: (top: 0.8em, bottom: 0.8em, left: 0em, right: 0.5em), align(left)[
          #text(weight: "bold", size: 0.9em)[#line1]\
          #text(size: 0.8em)[#line2]
        ])
      )
    )
  )
}

// Helper function for the database node with a dark blue left section
#let draw-db-node(pos, name, icon, line1, line2) = {
  node(pos, name: name, 
    block(
      width: 17em,
      stroke: 1.5pt + dark-blue,
      radius: 4pt,
      fill: white,
      clip: true,
      grid(
        columns: (3.5em, 1fr),
        align: center+horizon,
        block(width: 100%, height: 100%, fill: dark-blue, inset: 0.5em, align(center+horizon)[#text(size: 1.8em, fill: white)[#icon]]),
        block(inset: (top: 0.8em, bottom: 0.8em, left: 0em, right: 0.5em), align(left)[
          #text(weight: "bold", size: 0.9em)[#line1]\
          #text(size: 0.8em)[#line2]
        ])
      )
    )
  )
}

// Global edge styling
#let edge-style = (stroke: 1.5pt + dark-blue, corner-radius: 6pt)
#let retry-style = (stroke: (paint: dark-blue, thickness: 1.5pt, dash: "dashed"), corner-radius: 6pt)
#let box-style = (fill: light-bg, stroke: 1.5pt + border-gray, corner-radius: 5pt, layer: -1, inset: 1.2em)

// Pipeline of the NL -> PostGIS engine (app/services/geo_engine.py):
// intent check -> SQL generation -> validation -> read-only execution -> repair loop
// -> GeoJSON + explanation + SQL -> map. Left column runs down, right column runs up.
#align(center)[
  #diagram(
    // Sets the base global unit spacing. (x, y)
    spacing: (13em, 4em),

    // --- 1. ENCLOSURE LABELS ---
    node((0, -0.5), [*Input*], name: <L_In>),
    node((0, 0.7), [*Query generation*], name: <L_Proc>),
    node((1, -0.5), [*Output*], name: <L_Out>),
    node((1, 1.7), [*Backend*], name: <L_Back>),

    // --- 2. NODES ---
    // Column 0 (left, top to bottom)
    draw-node((0, 0), <A>, "👤", "User Input:", "Natural Language Question"),
    draw-node((0, 1), <B>, "🧠", "Intent Check (LLM):", "Clear query? else follow-up"),
    draw-node((0, 2), <C>, "⚙️", "SQL Generation (LLM):", "Schema description in prompt"),
    draw-node((0, 3), <D>, "🛡️", "Validation:", "Single read-only SELECT"),

    // Column 1 (right, bottom to top)
    draw-db-node((1, 3), <E>, "🛢️", "Execution: PostGIS", "geo_readonly, 15 s timeout"),
    draw-node((1, 2), <F>, "🔁", "Repair Loop:", "On DB error or 0 rows (bounded)"),
    draw-node((1, 1), <G>, "📋", "Result: GeoJSON", "+ Explanation + SQL"),
    draw-node((1, 0), <H>, "🖥️", "Visualization:", "Interactive Map + UI"),

    // --- 3. BACKGROUND GROUP BOXES ---
    node(enclose: (<L_In>, <A>), ..box-style),
    node(enclose: (<L_Proc>, <B>, <C>, <D>), ..box-style),
    node(enclose: (<L_Out>, <G>, <H>), ..box-style),
    node(enclose: (<L_Back>, <E>, <F>), ..box-style),

    // --- 4. EDGES ---
    edge(<A>, <B>, "-|>", ..edge-style),
    edge(<B>, <C>, "-|>", ..edge-style),
    edge(<C>, <D>, "-|>", ..edge-style),
    edge(<D>, <E>, "-|>", ..edge-style),
    // Repair: the error (or the empty result) goes back to the SQL generator.
    edge(<F>, <C>, "-|>", label: text(size: 0.75em)[error / 0 rows: retry], label-side: left, ..retry-style),
    edge(<E>, <F>, "-|>", ..edge-style),
    edge(<F>, <G>, "-|>", ..edge-style),
    edge(<G>, <H>, "-|>", ..edge-style),
  )
]
