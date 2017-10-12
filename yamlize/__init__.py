from yamlize.yamlizingerror import YamlizingError
from yamlize.attribute import Attribute, ANY
from yamlize.attribute import AttributeCollection
from yamlize.yamlizable import Object, Sequence


def yamlizable(*attributes):
    yaml_attributes = AttributeCollection(*attributes)

    def wrapper(klass):
        from ruamel.yaml.comments import CommentedMap

        class wrapped(klass, Object):
            __doc__ = klass.__doc__ # AttributeError: __doc__ not writable on type

            attributes = yaml_attributes

        wrapped.__name__ = klass.__name__
        wrapped.__module__ = klass.__module__

        return wrapped

    return wrapper

