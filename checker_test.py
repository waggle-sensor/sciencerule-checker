from checker import Checker, FakeDataBackbone
import unittest

measurements = [
    {"name": "env.temperature", "value": 23.1, "meta": {"sensor": "bme680"}},
    {"name": "env.temperature", "value": 41.2, "meta": {"sensor": "bme280"}},
    {"name": "sys.uptime", "value": 3700, "meta": {}},
]

class TestChecker(unittest.TestCase):

    def test_simple(self):
        backbone = FakeDataBackbone(measurements)
        self.checker = Checker(backbone)
        # r = self.checker.evaluate("v('env.temperature', sensor='bme680') > 46")
        # print(r)
        self.assertEqual(self.checker.evaluate("v('env.temperature', sensor='bme680') > 46")['result'], False)
        self.assertEqual(self.checker.evaluate("v('env.temperature', sensor='bme680') > 22")['result'], True)

if __name__ == "__main__":
    unittest.main()