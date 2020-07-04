import math
from datetime import datetime, timedelta
from threading import Lock


class VehicleType():
    TWO_WHEELER = 'TWO_WHEELER'
    CAR = 'CAR'
    ALLOWED_TYPES = (CAR, TWO_WHEELER)


class ParkingLot():
    def __init__(self, capacity_map, rate_card):
        self.id = id(self)
        self.capacity_map = capacity_map
        self.rate_card = rate_card
        self.occupancy_map = {}


class Vehicle():
    def __init__(self, vehicle_number, type_of_vehicle):
        self.vehicle_number = vehicle_number  # primary key
        self.type_of_vehicle = type_of_vehicle


class Parking():
    def __init__(self, parking_lot_id, vehicle_number, start_time=None):
        self.id = id(self)
        self.parking_lot_id = parking_lot_id
        self.vehicle_number = vehicle_number
        self.start_time = start_time if start_time else datetime.now()
        self.end_time = None
        self.charge = 0.0


class SingletonMetaClass(type):
    def __init__(cls, name, bases, dict):
        super(SingletonMetaClass, cls) \
            .__init__(name, bases, dict)
        original_new = cls.__new__

        def my_new(cls, *args, **kwds):
            if cls.instance == None:
                cls.instance = \
                    original_new(cls, *args, **kwds)
            return cls.instance

        cls.instance = None
        cls.__new__ = staticmethod(my_new)


class ParkingLotManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.parking_lot_id_to_parking_lot = {}
        self.vehicle_manager = VehicleManager()
        self.parking_manager = ParkingManager()
        self.parking_lot_id_to_vehicle_parking_map = {}
        self.vehicle_id_to_pl_id = {}
        self.db_lock = Lock()

    def register_parking_lot(self, capacity_map, rate_card):
        # todo: validate capacity_map and rate_card
        pl = ParkingLot(capacity_map=capacity_map, rate_card=rate_card)
        pl.lock = Lock()
        self.parking_lot_id_to_parking_lot[pl.id] = pl
        return pl.id

    def park_vehicle(self, parking_lot_id, vehicle_number):
        if parking_lot_id not in self.parking_lot_id_to_parking_lot:
            raise Exception("No parking lot with given id")
        pl = self.parking_lot_id_to_parking_lot[parking_lot_id]
        vehicle_type = self.vehicle_manager.get_vehicle_type(vehicle_number)
        with pl.lock:
            total_capacity = pl.capacity_map[vehicle_type]
            occupied = len(pl.occupancy_map.get(vehicle_type, []))
            if vehicle_number in self.vehicle_id_to_pl_id:
                raise Exception("vehicle already parked somewhere")
            if occupied < total_capacity:
                if vehicle_type not in pl.occupancy_map:
                    pl.occupancy_map[vehicle_type] = []
                pid = self.parking_manager.occupy(pl.id, vehicle_number)
                pl.occupancy_map[vehicle_type].append(pid)
                self.vehicle_manager.register_parking(vehicle_number, pid)
                if pl.id not in self.parking_lot_id_to_vehicle_parking_map:
                    self.parking_lot_id_to_vehicle_parking_map[pl.id] = {}
                self.parking_lot_id_to_vehicle_parking_map[pl.id][vehicle_number] = pid
                self.vehicle_id_to_pl_id[vehicle_number] = pl.id
                return
            raise Exception("No slot available for given vehicle type.")

    def exit_vehicle(self, parking_lot_id, vehicle_number):
        if parking_lot_id not in self.parking_lot_id_to_parking_lot:
            raise Exception("No parking lot with given id")
        pl = self.parking_lot_id_to_parking_lot[parking_lot_id]
        pid = self.parking_lot_id_to_vehicle_parking_map.get(pl.id, {}).get(vehicle_number)
        if not pid:
            raise Exception("vehicle not parked in parking lot.")
        vehicle_type = self.vehicle_manager.get_vehicle_type(vehicle_number)
        charge = self.parking_manager.free(pid, pl.rate_card.get(vehicle_type))
        self.parking_lot_id_to_vehicle_parking_map[pl.id].pop(vehicle_number)
        self.vehicle_id_to_pl_id.pop(vehicle_number)
        return charge


class ParkingManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.parking_id_to_parking = {}

    def get_by_id(self, pid):
        if pid not in self.parking_id_to_parking:
            raise Exception("not a valid pid")
        return self.parking_id_to_parking[pid].__dict__

    def occupy(self, parking_lot_id, vehicle_number):
        p = Parking(parking_lot_id=parking_lot_id, vehicle_number=vehicle_number)
        self.parking_id_to_parking[p.id] = p
        return p.id

    def get_occupying_vehicle_number(self, parking_id):
        if parking_id not in self.parking_id_to_parking:
            raise Exception("not a valid parking_id")
        p = self.parking_id_to_parking[parking_id]
        if p.end_time is not None:
            raise Exception("parking has been emptied.")
        return p.vehicle_number

    def free(self, parking_id, pl_charges):
        if parking_id not in self.parking_id_to_parking:
            raise Exception("No parking exists with given id.")
        parking = self.parking_id_to_parking[parking_id]
        if parking.end_time is not None:
            raise Exception("parking already free")
        parking.end_time = datetime.now() + timedelta(hours=28)
        td = (parking.end_time - parking.start_time)
        units = td.seconds // (60 * 60)
        units += (td.days * 24)
        charge = 0
        for w in pl_charges:
            if units > w[0] and units <= w[1]:
                if w[0] >= 24:
                    a = units // 24
                    if units % 24 > 0:
                        a += 1
                    charge = a * w[2]
                else:
                    charge = w[2]
                parking.charge = charge
                break
        self.parking_id_to_parking[parking_id] = parking
        return charge


class VehicleManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.vehicle_number_to_vehicle = {}
        self.vehicle_number_to_parking_id = {}
        self.parking_manger = ParkingManager()

    def add_vehicle(self, type_of_vehicle, vehicle_number):
        if vehicle_number in self.vehicle_number_to_vehicle:
            return self.vehicle_number_to_vehicle[vehicle_number]
        if type_of_vehicle not in VehicleType.ALLOWED_TYPES:
            raise Exception("Invalid vehicle type.")
        v = Vehicle(vehicle_number=vehicle_number, type_of_vehicle=type_of_vehicle)
        self.vehicle_number_to_vehicle[vehicle_number] = v
        return v

    def get_vehicle_by_number(self, vehicle_number):
        if vehicle_number not in self.vehicle_number_to_vehicle:
            raise Exception("vehicle_number not registerd.")
        return self.vehicle_number_to_vehicle[vehicle_number]

    def get_vehicle_type(self, vehicle_number):
        vehicle = self.get_vehicle_by_number(vehicle_number)
        return vehicle.type_of_vehicle

    def register_parking(self, vehicle_number, parking_id):
        vehicle = self.get_vehicle_by_number(vehicle_number)
        if vehicle_number not in self.vehicle_number_to_parking_id:
            self.vehicle_number_to_parking_id[vehicle_number] = []
        self.vehicle_number_to_parking_id[vehicle_number].append(parking_id)

    def get_parking_history(self, vehicle_number):
        v = self.get_vehicle_by_number(vehicle_number)
        for p in self.vehicle_number_to_parking_id.get(vehicle_number, []):
            print(self.parking_manger.get_by_id(p))


def master():
    PL = ParkingLotManager()
    V = VehicleManager()
    P = ParkingManager()
    v1 = V.add_vehicle("TWO_WHEELER", "V1")
    v2 = V.add_vehicle("CAR", "V2")
    v3 = V.add_vehicle("TWO_WHEELER", "V3")
    v4 = V.add_vehicle("CAR", "V4")
    # v5 = V.add_vehicle("TWO_WHEELER", "V5")
    pl1 = PL.register_parking_lot({"TWO_WHEELER": 2, "CAR": 4},
                                  {"TWO_WHEELER": [[0, 1, 20], [1, 3, 50], [3, 24, 80], [24, math.inf, 80]],
                                   "CAR": [[0, 1, 30], [1, 3, 70], [3, 24, 100], [24, math.inf, 100]]})
    pl2 = PL.register_parking_lot({"TWO_WHEELER": 4, "CAR": 3},
                                  {"TWO_WHEELER": [[0, 1, 20], [1, 3, 50], [3, 24, 80], [24, math.inf, 80]],
                                   "CAR": [[0, 1, 30], [1, 3, 70], [3, 24, 100], [24, math.inf, 100]]})
    PL.park_vehicle(pl1, "V1")
    PL.park_vehicle(pl1, "V3")
    # PL.park_vehicle(pl1, "V5")
    PL.park_vehicle(pl2, "V4")
    print(PL.exit_vehicle(pl1, "V1"))
    PL.park_vehicle(pl2, "V2")
    # PL.park_vehicle(pl2, "V2")
    # PL.exit_vehicle(pl1, "V2")
    print(PL.exit_vehicle(pl2, "V2"))
    V.get_parking_history("V2")
    V.get_parking_history("V1")


if __name__ == '__main__':
    master()
