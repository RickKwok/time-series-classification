import pandas as pd
import sys, os, csv
import collections
import math
import matplotlib.pyplot as plt
import random
import re
import requests
import numpy as np
from datetime import datetime
from collections import Counter
from sklearn.cluster import KMeans

URL_REGEX = re.compile('https.+github.+')
DTW_WIDTH = 5
git_headers = {'Authorization': 'token %s' % os.environ['GITHUB']}
ROOT_URL = 'https://api.github.com/repos/expertiza/expertiza/pulls/'


# Filter the urls of the pull requests and store into list.

def get_url_list():
    url_list = []
    with open('pull_requests', 'rb') as f:
        for line in f:
            line = line.strip()
            if URL_REGEX.match(line):
                url_list.append(line)

    return url_list


# Interacting with Github API by making get requests from the urls.
def read_series(url):
    # files_url = url + "/files"
    commits_url = url + "/commits?500"

    date = []

    r_commits = requests.get(commits_url, headers=git_headers).json()
    # r_files = requests.get(files_url, headers=git_headers).json()

    for c in r_commits:
        try:
            date.append(c["commit"]["author"]["date"])
        except TypeError:
            print ("url: " + c + ", has problem.")
            continue

    for i in range(0, len(date)):
        date[i] = datetime.strptime(date[i][:10], "%Y-%m-%d")

    dict_hash = Counter(date)
    # base = datetime(2016, 11, 9)
    # end = datetime(2016, 12, 16)

    # Stretch the timeframe into project period/ 35 days.
    date_list = pd.date_range('2016-11-9', periods=35, freq='D')

    for i in date_list:
        i = i.to_pydatetime()
        if i in dict_hash.keys():
            continue
        else:
            dict_hash[i] = 0

    # sort {date : num_commits} hash into ascending date order.

    dict_hash = collections.OrderedDict(sorted(dict_hash.items()))
    return dict_hash.values()


# A "Git PR link" ---> Return # of files have changed.
def read_num_files_changed(git_link):
    num = 0
    for x in git_link.split('/'):
        if x.isdigit():
            num = x
    link = ROOT_URL + num
    files_url = link + "/files"
    r_files = requests.get(files_url, headers=git_headers).json()
    num_files_changed = len(r_files)
    return num_files_changed


# Calculate similarity between two time series. Using Dynamic Time Wrapping.

def dtw_distance(s1, s2, w):
    DTW = {}
    w = max(w, abs(len(s1) - len(s2)))

    for i in range(-1, len(s1)):
        for j in range(-1, len(s2)):
            DTW[(i, j)] = float('inf')
    DTW[(-1, -1)] = 0

    for i in range(len(s1)):
        for j in range(max(0, i - w), min(len(s2), i + w)):
            dist = (int(s1[i]) - int(s2[j])) ** 2
            DTW[(i, j)] = dist + min(DTW[(i - 1, j)], DTW[(i, j - 1)], DTW[(i - 1, j - 1)])

    return math.sqrt(DTW[len(s1) - 1, len(s2) - 1])


# Using LB_Keogh to Optimize DTW efficiency.

def LB_Keogh(s1, s2, r):
    LB_sum = 0
    for ind, i in enumerate(s1):

        lower_bound = min(s2[(ind - r if ind - r >= 0 else 0):(ind + r)])
        upper_bound = max(s2[(ind - r if ind - r >= 0 else 0):(ind + r)])

        if i > upper_bound:
            LB_sum = LB_sum + (i - upper_bound) ** 2
        elif i < lower_bound:
            LB_sum = LB_sum + (i - lower_bound) ** 2

    return math.sqrt(LB_sum)

# k_means clustering
# def k_means_clust(data, num_clust, num_iter, w=5):
#     centroids = random.sample(data, num_clust)
#     counter = 0
#     for n in range(num_iter):
#         counter += 1
#         print(counter)
#         assignments = {}
#         # assign data points to clusters
#         for ind, i in enumerate(data):
#             min_dist = float('inf')
#             closest_clust = None
#             for c_ind, j in enumerate(centroids):
#                 if LB_Keogh(i, j, 5) < min_dist:
#                     cur_dist = dtw_distance(i, j, w)
#                     if cur_dist < min_dist:
#                         min_dist = cur_dist
#                         closest_clust = c_ind
#             if closest_clust in assignments:
#                 assignments[closest_clust].append(ind)
#             else:
#                 assignments[closest_clust] = []
#
#         # recalculate centroids of clusters
#         for key in assignments:
#             clust_sum = 0
#             for k in assignments[key]:
#                 clust_sum = clust_sum + data[k]
#             centroids[key] = [m / len(assignments[key]) for m in clust_sum]
#
#     return centroids