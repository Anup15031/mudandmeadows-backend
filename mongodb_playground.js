// MongoDB Playground Script for Resort Booking System
// Copy and paste this into MongoDB Atlas Playground or use with mongosh

// ==================== ACCOMMODATIONS ====================
db.accommodations.deleteMany({});

db.accommodations.insertMany([
  {
    name: "Luxury Oceanview Suite",
    description: "Premium oceanfront suite with private balcony overlooking the beach",
    price_per_night: 450,
    capacity: 2,
    amenities: [
      "Ocean View",
      "Private Balcony",
      "King Bed",
      "Marble Bathroom",
      "Mini Bar",
      "Free WiFi",
      "Air Conditioning",
      "Smart TV"
    ],
    images: [
      "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500",
      "https://images.unsplash.com/photo-1578926078328-123c61ab21d0?w=500"
    ],
    rating: 4.8,
    created_at: new Date()
  },
  {
    name: "Deluxe Garden Room",
    description: "Spacious garden view room with tropical garden access",
    price_per_night: 280,
    capacity: 2,
    amenities: [
      "Garden View",
      "Terrace",
      "Queen Bed",
      "Ensuite Bathroom",
      "Free WiFi",
      "Air Conditioning",
      "Work Desk",
      "Bathrobe & Slippers"
    ],
    images: [
      "https://images.unsplash.com/photo-1506439773649-6e0eb8cfb237?w=500",
      "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500"
    ],
    rating: 4.6,
    created_at: new Date()
  },
  {
    name: "Family Villa",
    description: "Spacious villa perfect for families with kids, separate living areas",
    price_per_night: 600,
    capacity: 4,
    amenities: [
      "Private Pool",
      "2 Bedrooms",
      "Living Area",
      "Full Kitchen",
      "Garden",
      "BBQ Area",
      "WiFi",
      "Kids Welcome"
    ],
    images: [
      "https://images.unsplash.com/photo-1618883479302-1461ae109845?w=500",
      "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
    ],
    rating: 4.9,
    created_at: new Date()
  },
  {
    name: "Romantic Beachfront Bungalow",
    description: "Intimate bungalow steps away from the beach, perfect for honeymooners",
    price_per_night: 350,
    capacity: 2,
    amenities: [
      "Beach Access",
      "Private Deck",
      "Outdoor Shower",
      "King Bed",
      "Romantic Ambiance",
      "Mini Bar",
      "WiFi",
      "Sunset View"
    ],
    images: [
      "https://images.unsplash.com/photo-1520381753852-7bea9d5beb89?w=500",
      "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500"
    ],
    rating: 4.7,
    created_at: new Date()
  },
  {
    name: "Standard Room",
    description: "Comfortable room with essential amenities, great value for budget travelers",
    price_per_night: 150,
    capacity: 1,
    amenities: [
      "Single Bed",
      "Private Bathroom",
      "Air Conditioning",
      "Free WiFi",
      "TV",
      "Work Desk"
    ],
    images: [
      "https://images.unsplash.com/photo-1570129477492-45c003cedd70?w=500",
      "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500"
    ],
    rating: 4.2,
    created_at: new Date()
  }
]);

// ==================== PACKAGES ====================
db.packages.deleteMany({});

db.packages.insertMany([
  {
    name: "Tropical Paradise 5-Day Package",
    description: "Experience the ultimate beach getaway with beach activities and water sports",
    price: 1499,
    duration_days: 5,
    includes: [
      "Accommodation (4 nights)",
      "Daily Breakfast",
      "Beach Access",
      "Snorkeling Tour",
      "Island Hopping",
      "Welcome Dinner",
      "Sunset Cruise"
    ],
    images: [
      "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500",
      "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=500"
    ],
    rating: 4.8,
    created_at: new Date()
  },
  {
    name: "Romantic Getaway 3-Day Package",
    description: "Perfect for couples - romance, relaxation, and luxury dining experiences",
    price: 899,
    duration_days: 3,
    includes: [
      "Accommodation (2 nights)",
      "Romantic Dinner",
      "Couples Spa Treatment",
      "Champagne & Fruits",
      "Beach Setup",
      "Breakfast in Bed",
      "Airport Transfer"
    ],
    images: [
      "https://images.unsplash.com/photo-1519046904884-53103b34b206?w=500",
      "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=500"
    ],
    rating: 4.9,
    created_at: new Date()
  },
  {
    name: "Adventure Explorer 7-Day Package",
    description: "Action-packed week with hiking, water sports, and cultural experiences",
    price: 1999,
    duration_days: 7,
    includes: [
      "Accommodation (6 nights)",
      "Daily Breakfast & Lunch",
      "Mountain Hiking Tour",
      "Scuba Diving",
      "Kayaking",
      "Cultural Village Visit",
      "Local Cooking Class",
      "All Equipment"
    ],
    images: [
      "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=500",
      "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=500"
    ],
    rating: 4.7,
    created_at: new Date()
  },
  {
    name: "Wellness Retreat 4-Day Package",
    description: "Rejuvenating wellness program with yoga, spa, and healthy cuisine",
    price: 699,
    duration_days: 4,
    includes: [
      "Accommodation (3 nights)",
      "Daily Yoga Sessions",
      "Spa Treatments",
      "Healthy Meals",
      "Meditation Classes",
      "Natural Healing Workshop",
      "Sauna & Steam Room"
    ],
    images: [
      "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=500",
      "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=500"
    ],
    rating: 4.6,
    created_at: new Date()
  }
]);

