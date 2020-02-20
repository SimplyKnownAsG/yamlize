import unittest
import re

import aenum

from yamlize import Attribute
from yamlize import Dynamic
from yamlize import Object
from yamlize import Map
from yamlize import KeyedList
from yamlize import Sequence
from yamlize import YamlizingError
from yamlize import Typed


class Animal(Object):
    name = Attribute(type=str)
    age = Attribute(type=int)

    def __init__(self, name, age):
        Object.__init__(self)
        self.name = name
        self.age = age


class AnimalList(Sequence):

    item_type=Animal


class NamedKennel(KeyedList):
    key_attr = Animal.name
    item_type = Animal


class Thing(Object):
    name = Attribute(type=str)
    int_attr = Attribute(type=int)
    str_attr = Attribute(type=str)
    float_attr = Attribute(type=float)


class Things(KeyedList):
    key_attr = Thing.name
    item_type = Thing


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
        class BadData(Object):
            data = Attribute()
            things = Attribute(type=Things)

        with self.assertRaisesRegex(YamlizingError, 'this will fail'):
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

    def test_yaml_keyed_complete_inheritance_modified(self):
        things = Things.load(TestMergeAndAnchor.keyed_list_complete_inheritance)
        self.assertIn('thing1', things)
        self.assertIn('thing2', things)
        thing2 = things['thing2']
        thing2.int_attr = 19
        actual = Things.dump(things).strip()
        self.assertIn('<<: *thing1', actual)
        self.assertIn('int_attr: 19', actual)

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
        class ColorThing(Thing):
            color = Attribute(type=str, default='yellow')

        self.assertIn('int_attr', ColorThing.attributes.by_name)

        class CThings(KeyedList):
            key_attr = ColorThing.name
            item_type = ColorThing

        things = CThings.load(TestSubclassing.multiple_merge)
        actual = CThings.dump(things).strip()
        self.assertEqual('an actual string', things['thing3'].str_attr)
        self.assertEqual(TestSubclassing.multiple_merge, actual)

    def test_object_subclassing2(self):
        class Shape(Object):

            shape = Attribute(type=str)

            @classmethod
            def from_yaml(cls, loader, node, round_trip_data):
                # the node is a map, let's find the "shape" key
                for key_node, val_node in node.value:
                    key = loader.construct_object(key_node)
                    if key == 'shape':
                        subclass_name = loader.construct_object(val_node)
                        break
                else:
                    raise YamlizingError('Missing "shape" key', node)

                subclass = {
                    'Circle' : Circle,
                    'Square' : Square,
                    'Rectangle' : Rectangle
                    }[subclass_name]

                # from_yaml.__func__ is the unbound class method
                return Object.from_yaml.__func__(subclass, loader, node, round_trip_data)

        class Circle(Shape):

            radius = Attribute(type=float)

        class Square(Shape):

            side = Attribute(type=float)

        class Rectangle(Shape):

            length = Attribute(type=float)
            width = Attribute(type=float)

        class Shapes(Sequence):

            item_type = Shape

        input_str = '\n'.join(l.strip() for l in '''
        - {shape: Circle, radius: 1.0}
        - {shape: Square, side: 2.0}
        - {shape: Rectangle, length: 3.0, width: 4.0}
        '''.split('\n') if l)

        shapes = Shapes.load(input_str)

        self.assertEqual(Shapes.dump(shapes), input_str)


class ReqOptPair(Object):
    name = Attribute(type=str)
    req1 = Attribute(type=int)
    opt1 = Attribute(type=str, default=None)


class ReqOpts(KeyedList):
    key_attr = ReqOptPair.name
    item_type = ReqOptPair


