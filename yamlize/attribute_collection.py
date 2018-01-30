
from yamlize.attributes import Attribute, MapItem, KeyedListItem
from yamlize.yamlizing_error import YamlizingError


class AttributeCollection(object):

    __slots__ = ('order', 'by_key', 'by_name')

    def __init__(self, *args, **kwargs):
        # let's assume the order things were defined is the order we want to
        # display them, still public if someone wants to muck
        self.order = list()
        self.by_key = dict()
        self.by_name = dict()

        for item in args:
            if not isinstance(item, Attribute):
                raise TypeError('Incorrect type {} while initializing '
                                'AttributeCollection with {}'
                                .format(type(item), item))
            self.add(item)

    def __iter__(self):
        return iter(self.order)

    @property
    def required(self):
        return {attr for attr in self if attr.is_required}

    def add(self, attr):
        if attr.key in self.by_key:
            raise KeyError('AttributeCollection already contains an entry for '
                           '{}, previously defined: {}'
                           .format(attr.key, self.by_key[attr.key]))

        if attr.name in self.by_name:
            raise KeyError('AttributeCollection already contains an entry for '
                           '{}, previously defined: {}'
                           .format(attr.name, self.by_name[attr.name]))

        self.by_key[attr.key] = attr
        self.by_name[attr.name] = attr
        self.order.append(attr)

    def from_yaml(self, obj, loader, key_node, val_node, round_trip_data):
        """
        returns: Attribute that was applied
        """
        key = loader.construct_object(key_node)
        attribute = self.by_key.get(key, None)

        if attribute is None:
            raise YamlizingError('Error parsing {}, found key `{}` but '
                                 'expected any of {}'
                                 .format(type(obj), key, self.by_key.keys()),
                                 key_node)

        attribute.from_yaml(obj, loader, val_node, round_trip_data)

        return attribute

    def yaml_attribute_order(self, obj, attr_order):
        """
        returns: Attribute that was applied
        """
        new_attrs = []
        for attr in self:
            if attr not in attr_order:
                new_attrs.append(attr)

        return attr_order + new_attrs

    def attr_dump_order(self, obj, attr_order):
        """
        returns: Attribute that was applied
        """
        new_attrs = []

        for attr in self:
            if attr.has_default and attr.get_value(obj) == attr.default:
                if attr in attr_order:
                    attr_order.remove(attr)
                continue

            if attr not in attr_order:
                new_attrs.append(attr)

        return attr_order + new_attrs


class MapAttributeCollection(AttributeCollection):

    __slots__ = ('key_type', 'value_type')

    def __init__(self, key_type, value_type, *args, **kwargs):
        AttributeCollection.__init__(self, *args, **kwargs)

        self.key_type = key_type
        self.value_type = value_type

    def from_yaml(self, obj, loader, key_node, val_node, round_trip_data):
        """
        returns: Attribute that was applied, or None.

        Raises an exception if there was actually a problem.
        """
        key = loader.construct_object(key_node)
        attribute = self.by_key.get(key, None)

        if attribute is not None:
            attribute.from_yaml(obj, loader, val_node, round_trip_data)
        else:
            # the key_node will point to our object
            del loader.constructed_objects[key_node]
            key = self.key_type.from_yaml(loader, key_node, round_trip_data)
            val = self.value_type.from_yaml(loader, val_node, round_trip_data)
            try:
                obj.__setitem__(key, val)
            except Exception as ee:
                raise YamlizingError(
                    'Failed to add key `{}` with value `{}`, got: {}'
                    .format(key, val, ee), key_node)

        return attribute  # could be None, and that is fine

    def yaml_attribute_order(self, obj, attr_order):
        """
        returns: Attribute that was applied
        """
        attr_order = AttributeCollection.yaml_attribute_order(self, obj,
                                                              attr_order)

        for item_key in obj.keys():
            attr_order.append(
                MapItem(item_key, self.key_type, self.value_type)
            )

        return attr_order

    def attr_dump_order(self, obj, attr_order):
        """
        returns: Attribute that was applied
        """
        attr_order = AttributeCollection.attr_dump_order(self, obj,
                                                         attr_order)

        for item_key in obj.keys():
            attr_order.append(
                MapItem(item_key, self.key_type, self.value_type)
            )

        return attr_order


class KeyedListAttributeCollection(AttributeCollection):

    __slots__ = ('key_name', 'item_type')

    def __init__(self, key_name, item_type, *args, **kwargs):
        AttributeCollection.__init__(self, *args, **kwargs)

        self.key_name = key_name
        self.item_type = item_type

    def from_yaml(self, obj, loader, key_node, val_node, round_trip_data):
        """
        returns: Attribute that was applied, or None.

        Raises an exception if there was actually a problem.
        """
        key = loader.construct_object(key_node)
        attribute = self.by_key.get(key, None)

        if attribute is not None:
            attribute.from_yaml(obj, loader, val_node, round_trip_data)
        else:
            # the key_node will point to our object
            del loader.constructed_objects[key_node]
            val = self.item_type.from_yaml_key_val(
                loader,
                key_node,
                val_node,
                self.key_name,
                round_trip_data
            )
            obj[getattr(val, self.key_name)] = val

        return attribute  # could be None, and that is fine

    def yaml_attribute_order(self, obj, attr_order):
        """
        returns: Attribute that was applied
        """
        attr_order = AttributeCollection.yaml_attribute_order(self, obj,
                                                              attr_order)

        for item_key in obj.keys():
            attr_order.append(
                KeyedListItem(self.key_name, self.item_type, item_key)
            )

        return attr_order

    def attr_dump_order(self, obj, attr_order):
        """
        returns: Attribute that was applied
        """
        attr_order = AttributeCollection.attr_dump_order(self, obj,
                                                         attr_order)

        for item_key in obj.keys():
            attr_order.append(
                KeyedListItem(self.key_name, self.item_type, item_key)
            )

        return attr_order

