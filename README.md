# gnucash-insert-prices

Insert gnucash quote prices from a json file.

## Usage

    usage: gnucash-insert-prices.py [-h] [-j JSON_FILE] [--tty] gnucash_file

    Insert gnucash quote prices from a json file

    positional arguments:
    gnucash_file          the gnucash file to be updated

    optional arguments:
    -h, --help            show this help message and exit
    -j JSON_FILE, --json_file JSON_FILE
                          the json file containing the new quotes (default stdin)
    --tty                 enable an interactive json file stream


If the JSON file is not specified, the quotes are read from `stdin`. For example:

    cat quotes.json | gnucash-insert-prices..py file.gnucash


*NOTE*: an error is returned if `stdin` is not ready, unless `--tty` flag is specified. 


For each quote in the JSON file it print out the operation performed: ADD, SKIP, ERR

In case of error, all the updates are discarded.

If no error is found, the gnucash file will be saved.



## JSON format

Each quote in the JSON must have the following fields:

|Field      |Description|Note|
|-----------|-----------|---|
|`isin`     |isin of the stock/fund|`isin` or `name` must be specified|
|`name`     |name of the stock/fund|`isin` or `name` must be specified|
|`date`     |datetime of the price in the `YYYY-MM-DDThh:mm:ssz` format. Example: `2020-09-11T00:00:00+02:00` |mandatory|       
|`price`    |value of the quote|mandatory|
|`currency` |price currency. Example: `"USD"`|default `"EUR"`|
|`namespace`|namespace in which the `isin`/`name` will be searched. Example: `namespace="FUND"`. If empty, all the namespaces will be searched and the first match will be used|default `""`|


All other fields will be ignored.


## Examples

### Example 1: Success

Input JSON file:

    [
    {"isin": "TEST00000001", "date": "2020-10-11T00:00:00+02:00", "price": 10.01},
    {"name": "Test commodity 2", "date": "2020-10-12T00:00:00+02:00", "price": 20.02}
    ]

Output:

    ADD : (commodity=TEST00000001, price=10.010 EUR, date=2020-10-11 00:00:00+02:00)
    ADD : (commodity=TEST00000002, price=20.020 EUR, date=2020-10-12 00:00:00+02:00)

    No errors found: Commit


### Example 2: Error

Input JSON file:

    [
    {"isin": "TEST00000001", "date": "2020-10-11T00:00:00+02:00", "price": 10.01},
    {"name": "Test commodity 2", "date": "2020-10-12T00:00:00+02:00", "price": 20.02},
    {"isin": "TEST00000005", "namespace": "TEST", "date": "2020-10-15T00:00:00+02:00", "price": 50.05},
    {"name": "Test commodity 6", "date": "2020-10-16T00:00:00+02:00", "price": 60.06},
    {"isin": "TEST00000001", "date": "2020-10-11T00:00:00+02:00", "price": 10.01},
    {"isin": "TEST00000001", "date": "2020-10-11T00:00:00+02:00", "price": 10.99}
    ]


Output:

    ADD : (commodity=TEST00000001, price=10.010 EUR, date=2020-10-11 00:00:00+02:00)
    ADD : (commodity=TEST00000002, price=20.020 EUR, date=2020-10-12 00:00:00+02:00)
    ERR : Commodity with isin="TEST00000005" and namespace="TEST" not found
    ERR : Commodity with name="Test commodity 6" not found
    SKIP: (commodity=TEST00000001, currency=EUR, date=2020-10-11 00:00:00+02:00) already exists
    ERR : Price exists: old value 10.99, new value 10.01

    Error updating gnucash file: Found 3 errors: Rollback

