import ruamel.yaml
import six
import inspect

from yamlize import YamlizingError
from yamlize import Attribute, ANY
from yamlize import AttributeCollection


class AnchorNode(object):

    __slots__ = ('value', )

    def __init__(self, value):
        self.value = value


class Yamlizable(object):

    __round_trip_data = None

    __type = None

    __types = dict()

    @classmethod
    def get_yamlizable(cls, type_):
        from yamlize.attribute import ANY

        if inspect.isclass(type_) and issubclass(type_, Yamlizable) or type_ is ANY:
            return type_
        elif type not in cls.__types:
            # attrs = {'load': Yamlizable.load, 'dump': Yamlizable.dump,
            cls.__types[type_] = type('Yamlizable' + type_.__name__, (type_, Yamlizable), {})
            cls.__types[type_].__type = type_

        return cls.__types[type_]

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

    def _set_round_trip_data(self, node):
        self.__round_trip_data = {}

        for key in dir(node):
            if key.startswith('__') or key in {'value', 'id'}:
                continue

            attr = getattr(node, key)

            if callable(attr):
                continue

            self.__round_trip_data[key] = attr

    def _apply_round_trip_data(self, node):
        if self.__round_trip_data is None:
            return

        for key, val in self.__round_trip_data.items():
            if key == 'anchor':
                val = AnchorNode(val)
            setattr(node, key, val)

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_object(node, deep=True)

        try:
            value = cls(data) # to to coerce to correct type
        except:
            raise YamlizingError('Failed to coerce data `{}` to type `{}`'
                                 .format(data, cls))

        value._set_round_trip_data(node)
        return value

    @classmethod
    def to_yaml(cls, dumper, self):
        node = dumper.yaml_representers[self.__type](dumper, self)
        # node = dumper.represent_data(self)
        self._apply_round_trip_data(node)
        return node


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
        self._set_round_trip_data(node)
        self._attribute_order = []
        loader.constructed_objects[node] = self

        # node.value is a ordered list of keys and values
        for key_node, val_node in node.value:
            key = loader.construct_object(key_node)
            attribute = attrs.get(key, None)

            if attribute is None:
                raise YamlizingError('Error parsing {}, found key `{}` but expected any of {}'
                                     .format(type(self), key, attrs.keys()), node)

            value = attribute.from_yaml(loader, val_node)
            self._attribute_order.append(key)
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
        self._apply_round_trip_data(node)
        dumper.represented_objects[self] = node

        attribute_order = getattr(self, '_attribute_order', [])
        attribute_order += sorted(set(cls.attributes.by_name.keys()) - set(attribute_order))

        for attr_name in attribute_order:
            attribute = cls.attributes.by_name[attr_name]
            attr_value = getattr(self, attr_name, attribute.default)
            val_node = attribute.to_yaml(dumper, attr_value)

            # short circuit when the value is the default
            if val_node is None:
                continue

            key_node = dumper.represent_data(attribute.key)

            items.append((key_node, val_node))

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
        self._set_round_trip_data(node)
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
        self._apply_round_trip_data(node)
        dumper.represented_objects[self] = node

        for item in self:
            if cls.item_type is not ANY:
                item_node = cls.item_type.to_yaml(dumper, item)
            else:
                item_node = dumper.represent_data(item)
            items.append(item_node)

        return node

