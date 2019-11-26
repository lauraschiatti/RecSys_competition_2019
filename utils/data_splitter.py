#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 23/04/2019
@author: Maurizio Ferrari Dacrema
"""

import numpy as np
import scipy.sparse as sps


def split_train_leave_k_out_user_wise(URM, k_out=1, use_validation_set=True, leave_random_out=True):
    """
    The function splits an URM in two matrices selecting the k_out interactions one user at a time
    :param URM:
    :param k_out:
    :param use_validation_set:
    :param leave_random_out: leave out a random interaction
    :return:
    """

    assert k_out > 0, "k_out must be a value greater than 0, provided was '{}'".format(k_out)

    URM = sps.csr_matrix(URM)
    n_users, n_items = URM.shape

    URM_train_builder = IncrementalSparseMatrix(auto_create_row_mapper=False, n_rows=n_users,
                                                auto_create_col_mapper=False, n_cols=n_items)

    URM_test_builder = IncrementalSparseMatrix(auto_create_row_mapper=False, n_rows=n_users,
                                               auto_create_col_mapper=False, n_cols=n_items)

    if use_validation_set:
        URM_validation_builder = IncrementalSparseMatrix(auto_create_row_mapper=False, n_rows=n_users,
                                                         auto_create_col_mapper=False, n_cols=n_items)

    for user_id in range(n_users):

        start_user_position = URM.indptr[user_id]
        end_user_position = URM.indptr[user_id + 1]

        user_profile = URM.indices[start_user_position:end_user_position]

        if leave_random_out:
            indices_to_suffle = np.arange(len(user_profile), dtype=np.int)

            np.random.shuffle(indices_to_suffle)

            user_interaction_items = user_profile[indices_to_suffle]
            user_interaction_data = URM.data[start_user_position:end_user_position][indices_to_suffle]

        else:

            # The first will be sampled so the last interaction must be the first one
            interaction_position = URM.data[start_user_position:end_user_position]

            sort_interaction_index = np.argsort(-interaction_position)

            user_interaction_items = user_profile[sort_interaction_index]
            user_interaction_data = URM.data[start_user_position:end_user_position][sort_interaction_index]

        # Test interactions
        user_interaction_items_test = user_interaction_items[0:k_out]
        user_interaction_data_test = user_interaction_data[0:k_out]

        URM_test_builder.add_data_lists([user_id] * len(user_interaction_items_test), user_interaction_items_test,
                                        user_interaction_data_test)

        # validation interactions
        if use_validation_set:
            user_interaction_items_validation = user_interaction_items[k_out:k_out * 2]
            user_interaction_data_validation = user_interaction_data[k_out:k_out * 2]

            URM_validation_builder.add_data_lists([user_id] * k_out, user_interaction_items_validation,
                                                  user_interaction_data_validation)

        # Train interactions
        user_interaction_items_train = user_interaction_items[k_out * 2:]
        user_interaction_data_train = user_interaction_data[k_out * 2:]

        URM_train_builder.add_data_lists([user_id] * len(user_interaction_items_train), user_interaction_items_train,
                                         user_interaction_data_train)

    URM_train = URM_train_builder.get_SparseMatrix()
    URM_test = URM_test_builder.get_SparseMatrix()

    URM_train = sps.csr_matrix(URM_train)
    user_no_item_train = np.sum(np.ediff1d(URM_train.indptr) == 0)

    if user_no_item_train != 0:
        print("Warning: {} ({:.2f} %) of {} users have no Train items".format(user_no_item_train,
                                                                              user_no_item_train / n_users * 100,
                                                                              n_users))

    if use_validation_set:
        URM_validation = URM_validation_builder.get_SparseMatrix()

        URM_validation = sps.csr_matrix(URM_validation)
        user_no_item_validation = np.sum(np.ediff1d(URM_validation.indptr) == 0)

        if user_no_item_validation != 0:
            print("Warning: {} ({:.2f} %) of {} users have no Validation items"
                  .format(user_no_item_validation, user_no_item_validation / n_users * 100, n_users))

        return URM_train, URM_validation, URM_test

    print(URM_train.shape)
    return URM_train, URM_test


#
# def _split_data_from_original_dataset(self, save_folder_path):
#     self.dataReader_object.load_data()
#     self._load_from_DataReader_ICM_and_mappers()
#
#     URM = self.dataReader_object.get_URM_all()
#     URM = sps.csr_matrix(URM)
#
#     split_number = 2
#     if self.use_validation_set:
#         split_number += 1
#
#     # Min interactions at least self.k_out_value for each split +1 for train and validation
#     min_user_interactions = (split_number - 1) * self.k_out_value + 1
#
#     if not self.allow_cold_users:
#         user_interactions = np.ediff1d(URM.indptr)
#         user_to_preserve = user_interactions >= min_user_interactions
#         user_to_remove = np.logical_not(user_to_preserve)
#
#         self._print(
#             "Removing {} ({:.2f} %) of {} users because they have less than the {} interactions required for {} splits ({} for test [and validation if requested] +1 for train)".format(
#                 URM.shape[0] - user_to_preserve.sum(), (1 - user_to_preserve.sum() / URM.shape[0]) * 100,
#                 URM.shape[0], min_user_interactions, split_number, self.k_out_value))
#
#         URM = URM[user_to_preserve, :]
#
#         self.SPLIT_GLOBAL_MAPPER_DICT["user_original_ID_to_index"] = reconcile_mapper_with_removed_tokens(
#             self.SPLIT_GLOBAL_MAPPER_DICT["user_original_ID_to_index"],
#             np.arange(0, len(user_to_remove), dtype=np.int)[user_to_remove])
#
#     splitted_data = split_train_leave_k_out_user_wise(URM, k_out=self.k_out_value,
#                                                       use_validation_set=self.use_validation_set,
#                                                       leave_random_out=self.leave_random_out)
#
#     if self.use_validation_set:
#         URM_train, URM_validation, URM_test = splitted_data
#
#     else:
#         URM_train, URM_test = splitted_data
#
#     self.SPLIT_URM_DICT = {
#         "URM_train": URM_train,
#         "URM_test": URM_test,
#     }
#
#     if self.use_validation_set:
#         self.SPLIT_URM_DICT["URM_validation"] = URM_validation
#
#     self._save_split(save_folder_path)
#
#     self._print("Split complete")


def _verify_data_consistency(self):
    self._assert_is_initialized()

    print_preamble = "{} consistency check: ".format(self.DATA_SPLITTER_NAME)

    URM_to_load_list = ["URM_train", "URM_test"]

    if self.use_validation_set:
        URM_to_load_list.append("URM_validation")

    assert len(self.SPLIT_URM_DICT) == len(URM_to_load_list), \
        print_preamble + "The available URM are not as many as they are supposed to be. URMs are {}, expected URMs are {}".format(
            len(self.SPLIT_URM_DICT), len(URM_to_load_list))

    assert all(URM_name in self.SPLIT_URM_DICT for URM_name in
               URM_to_load_list), print_preamble + "Not all URMs have been created"
    assert all(URM_name in URM_to_load_list for URM_name in
               self.SPLIT_URM_DICT.keys()), print_preamble + "The split contains URMs that should not exist"

    URM_shape = None

    for URM_name, URM_object in self.SPLIT_URM_DICT.items():

        if URM_shape is None:
            URM_shape = URM_object.shape

            n_users, n_items = URM_shape

            assert n_users != 0, print_preamble + "Number of users in URM is 0"
            assert n_items != 0, print_preamble + "Number of items in URM is 0"

        assert URM_shape == URM_object.shape, print_preamble + "URM shape is inconsistent"

    assert self.SPLIT_URM_DICT["URM_train"].nnz != 0, print_preamble + "Number of interactions in URM Train is 0"
    assert self.SPLIT_URM_DICT["URM_test"].nnz != 0, print_preamble + "Number of interactions in URM Test is 0"

    URM = self.SPLIT_URM_DICT["URM_test"].copy()
    user_interactions = np.ediff1d(sps.csr_matrix(URM).indptr)

    assert np.all(
        user_interactions == self.k_out_value), print_preamble + "Not all users have the desired number of interactions in URM_test, {} users out of {}".format(
        (user_interactions != self.k_out_value).sum(), n_users)

    if self.use_validation_set:
        assert self.SPLIT_URM_DICT[
                   "URM_validation"].nnz != 0, print_preamble + "Number of interactions in URM Validation is 0"

        URM = self.SPLIT_URM_DICT["URM_validation"].copy()
        user_interactions = np.ediff1d(sps.csr_matrix(URM).indptr)

        assert np.all(
            user_interactions == self.k_out_value), print_preamble + "Not all users have the desired number of interactions in URM_validation, {} users out of {}".format(
            (user_interactions != self.k_out_value).sum(), n_users)

    URM = self.SPLIT_URM_DICT["URM_train"].copy()
    user_interactions = np.ediff1d(sps.csr_matrix(URM).indptr)

    if not self.allow_cold_users:
        assert np.all(
            user_interactions != 0), print_preamble + "Cold users exist despite not being allowed as per DataSplitter parameters, {} users out of {}".format(
            (user_interactions == 0).sum(), n_users)

    assert assert_disjoint_matrices(list(self.SPLIT_URM_DICT.values()))

    assert_URM_ICM_mapper_consistency(URM_DICT=self.SPLIT_URM_DICT,
                                      GLOBAL_MAPPER_DICT=self.SPLIT_GLOBAL_MAPPER_DICT,
                                      ICM_DICT=self.SPLIT_ICM_DICT,
                                      ICM_MAPPER_DICT=self.SPLIT_ICM_MAPPER_DICT,
                                      DATA_SPLITTER_NAME=self.DATA_SPLITTER_NAME)


class IncrementalSparseMatrix_ListBased(object):

    def __init__(self, auto_create_col_mapper=False, auto_create_row_mapper=False, n_rows=None, n_cols=None):

        super(IncrementalSparseMatrix_ListBased, self).__init__()

        self._row_list = []
        self._col_list = []
        self._data_list = []

        self._n_rows = n_rows
        self._n_cols = n_cols
        self._auto_create_column_mapper = auto_create_col_mapper
        self._auto_create_row_mapper = auto_create_row_mapper

        if self._auto_create_column_mapper:
            self._column_original_ID_to_index = {}

        if self._auto_create_row_mapper:
            self._row_original_ID_to_index = {}

    def add_data_lists(self, row_list_to_add, col_list_to_add, data_list_to_add):

        assert len(row_list_to_add) == len(col_list_to_add) and len(row_list_to_add) == len(data_list_to_add), \
            "IncrementalSparseMatrix: element lists must have different length"

        col_list_index = [self._get_column_index(column_id) for column_id in col_list_to_add]
        row_list_index = [self._get_row_index(row_id) for row_id in row_list_to_add]

        self._row_list.extend(row_list_index)
        self._col_list.extend(col_list_index)
        self._data_list.extend(data_list_to_add)

    def add_single_row(self, row_id, col_list, data=1.0):

        n_elements = len(col_list)

        col_list_index = [self._get_column_index(column_id) for column_id in col_list]
        row_index = self._get_row_index(row_id)

        self._row_list.extend([row_index] * n_elements)
        self._col_list.extend(col_list_index)
        self._data_list.extend([data] * n_elements)

    def get_column_token_to_id_mapper(self):

        if self._auto_create_column_mapper:
            return self._column_original_ID_to_index.copy()

        dummy_column_original_ID_to_index = {}

        for col in range(self._n_cols):
            dummy_column_original_ID_to_index[col] = col

        return dummy_column_original_ID_to_index

    def get_row_token_to_id_mapper(self):

        if self._auto_create_row_mapper:
            return self._row_original_ID_to_index.copy()

        dummy_row_original_ID_to_index = {}

        for row in range(self._n_rows):
            dummy_row_original_ID_to_index[row] = row

        return dummy_row_original_ID_to_index

    def _get_column_index(self, column_id):

        if not self._auto_create_column_mapper:
            column_index = column_id

        else:

            if column_id in self._column_original_ID_to_index:
                column_index = self._column_original_ID_to_index[column_id]

            else:
                column_index = len(self._column_original_ID_to_index)
                self._column_original_ID_to_index[column_id] = column_index

        return column_index

    def _get_row_index(self, row_id):

        if not self._auto_create_row_mapper:
            row_index = row_id

        else:

            if row_id in self._row_original_ID_to_index:
                row_index = self._row_original_ID_to_index[row_id]

            else:
                row_index = len(self._row_original_ID_to_index)
                self._row_original_ID_to_index[row_id] = row_index

        return row_index

    def get_nnz(self):
        return len(self._row_list)

    def get_SparseMatrix(self):

        if self._n_rows is None:
            self._n_rows = max(self._row_list) + 1

        if self._n_cols is None:
            self._n_cols = max(self._col_list) + 1

        shape = (self._n_rows, self._n_cols)

        sparseMatrix = sps.csr_matrix((self._data_list, (self._row_list, self._col_list)), shape=shape)
        sparseMatrix.eliminate_zeros()

        return sparseMatrix


class IncrementalSparseMatrix(IncrementalSparseMatrix_ListBased):

    def __init__(self, auto_create_col_mapper=False, auto_create_row_mapper=False, n_rows=None, n_cols=None,
                 dtype=np.float64):

        super(IncrementalSparseMatrix, self).__init__(auto_create_col_mapper=auto_create_col_mapper,
                                                      auto_create_row_mapper=auto_create_row_mapper,
                                                      n_rows=n_rows,
                                                      n_cols=n_cols)

        self._dataBlock = 10000000
        self._next_cell_pointer = 0

        self._dtype_data = dtype
        self._dtype_coordinates = np.uint32
        self._max_value_of_coordinate_dtype = np.iinfo(self._dtype_coordinates).max

        self._row_array = np.zeros(self._dataBlock, dtype=self._dtype_coordinates)
        self._col_array = np.zeros(self._dataBlock, dtype=self._dtype_coordinates)
        self._data_array = np.zeros(self._dataBlock, dtype=self._dtype_data)

    def get_nnz(self):
        return self._next_cell_pointer

    def add_data_lists(self, row_list_to_add, col_list_to_add, data_list_to_add):

        assert len(row_list_to_add) == len(col_list_to_add) and len(row_list_to_add) == len(data_list_to_add), \
            "IncrementalSparseMatrix: element lists must have the same length"

        for data_point_index in range(len(row_list_to_add)):

            if self._next_cell_pointer == len(self._row_array):
                self._row_array = np.concatenate(
                    (self._row_array, np.zeros(self._dataBlock, dtype=self._dtype_coordinates)))
                self._col_array = np.concatenate(
                    (self._col_array, np.zeros(self._dataBlock, dtype=self._dtype_coordinates)))
                self._data_array = np.concatenate((self._data_array, np.zeros(self._dataBlock, dtype=self._dtype_data)))

            row_index = self._get_row_index(row_list_to_add[data_point_index])
            col_index = self._get_column_index(col_list_to_add[data_point_index])

            self._row_array[self._next_cell_pointer] = row_index
            self._col_array[self._next_cell_pointer] = col_index
            self._data_array[self._next_cell_pointer] = data_list_to_add[data_point_index]

            self._next_cell_pointer += 1

    def add_single_row(self, row_index, col_list, data=1.0):

        n_elements = len(col_list)

        self.add_data_lists([row_index] * n_elements,
                            col_list,
                            [data] * n_elements)

    def get_SparseMatrix(self):
        if self._n_rows is None:
            self._n_rows = self._row_array.max() + 1

        if self._n_cols is None:
            self._n_cols = self._col_array.max() + 1

        shape = (self._n_rows, self._n_cols)

        sparseMatrix = sps.csr_matrix((self._data_array[:self._next_cell_pointer],
                                       (self._row_array[:self._next_cell_pointer],
                                        self._col_array[:self._next_cell_pointer])),
                                      shape=shape,
                                      dtype=self._dtype_data)

        sparseMatrix.eliminate_zeros()

        return sparseMatrix


def assert_disjoint_matrices(URM_list):
    """
    Checks whether the URM in the list have an empty intersection, therefore there is no data point contained in more than one
    URM at a time
    :param URM_list:
    :return:
    """

    URM_implicit_global = None

    cumulative_nnz = 0

    for URM in URM_list:

        cumulative_nnz += URM.nnz
        URM_implicit = URM.copy()
        URM_implicit.data = np.ones_like(URM_implicit.data)

        if URM_implicit_global is None:
            URM_implicit_global = URM_implicit

        else:
            URM_implicit_global += URM_implicit

    assert cumulative_nnz == URM_implicit_global.nnz, \
        "assert_disjoint_matrices: URM in list are not disjoint, {} data points are in more than one URM".format(
            cumulative_nnz - URM_implicit_global.nnz)

    return True
