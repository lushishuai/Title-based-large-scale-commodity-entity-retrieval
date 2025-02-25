from models.bert_model import BERTModel
import json
import numpy as np
import math
import pandas as pd
import torch.nn as nn
import random
import torch
from processors.data_utils import *
from tqdm import tqdm
from models.callbacks import *
import torch.nn.functional as F
import os

# os.environ["CUDA_VISIBLE_DEVICES"] = "2"

from models.progressbar import *


def get_dataset():
    dataset = []
    kb_ids = pd.read_pickle('data/kb_ids.pkl')
    with open('data/train.txt') as f:
        for index, line in enumerate(f):
            line = json.loads(line)
            text_id = line['text_id']
            implicit_entity = line['implicit_entity']
            for entity in implicit_entity:
                subject_id = entity['subject_id']
                if subject_id in kb_ids:
                    dataset.append((text_id, subject_id))
    return dataset


def get_test():
    dataset = []
    with open('data/dev.txt') as f:
        for index, line in enumerate(f):
            line = str(line)
            dataset.append((index, 111786))

    return dataset


def get_negative(subject_ids: dict, pos_id: str):
    while True:
        neg_id = random.choice(list(subject_ids.keys()))
        if neg_id != pos_id:
            break
    return neg_id


class DataLoaderTrain(object):
    def __init__(self, dataset, batch_size=2, shuffle=True):
        self.dataset = dataset

        self.kb_id_token = pd.read_pickle('data/kb_ids.pkl')
        self.query_id_token = pd.read_pickle('data/train_ids.pkl')

        self.batch_size = batch_size
        self.data_length = len(self.dataset)
        self.steps_per_epoch = math.ceil(self.data_length / batch_size)
        self.indexes = np.arange(self.data_length)
        self.shuffle = shuffle
        self.indexes_no = list(np.arange(self.data_length))

        self.length = self.steps_per_epoch

    def __len__(self):

        return self.length

    def get_indexes(self, i):
        return self.indexes[i * self.batch_size:(i + 1) * self.batch_size]

    def __iter__(self):
        # bert input
        anchor_ids = []
        anchor_mask = []
        positive_ids = []
        positive_mask = []
        negative_ids = []
        negative_mask = []
        batch_index = [i for i in range(len(self.dataset))]
        if self.shuffle:
            np.random.shuffle(batch_index)
        for j, i in enumerate(batch_index):
            data = self.dataset[i]
            text_id = data[0]
            positive_id = data[1]
            if positive_id not in self.kb_id_token:
                continue
            negative_id = get_negative(self.kb_id_token, positive_id)

            an_token = self.query_id_token[text_id]
            an_mask = [1] * len(an_token)

            pos_token = self.kb_id_token[positive_id]
            pos_mask = [1] * len(pos_token)

            neg_token = self.kb_id_token[negative_id]
            neg_mask = [1] * len(neg_token)

            anchor_ids.append(an_token)
            anchor_mask.append(an_mask)
            positive_ids.append(pos_token)
            positive_mask.append(pos_mask)
            negative_ids.append(neg_token)
            negative_mask.append(neg_mask)

            if len(anchor_ids) == self.batch_size or j == len(batch_index) - 1:
                # torch.tensor(batch[i], dtype=torch.long)

                anchor_ids = torch.tensor(seq_padding(anchor_ids), dtype=torch.long)
                anchor_mask = torch.tensor(seq_padding(anchor_mask), dtype=torch.long)
                positive_ids = torch.tensor(seq_padding(positive_ids), dtype=torch.long)
                positive_mask = torch.tensor(seq_padding(positive_mask), dtype=torch.long)
                negative_ids = torch.tensor(seq_padding(negative_ids), dtype=torch.long)
                negative_mask = torch.tensor(seq_padding(negative_mask), dtype=torch.long)
                yield anchor_ids, anchor_mask, positive_ids, positive_mask, negative_ids, negative_mask

                anchor_ids = []
                anchor_mask = []
                positive_ids = []
                positive_mask = []
                negative_ids = []
                negative_mask = []


