
import xml.etree.cElementTree as ET
from collections import defaultdict
from pymongo import MongoClient
import pprint
import re
import codecs
import json
from __future__ import division

file_in = "milan_italy"

tree = ET.parse("{0}.osm".format(file_in))
root = tree.getroot()


'''
######## initial overview ########
'''

## tags
# create a dictionary including as keys all the possible tag values and as values their frequency in the whole file.
# cleaned is an optional argument allowing to include tags in the dictionary after removing ":" and everything that follows
# LowBound allows for including in the dictionary only those tags whose frequency is larger than a certain threshold. 
# So, that if we decide to clean the tag values from the ":" and create nested dictionaries we can decide to do that only if their presence is considered relevant

def cleaner(element):
	temp = element.partition(':')[0]
	return temp

def key_dict(root, cleaned = 0, LowBound = 0): 
	key_counter = defaultdict(int)
	selected = defaultdict(int)
	for node in root:
		for val in node.iter('tag'):
			if (cleaned == 1 and ':' in val.attrib['k']):
				element = cleaner(val.attrib['k'])
				selected[element] += 1
			else:
				element = val.attrib['k']
			
			key_counter[element] += 1
			
	final = dict((k, v) for k, v in key_counter.items() if (v >= LowBound))
	selected = dict((k, v) for k, v in selected.items() if (v >= LowBound))
	return final, selected

keys_dict_raw = key_dict(root)
keys_dict_refined, selected = key_dict(root, cleaned = 1, LowBound = 1000)

# clearer way to display keys and decide what to fix according to frequency

pprint.pprint(keys_dict_raw, indent=4)
pprint.pprint(keys_dict_refined, indent=4)
pprint.pprint(selected, indent=4)


# most frequent tags
# {'comment': 1418, 'building': 5683, 'addr': 116996, 'colour': 1107, 'source': 1236, 'contact': 1034, 'parking': 2196, 'mtb': 1115, 'name': 2107}

# there are several cases of abbreviated keys followed by ':'. i will try to substitute 'name:blahblah' with 'name:' in a programmatic way
# i will also created nester dictionaries for "contact" and "addresses"


### quick glance at contact attributes values
def test(root):
	for node in root:
		# print node.tag # allows me to understand whether is a 'way' or a 'node'
		for val in node.iter('tag'):
			if re.search(r'contact:\w+', val.attrib['k']):
				print val.attrib['k'], '====>', val.attrib['v']
	return 


### control for irregular postcodes length
def postcode_dict(root):
	post_dict = defaultdict(int)
	for node in root:
		for val in node.iter('tag'):
			if (val.attrib['k'] == 'addr:postcode'):	# if we want to isolate postcodes to be removed simple include "and len(val.attrib['v']) <> 5" 
				print val.attrib['k'], '====>', val.attrib['v']
				post_dict[val.attrib['v']] += 1
	post_dict = dict(post_dict)
	return post_dict

postcode = postcode_dict(root)

### Allows me to get an idea of how many postcodes are in Milan (201##). 
# The number of postcodes from Milan is consistently lower than the one from Monza, a very strange result given that Milan is consistently larger.
def sum_postcode_milan(dict):
	sum = 0
	for k, v in dict.iteritems():
		if re.search(r'201\w+', k):
			sum += v
	return sum

postcode_milan = sum_postcode_milan(postcode)

### I control for irregular street names
def streetname_dict(root):
	street_dict = defaultdict(int)
	for node in root:
		# print node.tag # allows me to understand whether is a 'way' or a 'node'
		for val in node.iter('tag'):
			if (val.attrib['k'] == 'addr:street'):
				street = val.attrib['v']
				street_init = street.partition(' ')[0]
				print val.attrib['k'], '====>', val.attrib['v']
				street_dict[street_init] += 1
	street_dict = dict(street_dict)
	return street_dict

street_init = streetname_dict(root)

### I control for irregular phone numbers
def phonenumber_dict(root):
	phone_dict = defaultdict(int)
	for node in root:
		# print node.tag # allows me to understand whether is a 'way' or a 'node'
		for val in node.iter('tag'):
			if (val.attrib['k'] == 'contact:phone' and len(str(val.attrib['v'])) <> 14 ):
				print val.attrib['k'], '====>', val.attrib['v']
				phone_dict[val.attrib['v']] += 1
	phone_dict = dict(phone_dict)
	return phone_dict

phone_dict = phonenumber_dict(root)

# all the numbers included have a corpo ranging from 4 to 7 digits, therefore they look like regular

'''
 Quality cleaning
'''

# 1) street names
# given the great variability in types of adressess it was not possible to define the set of "good" types and control if the analysed one was included.
# so after assessing all the types used i defined a set including the bad ones. So, that it was possible to test whether the analysed one was included or not.

bad = ["C.na", "S.P.208", "VIA" , "piazza", "via", "vial", "piazza", "Ingresso" ]

