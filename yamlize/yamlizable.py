import ruamel.yaml
import six
import inspect

from yamlize.round_trip_data import RoundTripData
from yamlize.yamlizing_error import YamlizingError


class Yamlizable(object):

    __slots__ = ()

    def __getstate__(self):
        state = {}

        if hasattr(self, '__dict__'):
            state.update(self.__dict__)

        applied_slots = set((None,))  # populated with None

        for cls in reversed(type(self).__mro__):
            cls_slots = getattr(cls, '__slots__', None)

            if cls_slots in applied_slots:
                continue

            applied_slots.add(cls_slots)

            for attr_name in cls_slots:
                if attr_name.startswith('__'):
                    attr_name = '_{}{}'.format(cls.__name__, attr_name)
                    while attr_name.startswith('__'):
                        attr_name = attr_name[1:]

                if attr_name in state:
                    continue

                state[attr_name] = getattr(self, attr_name)

        return state

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)

    @classmethod
    def get_yamlizable_type(cls, type_):
        if issubclass(type_, Yamlizable):
            return type_
        else:
            return Typed(type_)

    @classmethod
    def load(cls, stream, Loader=ruamel.yaml.RoundTripLoader):
        # can't use ruamel.yaml.load because I need a Resolver/loader for
        # resolving non-string types
        loader = Loader(stream)
        try:
            node = loader.get_single_node()
            return cls.from_yaml(loader, node, None)
        finally:
            loader.dispose()

    @classmethod
    def dump(cls, data, stream=None, Dumper=ruamel.yaml.RoundTripDumper):
        # can't use ruamel.yaml.load because I need a Resolver/loader for
        # resolving non-string types
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

    @classmethod
    def from_yaml(cls, loader, node, round_trip_data):
        raise NotImplementedError

    @classmethod
    def to_yaml(cls, dumper, self, round_trip_data):
        raise NotImplementedError


class Typed(type):

    __types = {}

    def __new__(mcls, type_):
        if type_ not in mcls.__types:
            mcls.__types[type_] = type('Yamlizable' + type_.__name__,
                                       (Strong,), {'_Strong__type': type_})
        return mcls.__types[type_]


class Strong(Yamlizable):

    __slots__ = ()

    __type = None

    @classmethod
    def from_yaml(cls, loader, node, round_trip_data):
        data = loader.construct_object(node, deep=True)

        if not isinstance(data, cls.__type):
            try:
                new_value = cls.__type(data)  # to coerce to correct type
                # TODO: round trip data
                # new_value._set_round_trip_data(node)
                # loader.constructed_objects[node] = new_value
            except Exception:
                raise YamlizingError('Failed to coerce data `{}` to type `{}`'
                                     .format(data, cls))

            if new_value != data:
                raise YamlizingError(
                    'Coerced `{}` to `{}`, but the new value `{}`'
                    ' is not equal to old `{}`.'
                    .format(type(data), type(new_value), new_value, data), node)

            data = new_value

        round_trip_data[data] = RoundTripData(node)
        return data

    @classmethod
    def to_yaml(cls, dumper, data, round_trip_data):
        if not isinstance(data, cls.__type):
            try:
                data = cls.__type(data)  # to coerce to correct type
            except BaseException:
                raise YamlizingError('Failed to coerce data `{}` to type `{}`'
                                     .format(data, cls))

        node = dumper.represent_data(data)
        round_trip_data[data].apply(node)
        return node


Dynamic = Typed(object)

