"""
laberler3.py: Better labeler

Improves on laberler.py by:
- ✨ Auto-completion of labels! ✨
- Limiting to civil and criminal cases. Bankruptcy is too crazy for now!
- Explicitly do a whole case at a time.
- Saves API query state so we don't restart from the same point every time.
- Better logging.
"""

import csv
import json
import logging
import sys

from os import environ
from pathlib import Path

import requests
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator, ValidationError


__NAME__ = "labeler3.py"
LOG_LEVEL = "DEBUG"
LOG_FN = "labeler3.log"

CL_API_TOKEN = environ["CL_API_TOKEN"]
CL_DE_ENDPOINT = "https://www.courtlistener.com/api/rest/v4/docket-entries/"
CL_DOCKET_ENDPOINT = (
    "https://www.courtlistener.com/api/rest/v4/dockets/?court__jurisdiction=FD"
)

ENTRIES_FN = "entries.json"
DOCKETS_FN = "dockets.json"
OUTPUT_FN = "output3.csv"
OUTPUT_HEADER_ROW = (
    "Description",
    "Label",
    "Docket Entry ID",
    "Docket ID",
    "Document ID",
)
LABELS_FN = "labels3.json"
LABELS = json.load(open(LABELS_FN))

INSTRUCTIONS = """Enter a label from the list below. Press Tab to auto-complete!
? to repeat these instructions. Ctrl-D to quit.

\t"""
PROMPT = "> "

# Init logging
logging.basicConfig(
    filename=LOG_FN,
    level=LOG_LEVEL,
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
)
log = logging.getLogger(__NAME__)
log.setLevel(LOG_LEVEL)
log.info(f"Starting {__NAME__}")

NEXT_FN = "next.json"
NEXT = None
try:
    NEXT = json.load(open(NEXT_FN))
except FileNotFoundError:
    log.info(f"No next.json file found. Starting from scratch.")

auth_headers = {"Authorization": f"Token {CL_API_TOKEN}"}


class DocketEntryFetcher:
    def __init__(self, next=None):
        self.dockets = {}
        self.entries = {}
        self.docket_next = next
        self.docket_queue = []
        log.debug(f"Initialized DocketEntryFetcher: {self}")

    def load(self):
        """Load state from file."""
        raise NotImplementedError

    def save(self):
        """Save state to file."""
        log.debug("Saving state...")
        with open(ENTRIES_FN, "w") as f:
            json.dump(self.entries, f)
            log.info(f"Saved docket entries to {ENTRIES_FN}.")
        with open(DOCKETS_FN, "w") as f:
            json.dump(self.dockets, f)
        log.info(f"Saved dockets to {DOCKETS_FN}.")

    def get_dockets(self, flush=False):
        log.debug("Getting dockets.")
        url = (
            self.docket_next
            if self.docket_next is not None
            else CL_DOCKET_ENDPOINT
        )
        response = requests.get(url, headers=auth_headers)
        response_data = response.json()
        self.docket_next = response_data["next"]
        json.dump(self.docket_next, open(NEXT_FN, "w"))
        for result in response_data["results"]:
            docket_id = result["id"]
            self.dockets[docket_id] = {
                "docket": result,
                "entries": [],
            }
            self.docket_queue.append(docket_id)
        if flush:
            self.flush_docket_queue()

    def flush_docket_queue(self, save=True):
        """
        Get entries for dockets in the docket queue.
        Returns a list of docket entries.
        """
        log.debug("Flushing docket queue.")
        ret = []
        while len(self.docket_queue) > 0:
            docket_id = self.docket_queue.pop()
            entries = self.get_entries(docket_id)
            if save:
                self.save()
            ret.extend(entries)
        return ret

    def get_entries(self, docket_id):
        log.debug(f"Getting docket entries for docket {docket_id}.")
        ret = []
        url = f"{CL_DE_ENDPOINT}?docket={docket_id}"
        response = requests.get(url, headers=auth_headers)
        response_data = response.json()

        for result in response_data["results"]:
            de_id = result["id"]
            doc_id = None
            description = result["description"]
            if description == "":
                if not "recap_documents" in result:
                    continue
                else:
                    for doc in result["recap_documents"]:
                        description = doc["description"]
                        doc_id = doc["id"]
                        entry = {
                            "docket_entry_id": de_id,
                            "docket_id": docket_id,
                            "doc_id": doc_id,
                            "description": description,
                            "label": None,
                        }
                        self.entries[de_id] = entry
                        self.dockets[docket_id]["entries"].append(entry)
                        ret.append(entry)
            else:
                entry = {
                    "docket_entry_id": de_id,
                    "docket_id": docket_id,
                    "doc_id": doc_id,
                    "description": description,
                    "label": None,
                }
                self.entries[de_id] = entry
                self.dockets[docket_id]["entries"].append(entry)
                ret.append(entry)
        return ret

    def generate(self, save=True):
        """Generator for infinite docket entries!"""
        while True:
            if len(self.docket_queue) == 0:
                print("Getting more dockets...\n")
                self.get_dockets()
                self.save()
            for entry in self.flush_docket_queue(save=save):
                log.info(
                    f"Yielding docket entry {entry['docket_entry_id']} in docket {entry['docket_id']}."
                )
                yield entry


