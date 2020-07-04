# Problem Statement
# Coffee machine
# 1. It will be serving some beverages.
# 2. Each beverage will be made using some ingredients.
# 3. Assume time to prepare a beverage is the same for all cases.
# 4. The quantity of ingredients used for each beverage can vary. Also the same
# ingredient (ex: water) can be used for multiple beverages.
# 5. There would be N ( N is an integer ) outlet from which beverages can be
# served.
# 6. Maximum N beverages can be served in parallel.
# 7. Any beverage can be served only if all the ingredients are available in terms
# of quantity.
# 8. There would be an indicator which would show which all ingredients are
# running low. We need some methods to refill them.
# 9. Please provide functional integration test cases for maximum coverage.


# Running instructions:
# 1. On console: python coffee_machine.py
# 2. Above line will setup the system and run test cases and print relevant output
# 3. If want to test with different input change fixture in get_fixture method.

from threading import Lock, BoundedSemaphore, Thread


class CoffeeMachine:
    def __init__(self, outlets, beverage_names, ingredient_to_quantity_map=None,
                 ingredient_to_threshold_for_notification=None):
        self.id = id(self)
        self.outlets = outlets
        self.beverage_names = beverage_names
        self.ingredient_to_quantity_map = ingredient_to_quantity_map or {}
        self.ingredient_to_threshold_for_notification = ingredient_to_threshold_for_notification or {}
        self.lock = Lock()  # for handling concurrent access to quantity maps
        self.outlet_semaphore = BoundedSemaphore(value=outlets)  # to allow maximum of #outlets dispense requests


class Beverage:
    def __init__(self, name, ingredient_to_quantity_map=None):
        self.name = name
        self.ingredient_to_quantity_map = ingredient_to_quantity_map or {}


class Ingredient:
    def __init__(self, name):
        self.id = id(id)
        self.name = name


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


class MachineManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.coffee_machine_id_to_coffee_machine_map = {}  # will work as in-memory DB for coffee machine model
        self.beverage_manager = BeverageManager()  # this will return the singleton of BeverageManager new object won't be created
        self.ingredient_manager = IngredientManager()  # this will return the singleton of IngredientManager new object won't be created

    def create(self, no_of_outlet, beverage_names, ingredient_to_quantity_map=None,
               ingredient_to_threshold_for_notification=None):

        # validations
        ingredient_names = set(
            list(ingredient_to_threshold_for_notification.keys()) + list(ingredient_to_quantity_map.keys()))
        self.ingredient_manager.get_by_names(ingredient_names)
        for quantity in ingredient_to_quantity_map.values():
            self.__validate_quantity(quantity)

        for quantity in ingredient_to_threshold_for_notification.values():
            self.__validate_quantity(quantity)
        # validations end

        cm = CoffeeMachine(outlets=no_of_outlet, beverage_names=beverage_names,
                           ingredient_to_quantity_map=ingredient_to_quantity_map,
                           ingredient_to_threshold_for_notification=ingredient_to_threshold_for_notification)
        self.coffee_machine_id_to_coffee_machine_map[cm.id] = cm
        return cm.id

    def __validate_id(self, coffee_machine_id):
        if coffee_machine_id not in self.coffee_machine_id_to_coffee_machine_map:
            raise Exception("Invalid coffee_machine_id.")

    def __validate_ingredient_name(self, ingredient_name):
        self.ingredient_manager.get_by_name(ingredient_name)

    def __validate_quantity(self, quantity):
        if quantity <= 0:
            raise Exception("Ingredient quantity must be a positive integer.")

    def get_by_id(self, coffee_machine_id):
        self.__validate_id(coffee_machine_id)
        # will return copy of the state to restrict edit access to only MachineManager
        return self.coffee_machine_id_to_coffee_machine_map[coffee_machine_id].__dict__.copy()

    def add_ingredient(self, coffee_machine_id, ingredient_name, quantity):
        self.__validate_quantity(quantity)
        self.__validate_id(coffee_machine_id)
        self.__validate_ingredient_name(ingredient_name)
        cm = self.coffee_machine_id_to_coffee_machine_map[coffee_machine_id]
        with cm.lock:
            if ingredient_name not in cm.ingredient_to_quantity_map:
                cm.ingredient_to_quantity_map[ingredient_name] = 0
            cm.ingredient_to_quantity_map[ingredient_name] += quantity
            self.__update_coffee_machine(cm)
            print("Coffee machine(id: %s) ingredient quantities after adding %s: %s" % (
                coffee_machine_id, ingredient_name, cm.ingredient_to_quantity_map))

    def __update_coffee_machine(self, cm):
        self.coffee_machine_id_to_coffee_machine_map[cm.id] = cm

    def dispense_beverage(self, coffee_machine_id, beverage_name):
        self.__validate_id(coffee_machine_id)
        cm = self.coffee_machine_id_to_coffee_machine_map[coffee_machine_id]
        with cm.outlet_semaphore:
            print("dispense request for %s from machine (id:%s)\n" % (beverage_name, coffee_machine_id))
            beverage = self.beverage_manager.get_by_name(beverage_name)
            if beverage_name not in cm.beverage_names:
                raise Exception("Asked beverage not available in this machine.")
            required_ingredient_to_quantity_map = beverage['ingredient_to_quantity_map']
            print("%s required quantities: %s\n" % (beverage_name, required_ingredient_to_quantity_map))
            with cm.lock:
                print("Coffee Machine(id: %s) available quantities: %s" % (
                    coffee_machine_id, cm.ingredient_to_quantity_map))
                for ingredient_name, required_quantity in required_ingredient_to_quantity_map.items():
                    if ingredient_name not in cm.ingredient_to_quantity_map:
                        raise Exception(
                            "%s cannot be prepared because %s is not available" % (beverage_name, ingredient_name))
                    if required_quantity > cm.ingredient_to_quantity_map[ingredient_name]:
                        raise Exception(
                            "%s cannot be prepared because item %s is 0" % (beverage_name, ingredient_name))
                for ingredient_name, required_quantity in required_ingredient_to_quantity_map.items():
                    cm.ingredient_to_quantity_map[ingredient_name] -= required_quantity
                    if cm.ingredient_to_quantity_map[
                        ingredient_name] <= cm.ingredient_to_threshold_for_notification.get(
                        ingredient_name, 0):
                        self.notify_low_on_ingredient(ingredient_name)
                self.__update_coffee_machine(cm)
            print("%s is prepared.\n" % (beverage_name))
            print("Coffee Machine(id: %s) available quantities: %s\n" % (
                coffee_machine_id, cm.ingredient_to_quantity_map))

    def notify_low_on_ingredient(self, ingredient_name):
        print("Low on %s, please refill." % (ingredient_name))


class BeverageManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.beverage_name_to_beverage_map = {}  # will work as in-memory DB for beverage model
        self.ingredient_manager = IngredientManager()  # this will return the singleton of IngredientManager new object wont be created

    def create(self, name, ingredient_to_quantity_map):
        if name in self.beverage_name_to_beverage_map:
            raise Exception("Beverage with same name is already present in DB.")
        # validations for ingredient ids and quantity
        ingredient_names = ingredient_to_quantity_map.keys()
        self.ingredient_manager.get_by_names(ingredient_names)
        for quantity in ingredient_to_quantity_map.values():
            if quantity <= 0:
                raise Exception("Ingredient quantity must be a positive integer.")
        # validations done

        b = Beverage(name=name, ingredient_to_quantity_map=ingredient_to_quantity_map)
        self.beverage_name_to_beverage_map[b.name] = b
        return b.name

    def __validate_name(self, name):
        if name not in self.beverage_name_to_beverage_map:
            raise Exception("Invalid beverage name.")

    def get_by_name(self, beverage_name):
        self.__validate_name(beverage_name)
        # will return copy of the state to restrict edit to only BeverageManager
        return self.beverage_name_to_beverage_map[beverage_name].__dict__.copy()


class IngredientManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.ingredient_name_to_ingredient_map = {}  # will work as in-memory DB for ingredient model

    def create(self, name):
        i = Ingredient(name=name)
        self.ingredient_name_to_ingredient_map[i.name] = i
        return i.name

    def __validate_name(self, name):
        if name not in self.ingredient_name_to_ingredient_map:
            raise Exception("Invalid ingredient name.")

    def get_by_name(self, name):
        self.__validate_name(name)
        # will return copy of the state to restrict edit to only IngredientManager
        return self.ingredient_name_to_ingredient_map[name].__dict__.copy()

    def get_by_names(self, names):
        invalid_ingredient_names = set(names) - set(self.ingredient_name_to_ingredient_map.keys())
        if invalid_ingredient_names:
            raise Exception("Ingredients with %s names are not valid." % (names))
        return [self.ingredient_name_to_ingredient_map[name].__dict__.copy() for name in names]


