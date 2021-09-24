# encode: utf-8
"""
Convert the ADS Libraries into the publication list.
"""

import os
import requests
import pandas as pd


def get_config():
    """
    Load ADS developer key from file
    :return: str
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

    r = requests.get(
        "{}/libraries/{id}?start={start}&rows={rows}".format(
            config["url"], id=library_id, start=start, rows=rows
        ),
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
    pub_df = get_pub_df("OLm3sdMXQOWK5cwYL5hfsg")

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
                pub_str += "In submission"
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
        
        
def main():
    # This all creates the final index.html
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
    main()
    



