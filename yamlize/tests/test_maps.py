import unittest
import re
import pickle
import copy

from yamlize import Object
from yamlize import YamlizingError
from yamlize import Attribute
from yamlize import Map
from yamlize import Typed
from yamlize import Dynamic
from yamlize import KeyedList
from yamlize.attribute_collection import MapAttributeCollection


class Animal(Object):
    name = Attribute(type=str)
    age = Attribute(type=int)

    def __init__(self, name, age):
        Object.__init__(self)
        self.name = name
        self.age = age


class Kennel(Map):

    key_type = Typed(str)

    value_type = Animal


kennel_yaml = """
Lucy:
    name: Lucy
    age: 5
Possum:
    name: Possum
    age: 5
"""


class NamedKennel(KeyedList):
    key_attr = Animal.name
    item_type = Animal


named_kennel_yaml = """
Lucy:
    age: 5
Possum:
    age: 5
"""


class Test_NamedKennel(unittest.TestCase):

    def test_keyed_list_fails_with_incorrect_assignment(self):
        poss = Animal('Possum', 5)
        kennel = NamedKennel()
        self.assertEqual('Possum', Animal.name.__get__(poss))
        with self.assertRaisesRegex(KeyError, 'expected.*`Possum`'):
            kennel[5] = poss


class Test_from_yaml(unittest.TestCase):

    def test_bad_type(self):
        with self.assertRaises(YamlizingError):
            # fails because of a lack of the name: attribute
            Kennel.load(named_kennel_yaml)

        with self.assertRaises(YamlizingError):
            # fails because of duplicated name
            NamedKennel.load(kennel_yaml)

    def test_attrs_applied(self):
        # once with normal dictionary
        # once with KeyedList
        for kennel in (Kennel.load(kennel_yaml),
                       NamedKennel.load(named_kennel_yaml)):
            poss = kennel['Possum']
            self.assertTrue('Possum', poss.name)
            self.assertTrue(5, poss.age)

    def test_incomplete_data(self):
        with self.assertRaises(YamlizingError):
            Kennel.load('{Lucy: {name: Lucy}}')

        with self.assertRaises(YamlizingError):
            NamedKennel.load('{Lucy: }')


class Test_to_yaml(unittest.TestCase):

    def setUp(self):
        self.poss = Animal('Possum', 5)
        self.lucy = Animal('Lucy', 5)

        self.kennel = Kennel()
        self.kennel[self.poss.name] = self.poss
        self.kennel[self.lucy.name] = self.lucy

        self.named_kennel = NamedKennel()
        self.named_kennel.add(self.poss)
        self.named_kennel.add(self.lucy)

    def test_write_map(self):
        yaml = Kennel.dump(self.kennel)
        self.assertIn('name: Lucy', yaml)
        self.assertIn('age: 5', yaml)
        self.assertLess(yaml.index('Possum'), yaml.index('Lucy'))

    def test_write_NamedList(self):
        yaml = NamedKennel.dump(self.named_kennel)
        self.assertNotIn('name:', yaml)
        self.assertIn('age: ', yaml)
        self.assertLess(yaml.index('Possum'), yaml.index('Lucy'))

