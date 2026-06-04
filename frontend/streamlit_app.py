"""
Complaint Analytics Dashboard - Streamlit Frontend
Uses Supabase when configured, with SQLite as the local fallback
"""
from __future__ import annotations

import sys
import re
import os
import uuid
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

PROJECT_ROOT = Path(__file__).resolve().parent
if not (PROJECT_ROOT / "backend").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import (
    DuplicateComplaintError,
    delete_complaint_record,
    generate_next_id,
    generate_next_id_supabase,
    insert_complaint,
    init_db,
    read_complaints_df,
    update_complaint_record,
    using_supabase,
)
from backend.ai_prioritizer import compute_priority
from backend.pincode_lookup import (
    get_location_from_pincode,
)

# ── Notification helper ────────────────────────────────────────────────────────
try:
    from notifier import notify as _notify_real
    _NOTIFIER_AVAILABLE = True
except Exception:
    _NOTIFIER_AVAILABLE = False

# ── Paths ──────────────────────────────────────────────────────────────────────
# Resolve data/ folder regardless of where Streamlit launches the script from.
# Candidates in priority order:
#   1. <repo_root>/data/  (local: frontend/streamlit_app.py -> parent.parent)
#   2. data/ relative to cwd (Streamlit Cloud runs from repo root)
#   3. /tmp/  (Vercel / read-only filesystems)
def _find_data_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / "data",  # local
        Path.cwd() / "data",                               # Streamlit Cloud
    ]
    for c in candidates:
        if c.exists():
            return c
    # None found - use first candidate and create it
    candidates[0].mkdir(parents=True, exist_ok=True)
    return candidates[0]

DATA_DIR = _find_data_dir()
DB_PATH  = DATA_DIR / "complaints.db"
CSV_PATH = DATA_DIR / "sample_complaints.csv"
UPLOAD_DIR = DATA_DIR / "uploads"

