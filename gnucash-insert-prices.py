#!/usr/bin/env python3

import argparse # Add the argparse import

from gnucash import Session, GncPrice, GncNumeric

import gnucash.gnucash_core_c
from gnucash.function_class import ClassFromFunctions

import datetime

from functools import lru_cache
import json 
import sys
from os.path import isfile
from os import isatty

# <MONKEY-PATCH>
# Monkey patch for GnuCash Python bindings 
# as the Python class GncPrice does not implement 
# a correct __init__ method by default


def create_price(self, book=None, instance=None):
    if instance:
        price_instance = instance
    else:
        price_instance = gnucash.gnucash_core_c.gnc_price_create(book.get_instance())
    ClassFromFunctions.__init__(self, instance=price_instance)
GncPrice.__init__ = create_price
# </MONKEY-PATCH>


@lru_cache(maxsize=32)
def get_currency(commodity_table, currency_str):
    "Returns the currency commodity with the given name in the commodity table"
    return commodity_table.lookup('ISO4217', currency_str)


def get_namespaces_list(commodity_table, namespace_name=""):
    namespaces = None
    if namespace_name != "": 
        # single namespace
        ns = commodity_table.find_namespace(namespace_name)
        if ns is not None:
            namespaces = [ ns ]
    else:
        # all namespaces
        namespaces = commodity_table.get_namespaces_list()
    
    return namespaces

# def print_commodity(commodity):
#     if commodity is None:
#         print("Commodity(None)")
#         return

#     print("Commodity(isin=\"{1}\", fullname=\"{0}\", namespace=\"{2}\")".format(
#         commodity.get_fullname(),
#         commodity.get_cusip(),
#         commodity.get_namespace()
#     ))

@lru_cache(maxsize=128)
def get_commodity_by_isin(commodity_table, isin, namespace_name=""):
    if isin == "":
        return None

    namespaces = get_namespaces_list(commodity_table, namespace_name)
    if namespaces is None:
        return

    for namespace in namespaces:
        # get a list of all commodities in namespace
        commodities = commodity_table.get_commodities(namespace.get_name())
        for commodity in commodities:
            if isin == commodity.get_cusip():
                return commodity
    return None

@lru_cache(maxsize=128)
def get_commodity_by_fullname(commodity_table, fullname, namespace_name=""):
    if fullname == "":
        return None

    namespaces = get_namespaces_list(commodity_table, namespace_name)
    if namespaces is None:
        return

    for namespace in namespaces:
        # Get a list of all commodities in namespace
        commodities = commodity_table.get_commodities(namespace.get_name())
        for commodity in commodities:
            if fullname == commodity.get_fullname():
                return commodity
    return None


# returns a price for the comodity with currency and date (only date, no time)
# returns None if not found
def find_price(book, commodity, currency, dtime):
    prices = book.get_price_db().get_prices(commodity, currency)
    for price in prices:
        price_datetime = price.get_time64()
        if price_datetime.date() == dtime.date():
            return price
    return None

