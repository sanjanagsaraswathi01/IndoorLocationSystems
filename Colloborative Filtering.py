# -*- coding: utf-8 -*-
"""CF.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1htq7qaGc6D8LVK9aN9IMJRBAevs0-jur

Dataset Description:
Data taken from kaggle MovieLens
1. movies_metadata.csv - contains detailed meta data for the movies
2. Ratings_small.csv - contains user ratings for thr movie
-> Columns taken from movies_metadata.csv : movieID and title
-> Columns taken from ratings_small.csv: userId, movieID and rating.
+ MovieId: Int
+ Title: String
+ userId: Int (Range: 1 to 671)
+ Rating: Decimal (Range: 0.5 to 5.0)

Loading the datasets
"""

# Commented out IPython magic to ensure Python compatibility.
import warnings
warnings.filterwarnings("ignore")
# %autosave 150
# %matplotlib inline
import pandas as pd
import numpy as np
import math
import matplotlib.pylab as plt
from scipy.stats import pearsonr
from sklearn.metrics import mean_squared_error
from math import sqrt
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

"""Data Selection:"""

#file='../input/the-movies-dataset/'

cols_ratings = ['userId', 'movieId', 'rating']
ratings = pd.read_csv('ratings_small.csv', usecols=cols_ratings)
ratings=ratings.rename(columns={"userId": "user_id","movieId":"movie_id"})
ratings['movie_id'] = ratings['movie_id'].astype('str')

cols_titles = ['id', 'original_title']
titles = pd.read_csv('movies_metadata.csv', usecols=cols_titles)
titles=titles.rename(columns={"id": "movie_id","original_title":"title"})

data = pd.merge(ratings, titles)

"""Data Transformation:"""

def overview(df):
    print('SHAPE:\n',df.shape)
    print('COLUMN NAMES:\n', df.columns.tolist())
    print('UNIQUE VALUES PER COLUMN:\n', df.nunique())
    print('COLUMNS WITH MISSING DATA:\n',df.isnull().sum())
    print('SAMPLE:\n',df.sample(10))
    print('INFO:\n',df.info())

overview(data)

"""Data Preprocessing: Data Splitting
+ Split ratio: 80:20
"""

def assign_to_testset(df):
    sampled_ids = np.random.choice(df.index,size=np.int64(np.ceil(df.index.size * 0.2)),replace=False)
    df.loc[sampled_ids, 'for_testing'] = True
    return df

data['for_testing'] = False
grouped = data.groupby('user_id', group_keys=False).apply(assign_to_testset)
data_train = data[grouped.for_testing == False]
data_test = data[grouped.for_testing == True]
print(data_train.shape)
print(data_test.shape)
print(data_train.index & data_test.index)

print("Training data_set has "+ str(data_train.shape[0]) +" ratings")
print("Test data set has "+ str(data_test.shape[0]) +" ratings")

"""Similarity Measures:
a) Pearson Corelation Coeffcient (PCC)
"""

def SimPearson(df,user1,user2,items_min=1):
    #movies rated by of user1
    data_user1=df[df['user_id']==user1]
    #movies rated by of user2
    data_user2=df[df['user_id']==user2]

    #movies rated by both
    both_rated=pd.merge(data_user1,data_user2,on='movie_id')

    if len(both_rated)<2:
        return 0
    if len(both_rated)<items_min:
        return 0
    res=pearsonr(both_rated.rating_x,both_rated.rating_y)[0]
    if(np.isnan(res)):
        return 0
    return res

"""b) Euclidean Distance"""

def SimEuclidean(df, user1, user2, items_min=1):
    # Movies rated by user1
    data_user1 = df[df['user_id'] == user1]

    # Movies rated by user2
    data_user2 = df[df['user_id'] == user2]

    # Movies rated by both
    both_rated = pd.merge(data_user1, data_user2, on='movie_id')

    # Check if the number of common rated items is less than minimum threshold
    if len(both_rated) < items_min:
        return 0

    # Calculate Euclidean distance
    diff_ratings = both_rated['rating_x'] - both_rated['rating_y']
    dist = np.sqrt(np.sum(np.square(diff_ratings)))

    # Inverse of distance to get similarity (higher distance = lower similarity)
    # Avoid division by zero
    if dist == 0:
        return 1
    else:
        return 1 / (1 + dist)

"""c) Cosine Similarity"""

