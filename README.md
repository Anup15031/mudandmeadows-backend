# FastAPI Resort Backend

This is a FastAPI backend for a resort booking system integrated with MongoDB.

## Features

- Accommodations management
- Packages management
- Experiences management
- Wellness services management
- Booking system
- Home page with featured items

## Setup

1. Create a virtual environment and install dependencies (Windows PowerShell shown):

```powershell
# Create venv
python -m venv .venv

# Upgrade pip and install requirements using the venv Python
& .\.venv\Scripts\python -m pip install --upgrade pip
& .\.venv\Scripts\python -m pip install -r requirements.txt

# Start server
& .\.venv\Scripts\python -m uvicorn main:app --reload --port 8000
```

2. Create a `.env` file (example):

```
MONGODB_URL=mongodb+srv://adivasi:8QawNxoebl0YeRil@adivasi-dev.0kt3ba1.mongodb.net/
DATABASE_NAME=resort_db
ADMIN_API_KEY=your-admin-key-optional
```

3. API docs (once server is running):
```text
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
```

## API Endpoints

Note about dummy/sample data
- Seed scripts in the repository (files named `mongo_seed*.py`) are intended for local development only. They have been updated to be non-destructive: they will only insert sample documents when the target collection is empty. The backend always reads from MongoDB; if your database contains real data, that data will be used and seed scripts will not overwrite it.


### Home
- `GET /home/` - Get home page data
- `GET /home/stats` - Get resort statistics

### Accommodations
- `GET /accommodations/` - Get all accommodations
- `GET /accommodations/{id}` - Get specific accommodation
- `POST /accommodations/` - Create accommodation
- `PUT /accommodations/{id}` - Update accommodation
- `DELETE /accommodations/{id}` - Delete accommodation

### Packages
- `GET /packages/` - Get all packages
- `GET /packages/{id}` - Get specific package
- `POST /packages/` - Create package
- `PUT /packages/{id}` - Update package
- `DELETE /packages/{id}` - Delete package

### Experiences
- `GET /experiences/` - Get all experiences
- `GET /experiences/{id}` - Get specific experience
- `POST /experiences/` - Create experience
- `PUT /experiences/{id}` - Update experience
- `DELETE /experiences/{id}` - Delete experience

### Wellness
- `GET /wellness/` - Get all wellness services
- `GET /wellness/{id}` - Get specific wellness service
- `POST /wellness/` - Create wellness service
- `PUT /wellness/{id}` - Update wellness service
- `DELETE /wellness/{id}` - Delete wellness service

### Bookings
- `GET /bookings/` - Get all bookings
- `GET /bookings/{id}` - Get specific booking
- `POST /bookings/` - Create booking
- `PUT /bookings/{id}` - Update booking
- `DELETE /bookings/{id}` - Delete booking
- `GET /bookings/guest/{email}` - Get bookings by guest email

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
