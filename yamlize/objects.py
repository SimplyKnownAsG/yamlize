import inspect

import ruamel.yaml

from yamlize.yamlizable import Yamlizable, Dynamic
from yamlize import YamlizingError


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

    @classmethod
    def from_yaml_key_val(cls, loader, key_node, val_node, key_name):
        if val_node in loader.constructed_objects:
            return loader.constructed_objects[val_node]

        attrs = cls.attributes.by_key
        self = cls.__new__(cls)
        self._attribute_order = []
        loader.constructed_objects[val_node] = self

        key_attribute = cls.attributes.by_name.get(key_name, None)

        if key_attribute is None:
            raise YamlizingError('Error parsing {}, there is no attribute named `{}`'
                                 .format(type(self), key_name), key_node)

        setattr(self, key_name, key_attribute.from_yaml(loader, key_node))

        # node.value is a ordered list of keys and values
        for k_node, v_node in val_node.value:
            key = loader.construct_object(k_node)
            attribute = attrs.get(key, None)

            if attribute is None:
                raise YamlizingError('Error parsing {}, found key `{}` but expected any of {}'
                                     .format(type(self), key, attrs.keys()), node)

            value = attribute.from_yaml(loader, v_node)
            self._attribute_order.append(key)
            setattr(self, attribute.name, value)

        return self

    @classmethod
    def to_yaml_key_val(cls, dumper, self):
        if val_node in dumper.represented_objects:
            return dumper.represented_objects[val_node]

        attrs = cls.attributes.by_name
        items = []
        node = ruamel.yaml.MappingNode(ruamel.yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, items)
        self._apply_round_trip_data(node)
        loader.represnted_objects[self] = self

        key_attribute = cls.attributes.by_name.get(key_name, None)

        if key_attribute is None:
            raise YamlizingError('Error parsing {}, there is no attribute named `{}`'
                                 .format(type(self), key_name), key_node)

        setattr(self, key_name, key_attribute.from_yaml(loader, key_node))

        # node.value is a ordered list of keys and values
        for attr_name in attribute_order:
            key = loader.construct_object(k_node)
            attribute = attrs.get(key, None)

            if attribute is None:
                raise YamlizingError('Error parsing {}, found key `{}` but expected any of {}'
                                     .format(type(self), key, attrs.keys()), node)

            value = attribute.from_yaml(loader, v_node)
            self._attribute_order.append(key)
            setattr(self, attribute.name, value)

        return self

    @classmethod
    def to_yaml_key_val(cls, dumper, self, key_name):
        if not isinstance(self, cls):
            raise YamlizingError('Expected instance of {}, got: {}'.format(cls, self))

        if self in dumper.represented_objects:
            return dumper.represented_objects[self]

        attrs = cls.attributes.by_name
        items = []
        node = ruamel.yaml.MappingNode(ruamel.yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, items)
        self._apply_round_trip_data(node)
        dumper.represented_objects[self] = node

        attribute_order = getattr(self, '_attribute_order', [])
        attribute_order += sorted(set(cls.attributes.by_name.keys()) - set(attribute_order))
        list_key_node = None

        for attr_name in attribute_order:
            attribute = cls.attributes.by_name[attr_name]
            attr_value = getattr(self, attr_name, attribute.default)
            val_node = attribute.to_yaml(dumper, attr_value)

            # short circuit when the value is the default
            if val_node is None:
                continue

            # this is the "index" node, so it shouldn't be in the object dict
            if attr_name == key_name:
                list_key_node = val_node
                continue

            key_node = dumper.represent_data(attribute.key)

            items.append((key_node, val_node))

        return list_key_node, node



class NODEFAULT:

    def __init__(self):
        raise NotImplementedError


class Attribute(object):
    """
    Represents an attribute of a Python class, and a key/value pair in YAML.

    Attributes
    ----------
    name : str
        name of the attribute within the Python class
    key : str
        name of the attribute within the YAML representation
    type : type or ANY
        type of the attribute within the Python class. When ``ANY``, the type is
        a pass-through and whatever YAML determines it should be will be applied.
    default : value or NODEFAULT
        default value if not supplied in YAML. If ``default=NODEFAULT``, then
        the attribute must be supplied.
    """

    __slots__ = ('name', 'key', 'type', 'default')

    def __init__(self, name, key=None, type=NODEFAULT, default=NODEFAULT):
        self.name = name
        self.key = key or name
        self.type = Yamlizable.get_yamlizable_type(type) if type != NODEFAULT else Dynamic
        self.default = default

    def from_yaml(self, loader, node):
        if inspect.isclass(self.type) and issubclass(self.type, Yamlizable):
            return self.type.from_yaml(loader, node)

        value = loader.construct_object(node, deep=True)

        if self.type is ANY or isinstance(value, self.type):
            return value
        else:
            try:
                return self.type(value)
            except:
                raise YamlizingError('Failed to coerce value `{}` to type `{}`'
                                     .format(value, self.type), node)

    def to_yaml(self, dumper, data):
        if data == self.default and data is not NODEFAULT:
            # short circuit, don't write out default data
            return

        # if not isinstance(data, self.type):
        #     try:
        #         data = self.type(data)
        #     except:
        #         raise YamlizingError('Failed to coerce value `{}` to type `{}`'
        #                              .format(data, self.type))

        return self.type.to_yaml(dumper, data)


class AttributeCollection(object):

    __slots__ = ('by_key', 'by_name')

    def __init__(self, *args, **kwargs):
        self.by_key = dict()
        self.by_name = dict()
        for item in args:
            if not isinstance(item, Attribute):
                raise TypeError('Incorrect type {} while initializing AttributeCollection with {}'
                                .format(type(item), item))
            self.add(item)

    def add(self, attr):
        if attr.key in self.by_key:
            raise KeyError('AttributeCollection already contains an entry for {}, previously defined: {}'
                           .format(attr.key, self.by_key[attr.key]))

        if attr.name in self.by_name:
            raise KeyError('AttributeCollection already contains an entry for {}, previously defined: {}'
                           .format(attr.name, self.by_name[attr.name]))

        self.by_key[attr.key] = attr
        self.by_name[attr.name] = attr


