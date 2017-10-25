from yamlize.yamlizing_error import YamlizingError
from yamlize.attributes import Attribute
from yamlize.yamlizable import Dynamic


def yamlizable(*attributes):
    from yamlize.attribute_collection import AttributeCollection
    from yamlize.objects import Object
    yaml_attributes = AttributeCollection(*attributes)

    def wrapper(klass):

        class wrapped(klass, Object):
            # __doc__ must be done here to avoid AttributeError not writable
            __doc__ = klass.__doc__

        wrapped.attributes = yaml_attributes
        wrapped.__name__ = klass.__name__
        wrapped.__module__ = klass.__module__

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
    from yamlize.attribute_collection import AttributeAndMapItemCollection
    from yamlize.yamlizable import Yamlizable
    from yamlize.maps import Map

    yaml_attributes = AttributeAndMapItemCollection(
        Yamlizable.get_yamlizable_type(key_type),
        Yamlizable.get_yamlizable_type(value_type),
        *attributes
    )

    def wrapper(klass):

        class wrapped(klass, Map):

            # __doc__ must be done here to avoid AttributeError not writable
            __doc__ = klass.__doc__

        wrapped.attributes = yaml_attributes
        wrapped.__name__ = klass.__name__
        wrapped.__module__ = klass.__module__

        return wrapped

    return wrapper


def yaml_keyed_list(key_name, item_type, *attributes):
    from yamlize.attribute_collection import KeyedListItemCollection
    from yamlize.yamlizable import Yamlizable
    from yamlize.maps import KeyedList

    yaml_attributes = KeyedListItemCollection(
        key_name,
        Yamlizable.get_yamlizable_type(item_type),
        *attributes
    )

    def wrapper(klass):

        class wrapped(klass, KeyedList):
            # __doc__ must be done here to avoid AttributeError not writable
            __doc__ = klass.__doc__

        wrapped.attributes = yaml_attributes
        wrapped.__name__ = klass.__name__
        wrapped.__module__ = klass.__module__

        return wrapped

    return wrapper


def yaml_list(item_type):
    from yamlize.yamlizable import Yamlizable
    from yamlize.sequences import Sequence

    def wrapper(klass):

        class wrapped(klass, Sequence):
            # __doc__ must be done here to avoid AttributeError not writable
            __doc__ = klass.__doc__

        wrapped.item_type = Yamlizable.get_yamlizable_type(item_type)
        wrapped.__name__ = klass.__name__
        wrapped.__module__ = klass.__module__

        return wrapped

    return wrapper

