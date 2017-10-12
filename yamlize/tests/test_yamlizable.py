
import unittest

import six

from yamlize import yamlizable
from yamlize import YamlizingError
from yamlize import Attribute
from yamlize import Sequence

# TODO: write default if default, or no? what about writing a comment indicating it is default?

@yamlizable(Attribute(name='name'),
            Attribute(name='age'))
class Animal(object):
    pass


@yamlizable(Attribute(name='one', type=int),
            Attribute(name='array', type=list))
class TypeCheck(object):
    pass


@yamlizable(Attribute(name='name', type=str))
class AnimalWithFriend(object):
    pass
AnimalWithFriend.attributes.add(Attribute(name='friend', type=AnimalWithFriend, default=None))

class TestDeserialization(unittest.TestCase):

    def test_bad_type(self):
        stream = six.StringIO('[this, is a list]')
        with self.assertRaises(YamlizingError):
            Animal.load(stream)

        stream = six.StringIO('this is a scalar')
        with self.assertRaises(YamlizingError):
            Animal.load(stream)

    def test_attrsApplied(self):
        stream = six.StringIO('name: Possum\nage: 5')
        poss = Animal.load(stream)
        self.assertTrue(hasattr(poss, 'name'))
        self.assertTrue(hasattr(poss, 'age'))

    def test_bonus_attributes_fail(self):
        stream = six.StringIO('name: Possum\nage: 5\nbonus: fail')
        with self.assertRaises(YamlizingError):
            Animal.load(stream)

    def test_TypeCheck_good(self):
        stream = six.StringIO('one: 1\narray: [a, bc]')
        tc = TypeCheck.load(stream)
        self.assertEqual(1, tc.one)
        self.assertEqual('a bc'.split(), tc.array)

    def test_TypeCheck_bad(self):
        stream = six.StringIO('one: 1\narray: 99')
        with self.assertRaises(YamlizingError):
            tc = TypeCheck.load(stream)

        stream = six.StringIO('one: a\narray: []')
        with self.assertRaises(YamlizingError):
            TypeCheck.load(stream)

    @unittest.skip('TODO: type check list')
    def test_typeCheck_badArray(self):
        stream = six.StringIO('one: 1\narray: this gets converted to a list')
        with self.assertRaises(YamlizingError):
            TypeCheck.load(stream)

    def test_animal_with_friend(self):
        stream = six.StringIO('&possum\n'
                              'name: Possum\n'
                              'friend:\n'
                              '    name: Maggie\n'
                              '    friend: *possum\n'
                              )
        poss = AnimalWithFriend.load(stream)
        maggie = poss.friend
        self.assertIs(poss, maggie.friend)

    def test_list_animals_with_friends(self):

        @yamlizable(Attribute(name='name', type=str))
        class AnimalWithFriends(object):
            pass

        class AnimalSequence(Sequence):
            item_type = AnimalWithFriends

        AnimalWithFriends.attributes.add(Attribute(name='friends', type=AnimalSequence, default=None))

        stream = six.StringIO('- name: Lucy # no friends\n'
                              '- &luna\n'
                              '  name: Luna\n'
                              '  friends:\n'
                              '  - &possum\n'
                              '    name: Possum\n'
                              '    friends: [*luna]\n'
                              '- *possum\n'
                              )
        animals = AnimalSequence.load(stream)

        # import ruamel.yaml, sys
        # ruamel.yaml.dump(animals, sys.__stdout__, Dumper=ruamel.yaml.RoundTripDumper)

# class TestSerialization(unittest.TestCase):

#     def test_badRoot(self):
#         stream = six.StringIO('[this, is a list]')
#         with self.assertRaises(YamlizingError):
#             Animal.load(stream)

#         stream = six.StringIO('this is a scalar')
#         with self.assertRaises(YamlizingError):
#             Animal.load(stream)

#     def test_attrsApplied(self):
#         stream = six.StringIO('name: Possum\nage: 5')
#         poss = Animal.load(stream)
#         self.assertTrue(hasattr(poss, 'name'))
#         self.assertTrue(hasattr(poss, 'age'))

#     def test_bonusAttributesFail(self):
#         stream = six.StringIO('name: Possum\nage: 5\nbonus: fail')
#         with self.assertRaises(YamlizingError):
#             Animal.load(stream)


if __name__ == '__main__':
    unittest.main()