# Ensure data directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_USERNAME = os.getenv("DASHBOARD_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("DASHBOARD_ADMIN_PASSWORD", "admin123")
MAX_DESCRIPTION_LENGTH = 300
MAX_IMAGE_BYTES = 5 * 1024 * 1024
GENERIC_AREA_LABELS = {
    "Central Zone",
    "East Zone",
    "North Zone",
    "South Zone",
    "West Zone",
}
INDIAN_STATES = [
    "Andaman and Nicobar Islands",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Ladakh",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
]
STATE_DISTRICT_OPTIONS = {
    "Andaman and Nicobar Islands": ["Nicobars", "North And Middle Andaman", "South Andamans"],
    "Andhra Pradesh": [
        "Alluri Sitharama Raju", "Anakapalli", "Ananthapuramu", "Annamayya", "Bapatla", "Chittoor",
        "Dr. B.R. Ambedkar Konaseema", "East Godavari", "Eluru", "Guntur", "Kakinada", "Krishna",
        "Kurnool", "Nandyal", "NTR", "Palnadu", "Parvathipuram Manyam", "Prakasam",
        "Sri Potti Sriramulu Nellore", "Sri Sathya Sai", "Srikakulam", "Tirupati", "Visakhapatnam",
        "Vizianagaram", "West Godavari", "YSR Kadapa",
    ],
    "Arunachal Pradesh": [
        "Anjaw", "Bichom", "Changlang", "Dibang Valley", "East Kameng", "East Siang", "Kamle",
        "Keyi Panyor", "Kra Daadi", "Kurung Kumey", "Leparada", "Lohit", "Longding",
        "Lower Dibang Valley", "Lower Siang", "Lower Subansiri", "Namsai", "Pakke Kessang",
        "Papum Pare", "Shi Yomi", "Siang", "Tawang", "Tirap", "Upper Siang", "Upper Subansiri",
        "West Kameng", "West Siang",
    ],
    "Assam": [
        "Bajali", "Baksa", "Barpeta", "Biswanath", "Bongaigaon", "Cachar", "Charaideo", "Chirang",
        "Darrang", "Dhemaji", "Dhubri", "Dibrugarh", "Dima Hasao", "Goalpara", "Golaghat",
        "Hailakandi", "Hojai", "Jorhat", "Kamrup", "Kamrup Metro", "Karbi Anglong", "Kokrajhar",
        "Lakhimpur", "Majuli", "Morigaon", "Nagaon", "Nalbari", "Sivasagar", "Sonitpur",
        "South Salmara-Mankachar", "Tamulpur", "Tinsukia", "Udalguri", "West Karbi Anglong",
    ],
    "Bihar": [
        "Araria", "Arwal", "Aurangabad", "Banka", "Begusarai", "Bhagalpur", "Bhojpur", "Buxar",
        "Darbhanga", "East Champaran", "Gaya", "Gopalganj", "Jamui", "Jehanabad", "Kaimur",
        "Katihar", "Khagaria", "Kishanganj", "Lakhisarai", "Madhepura", "Madhubani", "Munger",
        "Muzaffarpur", "Nalanda", "Nawada", "Patna", "Purnia", "Rohtas", "Saharsa", "Samastipur",
        "Saran", "Sheikhpura", "Sheohar", "Sitamarhi", "Siwan", "Supaul", "Vaishali",
        "West Champaran",
    ],
    "Chandigarh": ["Chandigarh"],
    "Chhattisgarh": [
        "Balod", "Baloda Bazar-Bhatapara", "Balrampur-Ramanujganj", "Bastar", "Bemetara", "Bijapur",
        "Bilaspur", "Dantewada", "Dhamtari", "Durg", "Gariaband", "Gaurela-Pendra-Marwahi",
        "Janjgir-Champa", "Jashpur", "Kabirdham", "Khairagarh-Chhuikhadan-Gandai", "Kondagaon",
        "Korba", "Korea", "Mahasamund", "Manendragarh-Chirmiri-Bharatpur", "Mohla-Manpur-Ambagarh Chowki",
        "Mungeli", "Narayanpur", "Raigarh", "Raipur", "Rajnandgaon", "Sakti", "Sarangarh-Bilaigarh",
        "Sukma", "Surajpur", "Surguja",
    ],
    "Dadra and Nagar Haveli and Daman and Diu": ["Dadra And Nagar Haveli", "Daman", "Diu"],
    "Delhi": [
        "Central Delhi", "East Delhi", "New Delhi", "North Delhi", "North East Delhi", "North West Delhi",
        "Shahdara", "South Delhi", "South East Delhi", "South West Delhi", "West Delhi",
    ],
    "Goa": ["North Goa", "South Goa"],
    "Gujarat": [
        "Ahmedabad", "Amreli", "Anand", "Aravalli", "Banaskantha", "Bharuch", "Bhavnagar", "Botad",
        "Chhota Udaipur", "Dahod", "Dang", "Devbhoomi Dwarka", "Gandhinagar", "Gir Somnath",
        "Jamnagar", "Junagadh", "Kachchh", "Kheda", "Mahisagar", "Mehsana", "Morbi", "Narmada",
        "Navsari", "Panchmahal", "Patan", "Porbandar", "Rajkot", "Sabarkantha", "Surat",
        "Surendranagar", "Tapi", "Vadodara", "Valsad",
    ],
    "Haryana": [
        "Ambala", "Bhiwani", "Charkhi Dadri", "Faridabad", "Fatehabad", "Gurugram", "Hisar",
        "Jhajjar", "Jind", "Kaithal", "Karnal", "Kurukshetra", "Mahendragarh", "Nuh", "Palwal",
        "Panchkula", "Panipat", "Rewari", "Rohtak", "Sirsa", "Sonipat", "Yamunanagar",
    ],
    "Himachal Pradesh": [
        "Bilaspur", "Chamba", "Hamirpur", "Kangra", "Kinnaur", "Kullu", "Lahaul And Spiti",
        "Mandi", "Shimla", "Sirmaur", "Solan", "Una",
    ],
    "Jammu and Kashmir": [
        "Anantnag", "Bandipora", "Baramulla", "Budgam", "Doda", "Ganderbal", "Jammu", "Kathua",
        "Kishtwar", "Kulgam", "Kupwara", "Poonch", "Pulwama", "Rajouri", "Ramban", "Reasi",
        "Samba", "Shopian", "Srinagar", "Udhampur",
    ],
    "Jharkhand": [
        "Bokaro", "Chatra", "Deoghar", "Dhanbad", "Dumka", "East Singhbhum", "Garhwa", "Giridih",
        "Godda", "Gumla", "Hazaribagh", "Jamtara", "Khunti", "Koderma", "Latehar", "Lohardaga",
        "Pakur", "Palamu", "Ramgarh", "Ranchi", "Sahebganj", "Saraikela Kharsawan", "Simdega",
        "West Singhbhum",
    ],
    "Karnataka": [
        "Bagalkote", "Ballari", "Belagavi", "Bengaluru Rural", "Bengaluru South", "Bengaluru Urban",
        "Bidar", "Chamarajanagar", "Chikkaballapura", "Chikkamagaluru", "Chitradurga",
        "Dakshina Kannada", "Davanagere", "Dharwad", "Gadag", "Hassan", "Haveri", "Kalaburagi",
        "Kodagu", "Kolar", "Koppal", "Mandya", "Mysuru", "Raichur", "Ramanagara", "Shivamogga",
        "Tumakuru", "Udupi", "Uttara Kannada", "Vijayanagara", "Vijayapura", "Yadgir",
    ],
    "Kerala": [
        "Alappuzha", "Ernakulam", "Idukki", "Kannur", "Kasaragod", "Kollam", "Kottayam",
        "Kozhikode", "Malappuram", "Palakkad", "Pathanamthitta", "Thiruvananthapuram", "Thrissur",
        "Wayanad",
    ],
    "Ladakh": ["Kargil", "Leh Ladakh"],
    "Lakshadweep": ["Lakshadweep District"],
    "Madhya Pradesh": [
        "Agar Malwa", "Alirajpur", "Anuppur", "Ashoknagar", "Balaghat", "Barwani", "Betul", "Bhind",
        "Bhopal", "Burhanpur", "Chhatarpur", "Chhindwara", "Damoh", "Datia", "Dewas", "Dhar",
        "Dindori", "Guna", "Gwalior", "Harda", "Indore", "Jabalpur", "Jhabua", "Katni", "Khandwa",
        "Khargone", "Maihar", "Mandla", "Mandsaur", "Mauganj", "Morena", "Narmadapuram", "Narsinghpur",
        "Neemuch", "Niwari", "Pandhurna", "Panna", "Raisen", "Rajgarh", "Ratlam", "Rewa", "Sagar",
        "Satna", "Sehore", "Seoni", "Shahdol", "Shajapur", "Sheopur", "Shivpuri", "Sidhi",
        "Singrauli", "Tikamgarh", "Ujjain", "Umaria", "Vidisha",
    ],
    "Maharashtra": [
        "Ahilyanagar", "Akola", "Amravati", "Beed", "Bhandara", "Buldhana", "Chandrapur",
        "Chhatrapati Sambhajinagar", "Dharashiv", "Dhule", "Gadchiroli", "Gondia", "Hingoli",
        "Jalgaon", "Jalna", "Kolhapur", "Latur", "Mumbai", "Mumbai Suburban", "Nagpur", "Nanded",
        "Nandurbar", "Nashik", "Palghar", "Parbhani", "Pune", "Raigad", "Ratnagiri", "Sangli",
        "Satara", "Sindhudurg", "Solapur", "Thane", "Wardha", "Washim", "Yavatmal",
    ],
    "Manipur": [
        "Bishnupur", "Chandel", "Churachandpur", "Imphal East", "Imphal West", "Jiribam", "Kakching",
        "Kamjong", "Kangpokpi", "Noney", "Pherzawl", "Senapati", "Tamenglong", "Tengnoupal",
        "Thoubal", "Ukhrul",
    ],
    "Meghalaya": [
        "East Garo Hills", "East Jaintia Hills", "East Khasi Hills", "Eastern West Khasi Hills",
        "North Garo Hills", "Ri Bhoi", "South Garo Hills", "South West Garo Hills",
        "South West Khasi Hills", "West Garo Hills", "West Jaintia Hills", "West Khasi Hills",
    ],
    "Mizoram": [
        "Aizawl", "Champhai", "Hnahthial", "Khawzawl", "Kolasib", "Lawngtlai", "Lunglei",
        "Mamit", "Saitual", "Serchhip", "Siaha",
    ],
    "Nagaland": [
        "Chumoukedima", "Dimapur", "Kiphire", "Kohima", "Longleng", "Meluri", "Mokokchung",
        "Mon", "Niuland", "Noklak", "Peren", "Phek", "Shamator", "Tseminyu", "Tuensang",
        "Wokha", "Zunheboto",
    ],
    "Odisha": [
        "Angul", "Balangir", "Balasore", "Bargarh", "Bhadrak", "Boudh", "Cuttack", "Deogarh",
        "Dhenkanal", "Gajapati", "Ganjam", "Jagatsinghapur", "Jajpur", "Jharsuguda", "Kalahandi",
        "Kandhamal", "Kendrapara", "Keonjhar", "Khordha", "Koraput", "Malkangiri", "Mayurbhanj",
        "Nabarangpur", "Nayagarh", "Nuapada", "Puri", "Rayagada", "Sambalpur", "Subarnapur",
        "Sundargarh",
    ],
    "Puducherry": ["Karaikal", "Mahe", "Puducherry", "Yanam"],
    "Punjab": [
        "Amritsar", "Barnala", "Bathinda", "Faridkot", "Fatehgarh Sahib", "Fazilka", "Ferozepur",
        "Gurdaspur", "Hoshiarpur", "Jalandhar", "Kapurthala", "Ludhiana", "Malerkotla", "Mansa",
        "Moga", "Pathankot", "Patiala", "Rupnagar", "S.A.S Nagar", "Sangrur",
        "Shahid Bhagat Singh Nagar", "Sri Muktsar Sahib", "Tarn Taran",
    ],
    "Rajasthan": [
        "Ajmer", "Alwar", "Balotra", "Banswara", "Baran", "Barmer", "Beawar", "Bharatpur",
        "Bhilwara", "Bikaner", "Bundi", "Chittorgarh", "Churu", "Dausa", "Deeg", "Dholpur",
        "Didwana-Kuchaman", "Dudu", "Dungarpur", "Ganganagar", "Gangapur City", "Hanumangarh",
        "Jaipur", "Jaipur Rural", "Jaisalmer", "Jalore", "Jhalawar", "Jhunjhunu", "Jodhpur",
        "Jodhpur Rural", "Karauli", "Kekri", "Khairthal-Tijara", "Kota", "Kotputli-Behror",
        "Nagaur", "Neem Ka Thana", "Pali", "Phalodi", "Pratapgarh", "Rajsamand", "Salumbar",
        "Sawai Madhopur", "Shahpura", "Sikar", "Sirohi", "Tonk", "Udaipur",
    ],
    "Sikkim": ["Gangtok", "Gyalshing", "Mangan", "Namchi", "Pakyong", "Soreng"],
    "Tamil Nadu": [
        "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri",
        "Dindigul", "Erode", "Kallakurichi", "Kancheepuram", "Kanniyakumari", "Karur",
        "Krishnagiri", "Madurai", "Mayiladuthurai", "Nagapattinam", "Namakkal", "Perambalur",
        "Pudukkottai", "Ramanathapuram", "Ranipet", "Salem", "Sivaganga", "Tenkasi", "Thanjavur",
        "Theni", "The Nilgiris", "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur",
        "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur", "Vellore", "Viluppuram",
        "Virudhunagar",
    ],
    "Telangana": [
        "Adilabad", "Bhadradri Kothagudem", "Hanumakonda", "Hyderabad", "Jagitial", "Jangoan",
        "Jayashankar Bhupalapally", "Jogulamba Gadwal", "Kamareddy", "Karimnagar", "Khammam",
        "Kumuram Bheem Asifabad", "Mahabubabad", "Mahabubnagar", "Mancherial", "Medak",
        "Medchal Malkajgiri", "Mulugu", "Nagarkurnool", "Nalgonda", "Narayanpet", "Nirmal",
        "Nizamabad", "Peddapalli", "Rajanna Sircilla", "Rangareddy", "Sangareddy", "Siddipet",
        "Suryapet", "Vikarabad", "Wanaparthy", "Warangal", "Yadadri Bhuvanagiri",
    ],
    "Tripura": ["Dhalai", "Gomati", "Khowai", "North Tripura", "Sepahijala", "South Tripura", "Unakoti", "West Tripura"],
    "Uttar Pradesh": [
        "Agra", "Aligarh", "Ambedkar Nagar", "Amethi", "Amroha", "Auraiya", "Ayodhya", "Azamgarh",
        "Baghpat", "Bahraich", "Ballia", "Balrampur", "Banda", "Barabanki", "Bareilly", "Basti",
        "Bhadohi", "Bijnor", "Budaun", "Bulandshahr", "Chandauli", "Chitrakoot", "Deoria", "Etah",
        "Etawah", "Farrukhabad", "Fatehpur", "Firozabad", "Gautam Buddha Nagar", "Ghaziabad",
        "Ghazipur", "Gonda", "Gorakhpur", "Hamirpur", "Hapur", "Hardoi", "Hathras", "Jalaun",
        "Jaunpur", "Jhansi", "Kannauj", "Kanpur Dehat", "Kanpur Nagar", "Kasganj", "Kaushambi",
        "Kheri", "Kushinagar", "Lalitpur", "Lucknow", "Maharajganj", "Mahoba", "Mainpuri",
        "Mathura", "Mau", "Meerut", "Mirzapur", "Moradabad", "Muzaffarnagar", "Pilibhit",
        "Pratapgarh", "Prayagraj", "Raebareli", "Rampur", "Saharanpur", "Sambhal", "Sant Kabir Nagar",
        "Shahjahanpur", "Shamli", "Shravasti", "Siddharthnagar", "Sitapur", "Sonbhadra",
        "Sultanpur", "Unnao", "Varanasi",
    ],
    "Uttarakhand": [
        "Almora", "Bageshwar", "Chamoli", "Champawat", "Dehradun", "Haridwar", "Nainital",
        "Pauri Garhwal", "Pithoragarh", "Rudraprayag", "Tehri Garhwal", "Udham Singh Nagar",
        "Uttarkashi",
    ],
    "West Bengal": [
        "Alipurduar", "Bankura", "Birbhum", "Cooch Behar", "Dakshin Dinajpur", "Darjeeling",
        "Hooghly", "Howrah", "Jalpaiguri", "Jhargram", "Kalimpong", "Kolkata", "Malda",
        "Murshidabad", "Nadia", "North 24 Parganas", "Paschim Bardhaman", "Paschim Medinipur",
        "Purba Bardhaman", "Purba Medinipur", "Purulia", "South 24 Parganas", "Uttar Dinajpur",
    ],
}
INDIAN_LOCATIONS = [
    "Agartala",
    "Agra",
    "Ahmedabad",
    "Ahmednagar",
    "Aizawl",
    "Ajmer",
    "Akola",
    "Alappuzha",
    "Aligarh",
    "Alipurduar",
    "Almora",
    "Alwar",
    "Amaravati",
    "Ambala",
    "Ambedkar Nagar",
    "Amravati",
    "Amritsar",
    "Anand",
    "Anantapur",
    "Anantnag",
    "Andaman and Nicobar Islands",
    "Andhra Pradesh",
    "Anducode",
    "Araria",
    "Ariyalur",
    "Arunachal Pradesh",
    "Asansol",
    "Assam",
    "Aurangabad",
    "Ayodhya",
    "Azamgarh",
    "Bagalkot",
    "Bahraich",
    "Balaghat",
    "Balangir",
    "Baleswar",
    "Ballari",
    "Balrampur",
    "Banda",
    "Bangalore",
    "Bankura",
    "Banswara",
    "Barabanki",
    "Baramulla",
    "Baran",
    "Bareilly",
    "Bargarh",
    "Barmer",
    "Barnala",
    "Barpeta",
    "Bastar",
    "Basti",
    "Bathinda",
    "Beed",
    "Begusarai",
    "Belagavi",
    "Bengaluru",
    "Betul",
    "Bhadrak",
    "Bhagalpur",
    "Bhandara",
    "Bharatpur",
    "Bharuch",
    "Bhavnagar",
    "Bhilai",
    "Bhilwara",
    "Bhiwani",
    "Bhopal",
    "Bhubaneswar",
    "Bidar",
    "Bihar",
    "Bijapur",
    "Bijnor",
    "Bikaner",
    "Bilaspur",
    "Birbhum",
    "Bokaro",
    "Bongaigaon",
    "Budaun",
    "Bulandshahr",
    "Buldhana",
    "Bundi",
    "Burdwan",
    "Buxar",
    "Chamarajanagar",
    "Chamba",
    "Chamoli",
    "Champawat",
    "Chandigarh",
    "Chandrapur",
    "Chennai",
    "Chhatarpur",
    "Chhattisgarh",
    "Chhindwara",
    "Chikkamagaluru",
    "Chitradurga",
    "Chittoor",
    "Chittorgarh",
    "Coimbatore",
    "Cooch Behar",
    "Cuddalore",
    "Cuttack",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Dahod",
    "Dakshina Kannada",
    "Darbhanga",
    "Darjeeling",
    "Dausa",
    "Dehradun",
    "Delhi",
    "Deoghar",
    "Deoria",
    "Dewas",
    "Dhanbad",
    "Dhar",
    "Dharmapuri",
    "Dharwad",
    "Dhemaji",
    "Dhenkanal",
    "Dholpur",
    "Dibrugarh",
    "Dimapur",
    "Dindigul",
    "Durg",
    "East Godavari",
    "Ernakulam",
    "Erode",
    "Etawah",
    "Faizabad",
    "Faridabad",
    "Faridkot",
    "Farrukhabad",
    "Fatehabad",
    "Fatehpur",
    "Firozabad",
    "Gadag",
    "Gandhinagar",
    "Gangtok",
    "Gaya",
    "Ghaziabad",
    "Ghazipur",
    "Giridih",
    "Goa",
    "Golaghat",
    "Gonda",
    "Gondia",
    "Gorakhpur",
    "Gujarat",
    "Gulbarga",
    "Guntur",
    "Gurgaon",
    "Gurugram",
    "Guwahati",
    "Gwalior",
    "Hailakandi",
    "Haldwani",
    "Hamirpur",
    "Hanumangarh",
    "Hapur",
    "Harda",
    "Haridwar",
    "Haryana",
    "Hassan",
    "Haveri",
    "Himachal Pradesh",
    "Hisar",
    "Hooghly",
    "Hoshiarpur",
    "Howrah",
    "Hubballi",
    "Hyderabad",
    "Idukki",
    "Imphal",
    "Indore",
    "Itanagar",
    "Jabalpur",
    "Jaipur",
    "Jaisalmer",
    "Jalandhar",
    "Jalgaon",
    "Jalna",
    "Jammu",
    "Jammu and Kashmir",
    "Jamnagar",
    "Jamshedpur",
    "Jaunpur",
    "Jhajjar",
    "Jhalawar",
    "Jhansi",
    "Jharkhand",
    "Jhunjhunu",
    "Jodhpur",
    "Jorhat",
    "Junagadh",
    "Kadapa",
    "Kaithal",
    "Kalaburagi",
    "Kanchipuram",
    "Kannauj",
    "Kannur",
    "Kanpur",
    "Kanyakumari",
    "Kapurthala",
    "Karaikal",
    "Karauli",
    "Karimnagar",
    "Karnal",
    "Karnataka",
    "Karur",
    "Kasaragod",
    "Kathua",
    "Katihar",
    "Katni",
    "Kaushambi",
    "Kavaratti",
    "Kendrapara",
    "Keonjhar",
    "Kerala",
    "Khammam",
    "Khandwa",
    "Khargone",
    "Kochi",
    "Kohima",
    "Kolar",
    "Kolkata",
    "Kollam",
    "Korba",
    "Kota",
    "Kottayam",
    "Kozhikode",
    "Kullu",
    "Kurnool",
    "Kurukshetra",
    "Ladakh",
    "Lakhimpur",
    "Lakshadweep",
    "Latur",
    "Leh",
    "Lucknow",
    "Ludhiana",
    "Madurai",
    "Maharashtra",
    "Malappuram",
    "Mandi",
    "Mangalore",
    "Manipal",
    "Manipur",
    "Mathura",
    "Meerut",
    "Meghalaya",
    "Mizoram",
    "Mohali",
    "Moradabad",
    "Mumbai",
    "Mysuru",
    "Nagaland",
    "Nagapattinam",
    "Nagpur",
    "Nainital",
    "Namakkal",
    "Nanded",
    "Nashik",
    "Navi Mumbai",
    "New Delhi",
    "Noida",
    "Odisha",
    "Palakkad",
    "Panchkula",
    "Panipat",
    "Panaji",
    "Patiala",
    "Patna",
    "Puducherry",
    "Pune",
    "Punjab",
    "Raipur",
    "Rajasthan",
    "Rajkot",
    "Ranchi",
    "Rourkela",
    "Salem",
    "Shillong",
    "Shimla",
    "Sikkim",
    "Siliguri",
    "Srinagar",
    "Surat",
    "Tamil Nadu",
    "Telangana",
    "Thanjavur",
    "Thiruvananthapuram",
    "Thrissur",
    "Tiruchirappalli",
    "Tirunelveli",
    "Tirupati",
    "Tripura",
    "Udaipur",
    "Udupi",
    "Ujjain",
    "Uttar Pradesh",
    "Uttarakhand",
    "Vadodara",
    "Varanasi",
    "Vellore",
    "Vijayawada",
    "Visakhapatnam",
    "Warangal",
    "West Bengal",
]