def SimCosine(df, user1, user2, items_min=1):
    # Movies rated by user1
    data_user1 = df[df['user_id'] == user1]

    # Movies rated by user2
    data_user2 = df[df['user_id'] == user2]

    # Movies rated by both
    both_rated = pd.merge(data_user1, data_user2, on='movie_id')

    # Check if the number of common rated items is less than the minimum threshold
    if len(both_rated) < items_min:
        return 0

    # Extracting the ratings and reshaping them to 2D arrays for cosine_similarity function
    ratings1 = both_rated['rating_x'].values.reshape(1, -1)
    ratings2 = both_rated['rating_y'].values.reshape(1, -1)

    # Calculate cosine similarity
    cos_sim = cosine_similarity(ratings1, ratings2)[0][0]

    return cos_sim

minidata = data[data['user_id']<100] # get only data from 100 users
print(minidata.shape)

minidata.loc[:,'for_testing'] = False
grouped = minidata.groupby('user_id', group_keys=False).apply(assign_to_testset)
minidata_train = minidata[grouped.for_testing == False]
minidata_test = minidata[grouped.for_testing == True]

print(minidata_train.shape )
print(minidata_test.shape )

print('users:', minidata.user_id.nunique() )
print('movies:',minidata.movie_id.nunique() )

"""Data mining:"""

class CF: #Collaborative Filtering
    def __init__ (self,df,simfunc):
        self.df=df
        self.simfunc=simfunc
        self.sim = pd.DataFrame(np.sum([0]),columns=data_train.user_id.unique(), index=data_train.user_id.unique())

    def compute_similarities(self):
        allusers=set(self.df.user_id)
        self.sim = {} #we are going to create a dictionary with the calculated similarities between users
        for user1 in allusers:
            self.sim.setdefault(user1, {})
            #we take all the movies whatched by user1
            movies_user1=data_train[data_train['user_id']==user1]['movie_id']
            #we take all the users that have whatched any of the movies user1 has
            data_mini=pd.merge(data_train,movies_user1,on='movie_id')

            for user2 in allusers:
                if user1==user2:continue
                self.sim.setdefault(user2, {})
                if (user1 in self.sim[user2]):continue
                # we calculate the similarity between user1 and user2
                simi=self.simfunc(data_mini,user1,user2)
                if (simi<0):
                    self.sim[user1][user2]=0
                    self.sim[user2][user1]=0
                else: # we store the similarity in the dictionary
                    self.sim[user1][user2]=simi
                    self.sim[user2][user1]=simi
        return self.sim

    def predict(self,user,movie):
        allratings=self.df[(self.df['movie_id']==movie)]
        allusers_movie=set(allratings.user_id)

        numerator=0.0
        denominator=0.0

        for u in allusers_movie:
            if u==user:continue
            #we calculate the numerator and denominator of the prediction formula we saw at the beginning
            numerator+=self.sim[user][u]*float(allratings[allratings['user_id']==u]['rating'])
            denominator+=self.sim[user][u]

        if denominator==0:
            if self.df.rating[self.df['movie_id']==movie].mean()>0:
            # if the sum of similarities is 0 we use the mean of ratings for that movie
                return self.df.rating[self.df['movie_id']==movie].mean()
            else:
            # else return mean rating for that user
                return self.df.rating[self.df['user_id']==user].mean()

        return numerator/denominator

CF_userbased_P=CF(df=minidata_train,simfunc=SimPearson)
dicsim_P=CF_userbased_P.compute_similarities()

CF_userbased=CF(df=minidata_train,simfunc=SimEuclidean)
dicsim=CF_userbased.compute_similarities()
CF_userbased_C=CF(df=minidata_train,simfunc=SimCosine)
dicsim_C=CF_userbased_C.compute_similarities()

"""Similarity scores:"""

#Euclideian
dicsim[2]

#cosine
dicsim_C[2]

#Pearson
dicsim_P[2]

#Euclidean
example_pred=CF_userbased.predict(user=13,movie=1)
print(example_pred)
#Pearson Correlation
example_pred_P=CF_userbased_P.predict(user=13,movie=1)
print(example_pred_P)
#Cosine
example_pred_C=CF_userbased_C.predict(user=13,movie=1)
print(example_pred_C)

"""Evaluation:"""

from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler
from math import sqrt
import pandas as pd
import numpy as np

