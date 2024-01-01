from pycitysim.streetview import StreetViews

sv = StreetViews(
    mongo_uri="mongodb://sim:FiblabSim1001@mgo.db.fiblab.tech:8635/",
    mongo_db="llmsim",
    mongo_coll="street_view",
    obs_ak="FYQ5GMIRA0GYZR6ODF5O",
    obs_sk="AIJhZFvdDvq8pMYMYckak1TENjG8wwVzl01wpDVO",
    obs_endpoint="obs.cn-north-4.myhuaweicloud.com",
    obs_bucket="fiblab-llmsim-streetview",
)

all = sv.query((116.322, 39.983), 100)
print(all)
