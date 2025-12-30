import pytest
from routes.api_compat import allocate_rooms
from bson import ObjectId


def make_room(_id, cap, price=100, slug=None, extra_beds=None):
    return {"_id": ObjectId(_id), "capacity": cap, "price_per_night": price, "slug": slug, "extra_beds": extra_beds}


def test_single_room_exact_fit():
    rooms = [make_room("000000000000000000000001", 4, 100), make_room("000000000000000000000002", 2, 50)]
    allocated = allocate_rooms(rooms, 3)
    assert len(allocated) == 1
    assert str(allocated[0]) == "000000000000000000000001"


def test_multiple_rooms_greedy():
    rooms = [make_room("000000000000000000000001", 2, 50), make_room("000000000000000000000002", 2, 50), make_room("000000000000000000000003", 4, 200)]
    allocated = allocate_rooms(rooms, 6)
    assert len(allocated) >= 2


def test_extra_beds_option():
    rooms = [make_room("000000000000000000000001", 2, 50, extra_beds=1), make_room("000000000000000000000002", 2, 50, extra_beds=0)]
    # without extra beds, need 6 guests -> 3 rooms
    alloc1 = allocate_rooms(rooms * 3, 6, allow_extra_beds=False)
    assert len(alloc1) >= 3
    # with extra beds allowed, each room can take one more -> capacity per room 3, so 2 rooms suffice
    alloc2 = allocate_rooms(rooms * 3, 6, allow_extra_beds=True)
    assert len(alloc2) <= 2


def test_preferred_room_types():
    rooms = [make_room("000000000000000000000001", 2, 50, slug="small"), make_room("000000000000000000000002", 4, 100, slug="large")]
    alloc = allocate_rooms(rooms, 4, preferred_room_types=["large"])
    assert len(alloc) == 1
    assert str(alloc[0]) == "000000000000000000000002"
