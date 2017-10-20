from yamlize.yamlizingerror import YamlizingError
from yamlize.objects import Attribute
from yamlize.sequences import Sequence
from yamlize.maps import Map, KeyedList
from yamlize.yamlizable import Yamlizable, Dynamic


def yamlizable(*attributes):
    from yamlize.objects import Object, AttributeCollection
    yaml_attributes = AttributeCollection(*attributes)

    def wrapper(klass):

        class wrapped(klass, Object):
            # __doc__ must be done here to avoid AttributeError not writable
            __doc__ = klass.__doc__

            attributes = yaml_attributes

        wrapped.__name__ = klass.__name__
        wrapped.__module__ = klass.__module__

        return wrapped

    return wrapper


def yaml_map(key_type=Dynamic, value_type=Dynamic):

    def wrapper(klass):

        class wrapped(klass, Map):
            # __doc__ must be done here to avoid AttributeError not writable
            __doc__ = klass.__doc__

        wrapped.key_type = Yamlizable.get_yamlizable_type(key_type)
        wrapped.value_type = Yamlizable.get_yamlizable_type(value_type)
        wrapped.__name__ = klass.__name__
        wrapped.__module__ = klass.__module__

        return wrapped

    return wrapper


def yaml_keyed_list(key_name, item_type):

    def wrapper(klass):

        class wrapped(klass, KeyedList):
            # __doc__ must be done here to avoid AttributeError not writable
            __doc__ = klass.__doc__

        wrapped.key_name = key_name
        wrapped.item_type = Yamlizable.get_yamlizable_type(item_type)
        wrapped.__name__ = klass.__name__
        wrapped.__module__ = klass.__module__

        return wrapped

    return wrapper
