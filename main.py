#!/usr/bin/env python3
#  -*- coding: utf-8 -*-

import traceback, os
import numpy as np
from utils.data_manager import build_URM, build_ICM, build_UCM, get_statistics_URM, get_target_users
from utils.evaluation import evaluate_algorithm
from utils.Evaluation.Evaluator import EvaluatorHoldout
from utils.ParameterTuning.hyperparameter_search import runParameterSearch_Collaborative, runParameterSearch_Content
from utils.DataIO import DataIO
from utils.create_submission_file import create_csv
from utils.data_splitter import split_train_validation_random_holdout, split_train_leave_k_out_user_wise

######################################################################
##########                                                  ##########
##########                  PURE COLLABORATIVE              ##########
##########                                                  ##########
######################################################################
# Non-Personalized
from recommenders.RandomRecommender import RandomRecommender
from recommenders.TopPopRecommender import TopPopRecommender
# Global effects not implemented for implicit ratings


# KNN
from recommenders.KNN.UserKNNCFRecommender import UserKNNCFRecommender
from recommenders.KNN.ItemKNNCFRecommender import ItemKNNCFRecommender
from recommenders.KNN.ItemKNNSimilarityHybridRecommender import ItemKNNSimilarityHybridRecommender

# Graph-based
from recommenders.GraphBased.P3alphaRecommender import P3alphaRecommender
from recommenders.GraphBased.RP3betaRecommender import RP3betaRecommender

# KNN machine learning
# from SLIM_BPR.Cython.SLIM_BPR_Cython import SLIM_BPR_Cython
# from SLIM_ElasticNet.SLIMElasticNetRecommender import SLIMElasticNetRecommender

# Matrix Factorization
from recommenders.PureSVDRecommender import PureSVDRecommender
# from MatrixFactorization.IALSRecommender import IALSRecommender
# from MatrixFactorization.NMFRecommender import NMFRecommender
# from MatrixFactorization.Cython.MatrixFactorization_Cython import MatrixFactorization_BPR_Cython,\
#     MatrixFactorization_FunkSVD_Cython, MatrixFactorization_AsySVD_Cython


######################################################################
##########                                                  ##########
##########                  PURE CONTENT BASED              ##########
##########                                                  ##########
######################################################################
from recommenders.KNN.ItemKNNCBFRecommender import ItemKNNCBFRecommender
from recommenders.KNN.UserKNNCBFRecommender import UserKNNCBFRecommender

######################################################################
##########                                                  ##########
##########                 HYBRID RECOMMENDERS              ##########
##########                                                  ##########
######################################################################
from recommenders.Hybrid.CFW_D_Similarity_Linalg import CFW_D_Similarity_Linalg
from recommenders.Hybrid.ItemKNNScoresHybridRecommender import ItemKNNScoresHybridRecommender