class DataLoaderTest(object):
    def __init__(self, dataset, batch_size=5, shuffle=True):
        self.dataset = dataset

        self.kb_id_token = pd.read_pickle('data/kb_ids.pkl')
        self.query_id_token = pd.read_pickle('data/test_ids.pkl')

        self.batch_size = batch_size
        self.data_length = len(self.dataset)
        self.steps_per_epoch = math.ceil(self.data_length / batch_size)
        self.indexes = np.arange(self.data_length)
        self.shuffle = shuffle
        self.indexes_no = list(np.arange(self.data_length))

        self.length = self.steps_per_epoch

    def __len__(self):

        return self.length

    def get_indexes(self, i):
        return self.indexes[i * self.batch_size:(i + 1) * self.batch_size]

    def __iter__(self):
        # bert input
        anchor_ids = []
        anchor_mask = []
        positive_ids = []
        positive_mask = []
        negative_ids = []
        negative_mask = []
        batch_index = [i for i in range(len(self.dataset))]
        if self.shuffle:
            np.random.shuffle(batch_index)
        for j, i in enumerate(batch_index):
            data = self.dataset[i]
            text_id = data[0]
            positive_id = data[1]

            negative_id = get_negative(self.kb_id_token, positive_id)

            an_token = self.query_id_token[text_id]
            an_mask = [1] * len(an_token)

            pos_token = self.kb_id_token[positive_id]
            pos_mask = [1] * len(pos_token)

            neg_token = self.kb_id_token[negative_id]
            neg_mask = [1] * len(neg_token)

            anchor_ids.append(an_token)
            anchor_mask.append(an_mask)
            positive_ids.append(pos_token)
            positive_mask.append(pos_mask)
            negative_ids.append(neg_token)
            negative_mask.append(neg_mask)

            if len(anchor_ids) == self.batch_size or j == len(batch_index) - 1:
                # torch.tensor(batch[i], dtype=torch.long)

                anchor_ids = torch.tensor(seq_padding(anchor_ids), dtype=torch.long)
                anchor_mask = torch.tensor(seq_padding(anchor_mask), dtype=torch.long)
                positive_ids = torch.tensor(seq_padding(positive_ids), dtype=torch.long)
                positive_mask = torch.tensor(seq_padding(positive_mask), dtype=torch.long)
                negative_ids = torch.tensor(seq_padding(negative_ids), dtype=torch.long)
                negative_mask = torch.tensor(seq_padding(negative_mask), dtype=torch.long)
                yield anchor_ids, anchor_mask, positive_ids, positive_mask, negative_ids, negative_mask

                anchor_ids = []
                anchor_mask = []
                positive_ids = []
                positive_mask = []
                negative_ids = []
                negative_mask = []


class DataLoaderKb(object):
    def __init__(self, dataset, batch_size=5, ):
        self.dataset = dataset
        self.kb_id_token = pd.read_pickle('data/kb_ids.pkl')
        self.batch_size = batch_size
        self.data_length = len(self.dataset)
        self.steps_per_epoch = math.ceil(self.data_length / batch_size)
        self.indexes = np.arange(self.data_length)
        self.length = self.steps_per_epoch

    def __len__(self):

        return self.length

    def get_indexes(self, i):
        return self.indexes[i * self.batch_size:(i + 1) * self.batch_size]

    def __iter__(self):
        # bert input
        kb_token_ids = []
        kb_token_mask = []
        batch_index = [i for i in range(len(self.dataset))]
        for j, i in enumerate(batch_index):
            data = self.dataset[i]
            kb_id = data
            token_id = self.kb_id_token[kb_id]
            token_mask = [1] * len(token_id)
            kb_token_ids.append(token_id)
            kb_token_mask.append(token_mask)
            if len(kb_token_ids) == self.batch_size or j == len(batch_index) - 1:
                kb_token_ids = torch.tensor(seq_padding(kb_token_ids), dtype=torch.long)
                kb_token_mask = torch.tensor(seq_padding(kb_token_mask), dtype=torch.long)
                yield kb_token_ids, kb_token_mask
                kb_token_ids = []
                kb_token_mask = []


