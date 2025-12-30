"""Seed script to populate sample menu items for local development."""
import os
import asyncio
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "resort_db")

SAMPLE_MENU_ITEMS = [
    # Starters
    {
        "name": "Moong Dal Chilla",
        "description": "Crispy pancake made from moong lentils with turmeric and ginger",
        "category": "starter",
        "portion": "1 piece",
        "price": 180.0,
        "imageUrl": "https://images.unsplash.com/photo-1585238341710-4b4e6cefc902?w=800&q=80",
        "dietaryTags": ["vegetarian", "vegan", "ayurvedic"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Steamed Veg Momos",
        "description": "Delicate dumplings filled with fresh vegetables and herbs",
        "category": "starter",
        "portion": "6 pieces",
        "price": 220.0,
        "imageUrl": "https://images.unsplash.com/photo-1609501676725-7186f017a4b8?w=800&q=80",
        "dietaryTags": ["vegetarian", "vegan"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Raw Papaya Salad",
        "description": "Fresh raw papaya tossed with lime, herbs, and light dressing",
        "category": "starter",
        "portion": "1 bowl",
        "price": 150.0,
        "imageUrl": "https://images.unsplash.com/photo-1609501676725-7186f017a4b8?w=800&q=80",
        "dietaryTags": ["vegan", "raw", "gluten-free"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    # Main Courses
    {
        "name": "Satvik Khichdi",
        "description": "One-pot rice and lentil dish with ghee and aromatic spices",
        "category": "main",
        "portion": "1 bowl",
        "price": 250.0,
        "imageUrl": "https://images.unsplash.com/photo-1596040960005-2b2e73529eae?w=800&q=80",
        "dietaryTags": ["vegetarian", "ayurvedic", "gluten-free"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Lauki Kofta Curry",
        "description": "Bottle gourd dumplings in a creamy tomato-based curry",
        "category": "main",
        "portion": "1 bowl",
        "price": 280.0,
        "imageUrl": "https://images.unsplash.com/photo-1604068549290-dea0e4a305ca?w=800&q=80",
        "dietaryTags": ["vegetarian", "vegan"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Paneer Tikka Masala",
        "description": "Grilled cottage cheese in a aromatic tomato and cream sauce",
        "category": "main",
        "portion": "1 bowl",
        "price": 320.0,
        "imageUrl": "https://images.unsplash.com/photo-1599043513069-4923f25a88b9?w=800&q=80",
        "dietaryTags": ["vegetarian"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    # Sides & Rotis
    {
        "name": "Tandoori Roti",
        "description": "Whole wheat bread baked in traditional tandoor",
        "category": "side",
        "portion": "1 piece",
        "price": 40.0,
        "imageUrl": "https://images.unsplash.com/photo-1595521012944-87a81eac89f0?w=800&q=80",
        "dietaryTags": ["vegetarian", "vegan"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Multigrain Paratha",
        "description": "Layered bread with mixed grains and mild spices",
        "category": "side",
        "portion": "1 piece",
        "price": 60.0,
        "imageUrl": "https://images.unsplash.com/photo-1565561142207-b1e3a3c0b6c8?w=800&q=80",
        "dietaryTags": ["vegetarian"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Steamed Basmati Rice",
        "description": "Fragrant basmati rice with cumin and bay leaves",
        "category": "side",
        "portion": "1 bowl",
        "price": 80.0,
        "imageUrl": "https://images.unsplash.com/photo-1606787620284-8d00c2f007a4?w=800&q=80",
        "dietaryTags": ["vegetarian", "vegan", "gluten-free"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    # Desserts
    {
        "name": "Jaggery Kheer",
        "description": "Rice pudding sweetened with jaggery and cardamom",
        "category": "dessert",
        "portion": "1 bowl",
        "price": 180.0,
        "imageUrl": "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=800&q=80",
        "dietaryTags": ["vegetarian"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Coconut Ladoo",
        "description": "Rolled coconut balls with dates and nuts",
        "category": "dessert",
        "portion": "3 pieces",
        "price": 120.0,
        "imageUrl": "https://images.unsplash.com/photo-1599599810694-b3fa506b263b?w=800&q=80",
        "dietaryTags": ["vegetarian", "vegan"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Fruit & Nut Bliss Balls",
        "description": "Dates, nuts, and dried fruit energy balls",
        "category": "dessert",
        "portion": "3 pieces",
        "price": 150.0,
        "imageUrl": "https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=800&q=80",
        "dietaryTags": ["vegan", "raw"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    # Beverages
    {
        "name": "Tulsi Ginger Tea",
        "description": "Aromatic herbal tea with tulsi, ginger, and honey",
        "category": "beverage",
        "portion": "1 cup",
        "price": 90.0,
        "imageUrl": "https://images.unsplash.com/photo-1597318972265-b7ddf0b0bbcd?w=800&q=80",
        "dietaryTags": ["vegan", "ayurvedic"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Almond Milk",
        "description": "Creamy almond milk with cardamom and saffron",
        "category": "beverage",
        "portion": "1 glass",
        "price": 120.0,
        "imageUrl": "https://images.unsplash.com/photo-1585529924183-d52c6a6e29d6?w=800&q=80",
        "dietaryTags": ["vegan", "gluten-free"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Herbal Coffee",
        "description": "Chicory-based herbal coffee with warming spices",
        "category": "beverage",
        "portion": "1 cup",
        "price": 100.0,
        "imageUrl": "https://images.unsplash.com/photo-1559056199-641a0ac8b8d0?w=800&q=80",
        "dietaryTags": ["vegan", "ayurvedic"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    },
    {
        "name": "Mineral Water",
        "description": "Pure mineral water",
        "category": "beverage",
        "portion": "500ml",
        "price": 60.0,
        "imageUrl": "https://images.unsplash.com/photo-1567921294565-20aeb2d4d72e?w=800&q=80",
        "dietaryTags": ["vegan", "gluten-free"],
        "isVisible": True,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
]

print("mongo_seed_menu.py is neutralized. See scripts_disabled/mongo_seed_menu.py for original script.")
