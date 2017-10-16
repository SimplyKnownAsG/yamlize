import ruamel.yaml
import six

from yamlize import YamlizingError
from yamlize import Attribute, ANY
from yamlize import AttributeCollection


class AnchorNode(object):
    __slots__ = ('value', )
    def __init__(self, value):
        self.value = value


class Yamlizable(object):

    @classmethod
    def load(cls, stream, Loader=ruamel.yaml.RoundTripLoader):
        # can't use ruamel.yaml.load because I need a Resolver/loader for resolving non-string types
        loader = Loader(stream)
        try:
            node = loader.get_single_node()
            return cls.from_yaml(loader, node)
        finally:
            loader.dispose()

    @classmethod
    def dump(cls, data, stream=None, Dumper=ruamel.yaml.RoundTripDumper):
        # can't use ruamel.yaml.load because I need a Resolver/loader for resolving non-string types
        convert_to_string = stream is None
        stream = stream or six.StringIO()
        dumper = Dumper(stream)

        try:
            dumper._serializer.open()
            root_node = cls.to_yaml(dumper, data)
            dumper.serialize(root_node)
            dumper._serializer.close()
        finally:
            try:
                dumper._emitter.dispose()
            except AttributeError:
                raise
                dumper.dispose()  # cyaml

        if convert_to_string:
            return stream.getvalue()

        return None


def _get_round_trip_data(node):
    round_trip_data = {}

    for key in dir(node):
        if key.startswith('__') or key in {'value', 'id'}:
            continue

        attr = getattr(node, key)

        if callable(attr):
            continue

        round_trip_data[key] = attr

    return round_trip_data


def _apply_round_trip_data(obj, node):
    round_trip_data = getattr(obj, '_round_trip_data', None)

    if round_trip_data is not None:
        for key, val in round_trip_data.items():
            if key == 'anchor':
                val = AnchorNode(val)
            setattr(node, key, val)


class Object(Yamlizable):

    attributes = ()

    @classmethod
    def from_yaml(cls, loader, node):
        if not isinstance(node, ruamel.yaml.MappingNode):
            raise YamlizingError('Expected a mapping node', node)

        if node in loader.constructed_objects:
            return loader.constructed_objects[node]

        attrs = cls.attributes.by_key
        self = cls.__new__(cls)
        self._round_trip_data = _get_round_trip_data(node)
        loader.constructed_objects[node] = self

        # node.value is a ordered list of keys and values
        for key_node, val_node in node.value:
            key = loader.construct_object(key_node)
            attribute = attrs.get(key, None)

            if attribute is None:
                raise YamlizingError('Error parsing {}, found key `{}` but expected any of {}'
                                     .format(type(self), key, attrs.keys()), node)
            value = attribute.from_yaml(loader, val_node)
            setattr(self, attribute.name, value)

        return self

    @classmethod
    def to_yaml(cls, dumper, self):
        if not isinstance(self, cls):
            raise YamlizingError('Expected instance of {}, got: {}'.format(cls, self))

        if self in dumper.represented_objects:
            return dumper.represented_objects[self]

        attrs = cls.attributes.by_name
        # self.__round_trip_data = _get_round_trip_data(node)
        # items is a ordered list of keys and values
        items = []
        node = ruamel.yaml.MappingNode(ruamel.yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, items)
        _apply_round_trip_data(self, node)
        dumper.represented_objects[self] = node

        for attr_name, attribute in cls.attributes.by_name.items():
            attr_value = getattr(self, attr_name, attribute.default)
            value_node = attribute.to_yaml(dumper, attr_value)

            # short circuit when the value is the default
            if value_node is None:
                continue

            key_node = dumper.represent_data(attr_name)
            items.append((key_node, value_node))

        return node


class Sequence(Yamlizable):

    __slots__ = ('__items',)

    def __init__(self, *items):
        self.__items = items or []

    def __getattr__(self, attr_name):
        return getattr(self.__items, attr_name)

    def __iter__(self):
        return iter(self.__items)

    def __repr__(self):
        return repr(self.__items)

    def __str__(self):
        return str(self.__items)

    def __len__(self):
        return len(self.__items)

    def __getitem__(self, index):
        return self.__items[index]

    @classmethod
    def from_yaml(cls, loader, node):
        if not isinstance(node, ruamel.yaml.SequenceNode):
            raise YamlizingError('Expected a SequenceNode', node)

        if node in loader.constructed_objects:
            return loader.constructed_objects[node]

        self = cls()
        self._round_trip_data = _get_round_trip_data(node)
        loader.constructed_objects[node] = self

        # node.value list of values
        for item_node in node.value:
            if cls.item_type is not ANY:
                value = cls.item_type.from_yaml(loader, item_node)
            else:
                value = loader.construct_object(item_node, deep=True)

            self.append(value)

        return self

    @classmethod
    def to_yaml(cls, dumper, self):
        if not isinstance(self, cls):
            raise YamlizingError('Expected instance of {}, got: {}'.format(cls, self))

        if self in dumper.represented_objects:
            return dumper.represented_objects[self]

        items = []
        node = ruamel.yaml.SequenceNode(ruamel.yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG, items)
        _apply_round_trip_data(self, node)
        dumper.represented_objects[self] = node

        for item in self:
            if cls.item_type is not ANY:
                item_node = cls.item_type.to_yaml(dumper, item)
            else:
                item_node = dumper.represent_data(item)
            items.append(item_node)

        return node

