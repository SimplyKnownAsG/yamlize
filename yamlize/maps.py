import ruamel.yaml

from collections import OrderedDict

from .objects import Object, ObjectType
from .yamlizable import Dynamic
from .yamlizing_error import YamlizingError


def _all_bases(bases):
    """returns a set of subclasses from bases tuple that would be passed in type.__init__"""
    subclasses = set()

    for base in bases:
        subclasses.add(base)
        subclasses.update(_all_bases(base.__subclasses__()))

    return subclasses


class MapType(ObjectType):

    def __init__(cls, name, bases, data):
        from yamlize.attribute_collection import (MapAttributeCollection,
                                                  KeyedListAttributeCollection)
        attributes = data.get('attributes', None)

        # the KeyedList in gloabls() hack short circuuits the below logic until Map and KeyedList
        # have been defined
        if attributes is None and 'KeyedList' in globals():
            all_bases = _all_bases(bases)
            if any(base is Map for base in all_bases):
                data['attributes'] = MapAttributeCollection()
            elif any(base is KeyedList for base in all_bases):
                data['attributes'] = KeyedListAttributeCollection()
            else:
                raise TypeError('Expected `{}` to be a yamlize.maps.Map subclass'
                                .format(name))
        return ObjectType.__init__(cls, name, bases, data)


class __MapBase(Object, metaclass=MapType):
    """
    __MapBase is a wrapper around and OrderedDict.

    Base class for other maps, provides wrapper methods to the underlying
    OrderedDict.
    """

    __slots__ = ('__data',)

    def __new__(cls, *args, **kwargs):
        """
        Explicit implementation of __new__ to assign __data as an attribute.

        :param ``*args``: sequence of key/value pairs.
        :param ``**kwargs``: kwargs for input to OrderedDict.
        """
        self = Object.__new__(cls)
        self.__data = OrderedDict()
        return self

    def __init__(self, *args, **kwargs):
        """
        Initialize a Map.

        :param ``*args``: sequence of key/value pairs.
        :param ``**kwargs``: kwargs for input to OrderedDict.
        """
        Object.__init__(self)
        self.__data = OrderedDict(*args, **kwargs)

    def __getattr__(self, attr_name):
        """
        Get attribute if it does not exist on the class already, by assuming it
        is implemented in the underlying OrderedDict.

        :param attr_name: attribute name to retrieve
        """
        try:
            return getattr(self.__data, attr_name)
        except AttributeError:
            raise AttributeError("'{}' object has no attribute '{}'"
                                 .format(self.__class__.__name__, attr_name))

    def __iter__(self):
        """Iterate over the items in the collection."""
        return iter(self.__data)

    def __repr__(self):
        """
        String representation of the collection - behaves like an OrderedDict.
        """
        return repr(self.__data).replace('OrderedDict', type(self).__name__)

    def __str__(self):
        """
        String representation of the collection - behaves like an OrderedDict.
        """
        return str(self.__data).replace('OrderedDict', type(self).__name__)

    def __len__(self):
        """Returns the number of items in the collection."""
        return len(self.__data)

    def __contains__(self, key):
        """
        Returns True if the collection contains the key, otherwise False.

        :param key: key of item in collection
        """
        return key in self.__data

    def __getitem__(self, key):
        """
        Get an item from the Map, or raise a KeyError if it is not in the
        collection.

        :param key: key of the item entry
        """
        return self.__data[key]

    def __setitem__(self, key, value):
        """
        Set an item in the collection based on the key.

        :param key: key of item
        :param value: value of the item
        """
        self.__data[key] = value

    def __delitem__(self, key):
        """
        Remove an item from the collection

        :param key: key of the item in the collection
        """
        del self.__data[key]


class Map(__MapBase):
    """
    Basic Map is an ordered dictionary of keys/values.
    """

    __slots__ = ()

    key_type = Dynamic

    value_type = Dynamic


class KeyedList(__MapBase):

    __slots__ = ()

    key_attr = None

    key_type = Dynamic

    def __setitem__(self, key, value):
        if self.__class__.key_attr.get_value(value) != key:
            raise KeyError("KeyedList expected key to be `{}`, but got `{}`. "
                           "Check the value\'s `{}` attribute."
                           .format(self.__class__.key_attr.get_value(value),
                                   key, self.__class__.key_attr))
        super(KeyedList, self).__setitem__(key, value)

    def add(self, item):
        self[self.__class__.key_attr.get_value(item)] = item

    def __iter__(self):
        return iter(self.values())

