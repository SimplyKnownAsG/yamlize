import unittest
import pickle
import copy

import sys

from yamlize import Attribute, IntList, StrList, Sequence, Object, YamlizingError


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

    def test_anchor(self):
        class ListLists(Sequence):

            item_type = IntList

        ll = ListLists.load(u'[ &list_1 [0, 1, 2], *list_1 ]')
        self.assertEqual(id(ll[0]), id(ll[1]))
        ll[0].append(4)

        self.assertEqual(u'[&list_1 [0, 1, 2, 4], *list_1]',
                         ListLists.dump(ll).strip())

        ll2 = ListLists()
        content = list(range(4,6))
        ll2 += [content]
        ll2 += [content]
        self.assertEqual(content, ll2[0])

        self.assertEqual(u'- &id001\n  - 4\n  - 5\n- *id001',
                         ListLists.dump(ll2).strip())

    def test_attribute_assignment(self):
        class ClassWithLists(Object):
            ints = Attribute(type=IntList)
            strs = Attribute(type=StrList)

        cwl = ClassWithLists()

        with self.assertRaises(YamlizingError):
            cwl.ints = 123

        cwl.ints = [1, 2, 3]

        with self.assertRaises(YamlizingError):
            cwl.strs = 'abc'

        cwl.strs = 'abc'.split()
        ClassWithLists.dump(cwl)

    def test_attribute_default(self):
        class ClassWithLists(Object):
            ints = Attribute(type=IntList, default=None)

        cwl = ClassWithLists()
        self.assertEqual('{}\n', ClassWithLists.dump(cwl))
        cwl.ints = None
        self.assertEqual('ints:\n', ClassWithLists.dump(cwl))
        del cwl.ints
        self.assertEqual('{}\n', ClassWithLists.dump(cwl))


class AnimalWithFriends(Object):

    name = Attribute(type=str)


class AnimalSequence(Sequence):

    item_type = AnimalWithFriends


AnimalWithFriends.friends = Attribute(name='friends',
                                      type=AnimalSequence,
                                      default=None)


class Test_two_way(unittest.TestCase):

    def test_IntList(self):
        self.assertEqual([1, 2, 3], IntList.load(IntList.dump([1, 2, 3])))
        il = IntList((1, 2, 3))
        self.assertEqual([1, 2, 3], il)
        with self.assertRaises(TypeError):
            IntList(123)

    def test_StrList(self):
        abc = 'a b c'.split()
        self.assertEqual(abc, StrList.load(StrList.dump(abc)))
        self.assertEqual(3, len(abc))
        with self.assertRaises(TypeError):
            StrList('a b c')

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

