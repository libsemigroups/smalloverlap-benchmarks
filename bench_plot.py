#!/usr/bin/env python3

import os
import re
import sys
from math import log

import matplotlib
import numpy as np
from bs4 import BeautifulSoup
from matplotlib import pyplot as plt

matplotlib.rcParams["mathtext.fontset"] = "stix"
matplotlib.rcParams["font.family"] = "STIXGeneral"

# Filenames should be: name.something.xml -> name.png


def normalize_xml(xml_fnam):
    with open(xml_fnam, "r") as f:
        xml = f.read()
        xml = re.sub("&lt;", "<", xml)
        xml = re.sub("{{", "[", xml)
        xml = re.sub("}}", "]", xml)
    with open(xml_fnam, "w") as f:
        f.write(xml)


def xml_stdout_get(xml, name):
    try:
        return xml.find("StdOut").find(name)["value"]
    except (KeyError, TypeError, NameError, AttributeError):
        print("No label {} in StdOut element, skipping . . .".format(name))
        return None


def time_unit_from_data_in_ns(Y):
    threshold = lambda Y: len([y for y in Y if y > 1000]) > 0.80 * len(Y)
    time_units = ("nanoseconds", "microseconds", "milliseconds", "seconds")
    index = 0

    while threshold(Y) and index < len(time_units):
        index += 1
        Y = [y / 1000 for y in Y]
    return time_units[index], Y


def convert_time_unit_from_data_in_ns(t, Y):
    if t == "nanoseconds":
        return Y
    elif t == "microseconds":
        return [y / 10 ** 3 for y in Y]
    elif t == "milliseconds":
        return [y / 10 ** 6 for y in Y]
    elif t == "seconds":
        return [y / 10 ** 9 for y in Y]


def get_y_data(xml_fnam):
    normalize_xml(xml_fnam)
    xml = BeautifulSoup(open(xml_fnam, "r"), "xml")
    results = xml.find_all("BenchmarkResults")

    data = xml_stdout_get(xml, "Data")

    if data is None:
        yfunc = lambda x, y: y
    else:
        data = eval(data)
        if isinstance(data, list):
            yfunc = lambda x, y: y / data[x]
        elif isinstance(data, int):
            yfunc = lambda x, y: y / data
        else:
            raise RuntimeError(
                "The <Data> tag should contain a list or an integer"
            )
    # We do the following so that we can make graphs even when the output XML
    # is not complete
    Y = []  # times in nanoseconds
    for x, xml in enumerate(results):
        if xml.find("mean") is not None:
            Y.append(yfunc(x, float(xml.find("mean")["value"])))
    return Y


def get_time_unit(xml_fnam, tu):
    t, Y = time_unit_from_data_in_ns(get_y_data(xml_fnam))
    time_units = ("nanoseconds", "microseconds", "milliseconds", "seconds")
    if tu is None:
        return t
    if time_units.index(t) > time_units.index(tu):
        return t
    return tu


def add_plot(xml_fnam, tu):
    normalize_xml(xml_fnam)

    xml = BeautifulSoup(open(xml_fnam, "r"), "xml")
    results = xml.find_all("BenchmarkResults")

    # Benchmark labels must be the value that is the x-axis

    title = xml_stdout_get(xml, "Title")
    xlabel = xml_stdout_get(xml, "XLabel")
    ylabel = xml_stdout_get(xml, "YLabel")
    label = xml_stdout_get(xml, "Label")

    X = [int(x["name"]) for x in results]
    Y = get_y_data(xml_fnam)  # times in nanoseconds
    X = X[: len(Y)]

    assert tu is not None

    tu, Y = tu, convert_time_unit_from_data_in_ns(tu, Y)

    Xl = [log(x) for x in X]
    Yl = [log(y) for y in Y]

    b, a = np.polyfit(Xl, Yl, deg=1)
    print("Growth rate is O(x ^ {}) for {}".format(b, xml_fnam))

    plt.plot(X, Y, "x", label=label)
    if title is not None:
        plt.title(title)
    if xlabel is not None:
        plt.xlabel(xlabel)
    if ylabel is not None:
        plt.ylabel(ylabel + " " + tu)
    else:
        plt.ylabel("Time in {}".format(t))
    if label is not None:
        plt.legend(loc="upper left")


from sys import argv

args = sys.argv[1:]
# TODO arg checks
# First determine the most fine grained time unit
tu = None
for x in args:
    print("Reading {} . . .".format(x))
    tu = get_time_unit(x, tu)
print("Time unit is {} . . .".format(tu))

for x in args:
    add_plot(x, tu)
xml_fnam = args[0]
png_fnam = "".join(xml_fnam.split(".")[:-2]) + ".png"
print("Writing {} . . .".format(png_fnam))
plt.savefig(png_fnam, format="png", dpi=300)
sys.exit(0)
