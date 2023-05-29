## Importing modules

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import random as rd
import strategy_scalp_indices as ssi
import threading as thd
import time
import queue
from datetime import datetime
from time import sleep
from itertools import product
from statistics import mode
from opt_function_V3 import optimize
from math import sqrt


"""
If auto has value 1 then it automatically connect you to the last used account.
Otherwise, it extracts the data contained in a file .txt located in <directory> with the following format :
    <login>;<password>;<server>
    
directory = "<name of the directory from the root to the the file>"
file = "\<name of file>.txt"
"""

auto = 1
directory = "C:\Documents\Finance"
file = "\connector.txt"

LIST_SYMBOL = ["[NQ100]"]
LIST_VOLUME = [3.0]
timeframe = mt5.TIMEFRAME_M5
long_ma_period = 100
rsi_period = 14

results_queue = queue.Queue()

def process_input():
    while True:
        # Récupérez un input de la liste
        try:
            input = inputs.pop(0)
        except IndexError:
            # Si la liste est vide, terminez le thread
            break

        # Exécutez la fonction sur l'input
        result = function(input)

        # Placez le résultat dans la file d'attente
        results_queue.put(result)


# Créez des threads pour chaque input
threads = []
for _ in inputs:
    thread = threading.Thread(target=process_input)
    threads.append(thread)
    thread.start()

# Attendez que tous les threads se terminent
for thread in threads:
    thread.join()

# Récupérez les résultats de la file d'attente
results = []
while not results_queue.empty():
    result = results_queue.get()
    results.append(result)

# Faites quelque chose avec les résultats obtenus
# Par exemple, imprimez-les
for result in results:
    print(result)

# Vous pouvez répéter le processus toutes les 2 secondes
while True:
    time.sleep(2)

    # Réexécutez les threads avec les nouveaux inputs
    threads = []
    for _ in inputs:
        thread = threading.Thread(target=process_input)
        threads.append(thread)
        thread.start()

    # Attendez que tous les threads se terminent
    for thread in threads:
        thread.join()

    # Récupérez les résultats de la file d'attente et traitez-les
    results = []
    while not results_queue.empty():
        result = results_queue.get()
        results.append(result)

    # Faites quelque chose avec les résultats obtenus à chaque instance
    # Par exemple, imprimez-les
    for result in results:
        print(result)

if __name__ == '__main__':
    
    n = len(LIST_SYMBOL)
    m = len(LIST_VOLUME)
    
    if n != m :
        ssi.close_positions('all')
    else :
        for i in range(n) :
            ssi.execute_strategy(symbol, volume, timeframe, long_ma_period, rsi_period, auto, directory, file)
if not __name__ == '__main__': ## Close all positions when closing it
    close_positions('all')

