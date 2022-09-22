# Sciencerule Checker
The checker evaluates science rules and returns result of the evaluation. Rules should be described in Python and its Python syntax must be valid.

A science rule has 2 parts: a state and its condition. The checker only takes the condition part to evaluate. A condition follows the below syntax,
```python3
<<condition>> : <<expression>>

<<expression>> : <<supported functions>>
                 <<python built-in functions>>
                 <<expression>> <<python operators>> <<expression>>
```

Examples of science rules are,
```python3
# my_state is valid because the condition is valid constantly
my_state: 1 + 2 == 3

# it is hot if ambient temperature is greater than 35 degree Celius
hot: v("env.temperature") > 35

# the rule is valid every minute as long as myprogram did not yet run at the timing
schedule: cronjob("myprogram", "* * * * *")
```

# Supported Functions To Describe Conditions
Many science rules use system variables, sensor measurements, and its own variables. The checker supports the following functions to support expressions of those variables. See [details](docs/supported_functions.md) on the supported functions.