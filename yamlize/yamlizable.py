import ruamel.yaml

from yamlize import YamlizingError
from yamlize import Attribute, ANY
from yamlize import AttributeCollection


class Yamlizable(object):

    @classmethod
    def load(cls, stream, loader=ruamel.yaml.RoundTripLoader, constructor=ruamel.yaml.RoundTripConstructor):
        # can't use ruamel.yaml.load because I need a Resolver/loader for resolving non-string types
        loader = loader(stream)
        try:
            node = loader.get_single_node()
            return cls.from_yaml(constructor(loader=loader), node)
        finally:
            loader.dispose()


class Object(Yamlizable):

    attributes = ()

    @classmethod
    def from_yaml(cls, constructor, node):
        if not isinstance(node, ruamel.yaml.MappingNode):
            raise YamlizingError('Expected a mapping node', node)

        if node in constructor.constructed_objects:
            return constructor.constructed_objects[node]

        attrs = cls.attributes.by_key
        self = cls.__new__(cls)
        constructor.constructed_objects[node] = self

        # node.value is a ordered list of keys and values
        for keyNode, valNode in node.value:
            key = constructor.construct_object(keyNode)
            attr = attrs.get(key, None)

            if attr is None:
                raise YamlizingError('Error parsing {}, found key `{}` but expected any of {}'
                                     .format(type(self), key, attrs.keys()), node)

            value = attr.from_yaml(constructor, valNode)
            setattr(self, attr.name, value)

        return self


class Sequence(Yamlizable):

    @classmethod
    def from_yaml(cls, constructor, node):
        if not isinstance(node, ruamel.yaml.SequenceNode):
            raise YamlizingError('Expected a SequenceNode', node)

        if node in constructor.constructed_objects:
            return constructor.constructed_objects[node]

        self = list()
        constructor.constructed_objects[node] = self

        # node.value list of values
        for item_node in node.value:
            if cls.item_type is not ANY:
                value = cls.item_type.from_yaml(constructor, item_node)
            else:
                value = constructor.construct_object(item_node, deep=True)

            self.append(value)

        return self

