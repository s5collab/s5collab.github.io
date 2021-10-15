# encode: utf-8
"""
Convert your ADS Libraries into the markdown publication pages.
"""

import os
import requests
import pandas as pd
from urllib.parse import quote
from pathlib import Path


def get_config():
    """
    Load ADS developer key from file and
    and return the headers for the request
    """
    if os.getenv('ADS_TOKEN') is None:
        with open(os.path.expanduser("~/.ads/dev_key")) as f:
            token = f.read().strip() 
    else:
        token = os.getenv('ADS_TOKEN')
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


def get_title_str(pub):
    # This fixes up a bunch of minor formatting issues
    title_str = pub['title'][0]

    things_to_fix = [[r"$\sim$", "~"],
                     [r"$R$", "*R*"],
                     [r"[$\alpha/\rm Fe]$", "[α/Fe]"],
                     [r"$\alpha$", "α"],
                     [r"∼", "~"],
                     [r"$< -0.75$", "< −0.75"],
                     [r"$\textit{TESS}$", "*TESS*"],
                     [r"$Gaia$", "*Gaia*"],
                     [r"${S}^5$", "S⁵"],
                     [r"$S^5$", "S⁵"],
                     ["(S5)", "(S⁵)"],
                     ["S<SUP>5</SUP>", "S⁵"],
                     ["*", "\*"]]

    for thing_to_fix in things_to_fix:
        title_str = title_str.replace(thing_to_fix[0], thing_to_fix[1])
    return title_str


def get_author_str(pub):
    # Different author formats depending on the number of authors
    if pub['author_count'] == 1:
        return f"{pub['author'][0]}"
    if pub['author_count'] == 2:
        return f"{pub['author'][0].split(',')[0]} and {pub['author'][1].split(',')[0]}"
    if pub['author_count'] > 2:
        return f"{pub['author'][0]} *et al.*"


def get_pub_vol_pp_str(pub):
    publication_str = pub['bibstem'][0].replace("Natur", "Nature")
    vol_str = ""
    pp_str = ""
    # Fixes for when there is no volume or page number
    if pub['bibstem'][0] != 'arXiv':
        vol_str = f"**{pub['volume']}**".replace("** **", "")
        pp_str = f"{pub['page'][0]}".replace(" ", "")
    if pub['bibstem'][0] == "arXiv":
        # Deal with papers accepted but not published
        if pub['page'][0] in ["arXiv:2109.03948", "arXiv:2106.12656"]:
            publication_str = "Accepted to ApJ"
        # Deal with papers still in submission.
        if pub['page'][0] in ["arXiv:2107.13004", "arXiv:2110.06950"]:
            publication_str = "Submitted to ApJ"
    return f"{publication_str} {vol_str} {pp_str}"


def get_doi_str(pub):
    if pub['doi'][0] == " ":
        return None
    return f"[doi:{pub['doi'][0]}](https://doi.org/{pub['doi'][0]})"


def get_arxiv_str(pub):
    arXiv_id = [i for i in pub['identifier'] if i.startswith("arXiv:")]
    if len(arXiv_id) == 0:
        return None
    return f"[{arXiv_id[0]}](https://arxiv.org/abs/{arXiv_id[0]})"


def link_str(doi_str, arxiv_str):
    if (doi_str is None) and (arxiv_str is None):
        return ""
    if (doi_str is None):
        return f"<small>({arxiv_str})</small>"
    if (arxiv_str is None):
        return f"<small>({doi_str})</small>"
    return f"<small>({doi_str}, {arxiv_str})</small>"


def get_data_frame(library_id):
    config = get_config()
    bibcodes = get_bibcodes(library_id)
    r = requests.post("https://api.adsabs.harvard.edu/v1/search/bigquery",
                      params={"q": "*:*",
                              "fl": "bibcode,title,year,bibstem,author_count,volume,pub,page,issue,identifier,author,doi,date,doctype",
                              "rows": 2000},
                      headers={'Authorization': config['headers']['Authorization'],
                               'Content-Type': 'big-query/csv'},
                      data="bibcode\n" + "\n".join(bibcodes))
    doc_dict = r.json()['response']['docs']
    pub_df = pd.DataFrame(doc_dict)
    pub_df.fillna(value=" ", inplace=True)
    ignore_doctype = ["catalog", "proposal", "inproceedings", "abstract"]
    pub_df = pub_df[~pub_df.doctype.isin(ignore_doctype).values]
    return pub_df

def create_webpage(library_id, md_pub_file, title, subtitle):
    pub_df = get_data_frame(library_id)

    cwd = Path(__file__).parent
    img_name = f"{md_pub_file.split('.')[0].split('/')[1]}_number_papers.svg"

    with open(md_pub_file, 'w') as pub_md:
        year_list = []
        article_list = []
        eprint_list = []
        for year, year_df in pub_df.sort_values('year', ascending=False).groupby("year", sort=False):
            year_list.append(int(year))
            year_counts = year_df['doctype'].value_counts()
            if 'article' in year_counts:
                article_list.append(year_counts['article'])
            else:
                article_list.append(0)
            if 'eprint' in year_counts:
                eprint_list.append(year_counts['eprint'])
            else:
                eprint_list.append(0)
            pub_md.write("\n")
            pub_md.write(f"#### {year}\n")
            pub_md.write("\n")
            for *_, pub in year_df.sort_values(['date', 'bibcode'], ascending=[False, False]).iterrows():
                markdown_str = "* "
                title_str = f"[**{get_title_str(pub)}**](https://ui.adsabs.harvard.edu/abs/{quote(pub['bibcode'])})"
                author_str = get_author_str(pub)
                year_str = f"({pub['year']})"
                publication_str = get_pub_vol_pp_str(pub)

                markdown_str = f"* {title_str}<br/>{author_str} {year_str} {publication_str} {link_str(get_doi_str(pub), get_arxiv_str(pub))}\n"

                pub_md.write(markdown_str)


if __name__ == '__main__':
    create_webpage(library_id='OLm3sdMXQOWK5cwYL5hfsg',
                   md_pub_file="_data/publications.md",
                   title="Publications using GALAH data",
                   subtitle="This page lists publications using GALAH data.")
