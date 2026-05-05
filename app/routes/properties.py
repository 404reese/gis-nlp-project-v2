import csv
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class PropertyFilter(BaseModel):
    region: Optional[str] = None
    bhk: Optional[int] = None
    price_max: Optional[float] = None

class PropertyResponse(BaseModel):
    bhk: int
    type: str
    locality: str
    area: float
    price: float
    price_unit: str
    region: str
    status: str
    age: str

def load_properties() -> List[dict]:
    """Load properties from CSV file"""
    properties = []
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "Mumbai House Prices.csv")
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row and row.get('region'):  # Skip empty rows
                    try:
                        prop = {
                            'bhk': int(row.get('bhk', 0)) if row.get('bhk') else None,
                            'type': row.get('type', ''),
                            'locality': row.get('locality', ''),
                            'area': float(row.get('area', 0)) if row.get('area') else None,
                            'price': float(row.get('price', 0)) if row.get('price') else None,
                            'price_unit': row.get('price_unit', ''),
                            'region': row.get('region', ''),
                            'status': row.get('status', ''),
                            'age': row.get('age', ''),
                        }
                        properties.append(prop)
                    except (ValueError, TypeError):
                        continue
    except FileNotFoundError:
        print(f"CSV file not found at {csv_path}")
        return []
    
    return properties

@router.post("/properties")
async def get_properties_by_location(filter: PropertyFilter) -> dict:
    """
    Get properties filtered by region.
    Returns a list of properties matching the filter criteria.
    """
    properties = load_properties()
    
    if not properties:
        raise HTTPException(status_code=500, detail="Could not load properties data")
    
    # Filter properties
    filtered = properties
    
    if filter.region:
        # Case-insensitive region filter
        filtered = [p for p in filtered if filter.region.lower() in p['region'].lower()]
    
    if filter.bhk:
        filtered = [p for p in filtered if p['bhk'] == filter.bhk]
    
    if filter.price_max:
        filtered = [p for p in filtered if p['price'] and p['price'] <= filter.price_max]
    
    # Return top 20 properties
    return {
        "total": len(filtered),
        "properties": filtered[:20],
        "filter_applied": {
            "region": filter.region,
            "bhk": filter.bhk,
            "price_max": filter.price_max
        }
    }

@router.get("/properties/regions")
async def get_regions() -> dict:
    """
    Get all unique regions from the dataset.
    """
    properties = load_properties()
    regions = sorted(list(set(p['region'] for p in properties if p['region'])))
    
    return {
        "total": len(regions),
        "regions": regions
    }
