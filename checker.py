import datetime
from typing import Tuple

import numpy as np
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from croniter import croniter

class DataBackbone():
    def get_measurements(self, name, since="-1m", last=False, **meta) -> pd.DataFrame:
        raise NotImplementedError()
    
    def get_rate(self, name, since, window="1s", unit="1s", **meta) -> pd.DataFrame:
        raise NotImplementedError()

class FakeDataBackbone(DataBackbone):
    def __init__(self, measurements: list):
        self.data = pd.DataFrame(measurements)

    def _get_timedelta(self, since) -> datetime.timedelta:
        if not isinstance(since, str):
            raise Exception(f'{since} is not string')
        if len(since) < 3:
            raise Exception(f'{since}\'s length is too short')
        unit = since[-1]
        value = int(since[1:-1])
        if unit == "s":
            return datetime.timedelta(seconds=value)
        elif unit == "m":
            return datetime.timedelta(minutes=value)
        elif unit == "h":
            return datetime.timedelta(hours=value)
        elif unit == "d":
            return datetime.timedelta(days=value)
        else:
            raise Exception("Unit must be in [second, minute, hour, day]")

    def push_measurements(self, measurements: list):
        df = pd.DataFrame(measurements)
        self.data = self.data.append(df)

    def get_measurements(self, name, since="-1m", last=False, **meta) -> pd.DataFrame:
        delta = self._get_timedelta(since)
        d = self.data[self.data.timestamp > datetime.datetime.now(datetime.timezone.utc) - delta]
        if meta.get("_value") not in [None, ""]:
            v = meta.pop("_value")
            meta["value"] = v
            return d[(d.name==name) & (d.value==v)]
        return d[d.name==name]

    def time_conversion_for_pandas(self, t) -> str:
        if t[-1] == "s":
            return t[:-1] + "S"
        elif t[-1] == "m":
            return t[:-1] + "min"
        elif t[-1] == "h":
            return t[:-1] + "H"
        else:
            return t

    def get_rate(self, name, since, window="1s", unit="1s", **meta):
        df = self.get_measurements(name, since, **meta)
        return df.groupby(pd.Grouper(key="timestamp", freq=self.time_conversion_for_pandas(window))).mean().diff()
       
class InfluxDataBackbone(DataBackbone):
    def __init__(self, influx_url, influx_token, influx_org='waggle', influx_bucket='waggle'):
        self.influx_url = influx_url
        self.influx_token = influx_token
        self.influx_org = influx_org
        self.influx_bucket = influx_bucket
        self.influx_client = None

    def get_influx_client(self):
        if self.influx_client == None or not self.influx_client.ping():
            self.influx_client = InfluxDBClient(
                url=self.influx_url,
                token=self.influx_token,
                org=self.influx_org,
                debug=False
            )
        return self.influx_client

    def query_builder(self, name, since, last, additional_queries=[], **meta):
        headers = """import "experimental/aggregate"
"""
        q = [
            f'from(bucket:"{self.influx_bucket}")',
            f'range(start: {since})',
            f'filter(fn: (r) => r["_measurement"] == "{name}")',
        ]
        for k, v in meta.items():
            q.append(f'filter(fn: (r) => r["{k}"] == "{v}")')
        q.extend(additional_queries)
        if last:
            q.append('last()')
        return headers + ' |> '.join(q)

    def _add_meta(self, row: pd.Series):
        return row.to_dict()

    """ Converts InfluxDB DataFrame into Waggle DataFrame
    """
    def convert_to_api_record(self, df: pd.DataFrame):
        meta_df = df.loc[:, ~df.columns.str.contains("_")]
        df.rename(columns={"_measurement": "name", "_value": "value", "_time": "timestamp"}, inplace=True)
        df.loc[:, "meta"] = meta_df.apply(lambda row: self._add_meta(row), axis=1)
        return df

    def get_measurements(self, name, since="-1m", last=False, **meta):
        client = self.get_influx_client()
        query = self.query_builder(name, since, last, **meta)
        df = client.query_api().query_data_frame(query)
        if type(df) == list:
            df = pd.concat(df)
        return self.convert_to_api_record(df)

    def get_rate(self, name, since, window="1s", unit="1s", **meta):
        client = self.get_influx_client()
        aggregation = [f'aggregate.rate(every: {window}, unit: {unit})']
        query = self.query_builder(name, since, last=False, additional_queries=aggregation, **meta)
        df = client.query_api().query_data_frame(query)
        if type(df) == list:
            df = pd.concat(df)
        return self.convert_to_api_record(df)

    def _generate_point(self, measurement:dict):
        if "name" not in measurement:
            return "name not found"
        if "value" not in measurement:
            return "value not found"
        p = Point(measurement["name"]).field("value", measurement["value"])
        if "timestamp" in measurement:
            p.time(measurement["timestamp"])
        if "meta" in measurement:
            for k, v in measurement["meta"].items():
                p.tag(k, v)
        return p

    def push_measurements(self, measurements: list):
        client = self.get_influx_client()
        with client.write_api(write_options=SYNCHRONOUS) as write_api:
            points = []
            for m in measurements:
                p = self._generate_point(m)
                if isinstance(p, str):
                    pass
                else:
                    points.append(p)
            write_api.write(
                bucket=self.influx_bucket,
                org=self.influx_org,
                record=points)

