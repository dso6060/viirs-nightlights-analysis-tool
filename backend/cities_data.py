"""
Comprehensive city data for 140+ cities worldwide.

Includes major metropolitan areas, industrial cities, and diverse geographic locations
for comprehensive VIIRS nightlights testing and analysis.
"""

# 140+ cities with coordinates and metadata
CITIES_DATA = [
    # Major Indian Cities
    {"name": "Mumbai", "country": "India", "lat": 19.0760, "lon": 72.8777, "radius_km": 20.0, "category": "metropolitan"},
    {"name": "Delhi", "country": "India", "lat": 28.7041, "lon": 77.1025, "radius_km": 25.0, "category": "metropolitan"},
    {"name": "Bengaluru", "country": "India", "lat": 12.9716, "lon": 77.5946, "radius_km": 18.0, "category": "tech_hub"},
    {"name": "Chennai", "country": "India", "lat": 13.0827, "lon": 80.2707, "radius_km": 15.0, "category": "industrial"},
    {"name": "Kolkata", "country": "India", "lat": 22.5726, "lon": 88.3639, "radius_km": 20.0, "category": "metropolitan"},
    {"name": "Hyderabad", "country": "India", "lat": 17.3850, "lon": 78.4867, "radius_km": 15.0, "category": "tech_hub"},
    {"name": "Pune", "country": "India", "lat": 18.5204, "lon": 73.8567, "radius_km": 12.0, "category": "industrial"},
    {"name": "Ahmedabad", "country": "India", "lat": 23.0225, "lon": 72.5714, "radius_km": 15.0, "category": "industrial"},
    {"name": "Jaipur", "country": "India", "lat": 26.9124, "lon": 75.7873, "radius_km": 12.0, "category": "cultural"},
    {"name": "Surat", "country": "India", "lat": 21.1702, "lon": 72.8311, "radius_km": 10.0, "category": "industrial"},
    {"name": "Tiruppur", "country": "India", "lat": 11.1085, "lon": 77.3411, "radius_km": 8.0, "category": "textile_hub"},
    {"name": "Coimbatore", "country": "India", "lat": 11.0168, "lon": 76.9558, "radius_km": 10.0, "category": "industrial"},
    {"name": "Kochi", "country": "India", "lat": 9.9312, "lon": 76.2673, "radius_km": 8.0, "category": "port_city"},
    {"name": "Indore", "country": "India", "lat": 22.7196, "lon": 75.8577, "radius_km": 10.0, "category": "commercial"},
    {"name": "Bhopal", "country": "India", "lat": 23.2599, "lon": 77.4126, "radius_km": 8.0, "category": "administrative"},
    {"name": "Visakhapatnam", "country": "India", "lat": 17.6868, "lon": 83.2185, "radius_km": 12.0, "category": "port_city"},
    {"name": "Vadodara", "country": "India", "lat": 22.3072, "lon": 73.1812, "radius_km": 8.0, "category": "industrial"},
    {"name": "Ludhiana", "country": "India", "lat": 30.9010, "lon": 75.8573, "radius_km": 8.0, "category": "industrial"},
    {"name": "Nashik", "country": "India", "lat": 19.9975, "lon": 73.7898, "radius_km": 8.0, "category": "industrial"},
    {"name": "Madurai", "country": "India", "lat": 9.9252, "lon": 78.1198, "radius_km": 8.0, "category": "cultural"},
    
    # Major Chinese Cities
    {"name": "Shanghai", "country": "China", "lat": 31.2304, "lon": 121.4737, "radius_km": 30.0, "category": "metropolitan"},
    {"name": "Beijing", "country": "China", "lat": 39.9042, "lon": 116.4074, "radius_km": 25.0, "category": "metropolitan"},
    {"name": "Guangzhou", "country": "China", "lat": 23.1291, "lon": 113.2644, "radius_km": 20.0, "category": "metropolitan"},
    {"name": "Shenzhen", "country": "China", "lat": 22.5431, "lon": 114.0579, "radius_km": 18.0, "category": "tech_hub"},
    {"name": "Tianjin", "country": "China", "lat": 39.3434, "lon": 117.3616, "radius_km": 15.0, "category": "industrial"},
    {"name": "Wuhan", "country": "China", "lat": 30.5928, "lon": 114.3055, "radius_km": 15.0, "category": "industrial"},
    {"name": "Chengdu", "country": "China", "lat": 30.5728, "lon": 104.0668, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Nanjing", "country": "China", "lat": 32.0603, "lon": 118.7969, "radius_km": 12.0, "category": "cultural"},
    {"name": "Hangzhou", "country": "China", "lat": 30.2741, "lon": 120.1551, "radius_km": 12.0, "category": "tech_hub"},
    {"name": "Xi'an", "country": "China", "lat": 34.3416, "lon": 108.9398, "radius_km": 12.0, "category": "cultural"},
    {"name": "Qingdao", "country": "China", "lat": 36.0986, "lon": 120.3719, "radius_km": 10.0, "category": "port_city"},
    {"name": "Dalian", "country": "China", "lat": 38.9140, "lon": 121.6147, "radius_km": 10.0, "category": "port_city"},
    {"name": "Suzhou", "country": "China", "lat": 31.2989, "lon": 120.5853, "radius_km": 10.0, "category": "industrial"},
    {"name": "Chongqing", "country": "China", "lat": 29.4316, "lon": 106.9123, "radius_km": 20.0, "category": "metropolitan"},
    {"name": "Shenyang", "country": "China", "lat": 41.8057, "lon": 123.4315, "radius_km": 12.0, "category": "industrial"},
    {"name": "Harbin", "country": "China", "lat": 45.7732, "lon": 126.6577, "radius_km": 10.0, "category": "industrial"},
    {"name": "Kunming", "country": "China", "lat": 25.0389, "lon": 102.7183, "radius_km": 10.0, "category": "cultural"},
    {"name": "Changsha", "country": "China", "lat": 28.2278, "lon": 112.9388, "radius_km": 10.0, "category": "industrial"},
    {"name": "Zhengzhou", "country": "China", "lat": 34.7466, "lon": 113.6254, "radius_km": 10.0, "category": "industrial"},
    
    # Major US Cities
    {"name": "New York", "country": "United States", "lat": 40.7128, "lon": -74.0060, "radius_km": 25.0, "category": "metropolitan"},
    {"name": "Los Angeles", "country": "United States", "lat": 34.0522, "lon": -118.2437, "radius_km": 20.0, "category": "metropolitan"},
    {"name": "Chicago", "country": "United States", "lat": 41.8781, "lon": -87.6298, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Houston", "country": "United States", "lat": 29.7604, "lon": -95.3698, "radius_km": 15.0, "category": "industrial"},
    {"name": "Phoenix", "country": "United States", "lat": 33.4484, "lon": -112.0740, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Philadelphia", "country": "United States", "lat": 39.9526, "lon": -75.1652, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "San Antonio", "country": "United States", "lat": 29.4241, "lon": -98.4936, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "San Diego", "country": "United States", "lat": 32.7157, "lon": -117.1611, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Dallas", "country": "United States", "lat": 32.7767, "lon": -96.7970, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "San Jose", "country": "United States", "lat": 37.3382, "lon": -121.8863, "radius_km": 10.0, "category": "tech_hub"},
    {"name": "Austin", "country": "United States", "lat": 30.2672, "lon": -97.7431, "radius_km": 8.0, "category": "tech_hub"},
    {"name": "Jacksonville", "country": "United States", "lat": 30.3322, "lon": -81.6557, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Fort Worth", "country": "United States", "lat": 32.7555, "lon": -97.3308, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Columbus", "country": "United States", "lat": 39.9612, "lon": -82.9988, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Charlotte", "country": "United States", "lat": 35.2271, "lon": -80.8431, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Seattle", "country": "United States", "lat": 47.6062, "lon": -122.3321, "radius_km": 10.0, "category": "tech_hub"},
    {"name": "Denver", "country": "United States", "lat": 39.7392, "lon": -104.9903, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Washington", "country": "United States", "lat": 38.9072, "lon": -77.0369, "radius_km": 10.0, "category": "administrative"},
    {"name": "Boston", "country": "United States", "lat": 42.3601, "lon": -71.0589, "radius_km": 8.0, "category": "cultural"},
    {"name": "El Paso", "country": "United States", "lat": 31.7619, "lon": -106.4850, "radius_km": 8.0, "category": "metropolitan"},
    
    # Major European Cities
    {"name": "London", "country": "United Kingdom", "lat": 51.5074, "lon": -0.1278, "radius_km": 20.0, "category": "metropolitan"},
    {"name": "Berlin", "country": "Germany", "lat": 52.5200, "lon": 13.4050, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Madrid", "country": "Spain", "lat": 40.4168, "lon": -3.7038, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Rome", "country": "Italy", "lat": 41.9028, "lon": 12.4964, "radius_km": 12.0, "category": "cultural"},
    {"name": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Amsterdam", "country": "Netherlands", "lat": 52.3676, "lon": 4.9041, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Vienna", "country": "Austria", "lat": 48.2082, "lon": 16.3738, "radius_km": 10.0, "category": "cultural"},
    {"name": "Moscow", "country": "Russia", "lat": 55.7558, "lon": 37.6176, "radius_km": 20.0, "category": "metropolitan"},
    {"name": "Istanbul", "country": "Turkey", "lat": 41.0082, "lon": 28.9784, "radius_km": 18.0, "category": "metropolitan"},
    {"name": "Barcelona", "country": "Spain", "lat": 41.3851, "lon": 2.1734, "radius_km": 12.0, "category": "cultural"},
    {"name": "Munich", "country": "Germany", "lat": 48.1351, "lon": 11.5820, "radius_km": 10.0, "category": "industrial"},
    {"name": "Milan", "country": "Italy", "lat": 45.4642, "lon": 9.1900, "radius_km": 10.0, "category": "industrial"},
    {"name": "Prague", "country": "Czech Republic", "lat": 50.0755, "lon": 14.4378, "radius_km": 8.0, "category": "cultural"},
    {"name": "Warsaw", "country": "Poland", "lat": 52.2297, "lon": 21.0122, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Budapest", "country": "Hungary", "lat": 47.4979, "lon": 19.0402, "radius_km": 8.0, "category": "cultural"},
    {"name": "Stockholm", "country": "Sweden", "lat": 59.3293, "lon": 18.0686, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Copenhagen", "country": "Denmark", "lat": 55.6761, "lon": 12.5683, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Oslo", "country": "Norway", "lat": 59.9139, "lon": 10.7522, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Helsinki", "country": "Finland", "lat": 60.1699, "lon": 24.9384, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Dublin", "country": "Ireland", "lat": 53.3498, "lon": -6.2603, "radius_km": 8.0, "category": "metropolitan"},
    
    # Major Asian Cities (excluding China and India)
    {"name": "Tokyo", "country": "Japan", "lat": 35.6762, "lon": 139.6503, "radius_km": 25.0, "category": "metropolitan"},
    {"name": "Seoul", "country": "South Korea", "lat": 37.5665, "lon": 126.9780, "radius_km": 20.0, "category": "metropolitan"},
    {"name": "Bangkok", "country": "Thailand", "lat": 13.7563, "lon": 100.5018, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Jakarta", "country": "Indonesia", "lat": -6.2088, "lon": 106.8456, "radius_km": 18.0, "category": "metropolitan"},
    {"name": "Manila", "country": "Philippines", "lat": 14.5995, "lon": 120.9842, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Ho Chi Minh City", "country": "Vietnam", "lat": 10.8231, "lon": 106.6297, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Kuala Lumpur", "country": "Malaysia", "lat": 3.1390, "lon": 101.6869, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Singapore", "country": "Singapore", "lat": 1.3521, "lon": 103.8198, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Hong Kong", "country": "Hong Kong", "lat": 22.3193, "lon": 114.1694, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Taipei", "country": "Taiwan", "lat": 25.0330, "lon": 121.5654, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Osaka", "country": "Japan", "lat": 34.6937, "lon": 135.5023, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Yokohama", "country": "Japan", "lat": 35.4437, "lon": 139.6380, "radius_km": 10.0, "category": "port_city"},
    {"name": "Nagoya", "country": "Japan", "lat": 35.1815, "lon": 136.9066, "radius_km": 10.0, "category": "industrial"},
    {"name": "Kyoto", "country": "Japan", "lat": 35.0116, "lon": 135.7681, "radius_km": 8.0, "category": "cultural"},
    {"name": "Busan", "country": "South Korea", "lat": 35.1796, "lon": 129.0756, "radius_km": 10.0, "category": "port_city"},
    {"name": "Incheon", "country": "South Korea", "lat": 37.4563, "lon": 126.7052, "radius_km": 8.0, "category": "port_city"},
    {"name": "Daegu", "country": "South Korea", "lat": 35.8714, "lon": 128.6014, "radius_km": 8.0, "category": "industrial"},
    {"name": "Daejeon", "country": "South Korea", "lat": 36.3504, "lon": 127.3845, "radius_km": 8.0, "category": "tech_hub"},
    {"name": "Gwangju", "country": "South Korea", "lat": 35.1595, "lon": 126.8526, "radius_km": 8.0, "category": "cultural"},
    
    # Major African Cities
    {"name": "Cairo", "country": "Egypt", "lat": 30.0444, "lon": 31.2357, "radius_km": 20.0, "category": "metropolitan"},
    {"name": "Lagos", "country": "Nigeria", "lat": 6.5244, "lon": 3.3792, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Kinshasa", "country": "Democratic Republic of the Congo", "lat": -4.4419, "lon": 15.2663, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Johannesburg", "country": "South Africa", "lat": -26.2041, "lon": 28.0473, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Cape Town", "country": "South Africa", "lat": -33.9249, "lon": 18.4241, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Nairobi", "country": "Kenya", "lat": -1.2921, "lon": 36.8219, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Addis Ababa", "country": "Ethiopia", "lat": 9.1450, "lon": 38.7667, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Casablanca", "country": "Morocco", "lat": 33.5731, "lon": -7.5898, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Algiers", "country": "Algeria", "lat": 36.7372, "lon": 3.0867, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Tunis", "country": "Tunisia", "lat": 36.8065, "lon": 10.1815, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Tripoli", "country": "Libya", "lat": 32.8872, "lon": 13.1913, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Khartoum", "country": "Sudan", "lat": 15.5007, "lon": 32.5599, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Dakar", "country": "Senegal", "lat": 14.6928, "lon": -17.4467, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Accra", "country": "Ghana", "lat": 5.6037, "lon": -0.1870, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Abidjan", "country": "Ivory Coast", "lat": 5.3600, "lon": -4.0083, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Bamako", "country": "Mali", "lat": 12.6392, "lon": -8.0029, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Ouagadougou", "country": "Burkina Faso", "lat": 12.3714, "lon": -1.5197, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Niamey", "country": "Niger", "lat": 13.5137, "lon": 2.1098, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Yaoundé", "country": "Cameroon", "lat": 3.8480, "lon": 11.5021, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Douala", "country": "Cameroon", "lat": 4.0483, "lon": 9.7043, "radius_km": 8.0, "category": "port_city"},
    
    # Major South American Cities
    {"name": "São Paulo", "country": "Brazil", "lat": -23.5505, "lon": -46.6333, "radius_km": 25.0, "category": "metropolitan"},
    {"name": "Rio de Janeiro", "country": "Brazil", "lat": -22.9068, "lon": -43.1729, "radius_km": 18.0, "category": "metropolitan"},
    {"name": "Buenos Aires", "country": "Argentina", "lat": -34.6118, "lon": -58.3960, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Lima", "country": "Peru", "lat": -12.0464, "lon": -77.0428, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Bogotá", "country": "Colombia", "lat": 4.7110, "lon": -74.0721, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Santiago", "country": "Chile", "lat": -33.4489, "lon": -70.6693, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Caracas", "country": "Venezuela", "lat": 10.4806, "lon": -66.9036, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Guayaquil", "country": "Ecuador", "lat": -2.1894, "lon": -79.8890, "radius_km": 10.0, "category": "port_city"},
    {"name": "Quito", "country": "Ecuador", "lat": -0.1807, "lon": -78.4678, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "La Paz", "country": "Bolivia", "lat": -16.2902, "lon": -68.1332, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Montevideo", "country": "Uruguay", "lat": -34.9011, "lon": -56.1645, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Asunción", "country": "Paraguay", "lat": -25.2637, "lon": -57.5759, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Brasília", "country": "Brazil", "lat": -15.7801, "lon": -47.9292, "radius_km": 10.0, "category": "administrative"},
    {"name": "Salvador", "country": "Brazil", "lat": -12.9777, "lon": -38.5016, "radius_km": 10.0, "category": "cultural"},
    {"name": "Fortaleza", "country": "Brazil", "lat": -3.7172, "lon": -38.5434, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Belo Horizonte", "country": "Brazil", "lat": -19.9167, "lon": -43.9345, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Manaus", "country": "Brazil", "lat": -3.1190, "lon": -60.0217, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Curitiba", "country": "Brazil", "lat": -25.4244, "lon": -49.2654, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Recife", "country": "Brazil", "lat": -8.0476, "lon": -34.8770, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Porto Alegre", "country": "Brazil", "lat": -30.0346, "lon": -51.2177, "radius_km": 8.0, "category": "metropolitan"},
    
    # Major Middle Eastern Cities
    {"name": "Dubai", "country": "United Arab Emirates", "lat": 25.2048, "lon": 55.2708, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Abu Dhabi", "country": "United Arab Emirates", "lat": 24.4539, "lon": 54.3773, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Riyadh", "country": "Saudi Arabia", "lat": 24.7136, "lon": 46.6753, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Jeddah", "country": "Saudi Arabia", "lat": 21.4858, "lon": 39.1925, "radius_km": 10.0, "category": "port_city"},
    {"name": "Mecca", "country": "Saudi Arabia", "lat": 21.3891, "lon": 39.8579, "radius_km": 8.0, "category": "cultural"},
    {"name": "Medina", "country": "Saudi Arabia", "lat": 24.5247, "lon": 39.5692, "radius_km": 8.0, "category": "cultural"},
    {"name": "Kuwait City", "country": "Kuwait", "lat": 29.3759, "lon": 47.9774, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Doha", "country": "Qatar", "lat": 25.2854, "lon": 51.5310, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Manama", "country": "Bahrain", "lat": 26.0667, "lon": 50.5577, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Muscat", "country": "Oman", "lat": 23.5880, "lon": 58.3829, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Tehran", "country": "Iran", "lat": 35.6892, "lon": 51.3890, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Baghdad", "country": "Iraq", "lat": 33.3152, "lon": 44.3661, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Damascus", "country": "Syria", "lat": 33.5138, "lon": 36.2765, "radius_km": 8.0, "category": "cultural"},
    {"name": "Beirut", "country": "Lebanon", "lat": 33.8938, "lon": 35.5018, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Amman", "country": "Jordan", "lat": 31.9454, "lon": 35.9284, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Jerusalem", "country": "Israel", "lat": 31.7683, "lon": 35.2137, "radius_km": 8.0, "category": "cultural"},
    {"name": "Tel Aviv", "country": "Israel", "lat": 32.0853, "lon": 34.7818, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Haifa", "country": "Israel", "lat": 32.7940, "lon": 34.9896, "radius_km": 8.0, "category": "port_city"},
    {"name": "Sana'a", "country": "Yemen", "lat": 15.3694, "lon": 44.1910, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Aden", "country": "Yemen", "lat": 12.7855, "lon": 45.0187, "radius_km": 8.0, "category": "port_city"},
    
    # Major Australian/Oceanian Cities
    {"name": "Sydney", "country": "Australia", "lat": -33.8688, "lon": 151.2093, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Melbourne", "country": "Australia", "lat": -37.8136, "lon": 144.9631, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Brisbane", "country": "Australia", "lat": -27.4698, "lon": 153.0251, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Perth", "country": "Australia", "lat": -31.9505, "lon": 115.8605, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Adelaide", "country": "Australia", "lat": -34.9285, "lon": 138.6007, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Auckland", "country": "New Zealand", "lat": -36.8485, "lon": 174.7633, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Wellington", "country": "New Zealand", "lat": -41.2865, "lon": 174.7762, "radius_km": 8.0, "category": "administrative"},
    {"name": "Christchurch", "country": "New Zealand", "lat": -43.5321, "lon": 172.6362, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Suva", "country": "Fiji", "lat": -18.1248, "lon": 178.4501, "radius_km": 5.0, "category": "metropolitan"},
    {"name": "Port Moresby", "country": "Papua New Guinea", "lat": -9.4438, "lon": 147.1803, "radius_km": 8.0, "category": "metropolitan"},
    
    # Additional Major Cities for Comprehensive Coverage
    {"name": "Toronto", "country": "Canada", "lat": 43.6532, "lon": -79.3832, "radius_km": 15.0, "category": "metropolitan"},
    {"name": "Vancouver", "country": "Canada", "lat": 49.2827, "lon": -123.1207, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Montreal", "country": "Canada", "lat": 45.5017, "lon": -73.5673, "radius_km": 12.0, "category": "metropolitan"},
    {"name": "Calgary", "country": "Canada", "lat": 51.0447, "lon": -114.0719, "radius_km": 8.0, "category": "metropolitan"},
    {"name": "Ottawa", "country": "Canada", "lat": 45.4215, "lon": -75.6972, "radius_km": 8.0, "category": "administrative"},
    {"name": "Mexico City", "country": "Mexico", "lat": 19.4326, "lon": -99.1332, "radius_km": 20.0, "category": "metropolitan"},
    {"name": "Guadalajara", "country": "Mexico", "lat": 20.6597, "lon": -103.3496, "radius_km": 10.0, "category": "metropolitan"},
    {"name": "Monterrey", "country": "Mexico", "lat": 25.6866, "lon": -100.3161, "radius_km": 10.0, "category": "industrial"},
    {"name": "Puebla", "country": "Mexico", "lat": 19.0414, "lon": -98.2063, "radius_km": 8.0, "category": "cultural"},
    {"name": "Tijuana", "country": "Mexico", "lat": 32.5149, "lon": -117.0382, "radius_km": 8.0, "category": "metropolitan"},
]


def get_cities_by_category(category: str) -> list:
    """
    Get cities filtered by category.
    
    Args:
        category: City category (metropolitan, industrial, tech_hub, etc.)
        
    Returns:
        List of cities in the specified category
    """
    return [city for city in CITIES_DATA if city.get("category") == category]


def get_cities_by_country(country: str) -> list:
    """
    Get cities filtered by country.
    
    Args:
        country: Country name
        
    Returns:
        List of cities in the specified country
    """
    return [city for city in CITIES_DATA if city.get("country") == country]


def get_cities_by_region(region: str) -> list:
    """
    Get cities filtered by geographic region.
    
    Args:
        region: Geographic region (Asia, Europe, North America, etc.)
        
    Returns:
        List of cities in the specified region
    """
    region_mapping = {
        "Asia": ["China", "India", "Japan", "South Korea", "Thailand", "Indonesia", "Philippines", "Vietnam", "Malaysia", "Singapore", "Hong Kong", "Taiwan"],
        "Europe": ["United Kingdom", "Germany", "Spain", "Italy", "France", "Netherlands", "Austria", "Russia", "Turkey", "Czech Republic", "Poland", "Hungary", "Sweden", "Denmark", "Norway", "Finland", "Ireland"],
        "North America": ["United States", "Canada", "Mexico"],
        "South America": ["Brazil", "Argentina", "Peru", "Colombia", "Chile", "Venezuela", "Ecuador", "Bolivia", "Uruguay", "Paraguay"],
        "Africa": ["Egypt", "Nigeria", "Democratic Republic of the Congo", "South Africa", "Kenya", "Ethiopia", "Morocco", "Algeria", "Tunisia", "Libya", "Sudan", "Senegal", "Ghana", "Ivory Coast", "Mali", "Burkina Faso", "Niger", "Cameroon"],
        "Middle East": ["United Arab Emirates", "Saudi Arabia", "Kuwait", "Qatar", "Bahrain", "Oman", "Iran", "Iraq", "Syria", "Lebanon", "Jordan", "Israel", "Yemen"],
        "Oceania": ["Australia", "New Zealand", "Fiji", "Papua New Guinea"]
    }
    
    countries = region_mapping.get(region, [])
    return [city for city in CITIES_DATA if city.get("country") in countries]


def get_total_cities_count() -> int:
    """Get total number of cities in the dataset."""
    return len(CITIES_DATA)


def get_cities_summary() -> dict:
    """
    Get summary statistics of the cities dataset.
    
    Returns:
        Dictionary with summary statistics
    """
    countries = set(city["country"] for city in CITIES_DATA)
    categories = set(city["category"] for city in CITIES_DATA)
    
    return {
        "total_cities": len(CITIES_DATA),
        "total_countries": len(countries),
        "categories": list(categories),
        "countries": sorted(list(countries)),
        "cities_by_category": {cat: len(get_cities_by_category(cat)) for cat in categories},
        "cities_by_country": {country: len(get_cities_by_country(country)) for country in sorted(countries)}
    }









