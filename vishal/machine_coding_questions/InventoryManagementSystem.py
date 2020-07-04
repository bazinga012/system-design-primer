# import requests
# import mysql.connector
# import pandas as pd


class ProductCategory:
    def __init__(self, creation_payload):
        self.name = creation_payload['name']


class Product:
    def __init__(self, creation_payload):
        self.product_category = creation_payload['product_category']
        self.name = creation_payload['name']
        self.description = creation_payload['description']
        self.quantity = creation_payload['quantity']
        # other attributes can be added


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


class ProductCategoryManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.category_key_to_categories = {}  # name is pk

    def _validate(self, payload):
        if 'name' not in payload:
            raise Exception("ProductCategory name must be present.")
        if payload['name'] in self.category_key_to_categories:
            raise Exception("ProductCategory with given name already exists.")

    def create(self, payload):
        self._validate(payload)
        p = ProductCategory(payload)
        self.category_key_to_categories[p.name] = p
        return p.name

    def get_by_name(self, name):
        if name not in self.category_key_to_categories:
            raise Exception("Category with given name doesn't exist.")


class InventoryManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.product_category_manager = ProductCategoryManager()
        self.product_name_to_product = {}
        self.search_stretegist = InventorySearchStrategist()
        self.search_algo = self.search_stretegist.get_search_algo()

    def _is_pk_exists(self, name):
        return name in self.product_name_to_product

    def _validate(self, payload):
        required_keys = {'name', 'product_category'}
        optional_keys = {'description', 'quantity'}
        absent_keys = required_keys - set(list(payload.keys()))
        if absent_keys:
            raise Exception(f"{absent_keys} must be present in payload.")
        self.product_category_manager.get_by_name(payload.get('product_category'))
        allowed_keys = required_keys | optional_keys
        validated_payload = {}
        for key in allowed_keys:
            validated_payload[key] = payload.get(key)
        return validated_payload

    def _validate_update(self, payload):
        allowed_to_update = ['description', 'product_category', 'quantity']
        return {key: val for key, val in payload.items() if key in allowed_to_update}

    def create(self, payload):
        if self._is_pk_exists(payload.get('name')):
            raise Exception("Product with name already exists.")
        validated_payload = self._validate(payload)
        p = Product(validated_payload)
        self.product_name_to_product[p.name] = p
        self.search_algo.add_in_ds(p.__dict__)
        return p.name

    def get_by_name(self, name):
        if not self._is_pk_exists(name):
            raise Exception("Product with given name doesn't exist.")
        return self.product_name_to_product[name]

    def update(self, name, payload):  # name is pk
        p = self.get_by_name(name)
        initial = p
        validated_payload = self._validate_update(payload)
        for key, value in validated_payload.items():
            p.__dict__[key] = value
        self.product_name_to_product[p.name] = p
        self.search_algo.update_ds(initial.__dict__, p.__dict__)
        return p.name

    def delete(self, name):
        p = self.get_by_name(name)
        self.product_name_to_product.pop(p.name)
        self.search_algo.remove_from_ds(p.__dict__)
        return p.name

    def search(self, term):
        pk_ids = self.search_algo.search(term)
        res = []
        for pk in pk_ids:
            try:
                p = self.get_by_name(pk)
                res.append(p)
            except Exception as e:
                print(e)
        return res


class InventorySearchStrategist(metaclass=SingletonMetaClass):
    def __init__(self, conf={}):
        self.config = conf

    def get_search_algo(self):
        # config can be used to decide which algo to use
        return BasicNameBasedSearchAlgo()


class TrieNode:
    def __init__(self):
        self.word_end_count = 0
        self.char_map = {}

    def insert(self, s):
        curr = self
        new_chars = 0
        for ch in s:
            if ch in curr.char_map:
                curr = curr.char_map[ch]
            else:
                curr.char_map[ch] = TrieNode()
                curr = curr.char_map[ch]
                new_chars += 1
        curr.word_end_count += 1

    def __get_till_leaf(self, node, s):
        res = []
        for ch in node.char_map:
            ns = s + ch
            if node.char_map[ch].word_end_count > 0:
                res.append(ns)
            res += (node.__get_till_leaf(node.char_map[ch], ns))
        return res

    def search(self, s):
        curr = self
        for ch in s:
            if ch in curr.char_map:
                curr = curr.char_map[ch]
            else:
                return []
        res = self.__get_till_leaf(curr, s)
        if curr.word_end_count > 0:
            res.append(s)
        return res

    def remove(self, s, n, i=0):
        if n <= i:
            return
        curr = self
        ch = s[i]
        if ch in curr.char_map:
            curr = curr.char_map[ch]
            if i == n - 1:
                if curr.word_end_count == 0:
                    raise Exception("Given string not part of trie.")
                curr.word_end_count -= 1
            else:
                removed_char = curr.remove(s, n, i + 1)
                if removed_char:
                    del curr.char_map[removed_char]
            if not curr.char_map.keys():
                del curr
                return ch
        else:
            raise Exception("Given string not part of trie.")

    def print_dict(self, s=''):
        curr = self
        if curr.word_end_count > 0:
            print(s)
        chars = list(curr.char_map.keys())
        chars.sort()
        for ch in chars:
            curr.char_map[ch].print_dict(s + ch)


class BasicNameBasedSearchAlgo(metaclass=SingletonMetaClass):
    def __init__(self):
        self.trie = TrieNode()

    def add_in_ds(self, data):
        self.trie.insert(data['name'])

    def update_ds(self, prev_data, data):
        self.trie.remove(prev_data['name'], len(prev_data['name']))
        self.trie.insert(data['name'])

    def remove_from_ds(self, data):
        self.trie.remove(data['name'], len(data['name']))

    def search(self, term):
        return self.trie.search(term)


def solution():
    p = ProductCategoryManager()
    i = InventoryManager()
    p.create({"name": "Mobiles"})
    p.create({"name": "Apparels"})
    i.create({"name": "redmi", "product_category": "Mobiles", "description": "chinese phone", "quantity": 5})
    i.create(
        {"name": "redmi 9 pro", "product_category": "Mobiles", "description": "awesome chinese phone", "quantity": 2})
    i.create({"name": "Tommy Jeans", "product_category": "Apparels", "description": "Hell expensive", "quantity": 2})
    i.create({"name": "Tommy stripped Jeans", "product_category": "Apparels", "description": "For poor people",
              "quantity": 1})
    i.create({"name": "Tommi tapered Jeans", "product_category": "Apparels", "description": "For poor people",
              "quantity": 1})

    print("Test case1: Search for Tommy After insert")
    res = i.search("Tommy")
    [print(s.__dict__) for s in res]

    print()
    print("Test case2: Search After similar name product Tommi Tommy products wont show ups")
    res = i.search("Tommi")
    [print(s.__dict__) for s in res]

    print()
    i.update("Tommy Jeans", {"description": "Available for cheap price"})
    print("Test case3: Search for Tommy After Updating description for Tommy Jeans")
    res = i.search("Tommy")
    [print(s.__dict__) for s in res]

    print()
    i.delete("Tommy Jeans")
    print("Test case4: Search for Tommy After Deleting Tommy Jeans")
    res = i.search("Tommy")
    [print(s.__dict__) for s in res]

    res = i.search("redmi")
    [print(s.__dict__) for s in res]


if __name__ == '__main__':
    solution()

