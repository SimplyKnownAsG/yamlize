import unittest
import pickle
import copy

import sys
import io

from yamlize import Object
from yamlize import YamlizingError
from yamlize import Attribute
from yamlize.objects import Object



class Animal(Object):

    name = Attribute()

    age = Attribute()

    def __init__(self, name, age):
        self.name = name
        self.age = age


class TypeCheck(Object):
    one = Attribute(type=int)
    array = Attribute(type=list)

    def __init__(self, one, array):
        Object.__init__(self)
        self.one = one
        self.array = array


class AnimalWithFriend(Object):
    name = Attribute(type=str)

AnimalWithFriend.friend = Attribute(name='friend',
                                    type=AnimalWithFriend,
                                    default=None)


class Test_from_yaml(unittest.TestCase):

    def test_bad_type(self):
        stream = io.StringIO('[this, is a list]')
        with self.assertRaises(YamlizingError):
            Animal.load(stream)

        stream = io.StringIO('this is a scalar')
        with self.assertRaises(YamlizingError):
            Animal.load(stream)

    def test_attrs_applied(self):
        stream = 'name: Possum\nage: 5'
        poss = Animal.load(stream)
        self.assertTrue(hasattr(poss, 'name'))
        self.assertTrue(hasattr(poss, 'age'))

    def test_missing_non_default_attributes_fail(self):
        stream = 'name: Possum'
        with self.assertRaises(YamlizingError):
            Animal.load(stream)
        self.assertEqual(None, AnimalWithFriend.load(stream).friend)

    def test_bonus_attributes_fail(self):
        stream = 'name: Possum\nage: 5\nbonus: fail'
        with self.assertRaises(YamlizingError):
            Animal.load(stream)

    def test_TypeCheck_good(self):
        stream = io.StringIO('one: 1\narray: [a, bc]')
        tc = TypeCheck.load(stream)
        self.assertEqual(1, tc.one)
        self.assertEqual('a bc'.split(), tc.array)

    def test_TypeCheck_bad(self):
        tc = TypeCheck(1, [])
        stream = io.StringIO('one: 1\narray: 99')
        with self.assertRaises(YamlizingError):
            tc = TypeCheck.load(stream)

        stream = io.StringIO('one: a\narray: []')
        with self.assertRaises(YamlizingError):
            TypeCheck.load(stream)

    def test_typeCheck_badArray(self):
        stream = io.StringIO('one: 1\narray: this gets converted to a list')
        with self.assertRaises(YamlizingError):
            TypeCheck.load(stream)

    def test_default_None_with_differing_types(self):
        class DefaultNone(Object):
            my_int = Attribute(type=int, default=None)
            my_str = Attribute(type=str, default=None)
            my_float = Attribute(type=float, default=None)
            my_bool = Attribute(type=bool, default=None)

        dn = DefaultNone()
        self.assertEqual('{}\n', DefaultNone.dump(dn))
        dn.my_int = None
        dn.my_str = None
        dn.my_float = None
        dn.my_bool = None

        # there is no guarantee of order in < Python3.6 https://www.python.org/dev/peps/pep-0520/
        actual = DefaultNone.dump(dn)
        self.assertIn('my_int:\n', actual)
        self.assertIn('my_float:\n', actual)
        self.assertIn('my_bool:\n', actual)

        # also, we can read it
        dn2 = DefaultNone.load(DefaultNone.dump(dn))
        self.assertIsNone(dn2.my_int)
        self.assertIsNone(dn2.my_str)
        self.assertIsNone(dn2.my_float)
        self.assertIsNone(dn2.my_bool)


class Test_to_yaml(unittest.TestCase):

    def test_bad_type(self):
        data = ['this', 'is a list']
        with self.assertRaises(YamlizingError):
            Animal.dump(data)

        stream = 'this is a scalar'
        with self.assertRaises(YamlizingError):
            Animal.load(stream)

    def test_writes_attrs(self):
        poss = Animal('Possum', 5)
        yaml = Animal.dump(poss)
        self.assertIn('name: Possum', yaml)
        self.assertIn('age: 5', yaml)

    def test_bonus_attributes_fail(self):
        poss = Animal('Possum', 5)
        poss.breed = 'awesome'
        yaml = Animal.dump(poss)
        self.assertNotIn('breed', yaml)
        self.assertNotIn('awesome', yaml)

    def test_TypeCheck_good(self):
        tc = TypeCheck(1, 'a bc'.split())
        yaml = TypeCheck.dump(tc)
        self.assertIn('one: 1', yaml)
        self.assertIn('array:', yaml)
        self.assertIn(' bc', yaml)

    def test_TypeCheck_bad(self):
        with self.assertRaises(YamlizingError):
            tc = TypeCheck(1, 99)

        with self.assertRaises(YamlizingError):
            tc = TypeCheck('a', [])

    def test_typeCheck_badArray(self):
        with self.assertRaises(YamlizingError):
            tc = TypeCheck(1, 'this gets converted to a list')


class Test_two_way(unittest.TestCase):

    test_yaml = ('&possum\n'
                 'name: Possum\n'
                 'friend: {name: Maggie, friend: *possum}\n'
                 )

    def test_animal_with_friend(self):
        poss = AnimalWithFriend.load(self.test_yaml)
        maggie = poss.friend
        self.assertIs(poss, maggie.friend)
        out_yaml = AnimalWithFriend.dump(poss)
        self.assertEqual(self.test_yaml, out_yaml)

    def test_pickleable(self):
        poss = AnimalWithFriend.load(self.test_yaml)
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            poss2 = pickle.loads(pickle.dumps(poss, protocol=protocol))
            out_yaml = AnimalWithFriend.dump(poss2)
            self.assertNotEqual(self.test_yaml, out_yaml)
            poss3 = AnimalWithFriend.load(out_yaml)
            self.assertEqual(poss3.name, 'Possum')
            self.assertEqual(poss3.friend.name, 'Maggie')

    def test_copy(self):
        poss = AnimalWithFriend.load(self.test_yaml)
        poss2 = copy.copy(poss)
        out_yaml = AnimalWithFriend.dump(poss2)
        self.assertNotEqual(self.test_yaml, out_yaml)
        poss3 = AnimalWithFriend.load(out_yaml)
        self.assertEqual(poss3.name, 'Possum')
        self.assertEqual(poss3.friend.name, 'Maggie')

    def test_deepcopy(self):
        poss = AnimalWithFriend.load(self.test_yaml)
        poss2 = copy.deepcopy(poss)
        out_yaml = AnimalWithFriend.dump(poss2)
        self.assertNotEqual(self.test_yaml, out_yaml)
        poss3 = AnimalWithFriend.load(out_yaml)
        self.assertEqual(poss3.name, 'Possum')
        self.assertEqual(poss3.friend.name, 'Maggie')

    def test_bool(self):
        class B(Object):
            val = Attribute(type=bool)

        self.assertTrue(B.load(B.dump(B.load('val: true'))).val)
        self.assertFalse(B.load(B.dump(B.load('val: false'))).val)


if __name__ == '__main__':
    unittest.main()