class TestOptionalAttributes(unittest.TestCase):

    inheritance_with_optional = """
reqonly: &reqonly {req1: 99}
reqonly2: *reqonly
reqopt_from_reqonly1: {<<: *reqonly, req1: 14}
reqopt_from_reqonly2: {<<: *reqonly, opt1: howdy how}

reqopt: &reqopt {req1: 92, opt1: option1}
reqopt2: *reqopt
reqopt1_from_reqopt: {<<: *reqopt, req1: 14}
reqopt2_from_reqopt: {<<: *reqopt, opt1: howdy how}
""".strip()

    def test_inheritance_with_optional_attributes(self):
        reqopts = ReqOpts.load(TestOptionalAttributes.inheritance_with_optional)
        actual = ReqOpts.dump(reqopts).strip()
        self.assertEqual(TestOptionalAttributes.inheritance_with_optional,
                         actual)

    def test_add_optional(self):
        reqopts = ReqOpts.load(TestOptionalAttributes.inheritance_with_optional)

        reqonly2 = reqopts['reqonly2']
        self.assertEqual(None, reqonly2.opt1)
        reqonly2.opt1 = 'changed'
        actual = ReqOpts.dump(reqopts).strip()
        self.assertRegex(actual, r'reqonly2:[\{\s\r\n]+<<: \*reqonly[,\s\r\n]+opt1: changed', actual)

    def test_del_optional(self):
        reqopts = ReqOpts.load(TestOptionalAttributes.inheritance_with_optional)

        reqopt = reqopts['reqopt_from_reqonly2']
        reqopt.opt1 = None  # explicit default should still show up
        actual = ReqOpts.dump(reqopts).strip()
        self.assertRegex(actual, r'reqopt_from_reqonly2:.*<<: \*reqonly, .*null', actual)

        del reqopt.opt1  # sets to default, and remoes value
        self.assertEqual(None, reqopt.opt1)
        actual = ReqOpts.dump(reqopts).strip()
        self.assertRegex(actual, r'reqopt_from_reqonly2: \*reqonly', actual)


class Sex(aenum.Enum):
    FEMALE = aenum.auto()
    MALE = aenum.auto()


TypedSex = Typed(Sex,
        from_yaml=lambda loader, node, rtd: Sex[loader.construct_object(node)],
        to_yaml=lambda dumper, data, rtd: dumper.represent_data(str(data).replace('Sex.', '')))


class Person(Object):
    sex = Attribute(type=TypedSex)


class Sexes(Sequence):
    item_type = TypedSex


class SexedPeople(Map):
    key_type = TypedSex
    value_type = Typed(str)

class PeopleSexed(Map):
    key_type = Typed(str)
    value_type = TypedSex


class TestNonSubclass(unittest.TestCase):

    def test_nonsubclass_as_attribute(self):
        ok = Person.load('sex: MALE')
        self.assertEqual(ok.sex, Sex.MALE)
        self.assertEqual('sex: MALE', Person.dump(ok).strip())

        better = Person.load('sex: FEMALE')
        self.assertEqual(better.sex, Sex.FEMALE)
        self.assertEqual('sex: FEMALE', Person.dump(better).strip())

        with self.assertRaises(KeyError):
            Person.load('sex: female')  # wrong case

    def test_nonsubclass_as_list_item(self):
        sexes = Sexes.load('[FEMALE, MALE]')
        self.assertEqual('[FEMALE, MALE]', Sexes.dump(sexes).strip())
        self.assertEqual(2, len(sexes))
        self.assertEqual(Sex.FEMALE, sexes[0])
        self.assertEqual(Sex.MALE, sexes[1])

    def test_nonsubclass_as_list_dict_key(self):
        peeps = SexedPeople.load('FEMALE: the girl\nMALE: the boy')
        self.assertEqual('FEMALE: the girl\nMALE: the boy', SexedPeople.dump(peeps).strip())
        self.assertEqual('the girl', peeps[Sex.FEMALE])
        self.assertEqual('the boy', peeps[Sex.MALE])

    def test_nonsubclass_as_list_dict_value(self):
        peeps = PeopleSexed.load('the girl: FEMALE\nthe boy: MALE')
        self.assertEqual('the girl: FEMALE\nthe boy: MALE', PeopleSexed.dump(peeps).strip())
        self.assertEqual(Sex.FEMALE, peeps['the girl'])
        self.assertEqual(Sex.MALE, peeps['the boy'])

if __name__ == '__main__':
    unittest.main()

