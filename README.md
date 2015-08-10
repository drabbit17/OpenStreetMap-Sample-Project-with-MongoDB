# OpenStreetMap Sample Project - DataWrangling with MongoDB
#### Matteo Pallini

Map Area: Milan, Lombardia, Italy

source:
[https://mapzen.com/data/metro-extracts](https://mapzen.com/data/metro-extracts)

## 1 Problems encountered in the Map
After downloading the Milan map area from metro extracts website i started exploring the data to better understand potential problems with them and the details included. Three main problems where identified and corrected. Those are discussed in the following order:
* Inconsistent postal codes, shorter than expected
* Street names lacking a common standard, i.e. "via" rather than "Via"...
* Dots included in tag values in the XML file. 

#### Postal Codes
Some postal codes included in the dataset present a smaller number of digits. The most likely cause for this issue is the partial compilation of the postal code. Rather than including a potentially misleading value i prefer to substitute the miscoded one with "None".

#### Street Names
In Italy the most commonly used name to call a street is "via", while for a square it is usually used "Piazza". In some cases, those commonly adopted names and some others, were used without the initial capital letter or using exclusively capital letters. In order to solve this problem a common standard was defined for each usually adopted word and used for each address.

In the table below can be found the standards adopted:

| Mistyped Name | Standard Used |
|---------------|:--------------|
| C.na | Cascina |
| S.P.208 | SP |
| VIA  | Via |
| piazza | Piazza |
| via | Via |
| vial | Viale |
| piazza | Piazza |
| Ingresso | Ingresso |


#### Dots in Keys
In few cases some tag names included "." rather than ":", creating a conflict when the XML was converted into a JSON file. In order to solve this issue all "." in tag names where substituted with ":".

## Data Overview
This section contains basic statistics about the dataset and the MongoDB queries used to gather them.

#### File sizes  

Milan.osm......... 549 mb  
Milan.json........ 625 mb  

*Number of documents*  
    collection.find().count()                                                  
4766245  
                                      
*Number of nodes*  
    collection.find({"type":"node"}).count()  
4383822  

*Number of ways*  
	collection.find({"type":"way"}).count()  
371559  
                                               
*Number of unique users*  
	DistUser = collection.distinct("created.user")  
    len(DistUser)  
1724  


                                              
#### *Function to identify top contributors*
	def ContributorExtr(n):
	contributor = collection.aggregate([{"$group" : {"_id" : "$created.user", "count" : {"$sum" : 1}}}, 
											{ "$sort" : { "count" : -1} },
											{"$limit" : n}])                                              
	contributor = list(contributor)
	return contributor
	
*Top 1 contributing user*  	
	> ContributorExtr(1)  
[{u'count': 599526, u'_id': u'ilrobi'}]

                                             
*Number of users appearing only once (having 1 post)*  
	> uniqueContribution = collection.aggregate([{"$group" : {"_id" : "$created.user", "count" : {"$sum" : 1}}}, 
							{"$group" : {"_id" : "$count", "num_users" : {"$sum" : 1}}}, 
							{"$sort" : {"_id" : 1}}, 
							{"$limit" : 1}])  

[{u'num_users': 131, u'_id': 1}]



#### Contributors Distribution
The contributors distribution results way less skewed than the one in the example provided. Still the number of users accounting for the bottom 1% is still very large, amounting to around 78% of all users.

* Top user contribution percentage (“ilrobi”) - 13.67%
* Combined top 2 users' contribution (“ilrobi” and “Alecs01”) - 25.69% 
* Combined Top 10 users contribution - 59.93%
* Combined number of users making up only 1% of posts - 1347 (about 78 % of the all users)
* Combined number of users making up only 1% of posts - 1347 (about 78 % of the all users)

#### Additional data exploration using MongoDB queries

*10 appearing amenities*               
	> collection.aggregate([{"$match" : {"amenity" : {"$exists" : 1}}},
				{"$group" : {"_id" : "$amenity", "count" : {"$sum" : 1}}}, 
				{"$sort" : {"count" : -1}}, 
				{"$limit" : 10}])                
 
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
                                              
*Biggest religion (being Italy a Catholic country christianity is the leading religion)*  
	> collection.aggregate([{"$match" : {"amenity" : {"$exists" : 1}, "amenity" : "place_of_worship"}},
              			{"$group" : {"_id" : "$religion", "count" : {"$sum" : 1}}},
                        	{"$sort" : {"count" : -1}}, 
                        	{"$limit" : 4}])

[{u'_id': u'christian', u'count': 1160},
 {u'_id': None, u'count': 33},
 {u'_id': u'jewish', u'count': 19},
 {u'_id': u'buddhist', u'count': 4}]

                                                                                    
*Most popular cuisines*  
	> collection.aggregate([{"$match" : {"amenity" : {"$exists" : 1}, "amenity" : "restaurant"}}, 
				{"$group" : {"_id" : "$cuisine", "count" : {"$sum" : 1}}},
				{"$sort" : {"count" : -1}}, 
				{"$limit" : 4}])

[{u'_id': None, u'count': 1088},
 {u'_id': u'italian', u'count': 424},
 {u'_id': u'pizza', u'count': 356},
 {u'_id': u'regional', u'count': 103}]       		


*Top Bank*  
	> collection.aggregate([{"$match" : {"name" : {"$exists" : 1}, 'amenity' : 'bank'}},
				{"$group" : {"_id" : "$name", "count" : {"$sum" : 1}}}, 
				{"$sort" : {"count" : -1}}, 
				{"$limit" : 4}])  

[{u'_id': u'Unicredit', u'count': 102},
 {u'_id': u'Banca Popolare di Milano', u'count': 57},
 {u'_id': u'Intesa San Paolo', u'count': 42},
 {u'_id': u'Banca Intesa', u'count': 41}]

*Top Cities listed (it is quite a surprise that most of observations listed belong to Monza rather than Milan)*  
	> collection.aggregate([{"$match" : {"address.city" : {"$exists" : 1}}},
				{"$group" : {"_id" : "$address.city", "count" : {"$sum" : 1}}}, 
				{"$sort" : {"count" : -1}}, 
				{"$limit" : 4}])

[{u'_id': u'Monza', u'count': 13196},
 {u'_id': u'Milano', u'count': 8410},
 {u'_id': u'Brugherio', u'count': 4356},
 {u'_id': u'Cusano Milanino', u'count': 3293}]


## Conclusion

After this review of the data it is obvious that not only the Milan area is incomplete, but apparently Monza (with a population of 120k) has many more has many more inputed observations than Milan (with a population of 1,251k). The data appeared fairly clean even before my intervention, only minor changes were needed. When we consider the names of the first ten users who inputed most of the data it looks like that all of them a real users and no bot is present.



