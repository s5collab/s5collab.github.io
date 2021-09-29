# encode: utf-8
"""
This script update the S5 website.

It does three things:
1) Updates the publication list if there are changes to the entries in
and ADS library (https://ui.adsabs.harvard.edu/user/libraries/OLm3sdMXQOWK5cwYL5hfsg)
2) Updates the list of people if there are changes to _basefiles/people.json
3) Joins several HTML files together to make the final index.html
"""

import os
import requests
import pandas as pd


def get_config():
    """
    Load ADS developer key from file and
    and return the headers for the request
    """
    token = os.getenv('ADS_TOKEN')
    # try:
    #     with open(os.path.expanduser("~/.ads/dev_key")) as f:
    #         token = f.read().strip()
    # except IOError:
    #     print(
    #         "The script assumes you have your ADS developer token in the"
    #         "folder: {}".format()
    #     )

    return {
        "url": "https://api.adsabs.harvard.edu/v1/biblib",
        "headers": {
            "Authorization": "Bearer:{}".format(token),
            "Content-Type": "application/json",
        },
    }


def get_bibcodes(library_id):
    """Get the bibcodes for all the papers in the library."""
    start = 0
    rows = 1000
    config = get_config()

    url = f"{config['url']}/libraries/{library_id}"
    r = requests.get(url,
                     params={"start": start,
                             "rows": rows},
                     headers=config["headers"],
    )
    # Get all the documents that are inside the library
    try:
        bibcodes = r.json()["documents"]
    except ValueError:
        raise ValueError(r.text)
    return bibcodes


def get_pub_df(library_id):
    """Return a dataframe of the useful publication info."""
    config = get_config()
    bibcodes = get_bibcodes(library_id)

    fields_wants = [
        "bibcode",
        "title",
        "year",
        "bibstem",
        "author_count",
        "citation_count",
        "volume",
        "pub",
        "page_range",
        "issue",
        "identifier",
        "author",
        "doi",
        "date",
        "doctype",
        "abstract",
        "bibstem",
    ]

    r = requests.post(
        "https://api.adsabs.harvard.edu/v1/search/bigquery",
        params={"q": "*:*", "fl": ",".join(fields_wants), "rows": 2000},
        headers={
            "Authorization": config["headers"]["Authorization"],
            "Content-Type": "big-query/csv",
        },
        data="bibcode\n" + "\n".join(bibcodes),
    )
    doc_dict = r.json()["response"]["docs"]

    pub_df = pd.DataFrame(doc_dict)
    pub_df.fillna(value=" ", inplace=True)
    return pub_df


def title_stuff(pub):
    """Some title formatting stuff."""
    title = pub.title[0].replace("${S}^5$", "S<sup>5</sup>")
    if pub.doi == " ":
        return f"<i>{title}</i>. "
    else:
        return f'<a href="https://doi.org/{pub.doi[0]}"><i>{title}</i></a>. '


def update_libary():
    """Update the publication list."""
    
    pub_df = get_pub_df("OLm3sdMXQOWK5cwYL5hfsg")

    # These are the papers we have press coverage for.
    press_set = set(["2020MNRAS.491.2465K", "2020Natur.583..768W"])

    # Update the publication section of the website.
    with open("_basefiles/section_pubs.html", "w") as pubs_doc:
        pubs_doc.write(
            """
    <section id="publications" class="wrapper style1">
        <header class="major">
        <h2>Publications</h2>
        </header>
        <div class="container">
        <ol>\n"""
        )
        for *_, pub in pub_df.sort_values("date").iterrows():
            arxiv = [a for a in pub.identifier if a.startswith("arXiv:")][0]
            pub_str = "        <li>"
            pub_str += pub.author[0] + " <i>et al</i>"
            pub_str += f" ({pub.year}). "
            pub_str += title_stuff(pub)
            
            
            if pub.pub == "arXiv e-prints":
                # Deal with papers accepted but not published
                if arxiv in ["arXiv:2109.03948", "arXiv:2106.12656"]:
                    pub_str += "Accepted to ApJ"
                # Deal with papers still in submission.
                if arxiv in ["arXiv:2107.13004"]:
                    pub_str += "Submitted to ApJ"
            else:
                pub_str += pub.pub
            pub_str += f' (<a href="https://arxiv.org/abs/{arxiv}">arXiv preprint</a>'
            if pub.bibcode in press_set:
                pub_str += '; <a href="#PressCoverage">Press coverage</a>'
            pub_str += ")"
            pub_str += "</li>\n"
            pubs_doc.write(pub_str)
        pubs_doc.write(
            """      </ol>
        </div>
    </section>
    """
        )
        