st.set_page_config(
    page_title="Complaint Analytics Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global Styles ──────────────────────────────────────────────────────────────
st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
/* Dark theme with enhanced contrast */
.stApp {
  background: radial-gradient(circle at 15% 50%, rgba(99, 102, 241, 0.12), transparent 25%),
              radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.12), transparent 25%),
              #030303;
  color: #e2e8f0;
}
.main .block-container { padding: 2rem 3rem !important; max-width: 100% !important; }

/* Sidebar styling */
section[data-testid="stSidebar"] { 
  background: rgba(12, 12, 20, 0.75) !important; 
  backdrop-filter: blur(24px) !important;
  -webkit-backdrop-filter: blur(24px) !important;
  border-right: 1px solid rgba(255, 255, 255, 0.08) !important; 
}
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255, 255, 255, 0.05); }

/* Custom Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.5); }

/* Advanced Page Header */
.page-header { 
  background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%); 
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  border: 1px solid rgba(255,255,255,0.12); 
  border-radius: 20px; 
  padding: 20px 24px; 
  margin-bottom: 24px; 
  box-shadow: 0 16px 32px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.12);
  position: relative;
  overflow: hidden;
}
.page-header-title { font-size: 1.8rem; font-weight: 800; color: #f1f5f9; margin-bottom: 4px; display:flex; align-items:center; gap:10px; }
.page-header-sub { font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px; }
.header-badges { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.header-badge { 
  background: rgba(99,102,241,0.25); 
  border: 1px solid rgba(99,102,241,0.5); 
  border-radius: 50px; 
  padding: 6px 18px; 
  font-size: 0.78rem; 
  color: #c4b5fd; 
  font-weight: 600; 
  display:inline-flex; 
  align-items:center; 
  gap:6px; 
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: default;
}
.header-badge:hover {
  transform: scale(1.1) translateY(-3px);
  background: rgba(99,102,241,0.3);
  box-shadow: 0 8px 16px rgba(0,0,0,0.3);
  z-index: 10;
}
.header-badge svg {
  transition: transform 0.2s ease, stroke 0.2s ease;
}
.header-badge:hover svg {
  transform: translateY(-1px);
  stroke: #c4b5fd;
}

/* macOS Dock Inspired KPI Cards */
.kpi-grid { 
  display: flex; 
  gap: 12px; 
  margin-bottom: 28px; 
  align-items: stretch; 
  justify-content: center; 
  perspective: 1000px; 
}
.kpi-card {
  background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.04) 100%);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 16px;
  padding: 18px 16px;
  position: relative;
  overflow: hidden;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease, background 0.22s ease;
  transform-origin: center center;
  cursor: pointer;
  z-index: 1;
}
.kpi-card:hover {
  transform: translateY(-4px);
  background: linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.06) 100%);
  border-color: rgba(99,102,241,0.5);
  box-shadow: 0 14px 30px rgba(0,0,0,0.32);
  z-index: 50;
}
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--accent, linear-gradient(90deg, #6366f1, #8b5cf6)); border-radius: 16px 16px 0 0; }
.kpi-grid:hover .kpi-card { filter: brightness(0.9); }
.kpi-grid:hover .kpi-card:hover {
  transform: translateY(-5px);
  filter: brightness(1);
  z-index: 10;
  box-shadow: 0 18px 38px rgba(0,0,0,0.38), 0 0 0 1px rgba(255,255,255,0.12), 0 8px 24px var(--glow, rgba(99,102,241,0.25));
}
.kpi-grid:hover .kpi-card:hover + .kpi-card,
.kpi-grid:hover .kpi-card:has(+ .kpi-card:hover) {
  filter: brightness(0.96);
  z-index: 5;
}

.kpi-icon { width:42px; height:42px; border-radius:12px; display:flex; align-items:center; justify-content:center; margin-bottom:10px; background: linear-gradient(135deg, var(--icon-bg, rgba(99,102,241,0.18)), rgba(255,255,255,0.06)); border: 1px solid rgba(255,255,255,0.08); box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 10px 24px var(--glow, rgba(99,102,241,0.18)); flex-shrink: 0; transition: transform 0.2s ease, background 0.2s ease, box-shadow 0.2s ease; }
.kpi-icon svg { display:block; width:22px; height:22px; transition: transform 0.2s ease, stroke-width 0.2s ease; }
.kpi-card:hover .kpi-icon { transform: translateY(-2px); background: rgba(255,255,255,0.08); box-shadow: 0 0 0 1px rgba(255,255,255,0.08), 0 8px 18px var(--glow, rgba(99,102,241,0.22)); }
.kpi-card:hover .kpi-icon svg { transform: scale(1.08); stroke-width: 2.1; }
.kpi-label { font-size: 0.68rem; color: #64748b; letter-spacing: .08em; text-transform: uppercase; font-weight: 600; display: block; }
.kpi-value { font-size: 1.75rem; font-weight: 800; line-height: 1.15; margin-top: 6px; display: block; }
.kpi-sub { font-size: 0.68rem; color: #475569; margin-top: 6px; display: block; }

.progress-bar-wrap { background: rgba(255,255,255,0.06); border-radius: 99px; height: 6px; overflow: hidden; margin-top: 10px; }
.progress-bar-fill { height: 100%; border-radius: 99px; }

/* Glassmorphic Tabs */
.stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,0.04); border-radius: 12px; padding: 4px; gap: 4px; border: 1px solid rgba(255,255,255,0.06); }
.stTabs [data-baseweb="tab"] { border-radius: 8px; color: #94a3b8; font-weight: 600; font-size: 0.85rem; padding: 8px 18px; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important; }

.stButton > button { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border: none; border-radius: 10px; font-weight: 600; padding: 10px 22px; }

/* Global Focus & Input Overrides */
* { outline: none !important; }
*:focus, *:active, *:focus-visible { outline: none !important; }

/* ── Widget backgrounds ── */
/* Text inputs, text areas & date inputs */
div[data-testid="stTextInput"] [data-baseweb="input"],
div[data-testid="stTextArea"] [data-baseweb="textarea"],
div[data-testid="stDateInput"] [data-baseweb="input"] {
  background: #2a2d3e !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 14px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div[data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
div[data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within,
div[data-testid="stDateInput"] [data-baseweb="input"]:focus-within {
  border-color: rgba(99, 102, 241, 0.8) !important;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}
div[data-testid="stTextInput"] [data-baseweb="base-input"],
div[data-testid="stTextArea"] [data-baseweb="base-input"],
div[data-testid="stDateInput"] [data-baseweb="base-input"] {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}
div[data-testid="stTextInput"] [data-baseweb="base-input"]:hover,
div[data-testid="stTextArea"] [data-baseweb="base-input"]:hover,
div[data-testid="stDateInput"] [data-baseweb="base-input"]:hover {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input {
  background: transparent !important;
  border: none !important;
  color: #f1f5f9 !important;
}

/* Selectbox */
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: #2a2d3e !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 14px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover {
  border-color: rgba(99,102,241,0.5) !important;
  background: #32364a !important;
}
/* Make selectbox input text visible but keep it minimal */
div[data-testid="stSelectbox"] input {
  color: #f1f5f9 !important;
  caret-color: transparent !important;
}
/* Style the dropdown list */
[data-baseweb="popover"] [data-baseweb="menu"] {
  background: #1e2130 !important;
  border: 1px solid rgba(99,102,241,0.3) !important;
  border-radius: 12px !important;
}
[data-baseweb="popover"] [role="option"] {
  background: transparent !important;
  color: #e2e8f0 !important;
  border-radius: 8px !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [aria-selected="true"] {
  background: rgba(99,102,241,0.2) !important;
  color: #a5b4fc !important;
}

input:-webkit-autofill {
  -webkit-text-fill-color: #f1f5f9 !important;
  -webkit-box-shadow: 0 0 0px 1000px #2a2d3e inset !important;
}
::selection { background: rgba(99,102,241,0.3); color: white; }
div[data-testid="InputInstructions"] { display: none !important; }

.sidebar-title {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #e2e8f0;
    font-size: 1.08rem;
    font-weight: 800;
    line-height: 1.2;
    margin: 0.25rem 0 0.9rem 0;
}
.sidebar-title svg {
    width: 32px;
    height: 32px;
    flex: 0 0 32px;
    padding: 7px;
    border-radius: 10px;
    background: linear-gradient(135deg, rgba(99,102,241,0.24), rgba(139,92,246,0.1));
    border: 1px solid rgba(165,180,252,0.18);
    stroke: #a5b4fc;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.1), 0 8px 18px rgba(99,102,241,0.13);
    transition: transform 0.2s ease, stroke 0.2s ease, filter 0.2s ease;
}
.sidebar-title:hover svg {
    transform: translateY(-2px);
    stroke: #c4b5fd;
    filter: drop-shadow(0 6px 10px rgba(99,102,241,0.22));
}

.chart-title {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #f8fafc;
    font-size: 1.55rem;
    font-weight: 800;
    line-height: 1.2;
    margin: 0 0 0.75rem 0;
}
.chart-title svg {
    width: 36px;
    height: 36px;
    flex: 0 0 36px;
    padding: 8px;
    border-radius: 10px;
    background: linear-gradient(135deg, rgba(99,102,241,0.22), rgba(139,92,246,0.1));
    border: 1px solid rgba(165,180,252,0.18);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.1), 0 8px 20px rgba(99,102,241,0.14);
    stroke: #a5b4fc;
    transition: transform 0.2s ease, stroke 0.2s ease, filter 0.2s ease;
}
.chart-title:hover svg {
    transform: translateY(-2px);
    stroke: #c4b5fd;
    filter: drop-shadow(0 6px 10px rgba(99,102,241,0.25));
}

/* No Results Styling */
.no-results-card {
    background: rgba(255,255,255,0.02);
    border: 1px dashed rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 40px 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: #64748b;
    margin-top: 10px;
    min-height: 250px;
}
.no-results-icon { font-size: 3rem; margin-bottom: 16px; opacity: 0.5; }
.no-results-title { font-size: 1.1rem; font-weight: 600; color: #94a3b8; margin-bottom: 4px; }
.no-results-sub { font-size: 0.85rem; max-width: 250px; }
</style>
<svg width="0" height="0">
  <defs>
    <linearGradient id="svg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop stop-color="#ec4899" offset="0%" />
      <stop stop-color="#8b5cf6" offset="100%" />
    </linearGradient>
  </defs>
</svg>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
if "is_admin"        not in st.session_state: st.session_state.is_admin        = False
if "login_step"      not in st.session_state: st.session_state.login_step      = 0   # 0=closed, 1=username, 2=password
if "login_uid_input" not in st.session_state: st.session_state.login_uid_input = ""
if "drawer_open"     not in st.session_state: st.session_state.drawer_open     = False
if "submit_msg"      not in st.session_state: st.session_state.submit_msg      = None
if "new_complaint_id" not in st.session_state:
    st.session_state.new_complaint_id = None
if "last_complaint_receipt" not in st.session_state:
    st.session_state.last_complaint_receipt = None


# ── Data Helpers ───────────────────────────────────────────────────────────────
try:
    init_db()
except Exception as e:
    st.error(f"Database initialization failed: {e}")


@st.cache_data(ttl=30)
def load_all() -> pd.DataFrame:
    df = read_complaints_df()
    for col in ["state", "district", "municipality", "village", "pincode"]:
        if col not in df.columns:
            df[col] = None
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"]  = pd.to_datetime(df["closed_date"],  errors="coerce")
    df["closure_days"] = (df["closed_date"] - df["created_date"]).dt.days
    return df


def filter_df(df, start, end, state, district, municipality, village, area, pincode, category, status):
    f = df.copy()
    f = f[f["created_date"].dt.date >= start]
    f = f[f["created_date"].dt.date <= end]
    if state:        f = f[f["state"].fillna("").astype(str)        == state]
    if district:     f = f[f["district"].fillna("").astype(str)     == district]
    if municipality: f = f[f["municipality"].fillna("").astype(str) == municipality]
    if village:      f = f[f["village"].fillna("").astype(str)      == village]
    if area:         f = f[f["area"].fillna("").astype(str)         == area]
    if pincode:      f = f[f["pincode"].fillna("").astype(str)      == pincode]
    if category != "All": f = f[f["category"] == category]
    if status   != "All": f = f[f["status"]   == status]
    return f.sort_values("created_date", ascending=False)


def _refresh():
    st.cache_data.clear()


def get_next_complaint_id() -> str:
    return generate_next_id_supabase() if using_supabase() else generate_next_id()


def infer_priority(description: str, category: str) -> str:
    text = f"{category} {description}".lower()
    high_terms = [
        "urgent", "emergency", "danger", "hazard", "sewage", "overflow",
        "contamination", "accident", "fire", "flood", "blocked", "leak",
    ]
    medium_terms = ["broken", "delay", "damaged", "repair", "outage", "garbage", "drainage"]
    if any(term in text for term in high_terms):
        return "High"
    if any(term in text for term in medium_terms):
        return "Medium"
    return "Low"


def build_receipt(complaint: dict[str, object]) -> str:
    fields = [
        ("Complaint ID", complaint["id"]),
        ("Date", complaint["created_date"]),
        ("State", complaint.get("state") or "Not provided"),
        ("District", complaint.get("district") or "Not provided"),
        ("Municipality", complaint.get("municipality") or "Not provided"),
        ("Village", complaint.get("village") or "Not provided"),
        ("Area", complaint["area"]),
        ("Pincode", complaint.get("pincode") or "Not provided"),
        ("Category", complaint["category"]),
        ("Priority", complaint["priority"] or "Not set"),
        ("Status", complaint["status"]),
        ("Submitted By", complaint.get("user_contact") or "Not provided"),
        ("Image", complaint.get("image_path") or "No image attached"),
        ("Description", complaint["description"]),
    ]
    lines = ["Complaint Receipt", "=================", ""]
    lines.extend(f"{label}: {value}" for label, value in fields)
    return "\n".join(lines)


def is_valid_contact(value: str) -> bool:
    value = value.strip()
    email_ok = re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value)
    mobile_ok = re.fullmatch(r"\+?[0-9][0-9\s-]{7,14}[0-9]", value)
    return bool(email_ok or mobile_ok)


def is_valid_pincode(value: str) -> bool:
    return bool(re.fullmatch(r"[1-9][0-9]{5}", value.strip()))


def build_location_options(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    return sorted(
        {
            value.strip()
            for value in df[column].dropna().astype(str)
            if value.strip()
        }
    )


def build_form_location_options(saved_options: list[str], fallback_options: list[str] | None = None) -> list[str]:
    fallback_options = fallback_options or []
    options = sorted({*saved_options, *fallback_options})
    return ["Not provided", *options]


def filter_location_rows(df: pd.DataFrame, filters: dict[str, str]) -> pd.DataFrame:
    filtered = df.copy()
    for column, value in filters.items():
        if value and value != "Not provided" and column in filtered.columns:
            filtered = filtered[filtered[column].fillna("").astype(str) == value]
    return filtered


def build_cascading_location_options(
    df: pd.DataFrame,
    column: str,
    filters: dict[str, str],
    fallback_options: list[str] | None = None,
) -> list[str]:
    filtered = filter_location_rows(df, filters)
    return build_form_location_options(build_location_options(filtered, column), fallback_options)


def select_valid_option(label: str, options: list[str], key: str, container=st) -> str:
    if key in st.session_state and st.session_state[key] not in options:
        # Try to find a case-insensitive match first
        current_val = st.session_state[key]
        match = next((o for o in options if o.lower() == current_val.lower()), None)
        if match:
            st.session_state[key] = match
        else:
            # Add the auto-filled value to options so it's selectable
            options = [current_val, *options]
    return container.selectbox(label, options, key=key)


def notify_user(contact: str, message: str) -> None:
    """Send a notification (email or SMS) to the user based on their contact.
    Routes to Gmail SMTP for emails and Twilio for phone numbers.
    Falls back to an in-app info banner if credentials are not configured.
    """
    contact = (contact or "").strip()
    if not contact:
        return
    subject = "Complaint Analytics Dashboard - Update"
    if _NOTIFIER_AVAILABLE:
        try:
            _notify_real(contact, subject, message)
            return
        except Exception as exc:
            st.warning(f"Notification delivery failed: {exc}")
    # Fallback: show in-app banner
    st.info(f"Notification to **{contact}**: {message}")


def save_uploaded_image(uploaded_file, complaint_id: str) -> str | None:
    if uploaded_file is None:
        return None
    file_name = getattr(uploaded_file, "name", "") or "attachment.jpg"
    suffix = Path(file_name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    filename = f"{complaint_id}_{uuid.uuid4().hex[:8]}{suffix}"
    path = UPLOAD_DIR / filename
    path.write_bytes(uploaded_file.getvalue())
    return str(path.relative_to(PROJECT_ROOT))


def auto_fill_location_from_pincode(pincode: str, location_key: int) -> dict[str, str] | None:
    """
    Auto-fill location details from pincode.
    Updates session state if valid pincode is provided.
    
    Args:
        pincode: 6-digit Indian pincode
        location_key: Key for session state storage
        
    Returns:
        Dictionary with state, district, municipality, village if found, else None
    """
    if not pincode or not is_valid_pincode(pincode):
        return None
    
    location_data = get_location_from_pincode(pincode)
    if location_data:
        # Update session state with auto-filled values
        st.session_state[f"new_state_f_{location_key}"] = location_data.get("state", "Not provided")
        st.session_state[f"new_district_f_{location_key}"] = location_data.get("district", "Not provided")
        st.session_state[f"new_municipality_f_{location_key}"] = location_data.get("municipality", "Not provided")
        st.session_state[f"new_village_f_{location_key}"] = location_data.get("village", "Not provided")
        return location_data
    return None


def build_area_options(saved_areas: list[str]) -> list[str]:
    custom_areas = [
        area.strip()
        for area in saved_areas
        if isinstance(area, str)
        and area.strip()
        and area.strip() not in GENERIC_AREA_LABELS
    ]
    return sorted({*INDIAN_LOCATIONS, *custom_areas})


LOCATION_FIELDS = ("state", "district", "municipality", "village", "area", "pincode")


def _clean_location_value(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def format_combined_location(location: dict[str, str]) -> str:
    if location.get("label"):
        return location["label"]
    filled_parts = [
        (field, location.get(field))
        for field in LOCATION_FIELDS
        if field != "pincode" and location.get(field)
    ]
    if len(filled_parts) == 1:
        field, value = filled_parts[0]
        return value
    parts = [value for _, value in filled_parts]
    label = ", ".join(part for part in parts if part)
    pincode = location.get("pincode")
    if pincode:
        label = f"{label} - {pincode}" if label else pincode
    if label:
        return label
    for field in LOCATION_FIELDS:
        if location.get(field):
            return location[field]
    return "Select location"


def build_combined_location_options(df: pd.DataFrame, area_options: list[str]) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()

    def add_location(location: dict[str, str]) -> None:
        cleaned = {field: _clean_location_value(location.get(field)) for field in LOCATION_FIELDS}
        if not any(cleaned.values()):
            return
        key = tuple(cleaned[field].casefold() for field in LOCATION_FIELDS)
        if key in seen:
            return
        seen.add(key)
        options.append(cleaned)

    if not df.empty:
        for _, row in df.iterrows():
            add_location({field: row.get(field, "") for field in LOCATION_FIELDS})

    for area in area_options:
        add_location({"area": area})

    return sorted(options, key=format_combined_location)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('## Analytics Dashboard')
    st.markdown("---")

    all_df = load_all()
    saved_areas = all_df["area"].dropna().astype(str).unique().tolist()
    areas      = build_area_options(saved_areas)
    combined_locations = build_combined_location_options(all_df, areas)
    location_filter_options = [{"label": "All locations"}, *combined_locations]
    state_options = build_form_location_options(build_location_options(all_df, "state"), INDIAN_STATES)
    categories = sorted({"General", *all_df["category"].dropna().unique().tolist()})
    statuses   = sorted(all_df["status"].dropna().unique().tolist())    or ["Pending"]

    st.markdown("""<div class="sidebar-title"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="21" y1="4" x2="14" y2="4"/><line x1="10" y1="4" x2="3" y2="4"/><circle cx="12" cy="4" r="2"/><line x1="21" y1="12" x2="12" y2="12"/><line x1="8" y1="12" x2="3" y2="12"/><circle cx="10" cy="12" r="2"/><line x1="21" y1="20" x2="16" y2="20"/><line x1="12" y1="20" x2="3" y2="20"/><circle cx="14" cy="20" r="2"/></svg><span>Filters</span></div>""", unsafe_allow_html=True)
    start_date = st.date_input("Start Date", value=date(2025, 1, 1), format="DD/MM/YYYY")
    end_date   = st.date_input("End Date",   value=date.today(), format="DD/MM/YYYY")

    if start_date > end_date:
        st.warning("Start date is after end date")

    sel_location = st.selectbox(
        "Location",
        location_filter_options,
        format_func=format_combined_location,
    )
    sel_category = st.selectbox("Category", ["All", *categories])
    sel_status   = st.selectbox("Status",   ["All", *statuses])

    st.markdown("---")
    st.markdown("""<div class="sidebar-title"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg><span>Admin Login</span></div>""", unsafe_allow_html=True)

    if st.session_state.is_admin:
        st.success("Admin mode active")
        if st.button("Logout", use_container_width=True):
            st.session_state.is_admin    = False
            st.session_state.login_step  = 0
            st.session_state.drawer_open = False
            st.rerun()

    elif st.session_state.login_step == 1:
        st.markdown("""<div class="sidebar-title"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V8a5 5 0 0 1 10 0v3"/></svg><span>Admin Login</span></div>""", unsafe_allow_html=True)
        uid = st.text_input("Admin Name", placeholder="Enter Admin Name", key="uid_field", label_visibility="collapsed")
        next_clicked = st.button("Next", use_container_width=True)

        if next_clicked:
            if uid.strip() == ADMIN_USERNAME:
                st.session_state.login_uid_input = uid.strip()
                st.session_state.login_step = 2
                st.rerun()
            else:
                st.error("Username not found")

        if st.button("Cancel", use_container_width=True):
            st.session_state.login_step = 0
            st.rerun()

    elif st.session_state.login_step == 2:
        st.markdown(f"""<div class="sidebar-title"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M6 21v-2a6 6 0 0 1 12 0v2"/></svg><span>Hi, {st.session_state.login_uid_input}</span></div>""", unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", placeholder="Enter Password", key="pwd_field", label_visibility="collapsed")
        login_clicked = st.button("Login", use_container_width=True)

        if login_clicked:
            if pwd == ADMIN_PASSWORD:
                st.session_state.is_admin    = True
                st.session_state.login_step  = 0
                st.session_state.drawer_open = True
                st.rerun()
            else:
                st.error("Incorrect password")

        if st.button("Back", use_container_width=True):
            st.session_state.login_step = 1
            st.rerun()
    else:
        if st.button("Login", use_container_width=True):
            st.session_state.login_step = 1
            st.rerun()
af = {
    "start_date": start_date,
    "end_date": end_date,
    "state": sel_location.get("state", ""),
    "district": sel_location.get("district", ""),
    "municipality": sel_location.get("municipality", ""),
    "village": sel_location.get("village", ""),
    "area": sel_location.get("area", ""),
    "pincode": sel_location.get("pincode", ""),
    "category": sel_category,
    "status": sel_status,
}
df = filter_df(
    all_df,
    af["start_date"],
    af["end_date"],
    af["state"],
    af["district"],
    af["municipality"],
    af["village"],
    af["area"],
    af["pincode"],
    af["category"],
    af["status"],
)

# ── Analytics ─────────────────────────────────────────────────────────────────
total     = len(df)
closed_df = df[df["status"] == "Closed"]
open_cnt  = len(df[df["status"] != "Closed"])
raw_avg   = closed_df["closure_days"].mean() if not closed_df.empty else 0.0
avg_days  = float(raw_avg) if not pd.isna(raw_avg) else 0.0
rate      = round((len(closed_df) / total) * 100, 2) if total else 0.0
rate_w    = min(int(rate), 100)

trend_df = (
    df.assign(month=df["created_date"].dt.to_period("M").astype(str))
    .groupby("month").size().reset_index(name="complaints").sort_values("month")
) if not df.empty else pd.DataFrame()

area_df = (
    df.groupby("area")
    .agg(complaints=("id","count"), avg_closure_days=("closure_days","mean"))
    .reset_index().sort_values("complaints", ascending=False)
) if not df.empty else pd.DataFrame()

category_df = (
    df.groupby("category").size().reset_index(name="complaints")
    .sort_values("complaints", ascending=False)
) if not df.empty else pd.DataFrame()

# ── Main Layout ────────────────────────────────────────────────────────────────
main_col = st.container()

with main_col:
    date_range = f"{af['start_date'].strftime('%b %d')} to {af['end_date'].strftime('%b %d, %Y')}"
    admin_badge = '<span class="header-badge" style="background:rgba(99,102,241,0.3);border-color:rgba(139,92,246,0.6)"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Admin</span>' if st.session_state.is_admin else ""

    st.markdown(f"""
<div class="page-header">
  <div class="page-header-title">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
    Complaint Analytics
  </div>
  <div class="page-header-sub">Real-time public service complaint intelligence dashboard</div>
  <div class="header-badges">
    <span class="header-badge" id="live-clock-badge">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      <span id="live-clock">--</span>
    </span>
    <span class="header-badge">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      {date_range}
    </span>
    {admin_badge}
  </div>
</div>
""", unsafe_allow_html=True)

    components.html("""
<script>
  (function() {
    function updateClock() {
      var clock = window.parent.document.getElementById('live-clock');
      if (!clock) {
        return;
      }
      var now = new Date();
      var options = {
        month: 'short',
        day: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      };
      clock.textContent = new Intl.DateTimeFormat(undefined, options).format(now);
    }
    updateClock();
    if (window.parent.liveClockInterval) {
      window.parent.clearInterval(window.parent.liveClockInterval);
    }
    window.parent.liveClockInterval = window.parent.setInterval(updateClock, 1000);
  })();
</script>
""", height=0)

    st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card" style="--accent:linear-gradient(90deg,#6366f1,#8b5cf6);--icon-bg:rgba(99,102,241,0.15);--glow:rgba(99,102,241,0.35)">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
        <rect x="9" y="3" width="6" height="4" rx="1"/>
        <line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/>
      </svg>
    </div>
    <span class="kpi-label">TOTAL COMPLAINTS</span>
    <span class="kpi-value" style="color:#f1f5f9">{total:,}</span>
    <span class="kpi-sub">In selected range</span>
  </div>
  <div class="kpi-card" style="--accent:linear-gradient(90deg,#10b981,#34d399);--icon-bg:rgba(16,185,129,0.15);--glow:rgba(16,185,129,0.35)">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#6ee7b7" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
    </div>
    <span class="kpi-label">CLOSED</span>
    <span class="kpi-value" style="color:#6ee7b7">{len(closed_df):,}</span>
    <span class="kpi-sub">Fully resolved</span>
  </div>
  <div class="kpi-card" style="--accent:linear-gradient(90deg,#f59e0b,#fbbf24);--icon-bg:rgba(245,158,11,0.15);--glow:rgba(245,158,11,0.35)">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#fcd34d" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
    </div>
    <span class="kpi-label">OPEN / PENDING</span>
    <span class="kpi-value" style="color:#fcd34d">{open_cnt:,}</span>
    <span class="kpi-sub">Awaiting resolution</span>
  </div>
  <div class="kpi-card" style="--accent:linear-gradient(90deg,#3b82f6,#60a5fa);--icon-bg:rgba(59,130,246,0.15);--glow:rgba(59,130,246,0.35)">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#93c5fd" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
        <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>
      </svg>
    </div>
    <span class="kpi-label">AVG CLOSURE TIME</span>
    <span class="kpi-value" style="color:#93c5fd">{avg_days:.1f} <span style="font-size:0.9rem;color:#64748b">days</span></span>
    <span class="kpi-sub">To close</span>
  </div>
  <div class="kpi-card" style="--accent:linear-gradient(90deg,#8b5cf6,#a78bfa);--icon-bg:rgba(139,92,246,0.15);--glow:rgba(139,92,246,0.35)">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#c4b5fd" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
        <line x1="6" y1="20" x2="6" y2="14"/>
        <polyline points="3 7 12 2 21 7"/>
      </svg>
    </div>
    <span class="kpi-label">CLOSURE RATE</span>
    <span class="kpi-value" style="color:#c4b5fd">{rate:.1f}<span style="font-size:0.9rem;color:#64748b">%</span></span>
    <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width:{rate_w}%;background:linear-gradient(90deg,#8b5cf6,#a78bfa)"></div></div>
  </div>
</div>
""", unsafe_allow_html=True)

    CHART_LAYOUT = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", size=11),
        margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#f1f5f9")),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=False),
    )

    tab_overview, tab_records, tab_submit = st.tabs(["Overview", "Records", "Raise a Complaint"])

    with tab_overview:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""<div class="chart-title"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 17 9 11 13 15 21 7"/><polyline points="14 7 21 7 21 14"/></svg><span>Monthly Trend</span></div>""", unsafe_allow_html=True)
            if not trend_df.empty:
                fig = go.Figure(go.Scatter(
                    x=trend_df["month"], y=trend_df["complaints"],
                    mode="lines+markers", line=dict(color="#6366f1", width=2.5),
                    marker=dict(size=7, color="#8b5cf6"),
                    fill="tozeroy", fillcolor="rgba(99,102,241,0.1)"
                ))
                fig.update_layout(**CHART_LAYOUT, height=280)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown("""
                <div class="no-results-card">
                    <div class="no-results-icon">No data</div>
                    <div class="no-results-title">No Trend Data</div>
                    <div class="no-results-sub">Adjust your filters to see monthly complaint trends</div>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("""<div class="chart-title"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12c0 4.97-4.03 9-9 9S3 16.97 3 12s4.03-9 9-9v9h9z"/><path d="M13 2.05A9 9 0 0 1 21.95 11H13V2.05z"/></svg><span>Category Distribution</span></div>""", unsafe_allow_html=True)
            if not category_df.empty:
                fig = go.Figure(go.Pie(
                    labels=category_df["category"], values=category_df["complaints"],
                    hole=0.6, marker=dict(colors=["#6366f1","#8b5cf6","#a78bfa","#c4b5fd"])
                ))
                fig.update_layout(**CHART_LAYOUT, height=280)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown("""
                <div class="no-results-card">
                    <div class="no-results-icon">No data</div>
                    <div class="no-results-title">No Category Data</div>
                    <div class="no-results-sub">No categories found in the selected range</div>
                </div>
                """, unsafe_allow_html=True)

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("""<div class="chart-title"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-4.35 7-11a7 7 0 1 0-14 0c0 6.65 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></svg><span>Complaints by Area</span></div>""", unsafe_allow_html=True)
            if not area_df.empty:
                sorted_area = area_df.sort_values("complaints")
                AREA_PALETTE = [
                    "#6366f1","#8b5cf6","#a78bfa","#c4b5fd",
                    "#3b82f6","#60a5fa","#10b981","#34d399",
                    "#f59e0b","#fbbf24","#ef4444","#f87171",
                    "#ec4899","#f472b6","#14b8a6","#2dd4bf",
                ]
                n = len(sorted_area)
                bar_colors = [AREA_PALETTE[i % len(AREA_PALETTE)] for i in range(n)]
                fig = go.Figure(go.Bar(
                    x=sorted_area["complaints"], y=sorted_area["area"],
                    orientation="h", marker=dict(color=bar_colors),
                    text=sorted_area["complaints"], textposition="outside",
                    textfont=dict(color="#94a3b8", size=11),
                ))
                fig.update_layout(**CHART_LAYOUT, height=max(280, n * 36))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown("""
                <div class="no-results-card">
                    <div class="no-results-icon">No data</div>
                    <div class="no-results-title">No Area Data</div>
                    <div class="no-results-sub">No area distribution available for these filters</div>
                </div>
                """, unsafe_allow_html=True)

        with col4:
            st.markdown("""<div class="chart-title"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg><span>Avg Closure Days</span></div>""", unsafe_allow_html=True)
            if not area_df.empty and "avg_closure_days" in area_df.columns:
                plot_df = area_df.dropna(subset=["avg_closure_days"])
                if not plot_df.empty:
                    fig = go.Figure(go.Bar(
                        x=plot_df["area"], y=plot_df["avg_closure_days"],
                        marker=dict(color=plot_df["avg_closure_days"], colorscale="RdYlGn_r")
                    ))
                    fig.update_layout(**CHART_LAYOUT, height=280)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.markdown("""
                    <div class="no-results-card">
                        <div class="no-results-icon">No data</div>
                        <div class="no-results-title">No Closure Data</div>
                        <div class="no-results-sub">Not enough closed complaints to calculate averages</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="no-results-card">
                    <div class="no-results-icon">No data</div>
                    <div class="no-results-title">No Data</div>
                    <div class="no-results-sub">Select a broader range to see closure time analytics</div>
                </div>
                """, unsafe_allow_html=True)

    with tab_records:
        st.subheader("Complaint Records")
        display_df = df.drop(columns=["closure_days"], errors="ignore").copy()
        for col in ["created_date", "closed_date"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else ""
                )
        if not display_df.empty:
            st.dataframe(display_df, use_container_width=True, height=400, hide_index=True)
            csv_data = display_df.to_csv(index=False).encode("utf-8")
            st.download_button("Export CSV", data=csv_data, file_name="complaints_export.csv", mime="text/csv")
        else:
            st.markdown("""
            <div class="no-results-card" style="min-height: 400px;">
                <div class="no-results-icon">No records</div>
                <div class="no-results-title">No Matching Records</div>
                <div class="no-results-sub">Try adjusting your filters or search criteria in the sidebar to find records.</div>
            </div>
            """, unsafe_allow_html=True)

    with tab_submit:
        def handle_complaint_submission():
            selected_location = {
                "state": "" if new_state == "Not provided" else new_state,
                "district": "" if new_district == "Not provided" else new_district,
                "municipality": "" if new_municipality == "Not provided" else new_municipality,
                "area": "" if new_area == "Not provided" else new_area,
                "village": "" if new_village == "Not provided" else new_village,
                "pincode": new_pincode.strip(),
            }
            final_area = next(
                (
                    selected_location[field].strip()
                    for field in ("area", "village", "municipality", "district", "state")
                    if selected_location[field].strip()
                ),
                "",
            )
            final_category = new_category
            final_contact = user_contact.strip()
            final_pincode = selected_location["pincode"]
            image_file = camera_file or uploaded_file
            final_desc = new_desc.strip()
            final_priority = compute_priority(final_desc)
            if len(final_area) < 2:
                st.error("Area must be at least 2 characters")
            elif len(final_area) > 80:
                st.error("Area must be 80 characters or fewer")
            elif len(final_category) < 2:
                st.error("Category must be at least 2 characters")
            elif final_contact and not is_valid_contact(final_contact):
                st.error("Enter a valid email ID or mobile number")
            elif final_pincode and not is_valid_pincode(final_pincode):
                st.error("Enter a valid 6-digit Indian PIN code")
            elif new_date > date.today():
                st.error("Complaint date cannot be in the future")
            elif image_mode != "No image" and not image_file:
                st.error("Please attach an image (take a photo or upload a file) before submitting")
            elif image_mode != "No image" and not photo_verified:
                st.error("Verify the attached image before submitting")
            elif image_file and len(image_file.getvalue()) > MAX_IMAGE_BYTES:
                st.error("Image must be 5 MB or smaller")
            elif len(final_desc) < 10:
                st.error("Description too short")
            elif len(final_desc) > MAX_DESCRIPTION_LENGTH:
                st.error(f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer")
            else:
                try:
                    image_path = save_uploaded_image(image_file, new_id.strip())
                    created = insert_complaint({
                        "id": new_id.strip(),
                        "created_date": new_date.isoformat(),
                        "closed_date": None,
                        "state": selected_location.get("state") or None,
                        "district": selected_location.get("district") or None,
                        "municipality": selected_location.get("municipality") or None,
                        "village": selected_location.get("village") or None,
                        "area": final_area,
                        "pincode": final_pincode or None,
                        "category": final_category,
                        "priority": final_priority,
                        "status": "Pending",
                        "description": final_desc,
                        "user_contact": final_contact or None,
                        "image_path": image_path,
                    })
                    st.session_state.submit_msg = f"Complaint {new_id} registered"
                    st.session_state.last_complaint_receipt = created
                    if final_contact:
                        notify_user(
                            final_contact,
                            f"Your complaint <b>{new_id}</b> has been registered successfully. "
                            "Our team will review it shortly. You can track its status on the dashboard.",
                        )
                    st.session_state.form_key_f += 1
                    st.session_state.new_complaint_id = get_next_complaint_id()
                    _refresh()
                    st.rerun()
                except DuplicateComplaintError:
                    st.error("Complaint ID already exists")
                except Exception as e:
                    st.error(f"Failed to save complaint: {e}")

        # Removed external submit button to avoid duplicate submissions
        
        if st.session_state.submit_msg:
            st.success(st.session_state.submit_msg)
            st.session_state.submit_msg = None
        if st.session_state.last_complaint_receipt:
            receipt = st.session_state.last_complaint_receipt
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Complaint ID", receipt["id"])
            r2.metric("Status", receipt["status"])
            r3.metric("Priority", receipt["priority"] or "Not set")
            r4.metric("Area", receipt["area"])
            location_bits = [
                receipt.get("village"),
                receipt.get("municipality"),
                receipt.get("district"),
                receipt.get("state"),
                receipt.get("pincode"),
            ]
            location_text = ", ".join(str(bit) for bit in location_bits if bit)
            if location_text:
                st.caption(f"Location: {location_text}")
            if receipt.get("image_path"):
                receipt_image_path = PROJECT_ROOT / str(receipt["image_path"])
                if receipt_image_path.exists():
                    st.image(str(receipt_image_path), caption="Attached image", use_container_width=True)
            st.download_button(
                "Download Receipt",
                data=build_receipt(receipt).encode("utf-8"),
                file_name=f"{receipt['id']}_receipt.txt",
                mime="text/plain",
                use_container_width=True,
            )

        st.subheader("Raise New Complaint")

        if "form_key_f" not in st.session_state:
            st.session_state.form_key_f = 0
        if not st.session_state.new_complaint_id:
            st.session_state.new_complaint_id = get_next_complaint_id()

        location_key = st.session_state.form_key_f
        st.markdown("Location")
        
        id_col, pincode_col = st.columns([1, 1.5])
        new_id = id_col.text_input("ID", value=st.session_state.new_complaint_id, disabled=True)
        new_pincode = pincode_col.text_input(
            "Pincode (optional)", 
            max_chars=6, 
            key=f"new_pincode_f_{location_key}",
            placeholder="Enter 6-digit pincode to auto-fill location",
            help="Enter a 6-digit pincode to auto-fill location details"
        )
        
        location_auto_filled = False
        if new_pincode and is_valid_pincode(new_pincode):
            auto_fill_result = auto_fill_location_from_pincode(new_pincode, location_key)
            if auto_fill_result:
                # Only update session state if the value is in the available options to avoid resetting
                _af_state = auto_fill_result.get("state", "")
                _af_district = auto_fill_result.get("district", "")
                _af_municipality = auto_fill_result.get("municipality", "")
                _af_village = auto_fill_result.get("village", "")
                if _af_state:
                    st.session_state[f"new_state_f_{location_key}"] = _af_state
                if _af_district:
                    st.session_state[f"new_district_f_{location_key}"] = _af_district
                if _af_municipality:
                    st.session_state[f"new_municipality_f_{location_key}"] = _af_municipality
                if _af_village:
                    st.session_state[f"new_village_f_{location_key}"] = _af_village
                location_auto_filled = True

        if location_auto_filled:
            st.success("Location auto-filled from pincode")

        state_options_form = build_form_location_options(build_location_options(all_df, "state"), INDIAN_STATES)
        state_col, district_col = st.columns([1.1, 1.1])
        new_state = select_valid_option("State", state_options_form, f"new_state_f_{location_key}", state_col)

        district_options = build_cascading_location_options(
            all_df,
            "district",
            {"state": new_state},
            STATE_DISTRICT_OPTIONS.get(new_state, []),
        )
        new_district = select_valid_option("District", district_options, f"new_district_f_{location_key}", district_col)

        muni_col, village_col = st.columns([1.1, 1.1])
        municipality_options = build_form_location_options(
            build_location_options(all_df, "municipality")
        )
        new_municipality = select_valid_option(
            "Municipality (optional)", municipality_options,
            f"new_municipality_f_{location_key}", muni_col
        )
        village_options = build_form_location_options(
            build_location_options(all_df, "village")
        )
        new_village = select_valid_option(
            "Village / Locality (optional)", village_options,
            f"new_village_f_{location_key}", village_col
        )

        new_area = st.text_input(
            "Specific Area / Locality (e.g., Street name, Ward, Landmark)",
            placeholder="Enter the specific location of the issue",
            max_chars=80,
            key=f"new_area_f_{location_key}"
        )
        camera_file = None
        uploaded_file = None
        photo_verified = False

        st.markdown("#### Attach Photo / Image")
        image_mode = st.radio(
            "Choose image source:",
            ["No image", "Take photo", "Upload file"],
            horizontal=True,
            key=f"image_mode_f_{st.session_state.form_key_f}",
        )

        if image_mode == "Take photo":
            st.info("Point your camera at the issue and click **Take Photo**")
            try:
                from streamlit_back_camera_input import back_camera_input
                camera_file = back_camera_input(
                    key=f"new_camera_f_{st.session_state.form_key_f}",
                )
            except Exception:
                camera_file = st.camera_input(
                    "Take a photo of the issue",
                    key=f"new_camera_f_{st.session_state.form_key_f}",
                )
            if camera_file:
                col1, col2 = st.columns([2, 1])
                col1.image(camera_file, caption="Photo Preview", use_container_width=True)
                photo_verified = col2.checkbox(
                    "I verify this photo is accurate and relevant to my complaint",
                    key=f"verify_camera_f_{st.session_state.form_key_f}",
                )
                if photo_verified:
                    col2.success("Photo verified")
                else:
                    col2.warning("Please verify before submitting")

        elif image_mode == "Upload file":
            uploaded_file = st.file_uploader(
                "Upload image file (JPG, PNG, or WebP)",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"new_image_f_{st.session_state.form_key_f}",
                help="Select an image file to attach to your complaint",
            )
            if uploaded_file:
                col1, col2 = st.columns([2, 1])
                col1.image(uploaded_file, caption="Image Preview", use_container_width=True)
                col2.success(f"Attached: {uploaded_file.name}")
                photo_verified = col2.checkbox(
                    "I verify this image is accurate and relevant to my complaint",
                    key=f"verify_upload_f_{st.session_state.form_key_f}",
                )
                if photo_verified:
                    col2.success("Image verified")
                else:
                    col2.warning("Please verify before submitting")

        with st.form("new_complaint", clear_on_submit=False):
            new_category = st.selectbox("Category", categories, key=f"new_category_f_{st.session_state.form_key_f}")
            user_contact = st.text_input(
                "Mobile number or email (optional)",
                placeholder="Add contact details for follow-up",
                key=f"user_contact_f_{st.session_state.form_key_f}",
            )
            new_date = st.date_input(
                "Date",
                value=date.today(),
                max_value=date.today(),
                key=f"new_date_f_{st.session_state.form_key_f}",
                format="DD/MM/YYYY",
            )
            
            new_desc = st.text_area(
                "Description",
                placeholder="Describe the issue, location landmark, and any urgency. Min 10 characters.",
                max_chars=MAX_DESCRIPTION_LENGTH,
                key=f"new_desc_f_{st.session_state.form_key_f}",
            )

            if st.form_submit_button("Submit Complaint"):
                handle_complaint_submission()
            
            

# ── Admin Panel (below dashboard when logged in) ───────────────────────────────
if st.session_state.is_admin:
    st.markdown("---")
    st.subheader("Admin Panel")

    tab_update, tab_delete = st.tabs(["Update Complaint", "Delete Complaint"])

    with tab_update:
        if not df.empty:
            sel_id = st.selectbox("Select Complaint", df["id"].tolist(), key="adm_sel")
            matching_rows = df[df["id"] == sel_id]
            if matching_rows.empty:
                st.warning("Selected complaint not found in filtered data")
            else:
                row    = matching_rows.iloc[0]
                admin_area_options = areas if row["area"] in areas else [str(row["area"]), *areas]
                u1, u2, u3 = st.columns(3)
                upd_status   = u1.selectbox("Status", ["Pending", "In Progress", "Closed"],
                                            index=["Pending", "In Progress", "Closed"].index(row["status"]) if row["status"] in ["Pending", "In Progress", "Closed"] else 0, key="adm_status")
                upd_area     = u2.selectbox("Area", admin_area_options, index=admin_area_options.index(row["area"]) if row["area"] in admin_area_options else 0, key="adm_area")
                upd_priority = u3.selectbox("Priority", ["Low", "Medium", "High"],
                                            index=["Low", "Medium", "High"].index(row["priority"]) if pd.notna(row["priority"]) and row["priority"] in ["Low", "Medium", "High"] else 1, key="adm_pri")
                upd_category = st.selectbox("Category", categories, index=categories.index(row["category"]) if row["category"] in categories else 0, key="adm_cat")
                loc1, loc2, loc3 = st.columns(3)
                upd_state = loc1.text_input("State", value=str(row.get("state") or ""), key="adm_state")
                upd_district = loc2.text_input("District", value=str(row.get("district") or ""), key="adm_district")
                upd_municipality = loc3.text_input("Municipality", value=str(row.get("municipality") or ""), key="adm_municipality")
                loc4, loc5 = st.columns(2)
                upd_village = loc4.text_input("Village", value=str(row.get("village") or ""), key="adm_village")
                upd_pincode = loc5.text_input("Pincode", value=str(row.get("pincode") or ""), max_chars=6, key="adm_pincode")
                upd_closed   = st.date_input("Closed Date", value=date.today(), key="adm_closed", format="DD/MM/YYYY") if upd_status == "Closed" else None
                upd_desc     = st.text_area("Description", value=str(row["description"]) if pd.notna(row["description"]) else "", key="adm_desc")
                if st.button("Save Changes", use_container_width=True, key="adm_save"):
                    closed_val = upd_closed.isoformat() if upd_closed else None
                    final_admin_pincode = upd_pincode.strip()
                    created_for_check = row["created_date"].date() if pd.notna(row["created_date"]) else date.today()
                    if final_admin_pincode and not is_valid_pincode(final_admin_pincode):
                        st.error("Enter a valid 6-digit Indian PIN code")
                        st.stop()
                    if upd_closed and upd_closed < created_for_check:
                        st.error("Closed date cannot be before created date")
                        st.stop()
                    try:
                        update_complaint_record(sel_id, {
                            "created_date": row["created_date"].strftime("%Y-%m-%d") if pd.notna(row["created_date"]) else date.today().isoformat(),
                            "closed_date": closed_val,
                            "state": upd_state.strip() or None,
                            "district": upd_district.strip() or None,
                            "municipality": upd_municipality.strip() or None,
                            "village": upd_village.strip() or None,
                            "area": upd_area,
                            "pincode": final_admin_pincode or None,
                            "category": upd_category,
                            "priority": upd_priority,
                            "status": upd_status,
                            "description": upd_desc,
                        })
                        st.success(f"Updated {sel_id}")
                        # Notify complainant if complaint was just closed
                        if upd_status == "Closed":
                            complainant_contact = str(row.get("user_contact") or "")
                            if complainant_contact:
                                notify_user(
                                    complainant_contact,
                                    f"Your complaint <b>{sel_id}</b> has been marked as <b>Closed</b>. "
                                    "Thank you for reaching out - our team has resolved your issue!",
                                )
                        _refresh()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update complaint: {e}")
        else:
            st.info("No complaints available.")

    with tab_delete:
        if not df.empty:
            del_id = st.selectbox("Select to Delete", df["id"].tolist(), key="adm_del")
            st.warning(f"This will permanently delete **{del_id}**.")
            if st.button("Confirm Delete", type="primary", use_container_width=True, key="adm_del_btn"):
                try:
                    delete_complaint_record(del_id)
                    st.success(f"Deleted {del_id}")
                    _refresh()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete complaint: {e}")
        else:
            st.info("No complaints available.")