# Hyperparameters tuning
# ----------------------
def hyperparams_tuning(recommender_class):
    global URM_train, URM_validation, URM_test, cutoff

    metric_to_optimize = "MAP"

    evaluator_validation = EvaluatorHoldout(URM_validation, cutoff_list=[cutoff])
    evaluator_test = EvaluatorHoldout(URM_test, cutoff_list=[cutoff, cutoff + 5])
    evaluator_validation_earlystopping = EvaluatorHoldout(URM_train, cutoff_list=[cutoff], exclude_seen=False)

    output_folder_path = "result_experiments/"

    # # If directory does not exist, create
    cwd = os.getcwd()
    if not os.path.exists(os.path.join(cwd, output_folder_path)):
        os.makedirs(output_folder_path)

    n_cases = 8  # 2
    n_random_starts = 5  # int(n_cases / 3)

    save_model = "no"
    allow_weighting = True  # provides better results
    similarity_type_list = ["cosine"]
    similarity_type = similarity_type_list[0]  # KNN Recommenders on similarity_type

    ICM_name = "ICM_all"

    output_file_name_root = "{}_metadata.zip".format(recommender_class.RECOMMENDER_NAME)

    # Non-personalized and Collaborative
    if recommender_class in [RandomRecommender, TopPopRecommender, ItemKNNCFRecommender, UserKNNCFRecommender,
                             PureSVDRecommender, P3alphaRecommender, RP3betaRecommender]:

        if recommender_class in [ItemKNNCFRecommender, UserKNNCFRecommender]:
            output_file_name_root = "{}_{}_metadata.zip".format(recommender_class.RECOMMENDER_NAME,
                                                                similarity_type)

        try:
            runParameterSearch_Collaborative(recommender_class=recommender_class,
                                             URM_train=URM_train,
                                             metric_to_optimize=metric_to_optimize,
                                             evaluator_validation=evaluator_validation,
                                             evaluator_test=evaluator_test,
                                             evaluator_validation_earlystopping=evaluator_validation_earlystopping,
                                             output_folder_path=output_folder_path,
                                             n_cases=n_cases,
                                             n_random_starts=n_random_starts,
                                             save_model=save_model,
                                             allow_weighting=allow_weighting,
                                             similarity_type_list=similarity_type_list)

        except Exception as e:
            print("On recommender {} Exception {}".format(recommender_class, str(e)))
            traceback.print_exc()


    # Content-based
    elif recommender_class in [ItemKNNCBFRecommender, UserKNNCBFRecommender]:
        print("content")

        output_file_name_root = "{}_{}_{}_metadata.zip".format(recommender_class.RECOMMENDER_NAME,
                                                               ICM_name, similarity_type)

        try:
            runParameterSearch_Content(recommender_class=recommender_class,
                                       URM_train=URM_train,
                                       ICM_object=ICM_all,
                                       ICM_name=ICM_name,
                                       n_cases=n_cases,
                                       n_random_starts=n_random_starts,
                                       save_model=save_model,
                                       evaluator_validation=evaluator_validation,
                                       evaluator_test=evaluator_test,
                                       metric_to_optimize=metric_to_optimize,
                                       output_folder_path=output_folder_path,
                                       allow_weighting=allow_weighting,
                                       similarity_type_list=similarity_type_list)

        except Exception as e:
            print("On recommender {} Exception {}".format(recommender_class, str(e)))
            traceback.print_exc()

    # Load best_parameters for training
    data_loader = DataIO(folder_path=output_folder_path)
    search_metadata = data_loader.load_data(output_file_name_root)
    best_parameters = search_metadata["hyperparameters_best"]  # dictionary with all the fit parameters
    print("{}_best_parameters {}".format(recommender_class.RECOMMENDER_NAME, best_parameters))

    return best_parameters


# Fit recommenders
# -----------------

