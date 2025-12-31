from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Accommodation(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    price_per_night: float
    capacity: int
    # Number of extra bedding items available for this room (optional)
    extra_bedding: Optional[int] = None
    # Optional per-night price for an extra bedding
    extra_bedding_price: Optional[float] = None
    # Admin control: allow extra beds for this room
    extraBedAllowed: Optional[bool] = False
    # Optional list of allowed extra bed type ids (integers)
    allowedExtraBedIds: list[int] = []
    amenities: list[str] = []
    images: list[str] = []
    rating: float
    created_at: Optional[datetime] = None

class Package(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    price: float
    duration_days: int
    includes: list[str] = []
    images: list[str] = []
    rating: float
    created_at: Optional[datetime] = None

class Experience(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    price: float
    duration_hours: float
    activities: list[str] = []
    images: list[str] = []
    rating: float
    created_at: Optional[datetime] = None

class Wellness(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    price: float
    duration_minutes: int
    days: Optional[int] = None
    benefits: list[str] = []
    images: list[str] = []
    rating: float
    inclusions: Optional[list[str]] = None
    diet: Optional[dict] = None  # {type: str, description: str}
    case_study: Optional[str] = None
    comprehensive_sessions: Optional[int] = None
    attention_sessions: Optional[int] = None
    wellness_consultation: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

class Booking(BaseModel):
    id: Optional[str] = None
    guest_name: str
    guest_email: str
    guest_phone: str
    accommodation_id: str
    guests: Optional[int] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    allow_extra_beds: Optional[bool] = False
    extra_beds_qty: Optional[int] = 0
    package_id: Optional[str] = None
    experience_ids: list[str] = []
    wellness_ids: list[str] = []
    check_in: datetime
    check_out: datetime
    total_price: float
    status: str = "pending"  # pending, confirmed, cancelled
    created_at: Optional[datetime] = None

class HomePage(BaseModel):
    title: str
    description: str
    featured_accommodations: list[str] = []
    featured_packages: list[str] = []
    featured_experiences: list[str] = []


class GalleryImage(BaseModel):
    id: Optional[str] = None
    imageUrl: str
    caption: Optional[str] = None
    category: Optional[str] = None  # rooms | spa | nature | dining | activities
    isVisible: bool = True
    createdAt: Optional[datetime] = None


class ExtraBedRequest(BaseModel):
    id: Optional[str] = None
    accommodation_id: str
    quantity: int = 1
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    requested_at: Optional[datetime] = None
    status: str = "pending"  # pending, fulfilled, cancelled


class ExtraBed(BaseModel):
    id: Optional[str] = None
    accommodation_id: Optional[str] = None
    quantity: int = 0
    price: Optional[float] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class Program(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    duration_days: Optional[int] = None
    tags: list[str] = []
    location: Optional[str] = None
    price: Optional[float] = 0.0
    is_included: bool = False
    capacity: Optional[int] = None  # total slots available (optional)
    created_at: Optional[datetime] = None


class Facility(BaseModel):
    id: Optional[str] = None
    program_id: str
    type: str
    title: str
    description: Optional[str] = None
    price: Optional[float] = 0.0
    capacity: Optional[int] = None
    is_optional: bool = True
    created_at: Optional[datetime] = None
