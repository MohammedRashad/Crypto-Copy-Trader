from flask import Flask, Response, render_template
from threading import Thread
from time import sleep
from main import *

app = Flask(__name__)

stop_run = False


def my_function(client, slaves, old_orders):
    print("I'm in thread #1 ")
    global stop_run
    start_time = time.time()
    while not stop_run:
        old_orders = looping_engine(client, slaves, old_orders)
        end = time.time()
        print ("time elasped in thread 1 = " + str(end - start_time)+ " sec")


def my_function2(file_name,client, slaves, old_orders, Thread_num):
    print("I'm in thread #" + Thread_num)
    global stop_run
    start_time = time.time()
    while not stop_run:
        copy_market(client, slaves, file_name)
        end = time.time()
        print ("time elasped in thread" + Thread_num + " = " + str(end - start_time)+ " sec")

def manual_run():
    client, slaves, old_orders = server_begin()
    t1 = Thread(target=my_function ,args=(client, slaves, old_orders,))
    t2 = Thread(target=my_function2, args=("config_files/symbols.csv",client, slaves, old_orders, "2"))
    t3 = Thread(target=my_function2, args=("config_files/symbols2.csv",client, slaves, old_orders, "3"))
    t4 = Thread(target=my_function2, args=("config_files/symbols3.csv",client, slaves, old_orders,"4"))
    t5 = Thread(target=my_function2, args=("config_files/symbols4.csv",client, slaves, old_orders,"5"))

    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()

    return "Processing"


@app.route("/stop", methods=['GET'])
def set_stop_run():
    global stop_run
    stop_run = True
    return render_template("home.html" , isRunning="Application Stopped")


@app.route("/run", methods=['GET'])
def run_process():
    global stop_run
    stop_run = False
    manual_run()
    return render_template("home.html" , isRunning="Application Running")

@app.route('/')
def homepage():
    return render_template("home.html" , isRunning= "Application Stop running Status : " +  str(stop_run))


if __name__ == "__main__":
    app.run(debug=True)