// ==================== EXPERIENCES ====================
db.experiences.deleteMany({});

db.experiences.insertMany([
  {
    name: "Snorkeling Adventure",
    description: "Explore vibrant coral reefs and tropical fish in crystal clear waters",
    price: 89,
    duration_hours: 3,
    activities: [
      "Boat Ride",
      "Snorkeling Equipment",
      "Coral Reef Exploration",
      "Photography",
      "Refreshments"
    ],
    images: [
      "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=500",
      "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=500"
    ],
    rating: 4.9,
    created_at: new Date()
  },
  {
    name: "Sunset Catamaran Cruise",
    description: "Romantic sunset cruise with cocktails and light snacks",
    price: 75,
    duration_hours: 2.5,
    activities: [
      "Catamaran Sailing",
      "Cocktails",
      "Appetizers",
      "Sunset Viewing",
      "Photography Opportunity"
    ],
    images: [
      "https://images.unsplash.com/photo-1511632765486-a01980e01a18?w=500",
      "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500"
    ],
    rating: 4.8,
    created_at: new Date()
  },
  {
    name: "Mountain Hiking Tour",
    description: "Guided hiking adventure with stunning panoramic views and nature experience",
    price: 65,
    duration_hours: 4,
    activities: [
      "Guided Hiking",
      "Nature Photography",
      "Picnic Lunch",
      "Panoramic Views",
      "Local Guide"
    ],
    images: [
      "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=500",
      "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=500"
    ],
    rating: 4.7,
    created_at: new Date()
  },
  {
    name: "Scuba Diving Certification",
    description: "Get certified and dive to 40m depth with professional instructors",
    price: 199,
    duration_hours: 8,
    activities: [
      "PADI Training",
      "Equipment Rental",
      "Two Dive Dives",
      "Certification",
      "Marine Life Spotting"
    ],
    images: [
      "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=500",
      "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=500"
    ],
    rating: 4.9,
    created_at: new Date()
  },
  {
    name: "Island Hopping Adventure",
    description: "Visit multiple islands in one day with swimming and beach time",
    price: 95,
    duration_hours: 6,
    activities: [
      "Speedboat Ride",
      "3 Island Visits",
      "Swimming",
      "Snorkeling",
      "Lunch & Drinks"
    ],
    images: [
      "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=500",
      "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=500"
    ],
    rating: 4.8,
    created_at: new Date()
  },
  {
    name: "Local Cooking Class",
    description: "Learn to cook traditional dishes from a local chef",
    price: 55,
    duration_hours: 3,
    activities: [
      "Market Tour",
      "Hands-on Cooking",
      "Recipe Cards",
      "Meal Tasting",
      "Chef Tips"
    ],
    images: [
      "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500",
      "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500"
    ],
    rating: 4.6,
    created_at: new Date()
  }
]);

// ==================== WELLNESS ====================
db.wellness.deleteMany({});

