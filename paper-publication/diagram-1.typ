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
#let box-style = (fill: light-bg, stroke: 1.5pt + border-gray, corner-radius: 5pt, layer: -1, inset: 1.2em)

#align(center)[
  #diagram(
    // Sets the base global unit spacing. (x, y) 
    spacing: (13em, 4em), 
    
    // --- 1. ENCLOSURE LABELS ---
    node((0, -0.5), [*Input*], name: <L_In>),
    node((0, 0.7), [*Processing*], name: <L_Proc>,),
    node((1, -0.5), [*Backend*], name: <L_Back>),
    node((1, 1.7), [*Output*], name: <L_Out>),

    // --- 2. NODES ---
    // Column 0 (Left Side)
    draw-node((0,0), <A>, "👤", "User Input:", "Natural Language Query"),
    
    draw-node((0,1), <B>, "🧠", "NLP Processing:", "Intent + Entities"),
    draw-node((0,2), <C>, "🌐", "Geocoding:", "Place " + sym.arrow.r + " Coordinates"),
    draw-node((0,3), <D>, "🗄️", "Query Engine: SQL", "Generation & Validation"),
    
    // Column 2 (Right Side)
    draw-db-node((1,0), <E>, "🛢️", "Spatial DB:", "PostgreSQL + PostGIS"),
    draw-node((1,1), <F>, "📋", "Decision/Scoring:", "Multi-factor Evaluation"),
    
    draw-node((1,2), <G>, "🗺️", "Result: GeoJSON", "+ Explanation"),
    draw-node((1,3), <H>, "🖥️", "Visualization:", "Interactive Map + UI"),

    // --- 3. BACKGROUND GROUP BOXES ---
    node(enclose: (<L_In>, <A>), ..box-style),
    node(enclose: (<L_Proc>, <B>, <C>, <D>), ..box-style),
    node(enclose: (<L_Back>, <E>, <F>), ..box-style),
    node(enclose: (<L_Out>, <G>, <H>), ..box-style),

    // --- 4. EDGES ---
    // A -> B (Leaves right of A, drops down, enters right of B)
    edge(<A>, (0.4, 0), (0.4, 1), <B>, "-|>", ..edge-style),
    
    // B -> C (Straight down)
    edge(<B>, <C>, "-|>", ..edge-style),
    
    // C -> D (Straight down)
    edge(<C>, <D>, "-|>", ..edge-style),

    // D -> E (Leaves right of D, travels up, enters left of E)
    edge(<D>, (0.5, 3), (0.5, 0), <E>, "-|>", ..edge-style),

    // F -> G (Leaves left of F, travels down, enters left of G)
    edge(<F>, (0.6, 1), (0.6, 2), <G>, "-|>", ..edge-style),

    // G -> H (Straight down)
    edge(<G>, <H>, "-|>", ..edge-style),
  )
]