from yamlize.yamlizingerror import YamlizingError
from yamlize.objects import Attribute
from yamlize.sequences import Sequence


def yamlizable(*attributes):
    from yamlize.objects import Object, AttributeCollection
    yaml_attributes = AttributeCollection(*attributes)

    def wrapper(klass):

        class wrapped(klass, Object):
            __doc__ = klass.__doc__ # AttributeError: __doc__ not writable on type

            attributes = yaml_attributes

        wrapped.__name__ = klass.__name__
        wrapped.__module__ = klass.__module__

        return wrapped

    return wrapper