def evaluation(dftest, CF_instance, threshold=0.5):
    preds_test = []
    for user in set(dftest.user_id):
        for movie in set(dftest[dftest['user_id'] == user]['movie_id'].tolist()):
            pred = CF_instance.predict(user=user, movie=movie)
            preds_test.append({
                'user_id': user,
                'movie_id': movie,
                'pred_rating': pred
            })

    pred_ratings = pd.DataFrame(preds_test)
    valid_union = pd.merge(pred_ratings, dftest, on=['user_id', 'movie_id'])

    real_rating = valid_union['rating'].values
    estimated = valid_union['pred_rating'].values

    # RMSE
    rms = sqrt(mean_squared_error(real_rating, estimated))

    # Accuracy
    correct_predictions = abs(real_rating - estimated) <= threshold
    accuracy = correct_predictions.sum() / len(correct_predictions)

    # Normalized Mean Absolute Error (NMAE)
    scaler = MinMaxScaler()
    real_rating_scaled = scaler.fit_transform(real_rating.reshape(-1, 1)).flatten()
    estimated_scaled = scaler.transform(estimated.reshape(-1, 1)).flatten()
    mae = np.mean(np.abs(real_rating_scaled - estimated_scaled))
    nmae = mae / (scaler.data_max_ - scaler.data_min_)

    # Coverage
    coverage = len(np.unique(valid_union['movie_id'])) / dftest['movie_id'].nunique()


    # R-squared
    r_squared = r2_score(real_rating, estimated)

    # Returning all metrics
    return rms, accuracy, nmae, coverage, r_squared

# For the Cosine Similarity model
rms_cosine, accuracy_cosine, nmae_cosine, coverage_cosine, r_squared_cosine = evaluation(minidata_test, CF_userbased_C, threshold=0.5)
print(f'Cosine Similarity - RMSE: {rms_cosine}, Accuracy: {accuracy_cosine}, NMAE: {nmae_cosine}, Coverage: {coverage_cosine}, R-squared: {r_squared_cosine}')

# For the Pearson Correlation model
rms_pearson, accuracy_pearson, nmae_pearson, coverage_pearson, r_squared_pearson = evaluation(minidata_test, CF_userbased_P, threshold=0.5)
print(f'Pearson Correlation - RMSE: {rms_pearson}, Accuracy: {accuracy_pearson}, NMAE: {nmae_pearson}, Coverage: {coverage_pearson}, R-squared: {r_squared_pearson}')

# For the Euclidean Distance model
rms_euclidean, accuracy_euclidean, nmae_euclidean, coverage_euclidean, r_squared_euclidean = evaluation(minidata_test, CF_userbased, threshold=0.5)
print(f'Euclidean Distance - RMSE: {rms_euclidean}, Accuracy: {accuracy_euclidean}, NMAE: {nmae_euclidean}, Coverage: {coverage_euclidean}, R-squared: {r_squared_euclidean}')

"""Visual Representation"""

import matplotlib.pyplot as plt
import numpy as np

# Define the metrics for each model
model_metrics = {
    'Cosine Similarity': [rms_cosine, accuracy_cosine, nmae_cosine, coverage_cosine, r_squared_cosine],
    'Pearson Correlation': [rms_pearson, accuracy_pearson, nmae_pearson, coverage_pearson, r_squared_pearson],
    'Euclidean Distance': [rms_euclidean, accuracy_euclidean, nmae_euclidean, coverage_euclidean, r_squared_euclidean]
}

# Metric names for labeling
metric_names = ['RMSE', 'Accuracy', 'NMAE', 'Coverage', 'R-squared']

# Create figure and axes
fig, ax = plt.subplots(figsize=(15, 7))

# Set position of bar on X axis
barWidth = 0.25
r1 = np.arange(len(metric_names))
r2 = [x + barWidth for x in r1]
r3 = [x + barWidth for x in r2]

# Make the plot
ax.bar(r1, model_metrics['Cosine Similarity'], color='b', width=barWidth, edgecolor='grey', label='Cosine Similarity')
ax.bar(r2, model_metrics['Pearson Correlation'], color='r', width=barWidth, edgecolor='grey', label='Pearson Correlation')
ax.bar(r3, model_metrics['Euclidean Distance'], color='g', width=barWidth, edgecolor='grey', label='Euclidean Distance')

# Add labels, title and axes ticks
ax.set_xlabel('Metrics', fontweight='bold')
ax.set_ylabel('Scores', fontweight='bold')
ax.set_title('Comparison of Collaborative Filtering Models')
ax.set_xticks([r + barWidth for r in range(len(metric_names))])
ax.set_xticklabels(metric_names)

# Create legend & Show graphic
ax.legend()
plt.show()