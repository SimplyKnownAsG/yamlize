
import unittest

from yamlize import yamlizable
from yamlize import Attribute
from yamlize import yaml_keyed_list
from yamlize import Sequence
from yamlize import YamlizingError


@yamlizable(Attribute(name='name', type=str),
            Attribute(name='age', type=int))
class Animal(object):
    def __init__(self, name, age):
        self.name = name
        self.age = age


class AnimalList(Sequence):
    item_type = Animal


@yaml_keyed_list(key_name='name',
                 item_type=Animal)
class NamedKennel(object):
    pass


@yamlizable(Attribute(name='name', type=str),
            Attribute(name='int_attr', type=int),
            Attribute(name='str_attr', type=str),
            Attribute(name='float_attr', type=float))
class Thing(object):
    pass


@yaml_keyed_list(key_name='name', item_type=Thing)
class Things(object):
    pass


class TestInheritance(unittest.TestCase):

    multiple_merge = '''
thing1: &thing1
  int_attr: 1
  str_attr: '1'
  float_attr: 99.2
thing2: &thing2
  <<: *thing1
  str_attr: an actual string
thing3:
  <<: *thing1
  <<: *thing2
  float_attr: 42.42
'''.strip()

    def test_multiple_merge(self):

        things = Things.load(TestInheritance.multiple_merge)
        actual = Things.dump(things).strip()
        self.assertEqual(TestInheritance.multiple_merge, actual)

    def test_multiple_merge_delete_parent(self):
        things = Things.load(TestInheritance.multiple_merge)
        del things['thing1']
        yaml = Things.dump(things)
        self.assertNotIn('thing1', yaml)
        self.assertIn('<<: *thing2', yaml)

    bad_data_merge = '''
data: &data
  int_attr: 12.12 # bad data
things:
  thing1:
    <<: *data # this will be OK, because all data is supplied below
    int_attr: 12
    str_attr: hello
    float_attr: 99.99
  thing2:
    <<: *data # this will fail
    str_attr: howdy
    float_attr: 12.12
'''.strip()

    def test_bad_type_in_merge(self):
        @yamlizable(Attribute('data'),
                    Attribute('things', type=Things))
        class BadData(object):
            pass

        with self.assertRaisesRegexp(YamlizingError, 'this will fail'):
            BadData.load(TestInheritance.bad_data_merge)

    list_inheritance = """
- &lucy {name: Lucy, age: 5}
- {<<: *lucy, name: Possum}
""".strip()

    def test_yaml_list_inheritance(self):
        pets = AnimalList.load(TestInheritance.list_inheritance)
        self.assertEqual('Lucy', pets[0].name)
        self.assertEqual('Possum', pets[1].name)
        self.assertEqual(5, pets[1].age)
        actual = AnimalList.dump(pets).strip()
        self.assertEqual(TestInheritance.list_inheritance, actual)

    keyed_list_complete_inheritance = """
thing1: &thing1
  int_attr: 12
  str_attr: haha
  float_attr: 42.42
thing2: *thing1
""".strip()

    def test_yaml_keyed_complete_inheritance(self):
        things = Things.load(TestInheritance.keyed_list_complete_inheritance)
        self.assertIn('thing1', things)
        self.assertIn('thing2', things)
        actual = Things.dump(things).strip()
        self.assertEqual(TestInheritance.keyed_list_complete_inheritance,
                         actual)

    list_complete_inheritance = """
- &lucy
  name: Lucy
  age: 5
- *lucy
""".strip()

    def test_yaml_list_complete_inheritance(self):
        lucy_twice = AnimalList.load(TestInheritance.list_complete_inheritance)
        actual = AnimalList.dump(lucy_twice).strip()
        self.assertEqual(TestInheritance.list_complete_inheritance, actual)

if __name__ == '__main__':
    unittest.main()

