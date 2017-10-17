

class Map(Yamlizable):

    __slots__ = ('__data',)

    key_type = None

    value_type = None

    def __init__(self, *args, **kwargs):
        self.__data = dict(*args, **kwargs)

    def __getattr__(self, attr_name):
        return getattr(self.__data, attr_name)

    def __iter__(self):
        return iter(self.__data)

    def __repr__(self):
        return repr(self.__data)

    def __str__(self):
        return str(self.__data)

    def __len__(self):
        return len(self.__data)

    def __getitem__(self, index):
        return self.__data[index]

    @classmethod
    def from_yaml(cls, loader, node):
        if not isinstance(node, ruamel.yaml.MappingNode):
            raise YamlizingError('Expected a MappingNode', node)

        if node in loader.constructed_objects:
            return loader.constructed_objects[node]

        self = cls()
        self._set_round_trip_data(node)
        loader.constructed_objects[node] = self

        # node.value list of values
        for key_node, value_node in node.value:
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