def train(index):
    model = BERTModel(bert_pre_model=BERT_TINY_MODEL)

    dataset = get_dataset()
    # train_dataset = dataset[:index * 10000] + dataset[(index + 1) * 10000:]
    # val_dataset = dataset[index * 10000:(index + 1) * 10000]
    train_dataset =  dataset[:500]
    val_dataset = dataset[500:1000]

    print(len(dataset))
    print(len(train_dataset))
    print(len(val_dataset))

    train_loader = DataLoaderTrain(train_dataset, batch_size=8)
    val_loader = DataLoaderTrain(val_dataset, batch_size=8)

    device = 'cuda'
    model.to(device)
    bert_model_params = list(map(id, model.bert_model.parameters()))
    base_params = filter(lambda p: id(p) not in bert_model_params,
                         model.parameters())
    params_list = [
        {"params": base_params, 'lr': 5e-04},
        {'params': model.bert_model.parameters(), 'lr': 3e-05}
    ]
    device_ids = range(torch.cuda.device_count())
    print(device_ids)
    model = nn.DataParallel(model)

    optimizer = torch.optim.Adam(params_list, lr=3e-05)  # torch.optim.Adam(params=model.parameters(), lr=2e-05)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.2, patience=1,
                                                           min_lr=5e-6, )
    earlystopping = EarlyStopping(model)
    mc = ModelCheckpoint(model, 'data/model' + str(index) + '_to100.pt')
    loss_function = torch.nn.TripletMarginLoss(margin=3)
    # epochs = 15
    epochs = 1
    for i in range(epochs):
        model.train()
        # tqdm_batch_iterator = tqdm(train_loader)
        ave_loss = 0
        pbar = ProgressBar(n_total=len(train_loader), desc=f'training{i}/{epochs}')
        for batch_index, batch in enumerate(train_loader):
            batch = [i.to('cuda') for i in batch]
            anchor_ids = batch[0]
            anchor_mask = batch[1]
            positive_ids = batch[2]
            positive_mask = batch[3]
            negative_ids = batch[4]
            negative_mask = batch[5]
            optimizer.zero_grad()
            anchor_out = model([anchor_ids, anchor_mask])
            positive_out = model([positive_ids, positive_mask])
            negative_out = model([negative_ids, negative_mask])

            loss = loss_function(anchor_out, positive_out, negative_out)
            ave_loss += loss.item() / len(train_loader)
            loss.backward()
            optimizer.step()
            pbar(step=batch_index, info={'loss': loss})
        print(ave_loss)
        model.eval()
        val_loss = 0.0
        preds, labels = [], []
        pos_distance = []
        neg_distance = []
        with torch.no_grad():
            tqdm_batch_iterator = val_loader
            for batch_index, batch in enumerate(tqdm_batch_iterator):
                batch = [i.to('cuda') for i in batch]
                anchor_ids = batch[0]
                anchor_mask = batch[1]
                positive_ids = batch[2]
                positive_mask = batch[3]
                negative_ids = batch[4]
                negative_mask = batch[5]
                anchor_out = model([anchor_ids, anchor_mask])
                positive_out = model([positive_ids, positive_mask])
                negative_out = model([negative_ids, negative_mask])
                loss = loss_function(anchor_out, positive_out, negative_out)
                val_loss += loss.item() / len(val_loader)
                dist_pos = F.pairwise_distance(anchor_out, positive_out, p=2).detach().cpu().numpy()
                pos_distance.extend(dist_pos)
                dist_neg = F.pairwise_distance(anchor_out, negative_out, p=2).detach().cpu().numpy()
                neg_distance.extend(dist_neg)
        scheduler.step(val_loss)
        earlystopping.step(val_loss)
        mc.epoch_step(val_loss)
        print('val loss', val_loss)
    torch.save(model.state_dict(),'data/model' + str(index) + '_to100.pt')


