import sys

from .attributes import Attribute, MapItem, KeyedListItem
from .attribute_collection import (AttributeCollection, MapAttributeCollection,
                                   KeyedListAttributeCollection)
from .maps import Map, KeyedList
from .objects import Object
from .sequences import Sequence
from .yamlizable import Dynamic, Yamlizable
from .yamlizing_error import YamlizingError


def yamlizable(*attributes):
    yaml_attributes = AttributeCollection(*attributes)

    def wrapper(klass):  # pylint: disable=missing-docstring
        wrapped = klass.__class__(klass.__name__, (klass, Object), {'attributes': yaml_attributes})
        wrapped.__module__ = klass.__module__
        setattr(sys.modules[wrapped.__module__], klass.__name__, wrapped)

        for t in wrapped.__bases__:
            if issubclass(t, Object):
                for attr in t.attributes:
                    wrapped.attributes.add(attr)

        return wrapped

    return wrapper


yaml_object = yamlizable
"""
A more logical, less fun, alias for `yamlizable`.
"""


def yaml_map(key_type, value_type, *attributes):
    yaml_attributes = MapAttributeCollection(
        Yamlizable.get_yamlizable_type(key_type),
        Yamlizable.get_yamlizable_type(value_type),
        *attributes
    )

    def wrapper(klass):  # pylint: disable=missing-docstring
        wrapped = klass.__class__(klass.__name__, (klass, Map), {'attributes': yaml_attributes})
        wrapped.__module__ = klass.__module__
        setattr(sys.modules[wrapped.__module__], klass.__name__, wrapped)
        return wrapped

    return wrapper


def yaml_keyed_list(key_name, item_type, *attributes):
    yaml_attributes = KeyedListAttributeCollection(
        key_name,
        Yamlizable.get_yamlizable_type(item_type),
        *attributes
    )

    def wrapper(klass):  # pylint: disable=missing-docstring
        wrapped = klass.__class__(klass.__name__, (klass, KeyedList),
                                  {'attributes': yaml_attributes})
        wrapped.__module__ = klass.__module__
        setattr(sys.modules[wrapped.__module__], klass.__name__, wrapped)
        return wrapped

    return wrapper


def yaml_list(item_type):
    def wrapper(klass):  # pylint: disable=missing-docstring
        wrapped = klass.__class__(klass.__name__, (klass, Sequence),
                                  {'item_type': Yamlizable.get_yamlizable_type(item_type)})
        wrapped.__module__ = klass.__module__
        setattr(sys.modules[wrapped.__module__], klass.__name__, wrapped)
        return wrapped

    return wrapper


@yaml_list(str)
class StrList(object):
    pass


@yaml_list(float)
class FloatList(object):
    pass


@yaml_list(int)
class IntList(object):
    pass


