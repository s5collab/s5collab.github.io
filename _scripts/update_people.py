import pandas as pd

def person_out(person, out_file):
    person_block = []
    person_name = " ".join(person[['first_name', 'last_name']].values)
    image_name = "".join(person[['first_name', 'last_name']].values).replace('-',"")
    person_block.append(f'  - name: "{person_name}"')
    
    if not person[['affiliation']].isna()[0]:
        affiliation = person['affiliation']
        person_block.append(f'    affiliation: "{affiliation}"')
    if not person[['description']].isna()[0]:
        description = person['description']
        person_block.append(f'    role: "{description}"')
    person_block.append(f'    image: assets/img/team/{image_name}.jpg')
    if not person[list(icons_dict.keys())].isna().all():
        person_block.append("    social:")
        for icon, icon_dict in icons_dict.items():
            if not person[[icon]].isna()[0]:
                person_block.append(f"      - url: {icon_dict['link_prefix']}{person[icon]}")
                person_block.append(f"        icon: {icon_dict['icon']}")
    person_block.append("\n")
    out_file.write("\n".join(person_block))
    
def get_icon_link(person, icon, icon_dict):
    icon_fa = icon_dict['icon']
    link_prefix = icon_dict['link_prefix']
    link = person[icon]
    return f'[<span class="{icon_fa}"></span>]({link_prefix}{link})'

def create_person(person):
    person_str = []
    person_str.append(" ".join(person[['first_name', 'last_name']].values))
    if not person[list(icons_dict.keys())].isna().all():
        person_str.append(" (")
        person_str.append(", ".join([get_icon_link(person, icon, icon_dict)
                                     for icon, icon_dict in icons_dict.items() if not person[[icon]].isna()[0]]))
        person_str.append(")")
    return "".join(person_str)
    
if __name__ == '__main__':
    
    """This updates/creates the people section of the webite."""
    people = pd.read_json("_scripts/people.json")
    # This self sorts the JSON file, so you can just new people at the end.
    people.sort_values(['last_name', 'first_name']).to_json("_scripts/people.json", orient='records', indent=2)

    icons_dict = {"website": {"icon": "fa fa-home", "link_prefix": "", "title": "Website"},
                "email": {"icon": "fas fa-envelope", "link_prefix": "mailto:", "title": "Email"},
                "twitter": {"icon": "fab fa-twitter", "link_prefix": "https://twitter.com/", "title": "Twitter"},}
    
    people_no_photos_idx = ~((people.tag == "photo") | (people.tag == "leadership"))
    with open("_data/people_no_photos.yml", 'w') as people_no_photos:
        peoples_str = [create_person(person) for p_count, person in people[people_no_photos_idx].sort_values(['last_name', 'first_name']).iterrows()]
        people_no_photos.write(",\n".join(peoples_str))

    people_leaders_idx = people.tag == "leadership"
    with open("_data/people_leaders.yml", 'w') as people_leaders:
        people_leaders.write("people:\n")
        for p_count, person in people[people_leaders_idx].sort_values(['last_name', 'first_name']).iterrows():
            person_out(person, people_leaders)
            
    people_photos_idx = people.tag == "photo"
    with open("_data/people_photos.yml", 'w') as people_photos:
        people_photos.write("people:\n")
        for p_count, person in people[people_photos_idx].sort_values(['last_name', 'first_name']).iterrows():
            person_out(person, people_photos)