mapping = { "C.na" : "Cascina",
			"S.P.208" : "SP",
			"VIA" : "Via",
			"piazza" : "Piazza",
			"via" : "Via",
			"vial" : "Viale",
            "piazza" : "Piazza",
            "Ingresso" : "Ingresso"
            }
 
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
    	
# 2) postcode, necessary to remove all the irregular postcodes, the ones with more or less than 5 digits

# the function below substitutes the misspelled values with the correct ones
def value_cleaner(element, mapping):
	streetName = element.attrib['v']
	streetInit = streetName.partition(' ')[0]
	recover = len(streetInit)
	preserved = streetName[recover:] 
	if (element.attrib['k'] == 'addr:street' and streetInit in bad):
		Substitute = mapping[streetInit]
		betterValue = Substitute + preserved
	elif (element.attrib['k'] == 'addr:postcode' and len(element.attrib['v']) <> 5):
		betterValue = None
	else:
		betterValue = element.attrib['v']
		
	return betterValue

# control for dots and problematic characters in the tags considered
def dot_scanner(element):
		return re.search(problemchars, element) <> None

# the function below clean the tag value in the case of addresses and contact, while remove the whole string component after ":" in the other cases
def key_cleaner(element):
	if (element.attrib['k'][:5] == "addr:" and not (":" in element.attrib['k'][5:])):
		betterKey = element.attrib['k'][5:]
	elif element.attrib['k'][:8] == "contact:":
		betterKey = element.attrib['k'][8:] 
	elif dot_scanner(element.attrib['k']):
		control = re.search(problemchars, element.attrib['k'])
		badguy = control.group()
		if badguy == '.':
			newkey = element.attrib['k']
			betterKey = newkey.replace('.', ':')
		else:
			newkey = element.attrib['k']
			betterKey = newkey.replace(badguy, '_')									
	else:
		betterKey = element.attrib['k']
		
	return betterKey			
					
# for each node tags and values are cleaned save as a dictionary
def audit(element):
	node = {}
	address_list = {}
	contact_list = {}
	node_refs = []
	if (element.tag == "node" or element.tag == "way" or element.tag =="relation"):
		node["id"] = element.attrib["id"]
		node["type"] = element.tag
	
		if "lat" in element.attrib:
			node["pos"] = [float(element.attrib['lat']), float(element.attrib['lon'])]
		
		node["created"] = {
							"version": element.attrib['version'],
							"changeset": element.attrib['changeset'],
							"timestamp": element.attrib['timestamp'],
							"user": element.attrib['user'],
							"uid": element.attrib['uid']
							}
		
		for tag in element.iter("tag"):
			betterValue = value_cleaner(tag, mapping)
			betterKey = key_cleaner(tag)
			
			if (tag.attrib['k'][:5] == "addr:" and not (":" in tag.attrib['k'][5:])):
				address_list[betterKey] = betterValue
			elif tag.attrib['k'][:8] == "contact:":
				contact_list[betterKey] = betterValue									
			else:
				node[betterKey] = betterValue
			
		for tag in element.iter("nd"):
			node_refs.append(tag.attrib['ref'])        	
		
		if len(node_refs) <> 0:
			node["node_refs"] = node_refs            
		if len(address_list) <> 0:
			node["address"] = address_list
		if len(address_list) <> 0:
			node["contact"] = contact_list            		
		
		return node
	
	else:
		return None
    	
# the function below creates the json file
def process_map(root, pretty = False):
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for element in root:
            el = audit(element)
            if el:
                data.append(el)
                if pretty:
                	fo.write(json.dumps(el, indent=2)+"\n")
                else:
                	fo.write(json.dumps(el) + "\n")
    return data            		
 

data = process_map(root, pretty = False)
     
# load the data into Mongodb    
def insert_data():
	data = process_map(root, pretty = False)
	print "start inserting data"
	client = MongoClient()
	db = client.OpenMaps  		# a new database including works related to OpenMaps is created	
	db.Milan.insert(data) 		# a new collection for the Milan project is created
	
	return 

# now that the collection is ready, we can run basic analysis!

'''
file sizes:
	milan.osm 549 mb
	milan.json 625 mb
'''

db = client.OpenMaps
collection = db.Milan

## Number of documents
collection.find().count()                                                
# 4766245
                                      
## Number of nodes
nodes = collection.find({"type":"node"}).count()
print nodes
# 4383822

## Number of ways
collection.find({"type":"way"}).count()
# 371559
                                               
## Number of unique users
DistUser = collection.distinct("created.user")
len(DistUser)
# 1724
                                              
## Top 1 contributing user
def ContributorExtr(n):
	contributor = collection.aggregate([{"$group" : {"_id" : "$created.user", "count" : {"$sum" : 1}}}, 
											{ "$sort" : { "count" : -1} },
											{"$limit" : n}])                                              
	contributor = list(contributor)
	
	return contributor

topContributor = ContributorExtr(1)
print topContributor 
# [{u'count': 599526, u'_id': u'ilrobi'}]

                                                
## Number of users appearing only once (having 1 post)
uniqueContribution = collection.aggregate([{"$group" : {"_id" : "$created.user", "count" : {"$sum" : 1}}}, 
											{"$group" : {"_id" : "$count", "num_users" : {"$sum" : 1}}}, 
											{"$sort" : {"_id" : 1}}, 
											{"$limit" : 1}])