def eval_mean():
    start = time.time()
    model = BERTModel(bert_pre_model=BERT_TINY_MODEL)
    model = nn.DataParallel(model)
    kb_id_token = pd.read_pickle('data/kb_ids.pkl')
    query_id_token = pd.read_pickle('data/train_ids.pkl')
    subject_ids = list(kb_id_token.keys())
    dataset = get_dataset()[70000:]

    val_dataset = dataset
    merge_scores = []
    for index in range(1):

        model.load_state_dict(torch.load('data/model' + str(index) + '_to100.pt'))
        model.cuda()
        model.eval()
        kb_preds = []
        kb_loader = tqdm(DataLoaderKb(subject_ids, batch_size=8))
        for batch_index, batch in enumerate(kb_loader):
            batch = [i.to('cuda') for i in batch]
            anchor_out = model(batch).detach()
            kb_preds.append(anchor_out)
        kb_preds = torch.cat(kb_preds, dim=0)

        val_loader = DataLoaderTrain(val_dataset, batch_size=8, shuffle=False)

        tqdm_batch_iterator = tqdm(val_loader)
        val_preds = []
        for batch_index, batch in enumerate(tqdm_batch_iterator):
            batch = [i.to('cuda') for i in batch]
            anchor_ids = batch[0]
            anchor_mask = batch[1]
            anchor_out = model([anchor_ids, anchor_mask]).detach()
            for i in range(len(anchor_out)):
                val_preds.append(anchor_out[i])
        scores = []
        for pred, data in zip(val_preds, val_dataset):
            score = F.pairwise_distance(pred, kb_preds, p=2).cpu().numpy()
            scores.append(score)
        scores = np.array(scores)
        merge_scores.append(scores)
    recall_num = 0
    recall_top100 = {}
    merge_scores = np.mean(merge_scores, axis=0)
    for data, scores in zip(val_dataset, merge_scores):
        text_id = data[0]
        subject_id = data[1]
        indices = scores.argsort()[:100]
        recall_subject_ids = [subject_ids[index] for index in indices]
        if subject_id in recall_subject_ids:
            recall_num += 1
        recall_top100[text_id] = recall_subject_ids
    print(recall_num / len(val_dataset))
    print(recall_num)
    pd.to_pickle(recall_top100, 'data/recall_top100.pkl')
    print(time.time() - start)


