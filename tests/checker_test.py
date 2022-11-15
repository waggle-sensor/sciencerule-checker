from os import getenv
import datetime
import unittest

from checker import Checker, InfluxDataBackbone, FakeDataBackbone

@unittest.skipIf(getenv("NODE_INFLUXDB_URL", "") == "", "No inlufxDB specified.")
class TestCheckerWithRealBackend(unittest.TestCase):
    def setUp(self):
        self.backbone = InfluxDataBackbone(
            getenv("NODE_INFLUXDB_URL", "http://wes-node-influxdb:8086"),
            getenv("NODE_INFLUXDB_QUERY_TOKEN", ""))
        self.checker = Checker(self.backbone)

    def test_measurements(self):
        measurements = [
            {"timestamp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=100), "name": "env.temperature", "value": 15.1, "meta": {"sensor": "bme680"}},
            {"timestamp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1), "name": "env.temperature", "value": 23.1, "meta": {"sensor": "bme680"}},
            {"timestamp": datetime.datetime.now(datetime.timezone.utc), "name": "env.temperature", "value": 41.2, "meta": {"sensor": "bme280"}},
            {"timestamp": datetime.datetime.now(datetime.timezone.utc), "name": "sys.uptime", "value": 3700, "meta": {}},
        ]
        self.backbone.push_measurements(measurements=measurements)
        # the avg returns 1 data point that its average is greater than 23
        self.assertTrue(self.checker.evaluate("avg(v('env.temperature', sensor='bme680')) > 23")[1])
        # the "since" returns 2 different data points that their average is less than 23
        self.assertFalse(self.checker.evaluate("avg(v('env.temperature', since='-2m', sensor='bme680')) > 23")[1])
        # swapping parameters other than measurement name should not affect the result.
        self.assertFalse(self.checker.evaluate("avg(v('env.temperature', sensor='bme680', since='-2m')) > 23")[1])


class TestCheckerFunctions(unittest.TestCase):
    def test_measurements(self):
        measurements = [
            {"timestamp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=100), "name": "env.temperature", "value": 15.1, "meta": {"sensor": "bme680"}},
            {"timestamp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1), "name": "env.temperature", "value": 23.1, "meta": {"sensor": "bme680"}},
            {"timestamp": datetime.datetime.now(datetime.timezone.utc), "name": "env.temperature", "value": 41.2, "meta": {"sensor": "bme280"}},
            {"timestamp": datetime.datetime.now(datetime.timezone.utc), "name": "sys.uptime", "value": 3700, "meta": {}},
        ]
        backbone = FakeDataBackbone(measurements)
        self.checker = Checker(backbone)
        # the avg returns 1 data point that its average is greater than 23
        self.assertTrue(self.checker.evaluate("avg(v('env.temperature', sensor='bme680')) > 23")[1])
        # the "since" returns 2 different data points that their average is less than 23
        self.assertFalse(self.checker.evaluate("avg(v('env.temperature', since='-2m', sensor='bme680')) > 23")[1])
        # swapping parameters other than measurement name should not affect the result.
        self.assertFalse(self.checker.evaluate("avg(v('env.temperature', sensor='bme680', since='-2m')) > 23")[1])

    def test_time(self):
        self.checker = Checker(None)
        target_hour = datetime.datetime.now(datetime.timezone.utc).hour
        _, result = self.checker.evaluate(f'time("hour") == {target_hour}')
        self.assertEqual(result, True)

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
        last_1_minutes = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)
        last_2_minutes = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)
        measurements = [
            {"timestamp": last_1_minutes, "name": "sys.scheduler.plugin.lastexecution", "value": "yourplugin", "meta": {}},
            {"timestamp": last_2_minutes, "name": "sys.scheduler.plugin.lastexecution", "value": "myplugin", "meta": {}},
        ]
        backbone = FakeDataBackbone(measurements)
        self.checker = Checker(backbone)
        # Check if notmyplugin ran before. False is expected because notmyplugin has not been run
        _, result = self.checker.evaluate(f'after("notmyplugin")')
        self.assertEqual(result, False)
        # Check if myplugin ran before. True is expected
        _, result = self.checker.evaluate(f'after("myplugin")')
        self.assertEqual(result, True)
        # Check if myplugin ran before notmyplugin. since there is no record for notmyplugin True is expected
        _, result = self.checker.evaluate(f'after("myplugin", since="notmyplugin")')
        self.assertEqual(result, True)
        # Check if yourplugin has run since the last run of my plugin. True is expected
        _, result = self.checker.evaluate(f'after("yourplugin", since="myplugin")')
        self.assertEqual(result, True)
        # Check if myplugin ran earlier than 119 seconds ago from now. True is expected as the myplugin ran 120 seconds ago
        _, result = self.checker.evaluate(f'after("myplugin", since=119)')
        self.assertEqual(result, True)
        # Check if myplugin ran earlier than 121 seconds from now. False is expected
        _, result = self.checker.evaluate(f'after("myplugin", since=121)')
        self.assertEqual(result, False)

if __name__ == "__main__":
    unittest.main()