"""
labeler.py
Improved interactive docket entry labeler
Adds to labeled.csv.
Press Ctrl-D to quit.
"""

import csv
import json

from de_classifier.get_docket_entries import get_docket_entries

OUTPUT_CSV_FN = "labeled.csv"
OUTPUT_JSON_FN = "labeled.json"
LABELS_FN = "labels.json"
OUTPUT_HEADER_ROW = ("Docket Entry ID", "Document ID", "Description", "Label")
LABELS = json.load(open(LABELS_FN, "r"))
LABEL_DEFAULT = "other"
INSTRUCTIONS = (
    "Enter a letter below to apply a label, ? for help, or Ctrl-D to quit."
)
PROMPT = "> "

dataset = {}
knowns = {}


def instruct():
    print(INSTRUCTIONS)
    for k in LABELS:
        print(f"\t{k}\t{LABELS[k]}")
    print()


# load existing labeled data from CSV file
def load_existing():
    global dataset, knowns
    rows = None
    with open(OUTPUT_CSV_FN, "r") as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    row_n = 0
    for row in rows:
        row_n += 1
        if row_n == 1:  # skip header row
            continue
        else:
            de_id, doc_id, description, label = row
            dataset[de_id] = {
                "doc_id": doc_id,
                "description": description,
                "label": label,
            }
            upperized = description.upper()
            if upperized not in knowns:
                knowns[upperized] = label
    print(f"Loaded existing labeled data: {row_n} rows.")
    return


class Fetcher:
    def __init__(self):
        self.next = None
        self.entries = []

    def next_item(self):
        if len(self.entries) == 0:
            # fetch more docket entries from CourtListener
            response_data = get_docket_entries(self.next)
            self.next = response_data["next"]

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
                    self.entries.append([de_id, doc_id, description])

        return self.entries.pop()


# save labeled data
def save_json():
    global dataset
    with open(OUTPUT_JSON_FN, "w") as f:
        json.dump(dataset, f)
    print(f"Saved labeled data to {OUTPUT_JSON_FN}.")


def save_csv():
    global dataset
    with open(OUTPUT_CSV_FN, "w") as f:
        writer = csv.writer(f)
        writer.writerow(OUTPUT_HEADER_ROW)
        for de_id in dataset:
            row = [
                de_id,
                dataset[de_id]["doc_id"],
                dataset[de_id]["description"],
                dataset[de_id]["label"],
            ]
            writer.writerow(row)


# add to labeled data
def add_label(de_id, doc_id, description, label):
    global dataset
    dataset[de_id] = {
        "doc_id": doc_id,
        "description": description,
        "label": label,
    }


if __name__ == "__main__":
    fetcher = Fetcher()
    load_existing()
    print(f"Ready with {len(LABELS.keys())} labels.")

    instruct()

    # label new docket entries
    while True:
        label = None

        de_id, doc_id, description = fetcher.next_item()
        if de_id in dataset:
            continue

        # Don't bother if it's blank!
        if description == "":
            label = LABEL_DEFAULT

        else:
            upperized = description.upper()
            if upperized in knowns:
                label = knowns[upperized]

            else:
                print(description)
                response = None

                # prompt loop
                while True:
                    try:
                        response = input(PROMPT).upper()
                    except EOFError:
                        print("Exiting...")
                        save_json()
                        save_csv()
                        exit()
                    if response == "?":
                        instruct()
                        print()
                        print(description)
                    elif response in LABELS:
                        label = LABELS[response]
                        knowns[upperized] = label
                        break
                    else:
                        print(f"Huh? I don't know what '{response}' means.")
                        instruct()

        add_label(de_id, doc_id, description, label)
