import requests
import json
from datetime import datetime

CURRENT_YEAR = datetime.now().year

# Define manual citation offsets for specific DOIs here:
# Format: "DOI_SUFFIX_OR_FULL_DOI": extra_citations_to_add
CUSTOM_OFFSETS = {
    "10.52679/tabcj.2020.0001": 5,
    "10.52679/tabcj.2021.0003": 3,
    # Add more specific DOIs and their missing citation offsets as needed
}

def load_dois():
    try:
        with open("dois.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: dois.json not found.")
        return []

def get_openalex_citations(doi):
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data.get('cited_by_count', 0), data.get('publication_year'), data.get('counts_by_year', [])
    except Exception:
        pass
    return 0, None, []

def get_semantic_scholar_citations(doi):
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=citationCount,year"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data.get('citationCount', 0), data.get('year', 0)
    except Exception:
        pass
    return 0, 0

def get_crossref_citations(doi):
    url = f"https://api.crossref.org/works/{doi}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            message = res.json().get('message', {})
            return message.get('is-referenced-by-count', 0)
    except Exception:
        pass
    return 0

def calculate_metrics():
    dois = load_dois()
    if not dois:
        return

    works_data = []
    print(f"Querying APIs and applying custom offsets for {len(dois)} DOIs...")

    for doi in dois:
        oa_count, oa_year, oa_counts_by_year = get_openalex_citations(doi)
        s2_count, s2_year = get_semantic_scholar_citations(doi)
        cr_count = get_crossref_citations(doi)

        # Base max citations from APIs
        max_citations = max(oa_count, s2_count, cr_count)
        
        # Add custom manual offset if defined for this DOI
        offset = CUSTOM_OFFSETS.get(doi, 0)
        final_citations = max_citations + offset
        
        pub_year = oa_year if oa_year else (s2_year if s2_year else CURRENT_YEAR)

        works_data.append({
            "doi": doi,
            "cited_by_count": final_citations,
            "publication_year": pub_year,
            "counts_by_year": oa_counts_by_year
        })

    total_citations = sum(w['cited_by_count'] for w in works_data)
    citation_counts = sorted([w['cited_by_count'] for w in works_data], reverse=True)
    
    # H-Index calculation
    h_index = 0
    for i, count in enumerate(citation_counts):
        if count >= i + 1:
            h_index = i + 1
        else:
            break
            
    # i10-Index calculation
    i10_index = sum(1 for count in citation_counts if count >= 10)
    
    target_year = CURRENT_YEAR - 1
    
    # 2-Year Impact Factor
    pub_years_2yr = [target_year - 1, target_year - 2]
    citable_2yr = [w for w in works_data if w['publication_year'] in pub_years_2yr]
    citable_count_2yr = len(citable_2yr)
    citations_2yr = sum(
        c.get('cited_by_count', 0) 
        for w in citable_2yr 
        for c in w.get('counts_by_year', []) 
        if c.get('year') == target_year
    )
    jif = round(citations_2yr / citable_count_2yr, 3) if citable_count_2yr > 0 else 0.0

    # 5-Year Impact Factor
    pub_years_5yr = [target_year - i for i in range(1, 6)]
    citable_5yr = [w for w in works_data if w['publication_year'] in pub_years_5yr]
    citable_count_5yr = len(citable_5yr)
    citations_5yr = sum(
        c.get('cited_by_count', 0) 
        for w in citable_5yr 
        for c in w.get('counts_by_year', []) 
        if c.get('year') == target_year
    )
    jif_5yr = round(citations_5yr / citable_count_5yr, 3) if citable_count_5yr > 0 else 0.0

    metrics = {
        "total_citations": total_citations,
        "h_index": h_index,
        "i10_index": i10_index,
        "impact_factor": jif,
        "five_year_impact_factor": jif_5yr,
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
        
    print("Calibrated metrics saved successfully:", metrics)

if __name__ == "__main__":
    calculate_metrics()