import ruamel.yaml

from collections import OrderedDict
from yamlize.yamlizable import Yamlizable, Dynamic


class __MapBase(Yamlizable):

    __slots__ = ('__data',)

    def __init__(self, *args, **kwargs):
        self.__data = OrderedDict(*args, **kwargs)

    def __getattr__(self, attr_name):
        return getattr(self.__data, attr_name)

    def __iter__(self):
        return iter(self.__data)

    def __repr__(self):
        return repr(self.__data)

    def __str__(self):
        return str(self.__data)

    def __len__(self):
        return len(self.__data)

    def __getitem__(self, index):
        return self.__data[index]

    def __setitem__(self, index, value):
        self.__data[index] = value


class Map(__MapBase):

    __slots__ = ()

    key_type = None

    value_type = None

    @classmethod
    def from_yaml(cls, loader, node):
        if not isinstance(node, ruamel.yaml.MappingNode):
            raise YamlizingError('Expected a MappingNode', node)

        if node in loader.constructed_objects:
            return loader.constructed_objects[node]

        self = cls()
        self._set_round_trip_data(node)
        loader.constructed_objects[node] = self

        # node.value list of values
        for key_node, val_node in node.value:

            key = self.key_type.from_yaml(loader, key_node)
            val = self.value_type.from_yaml(loader, val_node)
            self[key] = val

        return self

    @classmethod
    def to_yaml(cls, dumper, self):
        if not isinstance(self, cls):
            raise YamlizingError('Expected instance of {}, got: {}'.format(cls, self))

        if self in dumper.represented_objects:
            return dumper.represented_objects[self]

        items = []
        node = ruamel.yaml.MappingNode(ruamel.yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, items)
        self._apply_round_trip_data(node)
        dumper.represented_objects[self] = node

        for key, val in self.items():
            key_node = self.key_type.to_yaml(dumper, key)
            val_node = self.value_type.to_yaml(dumper, val)
            items.append((key_node, val_node))

        return node