def add_label(
    entry: dict,
    label: str,
    csv_writer: csv.writer,
    completed_de_ids: list,
    knowns: dict,
):
    row = [
        entry["description"],
        label,
        entry["docket_id"],
        entry["docket_entry_id"],
        entry["doc_id"],
    ]
    csv_writer.writerow(row)
    csv_writer
    output_f.flush()
    completed_de_ids.append(entry["docket_entry_id"])
    upperized = entry["description"].upper()
    if upperized not in knowns:
        knowns[upperized] = label
    log.info(
        f"Added label '{label}' to docket entry {entry['docket_entry_id']}"
    )
    print(f"Labeled {len(completed_de_ids)} entries.")


class YNValidator(Validator):
    def validate(self, document):
        text = document.text

        if text.upper() not in ("Y", "N"):
            raise ValidationError(message="Enter Y or N!")


def print_instructions():
    print(INSTRUCTIONS + "\n\t".join(LABELS) + "\n\n")


if __name__ == "__main__":
    print(__NAME__)
    log.debug("This is a debug line.")
    fetcher = DocketEntryFetcher(next=NEXT)
    completer = WordCompleter(LABELS)
    completed_de_ids = []
    knowns = {}

    # prepare output CSV file of labeled data
    output_f = open(OUTPUT_FN, "r")
    output_reader = csv.reader(output_f)
    for row in output_reader:
        description = row[0]
        label = row[1]
        docket_id = row[2]
        de_id = row[3]
        doc_id = row[4]
        completed_de_ids.append(de_id)
        knowns[description.upper()] = label
    output_f.close()

    output_f = open(OUTPUT_FN, "a")
    output_writer = csv.writer(output_f)

    print_instructions()

    for entry in fetcher.generate():
        label = None
        labeled_it = False

        upperized = entry["description"].upper()
        if upperized in knowns:
            label = knowns[upperized]
            add_label(entry, label, output_writer, completed_de_ids, knowns)
            labeled_it = True

        while not labeled_it:
            print(entry["description"])

            try:
                label = prompt(
                    PROMPT, completer=completer, complete_while_typing=True
                )
            except EOFError:
                log.info("User quit.")
                print("Goodbye!")
                sys.exit()

            if label == "":
                label = "other"

            if label == "?":
                print_instructions()
                print()
                continue

            if label not in LABELS:
                log.info(f"User entered invalid label: {label}")
                add_yn = prompt(
                    f"Do you want to add '{label}' as a new label? (y/n) >",
                    validator=YNValidator(),
                )
                if add_yn.upper() == "Y":
                    LABELS.append(label)
                    with open(LABELS_FN, "w") as f:
                        json.dump(LABELS, f)
                    print(f"Added '{label}' to labels.")

                    add_label(
                        entry, label, output_writer, completed_de_ids, knowns
                    )
                    labeled_it = True
                    print()
                elif add_yn.upper() == "N":
                    log.info("User chose not to add new label.")
                    print("OK. Now what?")
                    continue
                else:
                    print("Try again.")
                    print()
            else:
                add_label(
                    entry, label, output_writer, completed_de_ids, knowns
                )
                labeled_it = True
                print()

    output_f.close()
    log.info("Done.")
    print("Done!")
