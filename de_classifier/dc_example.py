# Adapted from:
# https://www.datacamp.com/tutorial/text-classification-python

# reading data

import pandas as pd
import re
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn import metrics


data = pd.read_csv(
    # "https://raw.githubusercontent.com/mohitgupta-omg/Kaggle-SMS-Spam-Collection-Dataset-/master/spam.csv",
    "labeled-1.csv",
    encoding="latin-1",
)
print(data.head())

# drop unnecessary columns and rename cols
data.drop(["Docket Entry ID", "Document ID"], axis=1, inplace=True)
data.columns = ["text", "label"]
print(data.head())
print(data.isna().sum())

# create a list text
text = list(data["text"])

# preprocessing loop
lemmatizer = WordNetLemmatizer()
corpus = []
pattern = "[^a-zA-Z]"
comp = re.compile(pattern)
print(text[:10])
print(len(text))
for i in range(len(text)):
    r = None
    # print(text[i])
    # print(type(text[i]))
    if (
        text[i] is None or type(text[i]) is float
    ):  # or text[i] is pd.isnull(text[i]) or text[i]:
        r = ""
        # print("it's None.")
    else:
        # print("it's not None.")
        # r = re.sub(pattern, " ", text[i])
        r = comp.sub(" ", text[i])
        r = r.lower()
        r = r.split()
        r = [word for word in r if word not in stopwords.words("english")]
        r = [lemmatizer.lemmatize(word) for word in r]
        r = " ".join(r)
    corpus.append(r)

# assign corpus to data['text']
data["text"] = corpus
print(data.head())

# Create Feature and Label sets
X = data["text"]
y = data["label"]

# train test split (66% train - 33% test)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.33, random_state=123
)
print("Training Data :", X_train.shape)
print("Testing Data : ", X_test.shape)

# Train Bag of Words model
cv = CountVectorizer()
X_train_cv = cv.fit_transform(X_train)
print(X_train_cv.shape)


# Training Logistic Regression model
lr = LogisticRegression()
lr.fit(X_train_cv, y_train)

# transform X_test using CV
X_test_cv = cv.transform(X_test)

# generate predictions
predictions = lr.predict(X_test_cv)
print("Predictions:")
print(predictions)
print()

# confusion matrix
all_labels = ("pleading", "motion", "declaration", "judgment", "order", "other")
df = pd.DataFrame(metrics.confusion_matrix(y_test,predictions), index=all_labels, columns=all_labels)
                  #index=['ham','spam'], columns=['ham','spam'])
print(df)