def fit_recommender(recommender_class, URM, ICM=None):

    apply_hyperparams_tuning = False

    # Non-personalized
    if recommender_class in non_personalized_list:
        recommender = recommender_class(URM)
        recommender.fit()

    # Content-based and Collaborative recommenders
    elif recommender_class in content_algorithm_list or \
            recommender_class in collaborative_algorithm_list:

        if recommender_class in content_algorithm_list:
            recommender = recommender_class(URM, ICM)  # todo: ICM_all or ICM_train?

        elif recommender_class in collaborative_algorithm_list:
            recommender = recommender_class(URM)

        if apply_hyperparams_tuning:
            best_parameters = hyperparams_tuning(recommender_class)
        else:
            best_parameters = best_parameters_list[recommender_class.RECOMMENDER_NAME]

        recommender.fit(**best_parameters)

    # Hybrid recommenders
    elif recommender_class is ItemKNNSimilarityHybridRecommender:
        # Hybrid: ItemKNNCF + P3alpha

        itemKNNCF = ItemKNNCFRecommender(URM)

        if apply_hyperparams_tuning:
            best_parameters_itemKNNCF = hyperparams_tuning(ItemKNNCFRecommender)
        else:
            best_parameters_itemKNNCF = best_parameters_list["ItemKNNCFRecommender"]

            # best_parameters_itemKNNCF = {'topK': 9, 'shrink': 47, 'similarity': 'cosine', 'normalize': True,
            #                    'feature_weighting': 'none'}

        itemKNNCF.fit(**best_parameters_itemKNNCF)

        ##########################################################################################

        P3alpha = P3alphaRecommender(URM)

        if apply_hyperparams_tuning:
            best_parameters_P3alpha = hyperparams_tuning(P3alphaRecommender)
        else:
            best_parameters_P3alpha = best_parameters_list["P3alphaRecommender"]

            # best_parameters_P3alpha = {'topK': 23, 'alpha': 0.014269061954631738, 'normalize_similarity': True}

        P3alpha.fit(**best_parameters_P3alpha)

        recommender = ItemKNNSimilarityHybridRecommender(URM, itemKNNCF.W_sparse, P3alpha.W_sparse)
        best_parameters = {'alpha': 0.6}
        recommender.fit(**best_parameters)

        # Hybrid: ItemKNNCF + itemKNNCBF
        # itemKNNCBF = ItemKNNCBFRecommender(URM_train, ICM_all)
        #
        # if apply_hyperparams_tuning:
        #     best_parameters_itemKNNCBF = hyperparams_tuning(ItemKNNCBFRecommender)
        # else:
        #     best_parameters_itemKNNCBF = {'topK': 983, 'shrink': 18, 'similarity': 'cosine', 'normalize': True,
        #                    'feature_weighting': 'none'}
        #
        # itemKNNCBF.fit(**best_parameters_itemKNNCBF)
        #
        # recommender = recommender_class(URM_train, itemKNNCF.W_sparse, itemKNNCBF.W_sparse)
        # best_parameters = {'alpha': 0.8}
        # recommender.fit(**best_parameters)

    # feature weighting techniques
    elif recommender_class is CFW_D_Similarity_Linalg:

        itemKNNCF = ItemKNNCFRecommender(URM)

        if apply_hyperparams_tuning:
            best_parameters_itemKNNCF = hyperparams_tuning(ItemKNNCFRecommender)
        else:
            best_parameters_itemKNNCF = best_parameters_list["ItemKNNCFRecommender"]

            # best_parameters_itemKNNCF = {'topK': 9, 'shrink': 47, 'similarity': 'cosine', 'normalize': True,
            #                              'feature_weighting': 'none'}

        itemKNNCF.fit(**best_parameters_itemKNNCF)

        W_sparse_CF = itemKNNCF.W_sparse

        # Weighted Content-based similarity
        recommender = CFW_D_Similarity_Linalg(URM, ICM, W_sparse_CF)
        recommender.fit()

    elif recommender_class is ItemKNNScoresHybridRecommender:
        # Hybrid: ItemKNNCF + pureSVD
        itemKNNCF = ItemKNNCFRecommender(URM)

        if apply_hyperparams_tuning:
            best_parameters_itemKNNCF = hyperparams_tuning(ItemKNNCFRecommender)
        else:
            best_parameters_itemKNNCF = best_parameters_list["ItemKNNCFRecommender"]

        # best_parameters_itemKNNCF = {'topK': 43, 'shrink': 997, 'similarity': 'cosine',
        #                              'normalize': True, 'feature_weighting': 'TF-IDF'}

        itemKNNCF.fit(**best_parameters_itemKNNCF)

        ##########################################################################################

        pureSVD = PureSVDRecommender(URM)

        if apply_hyperparams_tuning:
            best_parameters_pureSVD = hyperparams_tuning(PureSVDRecommender)
        else:
            best_parameters_pureSVD = best_parameters_list["PureSVDRecommender"]

            # best_parameters_pureSVD = {'num_factors': 50}

        pureSVD.fit(**best_parameters_pureSVD)

        recommender = ItemKNNScoresHybridRecommender(URM, itemKNNCF, pureSVD)
        best_parameters = {'alpha': 0.6}
        recommender.fit(**best_parameters)

    return recommender


