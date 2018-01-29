import unittest
import pickle
import copy

import sys
import six

from yamlize import Attribute, StrList, Sequence, yamlizable, yaml_list


class Test_Sequence_list_methods(unittest.TestCase):

    def test_eq(self):
        s_list = 'a bc def ghij'.split()
        s_seq = Sequence(s_list)
        self.assertEqual(s_seq, s_list)
        self.assertEqual(s_list, s_seq)

        # test with string list
        str_seq = StrList.load(Sequence.dump(s_seq))
        self.assertEqual(str_seq, s_list)
        self.assertEqual(s_list, str_seq)

        # test not equal
        s_list[0] = ord('a')
        self.assertFalse(s_seq == s_list)  # use assertFalse and == to force __eq__ usage
        self.assertFalse(s_list == s_seq)

    def test_ne(self):
        s_list = 'a bc def ghij'.split()
        s_seq = Sequence(s_list)
        s_list[1] = 'BC'
        self.assertNotEqual(s_seq, s_list)
        self.assertNotEqual(s_list, s_seq)

        # test with string list
        str_seq = StrList.load(Sequence.dump(s_seq))
        self.assertNotEqual(str_seq, s_list)
        self.assertNotEqual(s_list, str_seq)

        # test equal
        s_seq[1] = 'BC'
        self.assertFalse(s_seq != s_list)  # use assertFalse and == to force __eq__ usage
        self.assertFalse(s_list != s_seq)

@yamlizable(Attribute(name='name', type=str))
class AnimalWithFriends(object):
    pass

@yaml_list(item_type=AnimalWithFriends)
class AnimalSequence(object):
    pass

AnimalWithFriends.attributes.add(Attribute(name='friends',
                                           type=AnimalSequence,
                                           default=None))


class Test_two_way(unittest.TestCase):

    test_yaml = ('# no friends :(\n'
                 '- name: Lucy # no friends\n'
                 '- &luna\n'
                 '  name: Luna\n'
                 '  friends:\n'
                 '  - &possum\n'
                 '    name: Possum\n'
                 '    friends: [*luna]\n'
                 '- *possum\n'
                 )

    def test_sequence(self):
        animals = AnimalSequence.load(self.test_yaml)

        self.assertTrue(all(isinstance(a, AnimalWithFriends) for a in animals))
        self.assertEqual(animals[1], animals[2].friends[0])
        self.assertEqual(animals[2], animals[1].friends[0])

        out_stream = AnimalSequence.dump(animals)
        self.assertEqual(self.test_yaml, out_stream)

    def test_pickleable(self):
        animals = AnimalSequence.load(self.test_yaml)
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            a2 = pickle.loads(pickle.dumps(animals, protocol=protocol))
            self.assertEqual(a2[1].friends[0].name, 'Possum')

    def test_copy(self):
        animals = AnimalSequence.load(self.test_yaml)
        a2 = copy.copy(animals)
        self.assertEqual(a2[1].friends[0].name, 'Possum')

    def test_deepcopy(self):
        animals = AnimalSequence.load(self.test_yaml)
        a2 = copy.deepcopy(animals)
        self.assertEqual(a2[1].friends[0].name, 'Possum')


if __name__ == '__main__':
    unittest.main()

