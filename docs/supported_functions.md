# Supported Functions To Describe Conditions

## `v(measurement_name)`
`v` function returns an array of sensor measurements published inside the system. It returns an empty array if there is no measurements published under the name.

```python
# get temperature values from bme680 sensor
v('env.temperature', sensor='bme680')
# take average of temperature values from bme680
avg(v('env.temperature', sensor='bme680'))
# returns True if the total car counts in the last minute is greater than 5 cars
sum(v("env.count.car", since="-1m")) > 5
```

## `time(unit)`
`time` function returns the current time of the unit

```python
# compare if current hour is 2
time("hour") == 2
# compare if current minute is 0
time("minute") == 0
```

## `cronjob(program_name, cronjob_time)`
`cronjob` function returns _True_ whenever given `cronjob_time` is valid, otherwise _False_. If `program_name` has run successfully run at the `cronjob_time`, the function returns _False_ even if the `cronjob_time` is valid. This function is useful to schedule program runs every _x_ time.

```python
# returns True at every minute
cronjob("my_program", "* * * * *")
# returns True in every 30 minutes. If my_program has run at the time of every 30 minutes it returns False
cronjob("my_program", "*/30 * * * *")
```

## `after(program_name, since=None)`
`after` function returns _True_ if `program_name` has successfully run. `since` option can be used to provide a baseline in time to compare with `program_name`. There are 2 cases for the option,

- if `since` is a name of program, it uses the execution time of the program to compare. If execution log of the program does not exist, it uses the current time as baseline
- if `since` is positive integer, it calculates time from the current time using given number in seconds

```python
# returns True if program_A has run
after("program_A")
# returns True if program_A has run since program_B ran
after("program_A" since="program_B")
# returns True if program_A has run since 120 seconds from now
after("program_A" since=120)
```

This function can be useful to create a dependency between programs. For example, program B needs to run after program A runs
```python
# a complete science rule
# state: condition
schedule("program_B"): after("program_A", since="program_B")
```

## `rate(measurement_name, since="-1m")`
`rate` function returns an array of the per-second average rate of increase of the measurement. `since` controls the size of data. Larger value returns bigger data but takes longer. `rate` function works the best with counter-type values.

```python
# returns True if the summation of noise level changes in the last minute is greater than 30 dB
sum(rate("env.sound.noise")) > 30
# returns True if there is at least one per-second average of the raingauge accumulation that exceeds the threshold
threshold_for_event_per_second = 0.0006
any(rate("env.raingauge.event_acc", since="-5m") > threshold_for_event_per_second)
```