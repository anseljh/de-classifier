"""
A first whack at classifying docket entries!
Uses labeled.csv, which is labeled data created with labeler.py.
Does some preprocessing that may or may not be a good idea.
"""

import csv
import random

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, classification_report
import numpy as np


INPUT_FN = "labeled.csv"
TOP_N = 10


def load_dataset():
    dataset = {}
    with open(INPUT_FN, "r") as f:
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
    return dataset


def preprocess_description(description):
    lowered = description.lower()
    tokens = lowered.split()

    stops = stopwords.words("english")
    unstopped = [word for word in tokens if word not in stops]

    lemmatizer = WordNetLemmatizer()
    lemmas = [lemmatizer.lemmatize(word) for word in unstopped]

    return " ".join(lemmas)


def preprocess(dataset):
    """
    Do some text preprocessing
    """
    for de_id in dataset:
        dataset[de_id]["pp"] = preprocess_description(
            dataset[de_id]["description"]
        )
    return dataset


def split_dataset(dataset, train_size=0.70, wanted="pp", label="label"):
    """
    Split the dataset into training and testing sets
    """
    training_set, testing_set = [], []

    # randomize keys
    keys = list(dataset.keys())
    random.shuffle(keys)

    cutoff = round(len(keys) * train_size)
    n = 0
    for key in keys:
        if n < cutoff:
            # add to training set
            training_set.append((dataset[key][wanted], dataset[key][label]))
        else:
            # add to testing set
            testing_set.append((dataset[key][wanted], dataset[key][label]))
        n += 1
    print(
        f"Training set: {len(training_set)}\nTesting set: {len(testing_set)}"
    )
    return training_set, testing_set


if __name__ == "__main__":
    print("Loading data...")
    dataset = load_dataset()
    print()

    print("Preprocessing...")
    dataset = preprocess(dataset)
    for de_id in list(dataset.keys())[:20]:
        print(dataset[de_id]["pp"])
    print()

    print("Sampling...")
    train, test = split_dataset(dataset)
    for item in train[:10]:
        print(item)
    print()

    print("Vectorizing...")
    x_train = np.array([item[0] for item in train])  # features
    y_train = np.array([item[1] for item in train])  # label
    x_test = np.array([item[0] for item in test])  # features
    y_test = np.array([item[1] for item in test])  # label
    vectorizer = TfidfVectorizer(
        min_df=2,
        ngram_range=(1, 2),
        stop_words="english",
        strip_accents="unicode",
        norm="l2",
    )
    X_train = vectorizer.fit_transform(x_train)
    X_test = vectorizer.transform(x_test)
    print()

    # Naive Bayes classifier
    # https://learning-oreilly-com.rpa.sccl.org/library/view/natural-language-processing/9781787285101/ch06s03.html
    print("Running Naive Bayes classifier...")
    nb_classifier = MultinomialNB().fit(X_train, y_train)
    y_pred = nb_classifier.predict(X_test)
    # cm = confusion_matrix(y_test, y_pred)
    # print("Confusion Matrix:")
    # print(cm)
    cr = classification_report(y_test, y_pred)
    print("Classification Report:")
    print(cr)
    print()

    # Try to find out about features
    clf = nb_classifier
    # feature_names = vectorizer.get_feature_names()
    feature_names = vectorizer.get_feature_names_out()
    print(f"Number of features: {len(feature_names)}")
    print(feature_names[:10])