# class RedixDataBackbone(DataBackbone):
#     def __init__(self, redix_url):
#         self.data = pd.DataFrame(measurements)

#     def get_measurements(self, name, last=False, **meta) -> pd.DataFrame:
#         return self.data

class Checker():
    def __init__(self, backbone):
        self.backbone = backbone
    
    def get_supported_funcs(self):
        return {
            "v": self.get_measurements,
            "avg": self.avg,
            "time": self.time,
            "cronjob": self.cronjob,
            "after": self.after,
            "rate": self.rate,
        }

    def time(self, unit):
        try:
            return datetime.datetime.now(datetime.timezone.utc).__getattribute__(unit)
        except:
            raise Exception(f'{unit} is not supported for time()')

    # after returns True/False based on the last successful execution of given plugin
    # it returns True if the last execution is earlier than now + interval and returns False otherwise
    # if no execution found, it returns False
    def after(self, name, since=None):
        now = datetime.datetime.now(datetime.timezone.utc)
        df = self.backbone.get_measurements("sys.scheduler.plugin.lastexecution", last=True, _value=name)
        # return False if plugin has not run
        if len(df) < 1:
            return False
        p1 = df.iloc[0]
        if since == None:
            return now > p1.timestamp
        # if another plugin is given, compare them
        elif isinstance(since, str):
            df2 = self.backbone.get_measurements("sys.scheduler.plugin.lastexecution", last=True, _value=since)
            # the other plugin has not run.
            # we can assume the plugin has run since the other plugin that never ran. Return True
            if len(df2) < 1:
                return True
            p2 = df2.iloc[0]
            return p1.timestamp > p2.timestamp
        # if since is a number, use it to compare with the plugin
        elif isinstance(since, int):
            return (now - datetime.timedelta(seconds=since)) > p1.timestamp
        else:
            return Exception("since parameter must be a plugin name or positive integer")

    def avg(self, array):
        return np.average(array)

    def cronjob(self, name, expr):
        # Accepting the cronjob pattern (minute hour day month year)
        # for example cronjob("imagesampler", "30 * * * *")
        if not croniter.is_valid(expr):
            raise Exception(f'pattern {expr} is not supported')
        now = datetime.datetime.now(datetime.timezone.utc)
        cron_time = croniter(expr).get_prev(datetime.datetime).replace(tzinfo=datetime.timezone.utc)
        # if no plugin specified, we return the croniter result
        if name == None or name == "":
            return now - cron_time < datetime.timedelta(minutes=1)
        if now - cron_time < datetime.timedelta(minutes=1):
            # we should check if we have already run the plugin for this cronjob period
            df = self.backbone.get_measurements("sys.scheduler.plugin.lastexecution", last=True, _value=name)
            for _, p in df.iterrows():
                return now - p.timestamp > datetime.timedelta(minutes=1)
            return True
        else:
            return False
    
    def rate(self, name, **kargs):
        since = kargs.pop("since", "-1m")
        window = kargs.pop("window", "1s")
        unit = kargs.pop("unit", "1s")
        df = self.backbone.get_rate(name, since, window, unit, **kargs)
        # returned DataFrame only contains timestamp and value, no meta fields
        data = np.array([m["value"] for _, m in df.iterrows()])
        if len(data) < 1:
            raise Exception(f'no data for {name} with meta {kargs} found')
        else:
            return data

    def get_measurements(self, name, **kargs):
        since = kargs.pop("since", "-1m")
        last = kargs.pop("last", False)
        df = self.backbone.get_measurements(name, since, last, **kargs)
        data = np.array([m["value"] for _, m in df.iterrows() if m["name"] == name and self.matchmeta(kargs, m["meta"])])
        if len(data) < 1:
            raise Exception(f'no data for {name} with meta {kargs} found')
        else:
            return data

    def matchmeta(self, pattern: dict, meta):
        return all(k in meta and meta[k] == v for k, v in pattern.items())

    def evaluate(self, rule) -> Tuple[bool, any]:
        l = self.get_supported_funcs()
        try:
            r = eval(rule, None, l)
            if isinstance(r, bool) or isinstance(r, np.bool_):
                return True, bool(r)
            else:
                return False, f'rule produced not True/False: {str(r)}'
        except Exception as ex:
            return False, str(ex)
