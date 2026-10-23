import json

# Load generated JSON
with open('nme_values/PhysRevC.98.024608_extracted_direct.json') as f:
    data = json.load(f)

# Check first entry
entry = data['entries'][0]
print('Generated entry (76Ge WS model 1):')
print(f'  Isotope: {entry["Isotope"]}')
print(f'  Model class: {entry["Model class"]}')
print(f'  Model: {entry["Model"]}')
print(f'  g_A: {entry["g_A"]}')
print(f'  M_total: value={entry["matrix_elements"]["M_total"]["value"]}, error={entry["matrix_elements"]["M_total"]["error"]}')
print(f'  M_GT: value={entry["matrix_elements"]["M_summed"]["M_GT"]["value"]}, error={entry["matrix_elements"]["M_summed"]["M_GT"]["error"]}')
print(f'  M_F: value={entry["matrix_elements"]["M_summed"]["M_F"]["value"]}, error={entry["matrix_elements"]["M_summed"]["M_F"]["error"]}')
print(f'  M_T: value={entry["matrix_elements"]["M_summed"]["M_T"]["value"]}, error={entry["matrix_elements"]["M_summed"]["M_T"]["error"]}')

print(f'\nTotal entries: {len(data["entries"])}')
print(f'Reference: {data["Reference"]}')