def master():

    # first time creation of manager singletons
    machine_manager = MachineManager()
    ingredient_manager = IngredientManager()
    beverage_manager = BeverageManager()

    payload = get_fixture()
    for ingredient in payload.get('ingredients', []):
        ingredient_manager.create(ingredient)
    for beverage in payload.get('beverages', []):
        beverage_manager.create(beverage.get('name'), beverage.get('ingredient_to_quantity_map'))
    machine = payload.get('machine')
    cm_id = machine_manager.create(machine.get('outlets'), machine.get('beverages'), machine.get('ingredient_to_quantity_map'),
                           machine.get('ingredient_to_threshold_for_notification'))
    print("Setup complete.\n")

    print("Test case 1. Ingredient not available case for ginger tea, dispense request will print exception.")
    try:
        machine_manager.dispense_beverage(cm_id, "ginger tea")
    except Exception as e:
        print(e.__str__())  # Exception: ginger tea cannot be prepared because sugar syrup is not available
    print()

    print("Test case 2: Refill ingredient for ginger tea and again make dispense request for ginger tea.")
    machine_manager.add_ingredient(cm_id, "sugar syrup", 50)
    machine_manager.dispense_beverage(cm_id, "ginger tea")
    print()

    print("Test case 3: Notification for low on leaves syrup.")
    machine_manager.dispense_beverage(cm_id, "ginger tea")
    print()

    print("adding some more ingredients")
    machine_manager.add_ingredient(cm_id, "coffee syrup", 20)
    machine_manager.add_ingredient(cm_id, "elaichi syrup", 40)
    machine_manager.add_ingredient(cm_id, "tea leaves syrup", 40)
    machine_manager.add_ingredient(cm_id, "hot water", 200)
    machine_manager.add_ingredient(cm_id, "sugar syrup", 50)
    print()

    print("Test case 4: Maximum #outlets(3 in our example) concurrent dispense requests.")
    t1 = Thread(target=machine_manager.dispense_beverage, args=(cm_id, "elaichi tea"))
    t2 = Thread(target=machine_manager.dispense_beverage, args=(cm_id, "ginger tea"))
    t3 = Thread(target=machine_manager.dispense_beverage, args=(cm_id, "coffee"))
    t4 = Thread(target=machine_manager.dispense_beverage,
                args=(cm_id, "elaichi tea"))  # this will be processed when atleast one is finished from above 3
    t1.start()
    t2.start()
    t3.start()
    t4.start()


def get_fixture():
    """Right now it's hard coded dict we can change the script to take json file as input"""
    ingredients = ["hot water", "hot milk", "tea leaves syrup", "ginger syrup", "sugar syrup", "elaichi syrup",
                   "coffee syrup"]
    beverages = [
        {
            "name": "ginger tea",
            "ingredient_to_quantity_map": {
                "hot water": 50,
                "hot milk": 10,
                "tea leaves syrup": 10,
                "ginger syrup": 5,
                "sugar syrup": 10
            }
        },
        {
            "name": "elaichi tea",
            "ingredient_to_quantity_map": {
                "hot water": 50,
                "hot milk": 10,
                "tea leaves syrup": 10,
                "elaichi syrup": 5,
                "sugar syrup": 10
            }
        },
        {
            "name": "coffee",
            "ingredient_to_quantity_map": {
                "hot water": 30,
                "hot milk": 10,
                "coffee syrup": 5,
                "sugar syrup": 10
            }
        }
    ]
    machine = {
        "outlets": 3,
        "beverages": ["ginger tea", "elaichi tea", "coffee"],
        "ingredient_to_quantity_map": {
            "hot water": 200,
            "hot milk": 90,
            "tea leaves syrup": 30,
            "ginger syrup": 30
        },
        "ingredient_to_threshold_for_notification": {
            "hot water": 20,
            "hot milk": 20,
            "ginger syrup": 10,
            "tea leaves syrup": 10
        }
    }

    return {
        "ingredients": ingredients,
        "beverages": beverages,
        "machine": machine,
    }


if __name__ == '__main__':
    master()  # will setup and run all the test cases