# Build URM, ICM and UCM
# ----------------------

URM_all = build_URM()
ICM_all = build_ICM()
UCM_all = build_UCM(URM_all)
# get_statistics_URM(URM_all)


cutoff = 10  # k recommended_items

# URM train/validation/test splitting
# -----------------------------------
k_out = 1

# URM_train, URM_test = split_train_validation_random_holdout(URM_all, train_split=0.8)
# URM_train, URM_validation = split_train_validation_random_holdout(URM_train, train_split=0.9)

URM_train, URM_test = split_train_leave_k_out_user_wise(URM_all,
                                                        k_out=k_out,
                                                        use_validation_set=False,
                                                        leave_random_out=True)

URM_train, URM_validation = split_train_leave_k_out_user_wise(URM_train,
                                                              k_out=k_out,
                                                              use_validation_set=False,
                                                              leave_random_out=True)



# Non-personalized recommenders
non_personalized_list = [
    RandomRecommender,
    TopPopRecommender
]

# Collaborative recommenders
collaborative_algorithm_list = [
    ItemKNNCFRecommender,
    UserKNNCFRecommender,
    #     MatrixFactorization_BPR_Cython,
    # MatrixFactorization_FunkSVD_Cython,
    PureSVDRecommender,
    # SLIM_BPR_Cython,
    # SLIMElasticNetRecommender,

    # Graph-based
    P3alphaRecommender,
    RP3betaRecommender,
]

# Content-based recommenders
content_algorithm_list = [
    ItemKNNCBFRecommender,
    UserKNNCBFRecommender
]

# Hybrid recommenders
hybrid_algorithm_list = [
    ItemKNNSimilarityHybridRecommender,  # Linear combination of item-based models
    CFW_D_Similarity_Linalg,  # regression problem using linalg solver
    ItemKNNScoresHybridRecommender  # Linear combination of predictions
]

recommender_list = [
    # Non-personalized
    RandomRecommender,
    TopPopRecommender,

    # Graph-based recommenders
    P3alphaRecommender,
    RP3betaRecommender,

    # Collaborative recommenders
    ItemKNNCFRecommender,
    UserKNNCFRecommender,

    #     MatrixFactorization_BPR_Cython,
    # MatrixFactorization_FunkSVD_Cython,
    PureSVDRecommender,
    # SLIM_BPR_Cython,
    # SLIMElasticNetRecommender,

    # Content-based recommenders
    ItemKNNCBFRecommender,

    # Hybrid recommenders
    ItemKNNSimilarityHybridRecommender,
    CFW_D_Similarity_Linalg,
    ItemKNNScoresHybridRecommender
]


# Best hyperparameters found by tuning
# ------------------------------------

best_parameters_list = {

    # Collaborative recommenders
    'ItemKNNCFRecommender': {'topK': 9, 'shrink': 47, 'similarity': 'cosine', 'normalize': True,
                             'feature_weighting': 'none'},

    #     UserKNNCFRecommender,

    'MatrixFactorization_BPR_Cython': {'sgd_mode': 'adagrad', 'epochs': 1500, 'num_factors': 177, 'batch_size': 4,
                                       'positive_reg': 2.3859950782265896e-05,
                                       'negative_reg': 7.572911338047984e-05,
                                       'learning_rate': 0.0005586331284886803},

    'PureSVDRecommender': {'num_factors': 50},

    'P3alphaRecommender': {'topK': 23, 'alpha': 0.014269061954631738, 'normalize_similarity': True},

    'RP3betaRecommender': {'topK': 665, 'alpha': 0.33783086087987796, 'beta': 0.019967033755573075,
                           'normalize_similarity': True},

    # Content-based recommenders

    'ItemKNNCBFRecommender': {'topK': 972, 'shrink': 993, 'similarity': 'cosine', 'normalize': False,
                              'feature_weighting': 'BM25'},

}


