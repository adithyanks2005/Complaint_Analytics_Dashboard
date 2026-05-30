"""
Pincode to Location mapping for Indian locations
Maps 6-digit pincodes to state, district, municipality, village
"""

# Comprehensive Indian Pincode Database
# Format: pincode -> {state, district, municipality, village}
PINCODE_DATABASE = {
    # Delhi
    "110001": {"state": "Delhi", "district": "Central Delhi", "municipality": "Delhi", "village": "New Delhi"},
    "110002": {"state": "Delhi", "district": "Central Delhi", "municipality": "Delhi", "village": "Karol Bagh"},
    "110005": {"state": "Delhi", "district": "Central Delhi", "municipality": "Delhi", "village": "New Delhi"},
    "110006": {"state": "Delhi", "district": "Central Delhi", "municipality": "Delhi", "village": "Connaught Place"},
    "110011": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Indira Nagar"},
    "110012": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Sri Nagar"},
    "110013": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Kalkaji"},
    "110014": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Amar Colony"},
    "110015": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Sangam Vihar"},
    "110016": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Chhatarpur"},
    "110017": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Defence Colony"},
    "110018": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Malviya Nagar"},
    "110019": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Greater Kailash"},
    "110020": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Greater Kailash"},
    "110021": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Green Park"},
    "110022": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Hauz Khas"},
    "110023": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Haryana Vihar"},
    "110024": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Hari Nagar"},
    "110025": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Krishna Nagar"},
    "110030": {"state": "Delhi", "district": "South Delhi", "municipality": "Delhi", "village": "Mehrauli"},
    "110031": {"state": "Delhi", "district": "East Delhi", "municipality": "Delhi", "village": "Patparganj"},
    "110032": {"state": "Delhi", "district": "East Delhi", "municipality": "Delhi", "village": "Preet Vihar"},
    "110033": {"state": "Delhi", "district": "East Delhi", "municipality": "Delhi", "village": "Pandav Nagar"},
    "110034": {"state": "Delhi", "district": "East Delhi", "municipality": "Delhi", "village": "Pandav Nagar"},
    "110035": {"state": "Delhi", "district": "East Delhi", "municipality": "Delhi", "village": "Shakarpur"},
    "110036": {"state": "Delhi", "district": "East Delhi", "municipality": "Delhi", "village": "Ashok Vihar"},
    "110037": {"state": "Delhi", "district": "East Delhi", "municipality": "Delhi", "village": "Vikas Puri"},
    "110041": {"state": "Delhi", "district": "North East Delhi", "municipality": "Delhi", "village": "Karawal Nagar"},
    "110042": {"state": "Delhi", "district": "North East Delhi", "municipality": "Delhi", "village": "Karawal Nagar"},
    "110043": {"state": "Delhi", "district": "North East Delhi", "municipality": "Delhi", "village": "East Delhi"},
    "110051": {"state": "Delhi", "district": "North Delhi", "municipality": "Delhi", "village": "Civil Lines"},
    "110052": {"state": "Delhi", "district": "North Delhi", "municipality": "Delhi", "village": "Chandni Chowk"},
    "110053": {"state": "Delhi", "district": "North Delhi", "municipality": "Delhi", "village": "Old Delhi"},
    "110054": {"state": "Delhi", "district": "North Delhi", "municipality": "Delhi", "village": "Kasturba Nagar"},
    "110055": {"state": "Delhi", "district": "North Delhi", "municipality": "Delhi", "village": "Model Town"},
    "110056": {"state": "Delhi", "district": "North Delhi", "municipality": "Delhi", "village": "Model Town"},
    "110057": {"state": "Delhi", "district": "North Delhi", "municipality": "Delhi", "village": "Timarpur"},
    "110058": {"state": "Delhi", "district": "North Delhi", "municipality": "Delhi", "village": "Malka Ganj"},
    "110059": {"state": "Delhi", "district": "North Delhi", "municipality": "Delhi", "village": "Tri Nagar"},
    "110060": {"state": "Delhi", "district": "North Delhi", "municipality": "Delhi", "village": "Kasturba Nagar"},
    "110061": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Adarsh Nagar"},
    "110062": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Ashok Vihar"},
    "110063": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Ashok Vihar"},
    "110064": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Ashok Vihar"},
    "110065": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Azadpur"},
    "110066": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Azadpur"},
    "110067": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Prashant Vihar"},
    "110068": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Prashant Vihar"},
    "110069": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Rajouri Garden"},
    "110070": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Rajouri Garden"},
    "110071": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Rohini"},
    "110072": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Rohini"},
    "110073": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Rohini"},
    "110074": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Rohini"},
    "110075": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Rohini"},
    "110076": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Rohini"},
    "110077": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Sector 8 Rohini"},
    "110078": {"state": "Delhi", "district": "North West Delhi", "municipality": "Delhi", "village": "Sector 13 Rohini"},
    "110079": {"state": "Delhi", "district": "West Delhi", "municipality": "Delhi", "village": "Dwarka"},
    "110080": {"state": "Delhi", "district": "West Delhi", "municipality": "Delhi", "village": "Dwarka"},
    "110081": {"state": "Delhi", "district": "West Delhi", "municipality": "Delhi", "village": "Dwarka"},
    "110082": {"state": "Delhi", "district": "West Delhi", "municipality": "Delhi", "village": "Dwarka"},
    "110083": {"state": "Delhi", "district": "West Delhi", "municipality": "Delhi", "village": "Dwarka"},
    "110084": {"state": "Delhi", "district": "West Delhi", "municipality": "Delhi", "village": "Dwarka"},
    "110085": {"state": "Delhi", "district": "West Delhi", "municipality": "Delhi", "village": "Sector 12 Dwarka"},
    "110086": {"state": "Delhi", "district": "West Delhi", "municipality": "Delhi", "village": "Dwarka"},
    "110087": {"state": "Delhi", "district": "West Delhi", "municipality": "Delhi", "village": "Sector 8 Dwarka"},
    "110088": {"state": "Delhi", "district": "South West Delhi", "municipality": "Delhi", "village": "Chattarpur"},
    "110089": {"state": "Delhi", "district": "South West Delhi", "municipality": "Delhi", "village": "Mehrauli"},
    "110090": {"state": "Delhi", "district": "South West Delhi", "municipality": "Delhi", "village": "Mehrauli"},
    "110091": {"state": "Delhi", "district": "South West Delhi", "municipality": "Delhi", "village": "Deoli"},
    "110092": {"state": "Delhi", "district": "South East Delhi", "municipality": "Delhi", "village": "Kalkaji"},
    "110093": {"state": "Delhi", "district": "South East Delhi", "municipality": "Delhi", "village": "Kalkaji"},
    "110094": {"state": "Delhi", "district": "South East Delhi", "municipality": "Delhi", "village": "Kalkaji"},
    "110095": {"state": "Delhi", "district": "South East Delhi", "municipality": "Delhi", "village": "Kalkaji"},
    "110096": {"state": "Delhi", "district": "South East Delhi", "municipality": "Delhi", "village": "Kalkaji"},

    # Mumbai / Maharashtra
    "400001": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Fort"},
    "400002": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Kala Ghoda"},
    "400003": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Ballard Estate"},
    "400004": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Fort"},
    "400005": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Kala Ghoda"},
    "400006": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Ballard Estate"},
    "400007": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Colaba"},
    "400008": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Colaba"},
    "400009": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Back Bay"},
    "400010": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Marine Lines"},
    "400011": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Girgaum"},
    "400012": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Mumbai Central"},
    "400013": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Girgaum"},
    "400014": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Dhobi Talao"},
    "400015": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Opera House"},
    "400016": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Marine Lines"},
    "400017": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Keshavnagar"},
    "400018": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Parel"},
    "400019": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Tardeo"},
    "400020": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Worli"},
    "400021": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Worli"},
    "400022": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Worli"},
    "400023": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Lower Parel"},
    "400024": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Lower Parel"},
    "400025": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Bhuleshwar"},
    "400026": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Crawford Market"},
    "400027": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Mazgaon"},
    "400028": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Dhanraj Mahal"},
    "400029": {"state": "Maharashtra", "district": "Mumbai", "municipality": "Mumbai", "village": "Girgaum"},

    # Bangalore / Karnataka
    "560001": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Residency Road"},
    "560002": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Kumara Park"},
    "560003": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Vasanth Nagar"},
    "560004": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Shanthi Nagar"},
    "560005": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Chamarajpet"},
    "560006": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Indira Nagar"},
    "560008": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Whitefield"},
    "560009": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Old Madras Road"},
    "560010": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Okalipet"},
    "560011": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Padmanabha Nagar"},
    "560012": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Indiranagar"},
    "560014": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Halasuru"},
    "560015": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Halasuru"},
    "560017": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Vittal Mallya Road"},
    "560018": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Brigade Road"},
    "560019": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "MG Road"},
    "560020": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "MG Road"},
    "560021": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Cunningham Road"},
    "560022": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Ashok Nagar"},
    "560023": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Gandhinagar"},
    "560024": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Richmond Town"},
    "560025": {"state": "Karnataka", "district": "Bengaluru Urban", "municipality": "Bengaluru", "village": "Tasker Town"},

    # Hyderabad / Telangana
    "500001": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Bashirbagh"},
    "500002": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Secunderabad"},
    "500003": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Secunderabad"},
    "500004": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Begumpet"},
    "500005": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Secunderabad"},
    "500006": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Secunderabad"},
    "500007": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Hyderabad"},
    "500008": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Hyderabad"},
    "500009": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Hyderabad"},
    "500010": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Hyderabad"},
    "500011": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Hyderabad"},
    "500012": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Hyderabad"},
    "500013": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Hyderabad"},
    "500014": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Hyderabad"},
    "500015": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Hyderabad"},
    "500016": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Dilsukhnagar"},
    "500017": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Dilsukhnagar"},
    "500018": {"state": "Telangana", "district": "Hyderabad", "municipality": "Hyderabad", "village": "Kachiguda"},

    # Pune / Maharashtra
    "411001": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Pune Central"},
    "411002": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Pune"},
    "411003": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Pune"},
    "411004": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Pune"},
    "411005": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Kothrud"},
    "411006": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Kothrud"},
    "411007": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Kothrud"},
    "411008": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Kothrud"},
    "411009": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Kothrud"},
    "411010": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Pune"},
    "411011": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Ghorpade Peth"},
    "411012": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Pune"},
    "411013": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Pune"},
    "411014": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Pune"},
    "411015": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Ghorpade Peth"},
    "411016": {"state": "Maharashtra", "district": "Pune", "municipality": "Pune", "village": "Pune"},

    # Chennai / Tamil Nadu
    "600001": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Fort"},
    "600002": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Fort"},
    "600003": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "George Town"},
    "600004": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "George Town"},
    "600005": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Royapettah"},
    "600006": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Royapettah"},
    "600007": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Thousand Lights"},
    "600008": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Nungambakkam"},
    "600009": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Nungambakkam"},
    "600010": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Nandanam"},
    "600011": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Shastri Nagar"},
    "600012": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Shastri Nagar"},
    "600127": {"state": "Tamil Nadu", "district": "Chennai", "municipality": "Chennai", "village": "Tambaram"},

    # Kolkata / West Bengal
    "700001": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Koley Market"},
    "700002": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Lal Bazar"},
    "700003": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Fairlie Place"},
    "700004": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Esplanade"},
    "700005": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Esplanade"},
    "700006": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Ballygunge"},
    "700007": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Alipore"},
    "700008": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Alipore"},
    "700009": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Alipore"},
    "700010": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Alipore"},
    "700011": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Ballygunge"},
    "700012": {"state": "West Bengal", "district": "Kolkata", "municipality": "Kolkata", "village": "Ballygunge"},

    # Ahmedabad / Gujarat
    "380001": {"state": "Gujarat", "district": "Ahmedabad", "municipality": "Ahmedabad", "village": "Rajabazar"},
    "380002": {"state": "Gujarat", "district": "Ahmedabad", "municipality": "Ahmedabad", "village": "Lal Darwaja"},
    "380003": {"state": "Gujarat", "district": "Ahmedabad", "municipality": "Ahmedabad", "village": "Sarangpur"},
    "380004": {"state": "Gujarat", "district": "Ahmedabad", "municipality": "Ahmedabad", "village": "Kalupur"},
    "380005": {"state": "Gujarat", "district": "Ahmedabad", "municipality": "Ahmedabad", "village": "Bhadra"},
    "380006": {"state": "Gujarat", "district": "Ahmedabad", "municipality": "Ahmedabad", "village": "Bhadra"},
    "380007": {"state": "Gujarat", "district": "Ahmedabad", "municipality": "Ahmedabad", "village": "Paldi"},
    "380008": {"state": "Gujarat", "district": "Ahmedabad", "municipality": "Ahmedabad", "village": "Khanpur"},
    "380009": {"state": "Gujarat", "district": "Ahmedabad", "municipality": "Ahmedabad", "village": "Raipur"},
    "380010": {"state": "Gujarat", "district": "Ahmedabad", "municipality": "Ahmedabad", "village": "Raipur"},

    # Indore / Madhya Pradesh
    "452001": {"state": "Madhya Pradesh", "district": "Indore", "municipality": "Indore", "village": "Rajwada"},
    "452002": {"state": "Madhya Pradesh", "district": "Indore", "municipality": "Indore", "village": "Indore"},
    "452003": {"state": "Madhya Pradesh", "district": "Indore", "municipality": "Indore", "village": "Indore"},
    "452004": {"state": "Madhya Pradesh", "district": "Indore", "municipality": "Indore", "village": "Indore"},
    "452005": {"state": "Madhya Pradesh", "district": "Indore", "municipality": "Indore", "village": "Indore"},
    "452006": {"state": "Madhya Pradesh", "district": "Indore", "municipality": "Indore", "village": "Indore"},

    # Jaipur / Rajasthan
    "302001": {"state": "Rajasthan", "district": "Jaipur", "municipality": "Jaipur", "village": "City Palace"},
    "302002": {"state": "Rajasthan", "district": "Jaipur", "municipality": "Jaipur", "village": "Bani Park"},
    "302003": {"state": "Rajasthan", "district": "Jaipur", "municipality": "Jaipur", "village": "Bani Park"},
    "302004": {"state": "Rajasthan", "district": "Jaipur", "municipality": "Jaipur", "village": "C-Scheme"},
    "302005": {"state": "Rajasthan", "district": "Jaipur", "municipality": "Jaipur", "village": "Jaipur"},
    "302006": {"state": "Rajasthan", "district": "Jaipur", "municipality": "Jaipur", "village": "Jaipur"},

    # Lucknow / Uttar Pradesh
    "226001": {"state": "Uttar Pradesh", "district": "Lucknow", "municipality": "Lucknow", "village": "Residency Road"},
    "226002": {"state": "Uttar Pradesh", "district": "Lucknow", "municipality": "Lucknow", "village": "Lucknow"},
    "226003": {"state": "Uttar Pradesh", "district": "Lucknow", "municipality": "Lucknow", "village": "Lucknow"},
    "226004": {"state": "Uttar Pradesh", "district": "Lucknow", "municipality": "Lucknow", "village": "Lucknow"},
    "226005": {"state": "Uttar Pradesh", "district": "Lucknow", "municipality": "Lucknow", "village": "Lucknow"},
    "226006": {"state": "Uttar Pradesh", "district": "Lucknow", "municipality": "Lucknow", "village": "Lucknow"},

    # Surat / Gujarat
    "395001": {"state": "Gujarat", "district": "Surat", "municipality": "Surat", "village": "Surat"},
    "395002": {"state": "Gujarat", "district": "Surat", "municipality": "Surat", "village": "Surat"},
    "395003": {"state": "Gujarat", "district": "Surat", "municipality": "Surat", "village": "Surat"},
    "395004": {"state": "Gujarat", "district": "Surat", "municipality": "Surat", "village": "Surat"},
    "395005": {"state": "Gujarat", "district": "Surat", "municipality": "Surat", "village": "Surat"},
    "395006": {"state": "Gujarat", "district": "Surat", "municipality": "Surat", "village": "Surat"},

    # Guwahati / Assam
    "781001": {"state": "Assam", "district": "Kamrup Metro", "municipality": "Guwahati", "village": "Guwahati"},
    "781002": {"state": "Assam", "district": "Kamrup Metro", "municipality": "Guwahati", "village": "Guwahati"},
    "781003": {"state": "Assam", "district": "Kamrup Metro", "municipality": "Guwahati", "village": "Guwahati"},
    "781004": {"state": "Assam", "district": "Kamrup Metro", "municipality": "Guwahati", "village": "Guwahati"},
    "781005": {"state": "Assam", "district": "Kamrup Metro", "municipality": "Guwahati", "village": "Guwahati"},
    "781006": {"state": "Assam", "district": "Kamrup Metro", "municipality": "Guwahati", "village": "Guwahati"},

    # Add more as needed...
}


def get_location_from_pincode(pincode: str) -> dict | None:
    """
    Retrieve location details for a given pincode.
    
    Args:
        pincode: 6-digit Indian pincode
        
    Returns:
        Dictionary with state, district, municipality, village if found, else None
    """
    if not pincode:
        return None
    
    pincode_cleaned = pincode.strip()
    return PINCODE_DATABASE.get(pincode_cleaned)


def get_state_from_pincode(pincode: str) -> str | None:
    """Get state from pincode"""
    location = get_location_from_pincode(pincode)
    return location.get("state") if location else None


def get_district_from_pincode(pincode: str) -> str | None:
    """Get district from pincode"""
    location = get_location_from_pincode(pincode)
    return location.get("district") if location else None


def get_municipality_from_pincode(pincode: str) -> str | None:
    """Get municipality from pincode"""
    location = get_location_from_pincode(pincode)
    return location.get("municipality") if location else None


def get_village_from_pincode(pincode: str) -> str | None:
    """Get village from pincode"""
    location = get_location_from_pincode(pincode)
    return location.get("village") if location else None
