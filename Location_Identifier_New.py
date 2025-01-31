import pandas as pd
distances = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Locations_&_Tile_Coordinates.csv")
ref_data = pd.read_csv("e:/University/University lectures/4. Final Year/Semester 8/1. Research Project/Codes/Location Identifier/Locations_&_Magnetic_Data.csv")

# print(distances)
n = 1
matched_location = 'data_location_' + str(n)
template_size = 1

matched_location_x = distances[distances['Location'] == matched_location].iloc[0]['X']
matched_location_y = distances[distances['Location'] == matched_location].iloc[0]['Y']
selected_locations = distances[(distances['X'] >= matched_location_x - template_size) & (distances['X'] <= matched_location_x + template_size) & (distances['Y'] >= matched_location_y - template_size) & (distances['Y'] <= matched_location_y + template_size)]
filtered_data = ref_data[ref_data['Location'].isin(selected_locations['Location'])]
print(filtered_data)