def icon_list(person):
    # Add the little icons beside people's names
    icons_dict = {"website": {"icon": "fa fa-home", "link_prefix": "", "title": "Website"},
                 "email": {"icon": "fas fa-envelope", "link_prefix": "mailto:", "title": "Email"},
                 "twitter": {"icon": "fab fa-twitter", "link_prefix": "https://twitter.com/", "title": "Twitter"},}
    
    icon_str = []
    for icon, icon_dict in icons_dict.items():
        if not person[[icon]].isna()[0]:
            link_val = person[icon]
            icon_str.append(f"""<a class="item-link" href="{icon_dict['link_prefix']}{link_val}" title="{icon_dict['title']}"><span class="{icon_dict['icon']}"></span></a>""")
    return "\n".join(icon_str)

def create_circle_entry(person):
    """This makes the photo entry for a person."""
    
    person_name = " ".join(person[['first_name','last_name']].values)
    
    # The image names have the format JeffreySimpson.jpg
    image_name = person_name.replace(" ", "").replace("-", "")
    person_entry = []
    person_entry.append('           <div class="list-circles-item">')
    person_entry.append(f'            <img src="images/{image_name}.jpg" class="item-img" />')
    name_str = [f'            <div class="item-name">',
                f'               <b>{person_name}</b>']
    name_str.append(icon_list(person))
    name_str.append("            </div>")
    person_entry.append("\n".join(name_str))
    if not person[['affiliation']].isna()[0]:
        affiliation = person['affiliation']
        person_entry.append(f'            <div class="item-affiliation">{affiliation}</div>')
    if not person[['description']].isna()[0]:
        description = person['description']
        person_entry.append(f'            <div class="item-desc">({description})</div>')
    person_entry.append(f'           </div>')
    person_entry.append('')
    return "\n".join(person_entry)
    

def update_people_section():
    """This updates/creates the people section of the webite."""
    people = pd.read_json("_basefiles/people.json")

    people_html = []
    people_html.append('  <section id="collaboration" class="wrapper style1 special">')
    people_html.append('    <div class="inner">')
    people_html.append('      <header>')
    people_html.append('      <h2>S<sup>5</sup> Membership</h2>')
    people_html.append('        <p>The S<sup>5</sup> Collaboration consists of roughly 30 members spread across many institutions.</p>')
    people_html.append('      </header>')
    people_html.append('      <p>S<sup>5</sup> is a collaboration between the members of the DES Milky Way Working Group and a group of Australian astronomers.</p>')
    people_html.append('      <p>If you are interested in getting involved in S<sup>5</sup>, please contact <a href="mailto:tingli@carnegiescience.edu">Ting Li</a> or other members in the S<sup>5</sup> leadership team.</p>')

    #First section for the leadership
    people_html.append('      <div class="container">')
    people_html.append('        <h3>S<sup>5</sup> leadership</h3>')
    people_html.append('        <p>S<sup>5</sup> leadership team helps to coordinate the operational and scientific efforts of the collaboration.</p>')
    people_html.append('        <div class="list-circles">')
    for p_count, person in people[people.tag == "leadership"].iterrows():
        people_html.append(create_circle_entry(person))
    people_html.append('        </div>')
    people_html.append('      </div>')
    people_html.append('      <br/>')

    #Section section for other members
    people_html.append('      <div class="container">')
    people_html.append('        <h3>Other team members</h3>')
    people_html.append('        <div class="list-circles">')
    for p_count, person in people[(people.tag != "leadership") & (people.tag.str.contains("photo"))].iterrows():
        people_html.append(create_circle_entry(person))
    people_html.append('        </div>')
    people_html.append('      </div>')
    people_html.append('      <br/>')
    

    #The rest
    people_html.append('      <div class="container">')
    people_html.append('        <h3>and</h3>')
    # people_html.append('        <div class="list-circles">')
    people_list = []
    for p_count, person in people[people[['tag']].isna().values].iterrows():
        person_name = " ".join(person[['first_name','last_name']].values)
        person_icon_list = icon_list(person).strip().replace("\n", " ")
        if person_icon_list != "":
            person_name = f"{person_name} ({person_icon_list})"
        people_list.append(person_name)
    people_html.append(f'        {", ".join(people_list)}')
    people_html.append('      </div>')
    people_html.append('      <br/>')

    people_html.append('    </div>')
    people_html.append('  </section>')
    with open("_basefiles/section_people.html", 'w') as html_page:
        html_page.write("\n".join(people_html))

    
        
def main():
    """This all creates the final index.html"""
    
    html_files = [
        "header.html",
        "body_header.html",
        "section_intro.html",
        "section_data.html",
        "section_pubs.html",
        "section_press.html",
        "section_people.html",
        "body_footer.html",
    ]
    html_doc = ""
    for input_file in html_files:
        with open(f"_basefiles/{input_file}", "r") as insert_me:
            for line in insert_me:
                html_doc += line
    with open("index.html", "w") as index_out:
        index_out.write(html_doc)

if __name__ == "__main__":
    update_libary()
    update_people_section()
    main()
    



