import unittest
import pickle

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


class Test_two_way(unittest.TestCase):

    def test_sequence(self):

        @yamlizable(Attribute(name='name', type=str))
        class AnimalWithFriends(object):
            pass

        @yaml_list(item_type=AnimalWithFriends)
        class AnimalSequence(object):
            pass

        AnimalWithFriends.attributes.add(Attribute(name='friends',
                                                   type=AnimalSequence,
                                                   default=None))

        in_stream = six.StringIO('# no friends :(\n'
                                 '- name: Lucy # no friends\n'
                                 '- &luna\n'
                                 '  name: Luna\n'
                                 '  friends:\n'
                                 '  - &possum\n'
                                 '    name: Possum\n'
                                 '    friends: [*luna]\n'
                                 '- *possum\n'
                                 )
        animals = AnimalSequence.load(in_stream)

        self.assertTrue(all(isinstance(a, AnimalWithFriends) for a in animals))
        self.assertEqual(animals[1], animals[2].friends[0])
        self.assertEqual(animals[2], animals[1].friends[0])

        out_stream = six.StringIO()
        AnimalSequence.dump(animals, out_stream)
        self.assertEqual(in_stream.getvalue(), out_stream.getvalue())


if __name__ == '__main__':
    unittest.main()