uniqueContribution = list(uniqueContribution)
print uniqueContribution
# [{u'num_users': 131, u'_id': 1}]

## top two users
topTwoContributor = ContributorExtr(2)

## top ten users
topTenContributor = ContributorExtr(10)

## contributors distribution
def Contribution(list):
	FinalSum = 0
	for i in range(len(list)):
		print list[i]['count']
		FinalSum += list[i]['count']
	
	return FinalSum

firstTwo = Contribution(topTwoContributor)
firstTen = Contribution(topTenContributor)

firstShare = topcontributor[0]['count']/nodes
# 13.67%

firstTwoShare = firstTwo/nodes
# 25.69% 

firstTenShare = firstTen/nodes
# 59.93%

complete = ContributorExtr(1724)
onepercent = 0.01*float(nodes)


final = 0
counter = 0
stop = onepercent
for i in range(len(complete))[::-1]:
	if final < stop:
		print stop-final
		print complete[i]['count']
		print counter
		final += complete[i]['count']
		counter += 1
	else: 
		break
                 
print counter
# Combined number of users making up only 1% of posts - 1347 (about 78 % of the all users)

                               
# Top 10 appearing amenities
                                                
TopAmenities = collection.aggregate([{"$match" : {"amenity" : {"$exists" : 1}}},
								 	{"$group" : {"_id" : "$amenity", "count" : {"$sum" : 1}}}, 
					 				{"$sort" : {"count" : -1}}, 
					 				{"$limit" : 10}])                       

TopAmenities = list(TopAmenities)
pprint.pprint(TopAmenities)   
'''
[{u'_id': u'parking', u'count': 10444},
 {u'_id': u'bench', u'count': 4461},
 {u'_id': u'waste_basket', u'count': 2829},
 {u'_id': u'restaurant', u'count': 2448},
 {u'_id': u'fuel', u'count': 1856},
 {u'_id': u'cafe', u'count': 1830},
 {u'_id': u'drinking_water', u'count': 1728},
 {u'_id': u'bicycle_parking', u'count': 1529},
 {u'_id': u'bank', u'count': 1448},
 {u'_id': u'place_of_worship', u'count': 1219}]                      
'''
                                              
# Biggest religion 
                                                
TopReligion = collection.aggregate([{"$match" : {"amenity" : {"$exists" : 1}, "amenity" : "place_of_worship"}},
              				      	{"$group" : {"_id" : "$religion", "count" : {"$sum" : 1}}},
                        			{"$sort" : {"count" : -1}}, 
                        			{"$limit" : 4}])
TopReligion = list(TopReligion)
pprint.pprint(TopReligion)

'''
[{u'_id': u'christian', u'count': 1160},
 {u'_id': None, u'count': 33},
 {u'_id': u'jewish', u'count': 19},
 {u'_id': u'buddhist', u'count': 4}]
'''
                                                                                    
# Most popular cuisines
                                                
TopCuisine = collection.aggregate([{"$match" : {"amenity" : {"$exists" : 1}, "amenity" : "restaurant"}}, 
									{"$group" : {"_id" : "$cuisine", "count" : {"$sum" : 1}}},
									{"$sort" : {"count" : -1}}, 
									{"$limit" : 4}])
TopCuisine = list(TopCuisine)
pprint.pprint(TopCuisine)

'''
[{u'_id': None, u'count': 1088},
 {u'_id': u'italian', u'count': 424},
 {u'_id': u'pizza', u'count': 356},
 {u'_id': u'regional', u'count': 103}]       		
'''

# Top Bank brand	

TopBanks = collection.aggregate([{"$match" : {"name" : {"$exists" : 1}, 'amenity' : 'bank'}},
								 	{"$group" : {"_id" : "$name", "count" : {"$sum" : 1}}}, 
					 				{"$sort" : {"count" : -1}}, 
					 				{"$limit" : 4}])
TopBanks = list(TopBanks)
pprint.pprint(TopBanks)

'''
[{u'_id': u'Unicredit', u'count': 102},
 {u'_id': u'Banca Popolare di Milano', u'count': 57},
 {u'_id': u'Intesa San Paolo', u'count': 42},
 {u'_id': u'Banca Intesa', u'count': 41}]
'''

TopCity = collection.aggregate([{"$match" : {"address.city" : {"$exists" : 1}}},
								 	{"$group" : {"_id" : "$address.city", "count" : {"$sum" : 1}}}, 
					 				{"$sort" : {"count" : -1}}, 
					 				{"$limit" : 4}])

TopCity = list(TopCity)
pprint.pprint(TopCity)

'''
[{u'_id': u'Monza', u'count': 13196},
 {u'_id': u'Milano', u'count': 8410},
 {u'_id': u'Brugherio', u'count': 4356},
 {u'_id': u'Cusano Milanino', u'count': 3293}]
 '''

				 				


