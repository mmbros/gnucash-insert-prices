import unittest
from unittest.mock import patch 
from io import StringIO 

from gnucash import (
        Session, Account, Transaction, Split, GncNumeric, GncCommodity
)

import datetime
import sys
import glob

# <unittest-for-scripts> 
# How do I write Python unit tests for scripts
# https://stackoverflow.com/questions/33469246/how-do-i-write-python-unit-tests-for-scripts-in-my-bin-directory

from importlib.machinery import ModuleSpec, SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec
import os.path
import types


def import_from_source( name : str, file_path : str ) -> types.ModuleType:
    loader : SourceFileLoader = SourceFileLoader(name, file_path)
    spec : ModuleSpec = spec_from_loader(loader.name, loader)
    module : types.ModuleType = module_from_spec(spec)
    loader.exec_module(module)
    return module

# script_path = "/home/mau/Code/prj/fin/cmd/gnucash-insert-prices/gnucash-insert-prices.py"
script_path : str = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "gnucash-insert-prices.py",
    )
)
script : types.ModuleType = import_from_source("script", script_path)
# </unittest-for-scripts> 



FILE_PREFIX = "/tmp/gnucash-insert-prices"
COMMODITY_NAMESPACE = "TEST"
GNUCASH_PATH = FILE_PREFIX + "0.gnucash"


def gnc_commodity_new(book, fullname, commodity_namespace, mnemonic, cusip, fraction):
    return GncCommodity(
            book, 
            fullname, 
            commodity_namespace, 
            mnemonic, 
            cusip, 
            fraction)


def get_commodity_fullname(num):
    return "Test commodity %d" % num

def get_commodity_isin(num):
    return "TEST%08d" % num


def insert_test_commodity(book, num):
    comm = gnc_commodity_new(
        book, 
        get_commodity_fullname(num),
        "TEST",
        "TEST%d" % num,
        get_commodity_isin(num),
        1000)
    book.get_table().insert(comm)


def init_gnucash_file(path):
    session  = Session("xml://%s" % path, is_new=True, force_new=True) 

    book = session.book

    comm_table = book.get_table()
    
    #Set new root account
    root_acct = Account(book)
    root_acct.SetName("Root")
    root_acct.SetType(13) #ACCT_TYPE_ROOT = 13
    book.set_root_account(root_acct)


    insert_test_commodity(book, 1)
    insert_test_commodity(book, 2)
    insert_test_commodity(book, 3)

    # session.save()
    # session.end()
    return session

def delete_files(pattern):
    fileList = glob.glob(pattern)
    # Iterate over the list of filepaths & remove each file.
    for filePath in fileList:
        try:
            os.remove(filePath)
        except:
            print("Error while deleting file : ", filePath)


