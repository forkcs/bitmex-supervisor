# BitMEX Supervisor

This is a library-like application, which operates with orders and positions on your account.

*Current version:* **0.6**
#### Features:
* Creating an cancelling orders on your account. Stop-loss, Limit, passive, reduce-only, close-only, hidden orders supported.
* Preventing these orders for being lost, cancelled or rejected: Supervisor will place them anew.
* Supervisor closes all orders, which are not supervised.
* When the supervised order has been filled, Supervisor will not try to place it. 
* Put callbacks on supervised orders, which are called when order has been filled, partially executed or cancelled.
* Set and maintain the position size.
* Various market-price or limit entries in position.
* Place Trailing-stop levels
#### In develop:
* Enter position with rebate by tracking last market price and moving limit order up.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

For now we support only the version of Python that we use in development.

```
Pyhton 3.8 +
```

### Installing

#### Manual install from repo

Clone and go to directory:

```commandline
git clone https://github.com/forkcs/bitmex-supervisor.git
cd bitmex-supervisor/
```

Then create and activate a virtual environment:

```commandline
python3 -m venv venv
source venv/bin/activate
```

Install project requirements:

```commandline
pip install -r requirements.txt
```

#### Install with pip

```python
pip install bitmex-supervisor
```

#### Install from sources

Coming soon...

## Running the tests

There are automated tests for this project. Running the tests is optional. For run tests you need to install py.test and responses packages.

Install with pip:

```commandline
pip install pytest responses
```

Run tests:

```commandline
pytest
```

**If all the tests are passed, you may proceed to the next steps.**

### After successful installation:

Now you can import supervisor module from project dir:
```python
import supervisor
```
For more details see example.py.

### Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## Usage

Create Exchange instance:

```python
from supervisor.core.interface import Exchange

exchange = Exchange(symbol='XBTUSD',
                    api_key='YOUR_API_KEY',
                    api_secret='YOUR_API_SECRET',
                    test=True)       # test=True for use Testnet
```

Create Supervisor instance:

```python
from supervisor import Supervisor

supervisor = Supervisor(interface=exchange)
```

Set necessary position size, Supervisor will fix it:

```python
supervisor.position = 150
```

If Supervisor is already running, you can use on of provided entry methods

```python
supervisor.stop_cycle()
supervisor.enter_by_market_order(150)
supervisor.run_cycle()
```

Create order:

```python
from supervisor.core.orders import Order

my_order = Order(order_type='Limit', qty=100, side='Buy', price=6500, hidden=True, passive=True)

supervisor.add_order(my_order)
```

You can attach any callback to order events.

Callback must retrieve *args and **kwargs attributes.

```python
order_with_callback = Order(order_type='Limit', qty=100, side='Buy', price=6500)

# for example, let's attach callback to order fill event
def callback(*args, **kwargs):
    print('Order has been filled!!!')
order._on_fill = callback

# Run cycle and when your order filled, the message will be printed.
```

There are 3 possible events provided:

```python
Order._on_fill: Callable
Order._on_reject: Callable
Order._on_cancel: Callable
```

Run Supervisor cycle (works in own thread):

```python
supervisor.run_cycle()
```

You can stop, continue and exit Supervisor cycle:

```python
supervisor.stop_cycle()
# do staff
supervisor.run_cycle()  # this method can both run and continue cycle
supervisor.exit_cycle() # this method terminates cycle`s thread and quit correctly
```

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Authors

* **Fedor Soldatkin** - *Initial work* - [forkcs](https://github.com/forkcs)


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE) file for details.

