from binance.client import Client
from time import sleep, time
from sys import exit
from datetime import datetime
from csv import reader
import json
import pprint
from deepdiff import DeepDiff
import time
from ExchangeInterfaces.BinanceExchange import BinanceExchange
from SlaveContainer import SlaveContainer

import numpy as np
# import pandas as pd
import sqlite3 as sql


############################################
## -- Helper Functions
############################################


def create_slave_order(order, slave, client):
    # This function is responsible for the creation of new slave orders whenever requested
    # Takes as input orders list and slaves lists, and creates orders for them
    part = client.get_part(order['symbol'], order['origQty'], order['price'], order['side'])

    if (order['type'] == 'STOP_LOSS_LIMIT' or order['type'] == "TAKE_PROFIT_LIMIT"):
        slave.create_order(symbol=order['symbol'],
                           side=order['side'],
                           type=order['type'],
                           price=order['price'],
                           quantityPart=part,
                           timeInForce=order['timeInForce'],
                           stopPrice=order['stopPrice'], )
    elif (order['type'] == 'MARKET'):
        slave.create_order(symbol=order['symbol'],
                           side=order['side'],
                           type=order['type'],
                           quantity=part, )
    else:
        slave.create_order(symbol=order['symbol'],
                           side=order['side'],
                           type=order['type'],
                           quantityPart=part,
                           price=order['price'],
                           timeInForce=order['timeInForce'], )
    print('order copied')


def copy_trade(orders, slaves, client, old_orders=None):
    ## This is the main copy trading function managing all the operations happening
    ## doesn't track old orders in the first run of course
    print('in copy')
    if old_orders is None:
        print('first time')
        for order in orders:
            print('-- orders first time --')
            print('----------------------')
            for slave in slaves:
                print('-- slaves first time--')
                create_slave_order(order, slave, client)
        old_orders = orders.copy()
        return old_orders
    else:
        print('nth time')
        for order in orders:
            if not (order in old_orders):
                print('-- orders nth time --')
                print('----------------------')
                for slave in slaves:
                    create_slave_order(order, slave, client)
        old_orders = orders.copy()
        return old_orders


def order_cancel_checker(i_orders, i_old_orders, i_slaves):
    ## order cancel checker
    diff = DeepDiff(i_orders, i_old_orders)
    if bool(diff):
        for slave in i_slaves:
            slave_open_orders = slave.get_open_orders()
            for ordr_open in slave_open_orders:
                for order in i_old_orders:
                    if ((ordr_open['price'] == order['price']) and (ordr_open['symbol'] == order['symbol'])) and not (
                            order in i_orders):
                        slave.cancel_order(symbol=ordr_open['symbol'], orderId=ordr_open['orderId'])


def server_begin():
    ############################################
    ## -- Server Preparation
    ############################################
    print('Application started...')
    with open('./config_files/config.json', 'r') as config_f:
        config = json.load(config_f)

    print('Reading configuration file...')
    print(len(config['slaves']), ' Slave accounts detected')

    file = open('config_files/symbols.csv', "r")
    symbols = file.readlines()

    slave_container = SlaveContainer(config, symbols)

    client = slave_container.master

    print('')
    print('Get Master Orders...')
    orders = client.get_open_orders()
    pprint.pprint(str(orders))
    print('Opening Slave Accounts...')

    slaves = slave_container.slaves
    slave_number = 0
    for slave in slaves:
        slave_open_orders = slave.get_open_orders()
        print('')
        print('Opening Slave Account #' + str(slave_number) + ' ...')
        print('')
        print('Get Slave Orders...')

        pprint.pprint(slave_open_orders)
        slave_number += 1
        print('')

    print('Will start copying from now...please place a new order')
    print('')

    print('Open Master Orders are ' + str(len(orders)) + ' ...')

    slave_container.first_copy(orders)
    #old_orders = copy_trade(orders, slaves, client=client)

    return slave_container


def looping_engine(client, slaves, old_orders):
    orders = client.get_open_orders()
    order_cancel_checker(orders, old_orders, slaves)
    print('Open Master Orders are ' + str(len(orders)) + ' ...')

    old_orders = copy_trade(orders, slaves, old_orders=old_orders, client=client)
    print("Sleeping...")
    time.sleep(3)
    return old_orders


def copy_market(client, slaves, file_name):
    symbols = []
    print("getting symbols..")
    file = open(file_name, "r")
    symbols = file.readlines()

    print("getting orders..")
    orders_to_exec = []
    for symbol in symbols:
        orders = client.get_all_orders(symbol=symbol.replace("\n", ""), limit=1)
        print(symbol)
        for order in orders:
            if order["type"] == 'MARKET' and order["time"] > (int(time.time()) - 60 * 5000):
                print("making order..")
                copy_trade([order], slaves, client=client)
        time.sleep(3)

# ###########################################
# # -- First Run
# ###########################################

# client, slaves, old_orders = server_begin()

# ############################################
# ## -- Other Runs
# ############################################

# while True :
#    old_orders = looping_engine(client, slaves, old_orders)
#    copy_market(client, slaves, "config_files/symbols.csv")
