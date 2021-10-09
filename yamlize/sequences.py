import ruamel.yaml

from .round_trip_data import RoundTripData
from .yamlizable import Yamlizable, Dynamic, Typed
from .yamlizing_error import YamlizingError


class Sequence(Yamlizable):

    item_type = Dynamic

    __slots__ = ('__items', '__round_trip_data')

    def __init__(self, items=()):
        Yamlizable.__init__(self)
        self.__round_trip_data = RoundTripData(None)
        self.__items = []
        self.extend(items)

    def __getstate__(self):
        return list(self.__items)

    def __setstate__(self, state):
        self.__init__(state)

    def __iter__(self):
        return iter(self.__items)

    def __repr__(self):
        return repr(self.__items)

    def __str__(self):
        return str(self.__items)

    def __len__(self):
        return len(self.__items)

    def __getitem__(self, index):
        return self.__items[index]

    def __setitem__(self, index, value):
        self.__items[index] = value

    def __delitem__(self, index):
        del self.__items[index]

    def __eq__(self, other):
        try:
            if not isinstance(other, (self.__class__, list)):
                return False

            if len(self) != len(other):
                return False

            for mine, theirs in zip(self, other):
                # only uses the == comparison
                if mine == theirs:
                    continue

                return False

            return True

        except Exception:
            return False

    def __ne__(self, other):
        try:
            if not isinstance(other, (self.__class__, list)):
                return True

            if len(self) != len(other):
                return True

            for mine, theirs in zip(self, other):
                # only uses the != comparison
                if mine != theirs:
                    return True

            return False

        except Exception:
            return True

    def __iadd__(self, other):
        self.__items += other
        return self

    def append(self, item):
        if not isinstance(item, self.item_type):
            item = self.item_type(item)

        self.__items.append(item)

    def extend(self, items):
        if not isinstance(items, (list, tuple, Sequence)):
            raise TypeError('Cannot extend items in a {} with {}'
                            .format(self.__class__, type(items)))

        for item in items:
            self.append(item)

    @classmethod
    def from_yaml(cls, loader, node, _rtd=None):
        if not isinstance(node, ruamel.yaml.SequenceNode):
            raise YamlizingError('Expected a SequenceNode', node)

        if node in loader.constructed_objects:
            return loader.constructed_objects[node]

        self = cls()
        self.__round_trip_data = RoundTripData(node)
        loader.constructed_objects[node] = self

        # node.value list of values
        for item_node in node.value:
            value = cls.item_type.from_yaml(loader, item_node, self.__round_trip_data)
            self.append(value)

        return self

    @classmethod
    def to_yaml(cls, dumper, self, _rtd=None):
        # grab the id of the item before we try anything else, that way we can
        # easily track the original id
        self_id = id(self)

        if not isinstance(self, cls):
            try:
                # this makes it possible to do IntList.dump(range(4))
                self = cls(self)
            except Exception:
                raise YamlizingError('Expected instance of {}, got: {}'.format(cls, self))

        if self_id in dumper.represented_objects:
            return dumper.represented_objects[self_id]

        items = []
        node = ruamel.yaml.SequenceNode(
            ruamel.yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG, items)
        self.__round_trip_data.apply(node)
        dumper.represented_objects[self_id] = node

        for item in self:
            item_node = self.item_type.to_yaml(dumper, item, self.__round_trip_data)
            items.append(item_node)

        return node


class FloatList(Sequence):

    item_type = Typed(float)


class IntList(Sequence):

    item_type = Typed(int)


class StrList(Sequence):

    item_type = Typed(str)