def eval_union():  # 删除top 100 仍不能召回的数据 或许会好
    dataset = get_dataset()
    dataset = dataset
    model = BERTModel(bert_pre_model=BERT_TINY_MODEL)
    model = nn.DataParallel(model)
    def eval_(index):
        model.load_state_dict(torch.load('data/model' + str(index) + '_to100.pt'))
        model.cuda()
        model.eval()
        kb_id_token = pd.read_pickle('data/kb_ids.pkl')
        query_id_token = pd.read_pickle('data/train_ids.pkl')
        subject_ids = list(kb_id_token.keys())

        kb_preds = []
        kb_loader = tqdm(DataLoaderKb(subject_ids, batch_size=8))
        for batch_index, batch in enumerate(kb_loader):
            batch = [i.to('cuda') for i in batch]
            anchor_out = model(batch).detach()
            kb_preds.append(anchor_out)
        kb_preds = torch.cat(kb_preds, dim=0)

        data_loader = DataLoaderTrain(dataset, batch_size=8, shuffle=False)
        recall_top100 = {}
        recall_top100_score = {}
        tqdm_batch_iterator = tqdm(data_loader)
        val_preds = []
        for batch_index, batch in enumerate(tqdm_batch_iterator):
            batch = [i.to('cuda') for i in batch]
            anchor_ids = batch[0]
            anchor_mask = batch[1]
            anchor_out = model([anchor_ids, anchor_mask]).detach()
            for i in range(len(anchor_out)):
                val_preds.append(anchor_out[i])
        recall_num = 0
        for pred, data in zip(val_preds, dataset):
            text_id = data[0]
            subject_id = data[1]
            scores = F.pairwise_distance(pred, kb_preds, p=2).cpu().numpy()
            indices = scores.argsort()[:100]
            recall_subject_ids = [subject_ids[index] for index in indices]
            if subject_id in recall_subject_ids:
                recall_num += 1
            recall_top100[text_id] = recall_subject_ids
            recall_top100_score[text_id] = scores[indices]
        print(recall_num / len(dataset))
        print(recall_num)
        return recall_top100, recall_top100_score

    recall_top100_all = []
    recall_top100_score_all = []
    top_len = 0
    for i in range(1):
        top100, top100_score = eval_(i)
        recall_top100_all.append(top100)
        recall_top100_score_all.append(top100_score)

    recall_num = 0
    recall_top100 = {}
    for data in dataset:
        text_id = data[0]
        subject_id = data[1]
        # recall_subject_ids = []
        recall_subject_ids = dict()

        for top100, top100_score in zip(recall_top100_all, recall_top100_score_all):
            top_subject = top100[text_id]
            top_score = top100_score[text_id]
            for sub, sco in zip(top_subject, top_score):
                if sub in recall_subject_ids:
                    if sco < recall_subject_ids[sub]:
                        recall_subject_ids[sub] = sco
                else:
                    recall_subject_ids[sub] = sco
        recall_subject_ids = sorted(recall_subject_ids.items(), key=lambda d: d[1], reverse=False)
        recall_subject_ids = [i[0] for i in recall_subject_ids][:100]
        # recall_subject_ids = set(top100[text_id]) | recall_subject_ids
        top_len += len(recall_subject_ids)

        if subject_id in recall_subject_ids:
            recall_num += 1

        recall_top100[text_id] = recall_subject_ids
    print(recall_num / len(dataset))
    print(recall_num)
    print(top_len)
    print(top_len / len(dataset))
    pd.to_pickle(recall_top100, 'data/recall_top100.pkl')


def predict_mean():
    start = time.time()
    model = BERTModel(bert_pre_model=BERT_TINY_MODEL)
    model = nn.DataParallel(model)
    kb_id_token = pd.read_pickle('data/kb_ids.pkl')
    query_id_token = pd.read_pickle('data/train_ids.pkl')
    subject_ids = list(kb_id_token.keys())
    test_dataset = get_test()
    merge_scores = []
    for index in range(1):

        model.load_state_dict(torch.load('data/model' + str(index) + '_to100.pt'))
        model.cuda()
        model.eval()
        kb_preds = []
        kb_loader = tqdm(DataLoaderKb(subject_ids, batch_size=8))
        for batch_index, batch in enumerate(kb_loader):
            batch = [i.to('cuda') for i in batch]
            anchor_out = model(batch).detach()
            kb_preds.append(anchor_out)
        kb_preds = torch.cat(kb_preds, dim=0)

        data_loader = DataLoaderTest(test_dataset, batch_size=8, shuffle=False)

        tqdm_batch_iterator = tqdm(data_loader)
        val_preds = []
        for batch_index, batch in enumerate(tqdm_batch_iterator):
            batch = [i.to('cuda') for i in batch]
            anchor_ids = batch[0]
            anchor_mask = batch[1]
            anchor_out = model([anchor_ids, anchor_mask]).detach()
            for i in range(len(anchor_out)):
                val_preds.append(anchor_out[i])
        scores = []
        for pred, data in zip(val_preds, test_dataset):
            score = F.pairwise_distance(pred, kb_preds, p=2).cpu().numpy()
            scores.append(score)
        scores = np.array(scores)
        merge_scores.append(scores)
    recall_num = 0
    recall_top100 = {}
    merge_scores = np.mean(merge_scores, axis=0)
    for data, scores in zip(test_dataset, merge_scores):
        text_id = data[0]

        indices = scores.argsort()[:100]
        recall_subject_ids = [subject_ids[index] for index in indices]
        recall_top100[text_id] = recall_subject_ids
    print(recall_num / len(test_dataset))
    print(recall_num)
    pd.to_pickle(recall_top100, 'data/test_recall_top100.pkl')
    print(time.time() - start)


