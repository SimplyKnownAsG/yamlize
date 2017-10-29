import ruamel.yaml

from collections import OrderedDict

from yamlize.yamlizable import Dynamic
from yamlize.objects import Object
from yamlize import YamlizingError


class __MapBase(Object):

    __slots__ = ('__data',)

    def __new__(cls):
        self = object.__new__(cls)
        self.__data = OrderedDict()
        return self

    def __init__(self, *args, **kwargs):
        self.__data = OrderedDict(*args, **kwargs)

    def __getattr__(self, attr_name):
        try:
            return getattr(self.__data, attr_name)
        except AttributeError:
            raise AttributeError("'{}' object has no attribute '{}'"
                                 .format(self.__class__.__name__, attr_name))

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

    def __contains__(self, index):
        return index in self.__data

    def __delitem__(self, index):
        del self.__data[index]


class Map(__MapBase):

    __slots__ = ()


class KeyedList(__MapBase):

    __slots__ = ()

    def __setitem__(self, index, value):
        if getattr(value, self.attributes.key_name) != index:
            raise KeyError("KeyedList expected key to be `{}`, but got `{}`. "
                           "Check the value\'s `{}` attribute."
                           .format(getattr(value, self.attributes.key_name),
                                   index, self.attributes.key_name))
        super(KeyedList, self).__setitem__(index, value)

    def add(self, item):
        super(KeyedList, self).__setitem__(getattr(item, self.attributes.key_name), item)

    def __iter__(self):
        return iter(self.values())

