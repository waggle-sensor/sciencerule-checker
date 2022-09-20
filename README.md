# Sciencerule Checker
The checker evaluates science rules and returns result of the evaluation. Rules should be described in Python and its Python syntax should be valid.

A science rule has 2 parts: a state and its condition. The checker only takes the condition part to evaluate. A condition follows the below syntax,
```python3
<<condition>> : <<expression>>

<<expression>> : <<supported functions>>
                 <<python built-in functions>>
                 <<expression>> <<python operators>> <<expression>>
```

Simple examples are,
```python3
# my_condition is valid
my_condition: 1 + 2 == 3
```

# Supported Functions
Many science rules use system variables, sensor measurements, and its own variables. The checker supports the following functions to support expressions of those variables.

- `v(measurement_name)` returns an array of sensor measurements published inside the system. It returns an empty array if there is no measurements published under the name.

```python3
# a science rule that returns the condition
```