################################################################################################################

# User-wise hybrids
# -----------------

# Models do not have the same accuracy for different user types.
# Let's divide the users according to their profile length and then compare
# the recommendation quality we get from a CF model

def recommendations_quality_by_group():
    # TopPop
    topPop = fit_recommender(TopPopRecommender, URM_train, ICM_all)

    # ItemCF
    itemKNNCF = fit_recommender(ItemKNNCFRecommender, URM_train)

    # ItemCBF
    itemKNNCBF = fit_recommender(ItemKNNCBFRecommender, URM_train, ICM_all)

    # P3alpha
    P3alpha = fit_recommender(P3alphaRecommender, URM_train)

    # RP3beta
    RP3beta = fit_recommender(RP3betaRecommender, URM_train)

    # PureSVD
    pureSVD = fit_recommender(PureSVDRecommender, URM_train)

    # Similarity Hybrid: linear combination of item-based models
    # ----------------------------------------------------------

    # ItemKNNCF + itemKNNCBF
    itemCBF_similarity_hybrid = ItemKNNSimilarityHybridRecommender(URM_train, itemKNNCF.W_sparse, itemKNNCBF.W_sparse)
    best_parameters = {'alpha': 0.6}
    itemCBF_similarity_hybrid.fit(**best_parameters)

    # ItemKNNCF + P3alpha
    itemCF_alpha_similarity_hybrid = ItemKNNSimilarityHybridRecommender(URM_train, itemKNNCF.W_sparse, P3alpha.W_sparse)
    best_parameters = {'alpha': 0.6}
    itemCF_alpha_similarity_hybrid.fit(**best_parameters)

    # ItemKNNCF + RP3beta
    itemCF_beta_similarity_hybrid = ItemKNNSimilarityHybridRecommender(URM_train, itemKNNCF.W_sparse, RP3beta.W_sparse)
    best_parameters = {'alpha': 0.6}
    itemCF_beta_similarity_hybrid.fit(**best_parameters)

    # P3alpha + RP3beta
    itemCF_alpha_beta_similarity_hybrid = ItemKNNSimilarityHybridRecommender(URM_train, P3alpha.W_sparse, RP3beta.W_sparse)
    best_parameters = {'alpha': 0.6}
    itemCF_alpha_beta_similarity_hybrid.fit(**best_parameters)

    # Score Hybrid: linear combination of heterogeneous models (combination of predictions)
    # --------------------------------------------------------------------------------------

    # ItemKNNCF + pureSVD
    itemCF_scores_hybrid = ItemKNNScoresHybridRecommender(URM_train, itemKNNCF, pureSVD)
    best_parameters = {'alpha': 0.6}
    itemCF_scores_hybrid.fit(**best_parameters)

    # # User-wise discrimination
    # --------------------------

    profile_length = np.ediff1d(URM_train.indptr)  # users' profile
    block_size = int(len(profile_length) * 0.15)
    n_users, n_items = URM_train.shape
    num_groups = int(np.ceil(n_users / block_size))
    sorted_users = np.argsort(profile_length)

    MAP_topPop_per_group = []
    # MAP_itemKNNCF_per_group = []
    # MAP_itemKNNCBF_per_group = []
    # MAP_itemCBF_similarity_hybrid_per_group = []
    MAP_itemCF_alpha_similarity_hybrid_per_group = []
    MAP_itemCF_beta_similarity_hybrid_per_group = []
    MAP_itemCF_alpha_beta_similarity_hybrid_per_group = []
    # MAP_itemCF_scores_hybrid_per_group = []

    for group_id in range(0, num_groups):
        start_pos = group_id * block_size
        end_pos = min((group_id + 1) * block_size, len(profile_length))

        users_in_group = sorted_users[start_pos:end_pos]

        users_in_group_p_len = profile_length[users_in_group]

        print("Group {}, average p.len {:.2f}, min {}, max {}".format(group_id,
                                                                      users_in_group_p_len.mean(),
                                                                      users_in_group_p_len.min(),
                                                                      users_in_group_p_len.max()))

        users_not_in_group_flag = np.isin(sorted_users, users_in_group, invert=True)
        users_not_in_group = sorted_users[users_not_in_group_flag]

        evaluator_test = EvaluatorHoldout(URM_test,
                                          cutoff_list=[cutoff],
                                          ignore_users=users_not_in_group,
                                          exclude_seen=False)

        results, _ = evaluator_test.evaluateRecommender(topPop)
        MAP_topPop_per_group.append(results[cutoff]["MAP"])

        # results, _ = evaluator_test.evaluateRecommender(itemKNNCF)
        # MAP_itemKNNCF_per_group.append(results[cutoff]["MAP"])

        # results, _ = evaluator_test.evaluateRecommender(itemKNNCBF)
        # MAP_itemKNNCBF_per_group.append(results[cutoff]["MAP"])

        # results, _ = evaluator_test.evaluateRecommender(itemCBF_similarity_hybrid)
        # MAP_itemCBF_similarity_hybrid_per_group.append(results[cutoff]["MAP"])

        results, _ = evaluator_test.evaluateRecommender(itemCF_alpha_similarity_hybrid)
        MAP_itemCF_alpha_similarity_hybrid_per_group.append(results[cutoff]["MAP"])

        results, _ = evaluator_test.evaluateRecommender(itemCF_beta_similarity_hybrid)
        MAP_itemCF_beta_similarity_hybrid_per_group.append(results[cutoff]["MAP"])

        results, _ = evaluator_test.evaluateRecommender(itemCF_alpha_beta_similarity_hybrid)
        MAP_itemCF_alpha_beta_similarity_hybrid_per_group.append(results[cutoff]["MAP"])

        # results, _ = evaluator_test.evaluateRecommender(itemCF_scores_hybrid)
        # MAP_itemCF_scores_hybrid_per_group.append(results[cutoff]["MAP"])

    print("plotting.....")

    import matplotlib.pyplot as pyplot

    pyplot.plot(MAP_topPop_per_group, label="topPop")
    # pyplot.plot(MAP_itemKNNCF_per_group, label="itemKNNCF")
    # pyplot.plot(MAP_itemKNNCBF_per_group, label="itemKNNCBF")
    # pyplot.plot(MAP_itemCBF_similarity_hybrid_per_group, label="ItemKNNCF + ItemKNNCBF")
    # pyplot.plot(MAP_itemCF_scores_hybrid_per_group, label="ItemKNNCF + pureSVD")
    pyplot.plot(MAP_itemCF_alpha_beta_similarity_hybrid_per_group, label="P3alpha + RP3beta")
    pyplot.plot(MAP_itemCF_alpha_similarity_hybrid_per_group, label="ItemKNNCF + P3alpha")
    pyplot.plot(MAP_itemCF_beta_similarity_hybrid_per_group, label="ItemKNNCF + RP3beta")
    pyplot.ylabel('MAP')
    pyplot.xlabel('User Group')
    pyplot.legend()
    pyplot.show()