db.wellness.insertMany([
  {
    name: "Thai Massage",
    description: "Traditional Thai massage to relax muscles and improve flexibility",
    price: 60,
    duration_minutes: 60,
    benefits: [
      "Muscle Relaxation",
      "Improved Circulation",
      "Stress Relief",
      "Flexibility",
      "Energy Boost"
    ],
    images: [
      "https://images.unsplash.com/photo-1600334129128-685c5582fd35?w=500",
      "https://images.unsplash.com/photo-1544161515-8f98ce338aa0?w=500"
    ],
    rating: 4.9,
    created_at: new Date()
  },
  {
    name: "Hot Stone Massage",
    description: "Therapeutic massage with heated stones for deep relaxation",
    price: 75,
    duration_minutes: 60,
    benefits: [
      "Deep Relaxation",
      "Pain Relief",
      "Improved Sleep",
      "Stress Reduction",
      "Muscle Recovery"
    ],
    images: [
      "https://images.unsplash.com/photo-1600334129128-685c5582fd35?w=500",
      "https://images.unsplash.com/photo-1591013753814-1215ffd73b6b?w=500"
    ],
    rating: 4.8,
    created_at: new Date()
  },
  {
    name: "Yoga Class",
    description: "Guided yoga session for flexibility, strength, and mental peace",
    price: 25,
    duration_minutes: 60,
    benefits: [
      "Flexibility",
      "Strength",
      "Mental Peace",
      "Balance",
      "Breathing Techniques"
    ],
    images: [
      "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=500",
      "https://images.unsplash.com/photo-1588286840104-8957b019727f?w=500"
    ],
    rating: 4.7,
    created_at: new Date()
  },
  {
    name: "Facial Treatment",
    description: "Rejuvenating facial with organic products for glowing skin",
    price: 80,
    duration_minutes: 60,
    benefits: [
      "Skin Rejuvenation",
      "Deep Cleansing",
      "Hydration",
      "Anti-aging",
      "Radiant Glow"
    ],
    images: [
      "https://images.unsplash.com/photo-1596178065887-8f180341d67e?w=500",
      "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=500"
    ],
    rating: 4.8,
    created_at: new Date()
  },
  {
    name: "Aromatherapy Treatment",
    description: "Healing treatment using essential oils for physical and mental wellness",
    price: 50,
    duration_minutes: 45,
    benefits: [
      "Stress Relief",
      "Improved Mood",
      "Better Sleep",
      "Immune Boost",
      "Emotional Balance"
    ],
    images: [
      "https://images.unsplash.com/photo-1577720643272-265f4d3c8d58?w=500",
      "https://images.unsplash.com/photo-1600334129128-685c5582fd35?w=500"
    ],
    rating: 4.6,
    created_at: new Date()
  },
  {
    name: "Meditation Session",
    description: "Guided meditation for mindfulness and inner peace",
    price: 30,
    duration_minutes: 45,
    benefits: [
      "Inner Peace",
      "Stress Reduction",
      "Better Focus",
      "Emotional Healing",
      "Mindfulness"
    ],
    images: [
      "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=500",
      "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=500"
    ],
    rating: 4.5,
    created_at: new Date()
  }
]);

// ==================== BOOKINGS (Sample Data) ====================
db.bookings.deleteMany({});

db.bookings.insertMany([
  {
    guest_name: "John Smith",
    guest_email: "john.smith@email.com",
    guest_phone: "+1-555-123-4567",
    accommodation_id: ObjectId("000000000000000000000001"),
    package_id: ObjectId("000000000000000000000001"),
    experience_ids: [
      ObjectId("000000000000000000000001"),
      ObjectId("000000000000000000000002")
    ],
    wellness_ids: [
      ObjectId("000000000000000000000001")
    ],
    check_in: new Date("2025-12-20"),
    check_out: new Date("2025-12-25"),
    total_price: 2125,
    status: "confirmed",
    created_at: new Date()
  },
  {
    guest_name: "Sarah Johnson",
    guest_email: "sarah.j@email.com",
    guest_phone: "+1-555-987-6543",
    accommodation_id: ObjectId("000000000000000000000003"),
    package_id: ObjectId("000000000000000000000002"),
    experience_ids: [
      ObjectId("000000000000000000000004")
    ],
    wellness_ids: [
      ObjectId("000000000000000000000002"),
      ObjectId("000000000000000000000003")
    ],
    check_in: new Date("2025-12-22"),
    check_out: new Date("2025-12-25"),
    total_price: 1400,
    status: "confirmed",
    created_at: new Date()
  },
  {
    guest_name: "Michael Chen",
    guest_email: "mchen@email.com",
    guest_phone: "+1-555-456-7890",
    accommodation_id: ObjectId("000000000000000000000002"),
    package_id: null,
    experience_ids: [
      ObjectId("000000000000000000000003"),
      ObjectId("000000000000000000000005")
    ],
    wellness_ids: [],
    check_in: new Date("2025-12-26"),
    check_out: new Date("2026-01-02"),
    total_price: 1960,
    status: "pending",
    created_at: new Date()
  }
]);

// ==================== VERIFICATION ====================
console.log("✅ Collections created successfully!");
console.log("Accommodations:", db.accommodations.countDocuments({}));
console.log("Packages:", db.packages.countDocuments({}));
console.log("Experiences:", db.experiences.countDocuments({}));
console.log("Wellness Services:", db.wellness.countDocuments({}));
console.log("Bookings:", db.bookings.countDocuments({}));
