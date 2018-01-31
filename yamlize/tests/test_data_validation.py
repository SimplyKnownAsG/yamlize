import unittest

from yamlize import Object, AttributeCollection, YamlizingError, Attribute, yaml_object

class TestDataValidation(unittest.TestCase):

    def test_properties(self):
        class PositivePoint(Object):

            attributes = AttributeCollection(Attribute('x', type=float),
                                             Attribute('y', type=float))

            def __new__(cls):
                self = Object.__new__(cls)
                self._x = 0.0
                return self

            @property
            def x(self):
                return self._x

            @x.setter
            def x(self, x):
                if x < 0.0:
                    raise ValueError('Cannot set PositivePoint.x to {}'.format(x))
                self._x = x

        with self.assertRaises(YamlizingError):
            PositivePoint.load(u'{ x: -0.0000001, y: 1.0}') # doctest: +IGNORE_EXCEPTION_DETAIL

    def test_from_yaml(self):

        @yaml_object(Attribute('x', type=float),
                     Attribute('y', type=float))
        class PositivePoint2(object):

            @classmethod
            def from_yaml(cls, loader, node, round_trip_data=None):
                # from_yaml.__func__ is the unbound class method
                self = Object.from_yaml.__func__(PositivePoint2, loader, node, round_trip_data)

                if self.x < 0.0 or self.y < 0.0:
                    raise YamlizingError('Point x and y values must be positive', node)

                return self

        with self.assertRaises(YamlizingError):
            PositivePoint2.load(u'{ x: -0.0000001, y: 1.0}') # doctest: +IGNORE_EXCEPTION_DETAIL


if __name__ == '__main__':
    unittest.main()