recommendations_quality_by_group()
exit(0)

################################################################################################################

# --- generate predictions --- #

# Train models on the whole dataset
# TopPop
# topPop = TopPopRecommender(URM_all)
# topPop.fit()
#
# # Hybrid: ItemKNNCF + pureSVD
# # ItemKNNCFRecommender
# itemKNNCF = ItemKNNCFRecommender(URM_all)
# best_parameters_ItemKNNCF = {'topK': 43, 'shrink': 997, 'similarity': 'cosine',
#                                  'normalize': True, 'feature_weighting': 'TF-IDF'}
# itemKNNCF.fit(**best_parameters_ItemKNNCF)
#
# # PureSVD
# pureSVD = PureSVDRecommender(URM_all)
# best_parameters_PureSVD = {'num_factors': 50}
# pureSVD.fit(**best_parameters_PureSVD)
#
# itemKNN_scores_hybrid = ItemKNNScoresHybridRecommender(URM_all, itemKNNCF, pureSVD)
# best_parameters = {'alpha': 0.9}
# itemKNN_scores_hybrid.fit(**best_parameters)
#

#
# profile_length = np.ediff1d(URM_all.indptr)
# block_size = int(len(profile_length) * 0.15)
# n_users, n_items = URM_all.shape
# num_groups = int(np.ceil(n_users / block_size))
# sorted_users = np.argsort(profile_length)
#
# users_by_group = []
#
# for group_id in range(0, num_groups):
#     start_pos = group_id * block_size
#     end_pos = min((group_id + 1) * block_size, len(profile_length))
#
#     users_in_group = sorted_users[start_pos:end_pos]
#
#     users_in_group_p_len = profile_length[users_in_group]
#
#     print("Group {} with users_in_group {}, average p.len {:.2f}, min {}, max {}".format(group_id,
#                                                                                          len(users_in_group),
#                                                                                          users_in_group_p_len.mean(),
#                                                                                          users_in_group_p_len.min(),
#                                                                                          users_in_group_p_len.max()))
#
#     # Users by group
#     users_by_group.append(users_in_group)
#
#
# # Generate predictions
# user_id_array = get_target_users()
# items = []
#
# for user_id in user_id_array:
#
#     # TopPop for users with fewer interactions
#     if user_id in users_by_group[0] or \
#             user_id in users_by_group[1]:
#         # print("user_id: {}, group: 0 or 1, topPop".format(user_id))
#         item_list = topPop.recommend(user_id,
#                                      cutoff=cutoff,
#                                      remove_seen_flag=False,
#                                      remove_top_pop_flag=False)
#     else:
#         # print("user_id: {}, group: 2, 3, 4, itemKNN_scores_hybrid".format(user_id))
#         item_list = itemKNN_scores_hybrid.recommend(user_id,
#                                                     cutoff=cutoff,
#                                                     remove_seen_flag=True,
#                                                     remove_top_pop_flag=True)
#
#     items.append(np.array(item_list))
#
#
# # save predictions on csv file
# create_csv(user_id_array, items, None)
#
# exit(0)


