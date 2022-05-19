import datetime
from typing import Tuple

import numpy as np
import pandas as pd
from influxdb_client import InfluxDBClient
from croniter import croniter

class DataBackbone():
    def get_measurements(self, name, last=False, **meta) -> pd.DataFrame:
        raise NotImplementedError()

class FakeDataBackbone(DataBackbone):
    def __init__(self, measurements: list):
        self.data = pd.DataFrame(measurements)

    def get_measurements(self, name, last=False, **meta) -> pd.DataFrame:
        return self.data

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

    def query_builder(self, name, last, **meta):
        q = [
            f'from(bucket:"{self.influx_bucket}")',
            'range(start: -7d)',
            f'filter(fn: (r) => r["_measurement"] == "{name}")',
        ]
        for k, v in meta.items():
            q.append(f'filter(fn: (r) => r["{k}"] == "{v}")')
        if last:
            q.append('last()')
        return ' |> '.join(q)

    def _add_meta(self, row: pd.Series):
        return row.to_dict()

    """ Converts InfluxDB DataFrame into Waggle DataFrame
    """
    def convert_to_api_record(self, df: pd.DataFrame):
        meta_df = df.loc[:, ~df.columns.str.contains("_")]
        df.rename(columns={"_measurement": "name", "_value": "value", "_time": "timestamp"}, inplace=True)
        df.loc[:, "meta"] = meta_df.apply(lambda row: self._add_meta(row), axis=1)
        return df

    def get_measurements(self, name, last=False, **meta):
        client = self.get_influx_client()
        query = self.query_builder(name, last, **meta)
        df = client.query_api().query_data_frame(query)
        if type(df) == list:
            df = pd.concat(df)
        return self.convert_to_api_record(df)

class Checker():
    def __init__(self, backbone):
        self.backbone = backbone
    
    def get_supported_funcs(self):
        return {
            "v": self.get_measurements,
            "avg": self.avg,
            "time": self.time,
            "cronjob": self.cronjob,
        }

    def time(self, unit):
        try:
            return datetime.datetime.now().__getattribute__(unit)
        except:
            raise Exception(f'{unit} is not supported for time()')

    def avg(self, array):
        return np.average(array)

    def cronjob(self, name, expr):
        # Accepting the cronjob pattern (minute hour day month year)
        # for example cronjob("30 * * * *")
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

    def get_measurements(self, name, **meta):
        df = self.backbone.get_measurements(name, **meta)
        data = np.array([m["value"] for _, m in df.iterrows() if m["name"] == name and self.matchmeta(meta, m["meta"])])
        if len(data) < 1:
            raise Exception(f'no data for {name} with meta {meta} found')
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
