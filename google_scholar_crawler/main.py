from scholarly import scholarly
import json
from datetime import datetime, timezone
import os


scholar_id = os.environ.get('GOOGLE_SCHOLAR_ID', '').strip()
if not scholar_id:
    raise RuntimeError('GOOGLE_SCHOLAR_ID is not configured')

author: dict = scholarly.search_author_id(scholar_id)
scholarly.fill(author, sections=['basics', 'indices', 'counts', 'publications'])
author['updated'] = datetime.now(timezone.utc).isoformat()
author['publications'] = {
    publication['author_pub_id']: publication
    for publication in author.get('publications', [])
    if publication.get('author_pub_id')
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
