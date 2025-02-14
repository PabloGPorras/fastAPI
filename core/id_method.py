import os
from time import strftime
import random


def id_method():
    unique_ref = str(os.getlogin()).upper() + "-" + strftime("%Y%m%d%H%M%S") + str(random.randint(10000, 99999))
    return unique_ref