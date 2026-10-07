"""Benchmark questions for the NL -> PostGIS engine, each with a hand-written gold query.

Every gold query is a single read-only SELECT that returns the answer layer (a `geom` column,
plus `name` where the entity has one) for city_id = 1 (Mumbai). Expected answers are the
EXECUTED RESULTS of these queries on the loaded database, not stored strings, so the
benchmark stays valid when the data is reloaded.

Conventions follow the engine's own schema notes (app/services/geo_engine.py SCHEMA_DOC):
  * "hospital"   -> poi.place.category IN ('hospital','clinic','doctors')
  * "in <area>"  -> a point within 2 km of a crime.area gazetteer row matching the name
  * distances use geography casts, in metres

Fields
  id         stable identifier
  category   filter | proximity | area | ranking | listing | compositional
  difficulty easy | medium | hard
  question   what the user types
  gold       gold SQL (city_id = 1)
  ordered    True when the order of the rows is part of the answer (ranking questions)
  note       why this gold interpretation is the intended one (only where it is not obvious)

Ranking questions order by safety_score and then name. The cut-offs (top 5 safest, 3 least
safe, top 8 safest) were chosen so that no two areas tie at the boundary in
app/data/crime.json (checked against eval/results/weight_study/B2_safety_scores_by_area.csv),
so a correct alternative query returns the same rows. C06 additionally depends on which
areas have a metro stop within 2 km; check it with --validate-gold after a data reload.
"""

HOSPITAL = "('hospital','clinic','doctors')"


def _near(a_alias: str, b_alias: str, metres: int) -> str:
    return f"ST_DWithin({a_alias}.geom::geography, {b_alias}.geom::geography, {metres})"


def _in_area(area: str) -> str:
    """Gazetteer-based 'in <area>' join, exactly as the schema notes prescribe."""
    return (
        f"JOIN crime.area a ON a.city_id = 1 AND a.name ILIKE '%{area}%' "
        f"AND ST_DWithin(p.geom::geography, a.geom::geography, 2000)"
    )


