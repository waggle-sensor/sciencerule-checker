import datetime
import unittest

from checker import Checker, FakeDataBackbone


class TestCheckerFunctions(unittest.TestCase):
    def test_simple(self):
        measurements = [
            {"name": "env.temperature", "value": 23.1, "meta": {"sensor": "bme680"}},
            {"name": "env.temperature", "value": 41.2, "meta": {"sensor": "bme280"}},
            {"name": "sys.uptime", "value": 3700, "meta": {}},
        ]
        backbone = FakeDataBackbone(measurements)
        self.checker = Checker(backbone)
        self.assertEqual(self.checker.evaluate("all(v('env.temperature', sensor='bme680') > 46)")[1], False)
        self.assertEqual(self.checker.evaluate("avg(v('env.temperature', sensor='bme680')) > 22")[1], True)

    def test_cronjob(self):
        last_2_minutes = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)
        measurements = [
            {"timestamp": last_2_minutes, "name": "sys.scheduler.plugin.lastexecution", "value": "myplugin", "meta": {}},
        ]
        backbone = FakeDataBackbone(measurements)
        self.checker = Checker(backbone)
        current_minute = datetime.datetime.now(datetime.timezone.utc).minute
        _, result = self.checker.evaluate(f'cronjob(\'\', \'{current_minute} * * * *\')')
        self.assertEqual(result, True)
        _, result = self.checker.evaluate("cronjob('myplugin', '* * * * *')")
        self.assertEqual(result, True)

    def test_after(self):
        last_2_minutes = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)
        measurements = [
            {"timestamp": last_2_minutes, "name": "sys.scheduler.plugin.lastexecution", "value": "myplugin", "meta": {}},
        ]
        backbone = FakeDataBackbone(measurements)
        self.checker = Checker(backbone)
        # Check if notmyplugin ran before False is expected because notmyplugin has not been run
        _, result = self.checker.evaluate(f'after("notmyplugin")')
        self.assertEqual(result, False)
        # Check if myplugin ran before True is expected
        _, result = self.checker.evaluate(f'after("myplugin")')
        self.assertEqual(result, True)
        # Check if myplugin ran in the last 119 seconds True is expected as the myplugin ran 120 seconds ago
        _, result = self.checker.evaluate(f'after("myplugin", 119)')
        self.assertEqual(result, True)
        # Check if myplugin ran in the last 121 seconds False is expected
        _, result = self.checker.evaluate(f'after("myplugin", 121)')
        self.assertEqual(result, False)

if __name__ == "__main__":
    unittest.main()