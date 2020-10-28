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

## JSON format

Each quote in the JSON must have the following fields:

* **`isin`**: the isin of the stock/fund. `isin` or `stockname` must be specified.
* **`stockname`**: the name of the stock/fund. `isin` or `stockname` must be specified.
* **`date`**: the datetime of the price in the `YYYY-MM-DDThh:mm:ssz` format. The field is mandatory. Example: `2020-09-11T00:00:00+02:00`
* **`price`**: The value of the quote. The field is mandatory.
* **`currency`**: The price currency. Default "EUR".
* **`namespace`**: The namespace in which the isin/stockname must be search. Example: "FUND". If empty, all the namespace will be searched and the first match will be used. Default ""

Other fields will be ignored.
