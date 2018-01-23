import sys

from .attributes import Attribute
from .sequences import Sequence
from .yamlizable import Dynamic
from .yamlizing_error import YamlizingError


def yamlizable(*attributes):
    from .attribute_collection import AttributeCollection
    from .objects import Object
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
    from .attribute_collection import AttributeAndMapItemCollection
    from .yamlizable import Yamlizable
    from .maps import Map

    yaml_attributes = AttributeAndMapItemCollection(
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
    from .attribute_collection import KeyedListItemCollection
    from .yamlizable import Yamlizable
    from .maps import KeyedList

    yaml_attributes = KeyedListItemCollection(
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
    from .yamlizable import Yamlizable

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


