/**
 * One-shot mongosh script to upsert example room docs and normalize existing `rooms` collection.
 * This variant sets a default `child_age_limit` of 12 for rooms missing that field.
 * Usage:
 *  - Paste into MongoDB Compass Playground and run, or
 *  - Run with mongosh: `mongosh --file seed_rooms_mongosh_defaults.js`
 *
 * Edit `DB_NAME` at the top to match your database.
 */

const DB_NAME = "resort_db"; // <-- change to your DB name
const dbR = db.getSiblingDB(DB_NAME);
const rooms = dbR.rooms;

print(`Seeding/normalizing rooms collection in database: ${DB_NAME} (defaults variant)`);

// 1) Upsert Jacuzzi Cottage
const jacuzzi = {
  id: "jacuzzi-cottage",
  slug: "jacuzzi-cottage",
  name: "Jacuzzi Cottage",
  description: "Private terrace with an outdoor jacuzzi, mountain views and handcrafted interiors. Perfect for romantic getaways.",
  images: [
    "https://images.unsplash.com/photo-1519710164239-da123dc03ef4?q=80&w=1600&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1505691723518-36a7b30f9b1b?q=80&w=1600&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?q=80&w=1600&auto=format&fit=crop"
  ],
  pricePerNight: 12000,
  price_per_night: 12000,
  amenities: ["Outdoor Jacuzzi","Mountain View","Private Terrace","Mini Bar","Rain Shower","Complimentary Breakfast"],
  beds: "1 Queen",
  bedConfig: [{ type: "Queen", count: 1, size: "160x200 cm" }],
  sleeps: 2,
  sqm: "55",
  capacity_adults: 2,
  capacity_children: 1,
  child_age_limit: 12,
  policies: { cancellation: "Free cancellation up to 14 days before arrival", checkIn: "15:00", checkOut: "12:00" },
  restaurant: {
    name: "Terrace Bistro",
    description: "Light meals and beverages served on the terrace.",
    openingHours: "08:00 - 23:00",
    menu: [
      { name: "Grilled Fish", price: 650, description: "Fresh catch with herb butter." },
      { name: "Seasonal Salad", price: 350, description: "Local greens with house vinaigrette." }
    ]
  },
  updated_at: new Date()
};

print('Upserting Jacuzzi Cottage...');
rooms.updateOne(
  { $or: [{ slug: jacuzzi.slug }, { id: jacuzzi.id }, { name: jacuzzi.name }] },
  { $set: jacuzzi, $setOnInsert: { created_at: new Date() } },
  { upsert: true }
);
print('Jacuzzi upsert complete.');

// 2) Upsert cap-test-room example (if you want a quick test slug present)
const capTest = {
  id: "cap-test-room",
  slug: "cap-test-room",
  name: "Cap Test Room",
  description: "Room used for capacity testing.",
  images: [
    "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?q=80&w=1600&auto=format&fit=crop"
  ],
  pricePerNight: 5000,
  price_per_night: 5000,
  amenities: ["Free WiFi","King Bed"],
  beds: "1 King",
  bedConfig: [{ type: "King", count: 1, size: "180x200 cm" }],
  sleeps: 2,
  sqm: "32",
  capacity_adults: 2,
  capacity_children: 1,
  child_age_limit: 12,
  policies: { cancellation: "Free cancellation up to 7 days before arrival", checkIn: "15:00", checkOut: "12:00" },
  updated_at: new Date()
};

print('Upserting cap-test-room...');
rooms.updateOne(
  { $or: [{ slug: capTest.slug }, { id: capTest.id }, { name: capTest.name }] },
  { $set: capTest, $setOnInsert: { created_at: new Date() } },
  { upsert: true }
);
print('cap-test-room upsert complete.');

// 3) Normalize / enrich all existing rooms and set default child_age_limit = 12 if missing
print('Normalizing existing room documents (applying defaults)...');
const defaultImages = [
  'https://images.unsplash.com/photo-1505691723518-36a7b30f9b1b?q=80&w=1200&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?q=80&w=1200&auto=format&fit=crop'
];

let total = 0;
let updated = 0;
rooms.find({}).forEach(doc => {
  total++;
  const upd = {};
  // price
  if (doc.price_per_night === undefined || doc.price_per_night === null) {
    if (doc.pricePerNight !== undefined) upd.price_per_night = doc.pricePerNight;
    else if (doc.price !== undefined) upd.price_per_night = doc.price;
    else upd.price_per_night = 0;
  }
  // images
  if (!Array.isArray(doc.images) || doc.images.length === 0) {
    if (Array.isArray(doc.media) && doc.media.length) upd.images = doc.media;
    else if (doc.image) upd.images = [doc.image];
    else upd.images = defaultImages;
  }
  // sleeps / capacity fields
  if (doc.sleeps === undefined || doc.sleeps === null) {
    upd.sleeps = doc.capacity || doc.maxGuests || doc.capacity_max || 1;
  }
  // capacity_adults & capacity_children
  if (doc.capacity_adults === undefined) {
    upd.capacity_adults = doc.capacity || doc.maxGuests || 1;
  }
  if (doc.capacity_children === undefined) {
    upd.capacity_children = doc.capacity_children || doc.child_capacity || 0;
  }
  // child_age_limit - set to 12 if missing
  if (doc.child_age_limit === undefined && doc.child_age_max === undefined && doc.child_age === undefined) {
    upd.child_age_limit = 12;
  }
  // amenities
  if (!Array.isArray(doc.amenities)) upd.amenities = doc.features || doc.tags || [];
  // beds / bedConfig
  if (!doc.beds && Array.isArray(doc.bedConfig) && doc.bedConfig.length) {
    upd.beds = doc.bedConfig.map(b => `${b.count || 1} ${b.type || ''}`.trim()).join(', ');
  }
  // policies default
  if (!doc.policies) upd.policies = { cancellation: 'Free cancellation up to 7 days before check-in', checkIn: '15:00', checkOut: '12:00' };

  if (Object.keys(upd).length) {
    upd.updated_at = new Date();
    rooms.updateOne({ _id: doc._id }, { $set: upd });
    updated++;
  }
});

print(`Scanned ${total} rooms; updated ${updated} documents.`);

// 4) Create / ensure index on slug
try {
  rooms.createIndex({ slug: 1 });
  print('Ensured index on `slug`.');
} catch (e) {
  print('Index creation skipped or failed:', e);
}

print('Seed/normalize (defaults) complete. Verify results in Compass by inspecting the `rooms` collection.');
