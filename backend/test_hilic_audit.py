"""Audit HILIC columns by manufacturer."""
from app.core.chem.columns_db import list_columns, get_brands, get_chemistries

# Get all HILIC columns
cols, total = list_columns(chemistry="HILIC", limit=500)
print(f"Total HILIC columns: {total}")
print()

# Group by brand
by_brand: dict[str, list[str]] = {}
for c in cols:
    by_brand.setdefault(c.brand, [])
    # Unique names only
    if c.name not in by_brand[c.brand]:
        by_brand[c.brand].append(c.name)

print("HILIC columns by manufacturer:")
for brand in sorted(by_brand.keys()):
    names = sorted(by_brand[brand])
    print(f"\n  {brand} ({len(names)} unique names):")
    for n in names:
        print(f"    - {n}")

# Also check for ZIC specifically
print("\n\nZIC columns (any chemistry):")
cols_zic, total_zic = list_columns(search="ZIC", limit=500)
by_brand_zic: dict[str, list[str]] = {}
for c in cols_zic:
    by_brand_zic.setdefault(c.brand, [])
    if c.name not in by_brand_zic[c.brand]:
        by_brand_zic[c.brand].append(c.name)
for brand in sorted(by_brand_zic.keys()):
    print(f"  {brand}: {sorted(by_brand_zic[brand])}")