def add_price(book, value, date, currency_str="EUR", 
              commodity_isin="", commodity_fullname="", commodity_namespace="",
              ):
    # returns: 
    #   commodity: the commodity (eventually) updated 
    #   bool: 
    #     True:  added
    #     False: skipped because the price already exists
    #
    # exceptions: yessss

    PRICE_SOURCE_USER_PRICE = 2
    
    if book is None:
        raise ValueError('Book must not be None')

    if (commodity_isin == "") & (commodity_fullname == ""):
        raise ValueError('Either isin or fullname of commodity is expected')

    commodity_table = book.get_table()

    # get the currency by str
    currency = get_currency(commodity_table, currency_str)
    if currency is None:
        raise LookupError("Currency {0} not found".format(currency_str))

    commodity = None
    # get the commodity by isin (if defined)
    if commodity_isin != "":
        commodity = get_commodity_by_isin(commodity_table, commodity_isin, commodity_namespace)
        if commodity is None: 
            raise LookupError("Commodity with ISIN \"{0}\" and Namespace \"{1}\" not found".format(commodity_isin, commodity_namespace))

    # get the commodity by fullname (if needed)
    if commodity is None:
        commodity = get_commodity_by_fullname(commodity_table, commodity_fullname, commodity_namespace)
        if commodity is None: 
            raise LookupError("Commodity with FullName \"{0}\" and Namespace \"{1}\" not found".format(commodity_fullname, commodity_namespace))
    assert(commodity is not None)

    # check prise already exists
    price = find_price(book, commodity, currency, date)
    if price != None:
        v = price.get_value()
        vf = v.num/v.denom
        # GncNumeric(instance=v).to_string()
        if abs(value - vf) > 0.02:
            raise ValueError("Price exists: old value {0}, new value {1}".format(value, vf))

        # print("SKIP (commodity={0}, currency={1}, date={2}) already exists".format(commodity_isin, currency_str, date))
        return commodity, False

    p = GncPrice(book)
    p.set_time64(date)
    p.set_commodity(commodity)
    p.set_currency(currency)
    p.set_value(GncNumeric(value))
    p.set_source(PRICE_SOURCE_USER_PRICE)
    book.get_price_db().add_price(p)
    # print("ADD (commodity={0}, price={1:.3f} {2}, date={3})".format(commodity_isin, value, currency_str, date))
    return commodity, True

# try to insert the quotes and print the result of each operation
# returns the number of errors
def do_insert_prices(book, quotes):
    # quotes is an array of dict. each dict must have fields (* = mandatory)
    # *Date: 2020-09-11T00:00:00+02:00
    # *Isin: 
    # *Price: 
    #  StockName:
    #  Currency: default "EUR"
    #  Namespace: default ""

    errors = 0

    for q in quotes:
        date = datetime.datetime.strptime(q["Date"], '%Y-%m-%dT%H:%M:%S%z')
        isin = q["Isin"]
        namespace_name = q.get("Namespace", "")
        currency_str = q.get("Currency", "EUR")
        price = q["Price"]
        fullname = q.get("StockName")

        try:
            c, added = add_price(
                book, price, date, currency_str, 
                commodity_isin=isin, 
                commodity_fullname=fullname, 
                commodity_namespace=namespace_name)
            if added:
                print("ADD : (commodity={0}, price={1:.3f} {2}, date={3})".format(c.get_cusip(), price, currency_str, date))
            else:
                print("SKIP: (commodity={0}, currency={1}, date={2}) already exists".format(c.get_cusip(), currency_str, date))
        except Exception as err:
            print("ERR : %s" % err)
            errors = errors+1
        
    return errors

def insert_prices(gnucash_file, json_file):
    
    if not isfile(gnucash_file):
        print("gnucash_file not found")
        return

    if json_file is None:

        if isatty(sys.stdin.fileno()):
            print("Error: json expected from file or stdin")
            return
        try:
            quotes = json.load(sys.stdin)
        except Exception as err:
            print("Error reading json file: %s" % err)
            return
    else:

        if not isfile(json_file):
            print("json_file not found")
            return

        try:
            with open(json_file, "r") as read_file:
                quotes = json.load(read_file)
        except Exception as err:
            print("Error reading json file: %s" % err)
            return

    session = None
    try:
        session = Session(gnucash_file, ignore_lock=False)
        errs = do_insert_prices(session.book, quotes)
        if errs == 0:
            print("Non errors found")
            session.save()
        else:
            raise Exception("Found %d errors" % errs)
    except Exception as err:
        print("Error updating gnucash file: %s" % err)
    finally:
        if session != None:
            session.end()



def main_cmd():
    """Main command
    
    Handle command line arguments and call insert prices"""

    # Create a parser
    parser = argparse.ArgumentParser(description='Insert gnucash quote prices from a json file')

    # Add argument
    parser.add_argument('gnucash_file', help="The gnucash file to be updated")  
    parser.add_argument('-j', '--json_file', help="The json file with the new quotes")

    # parse arguments
    # args = parser.parse_args('test.gnucash quotes.json '.split())
    args = parser.parse_args()

    print(args)
    # print(parser.format_help())
    # print(args.gnucash_file)
    
    insert_prices(args.gnucash_file, args.json_file)


if __name__ == '__main__':
    main_cmd()