class TestGnucash(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        delete_files(FILE_PREFIX + "*")
        cls._session = init_gnucash_file(GNUCASH_PATH)

    @classmethod
    def tearDownClass(cls):
        cls._session.save()
        cls._session.end()

    def setUp(self):
        self.session = self.__class__._session
        self.book = self.session.book
        self.comm_table = self.book.get_table()


    def test_get_currency(self):
        script.get_currency.cache_clear()
        for currency_str in ["EUR", "USD", "GBP", "ITL", "EUR"]:
            curr = script.get_currency(self.comm_table, currency_str)
            self.assertIsNotNone(curr, msg="Currency not found (%s)" % currency_str)
       
        # check cache info
        cache_info = script.get_currency.cache_info()
        # print(cache_info)
        self.assertEqual(cache_info.hits, 1) # EUR
        self.assertEqual(cache_info.misses, 4)
        self.assertEqual(cache_info.currsize, 4)


    def test_get_namespaces_list(self):
        nslist = script.get_namespaces_list(self.comm_table)
        nslistnames = [ns.get_name() for ns in nslist] 
        # ['AMEX', 'NYSE', 'NASDAQ', 'EUREX', 'FUND', 'template', 'CURRENCY', 'TEST']
        self.assertIn(COMMODITY_NAMESPACE, nslistnames)
        self.assertIn("FUND", nslistnames)
        self.assertNotIn("UNKNOWN", nslistnames)

    def test_get_namespaces_list_with_ns(self):
        nslist = script.get_namespaces_list(self.comm_table, "TEST")
        nslistnames = [ns.get_name() for ns in nslist] 
        self.assertIn(COMMODITY_NAMESPACE, nslistnames)
        self.assertNotIn("FUND", nslistnames)
        self.assertNotIn("UNKNOWN", nslistnames)

    def test_get_commodity_by_isin(self):

        num = 1
        isin = get_commodity_isin(num)
        commodity = script.get_commodity_by_isin(self.comm_table, isin)
        self.assertIsNotNone(commodity, msg="Commodity not found (isin=%s)" % isin)
        self.assertEqual(commodity.get_cusip(), isin)

        num = 5
        isin = get_commodity_isin(num)
        commodity = script.get_commodity_by_isin(self.comm_table, isin)
        self.assertIsNone(commodity, msg="Commodity found (isin=%s)"%isin)

    def test_get_commodity_by_fullname(self):
        num = 1
        fullname = get_commodity_fullname(num)
        commodity = script.get_commodity_by_fullname(self.comm_table, fullname)
        self.assertIsNotNone(commodity, msg="Commodity not found (fullname=%s)"%fullname)
        self.assertEqual(commodity.get_fullname(), fullname)

        num = 5
        fullname = get_commodity_fullname(num)
        commodity = script.get_commodity_by_fullname(self.comm_table, fullname)
        self.assertIsNone(commodity, msg="Commodity found (fullname=%s)"%fullname)

    def test_get_commodity_by_isin_and_namespace(self):
        num = 1
        isin = get_commodity_isin(num)
        namespace = "TEST"
        commodity = script.get_commodity_by_isin(self.comm_table, isin, namespace)
        self.assertIsNotNone(commodity, msg="Commodity not found (isin=%s and namespace=%s)" % (isin, namespace))
        self.assertEqual(commodity.get_cusip(), isin)

        num = 1
        isin = get_commodity_isin(num)
        namespace = "UNKNOWN"
        commodity = script.get_commodity_by_isin(self.comm_table, isin, namespace)
        self.assertIsNone(commodity, msg="Commodity found (isin=%s and namespace=%s)" % (isin, namespace))

    def test_get_commodity_by_fullname_and_namespace(self):
        num = 1
        fullname = get_commodity_fullname(num)
        namespace = COMMODITY_NAMESPACE
        commodity = script.get_commodity_by_fullname(self.comm_table, fullname, namespace)
        self.assertIsNotNone(commodity, msg="Commodity not found (fullname=%s and namespace=%s)" % (fullname, namespace))
        self.assertEqual(commodity.get_fullname(), fullname)

        num = 1
        namespace = "UNKNOWN"
        fullname = get_commodity_fullname(num)
        commodity = script.get_commodity_by_fullname(self.comm_table, fullname, namespace)
        self.assertIsNone(commodity, msg="Commodity found (fullname=%s and namespace=%s)" % (fullname, namespace))


    def test_add_price_by_isin(self):
        # add_price(book, value, date, 
        #           currency_str="EUR", 
        #           commodity_isin="", commodity_fullname="", commodity_namespace="")

        value = 11.1
        date = datetime.datetime(2020, 1, 1)
        isin = get_commodity_isin(1)
        
        # 1 Added by ISIN: namespace=NO, currency=YES
        comm, added = script.add_price(self.book, value, date, 
            currency_str="EUR", commodity_isin=isin)  
        self.assertTrue(added, "add_price.1 Skipped unexpected!")
        self.assertEqual(comm.get_cusip(), isin)

        # 2 Skipped by ISIN:  namespace=NO, currency=YES
        comm, added = script.add_price(self.book, value, date, 
            currency_str="EUR", commodity_isin=isin)  
        self.assertFalse(added, "add_price.2 Added unexpected!")
        self.assertEqual(comm.get_cusip(), isin)

        # 3 Skipped by ISIN: namespace=YES, currency=NO
        comm, added = script.add_price(self.book, value, date, 
            commodity_isin=isin, commodity_namespace=COMMODITY_NAMESPACE)  
        self.assertFalse(added, "add_price.3 Added unexpected!")
        self.assertEqual(comm.get_cusip(), isin)

        # 4 Skipped by ISIN: namespace=YES, currency=NO
        value = 11.2
        with self.assertRaises(ValueError):
            script.add_price(self.book, value, date, 
                commodity_isin=isin, commodity_namespace=COMMODITY_NAMESPACE)  

        #  Error by ISIN
        isin = "UNKNOWN"
        with self.assertRaises(LookupError):
            script.add_price(self.book, value, date, commodity_isin=isin)


    def test_add_price_by_fullname(self):
        # add_price(book, value, date, 
        #           currency_str="EUR", 
        #           commodity_isin="", commodity_fullname="", commodity_namespace="")

        value = 22.2
        date = datetime.datetime(2020, 2, 2)
        fullname = get_commodity_fullname(2)
        
        # 1 Added: namespace=NO, currency=YES
        comm, added = script.add_price(self.book, value, date, 
            currency_str="EUR", commodity_fullname=fullname)  
        self.assertTrue(added, "1 Skipped unexpected!")
        self.assertEqual(comm.get_fullname(), fullname)

        # 2 Skipped: namespace=NO, currency=YES
        comm, added = script.add_price(self.book, value, date, 
            currency_str="EUR", commodity_fullname=fullname)  
        self.assertFalse(added, "2 Added unexpected!")
        self.assertEqual(comm.get_fullname(), fullname)

        # 3 Skipped: namespace=YES, currency=NO
        comm, added = script.add_price(self.book, value, date, 
            commodity_fullname=fullname, commodity_namespace=COMMODITY_NAMESPACE)  
        self.assertFalse(added, "3 Added unexpected!")
        self.assertEqual(comm.get_fullname(), fullname)

        # 4 Skipped: namespace=YES, currency=NO
        value = 22.25
        with self.assertRaises(ValueError):
            script.add_price(self.book, value, date, 
                commodity_fullname=fullname, commodity_namespace=COMMODITY_NAMESPACE)  

        #  Error
        fullname = "UNKNOWN"
        with self.assertRaises(LookupError) as cm:
            script.add_price(self.book, value, date, commodity_fullname=fullname)
        # print(cm.exception)

    def test_do_insert_prices(self):
        # def do_insert_new_prices(book, quotes):
        #     # Date: 2020-09-11T00:00:00+02:00
        #     # Isin: 
        #     # StockName:
        #     # Price: 
        #     # Currency: default "EUR"
        #     # Namespace: default ""

        # class quote:
        #     def __init__(self, n, date, price):
        #         self.Date = date
        #         self.Isin = get_commodity_isin(n)
        #         self.StockName = get_commodity_fullname(n)
        #         self.Price = price

        def quote(iter):
            return {
                "Date": datetime.datetime(2020,3,iter,  tzinfo=datetime.timezone.utc).isoformat(),
                "Isin": get_commodity_isin(3),
                "Price": 33.0 + iter/10.0,
            }

        # create the list of quotes
        quotes = []
        for i in range(1, 6):
            quotes.append( quote(i) )

        # skipped
        quotes.append( quote(1) )

        with patch('sys.stdout', new = StringIO()) as fake_out: 
            errs = script.do_insert_prices(self.book, quotes)
            self.assertEqual(errs, 0)


    def test_insert_prices_err_gnucash_file_not_found(self):
        gnucash_file = FILE_PREFIX + "-UNKNOWN.gnucash"
        json_file = FILE_PREFIX + "-UNKNOWN.json"

        with patch('sys.stdout', new = StringIO()) as fake_out: 
            script.insert_prices(gnucash_file, json_file)
            self.assertRegex( fake_out.getvalue(), "gnucash_file not found") 


    def test_insert_prices_err_json_file_not_found(self):
        gnucash_file = FILE_PREFIX + "1.gnucash"
        json_file = FILE_PREFIX + "-UNKNOWN.json"

        ses = init_gnucash_file(gnucash_file)
        ses.save()
        ses.end()

        with patch('sys.stdout', new = StringIO()) as fake_out: 
            script.insert_prices(gnucash_file, json_file)
            self.assertRegex( fake_out.getvalue(), "json_file not found") 


    def test_insert_prices_err_reading_json_file(self):
        gnucash_file = FILE_PREFIX + "2.gnucash"
        json_file = FILE_PREFIX + "2.json"

        ses = init_gnucash_file(gnucash_file)
        ses.save()
        ses.end()        

        f = open(json_file, 'w+')
        f.write('[\n')
        f.write('{"Isin": "ISIN00009999", "Date": "2020-09-10T00:00:00+02:00", "Price": 25.62},\n')
        f.write('INVALID JSON LINE\n')
        f.write(']\n')
        f.close()

        with patch('sys.stdout', new = StringIO()) as fake_out: 
            script.insert_prices(gnucash_file, json_file)
            self.assertRegex( fake_out.getvalue(), "Error reading json file") 


    def test_insert_prices_err_updating_gnucash_file(self):
        gnucash_file = FILE_PREFIX + "3.gnucash"
        json_file = FILE_PREFIX + "3.json"

        ses = init_gnucash_file(gnucash_file)
        ses.save()
        ses.end()

        f = open(json_file, 'w+')
        f.write('[\n')
        f.write('{"Isin": "ISIN00000001", "Date": "2020-09-10T00:00:00+02:00", "Price": 12.34}\n')
        f.write(']\n')
        f.close()

        with patch('sys.stdout', new = StringIO()) as fake_out: 
            script.insert_prices(gnucash_file, json_file)
            self.assertRegex( fake_out.getvalue(), "Error updating gnucash file") 


    def test_insert_prices_ok_json_from_stdin(self):
        gnucash_file = FILE_PREFIX + "4.gnucash"
        json_file = FILE_PREFIX + "4.json"

        ses = init_gnucash_file(gnucash_file)
        ses.save()
        ses.end()

        f = open(json_file, 'w+')
        f.write('[\n')
        f.write('{"Isin": "' + get_commodity_isin(1) + '", "Date": "2020-10-28T00:00:00+02:00", "Price": 25.62}\n')
        f.write(']\n')
        f.close()


        with patch('sys.stdout', new = StringIO()) as fake_out: 
            sys.stdin = open(json_file, 'r')
            script.insert_prices(gnucash_file, None)
            
            self.assertRegex( fake_out.getvalue(), "ADD : \(commodity=TEST00000001, price=25.620 EUR, date=") 
            # print(fake_out.getvalue())

    def test_insert_prices_no_json_from_stdin(self):
        gnucash_file = FILE_PREFIX + "5.gnucash"

        ses = init_gnucash_file(gnucash_file)
        ses.save()
        ses.end()

        with patch('sys.stdout', new = StringIO()) as fake_out: 
            script.insert_prices(gnucash_file, None)
            
            self.assertRegex( fake_out.getvalue(), "Error: json expected from file or stdin") 
            # print(fake_out.getvalue())


if __name__ == '__main__':
    unittest.main()