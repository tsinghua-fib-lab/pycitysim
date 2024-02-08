from pycitysim.urbankg import UrbanKG

kg = UrbanKG(
    mongo_uri="mongodb://username:password@url:port/",
    mongo_db="opencity",
    mongo_entity_coll="urban_kg_entity",
    mongo_relation_coll="urban_kg_relation",
    cache_size=100,
)

print(kg.CLASSES)
print(kg.RELATIONS)
print("==================")
print(kg.get_entity("POI_10000010724897277135"))
print("==================")
print(kg.query_object("POI_10000010724897277135", "LocateAt"))
print("==================")
print(kg.query_subject("Cate3_111000", "Cate3Of"))
print("==================")
print(kg.explore("POI_10000010724897277135", kg.RELATIONS))
