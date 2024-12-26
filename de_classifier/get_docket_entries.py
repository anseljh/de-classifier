from os import environ
import csv
import json

import requests

CL_API_TOKEN = environ["CL_API_TOKEN"]
CL_SEARCH_ENDPOINT = (
    "https://www.courtlistener.com/api/rest/v4/docket-entries/"
)
JSON_OUTPUT_FN = "response.json"
CSV_OUTPUT_FN = "docket_entries.csv"
CSV_HEADER_ROW = ("Docket Entry ID", "Document ID", "Description")
HOW_MANY = 500

headers = {
    "Authorization": f"Token {CL_API_TOKEN}"
}

# order_by=-date_filed

# Select only fields we need
# https://www.courtlistener.com/help/api/rest/v4#field-selection
# fields=["id", "description"]

# params = {
#     "fields": ",".join(fields)
# }

def get_docket_entries(next=None):
    # print("GETting...")
    print("Getting more docket entries...")
    url = CL_SEARCH_ENDPOINT
    if next is not None:
        url = next
    response = requests.get(
        url, 
        headers=headers, 
        # params=params
    )
    assert response.status_code == 200

    with open(JSON_OUTPUT_FN, "wb") as output_fp:
        output_fp.write(response.content)

    response_data = response.json()
    
    return response_data

if __name__ == "__main__":

    total = 0
    next = None
    rows = []

    while len(rows) <= HOW_MANY:
        response_data = get_docket_entries(next)
        next = response_data["next"]

        for result in response_data["results"]:
            # Each item looks like:
            # https://www.courtlistener.com/api/rest/v4/docket-entries/411065279/
            de_id = result["id"]
            if not "recap_documents" in result:
                continue
            # implicit else
            for doc in result["recap_documents"]:
                description = doc["description"]
                doc_id = doc["id"]
                rows.append([de_id, doc_id, description])
        print()

    print(len(rows))

    print("Writing CSV file...")
    with open(CSV_OUTPUT_FN, "w") as csv_fp:
        writer = csv.writer(csv_fp)
        writer.writerow(CSV_HEADER_ROW)
        writer.writerows(rows)
    print("Done.")