class Test_two_way(unittest.TestCase):

    nested_named_kennel = """
bark and play:
  Lucy:
    age: 5
  Possum:
    age: 5
paws for fun:
  Luna:
    age: 1
  Maggie:
    age: 2
""".strip()

    def test_nested(self):
        class Kennels(Map):
            key_type = Typed(str)
            value_type = NamedKennel

        kennels = Kennels.load(Test_two_way.nested_named_kennel)
        bap = kennels['bark and play']
        self.assertIn('Lucy', bap)
        self.assertIn('Possum', bap)

        pff = kennels['paws for fun']
        self.assertIn('Luna', pff)
        self.assertIn('Maggie', pff)

        actual = Kennels.dump(kennels)
        self.assertEqual(Test_two_way.nested_named_kennel, actual.strip())

    pet_map1 = """
G:
  name: G
  pets: &lucy_possum
    Lucy:
      age: 5
    Possum:
      age: 5
A:
  name: A
  pets: *lucy_possum
J:
  name: J
  pets: {Luna: {age: 1}}
T: {name: T, pets: {Maggie: {age: 2}}}
""".strip()

    def test_owner1(self):
        class Owner(Object):
            name = Attribute(type=str)
            pets = Attribute(type=NamedKennel)

        class PetMap(Map):
            key_type = Typed(str)
            value_type = Owner

        peeps = PetMap.load(Test_two_way.pet_map1)

        actual = PetMap.dump(peeps).strip()
        self.assertEqual(Test_two_way.pet_map1, actual)

    pet_map2 = """
G:
  pets: &lucy_possum
    Lucy:
      age: 5
    Possum:
      age: 5
A:
  pets: *lucy_possum
J:
  pets: {Luna: {age: 1}}
T: {pets: {Maggie: {age: 2}}}
""".strip()

    def test_owner2(self):

        class Owner(Object):
            name = Attribute(type=str)
            pets = Attribute(type=NamedKennel)

        class PetMap(KeyedList):
            key_attr = Owner.name
            item_type = Owner

        peeps = PetMap.load(Test_two_way.pet_map2)

        actual = PetMap.dump(peeps).strip()
        self.assertEqual(Test_two_way.pet_map2, actual)

    map_with_attribute = '''
name: blt
meat: bacon
cheese: Gorgonzola
'''.strip()

    def test_map_with_attribute(self):
        class NamedMap(Map):
            key_type = Typed(str)
            value_type = Dynamic
            name = Attribute(type=str)

        blt = NamedMap.load(self.__class__.map_with_attribute)
        self.assertNotIn('name', blt)
        self.assertEqual('blt', blt.name)
        self.assertFalse(hasattr(blt, 'meat'))
        self.assertFalse(hasattr(blt, 'cheese'))
        self.assertEqual('bacon', blt['meat'])
        self.assertEqual('Gorgonzola', blt['cheese'])

        actual = NamedMap.dump(blt).strip()
        self.assertEqual(self.__class__.map_with_attribute, actual)

    menu = '''
blt:
  fruit: tomato
  veggie: lettuce
  meat: bacon
  cheese: Gorgonzola
grilled cheese:
  cheese: American
  bread: French
  butter: true
'''.strip()

    def test_keyed_list_and_map_with_attribute(self):
        class MenuItem(Map):
            key_type = Typed(str)
            value_type = Dynamic
            name = Attribute(type=str)

        class Menu(KeyedList):
            key_attr = MenuItem.name
            item_type = MenuItem

        menu = Menu.load(self.__class__.menu)
        blt = menu['blt']
        self.assertNotIn('name', blt)
        self.assertEqual('blt', blt.name)
        self.assertFalse(hasattr(blt, 'meat'))
        self.assertFalse(hasattr(blt, 'cheese'))
        self.assertEqual('bacon', blt['meat'])
        self.assertEqual('Gorgonzola', blt['cheese'])

        gc = menu['grilled cheese']
        self.assertEqual(True, gc['butter'])

        actual = Menu.dump(menu).strip()
        self.assertEqual(self.__class__.menu, actual)

    daily_menu = '''
day: Monday
blt:
  fruit: tomato
  meat: bacon
grilled cheese:
  with: bacon
'''.strip()

    def test_daily_menu(self):
        class MenuItem(Map):
            key_type = Typed(str)
            value_type = Dynamic
            name = Attribute(type=str)

        self.assertIsInstance(MenuItem.attributes, MapAttributeCollection)

        class DailyMenu(KeyedList):
            key_attr = MenuItem.name
            item_type = MenuItem
            day = Attribute(type=str)

        menu = DailyMenu.load(self.__class__.daily_menu)
        self.assertEqual('Monday', menu.day)
        self.assertNotIn('Monday', menu)
        self.assertIn('blt', menu)
        self.assertIsInstance(menu['grilled cheese'], MenuItem)

        actual = DailyMenu.dump(menu).strip()
        self.assertEqual(self.__class__.daily_menu, actual)

    daily_menus = '''
Monday:
  blt: &blt
    fruit: tomato
    meat: bacon
  grilled cheese:
    with butter: true
Tuesday:
  blt tuesday: *blt
  fries:
    potatoes: from Idaho
'''.strip()

    def test_daily_menus(self):
        class MenuItem(Map):
            key_type = Typed(str)
            value_type = Dynamic
            name = Attribute(type=str)

        class DailyMenu(KeyedList):
            key_attr = MenuItem.name
            item_type = MenuItem
            day = Attribute(type=str)

        class Menus(KeyedList):
            key_attr = DailyMenu.day
            item_type = DailyMenu

        menus = Menus.load(self.__class__.daily_menus)
        self.assertEqual('Monday', menus['Monday'].day)
        tue_menu = menus['Tuesday']
        self.assertIsInstance(tue_menu, DailyMenu)
        self.assertIsInstance(tue_menu['fries'], MenuItem)
        blt_tue = tue_menu['blt tuesday']
        self.assertEqual('tomato', blt_tue['fruit'])

        actual = Menus.dump(menus).strip()
        self.assertEqual(self.__class__.daily_menus, actual)

    def test_assignKeyedListItem(self):
        class MenuItem(Map):
            key_type = Typed(str)
            value_type = Dynamic
            name = Attribute(type=str)

        class DailyMenu(KeyedList):
            key_attr = MenuItem.name
            item_type = MenuItem
            day = Attribute(type=str)
            def __init__(self, day):
                self.day = day

        class Menus(KeyedList):
            key_attr = DailyMenu.day
            item_type = DailyMenu

        menus = Menus.load(self.__class__.daily_menus)
        wed = DailyMenu('Wednesday')
        menus.add(wed)
        wed.add(menus['Monday']['blt'])
        actual = Menus.dump(menus).strip()
        self.assertEqual(self.__class__.daily_menus + '\nWednesday:\n  blt: *blt', actual)

    def test_pickleable(self):
        kennel = NamedKennel.load(named_kennel_yaml)
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            kennel2 = pickle.loads(pickle.dumps(kennel, protocol=protocol))
            self.assertEqual(kennel2['Lucy'].age, 5)

    def test_copy(self):
        kennel = NamedKennel.load(named_kennel_yaml)
        kennel2 = copy.copy(kennel)
        self.assertEqual(kennel2['Lucy'].age, 5)

    def test_deepcopy(self):
        kennel = NamedKennel.load(named_kennel_yaml)
        kennel2 = copy.deepcopy(kennel)
        self.assertEqual(kennel2['Lucy'].age, 5)


if __name__ == '__main__':
    unittest.main()

