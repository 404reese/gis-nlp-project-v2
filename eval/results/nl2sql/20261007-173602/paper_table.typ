#table(
  columns: (1fr, auto, auto, auto, auto),
  inset: 3pt,
  stroke: 0.5pt + gray,
  fill: (x, y) => if y == 0 { silver } else { none },
  [*Configuration*], [*Exact*], [*Geom. F1*], [*Executed*], [*Median s*],
  [Full engine], [74.4%], [88.4%], [100.0%], [4.5],
  [No repair stage], [74.4%], [88.4%], [100.0%], [n/a],
)