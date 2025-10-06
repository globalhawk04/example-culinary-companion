
# FILE: schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional

# --- Ingredient Schemas ---
# Describes the shape of a single ingredient item.
class ItemBase(BaseModel):
    itemName: str
    quantity: Optional[float] = None
    unit: Optional[str] = None

# This allows us to convert SQLAlchemy model instances into Pydantic schemas.
class Item(ItemBase):
    class Config:
        from_attributes = True


# --- Recipe Schemas ---
# Describes the fields needed to CREATE a new recipe.
# It doesn't have an 'id' because the database will create it.
class RecipeCreate(BaseModel):
    recipe_name: str = Field(..., min_length=1, max_length=100)
    provenance: Optional[str] = None
    items: List[ItemBase]
    chef_notes: Optional[List[str]] = None

# Describes the full recipe data, INCLUDING the 'id' field from the database.
# This will be the main schema we use for sending recipe data TO the frontend.
class Recipe(BaseModel):
    id: int
    recipe_name: str
    provenance: Optional[str] = None
    items: List[Item]
    chef_notes: Optional[List[str]] = None

    # This configuration allows Pydantic to read data directly from
    # SQLAlchemy model objects (e.g., recipe.id, recipe.items).
    class Config:
        from_attributes = True

# Describes the shape for a simple list view of recipes.
# We only need the name and ID to show in the cookbook list.
class RecipeListView(BaseModel):
    id: int
    recipe_name: str

    class Config:
        from_attributes = True