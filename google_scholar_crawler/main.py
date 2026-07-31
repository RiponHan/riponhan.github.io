from html import unescape
import json
from datetime import datetime, timezone
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


scholar_id = os.environ.get('GOOGLE_SCHOLAR_ID', '').strip()
if not scholar_id:
    raise RuntimeError('GOOGLE_SCHOLAR_ID is not configured')


def clean_text(fragment: str) -> str:
    """Convert a small HTML fragment into normalized plain text."""
    without_tags = re.sub(r'<[^>]+>', '', fragment)
    return ' '.join(unescape(without_tags).split())


profile_url = (
    'https://scholar.google.com/citations'
    f'?user={quote(scholar_id)}&hl=en&pagesize=100'
)
request = Request(
    profile_url,
    headers={
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0 Safari/537.36'
        ),
        'Accept-Language': 'en-US,en;q=0.9',
    },
)

try:
    with urlopen(request, timeout=30) as response:
        page = response.read().decode('ISO-8859-1', errors='replace')
except (HTTPError, URLError, TimeoutError) as error:
    raise RuntimeError(f'Unable to fetch Google Scholar profile: {error}') from error

name_match = re.search(r'<div id="gsc_prf_in">(.*?)</div>', page, re.DOTALL)
if not name_match:
    raise RuntimeError(
        'Google Scholar did not return a public profile page. '
        'The request may have been rate-limited.'
    )

description_match = re.search(
    r'<meta name="description" content="(.*?)">',
    page,
    re.DOTALL,
)
description = clean_text(description_match.group(1)) if description_match else ''
cited_by_match = re.search(r'Cited by\s+([\d,]+)', description)
cited_by = int(cited_by_match.group(1).replace(',', '')) if cited_by_match else 0

publications = {}
for row in re.findall(r'<tr class="gsc_a_tr".*?</tr>', page, re.DOTALL):
    publication_id_match = re.search(r'citation_for_view=([^&"\']+)', row)
    if not publication_id_match:
        continue

    publication_id = unescape(publication_id_match.group(1))
    title_match = re.search(
        r'class="gsc_a_at"[^>]*>(.*?)</a>',
        row,
        re.DOTALL,
    )
    citations_match = re.search(
        r'class="gsc_a_ac[^"]*"[^>]*>([\d,]+)</a>',
        row,
        re.DOTALL,
    )
    publications[publication_id] = {
        'author_pub_id': publication_id,
        'bib': {
            'title': clean_text(title_match.group(1)) if title_match else '',
        },
        'num_citations': (
            int(citations_match.group(1).replace(',', ''))
            if citations_match
            else 0
        ),
    }

author = {
    'scholar_id': scholar_id,
    'name': clean_text(name_match.group(1)),
    'citedby': cited_by,
    'publications': publications,
    'updated': datetime.now(timezone.utc).isoformat(),
}

print(json.dumps(author, indent=2))
os.makedirs('results', exist_ok=True)
with open('results/gs_data.json', 'w', encoding='utf-8') as outfile:
    json.dump(author, outfile, ensure_ascii=False, indent=2)

shieldio_data = {
  "schemaVersion": 1,
  "label": "citations",
  "message": str(author.get('citedby', 0)),
}
with open('results/gs_data_shieldsio.json', 'w', encoding='utf-8') as outfile:
    json.dump(shieldio_data, outfile, ensure_ascii=False, indent=2)
