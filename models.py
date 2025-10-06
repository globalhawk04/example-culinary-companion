# FILE: models.py (Update the Transcript class)

from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    full_text = Column(Text, nullable=False)
    status = Column(String, default="pending", nullable=False)

    # *** THIS IS THE FIX ***
    # The `ondelete="SET NULL"` parameter tells the database what to do
    # when the recipe this transcript points to is deleted. It will set
    # this column to NULL instead of causing an error.
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    
    recipe = relationship("Recipe", back_populates="transcript")

class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    recipe_name = Column(String, index=True, nullable=False)
    provenance = Column(String, nullable=True)
    items = Column(JSON, nullable=False)
    chef_notes = Column(JSON, nullable=True)
    transcript = relationship("Transcript", back_populates="recipe", uselist=False)