def predict_union():
    dataset = get_test()
    model = BERTModel(bert_pre_model=BERT_TINY_MODEL)
    model = nn.DataParallel(model)

    def predict_(index):

        model.load_state_dict(torch.load('data/model' + str(index) + '_to100.pt'))
        model.cuda()
        model.eval()
        kb_id_token = pd.read_pickle('data/kb_ids.pkl')
        subject_ids = list(kb_id_token.keys())

        kb_preds = []
        kb_loader = tqdm(DataLoaderKb(subject_ids, batch_size=8))
        for batch_index, batch in enumerate(kb_loader):
            batch = [i.to('cuda') for i in batch]
            anchor_out = model(batch).detach()
            kb_preds.append(anchor_out)
        kb_preds = torch.cat(kb_preds, dim=0)
        data_loader = DataLoaderTest(dataset, batch_size=8, shuffle=False)
        recall_top100 = {}
        recall_top100_score = {}
        tqdm_batch_iterator = tqdm(data_loader)
        val_preds = []
        for batch_index, batch in enumerate(tqdm_batch_iterator):
            batch = [i.to('cuda') for i in batch]
            anchor_ids = batch[0]
            anchor_mask = batch[1]
            anchor_out = model([anchor_ids, anchor_mask]).detach()
            for i in range(len(anchor_out)):
                val_preds.append(anchor_out[i])

        recall_num = 0
        for pred, data in zip(val_preds, dataset):
            text_id = data[0]
            subject_id = data[1]
            scores = F.pairwise_distance(pred, kb_preds, p=2).cpu().numpy()
            indices = scores.argsort()[:100]
            recall_subject_ids = [subject_ids[index] for index in indices]
            if subject_id in recall_subject_ids:
                recall_num += 1
            recall_top100_score[text_id] = scores[indices]
            recall_top100[text_id] = recall_subject_ids
        print(recall_num / len(dataset))
        print(recall_num)

        return recall_top100, recall_top100_score

    recall_top100_all = []
    recall_top100_score_all = []
    top_len = 0
    for i in range(1):
        top100, top100_score = predict_(i)
        recall_top100_all.append(top100)
        recall_top100_score_all.append(top100_score)

    recall_num = 0
    recall_top100 = {}
    for data in dataset:
        text_id = data[0]
        subject_id = data[1]
        recall_subject_ids = dict()

        for top100, top100_score in zip(recall_top100_all, recall_top100_score_all):
            top_subject = top100[text_id]
            top_score = top100_score[text_id]
            for sub, sco in zip(top_subject, top_score):
                if sub in recall_subject_ids:
                    if sco < recall_subject_ids[sub]:
                        recall_subject_ids[sub] = sco
                else:
                    recall_subject_ids[sub] = sco
        recall_subject_ids = sorted(recall_subject_ids.items(), key=lambda d: d[1], reverse=False)
        recall_subject_ids = [i[0] for i in recall_subject_ids][:100]
        top_len += len(recall_subject_ids)

        if subject_id in recall_subject_ids:
            recall_num += 1
        recall_top100[text_id] = list(recall_subject_ids)
    print(recall_num / len(dataset))
    print(recall_num)
    print(top_len / len(dataset))
    pd.to_pickle(recall_top100, 'data/test_recall_top100.pkl')


if __name__ == '__main__':

    # train(0)
    # eval_mean() #0.9791
    eval_union()  # 0.9809
    predict_union()