QUESTIONS = [
    # ------------------------------------------------------------------ filter (easy)
    dict(id="F01", category="filter", difficulty="easy",
         question="Show all pharmacies in the city.",
         gold="SELECT name, geom FROM poi.place WHERE city_id = 1 AND category = 'pharmacy'"),
    dict(id="F02", category="filter", difficulty="easy",
         question="Where are the cinemas?",
         gold="SELECT name, geom FROM poi.place WHERE city_id = 1 AND category = 'cinema'"),
    dict(id="F03", category="filter", difficulty="easy",
         question="List all police stations.",
         gold="SELECT name, geom FROM poi.place WHERE city_id = 1 AND category = 'police'"),
    dict(id="F04", category="filter", difficulty="easy",
         question="Show fuel stations.",
         gold="SELECT name, geom FROM poi.place WHERE city_id = 1 AND category = 'fuel'"),
    dict(id="F05", category="filter", difficulty="easy",
         question="Find all universities.",
         gold="SELECT name, geom FROM poi.place WHERE city_id = 1 AND category = 'university'"),
    dict(id="F06", category="filter", difficulty="easy",
         question="Show every hotel.",
         gold="SELECT name, geom FROM poi.place WHERE city_id = 1 AND category = 'hotel'"),
    dict(id="F07", category="filter", difficulty="easy",
         question="Show all hospitals.",
         gold=f"SELECT name, geom FROM poi.place WHERE city_id = 1 AND category IN {HOSPITAL}",
         note="Uses the schema notes' hospital rule (hospital, clinic, doctors)."),
    dict(id="F08", category="filter", difficulty="easy",
         question="Where are the metro stops?",
         gold="SELECT name, geom FROM transport.stop WHERE city_id = 1 AND mode = 'metro'"),
    dict(id="F09", category="filter", difficulty="easy",
         question="Show the fire stations.",
         gold="SELECT name, geom FROM poi.place WHERE city_id = 1 AND category = 'fire_station'"),
    dict(id="F10", category="filter", difficulty="easy",
         question="Show the motorways.",
         gold="SELECT name, geom FROM roads.segment WHERE city_id = 1 AND highway_class = 'motorway'"),

    # --------------------------------------------------------------- proximity (medium)
    dict(id="P01", category="proximity", difficulty="medium",
         question="Cafes within 500 m of a metro station.",
         gold=("SELECT DISTINCT p.name, p.geom FROM poi.place p JOIN transport.stop s "
               "ON s.city_id = 1 AND s.mode = 'metro' AND " + _near("p", "s", 500) +
               " WHERE p.city_id = 1 AND p.category = 'cafe'")),
    dict(id="P02", category="proximity", difficulty="medium",
         question="Hospitals within 1 km of a railway station.",
         gold=("SELECT DISTINCT p.name, p.geom FROM poi.place p JOIN transport.stop s "
               "ON s.city_id = 1 AND s.mode = 'rail' AND " + _near("p", "s", 1000) +
               f" WHERE p.city_id = 1 AND p.category IN {HOSPITAL}")),
    dict(id="P03", category="proximity", difficulty="medium",
         question="Banks within 300 m of a bus stop.",
         gold=("SELECT DISTINCT p.name, p.geom FROM poi.place p JOIN transport.stop s "
               "ON s.city_id = 1 AND s.mode = 'bus' AND " + _near("p", "s", 300) +
               " WHERE p.city_id = 1 AND p.category = 'bank'")),
    dict(id="P04", category="proximity", difficulty="medium",
         question="Pharmacies within 200 m of a hospital.",
         gold=("SELECT DISTINCT p.name, p.geom FROM poi.place p JOIN poi.place h "
               f"ON h.city_id = 1 AND h.category IN {HOSPITAL} AND " + _near("p", "h", 200) +
               " WHERE p.city_id = 1 AND p.category = 'pharmacy'")),
    dict(id="P05", category="proximity", difficulty="medium",
         question="Schools within 500 m of a metro station.",
         gold=("SELECT DISTINCT p.name, p.geom FROM poi.place p JOIN transport.stop s "
               "ON s.city_id = 1 AND s.mode = 'metro' AND " + _near("p", "s", 500) +
               " WHERE p.city_id = 1 AND p.category = 'school'")),
    dict(id="P06", category="proximity", difficulty="medium",
         question="Metro stops within 1 km of a university.",
         gold=("SELECT DISTINCT s.name, s.geom FROM transport.stop s JOIN poi.place p "
               "ON p.city_id = 1 AND p.category = 'university' AND " + _near("s", "p", 1000) +
               " WHERE s.city_id = 1 AND s.mode = 'metro'")),
    dict(id="P07", category="proximity", difficulty="medium",
         question="Restaurants within 250 m of a cinema.",
         gold=("SELECT DISTINCT p.name, p.geom FROM poi.place p JOIN poi.place c "
               "ON c.city_id = 1 AND c.category = 'cinema' AND " + _near("p", "c", 250) +
               " WHERE p.city_id = 1 AND p.category = 'restaurant'")),
    dict(id="P08", category="proximity", difficulty="medium",
         question="ATMs within 200 m of a railway station.",
         gold=("SELECT DISTINCT p.name, p.geom FROM poi.place p JOIN transport.stop s "
               "ON s.city_id = 1 AND s.mode = 'rail' AND " + _near("p", "s", 200) +
               " WHERE p.city_id = 1 AND p.category = 'atm'")),
    dict(id="P09", category="proximity", difficulty="medium",
         question="Bus stops within 300 m of a police station.",
         gold=("SELECT DISTINCT s.name, s.geom FROM transport.stop s JOIN poi.place p "
               "ON p.city_id = 1 AND p.category = 'police' AND " + _near("s", "p", 300) +
               " WHERE s.city_id = 1 AND s.mode = 'bus'")),

    # --------------------------------------------------- named area (medium, gazetteer)
    dict(id="A01", category="area", difficulty="medium",
         question="Cafes in Bandra.",
         gold=f"SELECT DISTINCT p.name, p.geom FROM poi.place p {_in_area('Bandra')} "
              "WHERE p.city_id = 1 AND p.category = 'cafe'",
         note="'In <area>' = within 2 km of a matching crime.area row (schema notes)."),
    dict(id="A02", category="area", difficulty="medium",
         question="Pharmacies in Andheri.",
         gold=f"SELECT DISTINCT p.name, p.geom FROM poi.place p {_in_area('Andheri')} "
              "WHERE p.city_id = 1 AND p.category = 'pharmacy'"),
    dict(id="A03", category="area", difficulty="medium",
         question="Banks in Powai.",
         gold=f"SELECT DISTINCT p.name, p.geom FROM poi.place p {_in_area('Powai')} "
              "WHERE p.city_id = 1 AND p.category = 'bank'"),
    dict(id="A04", category="area", difficulty="medium",
         question="Schools in Borivali.",
         gold=f"SELECT DISTINCT p.name, p.geom FROM poi.place p {_in_area('Borivali')} "
              "WHERE p.city_id = 1 AND p.category = 'school'"),
    dict(id="A05", category="area", difficulty="medium",
         question="Restaurants in Colaba.",
         gold=f"SELECT DISTINCT p.name, p.geom FROM poi.place p {_in_area('Colaba')} "
              "WHERE p.city_id = 1 AND p.category = 'restaurant'"),
    dict(id="A06", category="area", difficulty="medium",
         question="Hospitals in Dadar.",
         gold=f"SELECT DISTINCT p.name, p.geom FROM poi.place p {_in_area('Dadar')} "
              f"WHERE p.city_id = 1 AND p.category IN {HOSPITAL}"),
    dict(id="A07", category="area", difficulty="medium",
         question="Which metro stops are in Ghatkopar?",
         gold=("SELECT DISTINCT p.name, p.geom FROM transport.stop p "
               + _in_area("Ghatkopar") + " WHERE p.city_id = 1 AND p.mode = 'metro'")),

    # ----------------------------------------------------------------- ranking (medium)
    dict(id="R01", category="ranking", difficulty="medium", ordered=True,
         question="Which 5 areas are the safest?",
         gold="SELECT name, geom, safety_score FROM crime.area WHERE city_id = 1 "
              "ORDER BY safety_score DESC, name LIMIT 5"),
    dict(id="R02", category="ranking", difficulty="medium", ordered=True,
         question="Show the 3 least safe areas.",
         gold="SELECT name, geom, safety_score FROM crime.area WHERE city_id = 1 "
              "ORDER BY safety_score ASC, name LIMIT 3"),
    dict(id="R03", category="ranking", difficulty="medium", ordered=True,
         question="Top 8 areas by safety score.",
         gold="SELECT name, geom, safety_score FROM crime.area WHERE city_id = 1 "
              "ORDER BY safety_score DESC, name LIMIT 8"),

    # ---------------------------------------------------------------- listings (medium)
    dict(id="L01", category="listing", difficulty="medium",
         question="Listings with 3 or more bedrooms under 1 crore.",
         gold=("SELECT locality AS name, geom FROM realestate.listing WHERE city_id = 1 AND bhk >= 3 "
               "AND ((lower(price_unit) = 'cr' AND price < 1) OR lower(price_unit) = 'l')")),
    dict(id="L02", category="listing", difficulty="medium",
         question="Listings larger than 3000 sqft.",
         gold="SELECT locality AS name, geom FROM realestate.listing "
              "WHERE city_id = 1 AND area_sqft > 3000"),
    dict(id="L03", category="listing", difficulty="medium",
         question="Ready-to-move listings under 50 lakh.",
         gold=("SELECT locality AS name, geom FROM realestate.listing WHERE city_id = 1 "
               "AND status ILIKE '%ready%' AND lower(price_unit) = 'l' AND price < 50")),
    dict(id="L04", category="listing", difficulty="medium",
         question="Listings priced above 5 crore.",
         gold="SELECT locality AS name, geom FROM realestate.listing WHERE city_id = 1 "
              "AND lower(price_unit) = 'cr' AND price > 5"),

    # ------------------------------------------------------------ compositional (hard)
    dict(id="C01", category="compositional", difficulty="hard",
         question="Cafes within 500 m of a metro station that are also within 300 m of a bank.",
         gold=("SELECT DISTINCT p.name, p.geom FROM poi.place p "
               "WHERE p.city_id = 1 AND p.category = 'cafe' "
               "AND EXISTS (SELECT 1 FROM transport.stop s WHERE s.city_id = 1 AND s.mode = 'metro' "
               "AND ST_DWithin(p.geom::geography, s.geom::geography, 500)) "
               "AND EXISTS (SELECT 1 FROM poi.place b WHERE b.city_id = 1 AND b.category = 'bank' "
               "AND ST_DWithin(p.geom::geography, b.geom::geography, 300))")),
    dict(id="C02", category="compositional", difficulty="hard",
         question="Areas with a safety score above 70 that have a metro stop within 2 km.",
         gold=("SELECT a.name, a.geom, a.safety_score FROM crime.area a "
               "WHERE a.city_id = 1 AND a.safety_score > 70 "
               "AND EXISTS (SELECT 1 FROM transport.stop s WHERE s.city_id = 1 AND s.mode = 'metro' "
               "AND ST_DWithin(a.geom::geography, s.geom::geography, 2000))")),
    dict(id="C03", category="compositional", difficulty="hard",
         question="Areas with no hospital within 500 m.",
         gold=("SELECT a.name, a.geom FROM crime.area a WHERE a.city_id = 1 "
               f"AND NOT EXISTS (SELECT 1 FROM poi.place h WHERE h.city_id = 1 AND h.category IN {HOSPITAL} "
               "AND ST_DWithin(a.geom::geography, h.geom::geography, 500))")),
    dict(id="C04", category="compositional", difficulty="hard",
         question="Schools in Bandra that are within 500 m of a bus stop.",
         gold=(f"SELECT DISTINCT p.name, p.geom FROM poi.place p {_in_area('Bandra')} "
               "WHERE p.city_id = 1 AND p.category = 'school' "
               "AND EXISTS (SELECT 1 FROM transport.stop s WHERE s.city_id = 1 AND s.mode = 'bus' "
               "AND ST_DWithin(p.geom::geography, s.geom::geography, 500))")),
    dict(id="C05", category="compositional", difficulty="hard",
         question="Hospitals within 1 km of both a metro station and a railway station.",
         gold=("SELECT DISTINCT p.name, p.geom FROM poi.place p "
               f"WHERE p.city_id = 1 AND p.category IN {HOSPITAL} "
               "AND EXISTS (SELECT 1 FROM transport.stop s WHERE s.city_id = 1 AND s.mode = 'metro' "
               "AND ST_DWithin(p.geom::geography, s.geom::geography, 1000)) "
               "AND EXISTS (SELECT 1 FROM transport.stop r WHERE r.city_id = 1 AND r.mode = 'rail' "
               "AND ST_DWithin(p.geom::geography, r.geom::geography, 1000))")),
    dict(id="C06", category="compositional", difficulty="hard", ordered=True,
         question="The 3 safest areas that have a metro stop within 2 km.",
         gold=("SELECT a.name, a.geom, a.safety_score FROM crime.area a WHERE a.city_id = 1 "
               "AND EXISTS (SELECT 1 FROM transport.stop s WHERE s.city_id = 1 AND s.mode = 'metro' "
               "AND ST_DWithin(a.geom::geography, s.geom::geography, 2000)) "
               "ORDER BY a.safety_score DESC, a.name LIMIT 3")),
]

for _q in QUESTIONS:
    _q.setdefault("ordered", False)
    _q.setdefault("note", "")

assert len({q["id"] for q in QUESTIONS}) == len(QUESTIONS), "duplicate question id"
