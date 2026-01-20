import pandas as pd
import matplotlib.pyplot as plt
import src.config as config
import src.database as database
from parse_mysql_dump import *

data = convert_dump_to_json("RA.sql", "RA.json")
imei_objetivo = config.IMEI["519"]
date_start = '2025-12-30 11:00:00'
date_end = '2025-12-30 13:10:00'
metric_p = "diastolic_blood_pressure"
metric_hr = "heart_rate"
metric_oxsat = "blood_oxygen_saturation"
metric_t = "temperature"

d_pressure = database.get_data(metric_p, imei_objetivo, date_start, date_end)
database.show_dpressure(d_pressure)

h_rate = database.get_data(metric_hr, imei_objetivo, date_start, date_end)
database.show_hrate(h_rate)

oxsat = database.get_data(metric_oxsat, imei_objetivo, date_start, date_end)
database.show_oxsat(oxsat)

temp = database.get_data(metric_t, imei_objetivo, date_start, date_end)
database.show_temperature(temp)

plt.show()