################################################################################################################


# Recommenders
# ------------


print('\nRecommender Systems: ')
for i, recomm_type in enumerate(recommender_list, start=1):
    print('{}. {}'.format(i, recomm_type.RECOMMENDER_NAME))

while True:
    try:
        selected = int(input('\nSelect a recommender system: '.format(i)))
        recommender_class = recommender_list[selected - 1]
        print('\n ... {} ... '.format(recommender_class.RECOMMENDER_NAME))

        recommender = fit_recommender(recommender_class, URM_train, ICM_all)

        # Evaluate model
        # --------------

        evaluator_test = EvaluatorHoldout(URM_test, cutoff_list=[cutoff])
        result_dict, _ = evaluator_test.evaluateRecommender(recommender)

        print("{} result_dict MAP {}".format(recommender.RECOMMENDER_NAME, result_dict[cutoff]["MAP"]))

        # Generate predictions
        # --------------------

        predictions = input('\nCompute and save top-10 predictions?: y - Yes  n - No\n')

        if predictions == 'y':
            # Train the model on the whole dataset using tuned params
            # -------------------------------------------------------

            recommender = fit_recommender(recommender_class, URM_all, ICM_all)

            user_id_array = get_target_users()
            item_list = recommender.recommend(user_id_array,
                                              cutoff=cutoff,
                                              remove_seen_flag=True,
                                              remove_top_pop_flag=True)

            create_csv(user_id_array, item_list, recommender_class.RECOMMENDER_NAME)

        break

    except (ValueError, IndexError):
        print('Error. Please enter number between 1 and {}'.format(i))
