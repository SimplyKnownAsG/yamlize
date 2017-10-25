import unittest

from yamlize import yamlizable
from yamlize import Attribute
from yamlize import Dynamic
from yamlize import yaml_keyed_list
from yamlize import yaml_list
from yamlize import yaml_map
from yamlize import YamlizingError


@yamlizable(Attribute(name='name', type=str),
            Attribute(name='age', type=int))
class Animal(object):
    def __init__(self, name, age):
        self.name = name
        self.age = age


@yaml_list(item_type=Animal)
class AnimalList(object):
    pass


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


class TestMergeAndAnchor(unittest.TestCase):

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
        things = Things.load(TestMergeAndAnchor.multiple_merge)
        actual = Things.dump(things).strip()
        self.assertEqual(TestMergeAndAnchor.multiple_merge, actual)

    def test_multiple_merge_delete_parent(self):
        things = Things.load(TestMergeAndAnchor.multiple_merge)
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
            BadData.load(TestMergeAndAnchor.bad_data_merge)

    list_inheritance = """
- &lucy {name: Lucy, age: 5}
- {<<: *lucy, name: Possum}
""".strip()

    def test_yaml_list_inheritance(self):
        pets = AnimalList.load(TestMergeAndAnchor.list_inheritance)
        self.assertEqual('Lucy', pets[0].name)
        self.assertEqual('Possum', pets[1].name)
        self.assertEqual(5, pets[1].age)
        actual = AnimalList.dump(pets).strip()
        self.assertEqual(TestMergeAndAnchor.list_inheritance, actual)

    keyed_list_complete_inheritance = """
thing1: &thing1
  int_attr: 12
  str_attr: haha
  float_attr: 42.42
thing2: *thing1
""".strip()

    def test_yaml_keyed_complete_inheritance(self):
        things = Things.load(TestMergeAndAnchor.keyed_list_complete_inheritance)
        self.assertIn('thing1', things)
        self.assertIn('thing2', things)
        actual = Things.dump(things).strip()
        self.assertEqual(TestMergeAndAnchor.keyed_list_complete_inheritance,
                         actual)

    list_from_alias = """
- &lucy
  name: Lucy
  age: 5
- *lucy
""".strip()

    def test_yaml_list_complete_inheritance(self):
        lucy_twice = AnimalList.load(TestMergeAndAnchor.list_from_alias)
        actual = AnimalList.dump(lucy_twice).strip()
        self.assertEqual(TestMergeAndAnchor.list_from_alias, actual)


class TestSubclassing(unittest.TestCase):

    multiple_merge = '''
thing1: &thing1
  int_attr: 1
  str_attr: '1'
  float_attr: 99.2
thing2: &thing2
  <<: *thing1
  str_attr: an actual string
  color: blue
thing3:
  <<: *thing1
  <<: *thing2
  float_attr: 42.42
  color: green
'''.strip()

    def test_object_subclass(self):
        @yamlizable(Attribute(name='color', type=str, default='yellow'))
        class ColorThing(Thing):
            pass

        self.assertIn('int_attr', ColorThing.attributes.by_name)

        @yaml_keyed_list(key_name='name', item_type=ColorThing)
        class CThings(object):
            pass

        things = CThings.load(TestSubclassing.multiple_merge)
        actual = CThings.dump(things).strip()
        self.assertEqual('an actual string', things['thing3'].str_attr)
        self.assertEqual(TestSubclassing.multiple_merge, actual)


if __name__ == '__main__':
    unittest.main()

